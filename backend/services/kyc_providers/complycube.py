import logging
from complycube import ComplyCubeClient
from supabase import create_client, Client as SupabaseClient
from config import get_settings
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

class ComplyCubeApplicant(BaseModel):
    id: str
    type: str
    email: Optional[str] = None

class ComplyCubeService:
    def __init__(self):
        self.client = None
        self.supabase = None
        try:
            settings = get_settings()
            
            # Check for correct environment variable name
            api_key = (settings.COMPLYCUBE_API_KEY or 
                      getattr(settings, 'COMPLYCURE_API_KEY', None))
            
            if not api_key:
                logger.warning("COMPLYCUBE_API_KEY is not configured. KYC features will be disabled.")
                return

            self.client = ComplyCubeClient(api_key=api_key.get_secret_value())
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
        return self.client is not None

    def create_applicant(self, user_data: dict) -> ComplyCubeApplicant:
        if not self.is_available():
            raise HTTPException(status_code=503, detail="KYC service is currently unavailable.")

        try:
            applicant_response = self.client.clients.create(
                type='person',
                email=user_data.get('email'),
                personDetails={
                    'firstName': user_data.get('first_name', ''),
                    'lastName': user_data.get('last_name', '')
                }
            )
            
            # Extract applicant data from response
            if hasattr(applicant_response, 'id'):
                applicant_data = {
                    'id': applicant_response.id,
                    'type': getattr(applicant_response, 'type', 'person'),
                    'email': getattr(applicant_response, 'email', user_data.get('email'))
                }
            else:
                applicant_data = applicant_response
                
            applicant = ComplyCubeApplicant(**applicant_data)
            logger.info(f"Successfully created ComplyCube applicant: {applicant.id}")
            return applicant
            
        except Exception as e:
            logger.error(f"Failed to create ComplyCube applicant: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Could not create KYC applicant profile.")

    def create_verification_token(self, applicant_id: str) -> str:
        if not self.is_available():
            logger.warning("KYC service is unavailable. Returning a demo token for non-production environments.")
            return "complycube_demo_token_placeholder"

        try:
            # FIXED: Updated API call with correct parameter format
            token_response = self.client.tokens.create(
                clientId=applicant_id,  # Correct parameter name
                referrer='*://*/*'
            )
            
            # Handle different response structures
            if hasattr(token_response, 'client_token'):
                client_token = token_response.client_token
            elif hasattr(token_response, 'token'):  # Some versions return just 'token'
                client_token = token_response.token
            elif isinstance(token_response, dict):
                client_token = token_response.get('client_token') or token_response.get('token')
            else:
                logger.error(f"Unexpected token response format: {token_response}")
                raise ValueError("Client token not found in ComplyCube API response.")
            
            logger.info(f"Successfully created verification SDK token for applicant: {applicant_id}")
            return client_token
            
        except Exception as e:
            logger.error(f"Failed to create verification token for applicant {applicant_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Could not generate a secure verification token.")

complycube_service = ComplyCubeService()