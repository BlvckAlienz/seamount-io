# File Location: backend/services/kyc_providers/complycube.py
# COMPLETE FIX: Production-ready ComplyCube integration with CORS and token fixes

import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional
from fastapi import HTTPException
from pydantic import BaseModel
import uuid
from datetime import datetime, timedelta

from backend.config import get_settings

logger = logging.getLogger(__name__)

class ComplyCubeApplicant(BaseModel):
    id: str
    type: str
    email: Optional[str] = None

class ComplyCubeVerifier:
    """
    Production-ready ComplyCube integration with proper CORS and token handling
    """
    
    def __init__(self, api_key: str = None):
        settings = get_settings()
        self.api_key = api_key or settings.COMPLYCUBE_API_KEY
        self.base_url = "https://api.complycube.com/v1"
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.last_health_check = None
        self.health_status = "unknown"
        
        # Better initialization status tracking
        if not self.api_key:
            logger.warning("ComplyCube API key not configured - operating in simulation mode")
            self.simulation_mode = True
            self.initialization_status = "api_key_missing"
        else:
            self.simulation_mode = False
            self.initialization_status = "initialized"
            logger.info("ComplyCube service initialized successfully")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers with authentication"""
        return {
            "Authorization": f"Bearer {self.api_key.get_secret_value() if hasattr(self.api_key, 'get_secret_value') else self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make authenticated API request with comprehensive error handling
        """
        if self.simulation_mode:
            return self._simulate_response(endpoint, data)
        
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('/') else f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.request(method, url, headers=headers, json=data) as response:
                        response_data = await response.json()
                        
                        if response.status == 200 or response.status == 201:
                            logger.info(f"ComplyCube API success: {method} {endpoint}")
                            # Update health status on successful request
                            self.health_status = "healthy"
                            return response_data
                        elif response.status == 401:
                            # Authentication error - don't retry
                            self.health_status = "auth_failed"
                            logger.error(f"ComplyCube authentication failed: {response_data}")
                            raise HTTPException(
                                status_code=401,
                                detail="KYC service authentication failed"
                            )
                        elif response.status == 429:
                            # Rate limiting - exponential backoff
                            retry_count += 1
                            wait_time = 2 ** retry_count
                            logger.warning(f"Rate limited by ComplyCube, retrying in {wait_time}s (attempt {retry_count})")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            self.health_status = "api_error"
                            error_msg = response_data.get('message', 'Unknown error') if isinstance(response_data, dict) else str(response_data)
                            logger.error(f"ComplyCube API error: {response.status} - {error_msg}")
                            raise HTTPException(
                                status_code=500,
                                detail=f"ComplyCube API error: {error_msg}"
                            )
                            
            except asyncio.TimeoutError:
                retry_count += 1
                self.health_status = "timeout"
                if retry_count >= max_retries:
                    logger.error(f"ComplyCube API timeout after {max_retries} attempts")
                    raise HTTPException(status_code=408, detail="KYC service timeout")
                
                wait_time = 2 ** retry_count
                logger.warning(f"Request timeout, retrying in {wait_time}s (attempt {retry_count})")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                self.health_status = "connection_error"
                logger.error(f"ComplyCube API request failed: {str(e)}")
                raise HTTPException(status_code=500, detail="KYC service temporarily unavailable")
        
        self.health_status = "max_retries_exceeded"
        raise HTTPException(status_code=500, detail="Maximum retries exceeded")
    
    async def health_check(self) -> Dict[str, Any]:
        """Configuration validation without API calls"""
        try:
            self.last_health_check = datetime.utcnow().isoformat()
            
            if self.simulation_mode:
                self.health_status = "simulation_mode"
                return {"status": "healthy", "mode": "simulation"}
            
            # Validate API key format
            api_key = self.api_key.get_secret_value() if hasattr(self.api_key, 'get_secret_value') else self.api_key
            if not api_key or not api_key.startswith(('live_', 'test_')):
                self.health_status = "invalid_api_key"
                return {"status": "unhealthy", "error": "Invalid API key format"}
            
            self.health_status = "healthy"
            return {"status": "healthy", "provider": "complycube"}
        except Exception as e:
            self.health_status = "error"
            return {"status": "unhealthy", "error": str(e)}
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get detailed health status information for monitoring
        """
        return {
            "service": "ComplyCube KYC",
            "status": self.health_status,
            "simulation_mode": self.simulation_mode,
            "initialization_status": self.initialization_status,
            "last_health_check": self.last_health_check,
            "api_key_configured": bool(self.api_key),
            "base_url": self.base_url,
            "note": "Health check skips API calls to avoid unnecessary requests"
        }
    
    def _simulate_response(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Simulate ComplyCube responses for non-production environments"""
        
        if "account" in endpoint:
            return {
                "id": "simulated_account",
                "name": "Seamount Test Account",
                "status": "active"
            }
        elif "clients" in endpoint:
            return {
                "id": f"cc_client_{uuid.uuid4().hex[:8]}",
                "type": "person",
                "email": data.get("email") if data else None,
                "createdAt": datetime.utcnow().isoformat(),
                "status": "active"
            }
        elif "tokens" in endpoint:
            return {
                "token": f"cc_token_{uuid.uuid4().hex[:16]}",
                "expiresAt": (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }
        elif "checks" in endpoint:
            return {
                "id": f"cc_check_{uuid.uuid4().hex[:8]}",
                "status": "complete",
                "result": "clear",
                "createdAt": datetime.utcnow().isoformat()
            }
        
        return {"status": "simulated", "message": "Running in simulation mode"}
    
    async def create_client(self, user_id: str, email: str, country_code: str = "US") -> str:
        """
        Create ComplyCube client for user with enhanced error handling
        """
        try:
            client_data = {
                "type": "person",
                "email": email,
                "personDetails": {
                    "firstName": "User",  # Will be updated when available
                    "lastName": "Profile"
                }
            }
            
            if country_code:
                client_data["personDetails"]["nationality"] = country_code.upper()
            
            response = await self._make_request("POST", "clients", client_data)
            client_id = response.get("id")
            
            if not client_id:
                raise ValueError("Client ID not returned from ComplyCube API")
            
            logger.info(f"Created ComplyCube client {client_id} for user {user_id}")
            return client_id
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create ComplyCube client for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not create KYC profile")
    
    async def create_verification_session(self, client_id: str, referrer: str = "https://seamount.io/*") -> Dict[str, Any]:
        """
        Create hosted verification session with proper token handling and CORS configuration
        """
        try:
            token_response = await self._make_request("POST", "tokens", {
                "clientId": client_id,
                "referrer": referrer  # This fixes the CORS issue
            })
            
            token = token_response.get("token")
            if not token:
                raise ValueError("Verification token not returned from ComplyCube")
            
            # Create the session URL
            session_url = f"https://portal.complycube.com/verify?token={token}"
            
            return {
                "id": f"session_{client_id}",
                "url": session_url,
                "token": token,
                "client_id": client_id,
                "expires_at": token_response.get("expiresAt")
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create verification session for client {client_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not create verification session")

# Export service instance with proper initialization
complycube_service = ComplyCubeVerifier()