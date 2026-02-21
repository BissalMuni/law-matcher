"""
Articles API endpoints - 조문 조회 및 변경 감지
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.deps import get_db, get_current_user
from backend.models.user import User
from backend.models.article import Article
from backend.models.ordinance_article_mapping import OrdinanceArticleMapping
from backend.services.article_service import ArticleService
from backend.external.moleg_client import MolegClient
from backend.core.config import settings
from backend.schemas.article import (
    ArticleResponse,
    ArticleDetailResponse,
    ArticleListResponse,
    ArticleListParams,
    OrdinanceArticleMappingCreate,
    OrdinanceArticleMappingResponse,
    OrdinanceArticleMappingListResponse,
    ArticleChangeResponse,
    ArticleChangeListResponse,
    ArticleSyncRequest,
    ArticleSyncResponse,
    BulkMappingRequest,
    BulkMappingResponse,
    RevisionNeededOrdinanceItem,
    RevisionNeededOrdinanceListResponse,
    AutoMappingRecommendation,
    AutoMappingRecommendationResponse,
)

router = APIRouter()


async def get_moleg_client() -> MolegClient:
    """MolegClient 의존성 주입"""
    return MolegClient(api_key=settings.MOLEG_API_KEY)


async def get_article_service(
    db: AsyncSession = Depends(get_db),
    moleg_client: MolegClient = Depends(get_moleg_client),
) -> ArticleService:
    """ArticleService 의존성 주입"""
    return ArticleService(db=db, moleg_client=moleg_client)


# =============================================================================
# Article CRUD Endpoints
# =============================================================================

@router.get("", response_model=ArticleListResponse)
async def get_articles(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    law_id: Optional[int] = None,
    search: Optional[str] = None,
    has_ordinance: Optional[bool] = None,
    changed_since: Optional[str] = None,  # YYYY-MM-DD format
    current_user: User = Depends(get_current_user),
    service: ArticleService = Depends(get_article_service),
):
    """
    조문 목록 조회 (페이지네이션, 필터링)

    - **page**: 페이지 번호 (default: 1)
    - **size**: 페이지 크기 (default: 20, max: 100)
    - **law_id**: 법령 ID 필터 (optional)
    - **search**: 조문번호 또는 제목 검색 (optional)
    - **has_ordinance**: 연계 조례 존재 여부 (optional)
    - **changed_since**: 특정 일자 이후 변경된 조문 (YYYY-MM-DD, optional)
    """
    from datetime import datetime

    params = ArticleListParams(
        page=page,
        size=size,
        law_id=law_id,
        search=search,
        has_ordinance=has_ordinance,
        changed_since=datetime.strptime(changed_since, "%Y-%m-%d").date() if changed_since else None,
    )

    return await service.get_articles(params)


@router.get("/{article_id:int}", response_model=ArticleDetailResponse)
async def get_article_detail(
    article_id: int,
    current_user: User = Depends(get_current_user),
    service: ArticleService = Depends(get_article_service),
):
    """
    조문 상세 조회

    - **article_id**: 조문 ID
    """
    article = await service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "조문을 찾을 수 없습니다."},
        )

    # 연계 조례 개수 등 추가 정보 조회
    db = service.db

    from sqlalchemy import select, func

    ordinance_count = await db.scalar(
        select(func.count())
        .select_from(OrdinanceArticleMapping)
        .where(OrdinanceArticleMapping.article_id == article_id)
    ) or 0

    from backend.models.article_change import ArticleChange

    change_count = await db.scalar(
        select(func.count())
        .select_from(ArticleChange)
        .where(ArticleChange.article_id == article_id)
    ) or 0

    last_change = await db.scalar(
        select(ArticleChange.change_date)
        .where(ArticleChange.article_id == article_id)
        .order_by(ArticleChange.change_date.desc())
        .limit(1)
    )

    from datetime import datetime

    has_recent_change = False
    if last_change:
        has_recent_change = (datetime.now().date() - last_change).days <= 30

    article_dict = ArticleDetailResponse.model_validate(article).model_dump()
    article_dict["law_name"] = article.law.law_name if article.law else None
    article_dict["law_type"] = article.law.law_type if article.law else None
    article_dict["ordinance_count"] = ordinance_count
    article_dict["change_count"] = change_count
    article_dict["last_changed_date"] = last_change
    article_dict["has_recent_change"] = has_recent_change

    return ArticleDetailResponse(**article_dict)


# =============================================================================
# Article-Ordinance Mapping Endpoints
# =============================================================================

@router.get("/{article_id:int}/ordinances", response_model=OrdinanceArticleMappingListResponse)
async def get_article_ordinances(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    조문과 연계된 조례 목록 조회

    - **article_id**: 조문 ID
    """
    from sqlalchemy import select
    from backend.models.ordinance import Ordinance

    query = (
        select(OrdinanceArticleMapping)
        .options(
            selectinload(OrdinanceArticleMapping.ordinance),
            selectinload(OrdinanceArticleMapping.article),
            selectinload(OrdinanceArticleMapping.creator),
        )
        .where(OrdinanceArticleMapping.article_id == article_id)
    )

    result = await db.execute(query)
    mappings = result.scalars().all()

    items = []
    for mapping in mappings:
        mapping_dict = OrdinanceArticleMappingResponse.model_validate(mapping).model_dump()
        if mapping.ordinance:
            mapping_dict["ordinance_name"] = mapping.ordinance.name
            mapping_dict["category"] = mapping.ordinance.category
            mapping_dict["department"] = mapping.ordinance.department
        if mapping.article:
            mapping_dict["article_no"] = mapping.article.article_no
            mapping_dict["article_title"] = mapping.article.article_title

        items.append(OrdinanceArticleMappingResponse(**mapping_dict))

    return OrdinanceArticleMappingListResponse(
        items=items,
        total=len(items),
    )


