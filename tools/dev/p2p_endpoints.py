from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from pydantic import BaseModel, Field
from typing import Dict, Optional
from backend.seamount_payment_engine import SeamountPaymentEngine, PaymentType, PaymentStatus, Currency
from backend.payment_processor import FlutterwaveProcessor
from redis.asyncio import Redis
from backend.seamount_oracle_complete import SeamountOracle
from backend.usds_asset_manager import USDSManager, CollateralType
import os, asyncio
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime


logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services with robust error handling
payment_engine = SeamountPaymentEngine()
redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
oracle = SeamountOracle(os.getenv("ORACLE_DB_PATH"))
usds_manager = USDSManager({
    'algorand_token': os.getenv("ALGORAND_TOKEN", ""),
    'algorand_node_url': os.getenv("ALGORAND_SERVER", "https://testnet-api.algonode.cloud"),
    'treasury_address': os.getenv("TREASURY_ADDRESS", ""),
    'treasury_private_key': os.getenv("TREASURY_PRIVATE_KEY", ""),
    'reserve_address': os.getenv("RESERVE_ADDRESS", ""),
    'reserve_private_key': os.getenv("RESERVE_PRIVATE_KEY", ""),
    'supabase_url': os.getenv("SUPABASE_URL", ""),
    'supabase_key': os.getenv("SUPABASE_KEY", ""),
    'redis_url': os.getenv("REDIS_URL", "redis://localhost:6379")
})

