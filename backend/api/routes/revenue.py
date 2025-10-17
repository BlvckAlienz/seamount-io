# File: backend/api/routes/revenue.py
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta

from backend.dependencies import get_db_service

router = APIRouter(prefix="/revenue", tags=["Revenue Analytics"])

@router.get("/dashboard")
async def get_revenue_dashboard(
    days: int = 30,
    db_service = Depends(get_db_service)
):
    """Comprehensive revenue dashboard"""
    
    query = """
        SELECT 
            source,
            COUNT(*) as transaction_count,
            SUM(amount) as total_revenue
        FROM revenue
        WHERE timestamp >= NOW() - INTERVAL '%s days'
        GROUP BY source
    """
    
    results = await db_service.execute_query(query, (days,))
    
    breakdown = {}
    total_revenue = 0
    
    for row in results:
        breakdown[row["source"]] = {
            "transactions": row["transaction_count"],
            "revenue": float(row["total_revenue"])
        }
        total_revenue += float(row["total_revenue"])
    
    return {
        "period_days": days,
        "total_revenue": total_revenue,
        "breakdown": breakdown,
        "revenue_streams": {
            "onramp_fees": breakdown.get("onramp_fee", {}).get("revenue", 0),
            "offramp_fees": breakdown.get("offramp_fee", {}).get("revenue", 0),
            "yield_management": breakdown.get("yield_management_fees", {}).get("revenue", 0),
            "cross_border_fees": breakdown.get("cross_border_fee", {}).get("revenue", 0)
        }
    }