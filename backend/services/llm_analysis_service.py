"""
AI 통합 분석 서비스 - LLM 기반 개정내용 요약 + 검토의견 초안 생성
Constitution VIII: 1회 실행 원칙, AI 입출력 보존
"""
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.config import settings
from backend.models.law import Law
from backend.models.ordinance import Ordinance
from backend.models.ordinance_law_mapping import OrdinanceLawMapping
from backend.models.ordinance_text import OrdinanceText
from backend.models.llm_analysis_result import LlmAnalysisResult
from backend.models.llm_provider import LlmProvider
from backend.models.ordinance_review import OrdinanceReview
from backend.services.llm_client import get_active_llm_client, LlmServiceUnavailableError
from backend.services.llm_rate_limiter import check_rate_limit, RateLimitExceededError

logger = logging.getLogger(__name__)

# 프롬프트 YAML 로드
_PROMPTS_PATH = Path(__file__).parent.parent / "config" / "prompts.yaml"
_prompts_cache: Optional[dict] = None


def _load_prompts() -> dict:
    """프롬프트 YAML 파일 로드 (캐시)"""
    global _prompts_cache
    if _prompts_cache is None:
        with open(_PROMPTS_PATH, "r", encoding="utf-8") as f:
            _prompts_cache = yaml.safe_load(f)
    return _prompts_cache


def compute_input_hash(
    revision_reason: str, amendment_content: str, ordinance_name: str,
    ordinance_text: str = ""
) -> str:
    """입력 데이터만 해시 (프롬프트 제외)"""
    input_data = f"{revision_reason or ''}\n{amendment_content or ''}\n{ordinance_name or ''}\n{ordinance_text or ''}"
    return hashlib.sha256(input_data.encode("utf-8")).hexdigest()


