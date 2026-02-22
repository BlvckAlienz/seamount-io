# File: backend/api/routes/xrp_yield_routes.py
"""
XRP Yield Routes — Seamount.io Phase 3

GET  /xrp/yield/pools              → available pools + live stats
GET  /xrp/yield/positions          → user's active yield positions
POST /xrp/yield/deposit            → deposit into AMM pool
POST /xrp/yield/withdraw           → withdraw from AMM position
GET  /xrp/yield/history            → yield credit history
POST /xrp/yield/distribute         → admin: trigger daily distribution
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from backend.dependencies import get_current_user, get_supabase_client
from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/xrp/yield", tags=["XRP Yield Farming"])

SUPPORTED_POOLS = ["RLUSD/XRP", "USDC/XRP"]


# ─── Pydantic Models ───────────────────────────────────────────────────────────

class DepositRequest(BaseModel):
    pool: str
    amount: str  # string to preserve decimal precision

    @field_validator("pool")
    @classmethod
    def validate_pool(cls, v):
        if v not in ["RLUSD/XRP", "USDC/XRP"]:
            raise ValueError("Pool must be one of: RLUSD/XRP, USDC/XRP")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        try:
            d = Decimal(v)
            if d <= 0:
                raise ValueError("Amount must be greater than zero")
            return v
        except InvalidOperation:
            raise ValueError("Invalid amount format")


class WithdrawRequest(BaseModel):
    position_id: str

    @field_validator("position_id")
    @classmethod
    def validate_position_id(cls, v):
        if not v or len(v) < 5:
            raise ValueError("Invalid position_id")
        return v


# ─── Dependency: Yield Service ────────────────────────────────────────────────

def get_yield_service(
    supabase=Depends(get_supabase_client),
    settings=Depends(get_settings),
):
    try:
        from backend.services.xrp_service import XRPService
        from backend.services.xrp_defi_service import XRPDeFiService
        from backend.services.xrp_payment_service import XRPPaymentService
        from backend.services.xrp_yield_service import XRPYieldService

        xrp_svc = XRPService(settings=settings)
        defi_svc = XRPDeFiService(xrp_service=xrp_svc, settings=settings)
        payment_svc = XRPPaymentService(
            supabase_client=supabase,
            xrp_service=xrp_svc,
            settings=settings,
        )
        return XRPYieldService(
            supabase_client=supabase,
            xrp_defi_service=defi_svc,
            xrp_payment_service=payment_svc,
            settings=settings,
        )
    except Exception as e:
        logger.error(f"❌ Failed to init XRPYieldService: {e}")
        raise HTTPException(status_code=503, detail="Yield service unavailable")


def require_admin(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin") and current_user.get("role") != "tribe":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/pools")
async def get_pools(
    current_user: dict = Depends(get_current_user),
    svc=Depends(get_yield_service),
):
    """
    Return stats for all supported AMM pools.
    Shows: trading fee, Seamount's total position, minimum deposit.
    """
    try:
        results = []
        for pool in SUPPORTED_POOLS:
            try:
                stats = await svc.get_pool_stats(pool)
                results.append(stats)
            except Exception as e:
                logger.warning(f"Could not fetch stats for {pool}: {e}")
                results.append({"pool": pool, "success": False, "error": str(e)})
        return {"success": True, "pools": results}
    except Exception as e:
        logger.error(f"GET /xrp/yield/pools error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pool stats")


@router.get("/positions")
async def get_positions(
    current_user: dict = Depends(get_current_user),
    svc=Depends(get_yield_service),
):
    """
    Return all active and historical yield positions for the authenticated user.
    Includes estimated APY and days active per position.
    """
    try:
        user_id = current_user["id"]
        return await svc.get_user_positions(user_id)
    except Exception as e:
        logger.error(f"GET /xrp/yield/positions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve positions")


@router.post("/deposit")
async def deposit(
    body: DepositRequest,
    current_user: dict = Depends(get_current_user),
    svc=Depends(get_yield_service),
):
    """
    Deposit RLUSD or USDC into an AMM yield pool.
    Your internal balance is debited; a yield position is opened.
    Yield accrues daily and is credited back to your balance automatically.
    """
    try:
        user_id = current_user["id"]
        result = await svc.deposit(
            user_id=user_id,
            pool=body.pool,
            token_amount=Decimal(body.amount),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"POST /xrp/yield/deposit error: {e}")
        raise HTTPException(status_code=500, detail="Deposit failed")


@router.post("/withdraw")
async def withdraw(
    body: WithdrawRequest,
    current_user: dict = Depends(get_current_user),
    svc=Depends(get_yield_service),
):
    """
    Withdraw a yield position by position_id.
    Principal + all accrued yield is returned to your internal balance.
    """
    try:
        user_id = current_user["id"]
        result = await svc.withdraw(
            user_id=user_id,
            position_id=body.position_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"POST /xrp/yield/withdraw error: {e}")
        raise HTTPException(status_code=500, detail="Withdrawal failed")


@router.get("/history")
async def get_yield_history(
    pool: Optional[str] = Query(None, description="Filter by pool: RLUSD/XRP or USDC/XRP"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client),
):
    """
    Paginated yield credit history for the authenticated user.
    Shows all daily yield distributions received.
    """
    try:
        user_id = current_user["id"]
        query = (
            supabase.table("xrp_yield_distributions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if pool:
            query = query.eq("pool", pool)

        import asyncio
        result = await asyncio.to_thread(lambda: query.execute())

        total_yield = sum(
            Decimal(str(r.get("amount", 0)))
            for r in (result.data or [])
        )

        return {
            "success": True,
            "distributions": result.data or [],
            "total_in_view": str(total_yield),
            "count": len(result.data or []),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"GET /xrp/yield/history error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve yield history")


@router.post("/distribute")
async def trigger_distribution(
    pool: str = Query("RLUSD/XRP", description="Pool to distribute yield for"),
    admin: dict = Depends(require_admin),
    svc=Depends(get_yield_service),
):
    """
    Admin: Manually trigger daily yield distribution for a pool.
    In production this is called by the daily cron scheduler (3 AM UTC).
    """
    try:
        if pool not in SUPPORTED_POOLS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid pool. Choose from: {SUPPORTED_POOLS}"
            )
        result = await svc.distribute_yield(pool=pool)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /xrp/yield/distribute error: {e}")
        raise HTTPException(status_code=500, detail="Distribution failed")