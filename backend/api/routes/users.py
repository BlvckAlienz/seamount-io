# File Location: backend/api/routes/users.py
# CRITICAL FIX: Proper wallet provisioning with mnemonic return

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timezone
import uuid

from backend.dependencies import get_supabase_client, get_current_user, get_wallet_service
from backend.services.wallet_service import WalletService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/profile")
async def create_user_profile(
    request: Request,
    supabase=Depends(get_supabase_client)
):
    """Create user profile - matches frontend POST /api/v1/user/profile"""
    try:
        data = await request.json()
        user_id = data.get('id')
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # Verify user exists in auth system
        try:
            auth_user = supabase.auth.admin.get_user(user_id)
            if not auth_user.user:
                raise HTTPException(status_code=404, detail="User not found in authentication system")
        except Exception as auth_error:
            logger.error(f"[Profile Create] Auth user check failed: {auth_error}")
            raise HTTPException(status_code=400, detail="User must be authenticated before creating profile")
            
        insert_data = {
            "id": user_id,
            "email": data.get('email', ''),
            "first_name": data.get('firstName') or data.get('first_name', ''),
            "last_name": data.get('lastName') or data.get('last_name', ''),
            "country_code": (data.get('countryCode') or data.get('country_code', 'US')).upper(),
            "phone": data.get('phone', ''),
            "kyc_status": "not_started",  # ✅ FIXED
            "kyc_level": 0,
            "role": "alien",
            "is_active": True,
            "kyc_provider": None,  # ✅ FIXED - NULL until KYC starts
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert and fetch
        upsert_result = supabase.from_("user_profiles").upsert(insert_data, on_conflict="id").execute()
        fetch_result = supabase.from_("user_profiles").select("*").eq("id", user_id).execute()
        
        if not fetch_result.data:
            raise HTTPException(status_code=500, detail="Profile created but could not be retrieved")
            
        profile = fetch_result.data[0]
        logger.info(f"[Profile Create] Profile created successfully: {profile.get('email')}")
        
        return {
            "success": True,
            "profile": profile,
            "message": "Profile created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[Profile Create] Unexpected error [Error ID: {error_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create profile. Error ID: {error_id}")

@router.get("/profile")
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get user profile"""
    try:
        user_id = current_user.get('id')
        logger.info(f"[Profile Get] Fetching profile for user: {user_id}")
        
        return {
            "success": True,
            "profile": current_user
        }
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[Profile Get] Error [Error ID: {error_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile. Error ID: {error_id}")

@router.put("/profile")
async def update_user_profile(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    # ADD KYC-SPECIFIC FIELDS
    allowed_fields = [
        'first_name', 'last_name', 'country_code', 'phone', 
        'date_of_birth', 'gender', 'bvn', 'id_type'  # 🆕 ADD KYC FIELDS
    ]
    
    """Update user profile"""
    try:
        data = await request.json()
        user_id = current_user.get('id')
        
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        
        allowed_fields = ['first_name', 'last_name', 'country_code', 'phone', 'date_of_birth', 'kyc_status']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        # Handle camelCase from frontend
        if 'firstName' in data:
            update_data['first_name'] = data['firstName']
        if 'lastName' in data:
            update_data['last_name'] = data['lastName']
        if 'countryCode' in data:
            update_data['country_code'] = data['countryCode'].upper()
            
        update_result = supabase.from_("user_profiles").update(update_data).eq("id", user_id).execute()
        fetch_result = supabase.from_("user_profiles").select("*").eq("id", user_id).execute()
        
        if not fetch_result.data:
            raise HTTPException(status_code=404, detail="Profile not found after update")
            
        profile = fetch_result.data[0]
        logger.info(f"[Profile Update] Profile updated successfully for user: {user_id}")
        
        return {
            "success": True,
            "profile": profile,
            "message": "Profile updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[Profile Update] Error [Error ID: {error_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update profile. Error ID: {error_id}")

@router.post("/provision-wallets")
async def provision_wallets(
    current_user: Dict[str, Any] = Depends(get_current_user),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """
    CRITICAL FIX: Provision Algorand wallet with mnemonic return
    """
    try:
        user_id = current_user['id']
        logger.info(f"[Wallet Provision] User: {user_id}")
        
        # Check if wallet exists
        existing_wallet = await wallet_service.get_user_balances(user_id)
        if existing_wallet.get('wallet_exists'):
            return {
                "success": True,
                "wallet_address": existing_wallet['wallet_address'],
                "message": "Wallet already exists",
                "mnemonic": None  # Don't return mnemonic for existing wallets
            }
        
        # Create new wallet
        result = await wallet_service.create_algorand_wallet(user_id)
        
        if result["success"]:
            logger.info(f"[Wallet Provision] Wallet created: {result['wallet_address']}")
            return {
                "success": True,
                "wallet_address": result["wallet_address"],
                "mnemonic": result["mnemonic"],  # Return for one-time backup
                "supported_assets": result.get("supported_assets", []),
                "message": "Wallet created successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Wallet creation failed"))
            
    except Exception as e:
        logger.error(f"[Wallet Provision] Failed for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Wallet provisioning failed")
    
@router.post("/api/errors")
async def log_client_error(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Log frontend errors for debugging"""
    try:
        error_data = await request.json()
        logger.error(f"[Client Error] User: {current_user.get('id')} | {error_data}")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error logging failed: {e}")
        return {"success": False}, 500