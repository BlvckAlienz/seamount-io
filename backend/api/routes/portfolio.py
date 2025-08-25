from fastapi import APIRouter, Depends, HTTPException
from auth_dependency import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/portfolio/summary")
async def get_portfolio_summary(current_user: dict = Depends(get_current_user)):
    try:
        logger.info(f"Fetching portfolio summary for user: {current_user['id']}")
        
        # Return mock data for now - implement real logic later
        return {
            "total_balance": 0.0,
            "usds_balance": 0.0,
            "day_change": 0.0,
            "total_pnl": 0.0,
            "assets": []
        }
    except Exception as e:
        logger.error(f"Error fetching portfolio summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching portfolio data")