from fastapi import APIRouter, Depends, HTTPException
from services.kyc_providers.complycube import complycube_service
from dependencies import get_current_user

router = APIRouter()

@router.post("/kyc/token")
async def create_kyc_token(current_user: dict = Depends(get_current_user)):
    try:
        # Create applicant in ComplyCube
        applicant = complycube_service.create_applicant(current_user)
        
        # Generate token for frontend
        token = complycube_service.create_verification_token(applicant.id)
        
        # Store applicant ID in user profile
        from supabase import create_client
        import os
        
        supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        
        supabase.table('user_profiles') \
            .update({'complycube_applicant_id': applicant.id}) \
            .eq('id', current_user['id']) \
            .execute()
        
        return {"token": token, "applicantId": applicant.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create KYC token: {str(e)}")