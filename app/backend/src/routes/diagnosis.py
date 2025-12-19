"""Diagnosis endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..analytics import get_taoke_metrics, get_merchant_metrics
from ..schemas import DiagnosisReport
from ..llm.fake_llm import FakeLLM
from datetime import datetime

router = APIRouter()
llm = FakeLLM()


@router.get("/diagnosis/taoke/{taoke_id}", response_model=DiagnosisReport)
async def get_taoke_diagnosis(
    taoke_id: int,
    window: str = "14d",
    db: AsyncSession = Depends(get_db),
):
    """Get diagnosis for a taoke."""
    if window not in ["7d", "14d", "30d"]:
        raise HTTPException(status_code=400, detail="Window must be 7d, 14d, or 30d")

    metrics = await get_taoke_metrics(db, taoke_id, window)
    diagnosis = await llm.generate_diagnosis("taoke", taoke_id, metrics, window)
    
    # Convert datetime string to datetime object
    diagnosis["generated_at"] = datetime.fromisoformat(diagnosis["generated_at"])
    
    return DiagnosisReport(**diagnosis)


@router.get("/diagnosis/merchant/{merchant_id}", response_model=DiagnosisReport)
async def get_merchant_diagnosis(
    merchant_id: int,
    window: str = "30d",
    db: AsyncSession = Depends(get_db),
):
    """Get diagnosis for a merchant."""
    if window not in ["7d", "30d"]:
        raise HTTPException(status_code=400, detail="Window must be 7d or 30d")

    metrics = await get_merchant_metrics(db, merchant_id, window)
    diagnosis = await llm.generate_diagnosis("merchant", merchant_id, metrics, window)
    
    # Convert datetime string to datetime object
    diagnosis["generated_at"] = datetime.fromisoformat(diagnosis["generated_at"])
    
    return DiagnosisReport(**diagnosis)