# Initialize subsystem with retry logic
async def initialize_subsystems():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await payment_engine.initialize()
            await usds_manager.initialize()
            logger.info("Payment subsystems initialized successfully")
            return
        except Exception as e:
            logger.error(f"Subsystem init attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.critical("Failed to initialize subsystems after all retries")
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

# Run initialization as a background task
asyncio.create_task(initialize_subsystems())

class DepositFiatRequest(BaseModel):
    amount_usd: float = Field(..., gt=0, description="Amount in USD")
    email: str = Field(..., description="User email")
    phone: Optional[str] = Field(None, description="User phone")

class WithdrawFiatRequest(BaseModel):
    amount_usds: float = Field(..., gt=0, description="Amount in USDS")
    bank_details: Dict = Field(..., description="Bank account details")

class DisputeRequest(BaseModel):
    transaction_id: str = Field(..., description="Transaction ID to dispute")
    reason: str = Field(..., min_length=10, description="Dispute reason")

class DisputeUpdateRequest(BaseModel):
    status: str = Field(..., description="New dispute status")

class MintUSDSRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to mint")
    recipient: str = Field(..., description="Recipient address")

async def get_current_user(request: Request) -> Dict:
    # TODO: Implement proper JWT/auth validation
    return {"id": "user123", "kyc_level": 1, "email": "user@example.com"}

async def rate_limit(request: Request):
    user_id = (await get_current_user(request))["id"]
    key = f"rate_limit:{user_id}"
    
    try:
        count = await redis.get(key)
        if count is None:
            await redis.set(key, 1, ex=60)
        elif int(count) >= 100:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        else:
            await redis.incr(key)
    except Exception as e:
        logger.error(f"Rate limiting failed: {e}")
        # Don't block requests on rate limit failures

@router.get("/health")
async def health_check():
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "seamount-api",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/usds/balance")
async def get_usds_balance():
    try:
        total_supply = await usds_manager.get_total_supply()
        circulating_supply = await usds_manager.get_circulating_supply()
        reserve_balance = total_supply  # 1:1 backing
        
        return {
            "total_supply": float(total_supply),
            "circulating_supply": float(circulating_supply),
            "reserve_balance": float(reserve_balance),
            "backing_ratio": 1.0,
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"USDS balance check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions/recent")
async def get_recent_transactions(limit: int = 10, offset: int = 0):
    try:
        transactions = await payment_engine.supabase.table("payment_transactions").select("*").order("timestamp", desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            "transactions": [
                {
                    "id": tx["id"],
                    "type": tx["transaction_type"],
                    "amount": float(tx["amount"]),
                    "currency": "USDS",
                    "status": tx["status"],
                    "user_email": tx.get("user_email", ""),
                    "created_at": tx["timestamp"],
                    "blockchain_tx": tx["tx_id"]
                } for tx in transactions.data
            ],
            "total_count": len(transactions.data),
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Transaction history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/usds/mint")
async def mint_usds(req: MintUSDSRequest, current_user: Dict = Depends(get_current_user), _ = Depends(rate_limit)):
    """Mint new USDS stablecoin tokens to a recipient address"""
    try:
        if current_user["kyc_level"] < 2:  # Admin-level KYC
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get recipient's country from profile
        recipient_profile = await payment_engine.supabase.table("user_profiles").select("country_code").eq("algorand_address", req.recipient).execute()
        
        if not recipient_profile.data:
            country_code = "ZA"
            logger.warning(f"No profile found for {req.recipient}, using default country ZA")
        else:
            country_code = recipient_profile.data[0].get("country_code", "ZA")
        
        # Mint USDS tokens
        mint_result = await usds_manager.mint_usds(
            req.recipient,
            Decimal(str(req.amount)),
            country_code,
            CollateralType.USD_BANK_RESERVE,
            f"admin_mint_{current_user['id']}"
        )
        
        if not mint_result.get('success', False):
            raise HTTPException(
                status_code=400, 
                detail=mint_result.get('error', 'Minting failed')
            )
        
        # Record transaction
        await payment_engine.supabase.table("payment_transactions").insert({
            "transaction_type": "mint",
            "amount": float(req.amount),
            "fee": 0,  # Admin mint has no fee
            "currency": "USDS",
            "status": "completed",
            "sender_address": usds_manager.treasury_account['address'],
            "receiver_address": req.recipient,
            "country_code": country_code,
            "payment_type": "mint",
            "tx_id": mint_result.get('tx_id', ''),
            "blockchain_tx": mint_result['algorand_tx_hash'],
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
        
        return {
            "status": "success",
            "transaction_id": mint_result.get('tx_id', ''),
            "algorand_tx_hash": mint_result['algorand_tx_hash'],
            "amount": float(req.amount),
            "fees": 0,
            "recipient": req.recipient,
            "country": country_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"USDS minting failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_platform_stats():
    try:
        # Get platform statistics from payment engine
        stats = await payment_engine.get_platform_metrics()
        
        # Get USDS supply metrics
        usds_metrics = await usds_manager.get_usds_metrics()
        
        return {
            "total_transactions": stats.get("p2p_count", 0) + stats.get("cross_border_count", 0),
            "total_volume": stats.get("p2p_volume", 0) + stats.get("cross_border_volume", 0),
            "active_users": stats.get("active_users", 0),
            "usds_supply": float(usds_metrics.get("total_supply", 0)),
            "circulating_supply": float(usds_metrics.get("circulating_supply", 0)),
            "supported_corridors": len([
                "NG-KE", "KE-NG", "ZA-NG", "ZA-KE", "NG-GH", "KE-ZA"
            ]),
            "last_updated": datetime.utcnow().isoformat(),
            "network_status": "active"
        }
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deposit/fiat")
async def deposit_fiat(req: DepositFiatRequest, current_user: Dict = Depends(get_current_user), _ = Depends(rate_limit)):
    try:
        if current_user["kyc_level"] == 0:
            raise HTTPException(status_code=403, detail="KYC verification required")
        
        result = await payment_engine.deposit_fiat(
            user_id=current_user["id"],
            amount_usd=req.amount_usd,
            email=req.email,
            phone=req.phone
        )
        return result
    except Exception as e:
        logger.error(f"Fiat deposit failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/withdraw/fiat")
async def withdraw_fiat(req: WithdrawFiatRequest, current_user: Dict = Depends(get_current_user), _ = Depends(rate_limit)):
    try:
        if current_user["kyc_level"] == 0:
            raise HTTPException(status_code=403, detail="KYC verification required")
        
        result = await payment_engine.withdraw_fiat(
            user_id=current_user["id"],
            amount_usds=req.amount_usds,
            bank_details=req.bank_details
        )
        return result
    except Exception as e:
        logger.error(f"Fiat withdrawal failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/dispute/create")
async def create_dispute(req: DisputeRequest, current_user: Dict = Depends(get_current_user), _ = Depends(rate_limit)):
    try:
        result = await payment_engine.create_dispute(
            transaction_id=req.transaction_id,
            user_id=current_user["id"],
            reason=req.reason
        )
        return result
    except Exception as e:
        logger.error(f"Dispute creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/dispute/update")
async def update_dispute(req: DisputeUpdateRequest, current_user: Dict = Depends(get_current_user), _ = Depends(rate_limit)):
    try:
        if current_user["kyc_level"] < 2:  # Admin-level KYC
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await payment_engine.supabase.table("disputes").update({"status": req.status}).eq("id", req.transaction_id).execute()
        return result.data[0]
    except Exception as e:
        logger.error(f"Dispute update failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/payment/cross-border")
async def create_cross_border_payment(
    amount: float = Body(...),
    recipient_address: str = Body(...),
    from_currency: str = Body(...),
    to_currency: str = Body(...),
    memo: str = Body(""),
    current_user: Dict = Depends(get_current_user),
    _ = Depends(rate_limit)
):
    """Create a new cross-border payment"""
    try:
        # Convert string currencies to enum
        from_currency_enum = Currency(from_currency)
        to_currency_enum = Currency(to_currency)
        
        # Create cross-border payment
        request = await payment_engine.create_cross_border_payment(
            sender_user_id=current_user["id"],
            receiver_address=recipient_address,
            amount=Decimal(str(amount)),
            from_currency=from_currency_enum,
            to_currency=to_currency_enum,
            memo=memo
        )
        
        # Execute payment immediately
        result = await payment_engine.execute_cross_border_payment(request.id)
        
        return {
            "status": result.status.value,
            "payment_id": result.request_id,
            "tx_id": result.tx_id,
            "amount": float(result.final_amount) if result.final_amount else None,
            "fees": float(result.fees) if result.fees else None,
            "exchange_rate": float(result.exchange_rate) if result.exchange_rate else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Cross-border payment failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))