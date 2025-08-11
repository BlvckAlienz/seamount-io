import logging
import json
from supabase import Client
from upstash_redis import Redis
from fastapi import HTTPException

# --- Core Dependencies ---
from config import Settings
from .wallet_service import WalletService
from .kyc_service import KYCService

logger = logging.getLogger(__name__)

class OnboardingService:
    """
    Orchestrates the multi-step user onboarding journey, managing state via Redis
    and coordinating other services like Wallet and KYC.
    """
    def __init__(self, settings: Settings, supabase_client: Client, wallet_service: WalletService, kyc_service: KYCService):
        """
        Initializes the service with pre-configured dependencies.
        """
        self.settings = settings
        self.supabase = supabase_client
        self.wallet_service = wallet_service
        self.kyc_service = kyc_service
        
        if not settings.UPSTASH_REDIS_REST_URL or not settings.UPSTASH_REDIS_REST_TOKEN:
            raise ValueError("Upstash Redis environment variables are not set for OnboardingService.")
        
        self.redis = Redis(
            url=settings.UPSTASH_REDIS_REST_URL, 
            token=settings.UPSTASH_REDIS_REST_TOKEN.get_secret_value()
        )
        logger.info("OnboardingService initialized successfully.")

    async def get_onboarding_status(self, user_id: str) -> dict:
        """
        Retrieves the user's current onboarding step from Redis. If not in Redis,
        it infers the step from the user's profile in the database.
        """
        try:
            progress_json = await self.redis.get(f"onboarding:{user_id}")
            if progress_json:
                return json.loads(progress_json)
            
            profile_res = await self.supabase.table("user_profiles").select("kyc_level, algorand_address").eq("id", user_id).single().execute()
            
            if not profile_res.data:
                raise HTTPException(status_code=404, detail="User profile not found.")
            
            user = profile_res.data
            kyc_level = user.get("kyc_level", 0)
            has_wallet = user.get("algorand_address") is not None
            
            # Infer the current step based on the user's profile state
            current_step = 1 # Welcome
            if kyc_level >= 1: current_step = 2 # Identity
            if kyc_level >= 2: current_step = 3 # Wallet
            if has_wallet: current_step = 4 # Security/Complete
            
            return {"step": current_step, "data": {}}
            
        except Exception as e:
            logger.error(f"Failed to get onboarding status for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Could not retrieve onboarding status.")

    async def save_onboarding_progress(self, user_id: str, step: int, data: dict) -> dict:
        """Saves onboarding progress to Redis for resumable sessions."""
        try:
            progress = {"step": step, "data": data}
            # Set a 24-hour expiry for the onboarding session data
            await self.redis.set(f"onboarding:{user_id}", json.dumps(progress), ex=86400)
            return {"status": "success", "message": "Progress saved"}
        except Exception as e:
            logger.error(f"Failed to save onboarding progress for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Could not save progress.")

    async def advance_step(self, user_id: str, current_step: int, step_data: dict) -> dict:
        """
        Processes the data for the current step and advances the user to the next.
        This is the core logic of the "confidence-building machine".
        """
        try:
            # --- Step 1: Basic Info ---
            if current_step == 1:
                await self.supabase.table("user_profiles").update({
                    "first_name": step_data.get("first_name"),
                    "last_name": step_data.get("last_name"),
                    "country_code": step_data.get("country_code"),
                    "kyc_level": 1,
                    "kyc_status": "pending_documents"
                }).eq("id", user_id).execute()
                return {"next_step": 2, "message": "Profile updated. Please proceed to identity verification."}

            # --- Step 2: KYC Document Submission ---
            elif current_step == 2:
                user_profile_res = await self.supabase.table("user_profiles").select("email, country_code").eq("id", user_id).single().execute()
                if not user_profile_res.data:
                    raise HTTPException(status_code=404, detail="User not found for KYC.")
                
                kyc_session = await self.kyc_service.start_verification_session(
                    user_id, 
                    user_profile_res.data['email'], 
                    user_profile_res.data['country_code']
                )
                return {"next_step": 3, "message": "KYC session initiated.", "kyc_flow_url": kyc_session.get('flow_url')}

            # --- Step 3: Wallet Provisioning ---
            elif current_step == 3:
                wallets = await self.wallet_service.provision_user_wallet(user_id)
                return {"next_step": 4, "message": "Wallet created successfully.", "wallets": wallets}
                
            # --- Step 4: Onboarding Complete ---
            elif current_step == 4:
                # This step is now just for final confirmation. The kyc_status will be updated by a webhook.
                await self.supabase.table("user_profiles").update({
                    "kyc_level": 2 # Mark as fully onboarded pending verification
                }).eq("id", user_id).execute()
                
                await self.redis.delete(f"onboarding:{user_id}")
                return {"onboarding_complete": True, "message": "Welcome to Seamount!"}

            else:
                raise HTTPException(status_code=400, detail="Invalid onboarding step.")
        except Exception as e:
            logger.error(f"Failed to advance onboarding step for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An error occurred while processing your request.")