"""
User management routes with PROPER Supabase query chaining
File: backend/api/routes/users.py
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timezone
import uuid

from backend.dependencies import get_supabase_client, get_optional_auth, OptionalAuth

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/profile")
async def create_user_profile(
    request: Request,
    supabase=Depends(get_supabase_client),
    auth: OptionalAuth = Depends(get_optional_auth)
):
    """Create or update user profile with FIXED query chaining"""
    
    try:
        data = await request.json()
        logger.info(f"[Profile Create] Raw request data: {data}")
        
        # Extract user ID from auth or data
        user_id = None
        if auth and auth.payload:
            user_id = auth.payload.get('sub')
        
        if not user_id and 'id' in data:
            user_id = data['id']
            
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID required")
            
        logger.info(f"[Profile Create] Creating profile for user: {user_id}")
        
        # Build insert data with defaults
        now = datetime.now(timezone.utc).isoformat()
        
        # Handle country code - ensure uppercase
        country_code = data.get('countryCode', 'US') or data.get('country_code', 'US')
        if country_code:
            country_code = country_code.upper()
        else:
            country_code = 'US'
        
        insert_data = {
            "id": user_id,
            "user_id": user_id,
            "email": data.get('email', ''),
            "first_name": data.get('firstName', '') or data.get('first_name', ''),
            "last_name": data.get('lastName', '') or data.get('last_name', ''),
            "country_code": country_code,
            "kyc_status": "pending",
            "kyc_level": 0,
            "role": "alien",
            "created_at": now,
            "updated_at": now
        }
        
        logger.info(f"[Profile Create] Insert data: {insert_data}")
        
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
            logger.info(f"[Profile Create] Profile created/updated successfully: {profile.get('email')}")
            
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

@router.get("/profile")
async def get_user_profile(
    supabase=Depends(get_supabase_client),
    current_user: Optional[Dict] = Depends(OptionalAuth)
):
    """Get user profile"""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    user_id = current_user.get('sub')
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user token")
        
    try:
        logger.info(f"[Profile Get] Fetching profile for user: {user_id}")
        
        result = supabase.from_("user_profiles").select("*").eq("id", user_id).execute()
        
        if not result.data:
            logger.warning(f"[Profile Get] No profile found for user: {user_id}")
            raise HTTPException(status_code=404, detail="Profile not found")
            
        profile = result.data[0]
        logger.info(f"[Profile Get] Profile retrieved successfully for user: {user_id}")
        
        return {
            "success": True,
            "profile": profile
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[Profile Get] Error [Error ID: {error_id}]: {str(e)}")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch profile. Error ID: {error_id}"
        )

@router.put("/profile")
async def update_user_profile(
    request: Request,
    supabase=Depends(get_supabase_client),
    current_user: Optional[Dict] = Depends(OptionalAuth)
):
    """Update user profile"""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    user_id = current_user.get('sub')
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user token")
        
    try:
        data = await request.json()
        logger.info(f"[Profile Update] Updating profile for user: {user_id}")
        
        # Build update data
        update_data = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Add fields that are allowed to be updated
        allowed_fields = ['first_name', 'last_name', 'country_code', 'phone', 'date_of_birth']
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