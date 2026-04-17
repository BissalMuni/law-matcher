"""
Admin API endpoints for management tasks
"""
import os
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional

import redis.asyncio as aioredis

from backend.api.deps import get_db, get_current_user, verify_admin_password
from backend.core.config import settings
from backend.core.llm_models import AVAILABLE_MODELS
from backend.models.user import User
from backend.models.llm_provider import LlmProvider
from backend.models.sync_settings import SyncSettings
from backend.schemas.llm import (
    AvailableModel,
    LlmProviderResponse,
    LlmProviderListResponse,
    LlmProviderUpdate,
    AiAnalyticsResponse,
)
from backend.schemas.sync_settings import SyncSettingsResponse, SyncSettingsUpdate

router = APIRouter()

MAINTENANCE_KEY = "law_matcher:maintenance_mode"


async def get_redis():
    """Get async Redis connection"""
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


class MaintenanceToggleRequest(BaseModel):
    enabled: bool
    message: Optional[str] = None


@router.get("/maintenance")
async def get_maintenance_status():
    """점검모드 상태 조회 (인증 불필요)"""
    r = await get_redis()
    try:
        enabled = await r.get(MAINTENANCE_KEY)
        message = await r.get(f"{MAINTENANCE_KEY}:message")
        return {
            "enabled": enabled == "1",
            "message": message or "시스템 정비 중입니다. 잠시 후 다시 접속해 주세요.",
        }
    finally:
        await r.aclose()


@router.post("/maintenance")
async def toggle_maintenance(
    request: MaintenanceToggleRequest,
    _: bool = Depends(verify_admin_password),
):
    """점검모드 ON/OFF 토글 (관리자 비밀번호 필요)"""
    r = await get_redis()
    try:
        if request.enabled:
            await r.set(MAINTENANCE_KEY, "1")
            if request.message:
                await r.set(f"{MAINTENANCE_KEY}:message", request.message)
        else:
            await r.delete(MAINTENANCE_KEY)
            await r.delete(f"{MAINTENANCE_KEY}:message")

        return {
            "enabled": request.enabled,
            "message": "점검모드가 활성화되었습니다." if request.enabled else "점검모드가 해제되었습니다.",
        }
    finally:
        await r.aclose()


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


# ==================== LLM 프로바이더 관리 (006-llm-review-assistant) ====================


@router.get("/llm-providers", response_model=LlmProviderListResponse)
async def get_llm_providers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """LLM 프로바이더 목록 조회 (관리자 전용). API 키 존재 여부만 마스킹 표시."""
    result = await db.execute(
        select(LlmProvider).order_by(LlmProvider.id)
    )
    providers = list(result.scalars().all())

    items = []
    for p in providers:
        env_key = bool(os.getenv(p.api_key_env_name, ""))
        db_key = bool(p.api_key)
        api_key_configured = env_key or db_key
        api_key_source = "env" if env_key else ("db" if db_key else "none")

        # 프로바이더별 사용 가능한 모델 목록
        models = [
            AvailableModel(**m)
            for m in AVAILABLE_MODELS.get(p.provider_name, [])
        ]

        items.append(LlmProviderResponse(
            id=p.id,
            provider_name=p.provider_name,
            display_name=p.display_name,
            model_name=p.model_name,
            api_key_env_name=p.api_key_env_name,
            api_key_configured=api_key_configured,
            api_key_source=api_key_source,
            is_active=p.is_active,
            rate_limit_per_minute=p.rate_limit_per_minute,
            available_models=models,
            updated_at=p.updated_at,
        ))

    return LlmProviderListResponse(providers=items)


