# File: backend/api/routes/offramp.py
"""
Off-Ramp Routes - Cashramp/Paystack/Flutterwave Integration
PRIORITY ORDER: Cashramp (P2P) → Paystack (Bank Transfers) → Flutterwave (International)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
import logging
import aiohttp

from backend.config import get_settings
from backend.dependencies import get_current_user, get_db_service, get_audit_service
from backend.services.offramp_service import OfframpService
from backend.services.payment_providers.paystack import PaystackProvider
from backend.services.cashramp_service import CashrampService
from backend.services.oracle_service import EnhancedOracleService
from backend.services.payment_providers.pretium import PretiumProvider

router = APIRouter(prefix="/offramp", tags=["Off-Ramp"])
logger = logging.getLogger(__name__)


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class WithdrawalRequest(BaseModel):
    crypto_asset: str
    crypto_amount: float
    recipient_details: Dict[str, str]


# ============================================
# QUOTE ENDPOINTS (AUTHENTICATED)
# ============================================

@router.post("/quote")
async def get_offramp_quote(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    🎯 REAL-TIME OFFRAMP QUOTE - CRYPTO → FIAT
    
    Uses:
    - EnhancedOracleService for crypto prices
    - ExchangeRate-API for live forex rates
    - Multi-currency support (NGN, KES, GHS, ZAR, etc.)
    """
    
    try:
        data = await request.json()
        crypto_amount = Decimal(str(data.get("crypto_amount", 0)))
        crypto_asset = data.get("crypto_asset", "USDT_ALGO")
        fiat_currency = data.get("fiat_currency", "NGN")
        
        if crypto_amount <= 0:
            raise HTTPException(
                status_code=400, 
                detail="Amount must be greater than 0"
            )
        
        # 📍 STEP 1: Get asset config
        settings = get_settings()
        asset_config = settings.SUPPORTED_ASSETS.get(crypto_asset)
        
        if not asset_config:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported asset: {crypto_asset}"
            )
        
        # 📍 STEP 2: Get real crypto price
        oracle_service = EnhancedOracleService(db_service)
        oracle_symbol = asset_config.get("oracle_symbol", "bitcoin")
        
        try:
            crypto_price_usd, price_metadata = await oracle_service.get_asset_price(oracle_symbol)
            logger.info(
                f"✅ Live crypto price: {crypto_asset} = ${crypto_price_usd} "
                f"(source: {price_metadata.get('source')})"
            )
        except Exception as price_error:
            logger.error(f"❌ Price oracle failed: {price_error}")
            raise HTTPException(
                status_code=503,
                detail="Cannot get live crypto prices. Please try again."
            )
        
        # Calculate USD value
        crypto_value_usd = crypto_amount * crypto_price_usd
        
        # 📍 STEP 3: Get real forex rate
        if fiat_currency == "USD":
            usd_to_fiat_rate = Decimal("1.0")
        else:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://api.exchangerate-api.com/v4/latest/USD",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            rates_data = await response.json()
                            usd_to_fiat_rate = Decimal(str(rates_data["rates"].get(fiat_currency, 1)))
                            logger.info(f"✅ Live forex: 1 USD = {usd_to_fiat_rate} {fiat_currency}")
                        else:
                            raise Exception(f"ExchangeRate-API returned {response.status}")
            except Exception as forex_error:
                logger.error(f"❌ Forex API failed: {forex_error}")
                raise HTTPException(
                    status_code=503,
                    detail="Cannot get live exchange rates. Please try again."
                )
        
        # Convert to fiat currency
        gross_fiat_amount = crypto_value_usd * usd_to_fiat_rate
        
        # ✅ STEP 4: Calculate fees (currency-sensitive rates)
        # OFF-RAMP FEE STRUCTURE:
        # NGN (instant bank): 2.0%
        # KES (mobile money): 2.5%
        # GHS (mobile money): 2.5%
        # UGX (mobile money): 3.0%
        # International:      2.5-3.0%
        
        FEE_RATES = {
            "NGN": Decimal("0.020"),  # 2.0%
            "KES": Decimal("0.025"),  # 2.5%
            "GHS": Decimal("0.025"),  # 2.5%
            "UGX": Decimal("0.030"),  # 3.0%
            "ZAR": Decimal("0.025"),  # 2.5%
            "TZS": Decimal("0.030"),  # 3.0%
            "MWK": Decimal("0.025"),  # 2.5%
            "ETB": Decimal("0.025"),  # 2.5%
            "CDF": Decimal("0.030"),  # 3.0%
            "RWF": Decimal("0.030"),  # 3.0%
            "ZMW": Decimal("0.030"),  # 3.0%
        }
        
        fee_rate = FEE_RATES.get(fiat_currency, Decimal("0.025"))  # Default 2.5%
        withdrawal_fee_fiat = gross_fiat_amount * fee_rate
        withdrawal_fee_usd = crypto_value_usd * fee_rate
        
        # Net amount user receives
        net_fiat_amount = gross_fiat_amount - withdrawal_fee_fiat
        
        quote_response = {
            "success": True,
            "quote": {
                "crypto_amount": float(crypto_amount),
                "crypto_asset": crypto_asset,
                "blockchain": asset_config["blockchain"],
                "fiat_currency": fiat_currency,
                
                # Crypto pricing (LIVE!)
                "crypto_price_usd": float(crypto_price_usd),
                "price_source": price_metadata.get("source", "oracle"),
                "price_confidence": price_metadata.get("confidence", 0.95),
                
                # Forex rates (LIVE!)
                "exchange_rate": float(usd_to_fiat_rate),
                "forex_source": "ExchangeRate-API (live)",
                
                # Amounts
                "crypto_value_usd": float(crypto_value_usd),
                "gross_fiat_amount": float(gross_fiat_amount),
                "withdrawal_fee": float(withdrawal_fee_fiat),
                "withdrawal_fee_usd": float(withdrawal_fee_usd),
                "net_fiat_amount": float(net_fiat_amount),
                "fee_percentage": float(fee_rate * 100),
                
                # Quote metadata
                "valid_for_seconds": 300,
                "timestamp": datetime.now().isoformat(),
                "quote_id": f"offramp_quote_{current_user['id'][:8]}_{int(datetime.now().timestamp())}"
            }
        }
        
        logger.info(
            f"✅ Offramp quote generated: {crypto_amount} {crypto_asset} "
            f"→ {net_fiat_amount:.2f} {fiat_currency}"
        )
        
        return quote_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Offramp quote generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Quote generation failed: {str(e)}"
        )


