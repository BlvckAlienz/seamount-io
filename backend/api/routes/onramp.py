# File: backend/api/routes/onramp.py
"""
On-Ramp Routes - Paystack/Flutterwave/Cashramp Integration
MAXIMIZE REVENUE: Use our own providers instead of aggregators
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from decimal import Decimal
from typing import Optional
import logging

from backend.dependencies import get_current_user, get_db_service, get_audit_service
from backend.services.payment_providers.paystack import PaystackProvider
from backend.services.payment_providers.flutterwave import FlutterwaveProvider
from backend.services.cashramp_service import CashrampService
from backend.services.revenue_tracking_service import RevenueTrackingService
from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onramp", tags=["On-Ramp"])

class OnRampRequest(BaseModel):
    amount_fiat: float
    currency: str
    crypto_asset: str
    payment_method: str = "auto"  # auto, paystack, flutterwave, cashramp
    user_country: str = "NG"

@router.post("/initialize")
async def initialize_onramp(
    request: OnRampRequest,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """
    Initialize fiat → crypto on-ramp
    
    REVENUE OPTIMIZATION:
    - NGN payments → Paystack (1.2% fee) - WE KEEP 0.6%
    - International → Flutterwave (2.15% fee) - WE KEEP 0.35%
    - P2P fallback → Cashramp (2.6% fee) - WE KEEP 0.4%
    """
    
    try:
        settings = get_settings()
        amount = Decimal(str(request.amount_fiat))
        
        # Get user wallet address
        wallet_query = "SELECT algorand_address FROM user_wallets WHERE user_id = %s"
        wallet_result = await db_service.execute_query(wallet_query, (current_user["id"],))
        
        if not wallet_result:
            raise HTTPException(status_code=400, detail="User wallet not found. Create wallet first.")
        
        wallet_address = wallet_result[0]["algorand_address"]
        
        # 🎯 SMART ROUTING (Maximize our revenue)
        provider = None
        payment_result = None
        
        # TIER 1: Paystack (Best for NGN - lowest fees)
        if request.currency == "NGN" and request.payment_method in ["auto", "paystack"]:
            try:
                paystack = PaystackProvider(settings)
                
                # Calculate our fee (1.8% total, Paystack takes 1.2%, we keep 0.6%)
                our_fee = amount * Decimal("0.018")
                paystack_amount = amount - our_fee
                
                payment_result = await paystack.initialize_payment(
                    amount=float(paystack_amount),
                    currency="NGN",
                    email=current_user["email"],
                    tx_ref=f"ONRAMP_{current_user['id'][:8]}_{int(amount)}",
                    phone=current_user.get("phone"),
                    name=f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}"
                )
                
                provider = "paystack"
                logger.info(f"✅ Paystack on-ramp initialized: {amount} NGN")
                
            except Exception as paystack_error:
                logger.warning(f"⚠️ Paystack failed: {paystack_error}")
                # Fall through to Flutterwave
        
        # TIER 2: Flutterwave (International fallback)
        if not payment_result and request.payment_method in ["auto", "flutterwave"]:
            try:
                flutterwave = FlutterwaveProvider(settings)
                
                # Calculate our fee (2.5% total, Flutterwave takes 2.15%, we keep 0.35%)
                our_fee = amount * Decimal("0.025")
                flutterwave_amount = amount - our_fee
                
                payment_result = await flutterwave.initialize_payment(
                    amount=float(flutterwave_amount),
                    currency=request.currency,
                    email=current_user["email"],
                    tx_ref=f"ONRAMP_{current_user['id'][:8]}_{int(amount)}",
                    phone=current_user.get("phone"),
                    name=f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}"
                )
                
                provider = "flutterwave"
                logger.info(f"✅ Flutterwave on-ramp initialized: {amount} {request.currency}")
                
            except Exception as flutterwave_error:
                logger.warning(f"⚠️ Flutterwave failed: {flutterwave_error}")
                # Fall through to Cashramp
        
        # TIER 3: Cashramp (P2P fallback)
        if not payment_result and request.payment_method in ["auto", "cashramp"]:
            try:
                cashramp = CashrampService(db_service)
                
                # Calculate our fee (2.8% total, Cashramp takes 2.6%, we keep 0.2%)
                our_fee = amount * Decimal("0.028")
                
                payment_result = await cashramp.create_ngn_onramp(
                    user_id=current_user["id"],
                    asset=request.crypto_asset,
                    amount_ngn=amount,
                    payment_method="paystack"  # Cashramp uses Paystack internally
                )
                
                provider = "cashramp"
                logger.info(f"✅ Cashramp on-ramp initialized: {amount} {request.currency}")
                
            except Exception as cashramp_error:
                logger.error(f"❌ All providers failed! Last error: {cashramp_error}")
                raise HTTPException(
                    status_code=503,
                    detail="Payment service temporarily unavailable. Please try again."
                )
        
        if not payment_result:
            raise HTTPException(
                status_code=503,
                detail="All payment providers unavailable"
            )
        
        # Store on-ramp transaction
        tx_id = f"ONRAMP_{current_user['id'][:8]}_{int(amount)}"
        
        tx_data = {
            "id": tx_id,
            "user_id": current_user["id"],
            "type": "onramp",
            "status": "pending_payment",
            "provider": provider,
            "provider_name": provider.title(),
            "currency": request.currency,
            "crypto_asset": request.crypto_asset,
            "amount_fiat": float(amount),
            "seamount_fee": float(our_fee),
            "net_to_user": float(amount - our_fee),
            "wallet_address": wallet_address,
            "checkout_url": payment_result.get("payment_link") or payment_result.get("authorization_url"),
            "user_email": current_user["email"],
            "user_country": request.user_country,
            "estimated_settlement": "5-10 minutes"
        }
        
        await db_service.log_event("onramp_transactions", tx_data)
        
        # Track revenue
        revenue_service = RevenueTrackingService(db_service)
        await revenue_service.track_transaction_fee(
            user_id=current_user["id"],
            transaction_type="on_ramp",
            amount=amount,
            fee_rate=Decimal("0.018"),
            platform_fee=our_fee,
            network_fee=Decimal("0.001"),
            blockchain="algorand",
            metadata={
                "transaction_id": tx_id,
                "provider": provider,
                "currency": request.currency
            }
        )
        
        # Log audit
        if audit_service:
            await audit_service.log_event(
                "ONRAMP_INITIATED",
                user_id=current_user["id"],
                resource_id=tx_id,
                details={
                    "provider": provider,
                    "amount": float(amount),
                    "currency": request.currency,
                    "asset": request.crypto_asset
                }
            )
        
        logger.info(f"✅ On-ramp initialized: {tx_id} via {provider}")
        
        return {
            "success": True,
            "transaction_id": tx_id,
            "checkout_url": tx_data["checkout_url"],
            "provider": provider,
            "amount_fiat": float(amount),
            "currency": request.currency,
            "crypto_asset": request.crypto_asset,
            "seamount_fee": float(our_fee),
            "net_amount": float(amount - our_fee),
            "estimated_crypto_amount": float(amount - our_fee),  # 1:1 for stablecoins
            "estimated_settlement": "5-10 minutes",
            "expires_at": None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"On-ramp initialization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"On-ramp failed: {str(e)}")

@router.post("/webhook/{provider}")
async def handle_webhook(
    provider: str,
    request: Request,
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """
    Handle payment confirmation webhooks
    Provider notifies us when payment completes
    """
    
    try:
        payload = await request.json()
        logger.info(f"📨 Webhook received from {provider}: {payload.get('event')}")
        
        settings = get_settings()
        
        # Route to correct provider
        if provider == "paystack":
            paystack = PaystackProvider(settings)
            result = await paystack.verify_payment(payload.get("reference"))
            
            if result.get("verified"):
                # Credit user wallet
                await _credit_user_wallet(
                    db_service,
                    payload.get("reference"),
                    result.get("amount"),
                    result.get("currency")
                )
                
        elif provider == "flutterwave":
            flutterwave = FlutterwaveProvider(settings)
            result = await flutterwave.verify_payment(payload.get("tx_ref"))
            
            if result.get("verified"):
                await _credit_user_wallet(
                    db_service,
                    payload.get("tx_ref"),
                    result.get("amount"),
                    result.get("currency")
                )
        
        return {"status": "success", "processed": True}
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        return {"status": "error", "message": str(e)}

async def _credit_user_wallet(db_service, tx_ref: str, amount: float, currency: str):
    """Credit user wallet after successful payment"""
    
    try:
        # Get transaction details
        query = "SELECT user_id, crypto_asset, wallet_address FROM onramp_transactions WHERE id = %s"
        result = await db_service.execute_query(query, (tx_ref,))
        
        if not result:
            logger.error(f"Transaction not found: {tx_ref}")
            return
        
        tx = result[0]
        
        # Update wallet balance (assuming USDT for now)
        balance_query = """
            UPDATE wallet_balances 
            SET usdt_balance = usdt_balance + %s, updated_at = NOW()
            WHERE user_id = %s
        """
        await db_service.execute_query(balance_query, (amount, tx["user_id"]))
        
        # Mark transaction complete
        update_query = """
            UPDATE onramp_transactions 
            SET status = 'completed', completed_at = NOW()
            WHERE id = %s
        """
        await db_service.execute_query(update_query, (tx_ref,))
        
        logger.info(f"✅ Credited {amount} USDT to user {tx['user_id']}")
        
    except Exception as e:
        logger.error(f"Failed to credit wallet: {e}")

@router.get("/providers")
async def get_providers():
    """Get available payment providers"""
    
    return {
        "providers": [
            {
                "id": "paystack",
                "name": "Paystack",
                "currencies": ["NGN"],
                "fee": "1.8%",
                "settlement": "Instant",
                "recommended": True
            },
            {
                "id": "flutterwave",
                "name": "Flutterwave",
                "currencies": ["NGN", "KES", "GHS", "ZAR", "USD", "EUR"],
                "fee": "2.5%",
                "settlement": "5-10 minutes",
                "recommended": False
            },
            {
                "id": "cashramp",
                "name": "Cashramp P2P",
                "currencies": ["NGN", "KES", "GHS"],
                "fee": "2.8%",
                "settlement": "< 5 seconds",
                "recommended": False
            }
        ]
    }
```

---

### **✅ REVENUE COMPARISON:**

**OLD (Aggregator approach):**
```
User pays $100
Provider keeps $3.50 (3.5%)
We keep $0 ❌
User gets $96.50
```

**NEW (Our providers):**
```
User pays $100 NGN
Paystack keeps $1.20 (1.2%)
We keep $0.60 (0.6%) ✅
User gets $98.20