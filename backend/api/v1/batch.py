"""
일괄 개정검토 API endpoints
"""
import io
import json
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.models.user import User
from backend.services.batch_processing_service import BatchProcessingService

router = APIRouter()


# === Schemas ===

class BatchJobCreateRequest(BaseModel):
    name: str
    filter_params: dict  # {category?, department?, search?}


class BatchJobResponse(BaseModel):
    id: int
    name: str
    current_step: str
    step1_status: str
    step2_status: str
    step3_status: str
    step4_status: str
    step5_status: str
    step2_progress: int
    step2_total: int
    step3_progress: int
    step3_total: int
    step4_progress: int
    step4_total: int
    filter_params: Optional[dict] = None
    summary: Optional[dict] = None
    created_at: str

    class Config:
        from_attributes = True


class BatchJobItemResponse(BaseModel):
    id: int
    batch_job_id: int
    ordinance_id: int
    ordinance_name: str
    ordinance_department: Optional[str] = None
    ordinance_category: Optional[str] = None
    step1_result: str
    step1_reason: Optional[str] = None
    step2_result: Optional[str] = None
    step2_reason: Optional[str] = None
    step2_detail: Optional[dict] = None
    step3_result: Optional[str] = None
    step3_reason: Optional[str] = None
    step4_result: Optional[str] = None
    step4_reason: Optional[str] = None
    step4_ai_summary: Optional[str] = None
    step4_ai_result: Optional[str] = None
    final_result: Optional[str] = None
    manually_excluded: bool = False

    class Config:
        from_attributes = True


class RetryRequest(BaseModel):
    step: str  # "step2" | "step3" | "step4"
    item_ids: Optional[list[int]] = None


def _job_to_response(job) -> dict:
    return {
        "id": job.id,
        "name": job.name,
        "current_step": job.current_step,
        "step1_status": job.step1_status,
        "step2_status": job.step2_status,
        "step3_status": job.step3_status,
        "step4_status": job.step4_status,
        "step5_status": job.step5_status,
        "step2_progress": job.step2_progress,
        "step2_total": job.step2_total,
        "step3_progress": job.step3_progress,
        "step3_total": job.step3_total,
        "step4_progress": job.step4_progress,
        "step4_total": job.step4_total,
        "filter_params": job.filter_params,
        "summary": job.summary,
        "created_at": job.created_at.isoformat() if job.created_at else "",
    }


def _item_to_response(item) -> dict:
    return {
        "id": item.id,
        "batch_job_id": item.batch_job_id,
        "ordinance_id": item.ordinance_id,
        "ordinance_name": item.ordinance_name,
        "ordinance_department": item.ordinance_department,
        "ordinance_category": item.ordinance_category,
        "step1_result": item.step1_result,
        "step1_reason": item.step1_reason,
        "step2_result": item.step2_result,
        "step2_reason": item.step2_reason,
        "step2_detail": item.step2_detail,
        "step3_result": item.step3_result,
        "step3_reason": item.step3_reason,
        "step4_result": item.step4_result,
        "step4_reason": item.step4_reason,
        "step4_ai_summary": item.step4_ai_summary,
        "step4_ai_result": item.step4_ai_result,
        "final_result": item.final_result,
        "manually_excluded": item.manually_excluded,
    }


# === Endpoints ===

@router.get("")
async def get_batch_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """배치 작업 목록 조회"""
    if current_user.user_type != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    service = BatchProcessingService(db)
    jobs = await service.get_batch_jobs()
    return [_job_to_response(j) for j in jobs]


@router.post("")
async def create_batch_job(
    request: BatchJobCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """배치 작업 생성 (Step 1: 대상 선정)"""
    if current_user.user_type != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    service = BatchProcessingService(db)
    job = await service.create_batch_job(
        name=request.name,
        filter_params=request.filter_params,
        user_id=current_user.id,
    )
    return _job_to_response(job)


@router.get("/{job_id}")
async def get_batch_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """배치 작업 상세 조회"""
    service = BatchProcessingService(db)
    job = await service.get_batch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="배치 작업을 찾을 수 없습니다")
    return _job_to_response(job)


