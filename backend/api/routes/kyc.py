import logging
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from typing import Dict, Any

from dependencies import get_supabase_client, get_current_user
from services.kyc_providers.complycube import complycube_service

logger = logging.getLogger(__name__)
router = APIRouter()

# CHANGE: Updated endpoint to match frontend expectation
@router.post("/kyc/start-verification", tags=["KYC"])
async def start_kyc_verification(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Securely initiates the KYC verification flow for the authenticated user.
    Returns a short-lived SDK token for the frontend.
    """
    user_id = current_user.get("id")
    logger.info(f"Initiating KYC verification process for user: {user_id}")

    if not complycube_service.is_available():
        logger.error("ComplyCube service is not available.")
        raise HTTPException(status_code=503, detail="The KYC verification service is temporarily unavailable.")

    try:
        applicant_id = current_user.get("complycube_applicant_id")

        if applicant_id:
            logger.info(f"User {user_id} already has a ComplyCube applicant ID: {applicant_id}")
        else:
            logger.info(f"No ComplyCube applicant ID found for user {user_id}. Creating a new applicant.")
            
            user_data_for_kyc = {
                'email': current_user.get('email'),
                'first_name': current_user.get('first_name', ''),
                'last_name': current_user.get('last_name', '')
            }
            
            applicant = complycube_service.create_applicant(user_data_for_kyc)
            applicant_id = applicant.id

            # Store the new applicant ID
            response = supabase.table('user_profiles') \
                .update({'complycube_applicant_id': applicant_id}) \
                .eq('id', user_id) \
                .execute()
            
            if not response.data:
                logger.error(f"Failed to store applicant_id {applicant_id} for user {user_id}")
                raise HTTPException(status_code=500, detail="Could not update user profile.")

        # Create frontend SDK token
        sdk_token = complycube_service.create_verification_token(applicant_id)

        return {"token": sdk_token, "applicantId": applicant_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Critical error during KYC initiation for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")