@router.patch("/llm-providers/{provider_id}", response_model=LlmProviderResponse)
async def update_llm_provider(
    provider_id: int,
    body: LlmProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """LLM 프로바이더 설정 변경 (모델명/활성 상태/Rate Limit)"""
    result = await db.execute(
        select(LlmProvider).where(LlmProvider.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="프로바이더를 찾을 수 없습니다")

    # API 키 업데이트 (DB 저장)
    if body.api_key is not None:
        provider.api_key = body.api_key if body.api_key else None

    # 활성화 시 API 키 존재 검증 (env 또는 DB)
    if body.is_active is True:
        env_key = os.getenv(provider.api_key_env_name, "")
        db_key = provider.api_key
        if not env_key and not db_key:
            raise HTTPException(
                status_code=400,
                detail=f"API 키가 설정되지 않았습니다. 환경변수({provider.api_key_env_name}) 또는 DB에서 API 키를 먼저 설정하세요.",
            )
        # 기존 활성 프로바이더 비활성화 (동시 1개만 active)
        await db.execute(
            text("UPDATE llm_providers SET is_active = FALSE WHERE is_active = TRUE AND id != :id"),
            {"id": provider_id},
        )

    if body.model_name is not None:
        provider.model_name = body.model_name
    if body.is_active is not None:
        provider.is_active = body.is_active
    if body.rate_limit_per_minute is not None:
        provider.rate_limit_per_minute = body.rate_limit_per_minute

    provider.updated_at = datetime.utcnow()
    await db.commit()

    env_key = bool(os.getenv(provider.api_key_env_name, ""))
    db_key = bool(provider.api_key)
    api_key_configured = env_key or db_key
    api_key_source = "env" if env_key else ("db" if db_key else "none")

    models = [
        AvailableModel(**m)
        for m in AVAILABLE_MODELS.get(provider.provider_name, [])
    ]

    return LlmProviderResponse(
        id=provider.id,
        provider_name=provider.provider_name,
        display_name=provider.display_name,
        model_name=provider.model_name,
        api_key_env_name=provider.api_key_env_name,
        api_key_configured=api_key_configured,
        api_key_source=api_key_source,
        is_active=provider.is_active,
        rate_limit_per_minute=provider.rate_limit_per_minute,
        available_models=models,
        updated_at=provider.updated_at,
    )


@router.get("/ai-analytics")
async def get_ai_analytics(
    start_date: Optional[str] = Query(None, description="시작일 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료일 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 분석 이력/통계 (관리자 전용)"""
    from backend.services.llm_analysis_service import LlmAnalysisService

    now = datetime.utcnow()
    start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else now - timedelta(days=30)
    end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) if end_date else now

    service = LlmAnalysisService(db)
    return await service.get_ai_analytics(start, end)


async def _get_or_create_sync_settings(db: AsyncSession) -> SyncSettings:
    result = await db.execute(select(SyncSettings).where(SyncSettings.id == 1))
    settings_row = result.scalar_one_or_none()
    if settings_row is None:
        settings_row = SyncSettings(id=1, auto_sync_enabled=False, interval_hours=24)
        db.add(settings_row)
        await db.commit()
        await db.refresh(settings_row)
    return settings_row


@router.get("/sync-settings", response_model=SyncSettingsResponse)
async def get_sync_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """법령 자동 동기화 설정 조회 (관리자)"""
    row = await _get_or_create_sync_settings(db)
    return SyncSettingsResponse(
        auto_sync_enabled=row.auto_sync_enabled,
        interval_hours=row.interval_hours,
        last_sync_at=row.last_sync_at,
        next_sync_at=row.next_sync_at,
        updated_at=row.updated_at,
        updated_by=row.updated_by,
    )


@router.patch("/sync-settings", response_model=SyncSettingsResponse)
async def update_sync_settings(
    body: SyncSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """법령 자동 동기화 설정 변경 (관리자)"""
    row = await _get_or_create_sync_settings(db)
    now = datetime.utcnow()

    if body.auto_sync_enabled is not None:
        row.auto_sync_enabled = body.auto_sync_enabled
    if body.interval_hours is not None:
        row.interval_hours = body.interval_hours

    if row.auto_sync_enabled:
        base = row.last_sync_at or now
        row.next_sync_at = base + timedelta(hours=row.interval_hours)
    else:
        row.next_sync_at = None

    row.updated_at = now
    row.updated_by = current_user.id
    await db.commit()
    await db.refresh(row)

    return SyncSettingsResponse(
        auto_sync_enabled=row.auto_sync_enabled,
        interval_hours=row.interval_hours,
        last_sync_at=row.last_sync_at,
        next_sync_at=row.next_sync_at,
        updated_at=row.updated_at,
        updated_by=row.updated_by,
    )
