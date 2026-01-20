"""
LawChanges API endpoints - 법령 변경 이력 관리
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.deps import get_db
from backend.models.law_change import LawChange, ChangeStatus, ApiStatus
from backend.models.law import Law
from backend.schemas.ordinance import (
    LawChangeResponse,
    LawChangeListResponse,
    LawChangeApproveRequest,
    LawChangeRejectRequest,
    LawChangeBulkApproveRequest,
    LawChangeBulkRejectRequest,
    LawChangeStatsResponse,
)

router = APIRouter()


def _build_law_change_response(change: LawChange) -> dict:
    """LawChange 객체를 응답 dict로 변환"""
    return {
        "id": change.id,
        "law_id": change.law_id,
        "law_name": change.law.law_name if change.law else "",
        "law_type": change.law.law_type if change.law else None,
        "sync_date": change.sync_date,
        "sync_batch_id": change.sync_batch_id,
        "api_status": change.api_status.value if change.api_status else None,
        "api_message": change.api_message,
        "old_values": change.old_values,
        "new_values": change.new_values,
        "dept_name": change.dept_name,
        "dept_code": change.dept_code,
        "status": change.status.value if change.status else None,
        "processed_at": change.processed_at,
        "processed_by": change.processed_by,
        "process_note": change.process_note,
        "created_at": change.created_at,
        "updated_at": change.updated_at,
    }


@router.get("", response_model=LawChangeListResponse)
async def get_law_changes(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,  # pending, reviewing, approved, rejected
    api_status: Optional[str] = None,  # success, no_response, not_found
    dept_name: Optional[str] = None,
    sync_batch_id: Optional[str] = None,
    sync_date: Optional[str] = None,  # YYYY-MM-DD 형식 날짜 필터
    search: Optional[str] = None,  # 법령명 검색
    db: AsyncSession = Depends(get_db),
):
    """
    법령 변경 이력 목록 조회

    - 부서별, 상태별, API 상태별 필터링 가능
    - 동기화 날짜별 필터링 가능
    - 법령명 검색 가능
    """
    query = select(LawChange).options(selectinload(LawChange.law))

    # 필터링
    if status:
        try:
            status_enum = ChangeStatus(status)
            query = query.where(LawChange.status == status_enum)
        except ValueError:
            pass

    if api_status:
        try:
            api_status_enum = ApiStatus(api_status)
            query = query.where(LawChange.api_status == api_status_enum)
        except ValueError:
            pass

    if dept_name:
        query = query.where(LawChange.dept_name.ilike(f"%{dept_name}%"))

    if sync_batch_id:
        query = query.where(LawChange.sync_batch_id == sync_batch_id)

    if sync_date:
        # 날짜 필터링 (해당 날짜의 데이터만)
        query = query.where(func.date(LawChange.sync_date) == sync_date)

    if search:
        query = query.join(Law).where(Law.law_name.ilike(f"%{search}%"))

    # 총 개수
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 페이징 및 정렬
    query = query.order_by(LawChange.sync_date.desc(), LawChange.id.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    changes = result.scalars().all()

    items = [_build_law_change_response(c) for c in changes]

    return {
        "total": total or 0,
        "page": page,
        "size": size,
        "items": items,
    }


@router.get("/stats", response_model=LawChangeStatsResponse)
async def get_law_change_stats(
    db: AsyncSession = Depends(get_db),
):
    """법령 변경 통계 조회"""
    # 전체 통계
    total = await db.scalar(select(func.count(LawChange.id)))
    pending = await db.scalar(
        select(func.count(LawChange.id)).where(LawChange.status == ChangeStatus.PENDING)
    )
    reviewing = await db.scalar(
        select(func.count(LawChange.id)).where(LawChange.status == ChangeStatus.REVIEWING)
    )
    approved = await db.scalar(
        select(func.count(LawChange.id)).where(LawChange.status == ChangeStatus.APPROVED)
    )
    rejected = await db.scalar(
        select(func.count(LawChange.id)).where(LawChange.status == ChangeStatus.REJECTED)
    )

    # 부서별 통계
    dept_stats_query = (
        select(
            LawChange.dept_name,
            func.count(LawChange.id).label("total"),
            func.count(LawChange.id).filter(LawChange.status == ChangeStatus.PENDING).label("pending"),
        )
        .where(LawChange.dept_name.isnot(None))
        .group_by(LawChange.dept_name)
        .order_by(func.count(LawChange.id).desc())
    )
    dept_result = await db.execute(dept_stats_query)
    by_dept = [
        {"dept_name": row[0], "total": row[1], "pending": row[2]}
        for row in dept_result.all()
    ]

    return {
        "total": total or 0,
        "pending": pending or 0,
        "reviewing": reviewing or 0,
        "approved": approved or 0,
        "rejected": rejected or 0,
        "by_dept": by_dept,
    }


@router.get("/departments")
async def get_change_departments(
    db: AsyncSession = Depends(get_db),
):
    """변경 이력이 있는 부서 목록 조회"""
    query = (
        select(
            LawChange.dept_name,
            func.count(LawChange.id).label("total"),
            func.count(LawChange.id).filter(LawChange.status == ChangeStatus.PENDING).label("pending"),
        )
        .where(LawChange.dept_name.isnot(None))
        .group_by(LawChange.dept_name)
        .order_by(LawChange.dept_name)
    )
    result = await db.execute(query)
    return [
        {"dept_name": row[0], "total": row[1], "pending": row[2]}
        for row in result.all()
    ]


@router.get("/sync-batches")
async def get_sync_batches(
    db: AsyncSession = Depends(get_db),
):
    """동기화 배치 목록 조회"""
    query = (
        select(
            LawChange.sync_batch_id,
            func.min(LawChange.sync_date).label("sync_date"),
            func.count(LawChange.id).label("total"),
            func.count(LawChange.id).filter(LawChange.api_status == ApiStatus.SUCCESS).label("success"),
            func.count(LawChange.id).filter(LawChange.api_status == ApiStatus.NO_RESPONSE).label("no_response"),
            func.count(LawChange.id).filter(LawChange.api_status == ApiStatus.NOT_FOUND).label("not_found"),
        )
        .where(LawChange.sync_batch_id.isnot(None))
        .group_by(LawChange.sync_batch_id)
        .order_by(func.min(LawChange.sync_date).desc())
    )
    result = await db.execute(query)
    return [
        {
            "sync_batch_id": row[0],
            "sync_date": row[1],
            "total": row[2],
            "success": row[3],
            "no_response": row[4],
            "not_found": row[5],
        }
        for row in result.all()
    ]


@router.get("/sync-dates")
async def get_sync_dates(
    db: AsyncSession = Depends(get_db),
):
    """
    동기화 날짜 목록 조회 (드롭다운용)

    - 날짜별로 그룹핑하여 반환
    - 최신 날짜순 정렬
    """
    query = (
        select(
            func.date(LawChange.sync_date).label("sync_date"),
            func.count(LawChange.id).label("total"),
            func.count(LawChange.id).filter(LawChange.api_status == ApiStatus.SUCCESS).label("success"),
            func.count(LawChange.id).filter(LawChange.status == ChangeStatus.PENDING).label("pending"),
        )
        .group_by(func.date(LawChange.sync_date))
        .order_by(func.date(LawChange.sync_date).desc())
    )
    result = await db.execute(query)
    return [
        {
            "sync_date": str(row[0]),
            "total": row[1],
            "success": row[2],
            "pending": row[3],
        }
        for row in result.all()
    ]


@router.get("/{change_id}")
async def get_law_change(
    change_id: int,
    db: AsyncSession = Depends(get_db),
):
    """법령 변경 상세 조회"""
    query = (
        select(LawChange)
        .options(selectinload(LawChange.law))
        .where(LawChange.id == change_id)
    )
    result = await db.execute(query)
    change = result.scalar_one_or_none()

    if not change:
        raise HTTPException(status_code=404, detail="변경 이력을 찾을 수 없습니다.")

    return _build_law_change_response(change)


@router.post("/{change_id}/approve")
async def approve_law_change(
    change_id: int,
    request: LawChangeApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    법령 변경 승인

    - 변경 내용을 laws 테이블에 반영
    - law_changes 상태를 approved로 변경
    """
    query = (
        select(LawChange)
        .options(selectinload(LawChange.law))
        .where(LawChange.id == change_id)
    )
    result = await db.execute(query)
    change = result.scalar_one_or_none()

    if not change:
        raise HTTPException(status_code=404, detail="변경 이력을 찾을 수 없습니다.")

    if change.status == ChangeStatus.APPROVED:
        raise HTTPException(status_code=400, detail="이미 승인된 변경입니다.")

    # API 실패 상태인 경우 승인 불가
    if change.api_status != ApiStatus.SUCCESS:
        raise HTTPException(
            status_code=400,
            detail="API 실패 상태의 변경은 승인할 수 없습니다. 반려 처리해주세요."
        )

    # laws 테이블 업데이트
    law = change.law
    if law and change.new_values:
        new_values = change.new_values
        if "proclaimed_date" in new_values and new_values["proclaimed_date"]:
            from datetime import datetime as dt
            law.proclaimed_date = dt.strptime(new_values["proclaimed_date"], "%Y-%m-%d").date()
        if "enforced_date" in new_values and new_values["enforced_date"]:
            from datetime import datetime as dt
            law.enforced_date = dt.strptime(new_values["enforced_date"], "%Y-%m-%d").date()
        if "revision_type" in new_values:
            law.revision_type = new_values["revision_type"]
        if "law_id" in new_values:
            law.law_id = new_values["law_id"]
        if "dept_name" in new_values:
            law.dept_name = new_values["dept_name"]
        law.last_synced_at = datetime.utcnow()

    # 변경 상태 업데이트
    change.status = ChangeStatus.APPROVED
    change.processed_at = datetime.utcnow()
    change.processed_by = request.processed_by
    change.process_note = request.process_note

    await db.commit()

    return {"success": True, "message": "변경이 승인되었습니다."}


