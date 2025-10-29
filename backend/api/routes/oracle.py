from fastapi import APIRouter, HTTPException, Depends
from backend.services.oracle_service import EnhancedOracleService
from backend.services.database_service import DatabaseService
from backend.dependencies import get_db_service, get_oracle_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1")

@router.get("/oracle/price/{asset_name}")
async def get_asset_price(asset_name: str):
    """Get real-time asset price from 3-tier oracle system"""
    try:
        # Try to get oracle service from dependencies first
        try:
            oracle_service = get_oracle_service()
        except:
            # Fallback: create new instance
            db_service = get_db_service()
            oracle_service = EnhancedOracleService(db_service)
        
        price, metadata = await oracle_service.get_asset_price(asset_name)
        
        return {
            "price": str(price),
            "metadata": metadata,
            "asset": asset_name,
            "success": True
        }
    except Exception as e:
        logger.error(f"Oracle price fetch failed for {asset_name}: {e}")
        
        # Return cached/fallback data instead of failing
        fallback_prices = {
            'bitcoin': '63500.00',
            'ethereum': '2650.00',
            'algorand': '0.18'
        }
        
        fallback_price = fallback_prices.get(asset_name.lower(), '0.00')
        
        return {
            "price": fallback_price,
            "metadata": {
                "source": "fallback",
                "timestamp": "2025-10-08T00:00:00Z",
                "confidence": 0.5,
                "error": str(e),
                "warning": "Using fallback data - oracle service unavailable"
            },
            "asset": asset_name,
            "success": False
        }

@router.get("/oracle/health")
async def oracle_health():
    """Check oracle service health"""
    try:
        oracle_service = get_oracle_service()
        health_status = await oracle_service.get_health_status()
        return {"status": "healthy", "details": health_status}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}