@router.post("/{article_id:int}/mappings", response_model=OrdinanceArticleMappingResponse)
async def create_article_ordinance_mapping(
    article_id: int,
    request: OrdinanceArticleMappingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    조문-조례 연계 추가

    - **article_id**: 조문 ID
    - **ordinance_id**: 조례 ID
    - **mapping_reason**: 연계 사유
    - **related_article_nos**: 관련 조례 조문번호
    """
    from sqlalchemy import select
    from backend.models.ordinance_law_mapping import OrdinanceLawMapping

    # 중복 체크
    existing = await db.scalar(
        select(OrdinanceArticleMapping).where(
            OrdinanceArticleMapping.article_id == article_id,
            OrdinanceArticleMapping.ordinance_id == request.ordinance_id,
        )
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_MAPPING",
                "message": "이미 연계된 조문입니다.",
            },
        )

    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "조문을 찾을 수 없습니다."},
        )

    has_parent_law_mapping = await db.scalar(
        select(OrdinanceLawMapping.id).where(
            OrdinanceLawMapping.ordinance_id == request.ordinance_id,
            OrdinanceLawMapping.law_id == article.law_id,
        )
    )
    if not has_parent_law_mapping:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "LAW_MISMATCH",
                "message": "조례의 상위법령과 조문의 소속 법령이 일치하지 않습니다.",
            },
        )

    # 생성
    from datetime import datetime

    mapping = OrdinanceArticleMapping(
        article_id=article_id,
        ordinance_id=request.ordinance_id,
        mapping_reason=request.mapping_reason,
        related_article_nos=request.related_article_nos,
        created_by=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(mapping)
    await db.commit()
    await db.refresh(mapping, ["ordinance", "article", "creator"])

    mapping_dict = OrdinanceArticleMappingResponse.model_validate(mapping).model_dump()
    if mapping.ordinance:
        mapping_dict["ordinance_name"] = mapping.ordinance.name
        mapping_dict["category"] = mapping.ordinance.category
        mapping_dict["department"] = mapping.ordinance.department
    if mapping.article:
        mapping_dict["article_no"] = mapping.article.article_no
        mapping_dict["article_title"] = mapping.article.article_title

    return OrdinanceArticleMappingResponse(**mapping_dict)


@router.delete("/{article_id:int}/mappings/{mapping_id}")
async def delete_article_ordinance_mapping(
    article_id: int,
    mapping_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    조문-조례 연계 삭제

    - **article_id**: 조문 ID
    - **mapping_id**: 연계 ID

    권한:
    - 관리자: 모든 연계 삭제 가능
    - 일반 사용자: 본인이 생성한 연계만 삭제 가능
    """
    mapping = await db.get(OrdinanceArticleMapping, mapping_id)

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "연계를 찾을 수 없습니다."},
        )

    if mapping.article_id != article_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PARAMS", "message": "잘못된 요청입니다."},
        )

    # 권한 체크 (Admin만 모든 매핑 삭제 가능)
    is_admin = current_user.user_type in {"ADMIN", "SUPER_ADMIN"}
    if not is_admin and mapping.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "본인이 생성한 연계만 삭제할 수 있습니다.",
            },
        )

    await db.delete(mapping)
    await db.commit()

    return {"success": True, "message": "연계가 삭제되었습니다."}


