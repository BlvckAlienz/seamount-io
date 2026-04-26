# FILE: backend/api/routes/circle_swap_routes.py
"""
Circle App Kit — Swap Routes (same-chain USDC ↔ EURC ↔ tokens)
POST /api/v1/circle/swap/estimate
POST /api/v1/circle/swap
GET  /api/v1/circle/swap/chains
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from backend.dependencies import get_current_user, get_db_service
from backend.services.circle_appkit_service import CircleAppKitService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/circle", tags=["Circle App Kit"])


def get_circle_service(db=Depends(get_db_service)) -> CircleAppKitService:
    return CircleAppKitService(db)


class SwapEstimateRequest(BaseModel):
    chain:     str = Field(..., description="e.g. 'Arc_Testnet', 'Ethereum', 'Polygon'")
    token_in:  str = Field(..., description="e.g. 'USDC', 'EURC', 'NATIVE'")
    token_out: str = Field(..., description="e.g. 'EURC', 'USDC'")
    amount_in: str = Field(..., description="Human-readable amount e.g. '10.00'")


class CircleSwapRequest(SwapEstimateRequest):
    slippage_bps: int            = Field(default=300,  description="Slippage in bps, default 3%")
    stop_limit:   Optional[str]  = Field(default=None, description="Min output amount")


@router.post("/swap/estimate")
async def estimate_swap(
    request: SwapEstimateRequest,
    current_user: dict = Depends(get_current_user),
    svc: CircleAppKitService = Depends(get_circle_service),
):
    """Preview Circle App Kit swap output + fee breakdown."""
    try:
        result = await svc.estimate_swap(
            user_id   = current_user["id"],
            chain     = request.chain,
            token_in  = request.token_in,
            token_out = request.token_out,
            amount_in = request.amount_in,
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Estimate failed"))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Swap estimate failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/swap")
async def execute_swap(
    request: CircleSwapRequest,
    current_user: dict = Depends(get_current_user),
    svc: CircleAppKitService = Depends(get_circle_service),
):
    """
    Execute Circle App Kit same-chain token swap.
    Seamount 0.5% fee (50 bps) auto-collected on-chain.
    Requires CIRCLE_KIT_KEY in server environment.
    """
    try:
        result = await svc.swap_tokens(
            user_id      = current_user["id"],
            chain        = request.chain,
            token_in     = request.token_in,
            token_out    = request.token_out,
            amount_in    = request.amount_in,
            slippage_bps = request.slippage_bps,
            stop_limit   = request.stop_limit,
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Swap failed"))
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Circle swap failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/swap/chains")
async def get_swap_chains(svc: CircleAppKitService = Depends(get_circle_service)):
    """Chains that support Circle App Kit swap (requires Kit Key)."""
    try:
        return await svc.get_supported_chains(operation_type="swap")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))