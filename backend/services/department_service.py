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
                "parent_name": dept.parent_name,
                "sort_order": dept.sort_order,
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
        """Get all departments (for dropdown, sorted by sort_order)"""
        result = await self.db.execute(
            select(Department).order_by(Department.sort_order)
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
        from sqlalchemy import update as sql_update
        update_values = {k: v for k, v in data.items() if v is not None}
        print(f"[DEPT UPDATE] id={department_id}, values={update_values}", flush=True)
        await self.db.execute(
            sql_update(Department)
            .where(Department.id == department_id)
            .values(**update_values)
        )
        await self.db.commit()
        # 갱신된 객체 반환
        result = await self.db.execute(
            select(Department).where(Department.id == department_id)
        )
        department = result.scalar_one_or_none()
        if not department:
            raise NotFoundError(f"Department {department_id} not found")
        print(f"[DEPT UPDATE] after commit: name=[{department.name}]", flush=True)
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

    async def get_mismatches(self) -> list:
        """조례 테이블의 department 값 중 부서 마스터와 매칭되지 않는 항목 조회"""
        # 모든 부서 조회
        dept_result = await self.db.execute(select(Department))
        all_depts = dept_result.scalars().all()

        # 매칭 가능한 이름 셋 구성
        valid_names = set()
        for d in all_depts:
            valid_names.add(d.name)
            if d.parent_name:
                valid_names.add(f"{d.parent_name} {d.name}")

        # 조례 테이블의 고유 department 값 + 건수
        ord_result = await self.db.execute(
            select(Ordinance.department, func.count(Ordinance.id).label("count"))
            .where(
                Ordinance.status == "ACTIVE",
                Ordinance.department.isnot(None),
                Ordinance.department != "",
            )
            .group_by(Ordinance.department)
        )

        mismatches = []
        for row in ord_result:
            if row.department not in valid_names:
                mismatches.append({
                    "department": row.department,
                    "count": row.count,
                })

        mismatches.sort(key=lambda x: -x["count"])
        return mismatches

    async def fix_mismatch(self, old_name: str, new_name: str) -> int:
        """조례 테이블의 department 값을 일괄 변경"""
        from sqlalchemy import update
        result = await self.db.execute(
            update(Ordinance)
            .where(Ordinance.department == old_name)
            .values(department=new_name)
        )
        await self.db.commit()
        return result.rowcount

    async def get_tree(self) -> dict:
        """Get departments as hierarchical tree based on parent_name"""
        # Fetch all departments ordered by sort_order
        result = await self.db.execute(
            select(Department).order_by(Department.sort_order)
        )
        all_depts = result.scalars().all()

        # Pre-calculate ordinance counts by department_id (authoritative)
        count_by_id_result = await self.db.execute(
            select(
                Ordinance.department_id,
                func.count(Ordinance.id).label("count"),
            )
            .where(
                Ordinance.status == "ACTIVE",
                Ordinance.department_id.isnot(None),
            )
            .group_by(Ordinance.department_id)
        )
        ordinance_count_by_id = {
            row.department_id: row.count
            for row in count_by_id_result
            if row.department_id is not None
        }

        # Fallback counts for legacy rows without department_id
        count_by_name_result = await self.db.execute(
            select(
                Ordinance.department,
                func.count(Ordinance.id).label("count"),
            )
            .where(
                Ordinance.status == "ACTIVE",
                Ordinance.department_id.is_(None),
                Ordinance.department.isnot(None),
                Ordinance.department != "",
            )
            .group_by(Ordinance.department)
        )
        ordinance_count_by_name = {
            row.department: row.count
            for row in count_by_name_result
            if row.department
        }

        def resolve_count(dept: Department, parent_name: Optional[str] = None) -> int:
            """Resolve department ordinance count using id first, then string fallback."""
            count = ordinance_count_by_id.get(dept.id, 0)
            name_candidates = {dept.name}
            if parent_name:
                name_candidates.add(f"{parent_name} - {dept.name}")
                name_candidates.add(f"{parent_name} {dept.name}")
            count += sum(ordinance_count_by_name.get(name, 0) for name in name_candidates)
            return count

        # Get all parent names that exist
        parent_names = {d.name for d in all_depts if not d.parent_name}

        # Separate parents (no parent_name) and children (have parent_name with existing parent)
        parents = [d for d in all_depts if not d.parent_name]
        children = [d for d in all_depts if d.parent_name and d.parent_name in parent_names]
        # Orphans: have parent_name but parent doesn't exist - treat as top-level
        orphans = [d for d in all_depts if d.parent_name and d.parent_name not in parent_names]

        # Build tree
        dept_tree = []
        for parent in parents:
            # Get children for this parent
            parent_children = [d for d in children if d.parent_name == parent.name]

            # Build children nodes with ordinance counts
            children_nodes = []
            for child in parent_children:
                ordinance_count = resolve_count(child, parent.name)

                children_nodes.append({
                    "id": child.id,
                    "code": child.code,
                    "name": child.name,
                    "parent_name": child.parent_name,
                    "sort_order": child.sort_order,
                    "ordinance_count": ordinance_count,
                    "children": []
                })

            # Parent count includes both direct ordinances and child ordinances
            parent_direct_count = resolve_count(parent)
            parent_ordinance_count = parent_direct_count + sum(c["ordinance_count"] for c in children_nodes)

            dept_tree.append({
                "id": parent.id,
                "code": parent.code,
                "name": parent.name,
                "parent_name": parent.parent_name,
                "sort_order": parent.sort_order,
                "ordinance_count": parent_ordinance_count,
                "children": children_nodes
            })

        # Add orphan departments as top-level items
        for orphan in orphans:
            ordinance_count = resolve_count(orphan, orphan.parent_name)

            dept_tree.append({
                "id": orphan.id,
                "code": orphan.code,
                "name": orphan.name,
                "parent_name": orphan.parent_name,
                "sort_order": orphan.sort_order,
                "ordinance_count": ordinance_count,
                "children": []
            })

        # Sort by sort_order
        dept_tree.sort(key=lambda x: x["sort_order"])

        return {"bureaus": dept_tree, "zones": []}

    async def get_template(self) -> bytes:
        """Generate Excel template for department bulk upload"""
        template_data = [
            {"직제순": 1, "국": "", "부서": "기획경제국"},
            {"직제순": 2, "국": "기획경제국", "부서": "기획예산과"},
            {"직제순": 3, "국": "기획경제국", "부서": "세무관리과"},
        ]

        df = pd.DataFrame(template_data, columns=["직제순", "국", "부서"])

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='부서목록')

            worksheet = writer.sheets['부서목록']
            worksheet.column_dimensions['A'].width = 10
            worksheet.column_dimensions['B'].width = 25
            worksheet.column_dimensions['C'].width = 25

        output.seek(0)
        return output.getvalue()

    async def bulk_upload(self, file_content: bytes) -> dict:
        """Bulk upload departments from Excel file (overwrites existing data)"""
        # Read Excel file
        df = pd.read_excel(BytesIO(file_content))

        # Validate required columns (support both old and new column names)
        name_col = '부서' if '부서' in df.columns else '부서명'
        parent_col = '국' if '국' in df.columns else '상위부서명'

        required_columns = ['직제순', name_col]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"필수 컬럼이 없습니다: {col}")

        # Delete all existing departments
        await self.db.execute(
            Department.__table__.delete()
        )

        # Insert new departments
        created_count = 0
        for idx, row in df.iterrows():
            sort_order = int(row['직제순']) if pd.notna(row['직제순']) else idx + 1
            name = str(row[name_col]).strip() if pd.notna(row[name_col]) else None
            parent_name = str(row[parent_col]).strip() if parent_col in df.columns and pd.notna(row.get(parent_col)) else None

            if not name:
                continue

            # Generate code automatically
            code = f"DEPT_{sort_order:03d}"

            department = Department(
                code=code,
                name=name,
                parent_name=parent_name if parent_name else None,
                sort_order=sort_order,
            )
            self.db.add(department)
            created_count += 1

        await self.db.flush()

        return {
            "message": f"{created_count}개 부서가 등록되었습니다.",
            "created_count": created_count
        }