@router.post("/{change_id}/reject")
async def reject_law_change(
    change_id: int,
    request: LawChangeRejectRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    법령 변경 반려

    - laws 테이블은 변경하지 않음
    - law_changes 상태를 rejected로 변경
    """
    query = select(LawChange).where(LawChange.id == change_id)
    result = await db.execute(query)
    change = result.scalar_one_or_none()

    if not change:
        raise HTTPException(status_code=404, detail="변경 이력을 찾을 수 없습니다.")

    if change.status in [ChangeStatus.APPROVED, ChangeStatus.REJECTED]:
        raise HTTPException(status_code=400, detail="이미 처리된 변경입니다.")

    change.status = ChangeStatus.REJECTED
    change.processed_at = datetime.utcnow()
    change.processed_by = request.processed_by
    change.process_note = request.process_note

    await db.commit()

    return {"success": True, "message": "변경이 반려되었습니다."}


@router.post("/bulk-approve")
async def bulk_approve_law_changes(
    request: LawChangeBulkApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """법령 변경 일괄 승인"""
    query = (
        select(LawChange)
        .options(selectinload(LawChange.law))
        .where(
            and_(
                LawChange.id.in_(request.ids),
                LawChange.status == ChangeStatus.PENDING,
                LawChange.api_status == ApiStatus.SUCCESS,
            )
        )
    )
    result = await db.execute(query)
    changes = result.scalars().all()

    approved_count = 0
    for change in changes:
        # laws 테이블 업데이트
        law = change.law
        if law and change.new_values:
            new_values = change.new_values
            if "proclaimed_date" in new_values and new_values["proclaimed_date"]:
                from datetime import datetime as dt
                law.proclaimed_date = dt.strptime(new_values["proclaimed_date"], "%Y-%m-%d").date()
            if "enforced_date" in new_values and new_values["enforced_date"]:
                from datetime import datetime as dt
                law.enforced_date = dt.strptime(new_values["enforced_date"], "%Y-%m-%d").date()
            if "revision_type" in new_values:
                law.revision_type = new_values["revision_type"]
            if "law_id" in new_values:
                law.law_id = new_values["law_id"]
            if "dept_name" in new_values:
                law.dept_name = new_values["dept_name"]
            law.last_synced_at = datetime.utcnow()

        change.status = ChangeStatus.APPROVED
        change.processed_at = datetime.utcnow()
        change.processed_by = request.processed_by
        change.process_note = request.process_note
        approved_count += 1

    await db.commit()

    return {
        "success": True,
        "approved_count": approved_count,
        "message": f"{approved_count}건의 변경이 승인되었습니다.",
    }


@router.post("/bulk-reject")
async def bulk_reject_law_changes(
    request: LawChangeBulkRejectRequest,
    db: AsyncSession = Depends(get_db),
):
    """법령 변경 일괄 반려"""
    query = (
        select(LawChange)
        .where(
            and_(
                LawChange.id.in_(request.ids),
                LawChange.status.in_([ChangeStatus.PENDING, ChangeStatus.REVIEWING]),
            )
        )
    )
    result = await db.execute(query)
    changes = result.scalars().all()

    rejected_count = 0
    for change in changes:
        change.status = ChangeStatus.REJECTED
        change.processed_at = datetime.utcnow()
        change.processed_by = request.processed_by
        change.process_note = request.process_note
        rejected_count += 1

    await db.commit()

    return {
        "success": True,
        "rejected_count": rejected_count,
        "message": f"{rejected_count}건의 변경이 반려되었습니다.",
    }


@router.get("/history/{law_id}")
async def get_law_change_history(
    law_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    특정 법령의 변경 연혁 조회

    - 동기화일자 기준 내림차순 정렬
    - 승인/반려된 이력 모두 포함 (기록 관리용)
    """
    query = (
        select(LawChange)
        .options(selectinload(LawChange.law))
        .where(LawChange.law_id == law_id)
    )

    # 총 개수
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 페이징 및 정렬 (동기화일자 내림차순)
    query = query.order_by(LawChange.sync_date.desc(), LawChange.id.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    changes = result.scalars().all()

    items = [_build_law_change_response(c) for c in changes]

    return {
        "total": total or 0,
        "page": page,
        "size": size,
        "items": items,
    }


@router.get("/history-summary")
async def get_law_change_history_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    법령별 변경 연혁 요약 조회

    - 각 법령의 총 변경 횟수, 최근 변경일 등
    """
    query = (
        select(
            LawChange.law_id,
            Law.law_name,
            Law.law_type,
            Law.dept_name,
            func.count(LawChange.id).label("total_changes"),
            func.count(LawChange.id).filter(LawChange.status == ChangeStatus.APPROVED).label("approved_count"),
            func.count(LawChange.id).filter(LawChange.status == ChangeStatus.PENDING).label("pending_count"),
            func.max(LawChange.sync_date).label("last_sync_date"),
        )
        .join(Law, LawChange.law_id == Law.id)
        .group_by(LawChange.law_id, Law.law_name, Law.law_type, Law.dept_name)
        .order_by(func.max(LawChange.sync_date).desc())
    )
    result = await db.execute(query)

    return [
        {
            "law_id": row[0],
            "law_name": row[1],
            "law_type": row[2],
            "dept_name": row[3],
            "total_changes": row[4],
            "approved_count": row[5],
            "pending_count": row[6],
            "last_sync_date": row[7],
        }
        for row in result.all()
    ]
