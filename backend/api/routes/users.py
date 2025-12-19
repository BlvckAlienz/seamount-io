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
    """Create user profile with proper data capture - FIXED VERSION"""
    try:
        data = await request.json()
        user_id = data.get('id')
        
        # 🚨 CRITICAL FIX: Properly extract ALL data from frontend
        insert_data = {
            "id": user_id,
            "email": data.get('email', ''),
            "first_name": data.get('firstName', data.get('first_name', '')),  # Handle both formats
            "last_name": data.get('lastName', data.get('last_name', '')),
            "country_code": (data.get('countryCode') or data.get('country_code') or 'US').upper(),
            "phone": data.get('phone', ''),
            "kyc_status": "not_started",
            "kyc_level": 0,
            "role": "alien",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # ✅ Log for verification
        logger.info(f"[Profile Create] User {user_id}: {insert_data['first_name']} {insert_data['last_name']} ({insert_data['country_code']})")
        
        # Upsert to handle duplicate attempts
        result = supabase.from_("user_profiles").upsert(
            insert_data, 
            on_conflict="id"
        ).execute()
        
        if not result.data:
            raise Exception("Profile creation returned no data")
        
        return {
            "success": True, 
            "profile": result.data[0],
            "message": f"Profile created for {insert_data['first_name']}"
        }
        
    except Exception as e:
        logger.error(f"[Profile Create] Failed: {e}")
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
    """Update user profile - NOW INCLUDES BUSINESS QUESTIONNAIRE FIELDS"""
    
    # 🆕 EXPANDED: Core profile + KYC + Business questionnaire fields
    allowed_fields = [
        # Core profile fields
        'first_name', 'last_name', 'country_code', 'phone', 
        'date_of_birth', 'gender', 'kyc_status', 'kyc_level',
        
        # KYC-specific fields
        'bvn', 'id_type',
        
        # 🆕 Business questionnaire fields
        'account_type', 'business_type', 'legal_business_name', 
        'registered_company_number', 'company_size', 
        'business_sector', 'intent', 'tokenization_details',
        'capital_raising_details', 'has_corporate_docs',
        'questionnaire_completed', 'questionnaire_completed_at',
        'onboarding_complete'
    ]
    
    """Update user profile"""
    try:
        data = await request.json()
        user_id = current_user.get('id')
        
        logger.info(f"[Profile Update] User {user_id} updating fields: {list(data.keys())}")
        
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        
        # ✅ Process allowed fields (snake_case)
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        # ✅ Handle camelCase from frontend (legacy support)
        camel_to_snake_mapping = {
            'firstName': 'first_name',
            'lastName': 'last_name',
            'countryCode': 'country_code',
            'dateOfBirth': 'date_of_birth',
            'kycStatus': 'kyc_status',
            'kycLevel': 'kyc_level',
            'accountType': 'account_type',
            'businessType': 'business_type',
            'legalBusinessName': 'legal_business_name',
            'registeredCompanyNumber': 'registered_company_number',
            'companySize': 'company_size',
            'businessSector': 'business_sector',
            'tokenizationDetails': 'tokenization_details',
            'capitalRaisingDetails': 'capital_raising_details',
            'hasCorporateDocs': 'has_corporate_docs',
            'questionnaireCompleted': 'questionnaire_completed',
            'questionnaireCompletedAt': 'questionnaire_completed_at',
            'onboardingComplete': 'onboarding_complete'
        }
        
        for camel_key, snake_key in camel_to_snake_mapping.items():
            if camel_key in data:
                update_data[snake_key] = data[camel_key]
        
        # ✅ Uppercase country_code if present
        if 'country_code' in update_data:
            update_data['country_code'] = update_data['country_code'].upper()
        
        # 🆕 Log business questionnaire completion
        if update_data.get('questionnaire_completed'):
            logger.info(f"[Questionnaire] User {user_id} completed business questionnaire: "
                       f"Type={update_data.get('account_type')}, "
                       f"Business={update_data.get('business_type')}, "
                       f"Sector={update_data.get('business_sector')}, "
                       f"Intent={update_data.get('intent')}")
            
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
    CRITICAL FIX: Provision Algorand wallet with mnemonic return
    ✅ FIXED: Now returns exact structure frontend expects
    """
    try:
        user_id = current_user['id']
        logger.info(f"[Wallet Provision] User: {user_id}")
        
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
                    return {
                        "success": True,
                        "mnemonic": None,  # Don't return mnemonic for existing wallets
                        "message": "Wallet already exists"
                    }
        except Exception as check_error:
            logger.warning(f"Existing wallet check failed: {check_error}")
        
        # Create new wallet
        from cryptography.fernet import Fernet
        import os
        from algosdk import account, mnemonic
        
        # Generate keypair
        private_key, address = account.generate_account()
        mnemonic_phrase = mnemonic.from_private_key(private_key)
        
        # Fund wallet (non-blocking)
        try:
            await wallet_service.algorand.fund_account_for_opt_in(address)
            logger.info(f"✅ Funded wallet {address[:10]}...")
        except Exception as fund_error:
            logger.warning(f"⚠️ Wallet funding skipped: {fund_error}")
        
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
        
        wallet_service.db.supabase.table('user_wallets').upsert(
            wallet_data,
            on_conflict='user_id'
        ).execute()
        
        logger.info(f"[Wallet Provision] Created: {address[:10]}...")
        
        # ✅ CRITICAL FIX: Return exact structure frontend expects
        return {
            "success": True,
            "mnemonic": mnemonic_phrase,  # ✅ Return for first-time backup
            "wallet_address": address,    # ✅ Keep for backward compatibility
            "message": "Wallet created successfully"
        }
            
    except Exception as e:
        logger.error(f"[Wallet Provision] Failed: {e}")
        import traceback
        logger.error(f"[Wallet Provision] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

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
        profile = await db_service.get_user_profile(user_id)
        
        if not profile:
            return {
                'status': 'not_started',
                'cumulative_volume': 0.0,
                'limit': 5000.0,
                'remaining': 5000.0,
                'urgency': 'none'
            }
        
        kyc_status = profile.get('kyc_status', 'not_started')
        cumulative = Decimal(str(profile.get('cumulative_volume_30d', 0)))
        
        # Simple urgency calculation (you can enhance this)
        limit = 5000.0
        remaining = limit - float(cumulative)
        
        if remaining <= 0:
            urgency = 'critical'
        elif remaining < 1000:
            urgency = 'warning' 
        else:
            urgency = 'info'
        
        return {
            'status': kyc_status,
            'cumulative_volume': float(cumulative),
            'limit': limit,
            'remaining': remaining,
            'urgency': urgency,
            'percent_used': float((cumulative / limit) * 100) if limit > 0 else 0
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
    
@router.get("/questionnaire-stats")
async def get_questionnaire_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    🆕 Get aggregated business questionnaire statistics
    Requires admin role for now - remove auth for public dashboard
    """
    try:
        # Check if user is admin
        if not current_user.get('is_admin'):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Fetch all completed questionnaires
        result = supabase.from_("user_profiles")\
            .select("account_type, business_type, business_sector, intent, has_corporate_docs")\
            .eq("questionnaire_completed", True)\
            .execute()
        
        if not result.data:
            return {
                "success": True,
                "total_responses": 0,
                "stats": {}
            }
        
        data = result.data
        
        # Aggregate statistics
        stats = {
            "total_responses": len(data),
            "account_types": {},
            "business_types": {},
            "sectors": {},
            "intents": {},
            "has_docs": {"yes": 0, "no": 0}
        }
        
        for profile in data:
            # Account types
            account_type = profile.get('account_type', 'unknown')
            stats['account_types'][account_type] = stats['account_types'].get(account_type, 0) + 1
            
            # Business types (only for business accounts)
            if account_type == 'business':
                business_type = profile.get('business_type', 'unknown')
                stats['business_types'][business_type] = stats['business_types'].get(business_type, 0) + 1
                
                # Sectors
                sector = profile.get('business_sector', 'unknown')
                stats['sectors'][sector] = stats['sectors'].get(sector, 0) + 1
                
                # Intent
                intent = profile.get('intent', 'unknown')
                stats['intents'][intent] = stats['intents'].get(intent, 0) + 1
                
                # Corporate docs
                if profile.get('has_corporate_docs'):
                    stats['has_docs']['yes'] += 1
                else:
                    stats['has_docs']['no'] += 1
        
        # Calculate percentages
        total = stats['total_responses']
        stats['percentages'] = {
            "businesses": (stats['account_types'].get('business', 0) / total * 100) if total > 0 else 0,
            "tokenization_interest": (stats['intents'].get('tokenize_asset', 0) / total * 100) if total > 0 else 0,
            "capital_raising_interest": (stats['intents'].get('raise_capital', 0) / total * 100) if total > 0 else 0,
            "has_docs": (stats['has_docs']['yes'] / (stats['has_docs']['yes'] + stats['has_docs']['no']) * 100) 
                       if (stats['has_docs']['yes'] + stats['has_docs']['no']) > 0 else 0
        }
        
        logger.info(f"[Questionnaire Stats] Generated stats for {total} responses")
        
        return {
            "success": True,
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Questionnaire Stats] Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")