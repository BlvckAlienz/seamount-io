# backend/services/ipinfo_service.py
import aiohttp
import logging
from typing import Dict, Any, Optional
from config import get_settings

logger = logging.getLogger(__name__)

class IPInfoService:
    """Service for fetching IP geolocation and device information"""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://ipinfo.io"
        self.token = self.settings.IPINFO_TOKEN.get_secret_value() if self.settings.IPINFO_TOKEN else None
    
    async def get_ip_info(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get geolocation and other information for an IP address"""
        if not self.token:
            logger.warning("IPINFO_TOKEN not configured, skipping IP info lookup")
            return None
            
        try:
            url = f"{self.base_url}/{ip_address}/json?token={self.token}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "ip": data.get("ip"),
                            "city": data.get("city"),
                            "region": data.get("region"),
                            "country": data.get("country"),
                            "loc": data.get("loc"),  # Latitude, longitude
                            "org": data.get("org"),  # Organization/ISP
                            "timezone": data.get("timezone")
                        }
                    else:
                        logger.warning(f"IPInfo API returned status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching IP info: {str(e)}")
            return None
    
    async def get_device_info(self, user_agent: str) -> Dict[str, str]:
        """Extract device information from user agent"""
        # Simple device detection - in production you might want a proper library
        device_info = {
            "device_type": "desktop",
            "browser": "unknown",
            "platform": "unknown"
        }
        
        if "mobile" in user_agent.lower():
            device_info["device_type"] = "mobile"
        elif "tablet" in user_agent.lower():
            device_info["device_type"] = "tablet"
            
        if "chrome" in user_agent.lower():
            device_info["browser"] = "chrome"
        elif "firefox" in user_agent.lower():
            device_info["browser"] = "firefox"
        elif "safari" in user_agent.lower():
            device_info["browser"] = "safari"
            
        if "windows" in user_agent.lower():
            device_info["platform"] = "windows"
        elif "mac" in user_agent.lower():
            device_info["platform"] = "macos"
        elif "linux" in user_agent.lower():
            device_info["platform"] = "linux"
        elif "android" in user_agent.lower():
            device_info["platform"] = "android"
        elif "iphone" in user_agent.lower() or "ipad" in user_agent.lower():
            device_info["platform"] = "ios"
            
        return device_info