# File Location: backend/api/routes/payments.py

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
from decimal import Decimal
import uuid
import logging
from datetime import datetime
from backend.dependencies import get_supabase_client
from backend.services.payment_providers.paystack import PaystackProvider
from backend.services.payment_providers.flutterwave import FlutterwaveProvider
from backend.config import get_settings
from backend.services.database_service import DatabaseService
from backend.services.oracle_service import EnhancedOracleService
from supabase import Client
from slowapi import Limiter
from slowapi.util import get_remote_address

import logging
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

class DepositRequest(BaseModel):
    user_id: str
    user_email: EmailStr
    amount: float
    currency: str
    user_country: str

class OnRampRequest(BaseModel):
    user_id: str
    user_email: EmailStr
    user_phone: str
    amount_fiat: float

class PaymentSmartRouter:
    """Routes payments to optimal provider based on region/currency"""
    
    def __init__(self):
        self.settings = get_settings()
        try:
            self.paystack = PaystackProvider(self.settings) if hasattr(self.settings, 'PAYSTACK_SECRET_KEY') and self.settings.PAYSTACK_SECRET_KEY else None
            self.flutterwave = FlutterwaveProvider(self.settings) if hasattr(self.settings, 'FLUTTERWAVE_SECRET_KEY') and self.settings.FLUTTERWAVE_SECRET_KEY else None
        except Exception as e:
            logger.error(f"Failed to initialize payment providers: {e}")
            self.paystack = None
            self.flutterwave = None
    
    def select_provider(self, currency: str, country: str, amount: float) -> str:
        """Smart routing logic - prioritize Paystack for NGN"""
        
        # Paystack is optimal for Nigerian Naira
        if currency == "NGN" and self.paystack:
            return "paystack"
        
        # Flutterwave as fallback for all other currencies
        if self.flutterwave:
            return "flutterwave"
        
        # If no providers are available, raise an error
        raise HTTPException(
            status_code=503, 
            detail="No payment providers configured. Please contact support."
        )
    
    async def initialize_payment(self, provider: str, deposit_data: Dict) -> Dict:
        """Initialize payment with selected provider"""
        try:
            if provider == "paystack" and self.paystack:
                return await self.paystack.initialize_payment(deposit_data)
            elif provider == "flutterwave" and self.flutterwave:
                return await self.flutterwave.initialize_payment(deposit_data)
            else:
                raise ValueError(f"Provider {provider} not available")
                
        except Exception as e:
            logger.error(f"Payment initialization failed with {provider}: {e}")
            raise HTTPException(status_code=500, detail=f"Payment initialization failed")

# Initialize router
payment_router = PaymentSmartRouter()

@router.post("/deposit/initialize")
@limiter.limit("20/minute")
async def initialize_deposit(
    request: Request,
    deposit: DepositRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """Initialize deposit with smart provider routing"""
    
    logger.info(f"🔄 Initializing deposit: {deposit.amount} {deposit.currency} for {deposit.user_email}")
    
    try:
        # Generate transaction ID
        transaction_id = f"txn_{uuid.uuid4().hex[:16]}"
        
        # Smart routing
        selected_provider = payment_router.select_provider(
            deposit.currency, 
            deposit.user_country, 
            deposit.amount
        )
        
        logger.info(f"📍 Routing to provider: {selected_provider}")
        
        # Store transaction in database
        transaction_data = {
            "id": transaction_id,
            "user_id": deposit.user_id,
            "amount": deposit.amount,
            "currency": deposit.currency,
            "provider": selected_provider,
            "status": "pending",
            "type": "deposit",
            "user_email": deposit.user_email,
            "user_country": deposit.user_country
        }
        
        supabase.table("payment_transactions").insert(transaction_data).execute()
        
        # Initialize with provider
        payment_data = {
            "transaction_id": transaction_id,
            "user_email": deposit.user_email,
            "amount": deposit.amount,
            "currency": deposit.currency,
            "callback_url": f"https://api.seamount.io/webhooks/payment/{selected_provider}",
            "metadata": {
                "user_id": deposit.user_id,
                "user_country": deposit.user_country
            }
        }
        
        provider_response = await payment_router.initialize_payment(selected_provider, payment_data)
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "provider": selected_provider,
            "payment_url": provider_response.get("authorization_url", provider_response.get("link")),
            "reference": provider_response.get("reference", transaction_id),
            "message": f"Payment initialized with {selected_provider.title()}"
        }
        
    except Exception as e:
        logger.error(f"💥 Deposit initialization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize payment: {str(e)}")

@router.get("/transaction/{transaction_id}")
@limiter.limit("30/minute")
async def get_transaction_status(
    transaction_id: str,
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """Get payment transaction status"""
    
    try:
        result = supabase.table("payment_transactions").select("*").eq("id", transaction_id).maybe_single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return result.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch transaction {transaction_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch transaction status")

@router.post("/on-ramp/ngn")
async def initialize_ngn_onramp(
    request: Request,
    deposit: OnRampRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """NGN → USDT auto-conversion via Paystack"""
    
    try:
        user_id = deposit.user_id
        amount_ngn = Decimal(str(deposit.amount_fiat))
        
        # Get NGN/USD rate from oracle - FIXED: Use available services
        db_service = DatabaseService(supabase)
        oracle_service = EnhancedOracleService(db_service)
        ngn_rate, _ = await oracle_service.get_ngn_usd_rate()
        
        # Calculate USDT amount (with 2.9% Seamount fee)
        amount_usd = amount_ngn / ngn_rate
        seamount_fee = amount_usd * Decimal("0.029")
        usdt_to_mint = amount_usd - seamount_fee
        
        # Initialize Paystack payment
        paystack = PaystackProvider(get_settings())
        payment_result = await paystack.initialize_payment(
            amount=float(amount_ngn),
            currency="NGN",
            email=deposit.user_email,
            tx_ref=f"onramp_{uuid.uuid4().hex[:12]}",
            phone=deposit.user_phone
        )
        
        if payment_result['status'] != 'success':
            raise HTTPException(400, "Paystack initialization failed")
        
        # Store pending mint
        mint_data = {
            "id": payment_result['tx_ref'],
            "user_id": user_id,
            "amount_ngn": float(amount_ngn),
            "amount_usd": float(amount_usd),
            "usdt_to_mint": float(usdt_to_mint),
            "fee_usd": float(seamount_fee),
            "status": "awaiting_payment",
            "payment_url": payment_result['payment_link'],
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("pending_mints").insert(mint_data).execute()
        
        return {
            "success": True,
            "payment_url": payment_result['payment_link'],
            "tx_ref": payment_result['tx_ref'],
            "usdt_to_receive": float(usdt_to_mint),
            "fee_breakdown": {
                "amount_ngn": float(amount_ngn),
                "exchange_rate": float(ngn_rate),
                "amount_usd": float(amount_usd),
                "seamount_fee": float(seamount_fee),
                "net_usdt": float(usdt_to_mint)
            }
        }
        
    except Exception as e:
        logger.error(f"NGN on-ramp failed: {e}")
        raise HTTPException(500, f"On-ramp failed: {e}")