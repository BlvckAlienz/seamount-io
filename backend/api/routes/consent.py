# backend/api/routes/consent.py
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime
from supabase import Client
from dependencies import get_supabase_client
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

class ConsentUpdateRequest(BaseModel):
    session_id: str
    preferences: Dict[str, bool]
    user_id: Optional[str] = None  # Optional for unauthenticated users

@router.post("/consent/update")
async def update_consent(
    request: Request,
    consent_request: ConsentUpdateRequest,
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Extract user ID from authorization header if present
        user_id = consent_request.user_id
        auth_header = request.headers.get("authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # Try to extract user ID from token without requiring full authentication
                token = auth_header[7:]
                # Simple decode without verification (for user ID extraction only)
                import jwt
                decoded = jwt.decode(token, options={"verify_signature": False})
                user_id = decoded.get("sub", user_id)
                logger.info(f"Extracted user ID from token: {user_id}")
            except Exception as token_error:
                logger.warning(f"Could not extract user ID from token: {token_error}")
        
        logger.info(f"Updating consent for session: {consent_request.session_id}, user: {user_id}")
        
        # Prepare consent data
        consent_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
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