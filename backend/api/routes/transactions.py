# File: backend/api/routes/transactions.py
"""
Transaction Routes - Core Payment API
Handles all transaction types: cross-border, on-ramp, P2P, asset swaps
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from decimal import Decimal
import logging

from backend.dependencies import get_current_user, get_db_service
from backend.services.fee_calculator import FeeCalculatorService, TransactionType
from backend.services.wallet_service import WalletService
from backend.services.cashramp_service import CashrampService
from backend.services.oracle_service import EnhancedOracleService
from backend.config import settings, BusinessModelConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transactions", tags=["Transactions"])

# Request Models
class CrossBorderRequest(BaseModel):
    asset: str = Field(..., description="USDT or USDCa")
    amount_usd: float = Field(..., gt=0)
    recipient_country: str = Field(..., min_length=2, max_length=2)
    recipient_details: Dict[str, str]

class OnRampRequest(BaseModel):
    asset: str = Field(..., description="Asset to purchase")
    amount_fiat: float = Field(..., gt=0)
    currency: str = Field(default="NGN")
    payment_method: str = Field(default="paystack")

class AssetSwapRequest(BaseModel):
    from_asset: str
    to_asset: str  
    amount: float = Field(..., gt=0)

class FeeQuoteRequest(BaseModel):
    transaction_type: str
    amount: float = Field(..., gt=0)
    from_asset: Optional[str] = None
    to_asset: Optional[str] = None
    destination_country: Optional[str] = None

# Response Models
class TransactionResponse(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    status: str
    amount: float
    fee: float
    total_cost: float
    estimated_completion: str
    error: Optional[str] = None

@router.post("/cross-border", response_model=TransactionResponse)
async def send_cross_border_payment(
    request: CrossBorderRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    CORE FUNCTION: Send cross-border payment
    Enables fast, cheap transfers for African users
    """
    try:
        user_id = current_user["id"]
        
        # Initialize services
        fee_calculator = FeeCalculatorService(db_service)
        wallet_service = WalletService(db_service, None)  # AlgorandService injected separately
        cashramp_service = CashrampService(db_service)
        
        # Calculate fees
        fee_calculation = await fee_calculator.calculate_transaction_fee(
            transaction_type=TransactionType.CROSS_BORDER,
            amount=Decimal(str(request.amount_usd)),
            user_id=user_id,
            from_asset=request.asset,
            destination_country=request.recipient_country
        )
        
        # Validate user has sufficient balance
        balances = await wallet_service.get_user_balances(user_id)
        available_balance = balances["balances"].get(request.asset, 0)
        
        total_required = request.amount_usd + fee_calculation["total_fee"]
        if available_balance < total_required:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient balance. Required: {total_required}, Available: {available_balance}"
            )
        
        # Execute cross-border transfer via Cashramp
        transfer_result = await cashramp_service.send_cross_border_payment(
            sender_user_id=user_id,
            recipient_country=request.recipient_country,
            asset=request.asset,
            amount_usd=Decimal(str(request.amount_usd)),
            recipient_details=request.recipient_details
        )
        
        if not transfer_result["success"]:
            raise HTTPException(status_code=500, detail=transfer_result["error"])
        
        return TransactionResponse(
            success=True,
            transaction_id=transfer_result["transfer_id"],
            status="processing",
            amount=request.amount_usd,
            fee=fee_calculation["total_fee"],
            total_cost=total_required,
            estimated_completion=transfer_result["estimated_arrival"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cross-border payment failed: {e}")
        raise HTTPException(status_code=500, detail="Cross-border payment failed")

@router.post("/on-ramp", response_model=TransactionResponse)
async def create_fiat_onramp(
    request: OnRampRequest,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """Create fiat on-ramp (NGN → USDT/USDCa)"""
    try:
        user_id = current_user["id"]
        
        # Initialize services
        fee_calculator = FeeCalculatorService(db_service)
        cashramp_service = CashrampService(db_service)
        
        # Calculate fees
        fee_calculation = await fee_calculator.calculate_transaction_fee(
            transaction_type=TransactionType.ON_RAMP,
            amount=Decimal(str(request.amount_fiat)),
            user_id=user_id,
            to_asset=request.asset,
            payment_method=request.payment_method
        )
        
        # Create on-ramp via Cashramp/Paystack
        if request.currency == "NGN":
            onramp_result = await cashramp_service.create_ngn_onramp(
                user_id=user_id,
                asset=request.asset,
                amount_ngn=Decimal(str(request.amount_fiat)),
                payment_method=request.payment_method
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported currency: {request.currency}")
        
        if not onramp_result["success"]:
            raise HTTPException(status_code=500, detail=onramp_result["error"])
        
        return TransactionResponse(
            success=True,
            transaction_id=onramp_result["onramp_id"],
            status="pending_payment",
            amount=request.amount_fiat,
            fee=fee_calculation["total_fee"],
            total_cost=request.amount_fiat + fee_calculation["total_fee"],
            estimated_completion="Instant after payment"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"On-ramp creation failed: {e}")
        raise HTTPException(status_code=500, detail="On-ramp creation failed")

@router.post("/swap", response_model=TransactionResponse)
async def swap_assets(
    request: AssetSwapRequest,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """Swap between supported assets (USDT ↔ USDCa ↔ goBTC ↔ goETH)"""
    try:
        user_id = current_user["id"]
        
        # Validate assets
        if request.from_asset not in settings.SUPPORTED_ASSETS:
            raise HTTPException(status_code=400, detail=f"Unsupported asset: {request.from_asset}")
        if request.to_asset not in settings.SUPPORTED_ASSETS:
            raise HTTPException(status_code=400, detail=f"Unsupported asset: {request.to_asset}")
        
        # Initialize services
        fee_calculator = FeeCalculatorService(db_service)
        wallet_service = WalletService(db_service, None)
        oracle_service = EnhancedOracleService(db_service)
        
        # Calculate swap fee
        fee_calculation = await fee_calculator.calculate_transaction_fee(
            transaction_type=TransactionType.ASSET_SWAP,
            amount=Decimal(str(request.amount)),
            user_id=user_id,
            from_asset=request.from_asset,
            to_asset=request.to_asset
        )
        
        # Check balance
        balances = await wallet_service.get_user_balances(user_id)
        available = balances["balances"].get(request.from_asset, 0)
        
        if available < request.amount:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient {request.from_asset} balance"
            )
        
        # Get swap rate if volatile asset involved
        receive_amount = request.amount - fee_calculation["total_fee"]
        
        from_config = settings.SUPPORTED_ASSETS[request.from_asset]
        to_config = settings.SUPPORTED_ASSETS[request.to_asset]
        
        if not from_config["is_stable"] or not to_config["is_stable"]:
            # Get real-time price
            if not from_config["is_stable"]:
                from_price, _ = await oracle_service.get_asset_price(from_config["oracle_symbol"].lower())
                from_usd_value = Decimal(str(receive_amount)) * from_price
            else:
                from_usd_value = Decimal(str(receive_amount))
            
            if not to_config["is_stable"]:
                to_price, _ = await oracle_service.get_asset_price(to_config["oracle_symbol"].lower())
                receive_amount = float(from_usd_value / to_price)
            else:
                receive_amount = float(from_usd_value)
        
        # TODO: Execute actual swap transaction
        # For now, return success with calculated amounts
        
        return TransactionResponse(
            success=True,
            transaction_id=f"swap_{user_id}_{int(Decimal('1000000') * Decimal(str(request.amount)))}",
            status="completed",
            amount=request.amount,
            fee=fee_calculation["total_fee"],
            total_cost=request.amount,
            estimated_completion="Instant"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Asset swap failed: {e}")
        raise HTTPException(status_code=500, detail="Asset swap failed")

@router.post("/quote")
async def get_transaction_quote(
    request: FeeQuoteRequest,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """Get fee quote for any transaction type"""
    try:
        user_id = current_user["id"]
        
        fee_calculator = FeeCalculatorService(db_service)
        
        # Get quote
        quote = await fee_calculator.calculate_transaction_fee(
            transaction_type=TransactionType(request.transaction_type),
            amount=Decimal(str(request.amount)),
            user_id=user_id,
            from_asset=request.from_asset,
            to_asset=request.to_asset,
            destination_country=request.destination_country
        )
        
        return {
            "success": True,
            "quote": quote,
            "valid_for_minutes": 5,
            "quote_id": quote.get("quote_id")
        }
        
    except Exception as e:
        logger.error(f"Quote generation failed: {e}")
        raise HTTPException(status_code=500, detail="Quote generation failed")

@router.get("/status/{transaction_id}")
async def get_transaction_status(
    transaction_id: str,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """Track transaction status"""
    try:
        # Initialize Cashramp service for status tracking
        cashramp_service = CashrampService(db_service)
        
        # Track via Cashramp
        status_result = await cashramp_service.track_transfer_status(transaction_id)
        
        if status_result["success"]:
            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": status_result["status"],
                "completion_time": status_result.get("completion_time"),
                "tracking_info": status_result.get("tracking_info", {})
            }
        else:
            # Check local database
            query = """
                SELECT status, created_at, completed_at, failure_reason
                FROM transaction_logs 
                WHERE transaction_id = %s AND user_id = %s
            """
            result = await db_service.execute_query(query, (transaction_id, current_user["id"]))
            
            if result:
                tx_data = result[0]
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "status": tx_data["status"],
                    "created_at": tx_data["created_at"],
                    "completed_at": tx_data["completed_at"],
                    "failure_reason": tx_data.get("failure_reason")
                }
        
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status tracking failed: {e}")
        raise HTTPException(status_code=500, detail="Status tracking failed")

@router.get("/history")
async def get_transaction_history(
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """Get user's transaction history"""
    try:
        user_id = current_user["id"]
        
        query = """
            SELECT transaction_id, type, asset, amount, fee_amount, status, 
                   created_at, completed_at, recipient_country
            FROM transaction_logs 
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        
        results = await db_service.execute_query(query, (user_id, limit, offset))
        
        transactions = []
        for tx in results or []:
            transactions.append({
                "transaction_id": tx["transaction_id"],
                "type": tx["type"],
                "asset": tx["asset"],
                "amount": float(tx["amount"]) if tx["amount"] else 0,
                "fee_amount": float(tx["fee_amount"]) if tx["fee_amount"] else 0,
                "status": tx["status"],
                "created_at": tx["created_at"],
                "completed_at": tx["completed_at"],
                "recipient_country": tx.get("recipient_country")
            })
        
        return {
            "success": True,
            "transactions": transactions,
            "total_count": len(transactions),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Transaction history failed: {e}")
        raise HTTPException(status_code=500, detail="Transaction history retrieval failed")

@router.get("/corridors")
async def get_supported_corridors(
    db_service = Depends(get_db_service)
):
    """Get supported cross-border payment corridors"""
    try:
        cashramp_service = CashrampService(db_service)
        corridors = await cashramp_service.get_supported_corridors()
        
        return {
            "success": True,
            "corridors": corridors,
            "total_corridors": len(corridors)
        }
        
    except Exception as e:
        logger.error(f"Corridors fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch supported corridors")