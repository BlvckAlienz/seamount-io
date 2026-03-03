# backend/api/routes/wdk_protocols_routes.py
"""
WDK Protocol Routes
───────────────────
Exposes Velora Swap, USDT0 Bridge, Aave Lending,
MoonPay Fiat, and Tether Price Rates to the frontend.

Mount in main.py:
  from backend.api.routes.wdk_protocols_routes import router as wdk_protocols_router
  app.include_router(wdk_protocols_router, prefix="/api/v1")
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.wdk_client import WDKClient
from backend.services.database_service import DatabaseService
from backend.services.wdk_protocols_service import WDKProtocolsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wdk", tags=["WDK Protocols"])


# ── Dependency: build WDKProtocolsService per request ─────────────
def get_wdk_protocols_service() -> WDKProtocolsService:
    from backend.dependencies import get_database_service
    db  = get_database_service()
    wdk = WDKClient()
    return WDKProtocolsService(wdk_client=wdk, db_service=db)


# ── Request Models ─────────────────────────────────────────────────

class SwapRequest(BaseModel):
    token_in:      str = Field(..., description="Source token symbol (e.g. USDT)")
    token_out:     str = Field(..., description="Destination token symbol (e.g. USDC)")
    amount_in:     float = Field(..., gt=0)
    chain:         str = Field('ethereum', description="EVM chain: ethereum | polygon")
    account_index: int = Field(0, ge=0)


class BridgeRequest(BaseModel):
    token:         str = Field(..., description="Token to bridge (e.g. USDT)")
    amount:        float = Field(..., gt=0)
    target_chain:  str = Field(..., description="Destination chain (e.g. ton)")
    recipient:     str = Field(..., description="Recipient address on target chain")
    source_chain:  str = Field('ethereum')
    account_index: int = Field(0, ge=0)


class LendRequest(BaseModel):
    action:        str = Field(..., description="supply | withdraw | borrow | repay")
    token:         str = Field(..., description="Token symbol (e.g. USDT)")
    amount:        float = Field(..., gt=0)
    chain:         str = Field('ethereum')
    account_index: int = Field(0, ge=0)


class FiatQuoteRequest(BaseModel):
    currency_code:        str = Field(..., description="Fiat currency (e.g. NGN, USD)")
    crypto_currency:      str = Field('USDT', description="Target crypto")
    base_currency_amount: float = Field(..., gt=0)
    chain:                str = Field('ethereum')
    account_index:        int = Field(0, ge=0)


# ── Routes ─────────────────────────────────────────────────────────

@router.post("/swap")
async def wdk_swap(
    request:  SwapRequest,
    user:     Dict = Depends(get_current_user),
    svc:      WDKProtocolsService = Depends(get_wdk_protocols_service)
):
    """
    Velora EVM token swap.
    Swap USDT ↔ USDC (or any EVM-listed token pair) via Velora DEX.
    """
    try:
        result = await svc.swap(
            user_id       = user['id'],
            token_in      = request.token_in,
            token_out     = request.token_out,
            amount_in     = Decimal(str(request.amount_in)),
            chain         = request.chain,
            account_index = request.account_index
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ WDK swap failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Swap failed: {str(e)}")


@router.post("/bridge")
async def wdk_bridge(
    request: BridgeRequest,
    user:    Dict = Depends(get_current_user),
    svc:     WDKProtocolsService = Depends(get_wdk_protocols_service)
):
    """
    USDT0 cross-chain bridge.
    Bridge USDT from Ethereum/Polygon to TON (or reverse).
    """
    try:
        result = await svc.bridge(
            user_id       = user['id'],
            token         = request.token,
            amount        = Decimal(str(request.amount)),
            target_chain  = request.target_chain,
            recipient     = request.recipient,
            source_chain  = request.source_chain,
            account_index = request.account_index
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ WDK bridge failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bridge failed: {str(e)}")


@router.post("/lend")
async def wdk_lend(
    request: LendRequest,
    user:    Dict = Depends(get_current_user),
    svc:     WDKProtocolsService = Depends(get_wdk_protocols_service)
):
    """
    Aave lending protocol.
    supply / withdraw / borrow / repay via Aave EVM.
    This powers Seamount's yield farming feature.
    """
    try:
        result = await svc.lend(
            user_id       = user['id'],
            action        = request.action,
            token         = request.token,
            amount        = Decimal(str(request.amount)),
            chain         = request.chain,
            account_index = request.account_index
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ WDK lend({request.action}) failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lending failed: {str(e)}")


@router.post("/fiat/quote")
async def wdk_fiat_quote(
    request: FiatQuoteRequest,
    user:    Dict = Depends(get_current_user),
    svc:     WDKProtocolsService = Depends(get_wdk_protocols_service)
):
    """
    MoonPay on-ramp quote.
    Returns price, fees, and estimated crypto amount for a fiat purchase.
    """
    try:
        result = await svc.fiat_quote(
            user_id              = user['id'],
            currency_code        = request.currency_code,
            crypto_currency      = request.crypto_currency,
            base_currency_amount = request.base_currency_amount,
            chain                = request.chain,
            account_index        = request.account_index
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"❌ Fiat quote failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Fiat quote failed: {str(e)}")


@router.post("/fiat/buy")
async def wdk_fiat_buy(
    request: FiatQuoteRequest,
    user:    Dict = Depends(get_current_user),
    svc:     WDKProtocolsService = Depends(get_wdk_protocols_service)
):
    """
    Initiate MoonPay on-ramp purchase.
    Returns { url } — redirect user to this URL to complete payment.
    Replaces the current onramp.py provider with WDK-native MoonPay.
    """
    try:
        result = await svc.fiat_buy(
            user_id              = user['id'],
            currency_code        = request.currency_code,
            crypto_currency      = request.crypto_currency,
            base_currency_amount = request.base_currency_amount,
            chain                = request.chain,
            account_index        = request.account_index
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"❌ Fiat buy failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Fiat buy failed: {str(e)}")


@router.get("/price-rates")
async def wdk_price_rates(
    tokens: Optional[str] = None,   # comma-separated e.g. "USDT,ETH,BTC"
    svc:    WDKProtocolsService = Depends(get_wdk_protocols_service)
):
    """
    Tether WDK price oracle.
    Returns live USD rates for supported tokens.
    Used as primary source; falls back to oracle_service on error.
    """
    try:
        token_list = [t.strip() for t in tokens.split(',')] if tokens else None
        rates = await svc.get_price_rates(tokens=token_list)
        return {"success": True, "rates": rates}
    except Exception as e:
        logger.warning(f"⚠️ WDK price rates failed, using fallback: {e}")
        # Graceful fallback to existing oracle
        from backend.dependencies import get_database_service
        from backend.services.oracle_service import EnhancedOracleService
        try:
            oracle = EnhancedOracleService(get_database_service())
            price, _ = await oracle.get_asset_price('tether')
            return {
                "success": True,
                "rates": {"USDT": float(price)},
                "source": "oracle_fallback"
            }
        except Exception as fallback_err:
            raise HTTPException(status_code=503, detail=f"Price service unavailable: {str(e)}")