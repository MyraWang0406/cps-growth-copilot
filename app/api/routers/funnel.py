"""Funnel analysis API router."""
from fastapi import APIRouter, Query, HTTPException
from app.services.funnel import FunnelAnalyzer
from app.storage.db import Database

router = APIRouter()

# Initialize dependencies
_db = None
_funnel_analyzer = None


def get_db():
    """Get database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db


def get_funnel_analyzer():
    """Get funnel analyzer instance."""
    global _funnel_analyzer
    if _funnel_analyzer is None:
        _funnel_analyzer = FunnelAnalyzer(get_db())
    return _funnel_analyzer


@router.get("/funnel/diagnose")
async def diagnose_funnel(
    item_id: str = Query(..., description="Item ID to analyze"),
    lookback_days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
):
    """
    Diagnose funnel metrics for an item.
    
    - **item_id**: Item ID to analyze
    - **lookback_days**: Number of days to look back (1-90)
    
    Returns funnel metrics, drop-off points, and recommendations.
    """
    try:
        analyzer = get_funnel_analyzer()
        result = analyzer.diagnose(item_id, lookback_days)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["message"])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Funnel analysis error: {str(e)}")


