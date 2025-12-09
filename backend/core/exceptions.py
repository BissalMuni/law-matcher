"""
Custom exceptions and error handlers
"""
from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    """Resource not found"""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestError(HTTPException):
    """Bad request"""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ExternalAPIError(HTTPException):
    """External API error (MOLEG API)"""
    def __init__(self, detail: str = "External API error"):
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


class SyncInProgressError(HTTPException):
    """Sync already in progress"""
    def __init__(self, detail: str = "Sync already in progress"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
