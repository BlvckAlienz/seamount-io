import logging
from complycube import ComplyCubeClient, Client
from supabase import create_client
from config import get_settings
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class ComplyCubeService:
    def __init__(self):
        try:
            settings = get_settings()
            # Check if API key is available
            if not settings.COMPLYCUBE_API_KEY:
                logger.warning("COMPLYCUBE_API_KEY not configured. KYC features will be disabled.")
                self.client = None
                return
                
            self.client = ComplyCubeClient(api_key=settings.COMPLYCUBE_API_KEY.get_secret_value())
            self.supabase = create_client(
                settings.VITE_SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY.get_secret_value()
            )
            logger.info("ComplyCube service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ComplyCube service: {e}")
            self.client = None
    
    def is_available(self):
        return self.client is not None
    
    def create_applicant(self, user_data: dict) -> Client:
        """Create a new applicant in ComplyCube"""
        if not self.is_available():
            raise HTTPException(status_code=503, detail="KYC service not available")
            
        try:
            applicant = self.client.clients.create(
                type='person',
                email=user_data['email'],
                personDetails={
                    'firstName': user_data.get('first_name', ''),
                    'lastName': user_data.get('last_name', '')
                }
            )
            logger.info(f"Created ComplyCube applicant: {applicant.id}")
            return applicant
        except Exception as e:
            logger.error(f"Failed to create ComplyCube applicant: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create KYC applicant: {str(e)}")
    
    def create_verification_token(self, applicant_id: str) -> str:
        """Create a verification token for frontend use"""
        if not self.is_available():
            # Return a demo token in development mode
            return "complycube_demo_token_placeholder"
            
        try:
            token = self.client.tokens.create(
                client_id=applicant_id,
                referrer='*://*/*'  # Allow from any origin
            )
            logger.info(f"Created verification token for applicant: {applicant_id}")
            return token.client_token
        except Exception as e:
            logger.error(f"Failed to create verification token: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create verification token: {str(e)}")
    
    def update_user_kyc_status(self, user_id: str, applicant_id: str, status: str):
        """Update user KYC status in Supabase"""
        try:
            # Update user profile with KYC status
            update_data = {
                'kyc_status': status,
                'kyc_level': 3 if status == 'approved' else 1,
                'complycube_applicant_id': applicant_id,
                'updated_at': 'now()'
            }
            
            result = self.supabase.table('user_profiles') \
                .update(update_data) \
                .eq('id', user_id) \
                .execute()
                
            logger.info(f"Updated KYC status for user {user_id} to {status}")
            return result
        except Exception as e:
            logger.error(f"Failed to update user KYC status: {e}")
            raise

# Global instance
complycube_service = ComplyCubeService()