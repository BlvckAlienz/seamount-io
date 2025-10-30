# File: backend/api/routes/wallet_recovery.py
# 🛡️ SAFE WALLET RECOVERY ROUTE

from fastapi import APIRouter, HTTPException, Depends
from backend.services.database_service import DatabaseService, get_db_service
from backend.services.wallet_recovery_service import SafeRecoveryService
from backend.auth.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/recovery-seeds")
async def get_recovery_seeds(
    current_user: dict = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Safe wallet recovery endpoint - works with any table structure
    """
    try:
        recovery_service = SafeRecoveryService(db_service)
        result = await recovery_service.recover_wallet_seeds(current_user.id)
        
        if not result["success"]:
            # Return 200 with error details for frontend handling
            return result
        
        return result
        
    except Exception as e:
        logger.error(f"Wallet recovery route failed for {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Wallet recovery service temporarily unavailable"
        )

@router.get("/recovery-readiness")
async def check_recovery_readiness(
    current_user: dict = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """Check if user is ready for wallet recovery"""
    try:
        recovery_service = SafeRecoveryService(db_service)
        return await recovery_service.check_recovery_readiness(current_user.id)
    except Exception as e:
        logger.error(f"Recovery readiness check failed: {str(e)}")
        return {
            "user_id": current_user.id,
            "user_ready": False,
            "recovery_ready": False,
            "error": str(e)
        }

@router.get("/test")
async def test_wallet_recovery():
    """Test endpoint to verify route is working"""
    return {
        "success": True,
        "message": "✅ Wallet recovery route is working!",
        "endpoint": "/api/v1/wallet/recovery-seeds", 
        "timestamp": "2024-01-01T00:00:00Z"
    }