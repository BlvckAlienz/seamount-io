import logging
from complycube import ComplyCubeClient
from supabase import create_client, Client as SupabaseClient
from config import get_settings
from fastapi import HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Define a Pydantic model for the Applicant object for type safety and clarity.
class ComplyCubeApplicant(BaseModel):
    id: str
    type: str
    email: str | None = None

class ComplyCubeService:
    def __init__(self):
        """Initializes the ComplyCube service and its Supabase dependency."""
        self.client = None
        self.supabase = None
        try:
            settings = get_settings()
            
            # CORRECTED LOGIC: Check the SecretStr object itself, not its value.
            if not settings.COMPLYCUBE_API_KEY:
                logger.warning("COMPLYCUBE_API_KEY is not configured. KYC features will be disabled.")
                return

            # Now we can safely call .get_secret_value() because the type is correct.
            self.client = ComplyCubeClient(api_key=settings.COMPLYCUBE_API_KEY.get_secret_value())
            self.supabase = create_client(
                settings.VITE_SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY.get_secret_value()
            )
            logger.info("ComplyCube service initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize ComplyCube service: {e}", exc_info=True)
            self.client = None
            self.supabase = None

    def is_available(self) -> bool:
        """Checks if the ComplyCube client was successfully initialized."""
        return self.client is not None

    def create_applicant(self, user_data: dict) -> ComplyCubeApplicant:
        """Creates a new applicant in ComplyCube and returns a validated data model."""
        if not self.is_available():
            raise HTTPException(status_code=503, detail="KYC service is currently unavailable.")

        try:
            applicant_dict = self.client.clients.create(
                type='person',
                email=user_data.get('email'),
                personDetails={
                    'firstName': user_data.get('first_name', ''),
                    'lastName': user_data.get('last_name', '')
                }
            )
            applicant = ComplyCubeApplicant(**applicant_dict)
            logger.info(f"Successfully created ComplyCube applicant: {applicant.id}")
            return applicant
        except Exception as e:
            logger.error(f"Failed to create ComplyCube applicant: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Could not create KYC applicant profile.")

    def create_verification_token(self, applicant_id: str) -> str:
        """Creates a short-lived SDK token for the frontend to initialize the ComplyCube UI."""
        if not self.is_available():
            logger.warning("KYC service is unavailable. Returning a demo token for non-production environments.")
            return "sdk_demo_token"

        try:
            token_response = self.client.tokens.create(
                client_id=applicant_id,
                referrer='*://*/*' # Use a stricter referrer in production, e.g., 'https://seamount.io/*'
            )
            
            client_token = token_response.get('clientToken')
            if not client_token:
                logger.error(f"ComplyCube API response did not contain a 'clientToken' for applicant {applicant_id}.")
                raise ValueError("clientToken not found in ComplyCube API response.")
            
            logger.info(f"Successfully created verification SDK token for applicant: {applicant_id}")
            return client_token
        except Exception as e:
            logger.error(f"Failed to create verification token for applicant {applicant_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Could not generate a secure verification token.")

# Create a single, globally accessible instance of the service.
complycube_service = ComplyCubeService()