# FILE: backend/api/routes/circle_bridge_routes.py
"""
Circle App Kit — Bridge Routes (CCTP cross-chain USDC transfer)
POST /api/v1/circle/bridge/estimate
POST /api/v1/circle/bridge
POST /api/v1/circle/bridge/retry
GET  /api/v1/circle/bridge/chains
GET  /api/v1/circle/bridge/health
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal

from backend.dependencies import get_current_user, get_db_service
from backend.services.circle_appkit_service import CircleAppKitService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/circle", tags=["Circle App Kit"])


# ── Dependency ────────────────────────────────────────────────────────────────
def get_circle_service(db=Depends(get_db_service)) -> CircleAppKitService:
    return CircleAppKitService(db)


# ── Request models ────────────────────────────────────────────────────────────
class BridgeEstimateRequest(BaseModel):
    from_chain: str = Field(..., description="e.g. 'Ethereum', 'Polygon', 'Solana'")
    to_chain:   str = Field(..., description="e.g. 'Base', 'Arbitrum', 'Ethereum'")
    amount:     str = Field(..., description="Human-readable USDC e.g. '100.00'")


class BridgeRequest(BridgeEstimateRequest):
    recipient_address: Optional[str] = None
    transfer_speed:    str = Field(default="FAST", description="FAST | SLOW")
    use_forwarder:     bool = Field(default=False, description="Circle Forwarding Service")


class BridgeRetryRequest(BaseModel):
    bridge_result: dict = Field(..., description="BridgeResult object from a failed bridge call")


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/circle/bridge/estimate
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/bridge/estimate")
async def estimate_bridge(
    request: BridgeEstimateRequest,
    current_user: dict = Depends(get_current_user),
    svc: CircleAppKitService = Depends(get_circle_service),
):
    """
    Returns fee breakdown before the user confirms a bridge.
    Show seamount_fee, CCTP protocol fee, and gas fees in the UI.
    """
    try:
        result = await svc.estimate_bridge(
            user_id    = current_user["id"],
            from_chain = request.from_chain,
            to_chain   = request.to_chain,
            amount     = request.amount,
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Estimate failed"))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Bridge estimate failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bridge estimate failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/circle/bridge
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/bridge")
async def execute_bridge(
    request: BridgeRequest,
    current_user: dict = Depends(get_current_user),
    svc: CircleAppKitService = Depends(get_circle_service),
):
    """
    Execute CCTP cross-chain USDC bridge.
    Seamount 0.5% fee is collected on-chain automatically.
    Bridge steps: approve → burn → attestation → mint (can take 2-20 min on FAST).
    """
    try:
        # Input guard — minimum viable amount
        amount_dec = Decimal(str(request.amount))
        if amount_dec < Decimal("1.00"):
            raise HTTPException(status_code=400, detail="Minimum bridge amount is 1.00 USDC")

        result = await svc.bridge_usdc(
            user_id           = current_user["id"],
            from_chain        = request.from_chain,
            to_chain          = request.to_chain,
            amount            = request.amount,
            recipient_address = request.recipient_address,
            transfer_speed    = request.transfer_speed,
            use_forwarder     = request.use_forwarder,
        )

        if not result.get("success") and result.get("state") not in ("pending", "success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Bridge failed"))

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Bridge execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bridge failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/circle/bridge/retry
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/bridge/retry")
async def retry_bridge(
    request: BridgeRetryRequest,
    current_user: dict = Depends(get_current_user),
    svc: CircleAppKitService = Depends(get_circle_service),
):
    """
    Resume a partial bridge. Pass the BridgeResult from the failed attempt.
    Handles: burn succeeded, mint failed (network timeout, etc.)
    """
    try:
        result = await svc.retry_bridge(
            user_id       = current_user["id"],
            bridge_result = request.bridge_result,
        )
        return result
    except Exception as e:
        logger.error(f"Bridge retry failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/circle/bridge/chains
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/bridge/chains")
async def get_bridge_chains(svc: CircleAppKitService = Depends(get_circle_service)):
    """Returns all chains that support CCTP bridging."""
    try:
        return await svc.get_supported_chains(operation_type="bridge")
    except Exception as e:
        logger.error(f"get_bridge_chains failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/circle/bridge/health
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/bridge/health")
async def bridge_health(svc: CircleAppKitService = Depends(get_circle_service)):
    try:
        return await svc.health_check()
    except Exception as e:
        return {"success": False, "status": "unhealthy", "error": str(e)}