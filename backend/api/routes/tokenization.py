# File: backend/api/routes/tokenization.py
"""
Seamount Tokenization API Routes
Exposes FinP2P-inspired asset tokenization, DVP trading, and repo markets
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
import logging

from backend.dependencies import (
    get_current_user,
    get_db_service,
    get_audit_service
)
from backend.services.seamount_protocol import SeamountProtocol
from backend.services.algorand_service import AlgorandService
from backend.services.database_service import DatabaseService
from backend.services.audit_service import AuditService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tokenization", tags=["Tokenization"])

# ============================================================================
# PYDANTIC MODELS (Request/Response)
# ============================================================================

class TokenizeAssetRequest(BaseModel):
    """Request to tokenize traditional asset"""
    custodian_id: str = Field(..., description="Custodian holding the asset")
    symbol: str = Field(..., description="Asset ticker (e.g., DANGCEM)")
    name: Optional[str] = Field(None, description="Asset full name")
    quantity: int = Field(..., gt=0, description="Number of shares to tokenize")
    isin: Optional[str] = Field(None, description="ISIN code")
    price_per_unit: Decimal = Field(..., gt=0, description="Current price per share (USD)")

class PublishOfferRequest(BaseModel):
    """Request to publish secondary market offer"""
    asset_id: str = Field(..., description="Tokenized asset UUID")
    quantity: int = Field(..., gt=0, description="Quantity to sell")
    price_per_unit: Decimal = Field(..., gt=0, description="Asking price per unit (USD)")
    payment_network: str = Field(default="usdc_circle", description="Accepted payment network")
    expires_in_hours: Optional[int] = Field(default=168, description="Offer expiry (default 7 days)")

class ExecuteTradeRequest(BaseModel):
    """Request to buy tokenized asset (DVP)"""
    offer_id: str = Field(..., description="Offer UUID to execute")
    payment_network: str = Field(default="usdc_circle", description="Payment method")

class CreateRepoRequest(BaseModel):
    """Request to create repo trade (collateralized loan)"""
    collateral_asset_id: str = Field(..., description="Asset to use as collateral")
    collateral_quantity: int = Field(..., gt=0, description="Number of tokens to lock")
    loan_amount_usd: Decimal = Field(..., gt=0, description="Amount to borrow")
    repo_rate_percentage: Decimal = Field(..., gt=0, le=50, description="Annual interest rate")
    maturity_days: int = Field(..., gt=0, le=365, description="Loan duration")
    lender_id: Optional[str] = Field(None, description="Specific lender (optional)")

class UpdateAssetPriceRequest(BaseModel):
    """Admin: Update asset price"""
    asset_id: str
    new_price: Decimal = Field(..., gt=0)
    source: str = Field(default="manual", description="Price source")

# ============================================================================
# HELPER: Initialize Protocol Service
# ============================================================================

def get_protocol_service(
    db_service: DatabaseService = Depends(get_db_service),
    audit_service: AuditService = Depends(get_audit_service)
) -> SeamountProtocol:
    """Dependency injection for SeamountProtocol"""
    from backend.services.algorand_service import AlgorandService
    from backend.config import get_settings
    
    settings = get_settings()
    algorand_service = AlgorandService(settings)
    
    return SeamountProtocol(
        db_service=db_service,
        algorand_service=algorand_service,
        audit_service=audit_service
    )

# ============================================================================
# ENDPOINT 1: TOKENIZE ASSET (Convert Traditional → Digital Twin)
# ============================================================================

@router.post("/convert-asset")
async def convert_asset(
    request: TokenizeAssetRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    protocol: SeamountProtocol = Depends(get_protocol_service)
):
    """
    🏦 Convert Traditional Asset to Digital Twin
    
    **Flow:**
    1. Verify custody with custodian (CSCS/NSE)
    2. Create Algorand ASA
    3. Lock physical shares
    4. Issue digital tokens
    
    **Example:**
