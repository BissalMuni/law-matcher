"""
Department API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
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
    service = DepartmentService(db)
    return await service.update(department_id, data.model_dump(exclude_unset=True))


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