# =============================================================================
# Article History Endpoints
# =============================================================================

@router.get("/{article_id:int}/history", response_model=ArticleChangeListResponse)
async def get_article_history(
    article_id: int,
    current_user: User = Depends(get_current_user),
    service: ArticleService = Depends(get_article_service),
):
    """
    조문 변경 이력 조회

    - **article_id**: 조문 ID
    """
    changes = await service.get_article_changes(article_id)

    items = [ArticleChangeResponse.model_validate(change) for change in changes]

    return ArticleChangeListResponse(
        items=items,
        total=len(items),
    )


# =============================================================================
# Sync Endpoints
# =============================================================================

@router.post("/sync", response_model=ArticleSyncResponse)
async def sync_articles(
    request: ArticleSyncRequest,
    current_user: User = Depends(get_current_user),
    service: ArticleService = Depends(get_article_service),
):
    """
    조문 동기화

    - **law_ids**: 특정 법령만 동기화 (optional, 없으면 전체)
    - **force**: 강제 동기화 여부 (default: false)
    """
    # 권한 체크: ADMIN 계정만 허용
    allowed_user_types = {"ADMIN", "SUPER_ADMIN"}
    if current_user.user_type not in allowed_user_types:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "관리자만 동기화할 수 있습니다."},
        )

    # 동기화 대상 법령 결정
    from sqlalchemy import select
    from backend.models.law import Law

    if request.law_ids:
        laws_query = select(Law).where(Law.id.in_(request.law_ids))
    else:
        laws_query = select(Law)

    result = await service.db.execute(laws_query)
    laws = result.scalars().all()

    # 동기화 실행
    total_synced = 0
    total_created = 0
    total_updated = 0
    total_deleted = 0
    total_changes = 0

    for law in laws:
        try:
            sync_result = await service.sync_articles_for_law(
                law_id=law.id,
                force=request.force,
            )
            total_synced += sync_result["synced_articles"]
            total_created += sync_result["created"]
            total_updated += sync_result["updated"]
            total_deleted += sync_result["deleted"]
            total_changes += sync_result["changes_detected"]
        except Exception as e:
            # 개별 법령 동기화 실패 시 로깅만 하고 계속 진행
            import logging

            logging.error(f"Failed to sync articles for law {law.id}: {e}")

    return ArticleSyncResponse(
        success=True,
        synced_articles=total_synced,
        created=total_created,
        updated=total_updated,
        deleted=total_deleted,
        changes_detected=total_changes,
        message=f"조문 동기화 완료: {total_synced}건 처리, {total_changes}건 변경 감지",
    )
"""
Phase 4: 추가 API 엔드포인트
- 대량 매핑 API
- 개정 검토 필요 조례 목록 API
- 자동 매핑 추천 API
"""

# =============================================================================
# Phase 4: 대량 매핑 API
# =============================================================================

