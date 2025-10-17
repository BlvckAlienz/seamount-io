# File: backend/api/routes/offramp.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any

from backend.dependencies import get_current_user, get_db_service, get_audit_service
from backend.services.offramp_service import OfframpService
from backend.services.payment_providers.paystack import PaystackProvider
from backend.services.cashramp_service import CashrampService
from backend.services.oracle_service import EnhancedOracleService
from backend.config import settings

router = APIRouter(prefix="/offramp", tags=["Off-Ramp"])

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