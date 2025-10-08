from fastapi import APIRouter, HTTPException
from backend.services.oracle_service import EnhancedOracleService
from backend.services.database_service import DatabaseService

router = APIRouter()

@router.get("/oracle/price/{asset_name}")
async def get_asset_price(asset_name: str):
    try:
        db_service = DatabaseService()
        oracle_service = EnhancedOracleService(db_service)
        
        price, metadata = await oracle_service.get_asset_price(asset_name)
        
        return {
            "price": str(price),
            "metadata": metadata,
            "asset": asset_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))