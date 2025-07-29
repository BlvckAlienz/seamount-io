# File Location: backend/services/onboarding_service.py
# Description: Orchestrates the multi-step user onboarding journey.

import os
import logging
import json
from supabase import Client
from upstash_redis import Redis
from fastapi import HTTPException

from services.wallet_service import WalletService
# from services.kyc_service import KYCService # To be integrated next

logger = logging.getLogger(__name__)

class OnboardingService:
    def __init__(self, supabase_client: Client, wallet_service: WalletService):
        self.supabase = supabase_client
        self.wallet_service = wallet_service
        # self.kyc_service = kyc_service
        
        redis_url = os.environ.get("UPSTASH_REDIS_REST_URL")
        redis_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        if not redis_url or not redis_token:
            raise ValueError("Upstash Redis environment variables are not set.")
        self.redis = Redis(url=redis_url, token=redis_token)

    async def get_onboarding_status(self, user_id: str) -> dict:
        """Retrieves the user's current onboarding step and data from Redis."""
        try:
            progress_json = await self.redis.get(f"onboarding:{user_id}")
            if progress_json:
                return json.loads(progress_json)
            
            # If no progress in Redis, check their profile for completion status
            profile_res = await self.supabase.table("user_profiles").select("kyc_level").eq("id", user_id).single().execute()
            kyc_level = profile_res.data.get("kyc_level", 0)
            
            # Define logic for what step corresponds to what kyc_level
            current_step = 1
            if kyc_level == 1: current_step = 2 # Basic info done
            if kyc_level == 2: current_step = 3 # KYC docs submitted
            
            return {"step": current_step, "data": {}}
            
        except Exception as e:
            logger.error(f"Failed to get onboarding progress for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Could not retrieve onboarding status.")

    async def save_onboarding_progress(self, user_id: str, step: int, data: dict) -> dict:
        """Saves onboarding progress to Redis for resumable sessions."""
        try:
            progress = {"step": step, "data": data}
            # Set a 24-hour expiry for the onboarding session data
            await self.redis.set(f"onboarding:{user_id}", json.dumps(progress), ex=86400)
            return {"status": "success", "message": "Progress saved"}
        except Exception as e:
            logger.error(f"Failed to save onboarding progress for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Could not save progress.")

    async def advance_step(self, user_id: str, current_step: int, step_data: dict) -> dict:
        """
        Processes the data for the current step and advances the user to the next.
        This is the core logic of the "confidence-building machine".
        """
        # --- Step 1: Basic Info ---
        if current_step == 1:
            # Update user_profiles table with name, country, etc. from step_data
            await self.supabase.table("user_profiles").update({
                "first_name": step_data.get("first_name"),
                "last_name": step_data.get("last_name"),
                "country_code": step_data.get("country_code"),
                "kyc_level": 1, # Advance trust level
                "kyc_status": "pending_documents"
            }).eq("id", user_id).execute()
            return {"next_step": 2, "message": "Profile updated. Please proceed to identity verification."}

        # --- Step 2: KYC Document Submission ---
        elif current_step == 2:
            # This is where you would call your kyc_service to start the ComplyCube session
            # kyc_session = await self.kyc_service.start_verification(user_id, step_data)
            await self.supabase.table("user_profiles").update({
                "kyc_status": "pending_verification"
            }).eq("id", user_id).execute()
            return {"next_step": 3, "message": "KYC documents submitted for verification."}

        # --- Step 3: Wallet Provisioning ---
        elif current_step == 3:
            wallets = await self.wallet_service.provision_user_wallet(user_id)
            return {"next_step": 4, "message": "Wallet created successfully.", "wallets": wallets}
            
        # --- Step 4: Onboarding Complete ---
        elif current_step == 4:
            await self.supabase.table("user_profiles").update({
                "kyc_status": "approved", # Assume KYC is approved for now
                "kyc_level": 2
            }).eq("id", user_id).execute()
            
            # Clean up the temporary onboarding data from Redis
            await self.redis.delete(f"onboarding:{user_id}")
            return {"onboarding_complete": True, "message": "Welcome to Seamount!"}

        else:
            raise HTTPException(status_code=400, detail="Invalid onboarding step.")