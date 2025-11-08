# File: backend/api/routes/onramp.py
"""
On-Ramp Routes - Paystack/Flutterwave/Cashramp Integration
MAXIMIZE REVENUE: Use our own providers instead of aggregators
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

@router.post("/quote")
async def get_onramp_quote(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    🎯 REAL-TIME QUOTE - NO MOCKS OR HARDCODED RATES!
    
    Uses:
    - EnhancedOracleService for crypto prices (3-tier: Binance → CoinGecko → DIA)
    - ExchangeRate-API for live forex rates
    """
    
    try:
        data = await request.json()
        amount_fiat = Decimal(str(data.get("amount_fiat", 0)))
        currency = data.get("currency", "NGN")
        crypto_asset = data.get("crypto_asset", "USDT_ALGO")
        
        if amount_fiat <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        # Get asset config
        settings = get_settings()
        asset_config = settings.SUPPORTED_ASSETS.get(crypto_asset)
        
        if not asset_config:
            raise HTTPException(status_code=400, detail=f"Unsupported asset: {crypto_asset}")
        
        # 🎯 STEP 1: GET REAL FOREX RATE (NO HARDCODING!)
        if currency == "USD":
            fiat_to_usd_rate = Decimal("1.0")
        else:
            # Use ExchangeRate-API (free tier: 1500 requests/month)
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
                            logger.info(f"✅ Live forex: 1 USD = {fiat_per_usd} {currency}")
                        else:
                            raise Exception(f"ExchangeRate-API returned {response.status}")
            except Exception as forex_error:
                logger.error(f"❌ Forex API failed: {forex_error}")
                raise HTTPException(
                    status_code=503, 
                    detail="Cannot get live exchange rates. Please try again."
                )
        
        # Convert fiat to USD
        amount_usd = amount_fiat * fiat_to_usd_rate
        
        # 🎯 STEP 2: GET REAL CRYPTO PRICE
        from backend.services.oracle_service import EnhancedOracleService
        oracle_service = EnhancedOracleService(db_service)
        
        oracle_symbol = asset_config.get("oracle_symbol", "bitcoin")
        
        try:
            crypto_price_usd, price_metadata = await oracle_service.get_asset_price(oracle_symbol)
            logger.info(f"✅ Live crypto price: {crypto_asset} = ${crypto_price_usd} (source: {price_metadata.get('source')})")
        except Exception as price_error:
            logger.error(f"❌ Price oracle failed: {price_error}")
            raise HTTPException(
                status_code=503,
                detail="Cannot get live crypto prices. Please try again."
            )
        
        # 🎯 STEP 3: CALCULATE FEES (1.8% platform fee)
        platform_fee_usd = amount_usd * Decimal("0.018")
        net_usd = amount_usd - platform_fee_usd
        
        # Calculate crypto amount
        estimated_crypto = net_usd / crypto_price_usd
        
        # Convert fees back to user's currency
        platform_fee_fiat = platform_fee_usd / fiat_to_usd_rate if currency != "USD" else platform_fee_usd
        
        quote_response = {
            "success": True,
            "quote": {
                "amount_fiat": float(amount_fiat),
                "currency": currency,
                "crypto_asset": crypto_asset,
                "blockchain": asset_config["blockchain"],
                
                # Exchange rates (LIVE!)
                "exchange_rate": float(Decimal("1") / fiat_to_usd_rate) if currency != "USD" else 1.0,
                "forex_source": "ExchangeRate-API (live)",
                
                # Crypto pricing (LIVE!)
                "crypto_price_usd": float(crypto_price_usd),
                "price_source": price_metadata.get("source", "oracle"),
                "price_confidence": price_metadata.get("confidence", 0.95),
                
                # Amounts
                "amount_usd": float(amount_usd),
                "platform_fee": float(platform_fee_fiat),
                "platform_fee_usd": float(platform_fee_usd),
                "estimated_crypto_amount": float(estimated_crypto),
                
                # Quote metadata
                "valid_for_seconds": 300,  # 5 minutes
                "timestamp": datetime.now().isoformat(),
                "quote_id": f"quote_{current_user['id'][:8]}_{int(datetime.now().timestamp())}"
            }
        }
        
        logger.info(f"✅ Quote generated: {amount_fiat} {currency} → {estimated_crypto:.6f} {crypto_asset}")
        
        return quote_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Quote generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quote generation failed: {str(e)}")
    