# ============================================
# QUOTE ENDPOINTS (PUBLIC/UNAUTHENTICATED)
# ============================================

@router.post("/quote/public")
async def get_public_offramp_quote(request: Request):
    """
    🎯 PUBLIC offramp quote - no authentication required
    For unauthenticated users to see pricing
    """
    try:
        data = await request.json()
        crypto_amount = Decimal(str(data.get("crypto_amount", 0)))
        crypto_asset = data.get("crypto_asset", "USDT_ALGO")
        fiat_currency = data.get("fiat_currency", "NGN")
        
        if crypto_amount <= 0:
            raise HTTPException(
                status_code=400, 
                detail="Amount must be greater than 0"
            )
        
        # 📍 STEP 1: Get asset config
        settings = get_settings()
        asset_config = settings.SUPPORTED_ASSETS.get(crypto_asset)
        
        if not asset_config:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported asset: {crypto_asset}"
            )
        
        # 📍 STEP 2: Get database service (no await needed)
        from backend.dependencies import get_database_service
        database_service = get_database_service()
        
        # 📍 STEP 3: Get real crypto price
        oracle_service = EnhancedOracleService(database_service)
        oracle_symbol = asset_config.get("oracle_symbol", "bitcoin")
        
        try:
            crypto_price_usd, price_metadata = await oracle_service.get_asset_price(oracle_symbol)
            logger.info(f"✅ Public offramp - Live crypto price: {crypto_asset} = ${crypto_price_usd}")
        except Exception as price_error:
            logger.error(f"❌ Public offramp price oracle failed: {price_error}")
            raise HTTPException(
                status_code=503,
                detail="Cannot get live crypto prices. Please try again."
            )
        
        # Calculate USD value
        crypto_value_usd = crypto_amount * crypto_price_usd
        
        # 📍 STEP 4: Get real forex rate
        if fiat_currency == "USD":
            usd_to_fiat_rate = Decimal("1.0")
        else:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://api.exchangerate-api.com/v4/latest/USD",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            rates_data = await response.json()
                            usd_to_fiat_rate = Decimal(str(rates_data["rates"].get(fiat_currency, 1)))
                            logger.info(f"✅ Public offramp - Live forex: 1 USD = {usd_to_fiat_rate} {fiat_currency}")
                        else:
                            raise Exception(f"ExchangeRate-API returned {response.status}")
            except Exception as forex_error:
                logger.error(f"❌ Public offramp forex API failed: {forex_error}")
                raise HTTPException(
                    status_code=503,
                    detail="Cannot get live exchange rates. Please try again."
                )
        
        # Convert to fiat currency
        gross_fiat_amount = crypto_value_usd * usd_to_fiat_rate
        
        # ✅ STEP 5: Calculate fees (currency-sensitive rates)
        FEE_RATES = {
            "NGN": Decimal("0.020"),  # 2.0%
            "KES": Decimal("0.025"),  # 2.5%
            "GHS": Decimal("0.025"),  # 2.5%
            "UGX": Decimal("0.030"),  # 3.0%
            "ZAR": Decimal("0.025"),  # 2.5%
            "TZS": Decimal("0.030"),  # 3.0%
            "RWF": Decimal("0.030"),  # 3.0%
            "ZMW": Decimal("0.030"),  # 3.0%
        }
        
        fee_rate = FEE_RATES.get(fiat_currency, Decimal("0.025"))
        withdrawal_fee_fiat = gross_fiat_amount * fee_rate
        withdrawal_fee_usd = crypto_value_usd * fee_rate
        
        # Net amount user receives
        net_fiat_amount = gross_fiat_amount - withdrawal_fee_fiat
        
        quote_response = {
            "success": True,
            "quote": {
                "crypto_amount": float(crypto_amount),
                "crypto_asset": crypto_asset,
                "blockchain": asset_config["blockchain"],
                "fiat_currency": fiat_currency,
                
                # Crypto pricing (LIVE!)
                "crypto_price_usd": float(crypto_price_usd),
                "price_source": price_metadata.get("source", "oracle"),
                "price_confidence": price_metadata.get("confidence", 0.95),
                
                # Forex rates (LIVE!)
                "exchange_rate": float(usd_to_fiat_rate),
                "forex_source": "ExchangeRate-API (live)",
                
                # Amounts
                "crypto_value_usd": float(crypto_value_usd),
                "gross_fiat_amount": float(gross_fiat_amount),
                "withdrawal_fee": float(withdrawal_fee_fiat),
                "withdrawal_fee_usd": float(withdrawal_fee_usd),
                "net_fiat_amount": float(net_fiat_amount),
                "fee_percentage": float(fee_rate * 100),
                
                # Quote metadata
                "valid_for_seconds": 300,
                "timestamp": datetime.now().isoformat(),
                "quote_id": f"public_offramp_quote_{int(datetime.now().timestamp())}"
            }
        }
        
        logger.info(
            f"✅ Public offramp quote generated: {crypto_amount} {crypto_asset} "
            f"→ {net_fiat_amount:.2f} {fiat_currency}"
        )
        
        return quote_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Public offramp quote generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Quote generation failed: {str(e)}"
        )


