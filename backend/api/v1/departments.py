"""
Department API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io
from urllib.parse import quote

from backend.api.deps import get_db
from backend.schemas.department import (
    DepartmentResponse,
    DepartmentListResponse,
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentSummary,
    DepartmentInputStatsResponse,
    DepartmentTreeResponse,
)
from backend.schemas.ordinance import OrdinanceListResponse
from backend.services.department_service import DepartmentService

router = APIRouter()


@router.get("", response_model=DepartmentListResponse)
async def get_departments(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get list of departments"""
    service = DepartmentService(db)
    return await service.get_list(page=page, size=size, search=search)


@router.get("/all", response_model=List[DepartmentResponse])
async def get_all_departments(
    db: AsyncSession = Depends(get_db),
):
    """Get all departments (for dropdown selection)"""
    service = DepartmentService(db)
    return await service.get_all()


@router.get("/summary", response_model=List[DepartmentSummary])
async def get_department_summary(
    db: AsyncSession = Depends(get_db),
):
    """Get department summary with ordinance and review counts"""
    service = DepartmentService(db)
    return await service.get_summary()


@router.get("/input-statistics", response_model=DepartmentInputStatsResponse)
async def get_input_statistics(
    db: AsyncSession = Depends(get_db),
):
    """Get department-wise parent law input statistics"""
    service = DepartmentService(db)
    return await service.get_input_statistics()


@router.get("/mismatches")
async def get_department_mismatches(
    db: AsyncSession = Depends(get_db),
):
    """조례 테이블과 부서 마스터 간 불일치 부서명 조회"""
    service = DepartmentService(db)
    return await service.get_mismatches()


@router.post("/mismatches/fix")
async def fix_department_mismatch(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """조례 테이블의 부서명을 일괄 변경"""
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="old_name, new_name 필수")
    service = DepartmentService(db)
    updated = await service.fix_mismatch(old_name, new_name)
    return {"message": f"{updated}건 수정 완료", "updated": updated}


@router.get("/tree", response_model=DepartmentTreeResponse)
async def get_department_tree(
    db: AsyncSession = Depends(get_db),
):
    """Get departments as hierarchical tree (bureaus/zones with children)"""
    service = DepartmentService(db)
    return await service.get_tree()


@router.get("/export/uninput-ordinances")
async def export_uninput_ordinances(
    db: AsyncSession = Depends(get_db),
):
    """Export department-wise uninput ordinances to Excel"""
    service = DepartmentService(db)
    excel_file = await service.export_uninput_ordinances()

    filename = "미입력_자치법규_목록.xlsx"
    encoded_filename = quote(filename)

    return StreamingResponse(
        io.BytesIO(excel_file),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )


@router.get("/template/download")
async def download_department_template(
    db: AsyncSession = Depends(get_db),
):
    """Download Excel template for department bulk upload"""
    service = DepartmentService(db)
    excel_file = await service.get_template()

    filename = "부서_업로드_템플릿.xlsx"
    encoded_filename = quote(filename)

    return StreamingResponse(
        io.BytesIO(excel_file),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get department by ID"""
    service = DepartmentService(db)
    return await service.get_by_id(department_id)


@router.post("", response_model=DepartmentResponse)
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create new department"""
    service = DepartmentService(db)
    return await service.create(data.model_dump())


@router.patch("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update department"""
    update_data = data.model_dump(exclude_unset=True)
    print(f"[DEPT UPDATE] id={department_id}, data={update_data}", flush=True)
    service = DepartmentService(db)
    return await service.update(department_id, update_data)


@router.delete("/{department_id}")
async def delete_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete department"""
    service = DepartmentService(db)
    await service.delete(department_id)
    return {"message": "Department deleted"}


@router.get("/{department_id}/ordinances", response_model=OrdinanceListResponse)
async def get_department_ordinances(
    department_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get ordinances by department"""
    service = DepartmentService(db)
    return await service.get_ordinances(department_id, page=page, size=size)


@router.post("/upload")
async def upload_departments(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Bulk upload departments from Excel file (overwrites existing data)"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Excel 파일만 업로드 가능합니다.")

    content = await file.read()
    service = DepartmentService(db)

    try:
        result = await service.bulk_upload(content)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")
