# File: backend/api/routes/yield_routes.py
"""
Yield Management Routes - Tiered APY Strategy
Stable 7.5% | Growth 9% | Alpha 11%
Revenue: 2% management fee + 20% performance fee
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal

from backend.dependencies import (
    get_current_user, 
    get_db_service, 
    get_audit_service,
    get_oracle_service,
    get_algorand_service
)
from backend.services.yield_manager_service import (
    YieldManagerService, 
    YieldTier,
    YieldStrategy
)
from backend.services.database_service import DatabaseService
from backend.services.audit_service import AuditService
from backend.services.oracle_service import EnhancedOracleService
from backend.services.algorand_service import AlgorandService
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/yield", tags=["Yield Management"])
# limiter = Limiter(key_func=get_remote_address)  # ❌ REMOVED - causes .env encoding error

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class StakeRequest(BaseModel):
    """Request to stake funds in yield tier"""
    asset: str = Field(..., description="Asset to stake (USDT, USDCa, USDS)")
    amount: float = Field(..., gt=0, description="Amount to stake (minimum 10)")
    tier: YieldTier = Field(..., description="Yield tier: stable, growth, or alpha")
    
    class Config:
        json_schema_extra = {
            "example": {
                "asset": "USDT",
                "amount": 100.0,
                "tier": "stable"
            }
        }

class UnstakeRequest(BaseModel):
    """Request to unstake funds"""
    stake_id: str = Field(..., description="Stake ID to unstake from")
    partial_amount: Optional[float] = Field(None, gt=0, description="Optional partial unstake amount")
    
    class Config:
        json_schema_extra = {
            "example": {
                "stake_id": "STAKE_ABC123",
                "partial_amount": 50.0
            }
        }

class StakeResponse(BaseModel):
    """Response for stake creation"""
    success: bool
    stake_id: str
    tier: str
    amount_staked: float
    asset: str
    target_apy: str
    expected_daily_yield: float
    expected_annual_yield: float
    risk_level: str
    next_rebalance: str

class UnstakeResponse(BaseModel):
    """Response for unstake"""
    success: bool
    stake_id: str
    unstaked_amount: float
    remaining_staked: float
    total_yield_earned: float
    fees_paid: float
    status: str

# ============================================================================
# YIELD MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/stake", response_model=StakeResponse)
# @limiter.limit("10/minute")  # Using global limiter from main.py
async def stake_funds(
    request: Request,
    stake_request: StakeRequest,
    current_user: dict = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service),
    audit_service: AuditService = Depends(get_audit_service),
    oracle_service: EnhancedOracleService = Depends(get_oracle_service),
    algorand_service: AlgorandService = Depends(get_algorand_service)  # ➕ ADD THIS
):
    """
    Stake funds into yield-generating tier
    
    - **Stable Tier (7.5% APY)**: Low risk, Folks Finance + ALGO staking
    - **Growth Tier (9.0% APY)**: Medium risk, DEX liquidity + lending
    - **Alpha Tier (11.0% APY)**: High risk, Delta-neutral + DeFi composability
    
    **Minimum stake:** $10 equivalent
    **Revenue:** 2% management fee + 20% performance fee
    """
    
    try:
        logger.info(f"Stake request: {current_user['id']} - {stake_request.amount} {stake_request.asset} in {stake_request.tier.value}")
        
        # Validate minimum stake
        if stake_request.amount < 10:
            raise HTTPException(
                status_code=400,
                detail="Minimum stake amount is $10 equivalent"
            )
        
        # Validate asset
        supported_assets = ["USDT", "USDCa",  "ALGO"]
        if stake_request.asset not in supported_assets:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported asset. Supported: {', '.join(supported_assets)}"
            )
        
        # Initialize service
        service = YieldManagerService(db_service, audit_service, oracle_service, algorand_service)
        
        # Create stake
        result = await service.stake_funds(
            user_id=current_user["id"],
            asset=stake_request.asset,
            amount=stake_request.amount,
            tier=stake_request.tier
        )
        
        logger.info(f"✅ Stake created: {result['stake_id']} for user {current_user['id']}")
        
        return StakeResponse(**result)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Stake validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stake creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create stake. Please try again or contact support."
        )

@router.post("/unstake", response_model=UnstakeResponse)
# @limiter.limit("10/minute")  # Using global limiter from main.py
async def unstake_funds(
    request: Request,
    unstake_request: UnstakeRequest,
    current_user: dict = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service),
    audit_service: AuditService = Depends(get_audit_service),
    oracle_service: EnhancedOracleService = Depends(get_oracle_service),
    algorand_service: AlgorandService = Depends(get_algorand_service) 
):
    """
    Unstake funds from yield tier
    
    - **Full unstake**: Omit `partial_amount` to unstake everything
    - **Partial unstake**: Specify `partial_amount` to keep some staked
    
    **Returns:** Principal + accrued yield - fees
    **Settlement:** Instant to wallet balance
    """
    
    try:
        logger.info(f"Unstake request: {current_user['id']} - {unstake_request.stake_id}")
        
        # Initialize service
        service = YieldManagerService(db_service, audit_service, oracle_service, algorand_service)
        
        # Execute unstake
        result = await service.unstake_funds(
            user_id=current_user["id"],
            stake_id=unstake_request.stake_id,
            partial_amount=unstake_request.partial_amount
        )
        
        logger.info(f"✅ Unstake completed: {unstake_request.stake_id} for user {current_user['id']}")
        
        return UnstakeResponse(**result)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Unstake validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unstake failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process unstake. Please try again or contact support."
        )

@router.get("/stakes")
# @limiter.limit("30/minute")  # Using global limiter from main.py
async def get_user_stakes(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service),
    audit_service: AuditService = Depends(get_audit_service),
    oracle_service: EnhancedOracleService = Depends(get_oracle_service),
    algorand_service: AlgorandService = Depends(get_algorand_service)
):
    """
    Get all stakes for current user
    
    **Returns:** List of active and historical stakes with current values
    """
    
    try:
        logger.info(f"Fetching stakes for user: {current_user['id']}")
        
        service = YieldManagerService(db_service, audit_service, oracle_service, algorand_service)
        
        stakes = await service.get_user_stakes(current_user["id"])
        
        return {
            "success": True,
            "stakes": stakes,
            "total_staked": sum(float(s["current_value"]) for s in stakes if s["status"] == "active"),
            "total_earned": sum(float(s["net_yield"]) for s in stakes)
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch stakes: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch stakes. Please try again."
        )

@router.get("/stake/{stake_id}")
# @limiter.limit("30/minute")  # Using global limiter from main.py
async def get_stake_details(
    stake_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service),
    audit_service: AuditService = Depends(get_audit_service),
    oracle_service: EnhancedOracleService = Depends(get_oracle_service)
):
    """
    Get detailed yield calculation for specific stake
    
    **Returns:** 
    - Current value with accrued yield
    - Fee breakdown (management + performance)
    - Strategy performance details
    - Current APY vs target APY
    """
    
    try:
        logger.info(f"Fetching stake details: {stake_id} for user {current_user['id']}")
        
        service = YieldManagerService(db_service, audit_service, oracle_service)
        
        result = await service.calculate_current_yield(stake_id)
        
        # Verify ownership
        stake_check = await db_service.query(
            "yield_stakes",
            filters={"id": stake_id},
            columns=["user_id"]
        )
        
        if not stake_check or stake_check[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Stake not found")
        
        return {
            "success": True,
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch stake details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch stake details. Please try again."
        )

@router.get("/tiers")
# @limiter.limit("60/minute")  # Using global limiter from main.py
async def get_tier_info(
    request: Request,
    db_service: DatabaseService = Depends(get_db_service),
    audit_service: AuditService = Depends(get_audit_service),
    oracle_service: EnhancedOracleService = Depends(get_oracle_service)
):
    """
    Get information about all yield tiers
    
    **Returns:** 
    - Tier configurations (Stable, Growth, Alpha)
    - Target APYs and risk levels
    - Strategy allocations
    - Rebalancing schedules
    - User recommendations
    """
    
    try:
        logger.info("Fetching tier information")
        
        service = YieldManagerService(db_service, audit_service, oracle_service)
        
        tiers = await service.get_tier_info()
        
        return {
            "success": True,
            "tiers": tiers,
            "comparison": {
                "seamount_stable": "7.5% APY",
                "busha_best": "7.5% APY",
                "seamount_advantage": "2 higher tiers + transparent fees",
                "traditional_savings": "2-15% APY (inflation adjusted: negative)"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch tier info: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch tier information. Please try again."
        )

@router.get("/portfolio")
# @limiter.limit("30/minute")  # Using global limiter from main.py
async def get_yield_portfolio(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service),
    audit_service: AuditService = Depends(get_audit_service),
    oracle_service: EnhancedOracleService = Depends(get_oracle_service)
):
    """
    Get comprehensive yield portfolio summary
    
    **Returns:**
    - Total portfolio value
    - Breakdown by tier
    - Total earnings
    - Performance vs benchmarks
    """
    
    try:
        logger.info(f"Fetching yield portfolio for user: {current_user['id']}")
        
        service = YieldManagerService(db_service, audit_service, oracle_service)
        
        stakes = await service.get_user_stakes(current_user["id"])
        
        # Calculate portfolio metrics
        active_stakes = [s for s in stakes if s["status"] == "active"]
        
        total_value = sum(float(s["current_value"]) for s in active_stakes)
        total_principal = sum(float(s["principal"]) for s in stakes)
        total_yield = sum(float(s["net_yield"]) for s in stakes)
        
        # Tier breakdown
        tier_breakdown = {}
        for tier in ["stable", "growth", "alpha"]:
            tier_stakes = [s for s in active_stakes if s["tier"] == tier]
            tier_breakdown[tier] = {
                "count": len(tier_stakes),
                "total_value": sum(float(s["current_value"]) for s in tier_stakes),
                "total_yield": sum(float(s["net_yield"]) for s in tier_stakes)
            }
        
        # Calculate blended APY
        if total_principal > 0:
            blended_apy = (total_yield / total_principal) * 100
        else:
            blended_apy = 0
        
        return {
            "success": True,
            "portfolio_summary": {
                "total_value": total_value,
                "total_principal": total_principal,
                "total_yield": total_yield,
                "blended_apy": f"{blended_apy:.2f}%",
                "active_stakes": len(active_stakes),
                "total_stakes": len(stakes)
            },
            "tier_breakdown": tier_breakdown,
            "stakes": stakes
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch yield portfolio: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch portfolio. Please try again."
        )

@router.get("/strategies")
# @limiter.limit("60/minute")  # Using global limiter from main.py
async def get_strategy_info(request: Request):
    """
    Get information about yield strategies
    
    **Returns:** Details about underlying DeFi protocols and strategies
    """
    
    strategies = {
        "folks_finance": {
            "name": "Folks Finance Lending",
            "protocol": "Folks Finance",
            "type": "Lending",
            "base_apy": "8.0%",
            "risk_level": "Low",
            "description": "Lend stablecoins to Algorand's premier lending protocol",
            "url": "https://folks.finance"
        },
        "pact_liquidity": {
            "name": "Pact DEX Liquidity",
            "protocol": "Pact",
            "type": "DEX Liquidity",
            "base_apy": "9.5%",
            "risk_level": "Medium",
            "description": "Provide liquidity to USDS/USDCa pools on Pact DEX",
            "url": "https://pact.fi"
        },
        "algo_staking": {
            "name": "Algorand Governance",
            "protocol": "Algorand Foundation",
            "type": "Staking",
            "base_apy": "5.5%",
            "risk_level": "Very Low",
            "description": "Participate in Algorand governance for staking rewards",
            "url": "https://governance.algorand.foundation"
        },
        "delta_neutral": {
            "name": "Delta-Neutral Hedging",
            "protocol": "Multi-Exchange",
            "type": "Advanced Trading",
            "base_apy": "13.0%",
            "risk_level": "High (Managed)",
            "description": "Capture funding rates via delta-neutral BTC/ETH positions",
            "status": "Coming Soon"
        }
    }
    
    return {
        "success": True,
        "strategies": strategies,
        "note": "Strategies are automatically allocated based on your chosen tier"
    }

# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def yield_health_check():
    """Health check for yield management service"""
    return {
        "status": "healthy",
        "service": "yield_management",
        "tiers_available": ["stable", "growth", "alpha"],
        "min_stake": 10.0
    }

@router.post("/yield/stake")
async def stake_usdt(
    amount: Decimal,
    user: dict = Depends(get_current_user)
):
    # Transfer to Folks Finance vault
    vault_address = "FOLKS_USDT_VAULT_ADDRESS"  # Get from Folks Finance
    
    tx_id = await algorand_service.transfer_asset(
        sender_pk=user['private_key'],
        receiver=vault_address,
        asset_id=312769,  # USDT ASA
        amount=int(amount * 1_000_000)  # Convert to micro-units
    )
    
    # Record position
    await db.create_yield_position(
        user_id=user['id'],
        asset='USDT',
        amount=amount,
        protocol='folks_finance',
        apy=Decimal('0.08'),  # 8% APY
        tx_id=tx_id
    )
    
    return {"success": True, "tx_id": tx_id, "apy": "8%"}