@router.post("/mappings/bulk", response_model=BulkMappingResponse)
async def create_bulk_mappings(
    request: BulkMappingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    조문-조례 대량 매핑 생성

    - **mappings**: [{"article_id": 1, "ordinance_id": 2}, ...]
    - **notes**: 매핑 설명 (선택사항)
    """
    from sqlalchemy import select, and_
    from backend.models.ordinance_law_mapping import OrdinanceLawMapping

    created_count = 0
    failed_count = 0
    failed_items = []

    for mapping_data in request.mappings:
        try:
            article_id = mapping_data.get("article_id")
            ordinance_id = mapping_data.get("ordinance_id")

            if not article_id or not ordinance_id:
                failed_count += 1
                failed_items.append({
                    "data": mapping_data,
                    "error": "article_id 또는 ordinance_id가 누락되었습니다."
                })
                continue

            article = await db.get(Article, article_id)
            if not article:
                failed_count += 1
                failed_items.append({
                    "data": mapping_data,
                    "error": "조문을 찾을 수 없습니다."
                })
                continue

            has_parent_law_mapping = await db.scalar(
                select(OrdinanceLawMapping.id).where(
                    OrdinanceLawMapping.ordinance_id == ordinance_id,
                    OrdinanceLawMapping.law_id == article.law_id,
                )
            )
            if not has_parent_law_mapping:
                failed_count += 1
                failed_items.append({
                    "data": mapping_data,
                    "error": "조례의 상위법령과 조문의 소속 법령이 일치하지 않습니다."
                })
                continue

            # 중복 체크
            existing = await db.scalar(
                select(OrdinanceArticleMapping).where(
                    and_(
                        OrdinanceArticleMapping.article_id == article_id,
                        OrdinanceArticleMapping.ordinance_id == ordinance_id
                    )
                )
            )

            if existing:
                failed_count += 1
                failed_items.append({
                    "data": mapping_data,
                    "error": "이미 매핑이 존재합니다."
                })
                continue

            # 매핑 생성
            new_mapping = OrdinanceArticleMapping(
                article_id=article_id,
                ordinance_id=ordinance_id,
                mapping_reason=request.mapping_reason,
                created_by=current_user.id,
            )
            db.add(new_mapping)
            created_count += 1

        except Exception as e:
            failed_count += 1
            failed_items.append({
                "data": mapping_data,
                "error": str(e)
            })

    await db.commit()

    return BulkMappingResponse(
        success=failed_count == 0,
        created_count=created_count,
        failed_count=failed_count,
        message=f"{created_count}건 생성, {failed_count}건 실패",
        failed_items=failed_items if failed_count > 0 else None,
    )


# =============================================================================
# Phase 4: 개정 검토 필요 조례 목록 API
# =============================================================================

@router.get("/revision-needed")
async def get_revision_needed_ordinances(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    days: int = Query(30, ge=1, le=365, description="최근 N일 이내 감지된 조문 변경"),
    department: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    개정 검토 필요 조례 목록 조회

    조례의 상위법령에 입력된 related_articles를 파싱하여
    해당 조문의 변경사항만 표시합니다.

    예: "제13조" → article_no = "13"인 조문의 변경사항 표시
    예: "제64조~제68조" → article_no = "64", "65", "66", "67", "68"인 조문의 변경사항 표시

    - **days**: 최근 N일 이내 감지된 조문 변경 (기본값: 30일)
    - **department**: 담당부서 필터 (선택사항)
    """
    from backend.models.ordinance import Ordinance
    from backend.models.article_change import ArticleChange
    from backend.models.law import Law
    from backend.models.ordinance_law_mapping import OrdinanceLawMapping
    from datetime import datetime, timedelta
    import re

    def parse_article_numbers(related_articles: str) -> list:
        """
        related_articles 텍스트를 파싱하여 조문 번호 리스트 반환

        예:
        - "제13조" → ["13"]
        - "제64조~제68조" → ["64", "65", "66", "67", "68"]
        - "제13조, 제20조" → ["13", "20"]
        """
        if not related_articles:
            return []

        numbers = []

        # 범위 표현 (예: "제64조~제68조", "제10조-제15조")
        range_pattern = r'제?(\d+)조?\s*[~\-]\s*제?(\d+)조?'
        ranges = re.findall(range_pattern, related_articles)
        for start, end in ranges:
            start_num = int(start)
            end_num = int(end)
            numbers.extend([str(n) for n in range(start_num, end_num + 1)])

        # 단일 조문 (예: "제13조", "13조")
        single_pattern = r'제?(\d+)조?'
        singles = re.findall(single_pattern, related_articles)
        numbers.extend(singles)

        # 중복 제거 및 정렬
        return sorted(list(set(numbers)), key=lambda x: int(x))

    # 기준 날짜 계산
    cutoff_datetime = datetime.utcnow() - timedelta(days=days)

    from sqlalchemy import select, func, and_, or_

    # Step 1: 조례-법령 매핑 정보 가져오기 (related_articles 포함)
    olm_query = select(
        OrdinanceLawMapping.id.label("mapping_id"),
        OrdinanceLawMapping.ordinance_id,
        OrdinanceLawMapping.law_id,
        OrdinanceLawMapping.related_articles,
        Ordinance.name.label("ordinance_name"),
        Ordinance.category,
        Ordinance.department,
    ).join(Ordinance, OrdinanceLawMapping.ordinance_id == Ordinance.id)

    if department:
        olm_query = olm_query.where(Ordinance.department == department)

    olm_result = await db.execute(olm_query)
    mappings = olm_result.all()

    # Step 2: 각 매핑의 related_articles를 파싱하여 조문 번호 추출
    # {law_id: {ordinance_id: [article_numbers]}}
    law_article_map = {}
    ordinance_info = {}  # {ordinance_id: {name, category, department}}

    for mapping in mappings:
        article_numbers = parse_article_numbers(mapping.related_articles)
        if not article_numbers:
            # related_articles가 없으면 해당 법령의 모든 조문 포함
            if mapping.law_id not in law_article_map:
                law_article_map[mapping.law_id] = {}
            law_article_map[mapping.law_id][mapping.ordinance_id] = None  # None = 모든 조문
        else:
            if mapping.law_id not in law_article_map:
                law_article_map[mapping.law_id] = {}
            law_article_map[mapping.law_id][mapping.ordinance_id] = article_numbers

        ordinance_info[mapping.ordinance_id] = {
            "name": mapping.ordinance_name,
            "category": mapping.category,
            "department": mapping.department,
        }

    # Step 3: 변경된 조문 조회
    all_results = []

    for law_id, ordinance_articles in law_article_map.items():
        for ordinance_id, article_numbers in ordinance_articles.items():
            # 조문 변경사항 쿼리
            change_query = (
                select(
                    Article.id.label("article_id"),
                    Article.article_no,
                    Article.article_title,
                    Law.law_name,
                    ArticleChange.change_date,
                    ArticleChange.detected_at,
                    ArticleChange.change_type,
                    ArticleChange.diff_html,
                )
                .select_from(ArticleChange)
                .join(Article, ArticleChange.article_id == Article.id)
                .join(Law, Article.law_id == Law.id)
                .where(
                    and_(
                        Article.law_id == law_id,
                        ArticleChange.detected_at >= cutoff_datetime,
                    )
                )
            )

            # article_numbers가 지정되어 있으면 해당 조문만
            if article_numbers is not None:
                change_query = change_query.where(Article.article_no.in_(article_numbers))

            change_result = await db.execute(change_query)
            changes = change_result.all()

            # related_articles가 없는 경우: 조례당 1개만 표시
            if article_numbers is None and len(changes) > 0:
                # 가장 최근 변경사항 선택
                sorted_changes = sorted(changes, key=lambda x: (x.detected_at, x.change_date), reverse=True)
                representative_change = sorted_changes[0]

                all_results.append({
                    "ordinance_id": ordinance_id,
                    "ordinance_name": ordinance_info[ordinance_id]["name"],
                    "ordinance_category": ordinance_info[ordinance_id]["category"],
                    "department": ordinance_info[ordinance_id]["department"],
                    "article_id": representative_change.article_id,
                    "article_no": representative_change.article_no,
                    "article_title": representative_change.article_title,
                    "law_name": representative_change.law_name,
                    "change_date": representative_change.change_date,
                    "detected_at": representative_change.detected_at,
                    "change_type": representative_change.change_type,
                    "diff_html": representative_change.diff_html,
                    "affected_article_count": len(changes),  # 전체 변경된 조문 개수
                })
            else:
                # related_articles가 있는 경우: 모든 조문 표시
                for change in changes:
                    all_results.append({
                        "ordinance_id": ordinance_id,
                        "ordinance_name": ordinance_info[ordinance_id]["name"],
                        "ordinance_category": ordinance_info[ordinance_id]["category"],
                        "department": ordinance_info[ordinance_id]["department"],
                        "article_id": change.article_id,
                        "article_no": change.article_no,
                        "article_title": change.article_title,
                        "law_name": change.law_name,
                        "change_date": change.change_date,
                        "detected_at": change.detected_at,
                        "change_type": change.change_type,
                        "diff_html": change.diff_html,
                        "affected_article_count": None,  # related_articles가 있으면 None
                    })

    # Step 4: 정렬 및 페이지네이션
    all_results.sort(key=lambda x: (x["detected_at"], x["change_date"]), reverse=True)

    total = len(all_results)
    start = (page - 1) * size
    end = start + size
    paginated_results = all_results[start:end]

    # Step 5: 응답 구성
    items = [RevisionNeededOrdinanceItem(**item) for item in paginated_results]

    return RevisionNeededOrdinanceListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
    )