class LlmAnalysisService:
    """AI 통합 분석 비즈니스 로직"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_ordinance(
        self, ordinance_id: int, law_id: int
    ) -> LlmAnalysisResult:
        """
        메인 진입점: 1회 통합 호출로 요약 + 검토의견 초안을 동시 생성

        Raises:
            ValueError: 조례/법령 미발견, 매핑 미존재, 제개정이유 없음
            ConflictError: 이미 분석 완료
            LlmServiceUnavailableError: 프로바이더 미설정
            RateLimitExceededError: Rate Limit 초과
        """
        # 1. 조례 조회
        ordinance = await self._get_ordinance(ordinance_id)
        if not ordinance:
            raise ValueError("조례를 찾을 수 없습니다")

        # 2. 법령 조회
        law = await self._get_law(law_id)
        if not law:
            raise ValueError("법령을 찾을 수 없습니다")

        # 3. 매핑 확인
        mapping = await self._get_mapping(ordinance_id, law_id)
        if not mapping:
            raise ValueError("해당 법령과 조례의 연결 정보를 찾을 수 없습니다")

        # 4. 1회 실행 검증 (UNIQUE + status 확인)
        existing = await self._get_existing_result(
            ordinance_id, law_id, law.proclaimed_date
        )
        if existing and existing.status == "success":
            raise ConflictError("이미 AI 분석이 완료되었습니다", existing.id)
        # 실패 건은 1회 재시도 허용 — 기존 레코드 삭제 후 재생성
        if existing and existing.status == "failed":
            await self.db.delete(existing)
            await self.db.flush()

        # 5. 입력 데이터 수집 (제개정이유 + 개정문)
        # 005 미구현 시 → revision_reason, amendment_content가 없을 수 있음
        revision_reason = await self._get_revision_reason(law_id)
        amendment_content = await self._get_amendment_content(law_id)
        if not revision_reason and not amendment_content:
            raise ValueError("제개정이유 데이터가 없어 AI 분석을 수행할 수 없습니다")

        # 5-1. 조례 전문 조회 (DB 캐시 or API fetch)
        ordinance_text_str = await self._get_or_fetch_ordinance_text(ordinance)

        # 6. input_hash 계산
        input_hash = compute_input_hash(
            revision_reason or "", amendment_content or "", ordinance.name,
            ordinance_text_str or ""
        )

        # 7. 활성 LLM 클라이언트 가져오기
        try:
            client, provider = await get_active_llm_client(self.db)
        except LlmServiceUnavailableError:
            raise

        # 8. Rate Limit 검사
        try:
            await check_rate_limit(provider.rate_limit_per_minute)
        except RateLimitExceededError:
            raise

        # 9. 프롬프트 렌더링
        prompts = _load_prompts()
        token_limit = prompts.get("token_limit", {}).get("max_input_chars", 50000)

        # 토큰 초과 검사 → 2단계 처리
        combined_input = f"{revision_reason or ''}{amendment_content or ''}{ordinance_text_str or ''}"
        if len(combined_input) > token_limit:
            revision_reason, amendment_content, ordinance_text_str = await self._summarize_long_input(
                client, prompts, revision_reason, amendment_content, ordinance_text_str
            )

        system_prompt = prompts["unified_analysis"]["system_prompt"]
        user_prompt = prompts["unified_analysis"]["user_prompt"].format(
            law_name=law.law_name,
            law_proclaimed_date=str(law.proclaimed_date or ""),
            revision_reason=revision_reason or "(제개정이유 없음)",
            amendment_content=amendment_content or "(개정문 없음)",
            ordinance_name=ordinance.name,
            ordinance_text=ordinance_text_str or "(조례 전문 없음)",
        )

        # 10. pending 레코드 생성
        result = LlmAnalysisResult(
            ordinance_id=ordinance_id,
            law_id=law_id,
            law_proclaimed_date=law.proclaimed_date,
            status="pending",
            input_hash=input_hash,
            prompt_text=f"[system]\n{system_prompt}\n[user]\n{user_prompt}",
            provider_name=provider.provider_name,
            model_name=provider.model_name,
        )
        self.db.add(result)
        await self.db.flush()

        # 11. LLM 호출
        try:
            llm_response = await client.generate_with_retry(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_retries=settings.LLM_MAX_RETRIES,
            )

            # JSON 파싱
            parsed = json.loads(llm_response.content)
            summary = parsed.get("summary", {})
            review_draft = parsed.get("review_draft", {})

            # 요약 텍스트 구성
            main_changes = summary.get("main_changes", [])
            affected_articles = summary.get("affected_articles", [])
            ordinance_impact = summary.get("ordinance_impact", "")
            summary_text = ""
            if main_changes:
                summary_text += "### 주요 변경사항\n"
                for change in main_changes:
                    summary_text += f"- {change}\n"
            if affected_articles:
                summary_text += "\n### 변경 조문\n"
                for article in affected_articles:
                    summary_text += f"- {article}\n"
            if ordinance_impact:
                summary_text += f"\n### 조례 영향\n{ordinance_impact}\n"

            # 개정 필요 조례 조문별 분석 결과
            affected_ordinance_articles = parsed.get("affected_ordinance_articles", [])

            # 결과 업데이트
            result.status = "success"
            result.summary_text = summary_text.strip()
            result.review_draft_text = review_draft.get("content", "")
            result.review_draft_result = review_draft.get("result", "")
            result.affected_articles_json = affected_ordinance_articles if affected_ordinance_articles else None
            result.token_usage = {
                "input_tokens": llm_response.input_tokens,
                "output_tokens": llm_response.output_tokens,
            }

        except json.JSONDecodeError as e:
            result.status = "failed"
            result.error_message = f"LLM 응답 JSON 파싱 실패: {str(e)}"
            logger.error(f"AI 분석 JSON 파싱 실패 (ord={ordinance_id}, law={law_id}): {e}")

        except Exception as e:
            result.status = "failed"
            result.error_message = f"AI 분석 실패: {str(e)}"
            logger.error(f"AI 분석 실패 (ord={ordinance_id}, law={law_id}): {e}")

        await self.db.flush()
        return result

    async def get_analysis_results(
        self, ordinance_id: int, law_id: Optional[int] = None
    ) -> list[LlmAnalysisResult]:
        """분석 결과 조회 (법령별)"""
        query = select(LlmAnalysisResult).where(
            LlmAnalysisResult.ordinance_id == ordinance_id
        )
        if law_id:
            query = query.where(LlmAnalysisResult.law_id == law_id)
        query = query.order_by(LlmAnalysisResult.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_ai_analytics(
        self, start_date, end_date
    ) -> dict:
        """AI 분석 이력 통계"""
        from datetime import datetime

        # 총 분석 수 (기간 내)
        base_query = select(LlmAnalysisResult).where(
            LlmAnalysisResult.created_at >= start_date,
            LlmAnalysisResult.created_at <= end_date,
        )
        all_results = await self.db.execute(base_query)
        analyses = list(all_results.scalars().all())

        total = len(analyses)
        success = sum(1 for a in analyses if a.status == "success")
        failed = sum(1 for a in analyses if a.status == "failed")

        # 프로바이더별 통계
        by_provider = {}
        for a in analyses:
            if a.provider_name not in by_provider:
                by_provider[a.provider_name] = {"count": 0, "model": a.model_name}
            by_provider[a.provider_name]["count"] += 1

        # 채택률 계산 (기간 내 검토의견 중 AI 관련)
        review_query = select(OrdinanceReview).where(
            OrdinanceReview.created_at >= start_date,
            OrdinanceReview.created_at <= end_date,
        )
        review_result = await self.db.execute(review_query)
        reviews = list(review_result.scalars().all())

        ai_reviews = [r for r in reviews if r.is_ai_generated]
        ai_adopted = sum(1 for r in ai_reviews if not r.ai_modified)
        ai_modified = sum(1 for r in ai_reviews if r.ai_modified)
        ai_unused = max(0, success - len(ai_reviews))

        total_ai_related = ai_adopted + ai_modified + ai_unused
        adoption_rate = ai_adopted / total_ai_related if total_ai_related > 0 else 0
        modified_rate = ai_modified / total_ai_related if total_ai_related > 0 else 0
        unused_rate = ai_unused / total_ai_related if total_ai_related > 0 else 0

        # 평균 토큰 사용량
        token_analyses = [a for a in analyses if a.token_usage]
        avg_tokens = None
        if token_analyses:
            avg_input = sum(a.token_usage.get("input_tokens", 0) for a in token_analyses) / len(token_analyses)
            avg_output = sum(a.token_usage.get("output_tokens", 0) for a in token_analyses) / len(token_analyses)
            avg_tokens = {
                "input_tokens": round(avg_input),
                "output_tokens": round(avg_output),
            }

        return {
            "period": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
            },
            "total_analyses": total,
            "success_count": success,
            "failed_count": failed,
            "draft_adoption_rate": round(adoption_rate, 2),
            "draft_modified_rate": round(modified_rate, 2),
            "draft_unused_rate": round(unused_rate, 2),
            "average_token_usage": avg_tokens,
            "by_provider": by_provider,
        }

    # === Private helpers ===

    async def _get_ordinance(self, ordinance_id: int) -> Optional[Ordinance]:
        result = await self.db.execute(
            select(Ordinance).where(Ordinance.id == ordinance_id)
        )
        return result.scalar_one_or_none()

    async def _get_law(self, law_id: int) -> Optional[Law]:
        result = await self.db.execute(
            select(Law).where(Law.id == law_id)
        )
        return result.scalar_one_or_none()

    async def _get_mapping(
        self, ordinance_id: int, law_id: int
    ) -> Optional[OrdinanceLawMapping]:
        result = await self.db.execute(
            select(OrdinanceLawMapping).where(
                OrdinanceLawMapping.ordinance_id == ordinance_id,
                OrdinanceLawMapping.law_id == law_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_existing_result(
        self, ordinance_id: int, law_id: int, proclaimed_date
    ) -> Optional[LlmAnalysisResult]:
        result = await self.db.execute(
            select(LlmAnalysisResult).where(
                LlmAnalysisResult.ordinance_id == ordinance_id,
                LlmAnalysisResult.law_id == law_id,
                LlmAnalysisResult.law_proclaimed_date == proclaimed_date,
            )
        )
        return result.scalar_one_or_none()

    async def _get_revision_reason(self, law_id: int) -> Optional[str]:
        """법령의 제개정이유 조회 (005 LawRevisionReason 테이블 참조)"""
        # 005 미구현 시 테이블이 없을 수 있음 → 안전하게 처리
        try:
            from sqlalchemy import text
            result = await self.db.execute(
                text("SELECT revision_reason FROM law_revision_reasons WHERE law_id = :law_id"),
                {"law_id": law_id},
            )
            row = result.first()
            return row[0] if row else None
        except Exception:
            # 테이블 미존재 시
            return None

    async def _get_amendment_content(self, law_id: int) -> Optional[str]:
        """법령의 개정문 내용 조회 (005 LawRevisionReason 테이블 참조)"""
        try:
            from sqlalchemy import text
            result = await self.db.execute(
                text("SELECT amendment_content FROM law_revision_reasons WHERE law_id = :law_id"),
                {"law_id": law_id},
            )
            row = result.first()
            return row[0] if row else None
        except Exception:
            return None

    async def _get_or_fetch_ordinance_text(self, ordinance: Ordinance) -> Optional[str]:
        """조례 전문 조회 — DB 캐시 확인 → 없으면 법제처 API fetch → 저장"""
        # DB 캐시 확인
        result = await self.db.execute(
            select(OrdinanceText).where(OrdinanceText.ordinance_id == ordinance.id)
        )
        cached = result.scalar_one_or_none()
        if cached and cached.full_text:
            return cached.full_text

        # serial_no 없으면 API 호출 불가
        if not ordinance.serial_no:
            logger.warning("조례 serial_no 없음, 조례 전문 fetch 불가 (ordinance_id=%d)", ordinance.id)
            return None

        # 법제처 API에서 조례 전문 조회
        try:
            from backend.external.moleg_client import MolegClient
            moleg = MolegClient(api_key=settings.MOLEG_API_KEY)
            try:
                detail = await moleg.get_ordinance_detail(ordinance.serial_no)
            finally:
                await moleg.close()

            # 조문 텍스트 직렬화
            full_text = self._build_full_text(detail.articles)
            articles_json = [
                {
                    "article_no": a.article_no,
                    "article_title": a.article_title,
                    "article_content": a.article_content,
                }
                for a in detail.articles
            ]

            # DB에 저장 (기존 레코드 있으면 업데이트)
            if cached:
                cached.full_text = full_text
                cached.articles_json = articles_json
                cached.fetched_at = datetime.utcnow()
            else:
                new_text = OrdinanceText(
                    ordinance_id=ordinance.id,
                    serial_no=ordinance.serial_no,
                    full_text=full_text,
                    articles_json=articles_json,
                    fetched_at=datetime.utcnow(),
                )
                self.db.add(new_text)
            await self.db.flush()

            return full_text

        except Exception as e:
            logger.warning("조례 전문 fetch 실패 (ordinance_id=%d): %s", ordinance.id, e)
            return None

    def _build_full_text(self, articles) -> str:
        """조문 리스트를 텍스트로 직렬화"""
        lines = []
        for art in articles:
            header = art.article_no
            if art.article_title:
                header += f"({art.article_title})"
            lines.append(header)
            if art.article_content:
                lines.append(art.article_content)
            lines.append("")  # 빈 줄 구분
        return "\n".join(lines).strip()

    async def _summarize_long_input(
        self, client, prompts: dict, revision_reason: str, amendment_content: str,
        ordinance_text: str = ""
    ) -> tuple[str, str, str]:
        """토큰 초과 시 1차 요약 LLM 호출 (2단계 처리)"""
        summarize_prompts = prompts.get("summarize_long_text", {})
        system_prompt = summarize_prompts.get("system_prompt", "법령 텍스트를 요약해 주세요.")
        user_prompt_template = summarize_prompts.get("user_prompt", "{text}")

        summarized_reason = revision_reason
        summarized_content = amendment_content
        summarized_ordinance = ordinance_text

        # 제개정이유 요약
        if revision_reason and len(revision_reason) > 15000:
            try:
                resp = await client.generate(
                    prompt=user_prompt_template.format(text=revision_reason),
                    system_prompt=system_prompt,
                )
                summarized_reason = resp.content
            except Exception as e:
                logger.warning(f"제개정이유 요약 실패, 원본 사용: {e}")

        # 개정문 요약
        if amendment_content and len(amendment_content) > 15000:
            try:
                resp = await client.generate(
                    prompt=user_prompt_template.format(text=amendment_content),
                    system_prompt=system_prompt,
                )
                summarized_content = resp.content
            except Exception as e:
                logger.warning(f"개정문 요약 실패, 원본 사용: {e}")

        # 조례 전문 요약
        if ordinance_text and len(ordinance_text) > 15000:
            try:
                resp = await client.generate(
                    prompt=user_prompt_template.format(text=ordinance_text),
                    system_prompt=system_prompt,
                )
                summarized_ordinance = resp.content
            except Exception as e:
                logger.warning(f"조례 전문 요약 실패, 원본 사용: {e}")

        return summarized_reason, summarized_content, summarized_ordinance


class ConflictError(Exception):
    """이미 처리 완료된 건에 대한 중복 요청"""
    def __init__(self, message: str, existing_result_id: int):
        super().__init__(message)
        self.existing_result_id = existing_result_id
