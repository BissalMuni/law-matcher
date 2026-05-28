"""입안심사 영속화 + 등록 조례/상위법령 연동 서비스 (Phase 3).

핵심:
- 등록 조례(ordinance_texts.articles_json)에서 조문을 시드 → drafting_sections
- 상위법령(ordinance_law_mappings→laws)을 AI 작성/검증 컨텍스트로 제공
- 프로젝트/단계/조문/메시지/검증/스냅샷 영속화 (drafting_* 테이블)

get_db는 자동 커밋하지 않으므로 변경 메서드에서 명시적으로 commit/flush 한다
(backend/services/ordinance_service.py 와 동일 패턴).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.drafting import (
    DraftingProject,
    DraftingStage,
    DraftingSection,
    DraftingMessage,
    DraftingValidation,
    DraftingSnapshot,
)
from backend.models.ordinance import Ordinance
from backend.models.ordinance_text import OrdinanceText
from backend.models.ordinance_law_mapping import OrdinanceLawMapping
from backend.models.law import Law

_ARTICLE_NO = re.compile(r"제(\d+)조")
_ARTICLE_LABEL = re.compile(r"^(제\d+조(?:의\d+)?\s*(?:\([^)]*\))?)")


def classify_stage_key(title: str, label: str) -> str:
    """조문 제목/라벨로 적절한 표준 단계 key를 추정한다 (개정 조문 자동 분류).

    매칭 안 되는 일반 조문은 본칙(main)으로 보낸다.
    """
    t = f"{title} {label}"
    if "목적" in t:
        return "purpose"
    if "정의" in t:
        return "definition"
    if any(k in t for k in ("적용", "범위", "책무", "책임", "적용대상")):
        return "scope"
    if any(k in t for k in ("부칙", "시행일", "경과조치")):
        return "supplementary"
    return "main"

# 표준 8단계 템플릿 (StageKey ↔ 라벨 ↔ 근거 위키 섹션)
STAGE_TEMPLATE: list[dict] = [
    {"key": "meta", "label": "제명·종류", "wiki_ref": "ebansimsa/3.1.1", "required": True},
    {"key": "purpose", "label": "목적 규정", "wiki_ref": "ebansimsa/2.1.2", "required": True},
    {"key": "definition", "label": "정의 규정", "wiki_ref": "ebansimsa/2.1.4", "required": False},
    {"key": "scope", "label": "적용범위·책무", "wiki_ref": "ebansimsa/2.1.6", "required": False},
    {"key": "main", "label": "본칙", "wiki_ref": "ebansimsa/2.2.1", "required": True},
    {"key": "supplementary", "label": "부칙", "wiki_ref": "ebansimsa/2.3.1", "required": True},
    {"key": "review", "label": "전체 검토", "wiki_ref": None, "required": True},
    {"key": "finalize", "label": "최종 출력", "wiki_ref": None, "required": True},
]


def _derive_section_fields(idx: int, entry: dict) -> dict:
    """articles_json 한 항목에서 drafting_sections 필드를 도출한다.

    article_content가 '제1조(목적) ...'로 시작하는 법제처 자치법규 포맷을 활용한다.
    """
    body = (entry.get("article_content") or "").strip()
    title = (entry.get("article_title") or "").strip()

    # 조 번호: 본문/번호에서 '제N조' 추출, 없으면 순번
    m = _ARTICLE_NO.search(body) or _ARTICLE_NO.search(str(entry.get("article_no") or ""))
    article_no = int(m.group(1)) if m else idx + 1

    # 라벨: 본문 앞머리의 '제N조(제목)' 사용, 없으면 합성
    lm = _ARTICLE_LABEL.match(body)
    if lm:
        article_label = lm.group(1).strip()
    else:
        article_label = f"제{article_no}조({title})" if title else f"제{article_no}조"

    return {
        "article_no": article_no,
        "article_label": article_label,
        "title": title or article_label,
        "body": body,
    }


class DraftingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- 등록 조례 / 상위법령 연동 ----------

    async def list_source_ordinances(
        self, query: Optional[str] = None, limit: int = 30
    ) -> list[dict]:
        """입안심사 시작에 쓸 등록 조례 후보 목록 (본문 보유·상위법령 수 포함)."""
        stmt = (
            select(
                Ordinance.id,
                Ordinance.name,
                Ordinance.category,
                Ordinance.org_name,
                func.count(func.distinct(OrdinanceLawMapping.id)).label("parent_law_count"),
                func.count(func.distinct(OrdinanceText.id)).label("has_text"),
            )
            .outerjoin(OrdinanceLawMapping, OrdinanceLawMapping.ordinance_id == Ordinance.id)
            .outerjoin(OrdinanceText, OrdinanceText.ordinance_id == Ordinance.id)
            .group_by(Ordinance.id)
            .order_by(Ordinance.name)
            .limit(limit)
        )
        if query:
            stmt = stmt.where(Ordinance.name.ilike(f"%{query}%"))
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "category": r.category,
                "org_name": r.org_name,
                "parent_law_count": int(r.parent_law_count or 0),
                "has_text": bool(r.has_text),
            }
            for r in rows
        ]

    async def get_parent_laws(self, ordinance_id: int) -> list[dict]:
        """조례의 상위법령 목록 (AI 컨텍스트·UI 표시용)."""
        stmt = (
            select(Law, OrdinanceLawMapping.related_articles)
            .join(OrdinanceLawMapping, OrdinanceLawMapping.law_id == Law.id)
            .where(OrdinanceLawMapping.ordinance_id == ordinance_id)
            .order_by(Law.law_name)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "law_id": law.id,
                "law_name": law.law_name,
                "law_type": law.law_type,
                "proclaimed_date": law.proclaimed_date.isoformat() if law.proclaimed_date else None,
                "related_articles": related,
            }
            for law, related in rows
        ]

    def _parent_law_context(self, parent_laws: list[dict]) -> list[str]:
        """상위법령 dict 목록을 프롬프트 주입용 문자열 목록으로 변환한다."""
        out: list[str] = []
        for p in parent_laws:
            s = f"{p['law_name']} ({p['law_type']})"
            if p.get("related_articles"):
                s += f" — 관련 조문: {p['related_articles']}"
            out.append(s)
        return out

    async def parse_ordinance_sections(self, ordinance_id: int) -> list[dict]:
        """등록 조례 본문을 조 단위 필드 목록으로 변환한다 (시드/미리보기 공용)."""
        text_row = (
            await self.db.execute(
                select(OrdinanceText).where(OrdinanceText.ordinance_id == ordinance_id)
            )
        ).scalar_one_or_none()
        if not text_row:
            return []

        sections: list[dict] = []
        if text_row.articles_json:
            for idx, entry in enumerate(text_row.articles_json):
                fields = _derive_section_fields(idx, entry)
                if fields["body"]:
                    sections.append({**fields, "sort_order": idx})
        elif text_row.full_text:
            # 폴백: 포팅한 파서로 분리
            from backend.drafting.parser import parse_ordinance

            for pa in parse_ordinance(text_row.full_text):
                sections.append(
                    {
                        "article_no": pa.article_no,
                        "article_label": pa.article_label,
                        "title": pa.title or pa.article_label,
                        "body": pa.body,
                        "sort_order": pa.order,
                    }
                )
        return sections

    async def preview_source_ordinance(self, ordinance_id: int) -> dict:
        """등록 조례 미리보기 — 조문 + 상위법령."""
        ordinance = (
            await self.db.execute(select(Ordinance).where(Ordinance.id == ordinance_id))
        ).scalar_one_or_none()
        if not ordinance:
            return {"found": False}
        sections = await self.parse_ordinance_sections(ordinance_id)
        parent_laws = await self.get_parent_laws(ordinance_id)
        return {
            "found": True,
            "ordinance": {
                "id": ordinance.id,
                "name": ordinance.name,
                "category": ordinance.category,
                "org_name": ordinance.org_name,
                "detail_link": ordinance.detail_link,
            },
            "sections": sections,
            "parent_laws": parent_laws,
            "section_count": len(sections),
        }

    # ---------- 프로젝트 라이프사이클 ----------

    async def create_project(
        self,
        kind: str,
        title: str,
        municipality: str,
        ordinance_id: Optional[int] = None,
        source_url: Optional[str] = None,
    ) -> DraftingProject:
        """프로젝트 생성 + 표준 8단계 시드. 개정 모드면 등록 조례 조문을 시드한다."""
        project = DraftingProject(
            kind=kind,
            title=title,
            municipality=municipality,
            ordinance_id=ordinance_id,
            source_url=source_url,
            status="active",
            progress=0,
        )
        self.db.add(project)
        await self.db.flush()  # project.id 확보

        # 8단계 시드
        stages_by_key: dict[str, DraftingStage] = {}
        for order, tpl in enumerate(STAGE_TEMPLATE):
            stage = DraftingStage(
                project_id=project.id,
                key=tpl["key"],
                label=tpl["label"],
                sort_order=order,
                required=tpl["required"],
                status="available" if order == 0 else "locked",
                wiki_ref=tpl["wiki_ref"],
            )
            self.db.add(stage)
            stages_by_key[tpl["key"]] = stage
        await self.db.flush()

        # 개정 모드: 등록 조례 조문 시드 (원본 보존 → original_body)
        # 조문 제목으로 적절한 단계에 자동 분류한다 (목적→목적규정 등). 단계 클릭이 정상 동작하도록.
        if ordinance_id and kind in ("amend_partial", "amend_full"):
            main_stage = stages_by_key["main"]
            sections = await self.parse_ordinance_sections(ordinance_id)
            for sec in sections:
                key = classify_stage_key(sec["title"], sec["article_label"])
                target_stage = stages_by_key.get(key, main_stage)
                self.db.add(
                    DraftingSection(
                        project_id=project.id,
                        stage_id=target_stage.id,
                        article_no=sec["article_no"],
                        article_label=sec["article_label"],
                        title=sec["title"],
                        body=sec["body"],
                        original_body=sec["body"],  # 개정 전 원본 (읽기전용 비교용)
                        change_type="unchanged",
                        sort_order=sec["sort_order"],
                    )
                )

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update_project(self, project_id: int, fields: dict) -> Optional[DraftingProject]:
        """프로젝트 메타(제명/종류/지자체/상태/진행률) 수정."""
        project = (
            await self.db.execute(
                select(DraftingProject).where(DraftingProject.id == project_id)
            )
        ).scalar_one_or_none()
        if not project:
            return None
        for f in ("kind", "title", "municipality", "source_url", "status", "progress"):
            if f in fields and fields[f] is not None:
                setattr(project, f, fields[f])
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def map_section_criteria(self, section_id: int) -> Optional[list[dict]]:
        """조문에 적용되는 기준을 AI로 추려 section.mapped_criteria에 저장하고 반환한다.

        조문 선택 시 '적용 기준 칩'으로 표시된다 (조문 중심 UI).
        """
        from backend.drafting.criteria import catalog as load_catalog
        from backend.drafting.llm import DraftingLLM

        section = (
            await self.db.execute(
                select(DraftingSection).where(DraftingSection.id == section_id)
            )
        ).scalar_one_or_none()
        if not section:
            return None

        cat = load_catalog()  # [{criterion_id, source, title}]
        catalog_text = "\n".join(
            f"- {c['source']}/{c['criterion_id']}: {c['title'] or ''}" for c in cat
        )
        system = (
            "당신은 조례 심사자다. 주어진 조문에 '실제로 적용되는' 입안심사·정비 기준만 고른다.\n"
            "조문의 성격(정의·목적·벌칙·위임 등)과 직접 관련된 기준만 선택하고, "
            "무관한 기준은 절대 넣지 마라.\n"
            "반드시 아래 JSON 형식으로만 답하라(다른 텍스트 금지):\n"
            '{"criterion_ids": ["<source>/<id>", ...]}\n'
            "id 는 카탈로그의 'source/id' 표기를 그대로 쓴다."
        )
        user = (
            f"[조문] {section.article_label or ''} {section.title}\n{section.body}\n\n"
            f"[기준 카탈로그]\n{catalog_text}"
        )
        client = DraftingLLM()
        result = await client.call(system, user, max_tokens=512)
        ids = set(result.get("criterion_ids", [])) if isinstance(result, dict) else set()
        chosen = [c for c in cat if f"{c['source']}/{c['criterion_id']}" in ids]

        section.mapped_criteria = chosen
        await self.db.commit()
        return chosen

    async def list_projects(self) -> list[DraftingProject]:
        rows = (
            await self.db.execute(
                select(DraftingProject).order_by(DraftingProject.updated_at.desc())
            )
        ).scalars().all()
        return list(rows)

    async def get_project(self, project_id: int) -> Optional[DraftingProject]:
        return (
            await self.db.execute(
                select(DraftingProject)
                .options(
                    selectinload(DraftingProject.stages),
                    selectinload(DraftingProject.sections),
                )
                .where(DraftingProject.id == project_id)
            )
        ).scalar_one_or_none()

    async def delete_project(self, project_id: int) -> bool:
        project = (
            await self.db.execute(
                select(DraftingProject).where(DraftingProject.id == project_id)
            )
        ).scalar_one_or_none()
        if not project:
            return False
        await self.db.delete(project)  # cascade 로 하위 전부 삭제
        await self.db.commit()
        return True

    # ---------- 단계 / 조문 / 메시지 / 검증 / 스냅샷 ----------

    async def list_stages(self, project_id: int) -> list[DraftingStage]:
        rows = (
            await self.db.execute(
                select(DraftingStage)
                .where(DraftingStage.project_id == project_id)
                .order_by(DraftingStage.sort_order)
            )
        ).scalars().all()
        return list(rows)

    async def update_stage_status(
        self, stage_id: int, status: str, stale_reason: Optional[str] = None
    ) -> Optional[DraftingStage]:
        stage = (
            await self.db.execute(select(DraftingStage).where(DraftingStage.id == stage_id))
        ).scalar_one_or_none()
        if not stage:
            return None
        stage.status = status
        stage.stale_reason = stale_reason
        if status == "confirmed":
            stage.confirmed_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(stage)
        return stage

    async def list_sections(self, project_id: int) -> list[DraftingSection]:
        rows = (
            await self.db.execute(
                select(DraftingSection)
                .where(DraftingSection.project_id == project_id)
                .order_by(DraftingSection.sort_order)
            )
        ).scalars().all()
        return list(rows)

    async def upsert_section(self, data: dict) -> DraftingSection:
        """조문 생성/수정. data['id'] 있으면 수정."""
        section: Optional[DraftingSection] = None
        if data.get("id"):
            section = (
                await self.db.execute(
                    select(DraftingSection).where(DraftingSection.id == data["id"])
                )
            ).scalar_one_or_none()
        if section is None:
            section = DraftingSection(
                project_id=data["project_id"],
                stage_id=data["stage_id"],
                article_no=data.get("article_no", 0),
                sort_order=data.get("sort_order", 0),
                title=data.get("title", ""),
                body=data.get("body", ""),
            )
            self.db.add(section)
        for f in ("article_no", "article_label", "title", "body", "original_body",
                  "change_type", "sort_order", "stage_id"):
            if f in data and data[f] is not None:
                setattr(section, f, data[f])
        await self.db.commit()
        await self.db.refresh(section)
        return section

    async def delete_section(self, section_id: int) -> bool:
        section = (
            await self.db.execute(select(DraftingSection).where(DraftingSection.id == section_id))
        ).scalar_one_or_none()
        if not section:
            return False
        await self.db.delete(section)
        await self.db.commit()
        return True

    async def list_messages(self, stage_id: int) -> list[DraftingMessage]:
        rows = (
            await self.db.execute(
                select(DraftingMessage)
                .where(DraftingMessage.stage_id == stage_id)
                .order_by(DraftingMessage.created_at)
            )
        ).scalars().all()
        return list(rows)

    async def add_message(self, data: dict) -> DraftingMessage:
        msg = DraftingMessage(
            stage_id=data["stage_id"],
            role=data["role"],
            content=data["content"],
            citations=data.get("citations"),
            attachments=data.get("attachments"),
            applied=data.get("applied", False),
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def save_validations(
        self, section_id: int, results: list[dict], replace: bool = True
    ) -> int:
        """검증 결과 저장. replace=True면 해당 조문의 기존 검증을 비우고 새로 넣는다."""
        if replace:
            existing = (
                await self.db.execute(
                    select(DraftingValidation).where(
                        DraftingValidation.section_id == section_id
                    )
                )
            ).scalars().all()
            for e in existing:
                await self.db.delete(e)
        for r in results:
            self.db.add(
                DraftingValidation(
                    section_id=section_id,
                    criterion_id=r["criterion_id"],
                    source=r["source"],
                    verdict=r["verdict"],
                    severity=r.get("severity"),
                    reason=r.get("reason"),
                    suggestion=r.get("suggestion"),
                    dismissed_reason=r.get("dismissed_reason"),
                )
            )
        await self.db.commit()
        return len(results)

    async def list_validations(self, section_id: int) -> list[DraftingValidation]:
        rows = (
            await self.db.execute(
                select(DraftingValidation).where(
                    DraftingValidation.section_id == section_id
                )
            )
        ).scalars().all()
        return list(rows)

    async def create_snapshot(self, data: dict) -> DraftingSnapshot:
        snap = DraftingSnapshot(
            stage_id=data["stage_id"],
            trigger_type=data["trigger_type"],
            actor=data["actor"],
            label=data.get("label"),
            content=data["content"],
        )
        self.db.add(snap)
        await self.db.commit()
        await self.db.refresh(snap)
        return snap
