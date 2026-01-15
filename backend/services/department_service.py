"""
Department Service
"""
from typing import Optional, List
from sqlalchemy import select, func, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import pandas as pd
from io import BytesIO

from backend.models.department import Department
from backend.models.ordinance import Ordinance
from backend.models.review import AmendmentReview
from backend.models.ordinance_law_mapping import OrdinanceLawMapping
from backend.core.exceptions import NotFoundError


class DepartmentService:
    """Department business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
    ) -> dict:
        """Get paginated list of departments"""
        query = select(Department)

        if search:
            query = query.where(Department.name.ilike(f"%{search}%"))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(Department.name).offset((page - 1) * size).limit(size)
        result = await self.db.execute(query)
        departments = result.scalars().all()

        # Get ordinance counts for each department
        items = []
        for dept in departments:
            count_result = await self.db.execute(
                select(func.count()).where(Ordinance.department_id == dept.id)
            )
            ordinance_count = count_result.scalar() or 0
            items.append({
                "id": dept.id,
                "code": dept.code,
                "name": dept.name,
                "parent_code": dept.parent_code,
                "phone": dept.phone,
                "created_at": dept.created_at,
                "updated_at": dept.updated_at,
                "ordinance_count": ordinance_count,
            })

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": items,
        }

    async def get_all(self) -> List[Department]:
        """Get all departments (for dropdown)"""
        result = await self.db.execute(
            select(Department).order_by(Department.name)
        )
        return result.scalars().all()

    async def get_by_id(self, department_id: int) -> Department:
        """Get department by ID"""
        result = await self.db.execute(
            select(Department).where(Department.id == department_id)
        )
        department = result.scalar_one_or_none()
        if not department:
            raise NotFoundError(f"Department {department_id} not found")
        return department

    async def create(self, data: dict) -> Department:
        """Create new department"""
        department = Department(**data)
        self.db.add(department)
        await self.db.flush()
        await self.db.refresh(department)
        return department

    async def update(self, department_id: int, data: dict) -> Department:
        """Update department"""
        department = await self.get_by_id(department_id)
        for key, value in data.items():
            if value is not None:
                setattr(department, key, value)
        await self.db.flush()
        await self.db.refresh(department)
        return department

    async def delete(self, department_id: int) -> None:
        """Delete department"""
        department = await self.get_by_id(department_id)
        await self.db.delete(department)

    async def get_ordinances(
        self,
        department_id: int,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        """Get ordinances by department"""
        await self.get_by_id(department_id)  # Check exists

        query = select(Ordinance).where(
            Ordinance.department_id == department_id,
            Ordinance.status == "ACTIVE"
        )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(Ordinance.name).offset((page - 1) * size).limit(size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": items,
        }

    async def get_summary(self) -> List[dict]:
        """Get department summary with counts"""
        result = await self.db.execute(
            select(Department).order_by(Department.name)
        )
        departments = result.scalars().all()

        summaries = []
        for dept in departments:
            # Count ordinances
            ordinance_count = await self.db.scalar(
                select(func.count()).where(Ordinance.department_id == dept.id)
            ) or 0

            # Count pending reviews
            pending_count = await self.db.scalar(
                select(func.count())
                .select_from(AmendmentReview)
                .join(Ordinance)
                .where(
                    Ordinance.department_id == dept.id,
                    AmendmentReview.status == "PENDING"
                )
            ) or 0

            summaries.append({
                "id": dept.id,
                "code": dept.code,
                "name": dept.name,
                "ordinance_count": ordinance_count,
                "pending_review_count": pending_count,
            })

        return summaries

    async def get_input_statistics(self) -> dict:
        """Get department-wise parent law input statistics"""
        # Get distinct department names from ordinances
        result = await self.db.execute(
            select(Ordinance.department)
            .where(
                Ordinance.department.isnot(None),
                Ordinance.status == "ACTIVE"
            )
            .distinct()
            .order_by(Ordinance.department)
        )
        department_names = result.scalars().all()

        department_stats = []
        total_ordinances = 0
        total_with_laws = 0

        for idx, dept_name in enumerate(department_names, start=1):
            # Count total ordinances for this department
            total_count = await self.db.scalar(
                select(func.count())
                .select_from(Ordinance)
                .where(
                    Ordinance.department == dept_name,
                    Ordinance.status == "ACTIVE"
                )
            ) or 0

            # Count ordinances with at least one parent law mapping
            with_laws_count = await self.db.scalar(
                select(func.count(func.distinct(OrdinanceLawMapping.ordinance_id)))
                .select_from(OrdinanceLawMapping)
                .join(Ordinance, OrdinanceLawMapping.ordinance_id == Ordinance.id)
                .where(
                    Ordinance.department == dept_name,
                    Ordinance.status == "ACTIVE"
                )
            ) or 0

            without_laws_count = total_count - with_laws_count
            progress_rate = (with_laws_count / total_count * 100) if total_count > 0 else 0.0

            department_stats.append({
                "id": idx,
                "name": dept_name,
                "total_ordinances": total_count,
                "ordinances_with_laws": with_laws_count,
                "ordinances_without_laws": without_laws_count,
                "progress_rate": round(progress_rate, 1)
            })

            total_ordinances += total_count
            total_with_laws += with_laws_count

        total_without_laws = total_ordinances - total_with_laws
        overall_progress = (total_with_laws / total_ordinances * 100) if total_ordinances > 0 else 0.0

        return {
            "total_ordinances": total_ordinances,
            "total_with_laws": total_with_laws,
            "total_without_laws": total_without_laws,
            "overall_progress_rate": round(overall_progress, 1),
            "departments": department_stats
        }

    async def export_uninput_ordinances(self) -> bytes:
        """Export ordinances without parent laws to Excel"""
        # Get distinct department names
        result = await self.db.execute(
            select(Ordinance.department)
            .where(
                Ordinance.department.isnot(None),
                Ordinance.status == "ACTIVE"
            )
            .distinct()
            .order_by(Ordinance.department)
        )
        department_names = result.scalars().all()

        # Prepare data for Excel
        excel_data = []

        for dept_name in department_names:
            # Get all ordinances for this department
            ordinances_result = await self.db.execute(
                select(Ordinance)
                .where(
                    Ordinance.department == dept_name,
                    Ordinance.status == "ACTIVE"
                )
                .order_by(Ordinance.name)
            )
            ordinances = ordinances_result.scalars().all()

            for ordinance in ordinances:
                # Check if has parent laws
                parent_law_count = await self.db.scalar(
                    select(func.count())
                    .select_from(OrdinanceLawMapping)
                    .where(OrdinanceLawMapping.ordinance_id == ordinance.id)
                ) or 0

                # Only include ordinances without parent laws
                if parent_law_count == 0:
                    excel_data.append({
                        "부서명": dept_name,
                        "자치법규명": ordinance.name,
                        "종류": ordinance.category or "",
                        "공포일": ordinance.enacted_date.strftime("%Y-%m-%d") if ordinance.enacted_date else "",
                        "시행일": ordinance.enforced_date.strftime("%Y-%m-%d") if ordinance.enforced_date else "",
                        "제개정": ordinance.revision_type or "",
                    })

        # Create Excel file
        df = pd.DataFrame(excel_data)

        # Write to BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='미입력 자치법규')

            # Auto-adjust column width
            worksheet = writer.sheets['미입력 자치법규']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).map(len).max(),
                    len(str(col))
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = max_length

        output.seek(0)
        return output.getvalue()
