"""
Article Service - 조문 관리 및 변경 감지 서비스

법제처 API로부터 조문 정보를 조회하고, 변경 사항을 자동으로 감지하여
관련 조례의 개정 필요 여부를 판단합니다.
"""
import hashlib
import difflib
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from backend.models.article import Article
from backend.models.article_change import ArticleChange
from backend.models.ordinance_article_mapping import OrdinanceArticleMapping
from backend.models.law import Law
from backend.models.ordinance import Ordinance
from backend.external.moleg_client import MolegClient, LawArticle
from backend.schemas.article import (
    ArticleCreate,
    ArticleResponse,
    ArticleListResponse,
    ArticleListParams,
)


class ArticleService:
    """조문 관리 서비스"""

    def __init__(self, db: AsyncSession, moleg_client: Optional[MolegClient] = None):
        self.db = db
        self.moleg_client = moleg_client

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    async def get_articles(
        self,
        params: ArticleListParams,
    ) -> ArticleListResponse:
        """
        조문 목록 조회 (페이지네이션, 필터링)

        Args:
            params: 조회 파라미터

        Returns:
            페이지네이션된 조문 목록
        """
        # Base query
        query = select(Article).options(
            joinedload(Article.law)
        )

        # Filters
        conditions = []
        if params.law_id:
            conditions.append(Article.law_id == params.law_id)

        if params.search:
            search_pattern = f"%{params.search}%"
            conditions.append(
                or_(
                    Article.article_no.ilike(search_pattern),
                    Article.article_title.ilike(search_pattern),
                )
            )

        if params.changed_since:
            # 특정 일자 이후 변경된 조문만 조회
            subq = (
                select(ArticleChange.article_id)
                .where(ArticleChange.change_date >= params.changed_since)
                .distinct()
            )
            conditions.append(Article.id.in_(subq))

        if conditions:
            query = query.where(and_(*conditions))

        # Total count
        count_query = select(func.count()).select_from(Article)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query) or 0

        # Pagination
        query = query.offset((params.page - 1) * params.size).limit(params.size)

        # Execute
        result = await self.db.execute(query)
        articles = result.scalars().all()

        # N+1 쿼리 최적화: 단일 쿼리로 연계 조례 개수 조회
        article_ids = [article.id for article in articles]

        # Subquery for ordinance counts
        ordinance_counts_query = (
            select(
                OrdinanceArticleMapping.article_id,
                func.count().label('ordinance_count')
            )
            .where(OrdinanceArticleMapping.article_id.in_(article_ids))
            .group_by(OrdinanceArticleMapping.article_id)
        )
        ordinance_counts_result = await self.db.execute(ordinance_counts_query)
        ordinance_counts = {row.article_id: row.ordinance_count for row in ordinance_counts_result}

        # Subquery for change counts and last change date
        change_stats_query = (
            select(
                ArticleChange.article_id,
                func.count().label('change_count'),
                func.max(ArticleChange.change_date).label('last_change_date')
            )
            .where(ArticleChange.article_id.in_(article_ids))
            .group_by(ArticleChange.article_id)
        )
        change_stats_result = await self.db.execute(change_stats_query)
        change_stats = {
            row.article_id: {
                'change_count': row.change_count,
                'last_change_date': row.last_change_date
            }
            for row in change_stats_result
        }

        # Build response items
        items = []
        for article in articles:
            ordinance_count = ordinance_counts.get(article.id, 0)
            stats = change_stats.get(article.id, {'change_count': 0, 'last_change_date': None})
            change_count = stats['change_count']
            last_change = stats['last_change_date']

            # 30일 이내 변경 여부
            has_recent_change = False
            if last_change:
                has_recent_change = (datetime.now().date() - last_change).days <= 30

            article_dict = ArticleResponse.model_validate(article).model_dump()
            article_dict['law_name'] = article.law.law_name if article.law else None
            article_dict['law_type'] = article.law.law_type if article.law else None
            article_dict['ordinance_count'] = ordinance_count
            article_dict['change_count'] = change_count
            article_dict['last_changed_date'] = last_change
            article_dict['has_recent_change'] = has_recent_change

            items.append(ArticleResponse(**article_dict))

        pages = (total + params.size - 1) // params.size

        return ArticleListResponse(
            items=items,
            total=total,
            page=params.page,
            size=params.size,
            pages=pages,
        )

    async def get_article_by_id(self, article_id: int) -> Optional[Article]:
        """
        조문 ID로 조회

        Args:
            article_id: 조문 ID

        Returns:
            조문 객체 또는 None
        """
        query = select(Article).options(
            joinedload(Article.law)
        ).where(Article.id == article_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_article(self, article_data: ArticleCreate) -> Article:
        """
        조문 생성

        Args:
            article_data: 조문 생성 데이터

        Returns:
            생성된 조문 객체
        """
        article = Article(
            law_id=article_data.law_id,
            article_no=article_data.article_no,
            article_title=article_data.article_title,
            article_content=article_data.article_content,
            paragraphs=article_data.paragraphs,
            content_hash=article_data.content_hash,
            mst_seq=article_data.mst_seq,
            jo_seq=article_data.jo_seq,
            last_synced_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(article)
        await self.db.commit()
        await self.db.refresh(article)

        return article

    async def get_articles_by_law_id(self, law_id: int) -> List[Article]:
        """
        특정 법령의 조문 목록 조회

        Args:
            law_id: 법령 ID

        Returns:
            조문 목록
        """
        query = select(Article).where(Article.law_id == law_id).order_by(Article.article_no)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_article_changes(self, article_id: int) -> List[ArticleChange]:
        """
        조문 변경 이력 조회

        Args:
            article_id: 조문 ID

        Returns:
            변경 이력 목록
        """
        query = (
            select(ArticleChange)
            .where(ArticleChange.article_id == article_id)
            .order_by(ArticleChange.change_date.desc())
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    # =========================================================================
    # Sync & Change Detection
    # =========================================================================

    async def sync_articles_for_law(
        self,
        law_id: int,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        특정 법령의 조문 동기화 및 변경 감지

        Args:
            law_id: 법령 ID
            force: 강제 동기화 여부

        Returns:
            동기화 결과
        """
        if not self.moleg_client:
            raise ValueError("MolegClient가 설정되지 않았습니다.")

        # 법령 조회
        law = await self.db.get(Law, law_id)
        if not law:
            raise ValueError(f"법령을 찾을 수 없습니다: {law_id}")

        # 법제처 API에서 조문 조회
        law_detail = await self.moleg_client.get_law_detail(str(law.law_serial_no))
        if not law_detail.articles:
            # 일부 레코드는 오래된 법령일련번호(MST)를 가지고 있어 조문 조회가 0건일 수 있음.
            # 법령명으로 최신 식별자를 재조회해 보정 후 한 번 더 조회한다.
            search_results = await self.moleg_client.get_law_list(query=law.law_name, page=1)
            if isinstance(search_results, dict):
                search_results = [search_results]
            exact_match = next(
                (
                    item for item in search_results
                    if item.get("법령명한글") == law.law_name
                    and (not law.law_type or item.get("법령구분명") == law.law_type)
                ),
                None,
            ) or next(
                (item for item in search_results if item.get("법령명한글") == law.law_name),
                None,
            )

            if exact_match:
                serial_no = int(str(exact_match.get("법령일련번호", "0")) or "0")
                law_code = int(str(exact_match.get("법령ID", "0")).lstrip("0") or "0")
                if serial_no > 0:
                    law.law_serial_no = serial_no
                if law_code > 0:
                    law.law_id = law_code
                if exact_match.get("법령구분명"):
                    law.law_type = exact_match.get("법령구분명")

                law_detail = await self.moleg_client.get_law_detail(str(law.law_serial_no))

        # 변경 감지
        result = await self.detect_article_changes(
            law_id=law_id,
            api_articles=law_detail.articles,
            proclaimed_date=law.proclaimed_date,
        )

        # law.last_synced_at 업데이트
        law.last_synced_at = datetime.utcnow()
        await self.db.commit()

        return {
            "success": True,
            "law_id": law_id,
            "law_name": law.law_name,
            "synced_articles": len(law_detail.articles),
            "created": len(result["created"]),
            "updated": len(result["updated"]),
            "deleted": len(result["deleted"]),
            "changes_detected": len(result["updated"]),
        }

    async def detect_article_changes(
        self,
        law_id: int,
        api_articles: List[LawArticle],
        proclaimed_date: Optional[date] = None,
    ) -> Dict[str, List[Any]]:
        """
        조문 변경 감지 알고리즘

        Args:
            law_id: 법령 ID
            api_articles: 법제처 API 응답 조문 목록
            proclaimed_date: 법령 공포일자

        Returns:
            {
                "created": [신규 조문 목록],
                "updated": [(조문, 이전 내용, 이전 해시)],
                "deleted": [삭제된 조문 목록]
            }
        """
        # 1. DB에서 기존 조문 조회
        db_articles = await self.get_articles_by_law_id(law_id)
        db_article_map = {art.article_no: art for art in db_articles}

        # 2. API 조문 처리
        api_article_map = {}
        for api_art in api_articles:
            content_hash = self.generate_content_hash(api_art.article_content)

            api_article_map[api_art.article_no] = {
                "no": api_art.article_no,
                "title": api_art.article_title,
                "content": api_art.article_content,
                "hash": content_hash,
                "paragraphs": api_art.paragraphs,
            }

        # 3. 비교 결과 초기화
        result = {
            "created": [],
            "updated": [],
            "deleted": [],
        }

        # 4. 신규 및 변경 조문 감지
        for article_no, api_data in api_article_map.items():
            if article_no not in db_article_map:
                # 4.1 신규 조문
                new_article = await self.create_article(
                    ArticleCreate(
                        law_id=law_id,
                        article_no=article_no,
                        article_title=api_data["title"],
                        article_content=api_data["content"],
                        paragraphs={"paragraphs": api_data["paragraphs"]},
                        content_hash=api_data["hash"],
                    )
                )
                result["created"].append(new_article)

                # 변경 이력 생성 (신규)
                await self.create_article_change(
                    article_id=new_article.id,
                    change_type="created",
                    new_content=api_data["content"],
                    new_hash=api_data["hash"],
                    change_date=proclaimed_date or datetime.utcnow().date(),
                )

            else:
                # 4.2 기존 조문 - 해시 비교
                db_article = db_article_map[article_no]

                if db_article.content_hash != api_data["hash"]:
                    # 변경 감지!
                    old_hash = db_article.content_hash
                    old_content = db_article.article_content

                    # 조문 업데이트
                    db_article.article_content = api_data["content"]
                    db_article.article_title = api_data["title"]
                    db_article.paragraphs = {"paragraphs": api_data["paragraphs"]}
                    db_article.content_hash = api_data["hash"]
                    db_article.last_synced_at = datetime.utcnow()
                    db_article.updated_at = datetime.utcnow()

                    result["updated"].append((db_article, old_content, old_hash))

                    # 변경 이력 생성
                    await self.create_article_change(
                        article_id=db_article.id,
                        change_type="updated",
                        old_content=old_content,
                        new_content=api_data["content"],
                        old_hash=old_hash,
                        new_hash=api_data["hash"],
                        change_date=proclaimed_date or datetime.utcnow().date(),
                    )

                    # 연계된 조례의 needs_revision 업데이트
                    await self.notify_affected_ordinances(db_article.id)

        # 5. 삭제된 조문 감지
        for article_no, db_article in db_article_map.items():
            if article_no not in api_article_map:
                result["deleted"].append(db_article)

                # 변경 이력 생성 (삭제)
                await self.create_article_change(
                    article_id=db_article.id,
                    change_type="deleted",
                    old_content=db_article.article_content,
                    old_hash=db_article.content_hash,
                    change_date=proclaimed_date or datetime.utcnow().date(),
                )

                # 조문 삭제 (CASCADE로 관련 데이터도 삭제됨)
                await self.db.delete(db_article)

        await self.db.commit()

        return result

    async def create_article_change(
        self,
        article_id: int,
        change_type: str,
        change_date: date,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
        old_hash: Optional[str] = None,
        new_hash: Optional[str] = None,
    ) -> ArticleChange:
        """
        조문 변경 이력 레코드 생성

        Args:
            article_id: 조문 ID
            change_type: 변경 유형 ('created', 'updated', 'deleted')
            change_date: 변경 일자
            old_content: 이전 내용
            new_content: 새 내용
            old_hash: 이전 해시
            new_hash: 새 해시

        Returns:
            생성된 변경 이력 객체
        """
        # Diff HTML 생성
        diff_html = None
        if old_content and new_content:
            diff_html = self.generate_diff_html(old_content, new_content)

        change = ArticleChange(
            article_id=article_id,
            change_date=change_date,
            change_type=change_type,
            old_content=old_content,
            new_content=new_content,
            old_hash=old_hash,
            new_hash=new_hash,
            diff_html=diff_html,
            detected_at=datetime.utcnow(),
            notified=False,
            created_at=datetime.utcnow(),
        )

        self.db.add(change)
        # Commit은 호출자에서 처리

        return change

    async def notify_affected_ordinances(self, article_id: int):
        """
        변경된 조문과 연계된 조례들의 needs_revision 플래그 업데이트

        Args:
            article_id: 변경된 조문 ID
        """
        # 1. 연계된 조례 조회
        query = (
            select(Ordinance)
            .join(OrdinanceArticleMapping)
            .where(OrdinanceArticleMapping.article_id == article_id)
        )

        result = await self.db.execute(query)
        ordinances = result.scalars().all()

        # 2. needs_revision 업데이트
        for ordinance in ordinances:
            ordinance.needs_revision = True

        # Commit은 호출자에서 처리

    # =========================================================================
    # Utility Functions
    # =========================================================================

    @staticmethod
    def generate_content_hash(content: str) -> str:
        """
        조문 내용의 SHA-256 해시 생성

        Args:
            content: 조문 내용 텍스트

        Returns:
            64자 hex 문자열
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_diff_html(old_content: str, new_content: str) -> str:
        """
        두 조문 내용의 차이를 HTML로 생성

        Args:
            old_content: 이전 내용
            new_content: 새 내용

        Returns:
            HTML diff 테이블
        """
        diff = difflib.HtmlDiff(wrapcolumn=80)

        html = diff.make_table(
            old_content.splitlines(),
            new_content.splitlines(),
            fromdesc="이전 내용",
            todesc="새 내용",
            context=True,  # 변경된 부분 주변만 표시
            numlines=3,  # 컨텍스트 라인 수
        )

        return html
