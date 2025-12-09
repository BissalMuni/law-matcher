"""
Law Matcher - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
