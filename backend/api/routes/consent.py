import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any
from uuid import UUID
from supabase import Client

# Correctly import dependencies from the central module
from dependencies import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter()

class ConsentUpdatePayload(BaseModel):
    session_id: UUID = Field(..., description="The anonymous session ID generated on page load.")
    preferences: Dict[str, bool] = Field(..., description="The user's cookie consent choices.")

@router.post("/consent/update", status_code=200)
async def update_consent_preferences(
    payload: ConsentUpdatePayload,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Updates the consent preferences for a given anonymous user session.
    This is called by the frontend's cookie consent banner.
    """
    logger.info(f"Received consent update for session_id: {payload.session_id}")

    try:
        # Prepare the data for the JSONB column in the user_sessions table
        update_data = {
            "consent_preferences": payload.preferences
        }

        # Perform an UPDATE on the user_sessions table where the ID matches.
        result = supabase.table("user_sessions") \
            .update(update_data) \
            .eq("id", str(payload.session_id)) \
            .execute()

        # Check if the update was successful. If result.data is empty, no row was found.
        if not result.data:
            logger.warning(f"Attempted to update consent for a non-existent session_id: {payload.session_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Session with ID {payload.session_id} not found."
            )

        logger.info(f"Successfully updated consent for session_id: {payload.session_id}")
        return {"success": True, "message": "Consent preferences have been updated."}

    except HTTPException:
        # Re-raise known HTTP exceptions to be handled by FastAPI
        raise
    except Exception as e:
        logger.error(f"Error updating consent for session {payload.session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="A server error occurred while updating consent preferences."
        )