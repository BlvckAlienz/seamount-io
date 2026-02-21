# File: backend/api/routes/xrp_routes.py
"""
XRP Payment Routes — Seamount.io Phase 2
All endpoints require authentication via get_current_user.

GET  /xrp/deposit-info          → hot wallet address + user's destination tag
GET  /xrp/balances              → all XRP ledger balances (RLUSD, USDC, XRP)
POST /xrp/transfer              → internal P2P transfer (zero fee, instant)
POST /xrp/withdraw              → external withdrawal (on-chain, with fee)
GET  /xrp/transactions          → paginated transaction history
GET  /xrp/health                → service health check
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator, model_validator

from backend.dependencies import get_current_user, get_supabase_client
from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/xrp", tags=["XRP Payments"])

SUPPORTED_SYMBOLS = {"RLUSD", "USDC", "XRP"}


# ─── Pydantic Models ───────────────────────────────────────────────────────────

class TransferRequest(BaseModel):
    recipient_id: str
    symbol: str
    amount: str          # string to avoid float precision loss
    memo: Optional[str] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        v = v.upper()
        if v not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Symbol must be one of: {SUPPORTED_SYMBOLS}")
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

    @field_validator("recipient_id")
    @classmethod
    def validate_recipient(cls, v):
        if not v or len(v) < 10:
            raise ValueError("Invalid recipient_id")
        return v


class WithdrawRequest(BaseModel):
    symbol: str
    amount: str
    destination_address: str
    destination_tag: Optional[int] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        v = v.upper()
        if v not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Symbol must be one of: {SUPPORTED_SYMBOLS}")
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

    @field_validator("destination_address")
    @classmethod
    def validate_address(cls, v):
        if not v or not v.startswith("r") or len(v) < 25:
            raise ValueError(
                "Invalid XRPL address. Must start with 'r' and be at least 25 characters."
            )
        return v

    @field_validator("destination_tag")
    @classmethod
    def validate_tag(cls, v):
        if v is not None and not (0 <= v <= 4_294_967_295):
            raise ValueError("Destination tag must be between 0 and 4,294,967,295")
        return v


# ─── Dependency: XRP Payment Service ──────────────────────────────────────────

def get_xrp_payment_service(
    supabase=Depends(get_supabase_client),
    settings=Depends(get_settings),
):
    """
    Build XRPPaymentService on demand.
    Lazy-imports to avoid circular deps at startup.
    """
    try:
        from backend.services.xrp_service import XRPService
        from backend.services.xrp_payment_service import XRPPaymentService
        xrp_service = XRPService(settings=settings)
        return XRPPaymentService(
            supabase_client=supabase,
            xrp_service=xrp_service,
            settings=settings,
        )
    except Exception as e:
        logger.error(f"❌ Failed to init XRPPaymentService: {e}")
        raise HTTPException(status_code=503, detail="XRP payment service unavailable")


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/deposit-info")
async def get_deposit_info(
    current_user: dict = Depends(get_current_user),
    svc=Depends(get_xrp_payment_service),
):
    """
    Get the hot wallet address and destination tag for this user.
    User must include BOTH when sending to Seamount from an external wallet.
    """
    try:
        user_id = current_user["id"]
        return await svc.get_deposit_info(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"GET /xrp/deposit-info error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve deposit info")


@router.get("/balances")
async def get_balances(
    current_user: dict = Depends(get_current_user),
    svc=Depends(get_xrp_payment_service),
):
    """
    Return all XRP Ledger asset balances for the authenticated user.
    These are internal (custodial) balances — not queried from the blockchain.
    """
    try:
        user_id = current_user["id"]
        balances = await svc.get_all_balances(user_id)
        return {
            "success": True,
            "user_id": user_id,
            "balances": balances,
            "network": "XRP Ledger (custodial)",
        }
    except Exception as e:
        logger.error(f"GET /xrp/balances error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve balances")


@router.post("/transfer")
async def internal_transfer(
    body: TransferRequest,
    current_user: dict = Depends(get_current_user),
    svc=Depends(get_xrp_payment_service),
):
    """
    Send RLUSD, USDC, or XRP to another Seamount user.
    Zero fee. Instant. No blockchain transaction.
    Both sender and recipient must be registered Seamount users.
    """
    try:
        sender_id = current_user["id"]
        result = await svc.internal_transfer(
            sender_id=sender_id,
            recipient_id=body.recipient_id,
            symbol=body.symbol,
            amount=Decimal(body.amount),
            memo=body.memo,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"POST /xrp/transfer error: {e}")
        raise HTTPException(status_code=500, detail="Transfer failed")


@router.post("/withdraw")
async def withdraw(
    body: WithdrawRequest,
    current_user: dict = Depends(get_current_user),
    svc=Depends(get_xrp_payment_service),
):
    """
    Withdraw RLUSD, USDC, or XRP to an external XRPL address.
    Requires a valid 'r...' XRPL destination address.
    A small withdrawal fee is deducted from the amount.
    Settlement: ~5 seconds (XRPL finality).
    """
    try:
        user_id = current_user["id"]
        result = await svc.withdraw(
            user_id=user_id,
            symbol=body.symbol,
            amount=Decimal(body.amount),
            destination_address=body.destination_address,
            destination_tag=body.destination_tag,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"POST /xrp/withdraw error: {e}")
        raise HTTPException(status_code=500, detail="Withdrawal failed")


@router.get("/transactions")
async def get_transactions(
    symbol: Optional[str] = Query(None, description="Filter by asset: RLUSD, USDC, XRP"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    svc=Depends(get_xrp_payment_service),
):
    """
    Paginated transaction history for the authenticated user.
    Includes: deposits, withdrawals, internal transfers, yield credits.
    """
    try:
        user_id = current_user["id"]
        return await svc.get_transaction_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
            symbol=symbol,
        )
    except Exception as e:
        logger.error(f"GET /xrp/transactions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve transactions")


@router.get("/health")
async def xrp_health(settings=Depends(get_settings)):
    """XRP service health — checks connectivity to hot wallet."""
    try:
        from backend.services.xrp_service import XRPService
        xrp = XRPService(settings=settings)
        balances = await xrp.get_hot_wallet_balances()
        return {
            "status": "healthy",
            "network": settings.XRP_NETWORK,
            "hot_wallet": settings.XRP_HOT_WALLET_ADDRESS,
            "hot_wallet_balances": {k: str(v) for k, v in balances.items()},
        }
    except Exception as e:
        logger.error(f"XRP health check failed: {e}")
        return {"status": "degraded", "error": str(e)}