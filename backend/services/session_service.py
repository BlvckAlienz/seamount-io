# backend/services/session_service.py
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from supabase import Client
from .ipinfo_service import IPInfoService
from config import get_settings

logger = logging.getLogger(__name__)

class SessionService:
    """Service for managing user sessions with IPINFO integration"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.ipinfo_service = IPInfoService()
    
    async def create_session(self, request, user_id: Optional[str] = None) -> str:
        """Create a new user session with IPINFO data"""
        session_id = str(uuid.uuid4())
        
        # Get client IP address
        if request.headers.get("x-forwarded-for"):
            ip_address = request.headers.get("x-forwarded-for").split(",")[0]
        else:
            ip_address = request.client.host if request.client else "unknown"
        
        # Get user agent
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Fetch IP info and device info concurrently
        ip_info_task = self.ipinfo_service.get_ip_info(ip_address)
        device_info_task = self.ipinfo_service.get_device_info(user_agent)
        
        ip_info = await ip_info_task
        device_info = await device_info_task
        
        # Prepare session data
        session_data = {
            "id": session_id,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_type": device_info["device_type"],
            "browser": device_info["browser"],
            "platform": device_info["platform"],
            "city": ip_info.get("city") if ip_info else None,
            "region": ip_info.get("region") if ip_info else None,
            "country": ip_info.get("country") if ip_info else None,
            "latitude": ip_info.get("loc", "").split(",")[0] if ip_info and ip_info.get("loc") else None,
            "longitude": ip_info.get("loc", "").split(",")[1] if ip_info and ip_info.get("loc") else None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Store session in database
        try:
            result = self.supabase.table("user_sessions").insert(session_data).execute()
            if not result.data:
                logger.error("Failed to create user session")
                return session_id  # Still return ID even if DB insert fails
                
            logger.info(f"Created session {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return session_id  # Return ID even on error
    
    async def update_session_user(self, session_id: str, user_id: str) -> bool:
        """Update session with user ID after authentication"""
        try:
            result = self.supabase.table("user_sessions").update({
                "user_id": user_id,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", session_id).execute()
            
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating session user: {str(e)}")
            return False