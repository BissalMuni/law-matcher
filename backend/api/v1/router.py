"""
API v1 Router - Aggregates all endpoint routers
"""
from fastapi import APIRouter

from backend.api.v1 import ordinances, sync, amendments, reviews, dashboard, departments, laws

api_router = APIRouter()

api_router.include_router(
    departments.router,
    prefix="/departments",
    tags=["departments"]
)

api_router.include_router(
    laws.router,
    prefix="/laws",
    tags=["laws"]
)

api_router.include_router(
    ordinances.router,
    prefix="/ordinances",
    tags=["ordinances"]
)

api_router.include_router(
    sync.router,
    prefix="/sync",
    tags=["sync"]
)

api_router.include_router(
    amendments.router,
    prefix="/amendments",
    tags=["amendments"]
)

api_router.include_router(
    reviews.router,
    prefix="/reviews",
    tags=["reviews"]
)

api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"]
)
