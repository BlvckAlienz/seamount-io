import logging
from complycube import ComplyCubeClient
from supabase import create_client
from config import get_settings

logger = logging.getLogger(__name__)

class ComplyCubeService:
    def __init__(self):
        settings = get_settings()
        self.client = ComplyCubeClient(api_key=settings.COMPLYCUBE_API_KEY.get_secret_value())
        self.supabase = create_client(
            settings.VITE_SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY.get_secret_value()
        )
        logger.info("ComplyCube service initialized")
    
    def create_applicant(self, user_data):
        """Create a new applicant in ComplyCube"""
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
            raise
    
    def create_verification_token(self, applicant_id):
        """Create a verification token for frontend use"""
        try:
            token = self.client.tokens.create(applicant_id, '*://*/*')
            logger.info(f"Created verification token for applicant: {applicant_id}")
            return token
        except Exception as e:
            logger.error(f"Failed to create verification token: {e}")
            raise
    
    def update_user_kyc_status(self, applicant_id, status):
        """Update user KYC status in Supabase"""
        try:
            # Find user by applicant_id
            user_profile = self.supabase.table('user_profiles') \
                .select('*') \
                .eq('complycube_applicant_id', applicant_id) \
                .execute()
            
            if user_profile.data:
                # Update KYC status
                self.supabase.table('user_profiles') \
                    .update({
                        'kyc_status': status,
                        'kyc_level': 3 if status == 'approved' else 0
                    }) \
                    .eq('complycube_applicant_id', applicant_id) \
                    .execute()
                logger.info(f"Updated KYC status for applicant {applicant_id} to {status}")
        except Exception as e:
            logger.error(f"Failed to update user KYC status: {e}")
            raise

complycube_service = ComplyCubeService()