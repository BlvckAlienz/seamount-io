# backend/api/routes/session.py
from fastapi import APIRouter, Request, Depends
from typing import Dict, Any
import logging
from services.session_service import SessionService
from dependencies import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/session/initialize")
async def initialize_session(
    request: Request,
    supabase = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """Initialize a new session with IPINFO data"""
    try:
        session_service = SessionService(supabase)
        session_id = await session_service.create_session(request)
        
        return {"session_id": session_id, "success": True}
        
    except Exception as e:
        logger.error(f"Error initializing session: {str(e)}")
        return {"success": False, "error": "Failed to initialize session"}