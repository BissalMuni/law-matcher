"""
Admin API endpoints for management tasks
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from backend.api.deps import get_db

router = APIRouter()


@router.post("/migrate-departments")
async def migrate_departments(db: AsyncSession = Depends(get_db)):
    """Add new columns to departments table"""
    try:
        # Add manager_name column
        await db.execute(text("""
            ALTER TABLE departments
            ADD COLUMN IF NOT EXISTS manager_name VARCHAR(100)
        """))

        # Add department_type column
        await db.execute(text("""
            ALTER TABLE departments
            ADD COLUMN IF NOT EXISTS department_type VARCHAR(20)
        """))

        await db.commit()
        return {"message": "Migration completed successfully"}
    except Exception as e:
        await db.rollback()
        return {"error": str(e)}


@router.post("/seed-departments")
async def seed_departments(db: AsyncSession = Depends(get_db)):
    """Seed bureau, zone, and neighborhood data"""
    try:
        # Create bureaus and special groups
        bureaus = [
            ('ADMIN', '행정국', 'bureau', 10),
            ('PLAN_ECON', '기획경제국', 'bureau', 20),
            ('WELFARE', '복지생활국', 'bureau', 30),
            ('FUTURE_CULTURE', '미래문화국', 'bureau', 40),
            ('URBAN_ENV', '도시환경국', 'bureau', 50),
            ('SAFETY_TRANSPORT', '안전교통국', 'bureau', 60),
            ('FUTURE_STRATEGY', '미래전략기획단', 'bureau', 70),
            ('HEALTH_CENTER', '보건소', 'bureau', 80),
        ]

        for code, name, dept_type, sort_order in bureaus:
            await db.execute(text("""
                INSERT INTO departments (code, name, department_type, sort_order, created_at, updated_at)
                VALUES (:code, :name, :dept_type, :sort_order, :now, :now)
                ON CONFLICT (code) DO UPDATE SET
                    department_type = EXCLUDED.department_type,
                    sort_order = EXCLUDED.sort_order
            """), {
                'code': code,
                'name': name,
                'dept_type': dept_type,
                'sort_order': sort_order,
                'now': datetime.utcnow()
            })

        # Create zones
        zones = [
            ('ZONE_1', '1권역', 'zone', 1),
            ('ZONE_2', '2권역', 'zone', 2),
            ('ZONE_3', '3권역', 'zone', 3),
            ('ZONE_4', '4권역', 'zone', 4),
        ]

        for code, name, dept_type, sort_order in zones:
            await db.execute(text("""
                INSERT INTO departments (code, name, department_type, sort_order, created_at, updated_at)
                VALUES (:code, :name, :dept_type, :sort_order, :now, :now)
                ON CONFLICT (code) DO UPDATE SET
                    department_type = EXCLUDED.department_type,
                    sort_order = EXCLUDED.sort_order
            """), {
                'code': code,
                'name': name,
                'dept_type': dept_type,
                'sort_order': sort_order,
                'now': datetime.utcnow()
            })

        # Update existing departments - 행정국
        admin_depts = ['정책홍보실', '감사담당관', '중대재해예방실', '총무과', '주민자치과', '교육지원과', '재무과', '민원여권과']
        for idx, name in enumerate(admin_depts, start=1):
            await db.execute(text("""
                UPDATE departments
                SET parent_code = 'ADMIN', department_type = 'department', sort_order = :sort_order
                WHERE name = :name
            """), {'name': name, 'sort_order': idx * 10})

        # 기획경제국
        plan_econ_depts = ['기획예산과', '지역경제과', '일자리정책과', '세무관리과', '재산세과', '지방소득세과']
        for idx, name in enumerate(plan_econ_depts, start=1):
            await db.execute(text("""
                UPDATE departments
                SET parent_code = 'PLAN_ECON', department_type = 'department', sort_order = :sort_order
                WHERE name = :name
            """), {'name': name, 'sort_order': idx * 10})

        # 복지생활국
        welfare_depts = ['복지정책과', '사회보장과', '어르신복지과', '장애인복지과', '보육지원과', '가족정책과', '자원순환과']
        for idx, name in enumerate(welfare_depts, start=1):
            await db.execute(text("""
                UPDATE departments
                SET parent_code = 'WELFARE', department_type = 'department', sort_order = :sort_order
                WHERE name = :name
            """), {'name': name, 'sort_order': idx * 10})

        # 미래문화국
        future_culture_depts = ['디지털도시과', '스마트정보과', '문화도시과', '생활체육과', '관광진흥과']
        for idx, name in enumerate(future_culture_depts, start=1):
            await db.execute(text("""
                UPDATE departments
                SET parent_code = 'FUTURE_CULTURE', department_type = 'department', sort_order = :sort_order
                WHERE name = :name
            """), {'name': name, 'sort_order': idx * 10})

        # 도시환경국
        urban_env_depts = ['주택과', '재건축사업과', '도시계획과', '건축과', '환경과', '공원녹지과', '부동산정보과']
        for idx, name in enumerate(urban_env_depts, start=1):
            await db.execute(text("""
                UPDATE departments
                SET parent_code = 'URBAN_ENV', department_type = 'department', sort_order = :sort_order
                WHERE name = :name
            """), {'name': name, 'sort_order': idx * 10})

        # 안전교통국
        safety_transport_depts = ['재난안전과', '교통행정과', '주차관리과', '자동차민원과', '건설관리과', '도로관리과', '치수과']
        for idx, name in enumerate(safety_transport_depts, start=1):
            await db.execute(text("""
                UPDATE departments
                SET parent_code = 'SAFETY_TRANSPORT', department_type = 'department', sort_order = :sort_order
                WHERE name = :name
            """), {'name': name, 'sort_order': idx * 10})

        # 미래전략기획단
        future_strategy_depts = ['혁신전략과', '공간개발과']
        for idx, name in enumerate(future_strategy_depts, start=1):
            await db.execute(text("""
                UPDATE departments
                SET parent_code = 'FUTURE_STRATEGY', department_type = 'department', sort_order = :sort_order
                WHERE name = :name
            """), {'name': name, 'sort_order': idx * 10})

        # 보건소
        health_center_depts = ['보건행정과', '위생과', '질병관리과', '건강관리과', '의약과', '세곡보건지소']
        for idx, name in enumerate(health_center_depts, start=1):
            await db.execute(text("""
                UPDATE departments
                SET parent_code = 'HEALTH_CENTER', department_type = 'department', sort_order = :sort_order
                WHERE name = :name
            """), {'name': name, 'sort_order': idx * 10})

        # Create neighborhood (동) records
        neighborhoods = [
            # 1권역
            ('SINSA', '신사동', 'ZONE_1', 10),
            ('NONHYEON1', '논현1동', 'ZONE_1', 20),
            ('NONHYEON2', '논현2동', 'ZONE_1', 30),
            ('APGUJEONG', '압구정동', 'ZONE_1', 40),
            ('CHEONGDAM', '청담동', 'ZONE_1', 50),
            # 2권역
            ('SAMSUNG1', '삼성1동', 'ZONE_2', 10),
            ('SAMSUNG2', '삼성2동', 'ZONE_2', 20),
            ('DAECHI1', '대치1동', 'ZONE_2', 30),
            ('DAECHI2', '대치2동', 'ZONE_2', 40),
            ('DAECHI4', '대치4동', 'ZONE_2', 50),
            # 3권역
            ('YEOKSAM1', '역삼1동', 'ZONE_3', 10),
            ('YEOKSAM2', '역삼2동', 'ZONE_3', 20),
            ('DOGOK1', '도곡1동', 'ZONE_3', 30),
            ('DOGOK2', '도곡2동', 'ZONE_3', 40),
            ('GAEPO1', '개포1동', 'ZONE_3', 50),
            ('GAEPO2', '개포2동', 'ZONE_3', 60),
            # 4권역
            ('GAEPO3', '개포3동', 'ZONE_4', 10),
            ('GAEPO4', '개포4동', 'ZONE_4', 20),
            ('IRWONBON', '일원본동', 'ZONE_4', 30),
            ('IRWON1', '일원1동', 'ZONE_4', 40),
            ('SUSEO', '수서동', 'ZONE_4', 50),
            ('SEGOK', '세곡동', 'ZONE_4', 60),
        ]

        for code, name, parent_code, sort_order in neighborhoods:
            await db.execute(text("""
                INSERT INTO departments (code, name, parent_code, department_type, sort_order, created_at, updated_at)
                VALUES (:code, :name, :parent_code, 'neighborhood', :sort_order, :now, :now)
                ON CONFLICT (code) DO UPDATE SET
                    parent_code = EXCLUDED.parent_code,
                    department_type = EXCLUDED.department_type,
                    sort_order = EXCLUDED.sort_order
            """), {
                'code': code,
                'name': name,
                'parent_code': parent_code,
                'sort_order': sort_order,
                'now': datetime.utcnow()
            })

        await db.commit()
        return {
            "message": "Data seeding completed",
            "bureaus_created": len(bureaus),
            "zones_created": len(zones),
            "neighborhoods_created": len(neighborhoods)
        }
    except Exception as e:
        await db.rollback()
        return {"error": str(e)}
