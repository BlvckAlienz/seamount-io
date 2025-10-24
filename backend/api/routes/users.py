# File Location: backend/api/routes/users.py
# CRITICAL FIX: Proper wallet provisioning with mnemonic return

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timezone
from decimal import Decimal
import uuid

from backend.dependencies import get_supabase_client, get_current_user, get_multi_chain_wallet_service, get_database_service
from backend.services.multi_chain_wallet_service import MultiChainWalletService as WalletService
from backend.config import KYCConfig

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/profile")
async def create_user_profile(
    request: Request,
    supabase=Depends(get_supabase_client)
):
    """Create user profile - FIXED to handle KYC fields"""
    try:
        data = await request.json()
        user_id = data.get('id')
        
        insert_data = {
            "id": user_id,
            "email": data.get('email', ''),
            "first_name": data.get('firstName', ''),
            "last_name": data.get('lastName', ''),
            "country_code": data.get('countryCode', 'US').upper(),
            "phone": data.get('phone', ''),
            # ✅ ADD: KYC fields with safe defaults
            "bvn": data.get('bvn'),  # nullable
            "id_number": data.get('id_number'),  # nullable
            "id_type": data.get('id_type', 'BVN'),
            "date_of_birth": data.get('date_of_birth'),  # nullable
            "gender": data.get('gender'),  # nullable
            "kyc_status": "not_started",
            "kyc_level": 0,
            "role": "alien",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase.from_("user_profiles").upsert(insert_data, on_conflict="id").execute()
        
        return {"success": True, "profile": result.data[0]}
        
    except Exception as e:
        logger.error(f"Profile creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@router.post("/change-password")
async def change_password(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """Change user password"""
    try:
        data = await request.json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            raise HTTPException(status_code=400, detail="Both passwords required")
        if len(new_password) < 8:
            raise HTTPException(status_code=400, detail="Password must be 8+ characters")
        
        user_id = current_user.get('id')
        email = current_user.get('email')
        
        # Verify current password
        sign_in = supabase.auth.sign_in_with_password({
            "email": email,
            "password": current_password
        })
        if not sign_in:
            raise HTTPException(status_code=400, detail="Current password incorrect")
        
        # Update password
        supabase.auth.admin.update_user_by_id(user_id, {"password": new_password})
        
        logger.info(f"[Password Change] Success: {user_id}")
        return {"success": True, "message": "Password updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Password Change] Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Password change failed")

@router.post("/provision-wallets")
async def provision_wallets(
    current_user: Dict[str, Any] = Depends(get_current_user),
    wallet_service: WalletService = Depends(get_multi_chain_wallet_service)
):
    """
    CRITICAL FIX: Provision Algorand wallet with PROPER mnemonic return
    ✅ FIXED: Now ALWAYS returns mnemonic when creating new wallet
    """
    try:
        user_id = current_user['id']
        logger.info(f"[Wallet Provision] Starting for user: {user_id}")
        
        # Check if wallet exists
        try:
            existing = wallet_service.db.supabase.table('user_wallets')\
                .select('algorand_address, algorand_mnemonic')\
                .eq('user_id', user_id)\
                .execute()
            
            if existing.data and len(existing.data) > 0:
                existing_wallet = existing.data[0]
                if existing_wallet.get('algorand_address'):
                    logger.info(f"[Wallet Provision] Wallet exists: {existing_wallet['algorand_address'][:10]}...")
                    
                    # ✅ FIX: If wallet exists but we need mnemonic for onboarding, return error
                    # since we can't retrieve encrypted mnemonic
                    return {
                        "success": False,
                        "error": "Wallet already exists. Cannot retrieve mnemonic for existing wallet.",
                        "code": "WALLET_ALREADY_EXISTS"
                    }
        except Exception as check_error:
            logger.warning(f"Existing wallet check failed: {check_error}")
        
        # Create new wallet
        from cryptography.fernet import Fernet
        import os
        from algosdk import account, mnemonic
        
        logger.info("[Wallet Provision] Generating new Algorand keypair...")
        
        # Generate keypair
        private_key, address = account.generate_account()
        mnemonic_phrase = mnemonic.from_private_key(private_key)
        
        logger.info(f"[Wallet Provision] Generated wallet: {address[:10]}...")
        
        # Fund wallet (non-blocking) - but don't let this fail the whole process
        funding_success = False
        try:
            await wallet_service.algorand.fund_account_for_opt_in(address)
            funding_success = True
            logger.info(f"✅ Funded wallet {address[:10]}...")
        except Exception as fund_error:
            logger.warning(f"⚠️ Wallet funding skipped: {fund_error}")
            # Continue without funding - user can fund later
        
        # Encrypt keys
        encryption_key = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())
        fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        
        encrypted_private_key = fernet.encrypt(private_key.encode()).decode()
        encrypted_mnemonic = fernet.encrypt(mnemonic_phrase.encode()).decode()
        
        # Store wallet
        wallet_data = {
            'user_id': user_id,
            'algorand_address': address,
            'algorand_private_key': encrypted_private_key,
            'algorand_mnemonic': encrypted_mnemonic,
            'created_at': datetime.utcnow().isoformat()
        }
        
        logger.info("[Wallet Provision] Storing wallet in database...")
        
        insert_result = wallet_service.db.supabase.table('user_wallets').upsert(
            wallet_data,
            on_conflict='user_id'
        ).execute()
        
        logger.info(f"[Wallet Provision] Success! Wallet stored for user: {user_id}")
        
        # ✅ CRITICAL FIX: Return EXACT structure frontend expects
        return {
            "success": True,
            "mnemonic": mnemonic_phrase,  # ✅ MUST BE PRESENT for new wallets
            "wallet_address": address,
            "funded": funding_success,
            "message": "Wallet created successfully"
        }
            
    except Exception as e:
        logger.error(f"[Wallet Provision] Failed: {e}")
        import traceback
        logger.error(f"[Wallet Provision] Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "code": "WALLET_CREATION_FAILED"
        }

@router.post("/debug/provision-wallets")
async def debug_provision_wallets(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Temporary debug endpoint to test wallet creation
    """
    try:
        from algosdk import account, mnemonic
        
        # Generate test wallet
        private_key, address = account.generate_account()
        mnemonic_phrase = mnemonic.from_private_key(private_key)
        
        logger.info(f"[Debug] Generated test wallet: {address}")
        
        return {
            "success": True,
            "mnemonic": mnemonic_phrase,
            "wallet_address": address,
            "test": True,
            "message": "Debug wallet created successfully"
        }
        
    except Exception as e:
        logger.error(f"[Debug] Failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/kyc-status")
async def get_kyc_status(
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_database_service)
):
    """
    Get user's KYC status and transaction limit info
    """
    
    try:
        user_id = current_user['id']
        
        # Get user profile
        profile = db_service.supabase.table('user_profiles')\
            .select('kyc_status, cumulative_volume_30d')\
            .eq('id', user_id)\
            .execute()
        
        if not profile.data or len(profile.data) == 0:
            return {
                'status': 'not_started',
                'cumulative_volume': 0.0,
                'limit': float(KYCConfig.THRESHOLD_USD),
                'remaining': float(KYCConfig.THRESHOLD_USD),
                'urgency': 'none'
            }
        
        data = profile.data[0]
        kyc_status = data.get('kyc_status', 'not_started')
        cumulative = Decimal(str(data.get('cumulative_volume_30d', 0)))
        
        remaining = KYCConfig.calculate_remaining_limit(cumulative)
        urgency = KYCConfig.get_urgency_level(cumulative)
        
        return {
            'status': kyc_status,
            'cumulative_volume': float(cumulative),
            'limit': float(KYCConfig.THRESHOLD_USD),
            'remaining': float(remaining),
            'urgency': urgency,
            'percent_used': float((cumulative / KYCConfig.THRESHOLD_USD) * 100) if KYCConfig.THRESHOLD_USD > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"KYC status query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    
@router.get("/wallet-info")
async def get_wallet_info(
    current_user: Dict[str, Any] = Depends(get_current_user),
    wallet_service: WalletService = Depends(get_multi_chain_wallet_service)
):
    """Get wallet info without creating one"""
    try:
        user_id = current_user.get('id')
        wallet_info = await wallet_service.get_wallet_info(user_id)
        
        return {
            "success": True,
            "wallet_exists": wallet_info.get("wallet_exists", False),
            "wallet_address": wallet_info.get("wallet_address"),
            "blockchain": wallet_info.get("blockchain", "algorand")
        }
    except Exception as e:
        logger.error(f"[Wallet Info] Error: {str(e)}")
        return {"success": True, "wallet_exists": False}