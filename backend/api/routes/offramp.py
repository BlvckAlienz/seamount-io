# File: backend/api/routes/offramp.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any
from decimal import Decimal
from datetime import datetime  # ✅ ADD THIS
import logging
import aiohttp

from backend.config import get_settings  # ✅ ADD THIS

from backend.dependencies import get_current_user, get_db_service, get_audit_service
from backend.services.offramp_service import OfframpService
from backend.services.payment_providers.paystack import PaystackProvider
from backend.services.cashramp_service import CashrampService
from backend.services.oracle_service import EnhancedOracleService
from backend.config import settings

router = APIRouter(prefix="/offramp", tags=["Off-Ramp"])

logger = logging.getLogger(__name__)

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
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        # Get asset config
        settings = get_settings()
        asset_config = settings.SUPPORTED_ASSETS.get(crypto_asset)
        
        if not asset_config:
            raise HTTPException(status_code=400, detail=f"Unsupported asset: {crypto_asset}")
        
        # 🎯 STEP 1: GET REAL CRYPTO PRICE
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
        
        # Calculate USD value
        crypto_value_usd = crypto_amount * crypto_price_usd
        
        # 🎯 STEP 2: GET REAL FOREX RATE
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
        
        # 🎯 STEP 3: CALCULATE FEES (1.8% withdrawal fee)
        fee_rate = Decimal("0.018")
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
                "fee_percentage": 1.8,
                
                # Quote metadata
                "valid_for_seconds": 300,
                "timestamp": datetime.now().isoformat(),
                "quote_id": f"offramp_quote_{current_user['id'][:8]}_{int(datetime.now().timestamp())}"
            }
        }
        
        logger.info(f"✅ Offramp quote generated: {crypto_amount} {crypto_asset} → {net_fiat_amount:.2f} {fiat_currency}")
        
        return quote_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Offramp quote generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quote generation failed: {str(e)}")

class WithdrawalRequest(BaseModel):
    crypto_asset: str
    crypto_amount: float
    recipient_details: Dict[str, str]

@router.post("/withdraw")
async def withdraw(
    request: WithdrawalRequest,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Initialize crypto→fiat withdrawal"""
    
    paystack = PaystackProvider(settings)
    cashramp = CashrampService(db_service)
    oracle = EnhancedOracleService(db_service)
    
    service = OfframpService(db_service, audit_service, paystack, cashramp, oracle)
    
    return await service.initialize_withdrawal(
        user_id=current_user["id"],
        crypto_asset=request.crypto_asset,
        crypto_amount=request.crypto_amount,
        recipient_details=request.recipient_details
    )

@router.post("/webhook/{provider}")
async def handle_webhook(
    provider: str,
    request: Request,
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Handle payout webhooks"""
    
    paystack = PaystackProvider(settings)
    cashramp = CashrampService(db_service)
    oracle = EnhancedOracleService(db_service)
    
    service = OfframpService(db_service, audit_service, paystack, cashramp, oracle)
    payload = await request.json()
    
    return await service.handle_payout_webhook(provider, payload)

@router.get("/limits/{country}")
async def get_limits(
    country: str,
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Get withdrawal limits for country"""
    
    paystack = PaystackProvider(settings)
    cashramp = CashrampService(db_service)
    oracle = EnhancedOracleService(db_service)
    
    service = OfframpService(db_service, audit_service, paystack, cashramp, oracle)
    
    return await service.get_withdrawal_limits(country)