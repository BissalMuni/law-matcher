"""
Common schemas
"""
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response"""
    total: int
    page: int
    size: int
    items: List[T]
