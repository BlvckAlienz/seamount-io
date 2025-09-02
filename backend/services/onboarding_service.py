# File Location: backend/services/onboarding_service.py
# CRITICAL: Merged enhanced onboarding service with Redis state management and robust error handling

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from supabase import Client
from upstash_redis import Redis
from fastapi import HTTPException

# --- Core Dependencies ---
from config import Settings
from .wallet_service import WalletService  
from .kyc_service import KYCService
from .database_service import DatabaseService
from .email_service import EmailService
from .audit_service import AuditService
from .notification_service import NotificationService

logger = logging.getLogger(__name__)

class OnboardingService:
    """
    Enhanced orchestration service for multi-step user onboarding with robust error handling,
    Redis state management, and self-healing capabilities.
    """
    def __init__(self, settings: Settings, supabase_client: Client, wallet_service: WalletService, kyc_service: KYCService):
        self.settings = settings
        self.supabase = supabase_client
        self.wallet_service = wallet_service
        self.kyc_service = kyc_service
        
        # Initialize additional services with fallback handling
        try:
            self.db_service = DatabaseService()
            self.email_service = EmailService()
            self.audit_service = AuditService()
            self.notification_service = NotificationService()
        except Exception as e:
            logger.warning(f"Some services failed to initialize: {str(e)}")
            # Set to None to handle gracefully
            self.db_service = None
            self.email_service = None
            self.audit_service = None
            self.notification_service = None
        
        if not settings.UPSTASH_REDIS_REST_URL or not settings.UPSTASH_REDIS_REST_TOKEN:
            raise ValueError("Upstash Redis environment variables are not set for OnboardingService.")
        
        self.redis = Redis(
            url=settings.UPSTASH_REDIS_REST_URL, 
            token=settings.UPSTASH_REDIS_REST_TOKEN.get_secret_value()
        )
        logger.info("OnboardingService initialized successfully.")
    
    async def get_onboarding_status(self, user_id: str) -> dict:
        """
        Enhanced method that combines Redis cache with database fallback
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Try Redis first for performance
                progress_json = await self.redis.get(f"onboarding:{user_id}")
                if progress_json:
                    return json.loads(progress_json)
                
                # Fallback to database inference
                profile_res = await self.supabase.table("user_profiles").select(
                    "kyc_level, kyc_status, algorand_address, first_name, last_name, email, phone"
                ).eq("id", user_id).single().execute()
                
                if not profile_res.data:
                    raise HTTPException(status_code=404, detail="User profile not found.")
                
                user = profile_res.data
                kyc_level = user.get("kyc_level", 0)
                kyc_status = user.get("kyc_status", "not_started")
                has_wallet = user.get("algorand_address") is not None
                
                # Enhanced step inference with validation checks
                current_step = 1  # Welcome/Basic Info
                completeness_check = await self.check_profile_completeness(user_id)
                
                if completeness_check.get("profile_complete", False):
                    current_step = 2  # Identity/KYC
                    
                if kyc_level >= 1 or kyc_status in ["in_progress", "completed", "approved"]:
                    current_step = 3  # Wallet
                    
                if has_wallet and kyc_level >= 2:
                    current_step = 4  # Complete
                
                return {
                    "step": current_step, 
                    "data": {},
                    "kyc_status": kyc_status,
                    "profile_complete": completeness_check.get("profile_complete", False)
                }
                
            except Exception as e:
                retry_count += 1
                logger.error(f"Get onboarding status attempt {retry_count} failed for user {user_id}: {str(e)}")
                
                if retry_count >= max_retries:
                    raise HTTPException(status_code=500, detail="Could not retrieve onboarding status.")
                
                await asyncio.sleep(2 ** retry_count)
    
    async def check_profile_completeness(self, user_id: str) -> Dict[str, Any]:
        """
        CRITICAL: Enhanced profile completeness check with retry and validation
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use database service if available, otherwise direct Supabase
                if self.db_service:
                    profile_data = await self.db_service.get_user_profile(user_id)
                else:
                    profile_res = await self.supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
                    profile_data = profile_res.data if profile_res.data else None
                
                if not profile_data:
                    return {
                        "profile_complete": False,
                        "missing_fields": ["profile_not_found"],
                        "errors": ["User profile not found"],
                        "can_start_kyc": False,
                        "kyc_status": "not_started"
                    }
                
                # Required fields for KYC
                required_fields = {
                    "first_name": "First name",
                    "last_name": "Last name", 
                    "email": "Email address",
                    "phone": "Phone number"
                }
                
                missing_fields = []
                validation_errors = []
                
                # Check required fields
                for field, display_name in required_fields.items():
                    value = profile_data.get(field)
                    if not value or (isinstance(value, str) and not value.strip()):
                        missing_fields.append(field)
                        validation_errors.append(f"{display_name} is required")
                
                # Enhanced validation logic
                validation_errors.extend(self._validate_profile_data(profile_data))
                
                profile_complete = len(missing_fields) == 0 and len(validation_errors) == 0
                can_start_kyc = profile_complete and profile_data.get("kyc_status") in ["not_started", "rejected"]
                
                result = {
                    "profile_complete": profile_complete,
                    "missing_fields": missing_fields,
                    "errors": validation_errors,
                    "can_start_kyc": can_start_kyc,
                    "kyc_status": profile_data.get("kyc_status", "not_started"),
                    "last_updated": profile_data.get("updated_at"),
                    "profile_id": user_id
                }
                
                # Log the check for audit purposes
                if self.audit_service:
                    await self.audit_service.log_event(
                        user_id=user_id,
                        event_type="profile_completeness_check",
                        details={
                            "profile_complete": profile_complete,
                            "missing_field_count": len(missing_fields),
                            "validation_error_count": len(validation_errors)
                        }
                    )
                
                return result
                
            except Exception as e:
                retry_count += 1
                logger.error(f"Profile completeness check attempt {retry_count} failed for user {user_id}: {str(e)}")
                
                if retry_count >= max_retries:
                    return {
                        "profile_complete": False,
                        "missing_fields": ["system_error"],
                        "errors": [f"System error during profile check: {str(e)}"],
                        "can_start_kyc": False,
                        "kyc_status": "error"
                    }
                
                await asyncio.sleep(2 ** retry_count)

    async def save_onboarding_progress(self, user_id: str, step: int, data: dict) -> dict:
        """Enhanced progress saving with error handling"""
        try:
            progress = {"step": step, "data": data, "updated_at": datetime.utcnow().isoformat()}
            # Set a 24-hour expiry for the onboarding session data
            await self.redis.set(f"onboarding:{user_id}", json.dumps(progress), ex=86400)
            return {"status": "success", "message": "Progress saved"}
        except Exception as e:
            logger.error(f"Failed to save onboarding progress for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Could not save progress.")
    
    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        CRITICAL: Enhanced profile update with validation and error recovery
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Sanitize and validate input data
                sanitized_data = self._sanitize_profile_data(profile_data)
                validation_errors = self._validate_profile_data(sanitized_data)
                
                if validation_errors:
                    return {
                        "success": False,
                        "message": "Validation failed",
                        "errors": validation_errors,
                        "profile": None
                    }
                
                # Update profile using database service or direct Supabase
                if self.db_service:
                    updated_profile = await self.db_service.update_user_profile(user_id, sanitized_data)
                else:
                    # Direct Supabase update with proper field handling
                    update_data = {**sanitized_data, "updated_at": datetime.utcnow().isoformat()}
                    response = await self.supabase.table("user_profiles").update(update_data).eq("id", user_id).execute()
                    updated_profile = response.data[0] if response.data else None
                
                if not updated_profile:
                    raise ValueError("Profile update returned no data")
                
                # Log successful update
                if self.audit_service:
                    await self.audit_service.log_event(
                        user_id=user_id,
                        event_type="profile_updated",
                        details={
                            "updated_fields": list(sanitized_data.keys()),
                            "field_count": len(sanitized_data)
                        }
                    )
                
                return {
                    "success": True,
                    "message": "Profile updated successfully",
                    "profile": updated_profile,
                    "errors": []
                }
                
            except Exception as e:
                retry_count += 1
                logger.error(f"Profile update attempt {retry_count} failed for user {user_id}: {str(e)}")
                
                if retry_count >= max_retries:
                    return {
                        "success": False,
                        "message": f"Profile update failed after {max_retries} attempts",
                        "errors": [str(e)],
                        "profile": None
                    }
                
                await asyncio.sleep(2 ** retry_count)

    async def advance_step(self, user_id: str, current_step: int, step_data: dict) -> dict:
        """
        Enhanced step advancement with comprehensive error handling and validation
        """
        try:
            # --- Step 1: Basic Info ---
            if current_step == 1:
                # Validate and update basic profile info
                profile_update = await self.update_user_profile(user_id, step_data)
                
                if not profile_update.get("success"):
                    return {
                        "success": False,
                        "message": "Profile validation failed",
                        "errors": profile_update.get("errors", [])
                    }
                
                # Update KYC level to indicate profile completion
                await self.supabase.table("user_profiles").update({
                    "kyc_level": 1,
                    "kyc_status": "pending_documents"
                }).eq("id", user_id).execute()
                
                return {"next_step": 2, "message": "Profile updated. Please proceed to identity verification."}

            # --- Step 2: KYC Document Submission ---
            elif current_step == 2:
                # Verify profile completeness first
                completeness_check = await self.check_profile_completeness(user_id)
                
                if not completeness_check.get("can_start_kyc"):
                    return {
                        "success": False,
                        "message": "Profile prerequisites not met",
                        "errors": completeness_check.get("errors", [])
                    }
                
                user_profile_res = await self.supabase.table("user_profiles").select("email, country_code").eq("id", user_id).single().execute()
                if not user_profile_res.data:
                    raise HTTPException(status_code=404, detail="User not found for KYC.")
                
                kyc_session = await self.kyc_service.start_verification_session(
                    user_id, 
                    user_profile_res.data['email'], 
                    user_profile_res.data.get('country_code', 'US')
                )
                
                if not kyc_session.get('success', False):
                    return {
                        "success": False,
                        "message": "KYC initialization failed",
                        "errors": [kyc_session.get('error', 'Unknown KYC error')]
                    }
                
                return {"next_step": 3, "message": "KYC session initiated.", "kyc_flow_url": kyc_session.get('flow_url')}

            # --- Step 3: Wallet Provisioning ---
            elif current_step == 3:
                wallets = await self.wallet_service.provision_user_wallet(user_id)
                
                # Send notification if service available
                if self.notification_service:
                    await self.notification_service.send_wallet_created_notification(user_id)
                
                return {"next_step": 4, "message": "Wallet created successfully.", "wallets": wallets}
                
            # --- Step 4: Onboarding Complete ---
            elif current_step == 4:
                # Final onboarding completion
                await self.supabase.table("user_profiles").update({
                    "kyc_level": 2,  # Mark as fully onboarded
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", user_id).execute()
                
                # Clear Redis cache
                await self.redis.delete(f"onboarding:{user_id}")
                
                # Send welcome notification
                if self.notification_service:
                    await self.notification_service.send_welcome_notification(user_id)
                
                return {"onboarding_complete": True, "message": "Welcome to Seamount!"}

            else:
                raise HTTPException(status_code=400, detail="Invalid onboarding step.")
                
        except Exception as e:
            logger.error(f"Failed to advance onboarding step {current_step} for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="An error occurred while processing your request.")
    
    def _sanitize_profile_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced data sanitization"""
        sanitized = {}
        
        # String fields that need trimming
        string_fields = ["first_name", "last_name", "email", "phone", "country_code"]
        
        for field, value in data.items():
            if field in string_fields and isinstance(value, str):
                if field == "phone":
                    # Normalize phone number format
                    phone = ''.join(c for c in value if c.isdigit() or c in ['+', '-', '(', ')', ' '])
                    sanitized[field] = phone.strip()
                elif field == "email":
                    sanitized[field] = value.strip().lower()
                else:
                    sanitized[field] = value.strip()
            else:
                sanitized[field] = value
        
        return sanitized
    
    def _validate_profile_data(self, data: Dict[str, Any]) -> List[str]:
        """Enhanced profile data validation"""
        errors = []
        
        # Email validation
        if "email" in data and data["email"]:
            email = data["email"]
            if "@" not in email or "." not in email.split("@")[-1]:
                errors.append("Invalid email format")
            elif len(email) > 254:
                errors.append("Email address too long")
        
        # Name validation
        for name_field in ["first_name", "last_name"]:
            if name_field in data and data[name_field]:
                name = data[name_field]
                if len(name) < 2:
                    errors.append(f"{name_field.replace('_', ' ').title()} must be at least 2 characters")
                elif len(name) > 50:
                    errors.append(f"{name_field.replace('_', ' ').title()} too long (max 50 characters)")
                elif not name.replace(" ", "").replace("-", "").replace("'", "").isalpha():
                    errors.append(f"{name_field.replace('_', ' ').title()} contains invalid characters")
        
        # Phone validation
        if "phone" in data and data["phone"]:
            phone = data["phone"]
            digits_only = ''.join(c for c in phone if c.isdigit())
            if len(digits_only) < 10:
                errors.append("Phone number must be at least 10 digits")
            elif len(digits_only) > 15:
                errors.append("Phone number too long (max 15 digits)")
        
        return errors