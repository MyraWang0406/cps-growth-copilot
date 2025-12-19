"""Recommendation API router."""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.services.recommender import Recommender
from app.storage.db import Database
from app.core.guardrails import Guardrails

router = APIRouter()

# Initialize dependencies (in production, use dependency injection)
_db = None
_guardrails = None
_recommender = None


def get_db():
    """Get database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db


def get_guardrails():
    """Get guardrails instance."""
    global _guardrails
    if _guardrails is None:
        _guardrails = Guardrails()
    return _guardrails


def get_recommender():
    """Get recommender instance."""
    global _recommender
    if _recommender is None:
        _recommender = Recommender(get_db(), get_guardrails())
    return _recommender


@router.get("/recommend")
async def recommend(
    q: Optional[str] = Query(None, description="Search query (optional)"),
    top_n: int = Query(10, ge=1, le=100, description="Number of recommendations"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, alias="price_min", description="Minimum price filter"),
    max_price: Optional[float] = Query(None, alias="price_max", description="Maximum price filter"),
):
    """
    Get product recommendations with scoring, guardrails, reasons, and commission.
    
    - **q**: Optional search query (searches in product titles)
    - **top_n**: Number of recommendations to return (1-100)
    - **category**: Optional category filter (e.g., "All_Beauty", "Electronics")
    - **min_price**: Optional minimum price filter
    - **max_price**: Optional maximum price filter
    
    Returns items with:
    - score: Recommendation score
    - reasons: 2-3 explainable reasons
    - risk_flags: Any guardrail violations
    - commission_rate: Simulated commission rate
    - estimated_commission: Simulated commission amount
    """
    try:
        recommender = get_recommender()
        result = recommender.recommend(
            query=q,
            top_n=top_n,
            category=category,
            price_min=min_price,
            price_max=max_price
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")

