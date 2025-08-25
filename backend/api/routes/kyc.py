import logging
from fastapi import APIRouter, Depends, HTTPException
from services.kyc_providers.complycube import complycube_service
from auth_dependency import get_current_user
from supabase import create_client
from config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/kyc/token")
async def create_kyc_token(current_user: dict = Depends(get_current_user)):
    try:
        logger.info(f"Creating KYC token for user: {current_user['id']}")
        
        # Create applicant in ComplyCube
        applicant = complycube_service.create_applicant(current_user)
        
        # Generate token for frontend
        token = complycube_service.create_verification_token(applicant.id)
        
        # Store applicant ID in user profile
        settings = get_settings()
        supabase = create_client(
            settings.VITE_SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY.get_secret_value()
        )
        
        supabase.table('user_profiles') \
            .update({'complycube_applicant_id': applicant.id}) \
            .eq('id', current_user['id']) \
            .execute()
        
        logger.info(f"KYC token created successfully for user: {current_user['id']}")
        return {"token": token, "applicantId": applicant.id}
    except Exception as e:
        logger.error(f"Failed to create KYC token for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create KYC token: {str(e)}")