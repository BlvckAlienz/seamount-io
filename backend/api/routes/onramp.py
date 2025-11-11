# File: backend/api/routes/onramp.py
"""
On-Ramp Routes - Cashramp/Paystack/Flutterwave Integration
PRIORITY ORDER: Cashramp (lowest fees) → Paystack → Flutterwave
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from decimal import Decimal
from typing import Optional
from datetime import datetime
import logging

from backend.dependencies import get_current_user, get_db_service, get_audit_service
from backend.services.payment_providers.paystack import PaystackProvider
from backend.services.payment_providers.flutterwave import FlutterwaveProvider
from backend.services.cashramp_service import CashrampService
from backend.services.revenue_tracking_service import RevenueTrackingService
from backend.config import get_settings, TransactionType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onramp", tags=["On-Ramp"])

class OnRampRequest(BaseModel):
    amount_fiat: float
    currency: str
    crypto_asset: str
    payment_method: str = "auto"  # auto, cashramp, paystack, flutterwave
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
    PRIORITY: Cashramp (P2P) → Paystack (NGN) → Flutterwave (International)
    """
    
    try:
        settings = get_settings()
        amount = Decimal(str(request.amount_fiat))
        
        # Simple fee calculation (no fee calculator dependency)
        our_fee = Decimal("0")  # Will be set per provider

        # STEP 1: Get user wallet address
        try:
            wallet_result = db_service.supabase.from_('user_wallets')\
                .select('algorand_address')\
                .eq('user_id', current_user["id"])\
                .limit(1)\
                .execute()
            
            if not wallet_result.data or len(wallet_result.data) == 0:
                raise HTTPException(
                    status_code=400, 
                    detail="User wallet not found. Create wallet first."
                )
            
            wallet_address = wallet_result.data[0]["algorand_address"]
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch wallet: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Database error: {str(e)}"
            )
        
        # DEBUG: Provider Configuration Check
        logger.info(f"PROVIDER CONFIGURATION CHECK:")
        logger.info(f"Cashramp API Key: {'SET' if hasattr(settings, 'CASHRAMP_API_KEY') and settings.CASHRAMP_API_KEY else 'MISSING'}")
        logger.info(f"Paystack Secret Key: {'SET' if hasattr(settings, 'PAYSTACK_SECRET_KEY') and settings.PAYSTACK_SECRET_KEY else 'MISSING'}")
        logger.info(f"Flutterwave Secret Key: {'SET' if hasattr(settings, 'FLUTTERWAVE_SECRET_KEY') and settings.FLUTTERWAVE_SECRET_KEY else 'MISSING'}")

        # Check if Cashramp service is available
        cashramp_available = False
        try:
            cashramp = CashrampService(db_service)
            cashramp_available = cashramp.is_available()
            logger.info(f"Cashramp Service Available: {'YES' if cashramp_available else 'NO'}")
        except Exception as e:
            logger.error(f"Cashramp Service Check Failed: {e}")

        # STEP 2: Smart routing with proper URL extraction
        provider = None
        payment_result = None
        checkout_url = None
        
        # TIER 1: PAYSTACK (Most reliable for NGN, 1.8% fee)
        if request.currency == "NGN" and request.payment_method in ["auto", "paystack"]:
            try:
                logger.info(f"🔵 Attempting Paystack on-ramp (PRIMARY): {amount} {request.currency}")
                paystack = PaystackProvider(settings)
                
                # Paystack fee: 2.5% (0.5% Seamount + 2.0% Paystack)
                our_fee = amount * Decimal("0.005")  # 0.5% Seamount margin
                provider_amount = amount  # User pays full amount requested
                
                payment_result = await paystack.initialize_payment(
                    amount=float(provider_amount),  # Full amount to Paystack
                    currency="NGN",
                    email=current_user["email"],
                    tx_ref=f"ONRAMP_{current_user['id'][:8]}_{int(datetime.now().timestamp())}",
                    phone=current_user.get("phone"),
                    name=f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}"
                )
                
                if payment_result and payment_result.get("status") == "success":
                    checkout_url = (
                        payment_result.get("authorization_url") or 
                        payment_result.get("payment_link") or
                        payment_result.get("access_url")
                    )
                    
                    if checkout_url:
                        provider = "paystack"
                        logger.info(f"Paystack (PRIMARY) checkout URL: {checkout_url}")
                    else:
                        logger.warning(f"Paystack returned success but no URL: {payment_result}")
                else:
                    logger.warning(f"Paystack returned invalid response: {payment_result}")
                    
            except Exception as paystack_error:
                logger.warning(f"Paystack (PRIMARY) failed: {paystack_error}")
                # Fall through to Flutterwave
        
        # TIER 2: FLUTTERWAVE (International + NGN backup, 2.5% fee)
        if not checkout_url and request.payment_method in ["auto", "flutterwave"]:
            try:
                logger.info(f"Attempting Flutterwave on-ramp (SECONDARY): {amount} {request.currency}")
                flutterwave = FlutterwaveProvider(settings)
                
                # Flutterwave fee: 2.5-4.0% (0.5% Seamount + provider cost)
                our_fee = amount * Decimal("0.005")  # 0.5% Seamount margin
                provider_amount = amount  # Full amount to Flutterwave
                
                payment_result = await flutterwave.initialize_payment(
                    amount=float(provider_amount),  # Full amount to Flutterwave
                    currency=request.currency,
                    email=current_user["email"],
                    tx_ref=f"ONRAMP_{current_user['id'][:8]}_{int(datetime.now().timestamp())}",
                    phone=current_user.get("phone"),
                    name=f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}"
                )
                
                if payment_result and payment_result.get("status") == "success":
                    checkout_url = (
                        payment_result.get("link") or 
                        payment_result.get("payment_link") or
                        payment_result.get("data", {}).get("link")
                    )
                    
                    if checkout_url:
                        provider = "flutterwave"
                        logger.info(f"Flutterwave (SECONDARY) checkout URL: {checkout_url}")
                    else:
                        logger.warning(f"Flutterwave returned success but no URL: {payment_result}")
                else:
                    logger.warning(f"Flutterwave returned invalid response: {payment_result}")
                    
            except Exception as flutterwave_error:
                logger.warning(f"Flutterwave (SECONDARY) failed: {flutterwave_error}")
                # Fall through to Cashramp
        
        # TIER 3: CASHRAMP (P2P, currently under maintenance)
        if not checkout_url and request.payment_method in ["auto", "cashramp"]:
            try:
                logger.info(f"Attempting Cashramp on-ramp (TERTIARY): {amount} {request.currency}")
                cashramp = CashrampService(db_service)
                
                if not cashramp.is_available():
                    logger.warning("Cashramp not available (missing API keys)")
                    raise Exception("Cashramp service not configured")
                
                payment_result = await cashramp.create_ngn_onramp(
                    user_id=current_user["id"],
                    asset=request.crypto_asset,
                    amount_ngn=amount,
                    payment_method="p2p"
                )
                
                if payment_result and isinstance(payment_result, dict) and payment_result.get("success"):
                    url_candidates = [
                        payment_result.get("payment_url"),
                        payment_result.get("checkout_url"), 
                        payment_result.get("url"),
                        payment_result.get("link")
                    ]
                    
                    for candidate in url_candidates:
                        if candidate and isinstance(candidate, str) and candidate.startswith(('http://', 'https://')):
                            checkout_url = candidate
                            provider = "cashramp"
                            logger.info(f"Cashramp (TERTIARY) URL found: {checkout_url}")
                            break
                    
                    if not checkout_url:
                        logger.warning(f"Cashramp returned success but no valid URL")
                else:
                    logger.warning(f"Cashramp returned invalid response: {payment_result}")
                    
            except Exception as cashramp_error:
                logger.warning(f"Cashramp (TERTIARY) failed: {cashramp_error}")
                # Fall through to emergency
        
        # EMERGENCY FALLBACK: Force Paystack (most reliable)
        if not checkout_url:
            try:
                logger.info("ACTIVATING EMERGENCY PAYSTACK FALLBACK...")
                
                # Only for NGN - Flutterwave for others
                if request.currency == "NGN":
                    paystack = PaystackProvider(settings)
                    
                    payment_result = await paystack.initialize_payment(
                        amount=float(amount),
                        currency="NGN",
                        email=current_user["email"],
                        tx_ref=f"EMG_{current_user['id'][:8]}_{int(datetime.now().timestamp())}",
                        name=current_user.get('first_name', 'User')
                    )
                    
                    if payment_result and payment_result.get("status") == "success":
                        checkout_url = payment_result.get("authorization_url") or payment_result.get("payment_link")
                        if checkout_url:
                            provider = "paystack_emergency"
                            logger.info(f"EMERGENCY PAYSTACK URL: {checkout_url}")
                else:
                    # Non-NGN: Use Flutterwave
                    flutterwave = FlutterwaveProvider(settings)
                    
                    payment_result = await flutterwave.initialize_payment(
                        amount=float(amount),
                        currency=request.currency,
                        email=current_user["email"],
                        tx_ref=f"EMG_{current_user['id'][:8]}_{int(datetime.now().timestamp())}",
                        name=current_user.get('first_name', 'User')
                    )
                    
                    if payment_result and payment_result.get("status") == "success":
                        checkout_url = payment_result.get("data", {}).get("link") or payment_result.get("link")
                        if checkout_url:
                            provider = "flutterwave_emergency"
                            logger.info(f"EMERGENCY FLUTTERWAVE URL: {checkout_url}")
                        
            except Exception as emergency_error:
                logger.error(f"EMERGENCY FALLBACK FAILED: {emergency_error}")

        # VALIDATION: Ensure we have a checkout URL
        if not checkout_url:
            logger.error(
                f"All providers failed to return checkout URL. "
                f"Last provider: {provider}, Last result: {payment_result}"
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "Payment service temporarily unavailable. "
                    "All providers failed to generate payment link. "
                    "Please try again in a few minutes."
                )
            )
        
        # STEP 3: Store on-ramp transaction
        tx_id = f"ONRAMP_{current_user['id'][:8]}_{int(amount)}_{int(datetime.now().timestamp())}"
        
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
            "net_to_user": float(amount - our_fee),      # What user gets ($100)
            "wallet_address": wallet_address,
            "checkout_url": checkout_url,
            "user_email": current_user["email"],
            "user_country": request.user_country,
            "fee_breakdown": {
                "seamount_fee": float(our_fee),
                "provider": provider,
                "currency": request.currency
            },
            "estimated_settlement": "5-10 minutes",
            "created_at": datetime.now().isoformat()
        }
        
        try:
            db_service.supabase.from_('onramp_transactions').insert(tx_data).execute()
            logger.info(f"Transaction record created: {tx_id}")
        except Exception as db_error:
            logger.error(f"Failed to store transaction: {db_error}")
            # Continue anyway - payment link is still valid
        
        # STEP 4: Track revenue (optional, non-blocking)
        try:
            revenue_service = RevenueTrackingService(db_service)
            await revenue_service.track_transaction_fee(
                user_id=current_user["id"],
                transaction_type="on_ramp",
                amount=amount,
                fee_rate=Decimal("0.005"),  # 0.5% Seamount margin
                platform_fee=our_fee,
                network_fee=Decimal("0.001"),
                blockchain="algorand",
                metadata={
                    "transaction_id": tx_id,
                    "provider": provider,
                    "currency": request.currency
                }
            )
        except Exception as revenue_error:
            logger.warning(f"Failed to track revenue: {revenue_error}")
        
        # STEP 5: Log audit trail (optional, non-blocking)
        if audit_service:
            try:
                await audit_service.log_event(
                    "ONRAMP_INITIATED",
                    user_id=str(current_user["id"]) if current_user else "unknown",
                    resource_id=str(tx_id) if tx_id else "unknown",
                    details={
                        "provider": str(provider) if provider else "unknown",
                        "amount": float(amount) if amount else 0,
                        "currency": str(request.currency) if request.currency else "unknown",
                        "asset": str(request.crypto_asset) if request.crypto_asset else "unknown"
                    }
                )
            except Exception as audit_error:
                logger.warning(f"Failed to log audit (non-critical): {audit_error}")
        
        logger.info(f"On-ramp initialized: {tx_id} via {provider} - URL: {checkout_url}")
        
        return {
            "success": True,
            "transaction_id": tx_id,
            "checkout_url": checkout_url,  # ✅ CRITICAL: User needs this to pay
            "provider": provider,
            "amount_fiat": float(amount),
            "currency": request.currency,
            "crypto_asset": request.crypto_asset,
            "seamount_fee": float(our_fee),
            "net_amount": float(amount - our_fee),
            "estimated_crypto_amount": float(amount - our_fee),    
            "estimated_settlement": "5-10 minutes",
            "provider": provider,
            "estimated_settlement": tx_data.get("estimated_settlement", "5-10 minutes")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"On-ramp initialization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"On-ramp failed: {str(e)}"
        )


