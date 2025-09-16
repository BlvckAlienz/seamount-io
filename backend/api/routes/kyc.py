# File Location: backend/api/routes/kyc.py
# CRITICAL FIX: Corrected import paths and proper KYC service integration

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from supabase import Client
from typing import Dict, Any, Optional
import traceback
import uuid

from backend.dependencies import get_current_user, get_supabase_client, get_kyc_service, get_wallet_service
from backend.models import UserProfile
from backend.services.kyc_service import KYCService
from backend.services.wallet_service import WalletService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/profile-check")
async def check_profile_completeness(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    CRITICAL FIX: Check if user profile is complete for KYC with robust error handling
    """
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        logger.info(f"[KYC Profile Check] User: {user_id}")
        
        # Profile should already be loaded from get_current_user dependency
        profile = current_user
        
        # Check required fields with proper validation
        required_fields = ['first_name', 'last_name', 'email']
        missing_fields = []
        errors = []
        
        for field in required_fields:
            field_value = profile.get(field)
            if not field_value or (isinstance(field_value, str) and field_value.strip() == ""):
                missing_fields.append(field)
                errors.append(f"Missing or empty field: {field}")
        
        # Additional validation
        email = profile.get('email', '').strip()
        if email and '@' not in email:
            missing_fields.append('email')
            errors.append("Invalid email format")
        
        profile_complete = len(missing_fields) == 0
        kyc_status = profile.get('kyc_status', 'not_started')
        
        logger.info(f"[KYC Profile Check] User {user_id}: complete={profile_complete}, missing={missing_fields}")
        
        return {
            "profile_complete": profile_complete,
            "missing_fields": missing_fields,
            "errors": errors,
            "can_start_kyc": profile_complete,
            "kyc_status": kyc_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[KYC Profile Check] Error for user {current_user.get('id', 'unknown')}: {str(e)}")
        logger.error(traceback.format_exc())
        
        return {
            "profile_complete": False,
            "missing_fields": ["first_name", "last_name", "email"],
            "errors": [f"System error: {str(e)}"],
            "can_start_kyc": False,
            "kyc_status": "not_started"
        }

@router.post("/start-verification")
async def start_kyc_verification(
    current_user: dict = Depends(get_current_user),
    kyc_service: KYCService = Depends(get_kyc_service),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """Start real KYC verification with ComplyCube"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        # Check if user already has active verification session
        current_kyc_status = current_user.get('kyc_status')
        if current_kyc_status == "in_progress":
            # Check if there's an active session in the database
            try:
                session_response = supabase.from_("kyc_sessions").select("session_id").eq("user_id", user_id).eq("status", "pending").maybe_single().execute()
                if session_response.data:
                    logger.warning(f"User {user_id} already has active KYC session")
                    return {
                        "success": False,
                        "error": "KYC verification session already active",
                        "kyc_status": current_user.get("kyc_status")
                    }
            except Exception as session_error:
                logger.warning(f"Could not check session status for user {user_id}: {session_error}")
                # Continue with new session creation if we can't verify existing session
        
        # FIX: Use the KYC service's public method instead of accessing complycube directly
        result = await kyc_service.start_verification_session(
            user_id,
            current_user.get('email'),
            current_user.get('country_code', 'US')
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "KYC verification failed"))
        
        return {
            "token": result.get("session_token"),  # Adjust based on actual response structure
            "applicantId": result.get("applicant_id"),
            "status": "success",
            "message": "KYC verification initiated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[KYC Start] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"KYC initialization failed. Error ID: {error_id}")

@router.post("/webhook")
async def kyc_webhook_handler(
    request: Request,
    supabase: Client = Depends(get_supabase_client),
    wallet_service: WalletService = Depends(get_wallet_service)
) -> Dict[str, Any]:
    """
    CRITICAL FIX: Handle KYC provider webhooks with robust error handling
    """
    try:
        webhook_data = await request.json()
        logger.info(f"[KYC Webhook] Received: {webhook_data}")
        
        # Extract essential data with fallbacks
        user_reference = webhook_data.get('user_reference') or webhook_data.get('reference') or webhook_data.get('clientId')
        status = webhook_data.get('status', 'unknown').lower()
        
        if not user_reference:
            logger.error(f"[KYC Webhook] Missing user reference: {webhook_data}")
            raise HTTPException(status_code=400, detail="Missing user reference")
        
        # Map provider status to our internal status
        status_mapping = {
            'approved': 'verified',
            'completed': 'verified', 
            'verified': 'verified',
            'passed': 'verified',
            'clear': 'verified',
            'rejected': 'rejected',
            'failed': 'rejected',
            'declined': 'rejected',
            'consider': 'under_review',
            'pending': 'in_progress',
            'in_progress': 'in_progress',
            'processing': 'in_progress'
        }
        
        internal_status = status_mapping.get(status, 'in_progress')
        
        # Find and update user by reference
        try:
            # Try direct user ID lookup first
            user_response = supabase.table('user_profiles').select('id').eq('id', user_reference).execute()
            
            if not user_response.data or len(user_response.data) == 0:
                # Try looking for user by applicant ID pattern
                if user_reference.startswith('applicant_'):
                    actual_user_id = user_reference.replace('applicant_', '')
                    user_response = supabase.table('user_profiles').select('id').eq('id', actual_user_id).execute()
            
            if not user_response.data or len(user_response.data) == 0:
                logger.error(f"[KYC Webhook] User not found for reference: {user_reference}")
                return {"success": False, "error": "User not found"}
            
            user_id = user_response.data[0]['id']
            
            # Update the user's KYC status
            update_data = {
                'kyc_status': internal_status,
                'updated_at': 'now()'
            }
            
            # Add completion timestamp if verified
            if internal_status == 'verified':
                update_data['kyc_completed_at'] = 'now()'
                update_data['kyc_level'] = 3  # Level 3 verification complete
                update_data['role'] = 'tribe'  # Grant Tribe status
                
                # Create USDS wallet automatically
                try:
                    wallet_data = wallet_service.create_algorand_wallet()
                    await wallet_service.store_encrypted_wallet(user_id, wallet_data)
                    
                    logger.info(f"Automatically created wallet for verified user: {user_id}")
                except Exception as wallet_error:
                    logger.error(f"Failed to create wallet for verified user {user_id}: {wallet_error}")
            
            # Add rejection reason if applicable
            if internal_status == 'rejected':
                update_data['kyc_rejection_reason'] = webhook_data.get('reason', 'Verification failed')
            
            update_result = supabase.table('user_profiles').update(update_data).eq('id', user_id).execute()
            
            logger.info(f"[KYC Webhook] Status updated for user {user_id}: {internal_status}")
            
            return {
                "success": True,
                "message": f"KYC status updated successfully for user {user_id}",
                "user_id": user_id,
                "new_status": internal_status
            }
            
        except Exception as db_error:
            logger.error(f"[KYC Webhook] Database update failed for reference {user_reference}: {str(db_error)}")
            return {
                "success": False, 
                "error": f"Database update failed: {str(db_error)}"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[KYC Webhook] Processing error [Error ID: {error_id}]: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Webhook processing failed. Error ID: {error_id}")

@router.get("/status/{user_id}")
async def get_kyc_status(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    CRITICAL FIX: Get KYC status for a specific user with proper authorization
    """
    try:
        # Ensure user can only check their own KYC status (or admin override)
        if current_user.get('id') != user_id and current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Access denied")
        
        logger.info(f"[KYC Status] Fetching status for user: {user_id}")
        
        profile_response = supabase.table('user_profiles').select(
            'kyc_status, kyc_level, kyc_completed_at, kyc_rejection_reason'
        ).eq('id', user_id).execute()
        
        if not profile_response.data or len(profile_response.data) == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        profile = profile_response.data[0]
        
        return {
            "user_id": user_id,
            "kyc_status": profile.get('kyc_status', 'not_started'),
            "kyc_level": profile.get('kyc_level', 0),
            "completed_at": profile.get('kyc_completed_at'),
            "rejection_reason": profile.get('kyc_rejection_reason'),
            "can_upgrade": profile.get('kyc_level', 0) < 3
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[KYC Status] Error for user {user_id} [Error ID: {error_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch KYC status. Error ID: {error_id}")

@router.post("/skip-verification")
async def skip_kyc_verification(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    CRITICAL FIX: Allow users to skip KYC verification for demo/testing purposes
    """
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        logger.info(f"[KYC Skip] User {user_id} requested to skip verification")
        
        # Update user status to allow limited access
        update_data = {
            'kyc_status': 'skipped',
            'kyc_level': 1,  # Basic level for skipped verification
            'verification_skipped': True,
            'updated_at': 'now()'
        }
        
        update_result = supabase.table('user_profiles').update(update_data).eq('id', user_id).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to update verification status")
        
        logger.info(f"[KYC Skip] Verification skipped successfully for user: {user_id}")
        
        return {
            "success": True,
            "message": "Verification skipped successfully. You have limited access to platform features.",
            "kyc_status": "skipped",
            "kyc_level": 1,
            "access_level": "limited"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[KYC Skip] Error for user {current_user.get('id', 'unknown')} [Error ID: {error_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to skip verification. Error ID: {error_id}")

@router.get("/requirements")
async def get_kyc_requirements(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    CRITICAL FIX: Get KYC requirements based on user's country and current level
    """
    try:
        user_id = current_user.get('id')
        country_code = current_user.get('country_code', 'US')
        current_level = current_user.get('kyc_level', 0)
        
        logger.info(f"[KYC Requirements] User {user_id}, Country: {country_code}, Level: {current_level}")
        
        # Define requirements based on geographic tiers and levels
        geographic_tiers = {
            'tier_1': ['US', 'CA', 'GB', 'DE', 'FR', 'AU', 'JP', 'SG'],
            'tier_2_standard': ['MX', 'BR', 'IN', 'CN', 'KR', 'TH', 'MY'],
            'tier_2_african': ['NG', 'KE', 'EG', 'UG', 'ZW', 'TZ'],
            'tier_3': ['BD', 'PK', 'LK', 'MM', 'NP', 'ET']
        }
        
        # Determine user's tier
        user_tier = 'tier_3'  # Default to most restrictive
        for tier, countries in geographic_tiers.items():
            if country_code in countries:
                user_tier = tier
                break
        
        # Define level-based requirements and limits
        level_requirements = {
            0: {
                "max_transaction": 100,
                "max_monthly": 500,
                "features": ["basic_transfers"],
                "required_documents": []
            },
            1: {
                "max_transaction": 1000,
                "max_monthly": 5000,
                "features": ["basic_transfers", "p2p_payments"],
                "required_documents": ["email_verification"]
            },
            2: {
                "max_transaction": 10000,
                "max_monthly": 50000,
                "features": ["basic_transfers", "p2p_payments", "cross_border"],
                "required_documents": ["identity_document", "address_proof"]
            },
            3: {
                "max_transaction": 100000,
                "max_monthly": 500000,
                "features": ["all_features"],
                "required_documents": ["identity_document", "address_proof", "source_of_funds"]
            }
        }
        
        current_requirements = level_requirements.get(current_level, level_requirements[0])
        next_level_requirements = level_requirements.get(current_level + 1)
        
        return {
            "user_id": user_id,
            "country_code": country_code,
            "geographic_tier": user_tier,
            "current_level": current_level,
            "current_limits": current_requirements,
            "next_level": next_level_requirements,
            "can_upgrade": current_level < 3,
            "upgrade_required_for": {
                "higher_limits": current_level < 2,
                "cross_border": current_level < 2,
                "institutional_features": current_level < 3
            }
        }
        
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[KYC Requirements] Error for user {current_user.get('id', 'unknown')} [Error ID: {error_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch KYC requirements. Error ID: {error_id}")