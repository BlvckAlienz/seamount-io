# 📍 FILE: backend/api/routes/swap_routes.py
"""
Swap Routes - Pact Finance DEX Integration
MainNet Production
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Dict, Any

from backend.dependencies import (
    get_current_user,
    get_multi_chain_wallet_service,
    get_database_service
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/swap", tags=["Swap"])

# ========== REQUEST/RESPONSE MODELS ==========

class SwapQuoteRequest(BaseModel):
    from_asset: str = Field(..., description="Source asset symbol")
    to_asset: str = Field(..., description="Destination asset symbol")
    amount: float = Field(..., gt=0, description="Amount to swap")

class SwapExecuteRequest(BaseModel):
    from_asset: str
    to_asset: str
    amount: float = Field(..., gt=0)

# ========== ROUTES ==========

@router.post("/quote")
async def get_swap_quote(
    request: SwapQuoteRequest,
    current_user: Dict = Depends(get_current_user),
    wallet_service = Depends(get_multi_chain_wallet_service)
):
    """
    Get real-time swap quote from Pact DEX (MainNet)
    """
    try:
        logger.info(
            f"Swap quote: {request.amount} {request.from_asset} â†' {request.to_asset}"
        )
        
        # Get quote from swap service
        from backend.services.swap_service import SwapService
        from backend.config import get_settings
        
        settings = get_settings()
        swap_service = SwapService(
            settings=settings,
            algorand_service=wallet_service.algorand_service,
            db_service=wallet_service.db_service,
            wallet_service=wallet_service,
            revenue_service=wallet_service.revenue_service
        )
        
        quote = await swap_service.get_swap_quote(
            from_asset=request.from_asset,
            to_asset=request.to_asset,
            amount=Decimal(str(request.amount))
        )
        
        return {
            "success": True,
            **quote
        }
        
    except Exception as e:
        logger.error(f"Swap quote failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get quote: {str(e)}"
        )

@router.post("/execute")
async def execute_swap(
    request: SwapExecuteRequest,
    current_user: Dict = Depends(get_current_user),
    wallet_service = Depends(get_multi_chain_wallet_service),
    db_service = Depends(get_database_service)
):
    """
    Execute swap on Pact DEX (MainNet)
    
    🚨 REQUIRES: User wallet with sufficient balance
    """
    try:
        logger.info(
            f"Executing swap: {request.amount} {request.from_asset} â†' "
            f"{request.to_asset} for user {current_user['id']}"
        )
        
        # Initialize swap service
        from backend.services.swap_service import SwapService
        from backend.config import get_settings
        
        settings = get_settings()
        swap_service = SwapService(
            settings=settings,
            algorand_service=wallet_service.algorand_service,
            db_service=db_service,
            wallet_service=wallet_service,
            revenue_service=wallet_service.revenue_service
        )
        
        # Execute swap
        result = await swap_service.execute_swap(
            user_id=current_user["id"],
            from_asset=request.from_asset,
            to_asset=request.to_asset,
            amount=Decimal(str(request.amount))
        )
        
        logger.info(f"âœ… Swap successful: {result['tx_id']}")
        
        return {
            "success": True,
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Swap execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Swap failed: {str(e)}"
        )

@router.get("/health")
async def swap_health():
    """Health check for swap service"""
    return {
        "status": "healthy",
        "service": "swap",
        "dex": "pact_finance_mainnet"
    }