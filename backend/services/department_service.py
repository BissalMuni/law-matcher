"""
Department Service
"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.department import Department
from backend.models.ordinance import Ordinance
from backend.models.review import AmendmentReview
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
