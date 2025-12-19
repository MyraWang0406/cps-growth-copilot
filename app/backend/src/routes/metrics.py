"""Metrics endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..analytics import get_taoke_metrics, get_merchant_metrics
from ..schemas import MetricsResponse

router = APIRouter()


@router.get("/metrics/taoke/{taoke_id}", response_model=MetricsResponse)
async def get_taoke_metrics_endpoint(
    taoke_id: int,
    window: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    """Get metrics for a taoke."""
    if window not in ["7d", "14d", "30d"]:
        raise HTTPException(status_code=400, detail="Window must be 7d, 14d, or 30d")

    metrics = await get_taoke_metrics(db, taoke_id, window)
    return MetricsResponse(**metrics)


@router.get("/metrics/merchant/{merchant_id}", response_model=MetricsResponse)
async def get_merchant_metrics_endpoint(
    merchant_id: int,
    window: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    """Get metrics for a merchant."""
    if window not in ["7d", "30d"]:
        raise HTTPException(status_code=400, detail="Window must be 7d or 30d")

    metrics = await get_merchant_metrics(db, merchant_id, window)
    return MetricsResponse(**metrics)

