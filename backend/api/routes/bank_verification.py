# File: backend/api/routes/bank_verification.py
"""
🎯 Paystack Bank Verification Proxy
Keeps API keys secure on backend
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import logging

from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bank", tags=["Bank Verification"])

class BankVerificationRequest(BaseModel):
    account_number: str
    bank_code: str

@router.post("/verify")
async def verify_bank_account(request: BankVerificationRequest):
    """
    ✅ Verify Nigerian bank account via Paystack
    
    Security: Uses secret key from backend env
    Returns: Account holder name
    """
    
    settings = get_settings()
    
    # 🎯 CRITICAL: Use SECRET key, not public key
    paystack_secret = settings.PAYSTACK_SECRET_KEY
    if not paystack_secret:
        logger.error("❌ PAYSTACK_SECRET_KEY not configured")
        raise HTTPException(
            status_code=503,
            detail="Bank verification unavailable - Paystack not configured"
        )
    
    logger.info(f"🔍 Verifying account: {request.account_number} at bank {request.bank_code}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.paystack.co/bank/resolve",
                params={
                    "account_number": request.account_number,
                    "bank_code": request.bank_code
                },
                headers={
                    "Authorization": f"Bearer {paystack_secret.get_secret_value()}"
                },
                timeout=10.0
            )
            
            data = response.json()
            
            logger.debug(f"📡 Paystack response: {data}")
            
            if data.get("status") and data.get("data", {}).get("account_name"):
                account_name = data["data"]["account_name"]
                logger.info(f"✅ Account verified: {request.account_number} = {account_name}")
                
                return {
                    "success": True,
                    "account_name": account_name,
                    "account_number": request.account_number,
                    "bank_code": request.bank_code
                }
            else:
                error_msg = data.get("message", "Account verification failed")
                logger.warning(f"⚠️ Verification failed: {error_msg}")
                raise HTTPException(status_code=400, detail=error_msg)
                
    except httpx.TimeoutException:
        logger.error("⏱️ Paystack timeout")
        raise HTTPException(status_code=504, detail="Bank verification timeout - please retry")
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Paystack HTTP error: {e.response.status_code}")
        raise HTTPException(status_code=502, detail=f"Paystack error: {e.response.status_code}")
    except httpx.HTTPError as e:
        logger.error(f"❌ Paystack connection error: {e}")
        raise HTTPException(status_code=502, detail="Bank verification service unavailable")
    except Exception as e:
        logger.error(f"💥 Unexpected verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check for bank verification service"""
    settings = get_settings()
    
    has_key = bool(settings.PAYSTACK_SECRET_KEY)
    
    return {
        "status": "healthy" if has_key else "degraded",
        "service": "bank-verification",
        "paystack_configured": has_key
    }