```json
    {
      "custodian_id": "uuid-custodian",
      "symbol": "DANGCEM",
      "quantity": 1000,
      "price_per_unit": 450.00
    }
```
    """
    try:
        logger.info(f"🔄 Tokenization request from user {current_user['id']}: {request.symbol}")
        
        # Execute tokenization
        result = await protocol.tokenize_asset(
            user_id=current_user['id'],
            custodian_id=request.custodian_id,
            asset_details={
                'symbol': request.symbol,
                'name': request.name or request.symbol,
                'quantity': request.quantity,
                'isin': request.isin,
                'price_per_unit': float(request.price_per_unit)
            }
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Tokenization failed'))
        
        return {
            "success": True,
            "message": f"Successfully tokenized {request.quantity} shares of {request.symbol}",
            "data": {
                "asset_id": result['asset_id'],
                "algorand_asa_id": result['algorand_asa_id'],
                "digital_twin_address": result['digital_twin_address'],
                "custody_reference": result['custody_reference']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Tokenization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINT 2: PUBLISH SECONDARY OFFER
# ============================================================================

@router.post("/publish-offer")
async def publish_offer(
    request: PublishOfferRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    📢 Publish Asset for Sale (Secondary Market)
    
    **Flow:**
    1. Verify user owns the asset
    2. Lock tokens (prevent double-spend)
    3. Create public offer
    
    **Example:**
```json
    {
      "asset_id": "uuid-asset",
      "quantity": 500,
      "price_per_unit": 460.00
    }
```
    """
    try:
        # Verify ownership
        asset = db_service.supabase.table('tokenized_assets')\
            .select('*')\
            .eq('id', request.asset_id)\
            .eq('user_id', current_user['id'])\
            .single()\
            .execute()
        
        if not asset.data:
            raise HTTPException(status_code=404, detail="Asset not found or not owned by user")
        
        asset_data = asset.data
        
        # Check sufficient balance
        if asset_data['on_chain_balance'] < request.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. You have {asset_data['on_chain_balance']}, need {request.quantity}"
            )
        
        # Calculate total value
        total_value = request.price_per_unit * request.quantity
        
        # Create offer
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours)
        
        offer_data = {
            'seller_id': current_user['id'],
            'asset_id': request.asset_id,
            'quantity': request.quantity,
            'price_per_unit': float(request.price_per_unit),
            'total_value': float(total_value),
            'payment_network': request.payment_network,
            'status': 'published',
            'published_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat()
        }
        
        result = db_service.supabase.table('asset_offers').insert(offer_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create offer")
        
        return {
            "success": True,
            "message": "Offer published successfully",
            "data": {
                "offer_id": result.data[0]['id'],
                "symbol": asset_data['symbol'],
                "quantity": request.quantity,
                "price_per_unit": float(request.price_per_unit),
                "total_value": float(total_value),
                "expires_at": expires_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Offer creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINT 3: EXECUTE TRADE (DVP Settlement)
# ============================================================================

@router.post("/execute-trade")
async def execute_trade(
    request: ExecuteTradeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    protocol: SeamountProtocol = Depends(get_protocol_service)
):
    """
    💱 Execute Trade with Atomic DVP Settlement
    ...
    """
    try:
        logger.info(f"🔄 DVP trade execution: User {current_user['id']} buying offer {request.offer_id}")
        
        # Execute DVP settlement
        result = await protocol.execute_dvp_settlement(
            offer_id=request.offer_id,
            buyer_id=current_user['id'],
            payment_network=request.payment_network
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Trade execution failed'))
    
    except ValueError as val_err:
        # 🚨 Self-trade and validation errors (user-friendly)
        logger.warning(f"⚠️ Trade validation failed: {val_err}")
        raise HTTPException(status_code=400, detail=str(val_err))
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ Trade execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINT 4: CREATE REPO TRADE
# ============================================================================

@router.post("/create-repo")
async def create_repo(
    request: CreateRepoRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    protocol: SeamountProtocol = Depends(get_protocol_service)
):
    """
    🏦 Create Repo Trade (Borrow Against Collateral)
    
    **Flow:**
    1. Lock collateral tokens
    2. Transfer loan to borrower
    3. Deploy smart contract for auto-settlement
    
    **Example:**
```json
    {
      "collateral_asset_id": "uuid-asset",
      "collateral_quantity": 100,
      "loan_amount_usd": 40000,
      "repo_rate_percentage": 4.5,
      "maturity_days": 30
    }
```
    """
    try:
        # ✅ FIX: Use None (NULL in DB) for platform liquidity pool
        lender_id = request.lender_id  # Will be None if not provided
        
        result = await protocol.create_repo_trade(
            borrower_id=current_user['id'],
            lender_id=lender_id,  # ✅ Now None instead of "PLATFORM_LIQUIDITY_POOL"
            collateral_asset_id=request.collateral_asset_id,
            collateral_quantity=request.collateral_quantity,
            loan_amount_usd=request.loan_amount_usd,
            repo_rate_percentage=request.repo_rate_percentage,
            maturity_days=request.maturity_days
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Repo creation failed'))
        
        return {
            "success": True,
            "message": result['message'],
            "data": {
                "repo_id": result['repo_id'],
                "smart_contract_address": result['smart_contract_address'],
                "collateral_tx": result['collateral_tx'],
                "loan_tx": result['loan_tx'],
                "repurchase_amount": result['repurchase_amount'],
                "maturity_date": result['maturity_date']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Repo creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINT 5: LIST USER'S TOKENIZED ASSETS
# ============================================================================

@router.get("/my-assets")
async def get_my_assets(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """📋 List User's Tokenized Assets"""
    try:
        assets = db_service.supabase.table('tokenized_assets')\
            .select('*')\
            .eq('user_id', current_user['id'])\
            .execute()
        
        return {
            "success": True,
            "count": len(assets.data) if assets.data else 0,
            "assets": assets.data or []
        }
        
    except Exception as e:
        logger.error(f"❌ Asset listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINT 6: LIST AVAILABLE OFFERS (Secondary Market)
# ============================================================================

@router.get("/offers")
async def get_offers(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    status: str = Query("published", description="Offer status"),
    db_service: DatabaseService = Depends(get_db_service)
):
    """📊 List Available Secondary Market Offers"""
    try:
        query = db_service.supabase.table('asset_offers')\
            .select('*, tokenized_assets(symbol, name)')
        
        if symbol:
            query = query.eq('tokenized_assets.symbol', symbol)
        
        query = query.eq('status', status)
        
        result = query.execute()
        
        return {
            "success": True,
            "count": len(result.data) if result.data else 0,
            "offers": result.data or []
        }
        
    except Exception as e:
        logger.error(f"❌ Offer listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINT 7: LIST USER'S REPO TRADES
# ============================================================================

@router.get("/my-repos")
async def get_my_repos(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """💼 List User's Active Repo Trades"""
    try:
        repos = db_service.supabase.table('repo_trades')\
            .select('*')\
            .or_(f"borrower_id.eq.{current_user['id']},lender_id.eq.{current_user['id']}")\
            .execute()
        
        return {
            "success": True,
            "count": len(repos.data) if repos.data else 0,
            "repos": repos.data or []
        }
        
    except Exception as e:
        logger.error(f"❌ Repo listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINT 8: PROTOCOL METRICS (Public Analytics)
# ============================================================================

@router.get("/metrics")
async def get_metrics(
    protocol: SeamountProtocol = Depends(get_protocol_service)
):
    """📈 Seamount Protocol Metrics"""
    try:
        metrics = await protocol.get_protocol_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINT 9: HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check(
    protocol: SeamountProtocol = Depends(get_protocol_service)
):
    """🏥 Protocol Health Status"""
    try:
        health = await protocol.health_check()
        return health
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ADMIN ENDPOINTS (Role-protected)
# ============================================================================

@router.post("/admin/update-price")
async def admin_update_price(
    request: UpdateAssetPriceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    protocol: SeamountProtocol = Depends(get_protocol_service)
):
    """🔧 Admin: Update Asset Price"""
    # TODO: Add role check (current_user['role'] == 'admin')
    try:
        result = await protocol.update_asset_price(
            asset_id=request.asset_id,
            new_price=request.new_price,
            source=request.source
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Price update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))