# File Location: backend/api/routes/users.py
# SURGICAL FIX: Fixed profile creation/update endpoints and authentication

import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, ValidationError
from supabase import Client

from backend.dependencies import get_supabase_client, get_current_user, OptionalAuth
from backend.models import UserProfile, ProfileUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/user", tags=["User Management"])

class ProfileCreateRequest(BaseModel):
    """SURGICAL FIX: Schema-matched profile creation"""
    id: str  # Auth user ID
    user_id: str  # Additional field from schema
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    country_code: str = "US"
    kyc_status: str = "pending"  # Match DB default
    kyc_level: int = 0
    role: str = "alien"

class ProfileResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    country_code: Optional[str]
    kyc_status: str
    kyc_level: int
    created_at: str
    updated_at: str

@router.get("/profile", response_model=ProfileResponse)
async def get_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """SURGICAL FIX: Get user profile with proper error handling"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        logger.info(f"[Profile Get] Fetching profile for user: {user_id}")
        
        # Query user profile from database
        result = supabase.from_("user_profiles").select("*").eq("id", user_id).maybe_single().execute()
        
        if not result.data:
            logger.warning(f"[Profile Get] No profile found for user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        profile_data = result.data
        
        logger.info(f"[Profile Get] Profile retrieved successfully for user: {user_id}")
        
        return ProfileResponse(
            id=str(profile_data["id"]),
            email=profile_data["email"],
            first_name=profile_data.get("first_name") or "",
            last_name=profile_data.get("last_name") or "",
            country_code=profile_data.get("country_code") or "US",
            kyc_status=profile_data.get("kyc_status", "pending"),
            kyc_level=profile_data.get("kyc_level", 0),
            created_at=profile_data["created_at"],
            updated_at=profile_data["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"[Profile Get] Unexpected error for user {user_id} [Error ID: {error_id}]: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve profile. Error ID: {error_id}"
        )

@router.post("/profile", response_model=ProfileResponse)
async def create_user_profile(
    profile_data: ProfileCreateRequest,
    supabase: Client = Depends(get_supabase_client),
    current_user: Optional[Dict[str, Any]] = Depends(OptionalAuth())  # SURGICAL FIX: Allow creation without auth
):
    """SURGICAL FIX: Create user profile during registration"""
    try:
        logger.info(f"[Profile Create] Creating profile for user: {profile_data.id}")
        
        # SURGICAL FIX: Prepare data exactly matching schema
        insert_data = {
            "id": profile_data.id,  # Primary key (UUID from auth.users)
            "user_id": profile_data.user_id,  # Additional field in schema
            "email": profile_data.email.lower().strip(),
            "first_name": profile_data.first_name.strip() or "",
            "last_name": profile_data.last_name.strip() or "",
            "country_code": profile_data.country_code.upper(),
            "kyc_status": profile_data.kyc_status,
            "kyc_level": profile_data.kyc_level,
            "role": profile_data.role,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"[Profile Create] Insert data: {insert_data}")
        
        # SURGICAL FIX: Use upsert to handle potential duplicates
        result = supabase.from_("user_profiles").upsert(insert_data, on_conflict="id").select().execute()
        
        if not result.data:
            logger.error(f"[Profile Create] Database operation failed: {result}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user profile"
            )
        
        created_profile = result.data[0]
        logger.info(f"[Profile Create] Profile created successfully for user: {profile_data.id}")
        
        return ProfileResponse(
            id=str(created_profile["id"]),
            email=created_profile["email"],
            first_name=created_profile.get("first_name") or "",
            last_name=created_profile.get("last_name") or "",
            country_code=created_profile.get("country_code") or "US",
            kyc_status=created_profile.get("kyc_status", "pending"),
            kyc_level=created_profile.get("kyc_level", 0),
            created_at=created_profile["created_at"],
            updated_at=created_profile["updated_at"]
        )
        
    except ValidationError as e:
        logger.error(f"[Profile Create] Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid profile data: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"[Profile Create] Unexpected error [Error ID: {error_id}]: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create profile. Error ID: {error_id}"
        )

@router.put("/profile", response_model=ProfileResponse)
async def update_user_profile(
    profile_updates: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """SURGICAL FIX: Update user profile with authentication"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        logger.info(f"[Profile Update] Updating profile for user: {user_id}")
        logger.info(f"[Profile Update] Update data: {profile_updates}")
        
        # Validate and prepare update data
        allowed_fields = {
            "first_name", "last_name", "country_code", "kyc_status", 
            "kyc_level", "phone_number", "date_of_birth"
        }
        
        update_data = {}
        for field, value in profile_updates.items():
            if field in allowed_fields and value is not None:
                if field in ["first_name", "last_name"] and isinstance(value, str):
                    update_data[field] = value.strip()
                elif field == "country_code" and isinstance(value, str):
                    update_data[field] = value.upper()
                else:
                    update_data[field] = value
        
        # Always update the timestamp
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        if not update_data or update_data == {"updated_at": update_data["updated_at"]}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )
        
        # Perform update
        result = supabase.from_("user_profiles").update(update_data).eq("id", user_id).select().execute()
        
        if not result.data:
            logger.error(f"[Profile Update] Update failed for user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found or update failed"
            )
        
        updated_profile = result.data[0]
        logger.info(f"[Profile Update] Profile updated successfully for user: {user_id}")
        
        return ProfileResponse(
            id=str(updated_profile["id"]),
            email=updated_profile["email"],
            first_name=updated_profile.get("first_name") or "",
            last_name=updated_profile.get("last_name") or "",
            country_code=updated_profile.get("country_code") or "US",
            kyc_status=updated_profile.get("kyc_status", "pending"),
            kyc_level=updated_profile.get("kyc_level", 0),
            created_at=updated_profile["created_at"],
            updated_at=updated_profile["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"[Profile Update] Unexpected error for user {user_id} [Error ID: {error_id}]: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile. Error ID: {error_id}"
        )

@router.delete("/profile")
async def delete_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """SURGICAL FIX: Delete user profile (admin only or self-deletion)"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        logger.info(f"[Profile Delete] Deleting profile for user: {user_id}")
        
        # Soft delete - mark as inactive rather than hard delete
        update_data = {
            "is_active": False,
            "updated_at": datetime.utcnow().isoformat(),
            "email": f"deleted_{user_id}@seamount.deleted"  # Anonymize email
        }
        
        result = supabase.from_("user_profiles").update(update_data).eq("id", user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        logger.info(f"[Profile Delete] Profile soft-deleted for user: {user_id}")
        
        return JSONResponse(
            content={"message": "User profile deleted successfully"},
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"[Profile Delete] Unexpected error for user {user_id} [Error ID: {error_id}]: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete profile. Error ID: {error_id}"
        )