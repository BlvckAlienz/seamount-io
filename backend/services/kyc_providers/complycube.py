import os
from complycube import ComplyCubeClient
from supabase import create_client
import os

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class ComplyCubeService:
    def __init__(self):
        self.client = ComplyCubeClient(api_key=os.getenv('COMPLYCUBE_API_KEY'))
    
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
            return applicant
        except Exception as e:
            print(f"Failed to create ComplyCube applicant: {e}")
            raise
    
    def create_verification_token(self, applicant_id):
        """Create a verification token for frontend use"""
        try:
            token = self.client.tokens.create(applicant_id, '*://*/*')
            return token
        except Exception as e:
            print(f"Failed to create verification token: {e}")
            raise
    
    def update_user_kyc_status(self, applicant_id, status):
        """Update user KYC status in Supabase"""
        try:
            # Find user by applicant_id
            user_profile = supabase.table('user_profiles') \
                .select('*') \
                .eq('complycube_applicant_id', applicant_id) \
                .execute()
            
            if user_profile.data:
                # Update KYC status
                supabase.table('user_profiles') \
                    .update({
                        'kyc_status': status,
                        'kyc_level': 3 if status == 'approved' else 0
                    }) \
                    .eq('complycube_applicant_id', applicant_id) \
                    .execute()
        except Exception as e:
            print(f"Failed to update user KYC status: {e}")
            raise

complycube_service = ComplyCubeService()