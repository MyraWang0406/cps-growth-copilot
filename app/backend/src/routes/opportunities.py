"""Opportunities endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..analytics import get_taoke_metrics, get_merchant_metrics
from ..schemas import OpportunitiesResponse
from ..llm.fake_llm import FakeLLM

router = APIRouter()
llm = FakeLLM()


@router.get("/opportunities/taoke/{taoke_id}", response_model=OpportunitiesResponse)
async def get_taoke_opportunities(
    taoke_id: int,
    window: str = "14d",
    db: AsyncSession = Depends(get_db),
):
    """Get opportunities for a taoke."""
    if window not in ["7d", "14d", "30d"]:
        raise HTTPException(status_code=400, detail="Window must be 7d, 14d, or 30d")

    metrics = await get_taoke_metrics(db, taoke_id, window)
    opportunities = await llm.generate_opportunities("taoke", taoke_id, metrics, window)
    return OpportunitiesResponse(**opportunities)


@router.get("/opportunities/merchant/{merchant_id}", response_model=OpportunitiesResponse)
async def get_merchant_opportunities(
    merchant_id: int,
    window: str = "30d",
    db: AsyncSession = Depends(get_db),
):
    """Get opportunities for a merchant."""
    if window not in ["7d", "30d"]:
        raise HTTPException(status_code=400, detail="Window must be 7d or 30d")

    metrics = await get_merchant_metrics(db, merchant_id, window)
    opportunities = await llm.generate_opportunities("merchant", merchant_id, metrics, window)
    return OpportunitiesResponse(**opportunities)