# =============================================================================
# Phase 4: 자동 매핑 추천 API
# =============================================================================

@router.get("/auto-recommendations", response_model=AutoMappingRecommendationResponse)
async def get_auto_mapping_recommendations(
    law_id: Optional[int] = None,
    ordinance_id: Optional[int] = None,
    min_score: float = Query(0.5, ge=0.0, le=1.0, description="최소 유사도 점수"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    자동 매핑 추천

    조문 내용과 조례 내용을 분석하여 관련성이 높은 매핑을 추천합니다.

    - **law_id**: 특정 법령의 조문만 추천 (선택사항)
    - **ordinance_id**: 특정 조례와 매핑할 조문 추천 (선택사항)
    - **min_score**: 최소 유사도 점수 (0.0 ~ 1.0, 기본값: 0.5)
    - **limit**: 최대 추천 개수 (기본값: 20)
    """
    from backend.models.ordinance import Ordinance
    from backend.models.law import Law
    from sqlalchemy import select

    # 간단한 키워드 기반 추천 (추후 고도화 가능)
    recommendations = []

    # 조문 조회
    article_query = select(Article).join(Law)
    if law_id:
        article_query = article_query.where(Article.law_id == law_id)

    # 조례 조회
    ordinance_query = select(Ordinance)
    if ordinance_id:
        ordinance_query = ordinance_query.where(Ordinance.id == ordinance_id)

    articles = await db.execute(article_query.limit(100))
    articles = articles.scalars().all()

    ordinances = await db.execute(ordinance_query.limit(100))
    ordinances = ordinances.scalars().all()

    # 간단한 키워드 매칭 (TODO: 더 정교한 알고리즘으로 개선)
    for article in articles:
        article_keywords = set(article.article_content[:200].split())

        for ordinance in ordinances:
            # 이미 매핑된 경우 제외
            from sqlalchemy import and_
            existing = await db.scalar(
                select(OrdinanceArticleMapping).where(
                    and_(
                        OrdinanceArticleMapping.article_id == article.id,
                        OrdinanceArticleMapping.ordinance_id == ordinance.id
                    )
                )
            )
            if existing:
                continue

            ordinance_keywords = set(ordinance.content[:200].split() if ordinance.content else [])

            # 유사도 계산 (Jaccard Similarity)
            if len(article_keywords) > 0 and len(ordinance_keywords) > 0:
                intersection = article_keywords & ordinance_keywords
                union = article_keywords | ordinance_keywords
                similarity = len(intersection) / len(union) if len(union) > 0 else 0.0

                if similarity >= min_score:
                    recommendations.append(AutoMappingRecommendation(
                        article_id=article.id,
                        article_no=article.article_no,
                        article_title=article.article_title,
                        article_content=article.article_content[:200] + "...",
                        ordinance_id=ordinance.id,
                        ordinance_name=ordinance.name,
                        category=ordinance.category,  # category -> category
                        similarity_score=round(similarity, 3),
                        reason=f"키워드 일치율: {len(intersection)}개 공통 키워드",
                    ))

    # 유사도 순으로 정렬
    recommendations.sort(key=lambda x: x.similarity_score, reverse=True)
    recommendations = recommendations[:limit]

    return AutoMappingRecommendationResponse(
        recommendations=recommendations,
        total=len(recommendations),
    )
