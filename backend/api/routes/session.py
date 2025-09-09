# File: backend/api/routes/session.py
import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from supabase import Client
from uuid import uuid4
from datetime import datetime
import aiohttp
from typing import Optional

from backend.dependencies import get_supabase_client, get_settings
from backend.config import Settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/initialize")
async def initialize_session(
    request: Request,
    user_agent: Optional[str] = None,
    supabase: Client = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings)
):
    """Initialize user session with IP information"""
    ip_address = request.client.host if request.client else "unknown"
    
    session_data = {
        "id": str(uuid4()),
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": datetime.utcnow().isoformat()
    }

    # IPInfo integration
    if settings.IPINFO_TOKEN and ip_address != "unknown":
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2.0)) as http_session:
                async with http_session.get(
                    f"https://ipinfo.io/{ip_address}?token={settings.IPINFO_TOKEN.get_secret_value()}"
                ) as response:
                    if response.status == 200:
                        ip_data = await response.json()
                        session_data.update({
                            "country": ip_data.get("country", "US"),
                            "city": ip_data.get("city", "Unknown"),
                            "region": ip_data.get("region", "Unknown"),
                            "org": ip_data.get("org", "Unknown ISP"),
                            "timezone": ip_data.get("timezone", "UTC"),
                            "is_vpn": ip_data.get("privacy", {}).get("vpn", False)
                        })
        except Exception as e:
            logger.warning(f"IPInfo enrichment failed: {e}")
    
    try:
        insert_res = supabase.from_("user_sessions").insert(session_data).execute()
        return {"session_id": session_data["id"]}
    except Exception as e:
        logger.error(f"Session initialization error: {e}")
        return {"session_id": session_data["id"]}