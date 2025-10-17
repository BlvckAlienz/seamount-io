# File: backend/api/routes/yield.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.dependencies import get_current_user, get_db_service, get_audit_service
from backend.services.yield_manager_service import YieldManagerService, YieldTier
from backend.services.oracle_service import EnhancedOracleService

router = APIRouter(prefix="/yield", tags=["Yield Management"])

class StakeRequest(BaseModel):
    asset: str
    amount: float
    tier: YieldTier

class UnstakeRequest(BaseModel):
    stake_id: str
    partial_amount: Optional[float] = None

@router.post("/stake")
async def stake_funds(
    request: StakeRequest,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Stake funds into yield tier"""
    
    oracle = EnhancedOracleService(db_service)
    service = YieldManagerService(db_service, audit_service, oracle)
    
    return await service.stake_funds(
        user_id=current_user["id"],
        asset=request.asset,
        amount=request.amount,
        tier=request.tier
    )

@router.post("/unstake")
async def unstake_funds(
    request: UnstakeRequest,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Unstake funds from yield tier"""
    
    oracle = EnhancedOracleService(db_service)
    service = YieldManagerService(db_service, audit_service, oracle)
    
    return await service.unstake_funds(
        user_id=current_user["id"],
        stake_id=request.stake_id,
        partial_amount=request.partial_amount
    )

@router.get("/stakes")
async def get_stakes(
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Get user's yield stakes"""
    
    oracle = EnhancedOracleService(db_service)
    service = YieldManagerService(db_service, audit_service, oracle)
    
    return await service.get_user_stakes(current_user["id"])

@router.get("/stake/{stake_id}")
async def get_stake_details(
    stake_id: str,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Get detailed yield calculation for stake"""
    
    oracle = EnhancedOracleService(db_service)
    service = YieldManagerService(db_service, audit_service, oracle)
    
    return await service.calculate_current_yield(stake_id)

@router.get("/tiers")
async def get_tiers(
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Get yield tier information"""
    
    oracle = EnhancedOracleService(db_service)
    service = YieldManagerService(db_service, audit_service, oracle)
    
    return await service.get_tier_info()