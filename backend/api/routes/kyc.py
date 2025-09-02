# File Location: backend/api/routes/kyc.py
# CRITICAL FIX: Robust profile checking with proper error handling

import logging
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from typing import Dict, Any, Optional
import traceback

from dependencies import get_current_user, get_supabase_client
from services.kyc_service import KYCService as KycService
from models import UserProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/kyc", tags=["kyc"])

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
        
        logger.info(f"Checking profile completeness for user: {user_id}")
        
        # Fetch user profile with error handling
        try:
            profile_response = supabase.table('user_profiles').select('*').eq('id', user_id).single().execute()
            
            if not profile_response.data:
                logger.warning(f"No profile found for user: {user_id}")
                return {
                    "profile_complete": False,
                    "missing_fields": ["first_name", "last_name", "email"],
                    "errors": ["Profile not found"],
                    "can_start_kyc": False,
                    "kyc_status": "not_started"
                }
                
            profile = profile_response.data
            
        except Exception as db_error:
            logger.error(f"Database error fetching profile for {user_id}: {str(db_error)}")
            return {
                "profile_complete": False,
                "missing_fields": ["first_name", "last_name", "email"],
                "errors": [f"Database error: {str(db_error)}"],
                "can_start_kyc": False,
                "kyc_status": "not_started"
            }
        
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
        
        logger.info(f"Profile check result for {user_id}: complete={profile_complete}, missing={missing_fields}")
        
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
        logger.error(f"Unexpected error in profile check for user {current_user.get('id', 'unknown')}: {str(e)}")
        logger.error(traceback.format_exc())
        
        return {
            "profile_complete": False,
            "missing_fields": ["first_name", "last_name", "email"],
            "errors": [f"System error: {str(e)}"],
            "can_start_kyc": False,
            "kyc_status": "not_started"
        }

@router.post("/update-profile")
async def update_user_profile(
    profile_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    CRITICAL FIX: Update user profile with proper validation and error handling
    """
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        logger.info(f"Updating profile for user: {user_id}")
        
        # Validate and sanitize input data
        allowed_fields = ['first_name', 'last_name', 'email']
        update_data = {}
        
        for field in allowed_fields:
            if field in profile_data:
                value = profile_data[field]
                if isinstance(value, str):
                    value = value.strip()
                if value:  # Only update non-empty values
                    update_data[field] = value
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        # Add timestamp
        update_data['updated_at'] = 'now()'
        
        # Update profile in database with error handling
        try:
            update_response = supabase.table('user_profiles').update(update_data).eq('id', user_id).execute()
            
            if not update_response.data:
                raise HTTPException(status_code=404, detail="Profile not found or update failed")
            
            updated_profile = update_response.data[0]
            logger.info(f"Profile updated successfully for user: {user_id}")
            
            return {
                "success": True,
                "message": "Profile updated successfully",
                "profile": updated_profile
            }
            
        except Exception as db_error:
            logger.error(f"Database error updating profile for {user_id}: {str(db_error)}")
            raise HTTPException(status_code=500, detail=f"Database update failed: {str(db_error)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating profile for user {current_user.get('id', 'unknown')}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")

@router.post("/start-verification")
async def start_kyc_verification(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    kyc_service: KycService = Depends(lambda: KycService())
) -> Dict[str, Any]:
    """
    CRITICAL FIX: Start KYC verification with enhanced prerequisite checking
    """
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        logger.info(f"Starting KYC verification for user: {user_id}")
        
        # CRITICAL: Double-check profile completeness before starting
        profile_check = await check_profile_completeness(current_user, supabase)
        
        if not profile_check["profile_complete"]:
            logger.warning(f"KYC verification blocked - incomplete profile for user: {user_id}")
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "Profile incomplete",
                    "missing_fields": profile_check["missing_fields"],
                    "message": "Please complete your profile before starting KYC verification"
                }
            )
        
        # Check if KYC already in progress or completed
        current_kyc_status = profile_check.get("kyc_status", "not_started")
        if current_kyc_status in ["in_progress", "completed"]:
            logger.info(f"KYC already {current_kyc_status} for user: {user_id}")
            return {
                "success": False,
                "message": f"KYC verification already {current_kyc_status}",
                "kyc_status": current_kyc_status
            }
        
        # Initialize KYC with retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                kyc_result = await kyc_service.start_verification(user_id)
                
                # Update KYC status in database
                try:
                    supabase.table('user_profiles').update({
                        'kyc_status': 'in_progress',
                        'kyc_started_at': 'now()',
                        'updated_at': 'now()'
                    }).eq('id', user_id).execute()
                    
                    logger.info(f"KYC verification started successfully for user: {user_id}")
                    
                    return {
                        "success": True,
                        "message": "KYC verification started",
                        "kyc_status": "in_progress",
                        "verification_url": kyc_result.get("verification_url"),
                        "reference": kyc_result.get("reference")
                    }
                    
                except Exception as db_error:
                    logger.error(f"Failed to update KYC status for {user_id}: {str(db_error)}")
                    # Continue with KYC even if status update fails
                    return {
                        "success": True,
                        "message": "KYC verification started (status update pending)",
                        "kyc_status": "in_progress",
                        "verification_url": kyc_result.get("verification_url"),
                        "reference": kyc_result.get("reference"),
                        "warning": "Status update may be delayed"
                    }
                
            except Exception as kyc_error:
                logger.warning(f"KYC start attempt {attempt + 1} failed for {user_id}: {str(kyc_error)}")
                if attempt == max_retries - 1:
                    logger.error(f"All KYC start attempts failed for {user_id}: {str(kyc_error)}")
                    raise HTTPException(
                        status_code=503, 
                        detail=f"KYC service unavailable after {max_retries} attempts: {str(kyc_error)}"
                    )
                
                # Wait before retry
                import asyncio
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error starting KYC for user {current_user.get('id', 'unknown')}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"KYC initialization failed: {str(e)}")

@router.post("/webhook")
async def kyc_webhook_handler(
    webhook_data: Dict[str, Any],
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    CRITICAL FIX: Handle KYC provider webhooks with robust error handling
    """
    try:
        logger.info(f"Received KYC webhook: {webhook_data}")
        
        # Extract essential data with fallbacks
        user_reference = webhook_data.get('user_reference') or webhook_data.get('reference')
        status = webhook_data.get('status', 'unknown').lower()
        
        if not user_reference:
            logger.error(f"Webhook missing user reference: {webhook_data}")
            raise HTTPException(status_code=400, detail="Missing user reference")
        
        # Map provider status to our internal status
        status_mapping = {
            'approved': 'completed',
            'completed': 'completed', 
            'verified': 'completed',
            'passed': 'completed',
            'rejected': 'rejected',
            'failed': 'rejected',
            'declined': 'rejected',
            'pending': 'in_progress',
            'in_progress': 'in_progress',
            'processing': 'in_progress'
        }
        
        internal_status = status_mapping.get(status, 'in_progress')
        
        # Update user KYC status with retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                update_data = {
                    'kyc_status': internal_status,
                    'kyc_completed_at': 'now()' if internal_status == 'completed' else None,
                    'updated_at': 'now()'
                }
                
                # Add rejection reason if applicable
                if internal_status == 'rejected':
                    update_data['kyc_rejection_reason'] = webhook_data.get('reason', 'Verification failed')
                
                # Find user by reference and update
                user_response = supabase.table('user_profiles').select('id').eq('id', user_reference).single().execute()
                
                if not user_response.data:
                    # Try finding by other potential reference fields
                    user_response = supabase.table('user_profiles').select('id').eq('kyc_reference', user_reference).single().execute()
                
                if not user_response.data:
                    logger.error(f"User not found for reference: {user_reference}")
                    return {"success": False, "error": "User not found"}
                
                user_id = user_response.data['id']
                
                # Update the user's KYC status
                supabase.table('user_profiles').update(update_data).eq('id', user_id).execute()
                
                logger.info(f"KYC status updated for user {user_id}: {internal_status}")
                
                return {
                    "success": True,
                    "message": f"KYC status updated to {internal_status}",
                    "user_id": user_id,
                    "status": internal_status
                }
                
            except Exception as update_error:
                logger.warning(f"Webhook update attempt {attempt + 1} failed: {str(update_error)}")
                if attempt == max_retries - 1:
                    logger.error(f"All webhook update attempts failed: {str(update_error)}")
                    raise HTTPException(status_code=500, detail="Failed to process webhook")
                
                # Wait before retry
                import asyncio
                await asyncio.sleep(2 ** attempt)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected webhook error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")
        