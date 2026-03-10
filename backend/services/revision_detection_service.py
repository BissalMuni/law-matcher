"""
Revision detection service for 3-tab comparison methods.
"""
import logging
import re
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.core.config import settings
from backend.external.moleg_client import MolegClient
from backend.models.law import Law
from backend.models.law_revision_reason import LawRevisionReason
from backend.models.ordinance import Ordinance
from backend.models.ordinance_law_mapping import OrdinanceLawMapping
from backend.models.revision_detection_result import RevisionDetectionResult
from backend.services.amendment_parser import parse_amendment_articles, match_articles_to_ordinance

logger = logging.getLogger(__name__)


class RevisionDetectionService:
    """3가지 방식(공포일자/조문변경/개정이유) 개정 판별 서비스"""

    DEFAULT_METHODS = ("proclaimed_date", "revision_reason")

    def __init__(self, db: AsyncSession, moleg_client: Optional[MolegClient] = None):
        self.db = db
        self.moleg_client = moleg_client

    async def detect_by_proclaimed_date(self, ordinance: Ordinance, law: Law) -> Dict[str, Any]:
        ordinance_date = self._get_ordinance_reference_date(ordinance)
        law_date = law.proclaimed_date
        needs_revision = bool(ordinance_date and law_date and law_date > ordinance_date)
        days_diff = None
        if ordinance_date and law_date:
            days_diff = (law_date - ordinance_date).days

        detected_at = datetime.utcnow()
        return {
            "method": "proclaimed_date",
            "needs_revision": needs_revision,
            "detail": {
                "law_id": law.id,
                "law_name": law.law_name,
                "ordinance_id": ordinance.id,
                "ordinance_name": ordinance.name,
                "ordinance_date": ordinance_date.isoformat() if ordinance_date else None,
                "law_proclaimed_date": law_date.isoformat() if law_date else None,
                "days_diff": days_diff,
            },
            "detected_at": detected_at,
        }

    async def detect_by_revision_reason(self, ordinance: Ordinance, law: Law) -> Dict[str, Any]:
        reason = await self._get_or_fetch_revision_reason(law)
        extracted_articles = self._extract_articles_from_reason(reason)
        # 연계 조문 목록: OrdinanceLawMapping.related_articles 필드 사용
        law_mapping_stmt = select(OrdinanceLawMapping.related_articles).where(
            and_(
                OrdinanceLawMapping.ordinance_id == ordinance.id,
                OrdinanceLawMapping.law_id == law.id,
            )
        )
        related_articles_str = (await self.db.execute(law_mapping_stmt)).scalar_one_or_none()
        mapped_articles = sorted(
            {self._normalize_article_no(c) for c in self._split_related_articles(related_articles_str) if c},
            key=self._article_sort_key,
        )
        matched = match_articles_to_ordinance(extracted_articles, mapped_articles)

        note = None
        if law.revision_type == "타법개정" and not reason.revision_reason:
            note = "타법개정 - 상세 확인 필요"

        detected_at = datetime.utcnow()
        return {
            "method": "revision_reason",
            "needs_revision": matched["needs_revision"],
            "detail": {
                "law_id": law.id,
                "law_name": law.law_name,
                "ordinance_id": ordinance.id,
                "ordinance_name": ordinance.name,
                "revision_reason": reason.revision_reason,
                "amendment_content": reason.amendment_content,
                "match": matched,
                "note": note,
            },
            "detected_at": detected_at,
        }

    async def detect_all(
        self,
        ordinance_id: int,
        methods: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        ordinance = await self.db.get(Ordinance, ordinance_id)
        if not ordinance:
            raise ValueError(f"Ordinance not found: {ordinance_id}")
        previous_results = await self.get_cached_results(ordinance_id)
        previous_signature = self._build_signature(previous_results.get("results", []))

        method_list = [m for m in (methods or self.DEFAULT_METHODS) if m in self.DEFAULT_METHODS]
        if not method_list:
            method_list = list(self.DEFAULT_METHODS)

        mapping_stmt = (
            select(OrdinanceLawMapping)
            .options(joinedload(OrdinanceLawMapping.law))
            .where(OrdinanceLawMapping.ordinance_id == ordinance_id)
        )
        mappings = (await self.db.execute(mapping_stmt)).scalars().all()

        per_law_results: List[Dict[str, Any]] = []
        for mapping in mappings:
            if not mapping.law:
                continue
            for method in method_list:
                try:
                    result = await self._run_method(method, ordinance, mapping.law)
                except Exception as exc:
                    logger.exception(
                        "Detection failed: ordinance_id=%s law_id=%s method=%s error=%s",
                        ordinance.id,
                        mapping.law.id,
                        method,
                        exc,
                    )
                    result = {
                        "method": method,
                        "needs_revision": False,
                        "detail": {
                            "law_id": mapping.law.id,
                            "law_name": mapping.law.law_name,
                            "ordinance_id": ordinance.id,
                            "ordinance_name": ordinance.name,
                            "error": str(exc),
                        },
                        "detected_at": datetime.utcnow(),
                    }
                per_law_results.append(result)
                await self._upsert_detection_result(
                    ordinance_id=ordinance.id,
                    law_id=mapping.law.id,
                    method=method,
                    needs_revision=result["needs_revision"],
                    detail=result["detail"],
                    detected_at=result["detected_at"],
                )

        aggregated = self._aggregate_results(ordinance.id, ordinance.name, per_law_results)
        current_signature = self._build_signature(aggregated.get("results", []))
        changed = previous_signature != current_signature
        changed_methods = self._find_changed_methods(
            previous_results.get("results", []),
            aggregated.get("results", []),
        )
        overall_needs_revision = any(item.get("needs_revision") for item in aggregated.get("results", []))
        ordinance.needs_revision = overall_needs_revision

        if changed and overall_needs_revision:
            aggregated["notification"] = {
                "message": "새로운 변경이 감지되었습니다.",
                "changed_methods": changed_methods,
                "created_at": datetime.utcnow().isoformat(),
            }

        await self.db.commit()
        return aggregated

    async def get_cached_results(self, ordinance_id: int) -> Dict[str, Any]:
        ordinance = await self.db.get(Ordinance, ordinance_id)
        if not ordinance:
            raise ValueError(f"Ordinance not found: {ordinance_id}")

        stmt = (
            select(RevisionDetectionResult)
            .where(RevisionDetectionResult.ordinance_id == ordinance_id)
            .order_by(RevisionDetectionResult.detected_at.desc())
        )
        rows = (await self.db.execute(stmt)).scalars().all()

        per_law_results = [
            {
                "method": row.detection_method,
                "needs_revision": row.needs_revision,
                "detail": row.detail or {},
                "detected_at": row.detected_at,
            }
            for row in rows
        ]
        return self._aggregate_results(ordinance.id, ordinance.name, per_law_results)

    async def _run_method(self, method: str, ordinance: Ordinance, law: Law) -> Dict[str, Any]:
        if method == "proclaimed_date":
            return await self.detect_by_proclaimed_date(ordinance, law)
        if method == "revision_reason":
            return await self.detect_by_revision_reason(ordinance, law)
        raise ValueError(f"Unsupported method: {method}")

    async def _upsert_detection_result(
        self,
        ordinance_id: int,
        law_id: int,
        method: str,
        needs_revision: bool,
        detail: Dict[str, Any],
        detected_at: datetime,
    ) -> None:
        stmt = select(RevisionDetectionResult).where(
            and_(
                RevisionDetectionResult.ordinance_id == ordinance_id,
                RevisionDetectionResult.law_id == law_id,
                RevisionDetectionResult.detection_method == method,
            )
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.needs_revision = needs_revision
            existing.detail = detail
            existing.detected_at = detected_at
            existing.updated_at = datetime.utcnow()
            return

        self.db.add(
            RevisionDetectionResult(
                ordinance_id=ordinance_id,
                law_id=law_id,
                detection_method=method,
                needs_revision=needs_revision,
                detail=detail,
                detected_at=detected_at,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

    async def _get_or_fetch_revision_reason(self, law: Law) -> LawRevisionReason:
        stmt = select(LawRevisionReason).where(LawRevisionReason.law_id == law.id)
        cached = (await self.db.execute(stmt)).scalar_one_or_none()
        if cached:
            return cached

        owns_client = False
        client = self.moleg_client
        if client is None:
            client = MolegClient(
                api_key=settings.MOLEG_API_KEY or "test",
                base_url=settings.MOLEG_API_BASE_URL,
            )
            owns_client = True

        try:
            mst = law.effective_mst
            law_detail = await client.get_law_detail(mst)
        finally:
            if owns_client:
                await client.close()

        extracted_articles = parse_amendment_articles(law_detail.amendment_content or "")
        record = LawRevisionReason(
            law_id=law.id,
            law_mst=mst,
            revision_reason=law_detail.revision_reason,
            amendment_content=law_detail.amendment_content,
            extracted_articles={"articles": extracted_articles},
            fetched_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(record)
        await self.db.flush()
        return record

    def _extract_articles_from_reason(self, reason: LawRevisionReason) -> List[str]:
        if reason.extracted_articles and isinstance(reason.extracted_articles, dict):
            cached = reason.extracted_articles.get("articles")
            if isinstance(cached, list) and cached:
                return [str(item) for item in cached]

        extracted = parse_amendment_articles(reason.amendment_content or "")
        reason.extracted_articles = {"articles": extracted}
        reason.updated_at = datetime.utcnow()
        return extracted

    def _aggregate_results(
        self,
        ordinance_id: int,
        ordinance_name: str,
        results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        grouped: Dict[str, List[Dict[str, Any]]] = {method: [] for method in self.DEFAULT_METHODS}
        for item in results:
            method = item.get("method")
            if method in grouped:
                grouped[method].append(item)

        aggregated: List[Dict[str, Any]] = []
        for method in self.DEFAULT_METHODS:
            method_items = grouped.get(method, [])
            if not method_items:
                continue
            detected_at = max(item["detected_at"] for item in method_items)
            aggregated.append(
                {
                    "method": method,
                    "needs_revision": any(item["needs_revision"] for item in method_items),
                    "detail": {
                        "by_law": [item["detail"] for item in method_items],
                        "law_count": len(method_items),
                    },
                    "detected_at": detected_at,
                }
            )

        return {
            "ordinance_id": ordinance_id,
            "ordinance_name": ordinance_name,
            "results": aggregated,
        }

    @staticmethod
    def _build_signature(results: List[Dict[str, Any]]) -> List[tuple]:
        signature: List[tuple] = []
        for item in results:
            signature.append((item.get("method"), bool(item.get("needs_revision"))))
        signature.sort(key=lambda value: str(value[0]))
        return signature

    @staticmethod
    def _find_changed_methods(
        old_results: List[Dict[str, Any]],
        new_results: List[Dict[str, Any]],
    ) -> List[str]:
        old_map = {item.get("method"): bool(item.get("needs_revision")) for item in old_results}
        changed: List[str] = []
        for item in new_results:
            method = item.get("method")
            value = bool(item.get("needs_revision"))
            if old_map.get(method) != value:
                changed.append(str(method))
        return changed

    @staticmethod
    def _get_ordinance_reference_date(ordinance: Ordinance) -> Optional[date]:
        return ordinance.enacted_date or ordinance.revision_date

    @staticmethod
    def _split_related_articles(value: Optional[str]) -> List[str]:
        if not value:
            return []
        return [token.strip() for token in re.split(r"[,\n/]+", value) if token.strip()]

    @staticmethod
    def _normalize_article_no(value: str) -> str:
        if not value:
            return ""
        matched = re.search(r"제(\d+조(?:의\d+)?)", str(value))
        if not matched:
            return ""
        return f"제{matched.group(1)}"

    @staticmethod
    def _article_sort_key(article_no: str) -> tuple:
        matched = re.match(r"^제(\d+)조(?:의(\d+))?$", article_no)
        if not matched:
            return (10**9, 10**9, article_no)
        main_no = int(matched.group(1))
        sub_no = int(matched.group(2)) if matched.group(2) else 0
        return (main_no, sub_no, article_no)
