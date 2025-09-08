# File Location: backend/api/routes/users.py
# CRITICAL FIX: Proper endpoint paths matching frontend expectations

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timezone
import uuid

from backend.dependencies import get_supabase_client, get_current_user, get_optional_auth

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
        logger.info(f"[Profile Create] Raw request data: {data}")
        
        # Extract user ID - must be provided in request
        user_id = data.get('id')
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # CRITICAL FIX: Verify user exists in auth.users before creating profile
        try:
            # Check if user exists in auth system first
            auth_user = supabase.auth.admin.get_user(user_id)
            if not auth_user.user:
                raise HTTPException(status_code=404, detail="User not found in authentication system")
        except Exception as auth_error:
            logger.error(f"[Profile Create] Auth user check failed: {auth_error}")
            raise HTTPException(status_code=400, detail="User must be authenticated before creating profile")
            
        logger.info(f"[Profile Create] Creating profile for user: {user_id}")
        
        # FIXED: Separate upsert and select operations
        try:
            # Step 1: Upsert the data
            upsert_result = supabase.from_("user_profiles").upsert(
                insert_data, 
                on_conflict="id"
            ).execute()
            
            logger.info(f"[Profile Create] Upsert successful")
            
            # Step 2: Fetch the created/updated record
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
            
        except Exception as db_error:
            error_id = str(uuid.uuid4())[:8]
            logger.error(f"[Profile Create] Database error [Error ID: {error_id}]: {str(db_error)}")
            logger.error(f"Traceback", exc_info=True)
            
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to create profile. Error ID: {error_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[Profile Create] Unexpected error [Error ID: {error_id}]: {str(e)}")
        logger.error(f"Traceback", exc_info=True)
        
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create profile. Error ID: {error_id}"
        )

@router.get("/profile")  # This creates /api/v1/user/profile endpoint
async def get_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user profile - matches frontend GET /api/v1/user/profile"""
    
    try:
        user_id = current_user.get('id')
        logger.info(f"[Profile Get] Fetching profile for user: {user_id}")
        
        # Profile is already fetched by get_current_user dependency
        logger.info(f"[Profile Get] Profile retrieved successfully for user: {user_id}")
        
        return {
            "success": True,
            "profile": current_user
        }
        
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[Profile Get] Error [Error ID: {error_id}]: {str(e)}")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch profile. Error ID: {error_id}"
        )

@router.put("/profile")  # This creates /api/v1/user/profile endpoint
async def update_user_profile(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """Update user profile - matches frontend PUT /api/v1/user/profile"""
    
    try:
        data = await request.json()
        user_id = current_user.get('id')
        
        logger.info(f"[Profile Update] Updating profile for user: {user_id}")
        
        # Build update data
        update_data = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Add fields that are allowed to be updated
        allowed_fields = ['first_name', 'last_name', 'country_code', 'phone', 'date_of_birth', 'kyc_status']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        # Handle firstName/lastName from frontend
        if 'firstName' in data:
            update_data['first_name'] = data['firstName']
        if 'lastName' in data:
            update_data['last_name'] = data['lastName']
        if 'countryCode' in data:
            # Ensure country code is uppercase
            update_data['country_code'] = data['countryCode'].upper()
            
        logger.info(f"[Profile Update] Update data: {update_data}")
        
        # FIXED: Separate update and select operations
        update_result = supabase.from_("user_profiles").update(update_data).eq("id", user_id).execute()
        
        # Fetch updated profile
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
        
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to update profile. Error ID: {error_id}"
        )