@router.delete("/{job_id}")
async def delete_batch_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """배치 작업 삭제"""
    if current_user.user_type != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    service = BatchProcessingService(db)
    deleted = await service.delete_batch_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="배치 작업을 찾을 수 없습니다")
    return {"message": "삭제되었습니다"}


@router.get("/{job_id}/items")
async def get_batch_items(
    job_id: int,
    step_filter: Optional[str] = None,
    result_filter: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """배치 항목 조회"""
    service = BatchProcessingService(db)
    result = await service.get_batch_items(
        job_id, step_filter, result_filter, page, size
    )
    return {
        "items": [_item_to_response(i) for i in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "size": result["size"],
    }


@router.get("/{job_id}/counts")
async def get_step_counts(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """단계별 결과 집계"""
    service = BatchProcessingService(db)
    return await service.get_step_counts(job_id)


@router.post("/{job_id}/items/{item_id}/toggle-exclude")
async def toggle_item_exclusion(
    job_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """항목 수동 제외/포함 토글"""
    service = BatchProcessingService(db)
    item = await service.toggle_item_exclusion(item_id)
    return _item_to_response(item)


@router.get("/{job_id}/items/{item_id}/detail")
async def get_item_detail(
    job_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """항목 상세 조회 — 수집내용(제개정이유/개정문) + AI 분석결과"""
    service = BatchProcessingService(db)
    return await service.get_item_detail(item_id)


# === Step execution with SSE streaming ===

@router.post("/{job_id}/step2")
async def run_step2(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Step 2: 개정판별 실행 (SSE 스트리밍)"""
    if current_user.user_type != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")

    service = BatchProcessingService(db)

    async def event_stream():
        try:
            async for progress in service.run_step2_detect(job_id):
                yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{job_id}/step3")
async def run_step3(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Step 3: 제개정이유 수집 (SSE 스트리밍)"""
    if current_user.user_type != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")

    service = BatchProcessingService(db)

    async def event_stream():
        try:
            async for progress in service.run_step3_collect(job_id):
                yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{job_id}/step4")
async def run_step4(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Step 4: AI 분석 실행 (SSE 스트리밍)"""
    if current_user.user_type != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")

    service = BatchProcessingService(db)

    async def event_stream():
        try:
            async for progress in service.run_step4_analyze(job_id):
                yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{job_id}/retry")
async def retry_step(
    job_id: int,
    request: RetryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """오류 항목 재시도 초기화"""
    service = BatchProcessingService(db)
    count = await service.retry_step_items(job_id, request.step, request.item_ids)
    return {"message": f"{count}건 초기화 완료", "count": count}


@router.get("/{job_id}/report")
async def get_report(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """보고서 데이터 조회 (JSON)"""
    service = BatchProcessingService(db)
    return await service.generate_report_data(job_id)


@router.get("/{job_id}/export")
async def export_excel(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """보고서 Excel 다운로드"""
    service = BatchProcessingService(db)

    try:
        excel_bytes = await service.export_excel(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel 생성 실패: {str(e)}")

    job = await service.get_batch_job(job_id)
    filename = f"일괄개정검토_{job.name}_{job.created_at.strftime('%Y%m%d')}.xlsx" if job else "보고서.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@router.get("/{job_id}/export-pdf")
async def export_pdf(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """보고서 PDF 다운로드"""
    service = BatchProcessingService(db)

    try:
        pdf_bytes = await service.export_pdf(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 생성 실패: {str(e)}")

    job = await service.get_batch_job(job_id)
    filename = f"일괄개정검토_{job.name}_{job.created_at.strftime('%Y%m%d')}.pdf" if job else "보고서.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@router.get("/{job_id}/export-docx")
async def export_docx(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """보고서 Word(docx) 다운로드"""
    service = BatchProcessingService(db)

    try:
        docx_bytes = await service.export_docx(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Word 생성 실패: {str(e)}")

    job = await service.get_batch_job(job_id)
    filename = f"일괄개정검토_{job.name}_{job.created_at.strftime('%Y%m%d')}.docx" if job else "보고서.docx"

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )
