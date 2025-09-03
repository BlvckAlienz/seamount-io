# File Location: backend/api/routes/users.py
# CRITICAL: Add this new router to fix 404 errors

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from typing import Dict, Any
from pydantic import BaseModel, Field
import traceback

from dependencies import get_current_user, get_supabase_client
from models import UserProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/user", tags=["User"])

class UpdateProfileRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    country_code: str = Field(..., min_length=2, max_length=3)

@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> UserProfile:
    """FIXED: Get user profile - matches frontend expectation"""
    try:
        # Handle KYC status validation errors gracefully
        safe_user = current_user.copy()
        if safe_user.get('kyc_status') not in [
            'not_started', 'initiated', 'in_progress', 
            'under_review', 'approved', 'rejected', 'skipped'
        ]:
            safe_user['kyc_status'] = 'not_started'
        
        return UserProfile(**safe_user)
        
    except Exception as e:
        logger.warning(f"Profile validation error, returning safe version: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Error processing user profile"
        )

@router.put("/profile")
async def update_user_profile(
    profile_updates: UpdateProfileRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """FIXED: Update user profile with proper field mapping"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        # Prepare update data with correct field names
        update_data = {
            "first_name": profile_updates.first_name.strip(),
            "last_name": profile_updates.last_name.strip(),
            "country_code": profile_updates.country_code.upper(),
            "updated_at": "now()"
        }
        
        # Update in database
        result = supabase.table('user_profiles').update(update_data).eq('id', user_id).execute()
        
        if not result.data:
            logger.error(f"Failed to update profile for user {user_id}")
            raise HTTPException(status_code=500, detail="Profile update failed")
        
        updated_profile = result.data[0]
        logger.info(f"Profile updated successfully for user: {user_id}")
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "profile": updated_profile
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error for user {current_user.get('id', 'unknown')}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")

@router.post("/profile", response_model=UserProfile)
async def create_user_profile(
    profile_data: Dict[str, Any],
    supabase: Client = Depends(get_supabase_client)
):
    """Create user profile - matches frontend expectation"""
    try:
        # Convert camelCase to snake_case for database
        db_data = {
            "id": profile_data.get("id"),
            "email": profile_data.get("email"),
            "first_name": profile_data.get("firstName", ""),
            "last_name": profile_data.get("lastName", ""),
            "country_code": profile_data.get("countryCode", "US").upper(),
            "kyc_status": "not_started",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Insert profile
        result = supabase.from_("user_profiles").insert(db_data).execute()
        
        if not result.data:
            logger.error(f"Failed to create profile for user {profile_data.get('id')}")
            raise HTTPException(status_code=500, detail="Profile creation failed")
        
        created_profile = result.data[0]
        logger.info(f"Profile created successfully for user: {profile_data.get('id')}")
        
        return UserProfile(**created_profile)
        
    except Exception as e:
        logger.error(f"Profile creation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Profile creation failed: {str(e)}")
        
@router.post("/users/profile")
async def create_user_profile_legacy(
    profile_data: Dict[str, Any],
    supabase: Client = Depends(get_supabase_client)
):
    """Legacy endpoint support - maps to new endpoint"""
    return await create_user_profile(profile_data, supabase)

@router.get("/users/profile")
async def get_user_profile_legacy(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Legacy endpoint support - maps to new endpoint"""
    return await get_user_profile(current_user)
