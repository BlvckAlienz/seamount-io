from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict
from datetime import datetime
from supabase import Client
from auth_dependency import get_current_user, get_supabase_client
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

class ConsentUpdateRequest(BaseModel):
    session_id: str
    preferences: Dict[str, bool]

@router.post("/consent/update")
async def update_consent(
    request: ConsentUpdateRequest,
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_user)
):
    try:
        logger.info(f"Updating consent for user: {current_user.get('id')}")
        
        # Prepare consent data
        consent_data = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.get('id'),
            "session_id": request.session_id,
            "preferences": request.preferences,
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