# ============================================
# WITHDRAWAL ENDPOINT
# ============================================

@router.post("/withdraw")
async def withdraw(
    request: WithdrawalRequest,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """
    Execute crypto → fiat withdrawal
    ✅ Checks actual user balance
    ✅ Executes payout via Paystack/Flutterwave
    ✅ NO MINIMUM RESTRICTIONS
    """
    
    try:
        settings = get_settings()
        crypto_amount = Decimal(str(request.crypto_amount))
        crypto_asset = request.crypto_asset
        recipient_details = request.recipient_details
        
        # ✅ STEP 1: Get user's actual balance from database
        try:
            balance_query = db_service.supabase.from_('wallet_balances')\
                .select('*')\
                .eq('user_id', current_user["id"])\
                .limit(1)\
                .execute()
            
            if not balance_query.data:
                raise HTTPException(status_code=400, detail="Wallet not found. Please create wallet first.")
            
            balance_row = balance_query.data[0]
            
            # Map crypto asset to balance column
            ASSET_TO_COLUMN = {
                'ALGO': 'algo_balance',
                'USDT_ALGO': 'usdt_balance',
                'USDCa': 'usdca_balance',
                'goBTC': 'gobtc_balance',
                'goETH': 'goeth_balance',
                'BTC': 'btc_balance',
                'ETH': 'eth_balance',
                'MATIC': 'matic_balance',
                'TRX': 'trx_balance',
                'USDT_TRON': 'usdt_tron_balance'
            }
            
            balance_column = ASSET_TO_COLUMN.get(crypto_asset)
            if not balance_column:
                raise HTTPException(status_code=400, detail=f"Unsupported asset: {crypto_asset}")
            
            current_balance = Decimal(str(balance_row.get(balance_column, 0)))
            
            logger.info(f"💰 User {current_user['id']} balance: {current_balance} {crypto_asset}")
            
            # ✅ Check sufficient balance (NO MINIMUM!)
            if current_balance < crypto_amount:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient balance. Available: {current_balance} {crypto_asset}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Balance check failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to check balance")
        
        # ✅ STEP 2: Get asset config & calculate amounts
        asset_config = settings.SUPPORTED_ASSETS.get(crypto_asset)
        if not asset_config:
            raise HTTPException(status_code=400, detail=f"Unsupported asset: {crypto_asset}")
        
        # Get crypto price
        oracle_service = EnhancedOracleService(db_service)
        oracle_symbol = asset_config.get("oracle_symbol", "algorand")
        
        try:
            crypto_price_usd, price_metadata = await oracle_service.get_asset_price(oracle_symbol)
            crypto_value_usd = crypto_amount * crypto_price_usd
        except Exception as e:
            logger.error(f"❌ Price oracle failed: {e}")
            raise HTTPException(status_code=503, detail="Cannot get live prices")
        
        # Get forex rate
        fiat_currency = recipient_details.get("currency", "NGN")
        
        if fiat_currency == "USD":
            usd_to_fiat_rate = Decimal("1.0")
        else:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://api.exchangerate-api.com/v4/latest/USD",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            rates_data = await response.json()
                            usd_to_fiat_rate = Decimal(str(rates_data["rates"].get(fiat_currency, 1)))
                        else:
                            raise Exception("Forex API failed")
            except Exception as e:
                logger.error(f"❌ Forex failed: {e}")
                raise HTTPException(status_code=503, detail="Cannot get exchange rates")
        
        gross_fiat_amount = crypto_value_usd * usd_to_fiat_rate
        
        # Calculate fee (1.8%)
        fee_rate = Decimal("0.018")
        withdrawal_fee = gross_fiat_amount * fee_rate
        net_fiat_amount = gross_fiat_amount - withdrawal_fee
        
        # ✅ STEP 3: Execute payout via Paystack or Flutterwave
        payment_method = recipient_details.get("payment_method", "bank_transfer")
        provider = None
        payout_result = None
        
        # Try Paystack first (NGN only, best rates)
        if fiat_currency == "NGN" and payment_method == "bank_transfer":
            try:
                logger.info(f"🏦 Routing to Paystack for {net_fiat_amount} NGN")
                
                paystack = PaystackProvider(settings)
                
                bank_details = {
                    "account_name": recipient_details.get("account_name"),
                    "account_number": recipient_details.get("account_number"),
                    "bank_code": recipient_details.get("bank_code")
                }
                
                payout_result = await paystack.initiate_payout(
                    amount=net_fiat_amount,
                    bank_details=bank_details,
                    tx_ref=f"OFFRAMP_{current_user['id'][:8]}_{int(datetime.now().timestamp())}"
                )
                
                if payout_result and payout_result.get("success"):
                    provider = "paystack"
                    logger.info(f"✅ Paystack payout initiated")
                else:
                    raise Exception(payout_result.get('message', 'Paystack failed'))
                    
            except Exception as paystack_error:
                logger.warning(f"⚠️ Paystack failed: {paystack_error}")
                # Fall through to Flutterwave
        
        # Fallback to Flutterwave (multi-currency, mobile money)
        if not provider:
            try:
                logger.info(f"🌍 Routing to Flutterwave for {net_fiat_amount} {fiat_currency}")
                
                flutterwave = FlutterwaveProvider(settings)
                
                bank_details = {
                    "account_name": recipient_details.get("account_name"),
                    "account_number": recipient_details.get("account_number"),
                    "bank_code": recipient_details.get("bank_code"),
                    "currency": fiat_currency
                }
                
                payout_result = await flutterwave.initiate_payout(
                    amount=net_fiat_amount,
                    bank_details=bank_details,
                    tx_ref=f"OFFRAMP_{current_user['id'][:8]}_{int(datetime.now().timestamp())}"
                )
                
                if payout_result and payout_result.get("success"):
                    provider = "flutterwave"
                    logger.info(f"✅ Flutterwave payout initiated")
                else:
                    raise Exception(payout_result.get('message', 'Flutterwave failed'))
                    
            except Exception as fw_error:
                logger.error(f"❌ All providers failed! Last error: {fw_error}")
                raise HTTPException(
                    status_code=503,
                    detail="Payment providers unavailable. Please try again later."
                )
        
        # ✅ STEP 4: Deduct from user balance
        try:
            new_balance = current_balance - crypto_amount
            
            update_query = db_service.supabase.from_('wallet_balances')\
                .update({balance_column: float(new_balance), 'updated_at': 'NOW()'})\
                .eq('user_id', current_user["id"])\
                .execute()
            
            logger.info(f"✅ Deducted {crypto_amount} {crypto_asset} from user {current_user['id']}")
            
        except Exception as balance_error:
            logger.error(f"❌ Failed to update balance: {balance_error}")
            raise HTTPException(status_code=500, detail="Failed to process withdrawal")
        
        # ✅ STEP 5: Store transaction record
        tx_id = f"OFFRAMP_{current_user['id'][:8]}_{int(datetime.now().timestamp())}"
        
        tx_data = {
            "id": tx_id,
            "user_id": current_user["id"],
            "type": "offramp",
            "status": "processing",
            "provider": provider,
            "crypto_asset": crypto_asset,
            "crypto_amount": float(crypto_amount),
            "fiat_currency": fiat_currency,
            "gross_fiat_amount": float(gross_fiat_amount),
            "withdrawal_fee": float(withdrawal_fee),
            "net_fiat_amount": float(net_fiat_amount),
            "recipient_details": recipient_details,
            "exchange_rate": float(usd_to_fiat_rate),
            "created_at": datetime.now().isoformat()
        }
        
        try:
            await db_service.supabase.from_('offramp_transactions').insert(tx_data).execute()
        except Exception as db_error:
            logger.error(f"❌ Failed to store transaction: {db_error}")
        
        # Log audit
        if audit_service:
            try:
                await audit_service.log_event(
                    "OFFRAMP_INITIATED",
                    user_id=current_user["id"],
                    resource_id=tx_id,
                    details={
                        "provider": provider,
                        "crypto_amount": float(crypto_amount),
                        "crypto_asset": crypto_asset,
                        "fiat_amount": float(net_fiat_amount),
                        "currency": fiat_currency
                    }
                )
            except Exception as audit_error:
                logger.warning(f"⚠️ Failed to log audit: {audit_error}")
        
        return {
            "success": True,
            "transaction_id": tx_id,
            "provider": provider,
            "crypto_amount": float(crypto_amount),
            "crypto_asset": crypto_asset,
            "fiat_amount": float(net_fiat_amount),
            "currency": fiat_currency,
            "withdrawal_fee": float(withdrawal_fee),
            "status": "processing",
            "estimated_settlement": "1-2 hours"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Withdrawal failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Withdrawal failed: {str(e)}")


# ============================================
# WEBHOOK ENDPOINT
# ============================================

@router.post("/webhook/{provider}")
async def handle_webhook(
    provider: str,
    request: Request,
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Handle payout webhooks from providers"""
    
    try:
        payload = await request.json()
        logger.info(f"📨 Webhook received from {provider}: {payload.get('event')}")
        
        settings = get_settings()
        
        # Route to correct provider
        if provider == "cashramp":
            cashramp = CashrampService(db_service)
            result = await cashramp.verify_payout(payload.get("reference"))
            
            if result.get("verified"):
                await _mark_withdrawal_complete(
                    db_service,
                    payload.get("reference"),
                    "completed"
                )
                
        elif provider == "paystack":
            paystack = PaystackProvider(settings)
            result = await paystack.verify_payout(payload.get("reference"))
            
            if result.get("verified"):
                await _mark_withdrawal_complete(
                    db_service,
                    payload.get("reference"),
                    "completed"
                )
        
        return {"status": "success", "processed": True}
        
    except Exception as e:
        logger.error(f"❌ Webhook processing failed: {e}")
        return {"status": "error", "message": str(e)}


async def _mark_withdrawal_complete(db_service, tx_ref: str, status: str):
    """Mark withdrawal as complete"""
    try:
        await db_service.supabase.from_('offramp_transactions')\
            .update({'status': status, 'completed_at': 'NOW()'})\
            .eq('id', tx_ref)\
            .execute()
        
        logger.info(f"✅ Withdrawal {tx_ref} marked as {status}")
    except Exception as e:
        logger.error(f"❌ Failed to update withdrawal status: {e}")


# ============================================
# LIMITS ENDPOINT
# ============================================

@router.get("/limits/{country}")
async def get_limits(country: str):
    """Get withdrawal limits for country"""
    
    limits = {
        "NG": {
            "min_withdrawal_ngn": 5000,
            "max_withdrawal_ngn": 10000000,
            "daily_limit_ngn": 5000000,
            "supported_methods": ["bank_transfer", "mobile_money"],
            "providers": ["cashramp", "paystack", "flutterwave"]
        },
        "KE": {
            "min_withdrawal_kes": 500,
            "max_withdrawal_kes": 5000000,
            "daily_limit_kes": 2000000,
            "supported_methods": ["mobile_money", "bank_transfer"],
            "providers": ["cashramp", "flutterwave"]
        },
        "GH": {
            "min_withdrawal_ghs": 50,
            "max_withdrawal_ghs": 500000,
            "daily_limit_ghs": 200000,
            "supported_methods": ["mobile_money", "bank_transfer"],
            "providers": ["cashramp", "flutterwave"]
        }
    }
    
    return {
        "success": True,
        "country": country,
        "limits": limits.get(country, limits["NG"])
    }


# ============================================
# PROVIDERS ENDPOINT
# ============================================

@router.get("/providers")
async def get_providers():
    """Get available offramp providers (updated priority order)"""
    
    return {
        "providers": [
            {
                "id": "cashramp",
                "name": "Cashramp P2P",
                "currencies": ["NGN", "KES", "GHS"],
                "methods": ["mobile_money", "bank_transfer"],
                "fee": "1.8%",
                "settlement": "< 5 seconds",
                "recommended": True,
                "priority": 1
            },
            {
                "id": "paystack",
                "name": "Paystack",
                "currencies": ["NGN"],
                "methods": ["bank_transfer"],
                "fee": "1.8%",
                "settlement": "1-2 hours",
                "recommended": True,
                "priority": 2
            },
            {
                "id": "flutterwave",
                "name": "Flutterwave",
                "currencies": ["NGN", "KES", "GHS", "ZAR", "USD", "EUR"],
                "methods": ["bank_transfer"],
                "fee": "2.5%",
                "settlement": "2-4 hours",
                "recommended": False,
                "priority": 3
            }
        ]
    }