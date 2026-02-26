"""
Health check endpoints for monitoring.
"""

from fastapi import APIRouter, status
import datetime

router = APIRouter()


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "service": "DealLens AI API"
    }


@router.get("/ping")
async def ping():
    """Simple ping endpoint for connectivity testing."""
    return {"ping": "pong"}