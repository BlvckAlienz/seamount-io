# File: backend/api/routes/onramp.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional

from backend.dependencies import get_current_user, get_db_service, get_audit_service
from backend.services.onramp_aggregator_service import OnRampAggregatorService

router = APIRouter(prefix="/onramp", tags=["On-Ramp"])

class OnRampRequest(BaseModel):
    amount_fiat: float
    currency: str
    crypto_asset: str
    user_country: str = "NG"

@router.post("/initialize")
async def initialize_onramp(
    request: OnRampRequest,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Initialize on-ramp transaction"""
    
    service = OnRampAggregatorService(db_service, audit_service)
    
    # Get user wallet address
    wallet_query = "SELECT algorand_address FROM user_wallets WHERE user_id = %s"
    wallet_result = await db_service.execute_query(wallet_query, (current_user["id"],))
    
    if not wallet_result:
        raise HTTPException(status_code=400, detail="User wallet not found")
    
    wallet_address = wallet_result[0]["algorand_address"]
    
    return await service.initialize_onramp(
        user_id=current_user["id"],
        user_email=current_user["email"],
        amount_fiat=request.amount_fiat,
        currency=request.currency,
        crypto_asset=request.crypto_asset,
        user_wallet_address=wallet_address,
        user_country=request.user_country
    )

@router.post("/webhook/{provider}")
async def handle_webhook(
    provider: str,
    request: Request,
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Handle provider webhook callbacks"""
    
    service = OnRampAggregatorService(db_service, audit_service)
    payload = await request.json()
    
    return await service.handle_webhook(provider, payload)

@router.get("/providers")
async def get_providers(
    currency: Optional[str] = None,
    crypto: Optional[str] = None,
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Get supported on-ramp providers"""
    
    service = OnRampAggregatorService(db_service, audit_service)
    return await service.get_supported_providers(currency, crypto)