@router.post("/webhook/{provider}")
async def handle_webhook(
    provider: str,
    request: Request,
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Handle payment confirmation webhooks"""
    
    try:
        payload = await request.json()
        logger.info(f"Webhook received from {provider}: {payload.get('event')}")
        
        settings = get_settings()
        
        # Route to correct provider
        if provider == "cashramp":
            cashramp = CashrampService(db_service)
            result = await cashramp.verify_payment(payload.get("reference"))
            
            if result.get("verified"):
                await _credit_user_wallet(
                    db_service,
                    payload.get("reference"),
                    result.get("amount"),
                    result.get("currency")
                )
                
        elif provider == "paystack":
            paystack = PaystackProvider(settings)
            result = await paystack.verify_payment(payload.get("reference"))
            
            if result.get("verified"):
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
        result = db_service.supabase.from_('onramp_transactions')\
            .select('user_id, crypto_asset, wallet_address')\
            .eq('id', tx_ref)\
            .limit(1)\
            .execute()
        
        if not result.data:
            logger.error(f"Transaction not found: {tx_ref}")
            return
        
        tx = result.data[0]
    except Exception as e:
        logger.error(f"Failed to fetch transaction: {e}")
        return
    
    try:
        balance_result = await db_service.supabase.from_('wallet_balances')\
            .select('usdt_balance')\
            .eq('user_id', tx["user_id"])\
            .limit(1)\
            .execute()
        
        if balance_result.data:
            current_balance = float(balance_result.data[0].get('usdt_balance', 0))
            new_balance = current_balance + amount
            
            db_service.supabase.from_('wallet_balances')\
                .update({'usdt_balance': new_balance, 'updated_at': 'NOW()'})\
                .eq('user_id', tx["user_id"])\
                .execute()
            
            logger.info(f"Credited {amount} USDT to user {tx['user_id']}")
    except Exception as e:
        logger.error(f"Failed to update balance: {e}")
    
    try:
        db_service.supabase.from_('onramp_transactions')\
            .update({'status': 'completed', 'completed_at': 'NOW()'})\
            .eq('id', tx_ref)\
            .execute()
    except Exception as e:
        logger.error(f"Failed to mark transaction complete: {e}")


@router.get("/providers")
async def get_providers():
    """Get available payment providers (UPDATED PRIORITY ORDER)"""
    
    return {
        "providers": [
            {
                "id": "paystack",
                "name": "Paystack",
                "currencies": ["NGN"],
                "fee": "2.5%",
                "settlement": "Instant",
                "recommended": True,
                "priority": 1,
                "status": "operational"
            },
            {
                "id": "flutterwave",
                "name": "Flutterwave",
                "currencies": ["NGN", "KES", "GHS", "ZAR", "USD", "EUR"],
                "fee": "2.5-4.0%",
                "settlement": "5-10 minutes",
                "recommended": True,
                "priority": 2,
                "status": "operational"
            },
            {
                "id": "cashramp",
                "name": "Cashramp P2P",
                "currencies": ["NGN", "KES", "GHS"],
                "fee": "1.8%",
                "settlement": "< 5 seconds",
                "recommended": False,
                "priority": 3,
                "status": "maintenance"
            }
        ]
    }


@router.post("/quote")
async def get_onramp_quote(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """Real-time on-ramp quote (live prices)"""
    
    try:
        data = await request.json()
        amount_fiat = Decimal(str(data.get("amount_fiat", 0)))
        currency = data.get("currency", "NGN")
        crypto_asset = data.get("crypto_asset", "USDT_ALGO")
        
        if amount_fiat <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        settings = get_settings()
        asset_config = settings.SUPPORTED_ASSETS.get(crypto_asset)
        
        if not asset_config:
            raise HTTPException(status_code=400, detail=f"Unsupported asset: {crypto_asset}")
        
        # Get forex rate
        if currency == "USD":
            fiat_to_usd_rate = Decimal("1.0")
        else:
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://api.exchangerate-api.com/v4/latest/USD",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            rates_data = await response.json()
                            fiat_per_usd = Decimal(str(rates_data["rates"].get(currency, 1)))
                            fiat_to_usd_rate = Decimal("1") / fiat_per_usd if fiat_per_usd > 0 else Decimal("1")
                        else:
                            raise Exception(f"ExchangeRate-API returned {response.status}")
            except Exception as forex_error:
                logger.error(f"Forex API failed: {forex_error}")
                raise HTTPException(
                    status_code=503,
                    detail="Cannot get live exchange rates. Please try again."
                )
        
        amount_usd = amount_fiat * fiat_to_usd_rate
        
        # Simple fee calculation: 2.5% total (0.5% Seamount)
        seamount_fee_rate = Decimal("0.005")  # 0.5% Seamount margin
        provider_fee_rate = Decimal("0.020")  # ~2.0% provider cost
        total_fee_rate = seamount_fee_rate + provider_fee_rate
        
        # Get crypto price
        from backend.services.oracle_service import EnhancedOracleService
        oracle_service = EnhancedOracleService(db_service)
        
        oracle_symbol = asset_config.get("oracle_symbol", "bitcoin")
        
        try:
            crypto_price_usd, price_metadata = await oracle_service.get_asset_price(oracle_symbol)
        except Exception as price_error:
            logger.error(f"Price oracle failed: {price_error}")
            raise HTTPException(
                status_code=503,
                detail="Cannot get live crypto prices. Please try again."
            )
        
        # Calculate USD fees first
        total_fee_usd = amount_usd * total_fee_rate
        seamount_fee_usd = amount_usd * seamount_fee_rate
        provider_fee_usd = total_fee_usd - seamount_fee_usd

        # User receives full requested amount (fees are added on top)
        estimated_crypto = amount_usd / crypto_price_usd  # ✅ Full amount

        # Convert fees to fiat currency
        if currency != "USD":
            total_fee_fiat = total_fee_usd / fiat_to_usd_rate
            seamount_fee_fiat = seamount_fee_usd / fiat_to_usd_rate
            provider_fee_fiat = provider_fee_usd / fiat_to_usd_rate
            total_to_charge_fiat = amount_fiat + total_fee_fiat
            usd_to_fiat_rate = Decimal("1") / fiat_to_usd_rate
        else:
            total_fee_fiat = total_fee_usd
            seamount_fee_fiat = seamount_fee_usd
            provider_fee_fiat = provider_fee_usd
            total_to_charge_fiat = amount_fiat + total_fee_fiat
            usd_to_fiat_rate = Decimal("1")
        
        return {
            "success": True,
            "quote": {
                "requested_fiat_amount": float(amount_fiat),  # ✅ What user wants to spend
                "currency": currency,
                "crypto_asset": crypto_asset,
                "blockchain": asset_config["blockchain"],
                
                # Pricing info
                "crypto_price_usd": float(crypto_price_usd),
                "exchange_rate": float(usd_to_fiat_rate),
                "forex_source": "ExchangeRate-API (live)",
                
                # ✅ TRANSPARENT FEE BREAKDOWN:
                "seamount_fee": float(seamount_fee_fiat),
                "seamount_fee_pct": float(seamount_fee_rate * 100),  # e.g., 0.5%
                "provider_fee": float(provider_fee_fiat),
                "provider_fee_pct": float((total_fee_rate - seamount_rate) * 100),
                "total_fee": float(total_fee_fiat),
                "total_fee_pct": float(total_fee_rate * 100),  # e.g., 2.5%
                
                # ✅ WHAT USER PAYS & GETS:
                "total_to_charge": float(total_to_charge_fiat),  # User pays this
                "crypto_to_receive": float(estimated_crypto),    # User gets this
                
                "valid_for_seconds": 300,
                "timestamp": datetime.now().isoformat(),
                "quote_id": f"onramp_quote_{current_user['id'][:8]}_{int(datetime.now().timestamp())}"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quote generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quote failed: {str(e)}")


@router.post("/quote/public")
async def get_public_onramp_quote(request: Request):
    """Public quote endpoint (no auth required)"""
    
    try:
        data = await request.json()
        amount_fiat = Decimal(str(data.get("amount_fiat", 0)))
        currency = data.get("currency", "NGN")
        crypto_asset = data.get("crypto_asset", "USDT_ALGO")
        
        if amount_fiat <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        settings = get_settings()
        asset_config = settings.SUPPORTED_ASSETS.get(crypto_asset)
        
        if not asset_config:
            raise HTTPException(status_code=400, detail=f"Unsupported asset: {crypto_asset}")
        
        from backend.dependencies import get_database_service
        database_service = get_database_service()
        
        # Get forex rate
        if currency == "USD":
            fiat_to_usd_rate = Decimal("1.0")
        else:
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://api.exchangerate-api.com/v4/latest/USD",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            rates_data = await response.json()
                            fiat_per_usd = Decimal(str(rates_data["rates"].get(currency, 1)))
                            fiat_to_usd_rate = Decimal("1") / fiat_per_usd if fiat_per_usd > 0 else Decimal("1")
                        else:
                            raise Exception(f"ExchangeRate-API returned {response.status}")
            except Exception as forex_error:
                logger.error(f"Forex API failed: {forex_error}")
                raise HTTPException(
                    status_code=503,
                    detail="Cannot get live exchange rates. Please try again."
                )
        
        amount_usd = amount_fiat * fiat_to_usd_rate
        
        # Simple fee calculation: 2.5% total (0.5% Seamount)
        seamount_fee_rate = Decimal("0.005")  # 0.5% Seamount margin
        provider_fee_rate = Decimal("0.020")  # ~2.0% provider cost
        total_fee_rate = seamount_fee_rate + provider_fee_rate
        
        # Get crypto price
        from backend.services.oracle_service import EnhancedOracleService
        oracle_service = EnhancedOracleService(database_service)
        
        oracle_symbol = asset_config.get("oracle_symbol", "bitcoin")
        
        try:
            crypto_price_usd, price_metadata = await oracle_service.get_asset_price(oracle_symbol)
        except Exception as price_error:
            logger.error(f"Price oracle failed: {price_error}")
            raise HTTPException(
                status_code=503,
                detail="Cannot get live crypto prices. Please try again."
            )
        
        # Calculate USD fees first
        total_fee_usd = amount_usd * total_fee_rate
        seamount_fee_usd = amount_usd * seamount_fee_rate
        provider_fee_usd = total_fee_usd - seamount_fee_usd

        # User receives full requested amount (fees are added on top)
        estimated_crypto = amount_usd / crypto_price_usd  # ✅ Full amount

        # Convert fees to fiat currency
        if currency != "USD":
            total_fee_fiat = total_fee_usd / fiat_to_usd_rate
            seamount_fee_fiat = seamount_fee_usd / fiat_to_usd_rate
            provider_fee_fiat = provider_fee_usd / fiat_to_usd_rate
            total_to_charge_fiat = amount_fiat + total_fee_fiat
            usd_to_fiat_rate = Decimal("1") / fiat_to_usd_rate
        else:
            total_fee_fiat = total_fee_usd
            seamount_fee_fiat = seamount_fee_usd
            provider_fee_fiat = provider_fee_usd
            total_to_charge_fiat = amount_fiat + total_fee_fiat
            usd_to_fiat_rate = Decimal("1")
        
        return {
            "success": True,
            "quote": {
                "requested_fiat_amount": float(amount_fiat),
                "currency": currency,
                "crypto_asset": crypto_asset,
                "blockchain": asset_config["blockchain"],
                
                # Pricing info
                "crypto_price_usd": float(crypto_price_usd),
                "exchange_rate": float(usd_to_fiat_rate),
                "forex_source": "ExchangeRate-API (live)",
                
                # ✅ FEE BREAKDOWN (with updated mobile money rate: 0.6% Seamount):
                "seamount_fee": float(seamount_fee_fiat),
                "seamount_fee_pct": float(seamount_fee_rate * 100),
                "provider_fee": float(provider_fee_fiat),
                "provider_fee_pct": float((total_fee_rate - seamount_fee_rate) * 100),
                "total_fee": float(total_fee_fiat),
                "total_fee_pct": float(total_fee_rate * 100),
                
                # ✅ WHAT USER PAYS & GETS:
                "total_to_charge": float(total_to_charge_fiat),
                "crypto_to_receive": float(estimated_crypto),
                
                "valid_for_seconds": 300,
                "timestamp": datetime.now().isoformat(),
                "quote_id": f"public_onramp_quote_{int(datetime.now().timestamp())}"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Public quote failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quote failed: {str(e)}")