# File Location: backend/api/routes/webhooks.py
from fastapi import APIRouter, Request, HTTPException, Depends
from supabase import Client
import logging
import hmac
import hashlib
from dependencies import get_supabase_client
from config import get_settings, Settings  # Import Settings class
from services.wallet_service import WalletService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/complycube")
async def handle_complycube_webhook(
    request: Request,
    supabase: Client = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings)
):
    # Verify webhook signature
    signature = request.headers.get("X-ComplyCube-Signature")
    body = await request.body()
    
    if not verify_signature(body, signature, settings.COMPLYCUBE_WEBHOOK_SECRET.get_secret_value()):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    event = await request.json()
    
    if event["type"] == "check.completed" and event["data"]["status"] == "complete":
        applicant_id = event["data"]["applicantId"]
        
        # Find user with this applicant ID
        user_res = supabase.from_("user_profiles").select("*").eq("complycube_applicant_id", applicant_id).execute()
        
        if user_res.data:
            user_id = user_res.data[0]["id"]
            
            # Update user role to 'tribe'
            supabase.from_("user_profiles").update({
                "role": "tribe",
                "kyc_status": "approved",
                "kyc_level": 3
            }).eq("id", user_id).execute()
            
            # Create wallet for user
            wallet_service = WalletService(settings, supabase)
            await wallet_service.provision_user_wallet(user_id)
            
            logger.info(f"User {user_id} KYC completed and wallet created")
    
    return {"status": "success"}

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    # Implement proper signature verification logic
    if not signature or not secret:
        return False
        
    try:
        expected_signature = hmac.new(
            secret.encode(), 
            payload, 
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False