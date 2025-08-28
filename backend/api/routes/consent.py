# backend/api/routes/consent.py (replace entire file)
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Dict
from datetime import datetime
from supabase import Client
from auth_dependency import get_current_user
from dependencies import get_supabase_client
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

class ConsentUpdateRequest(BaseModel):
    session_id: str
    preferences: Dict[str, bool]

@router.post("/consent/update")
async def update_consent(
    request: Request,
    consent_request: ConsentUpdateRequest,
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_user)
):
    try:
        logger.info(f"Updating consent for user: {current_user.id}")
        
        # Prepare consent data
        consent_data = {
            "id": str(uuid.uuid4()),
            "user_id": str(current_user.id),
            "session_id": consent_request.session_id,
            "preferences": consent_request.preferences,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Upsert consent record
        result = supabase.table("user_consents").upsert(consent_data).execute()
        
        if not result.data:
            logger.error("Failed to update consent preferences")
            raise HTTPException(status_code=500, detail="Failed to save consent preferences")
        
        return {"success": True, "message": "Consent preferences updated"}
        
    except Exception as e:
        logger.error(f"Error updating consent: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process consent update")