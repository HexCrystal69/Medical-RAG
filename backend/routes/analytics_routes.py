"""
FastAPI Routes — System Analytics
==================================
Returns statistical data for latency charts, topic counts, and reference rates.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("")
async def get_system_analytics():
    """Retrieve statistical performance logs for the dashboard."""
    from main import get_tracker
    try:
        tracker = get_tracker()
        return tracker.get_analytics_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch system analytics data: {exc}")
