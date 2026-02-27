"""
Law Matcher - FastAPI Application Entry Point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import redis.asyncio as aioredis

from backend.api.v1.router import api_router
from backend.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="자치법규 개정 검토 시스템",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAINTENANCE_KEY = "law_matcher:maintenance_mode"

# 점검모드에서도 허용되는 경로
MAINTENANCE_BYPASS_PATHS = [
    "/health",
    f"{settings.API_V1_PREFIX}/admin/maintenance",
    f"{settings.API_V1_PREFIX}/auth/login",
]


class MaintenanceMiddleware(BaseHTTPMiddleware):
    """점검모드 미들웨어 - 활성화 시 허용된 경로 외 503 반환"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 허용된 경로는 점검모드와 무관하게 통과
        if any(path.startswith(bp) for bp in MAINTENANCE_BYPASS_PATHS):
            return await call_next(request)

        # Redis에서 점검모드 상태 확인
        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            enabled = await r.get(MAINTENANCE_KEY)
            await r.aclose()
        except Exception:
            # Redis 연결 실패 시 점검모드 체크를 건너뜀
            return await call_next(request)

        if enabled == "1":
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "시스템 정비 중입니다.",
                    "maintenance": True,
                },
            )

        return await call_next(request)


app.add_middleware(MaintenanceMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
