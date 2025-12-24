# backend/api/routes/quidax.py
"""
Quidax API Routes
Handles instant crypto buy/sell operations
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional
import logging
from datetime import datetime

from backend.dependencies import get_supabase_client, get_current_user
from backend.services.quidax_service import QuidaxService
from supabase import Client

router = APIRouter(prefix="/quidax", tags=["quidax"])
logger = logging.getLogger(__name__)


# ============================================================================
# REQUEST MODELS
# ============================================================================

class QuoteRequest(BaseModel):
    """Request model for getting a quote"""
    market: str = Field(..., example="usdtngn", description="Market pair")
    quote_type: str = Field(..., example="buy", description="'buy' or 'sell'")
    amount: float = Field(..., gt=0, example=10000.0, description="Amount in NGN or crypto")
    amount_type: str = Field(default="fiat", example="fiat", description="'fiat' or 'crypto'")


class InstantOrderRequest(BaseModel):
    """Request model for creating an instant order"""
    quote_reference: str = Field(..., example="quote_abc123", description="Quote reference from /quote endpoint")


class WithdrawalRequest(BaseModel):
    """Request model for withdrawing crypto"""
    currency: str = Field(..., example="usdt", description="Crypto currency")
    amount: float = Field(..., gt=0, example=10.0, description="Amount to withdraw")
    destination_address: str = Field(..., description="Destination wallet address")
    network: Optional[str] = Field(default="trc20", example="trc20", description="Network for token transfers")


# ============================================================================
# ROUTES
# ============================================================================

@router.get("/markets")
async def get_markets(
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get all available Quidax markets
    
    Returns list of tradeable market pairs (e.g., usdtngn, btcngn)
    """
    try:
        quidax = QuidaxService(supabase)
        markets = await quidax.get_markets()
        
        return {
            "success": True,
            "markets": markets.get("data", []),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch markets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/ticker/{market}")
async def get_ticker(
    market: str,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get current price ticker for a market
    
    Args:
        market: Market pair (e.g., 'usdtngn', 'btcngn')
    
    Returns:
        Current bid/ask prices and volume
    """
    try:
        quidax = QuidaxService(supabase)
        ticker = await quidax.get_ticker(market)
        
        if not ticker.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ticker.get("error", "Failed to fetch ticker")
            )
        
        return ticker
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch ticker: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/quote")
async def get_quote(
    request: QuoteRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get a price quote for buying/selling crypto
    
    Quote is valid for 5 minutes. Use quote_reference to create instant order.
    
    Example:
        POST /quidax/quote
        {
            "market": "usdtngn",
            "quote_type": "buy",
            "amount": 10000,
            "amount_type": "fiat"
        }
    
    Returns:
        {
            "success": true,
            "quote_reference": "quote_abc123",
            "unit_price": 1650.50,
            "crypto_amount": 6.06,
            "fiat_amount": 10000.0,
            "fee": 100.0,
            "total": 10100.0,
            "expires_at": "2025-01-01T12:05:00Z"
        }
    """
    try:
        user_id = current_user["id"]
        
        # Validate market format
        if not request.market or len(request.market) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid market format"
            )
        
        # Validate quote type
        if request.quote_type not in ["buy", "sell"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="quote_type must be 'buy' or 'sell'"
            )
        
        # Validate amount type
        if request.amount_type not in ["fiat", "crypto"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="amount_type must be 'fiat' or 'crypto'"
            )
        
        quidax = QuidaxService(supabase)
        quote = await quidax.get_quote(
            user_id=user_id,
            market=request.market,
            quote_type=request.quote_type,
            amount=request.amount,
            amount_type=request.amount_type
        )
        
        if not quote.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=quote.get("error", "Failed to generate quote")
            )
        
        return quote
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Quote generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/instant-order")
async def create_instant_order(
    request: InstantOrderRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Create an instant order from a quote
    
    This initiates the payment flow. User will be redirected to payment page.
    
    Example:
        POST /quidax/instant-order
        {
            "quote_reference": "quote_abc123"
        }
    
    Returns:
        {
            "success": true,
            "order_id": "instant_order_12345",
            "payment_url": "https://quidax.com/pay/...",
            "status": "pending"
        }
    """
    try:
        user_id = current_user["id"]
        
        quidax = QuidaxService(supabase)
        order = await quidax.create_instant_order(
            user_id=user_id,
            quote_reference=request.quote_reference
        )
        
        if not order.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=order.get("error", "Failed to create instant order")
            )
        
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Instant order creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/orders/{order_id}")
async def get_order_status(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get status of an instant order
    
    Use this to verify order completion before crediting user
    """
    try:
        # Verify order belongs to user
        order_result = supabase.table("onramp_transactions")\
            .select("*")\
            .eq("quidax_order_id", order_id)\
            .eq("user_id", current_user["id"])\
            .single()\
            .execute()
        
        if not order_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        quidax = QuidaxService(supabase)
        order_status = await quidax.get_order_status(order_id)
        
        if not order_status.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=order_status.get("error", "Failed to fetch order status")
            )
        
        return order_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/withdraw")
async def withdraw_crypto(
    request: WithdrawalRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Withdraw crypto from Quidax to external wallet
    
    Used for auto-withdrawal to user's WDK wallet after purchase
    
    🚨 IMPORTANT: Verify user has sufficient balance first
    """
    try:
        user_id = current_user["id"]
        
        # TODO: Check user's Quidax balance before withdrawal
        # This requires implementing balance tracking
        
        quidax = QuidaxService(supabase)
        withdrawal = await quidax.withdraw_crypto(
            user_id=user_id,
            currency=request.currency,
            amount=request.amount,
            destination_address=request.destination_address,
            network=request.network
        )
        
        if not withdrawal.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=withdrawal.get("error", "Withdrawal failed")
            )
        
        return withdrawal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Withdrawal failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/wallets")
async def get_wallets(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get Quidax wallet balances
    
    Returns balances for all supported currencies
    """
    try:
        quidax = QuidaxService(supabase)
        wallets = await quidax.get_wallets()
        
        return wallets
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch wallets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
# Test entry point
if __name__ == "__main__":
    print("✅ Quidax routes module loaded successfully")
    print(f"📍 Router prefix: {router.prefix}")
    print(f"📍 Number of routes: {len(router.routes)}")