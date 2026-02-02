# File: backend/api/routes/tokenization.py
"""
Seamount Tokenization API Routes
Exposes FinP2P-inspired asset tokenization, DVP trading, and repo markets
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Form, File, UploadFile
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
import logging
import uuid
from pathlib import Path

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
    payment_network: str = Field(default="algorand", description="Payment method")
    quantity: Optional[int] = Field(None, description="Quantity to purchase (defaults to full offer)")

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

@router.get("/partial-purchases")
async def get_partial_purchases(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """📋 Get user's partial purchases from sold_offer_parts"""
    try:
        partial_purchases = db_service.supabase.table('sold_offer_parts')\
            .select('*, asset_offers(asset_id, tokenized_assets(*))')\
            .eq('buyer_id', current_user['id'])\
            .execute()
        
        return {
            "success": True,
            "count": len(partial_purchases.data) if partial_purchases.data else 0,
            "partial_purchases": partial_purchases.data or []
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch partial purchases: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# ============================================================================
# ENDPOINT 1: TOKENIZE ASSET (Convert Traditional → Digital Twin)
# ============================================================================

@router.post("/convert-asset")
async def convert_asset(
    custodian_id: str = Form(...),
    symbol: str = Form(...),
    quantity: int = Form(...),
    price_per_unit: float = Form(...),
    name: Optional[str] = Form(None),
    isin: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    protocol: SeamountProtocol = Depends(get_protocol_service),
    db_service: DatabaseService = Depends(get_db_service)
):
    """Convert traditional asset with optional image upload"""
    try:
        # 1️⃣ Handle image upload (if provided)
        image_url = None
        if image:
            logger.info(f"Processing image upload for user {current_user['id']}")
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/webp']
            if image.content_type not in allowed_types:
                raise HTTPException(400, f"Invalid image format. Allowed: {', '.join(allowed_types)}")
            
            # Validate file size (max 5MB)
            MAX_SIZE = 5 * 1024 * 1024  # 5MB
            file_size = 0
            chunks = []
            while chunk := await image.read(8192):  # Read in chunks
                file_size += len(chunk)
                chunks.append(chunk)
                if file_size > MAX_SIZE:
                    raise HTTPException(400, "Image size exceeds 5MB limit")
            
            if file_size == 0:
                raise HTTPException(400, "Empty image file")
            
            # Reset file pointer and combine chunks
            await image.seek(0)
            image_bytes = b''.join(chunks)
            
            # Generate unique filename
            file_ext = Path(image.filename).suffix or '.jpg'
            filename = f"{uuid.uuid4()}{file_ext}"
            file_path = f"assets/{filename}"
            
            logger.info(f"Uploading image to Supabase: {file_path}")
            
            try:
                # Upload to Supabase Storage using direct client
                upload_result = db_service.supabase.storage.from_("asset-images").upload(
                    file_path,
                    image_bytes,
                    {"content-type": image.content_type, "cache-control": "max-age=3600"}
                )
                
                if upload_result.error:
                    logger.error(f"Supabase upload error: {upload_result.error}")
                    raise HTTPException(500, f"Failed to upload image: {upload_result.error.message}")
                
                # Get public URL
                public_url_data = db_service.supabase.storage.from_("asset-images").get_public_url(file_path)
                image_url = public_url_data.public_url
                
                logger.info(f"Image uploaded successfully: {image_url}")
                
            except Exception as storage_error:
                logger.error(f"Storage upload failed: {storage_error}")
                # Don't fail the entire process if image upload fails
                image_url = None
        
        # 2️⃣ Tokenize asset
        logger.info(f"Tokenizing asset: {symbol.upper()} for user {current_user['id']}")
        
        result = await protocol.tokenize_asset(
            user_id=current_user['id'],
            custodian_id=custodian_id,
            asset_details={
                'symbol': symbol.upper(),
                'name': name or symbol,
                'quantity': quantity,
                'price_per_unit': price_per_unit,
                'isin': isin,
                'image_url': image_url  # ✅ Store image URL (could be None)
            }
        )
        
        if not result.get('success'):
            error_msg = result.get('error', 'Tokenization failed')
            logger.error(f"Tokenization failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 3️⃣ Add image_url to response if available
        if image_url and 'data' in result:
            result['data']['image_url'] = image_url
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Conversion failed: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Internal server error: {str(e)}")

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
    
    **Parameters:**
    - `offer_id`: The offer to purchase
    - `payment_network`: Payment method (default: algorand)
    - `quantity`: Optional quantity to purchase (for partial purchases)
    """
    try:
        logger.info(f"🔄 DVP trade execution: User {current_user['id']} buying offer {request.offer_id}, quantity: {request.quantity}")
        
        # Execute DVP settlement
        result = await protocol.execute_dvp_settlement(
            offer_id=request.offer_id,
            buyer_id=current_user['id'],
            payment_network=request.payment_network,
            quantity=request.quantity  # ✅ Pass quantity parameter
        )
        
        if not result['success']:
            # 🚨 Ensure error message is properly formatted
            error_detail = result.get('error', 'Trade execution failed')
            logger.error(f"❌ Trade execution failed with result: {error_detail}")
            raise HTTPException(status_code=400, detail=error_detail)
        
        return {
            "success": True,
            "message": result.get('message', 'Trade executed successfully'),
            "data": result.get('data', {})
        }
        
    except ValueError as val_err:
        # 🚨 Self-trade and validation errors (user-friendly)
        logger.warning(f"⚠️ Trade validation failed: {val_err}")
        # Return JSON response instead of raising HTTPException with just string
        raise HTTPException(
            status_code=400,
            detail={
                "message": str(val_err),
                "code": "SELF_TRADE_BLOCKED",
                "user_id": current_user['id']
            }
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ Trade execution failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail={
                "message": str(e),
                "code": "INTERNAL_SERVER_ERROR"
            }
        )

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
        query = (
            db_service.supabase.table('asset_offers')
            .select('*, tokenized_assets(symbol, name, image_url, isin, asset_type, asset_id)')
            .eq('status', status)
            .gt('expires_at', datetime.utcnow().isoformat())  # ✅ Filter expired
        )
        if symbol:
            query = query.eq('tokenized_assets.symbol', symbol)
        
        result = query.execute()
        
        return {
            "success": True,
            "count": len(result.data) if result.data else 0,
            "offers": result.data or []
        }
    except Exception as e:
        raise HTTPException(500, str(e))

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
    
@router.get("/my-purchases")
async def get_my_purchases(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """Get user's purchased assets"""
    try:
        # Fetch from trade_history
        trades = db_service.supabase.table('trade_history')\
            .select('*, tokenized_assets(symbol, name, image_url, current_price_usd)')\
            .eq('buyer_id', current_user['id'])\
            .execute()
        
        # Calculate P&L
        assets = []
        for trade in (trades.data or []):
            asset = trade['tokenized_assets']
            purchase_price = trade['total_value']
            current_value = trade['quantity'] * asset['current_price_usd']
            
            assets.append({
                'id': trade['asset_id'],
                'symbol': asset['symbol'],
                'name': asset['name'],
                'image_url': asset.get('image_url'),
                'quantity': trade['quantity'],
                'purchase_price': purchase_price,
                'current_value': current_value,
                'purchased_at': trade['settled_at']
            })
        
        return {
            'success': True,
            'assets': assets
        }
    except Exception as e:
        raise HTTPException(500, str(e))