@router.post("/quote/public")
async def get_public_onramp_quote(request: Request):
    """
    🎯 PUBLIC quote endpoint - no authentication required
    For unauthenticated users to see pricing
    """
    try:
        data = await request.json()
        amount_fiat = Decimal(str(data.get("amount_fiat", 0)))
        currency = data.get("currency", "NGN")
        crypto_asset = data.get("crypto_asset", "USDT_ALGO")
        
        if amount_fiat <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        # Get asset config
        settings = get_settings()
        asset_config = settings.SUPPORTED_ASSETS.get(crypto_asset)
        
        if not asset_config:
            raise HTTPException(status_code=400, detail=f"Unsupported asset: {crypto_asset}")
        
        # 🎯 FIX: Get database service properly
        from backend.dependencies import get_database_service
        database_service = await get_database_service()  # 🎯 CORRECT NAME
        
        # 🎯 STEP 1: GET REAL FOREX RATE
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
                            logger.info(f"✅ Public quote - Live forex: 1 USD = {fiat_per_usd} {currency}")
                        else:
                            raise Exception(f"ExchangeRate-API returned {response.status}")
            except Exception as forex_error:
                logger.error(f"❌ Public quote forex API failed: {forex_error}")
                raise HTTPException(
                    status_code=503, 
                    detail="Cannot get live exchange rates. Please try again."
                )
        
        # Convert fiat to USD
        amount_usd = amount_fiat * fiat_to_usd_rate
        
        # 🎯 STEP 2: GET REAL CRYPTO PRICE
        from backend.services.oracle_service import EnhancedOracleService
        oracle_service = EnhancedOracleService(database_service)  # 🎯 USE CORRECT NAME
        
        oracle_symbol = asset_config.get("oracle_symbol", "bitcoin")
        
        try:
            crypto_price_usd, price_metadata = await oracle_service.get_asset_price(oracle_symbol)
            logger.info(f"✅ Public quote - Live crypto price: {crypto_asset} = ${crypto_price_usd}")
        except Exception as price_error:
            logger.error(f"❌ Public quote price oracle failed: {price_error}")
            raise HTTPException(
                status_code=503,
                detail="Cannot get live crypto prices. Please try again."
            )
        
        # 🎯 STEP 3: CALCULATE FEES (1.8% platform fee)
        platform_fee_usd = amount_usd * Decimal("0.018")
        net_usd = amount_usd - platform_fee_usd
        
        # Calculate crypto amount
        estimated_crypto = net_usd / crypto_price_usd
        
        # Convert fees back to user's currency
        platform_fee_fiat = platform_fee_usd / fiat_to_usd_rate if currency != "USD" else platform_fee_usd
        
        quote_response = {
            "success": True,
            "quote": {
                "amount_fiat": float(amount_fiat),
                "currency": currency,
                "crypto_asset": crypto_asset,
                "blockchain": asset_config["blockchain"],
                
                # Exchange rates (LIVE!)
                "exchange_rate": float(Decimal("1") / fiat_to_usd_rate) if currency != "USD" else 1.0,
                "forex_source": "ExchangeRate-API (live)",
                
                # Crypto pricing (LIVE!)
                "crypto_price_usd": float(crypto_price_usd),
                "price_source": price_metadata.get("source", "oracle"),
                "price_confidence": price_metadata.get("confidence", 0.95),
                
                # Amounts
                "amount_usd": float(amount_usd),
                "platform_fee": float(platform_fee_fiat),
                "platform_fee_usd": float(platform_fee_usd),
                "estimated_crypto_amount": float(estimated_crypto),
                
                # Quote metadata
                "valid_for_seconds": 300,
                "timestamp": datetime.now().isoformat(),
                "quote_id": f"public_quote_{int(datetime.now().timestamp())}"
            }
        }
        
        logger.info(f"✅ Public quote generated: {amount_fiat} {currency} → {estimated_crypto:.6f} {crypto_asset}")
        
        return quote_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Public quote generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quote generation failed: {str(e)}")