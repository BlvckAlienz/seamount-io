# File Location: backend/services/kyc_providers/complycube.py
# Description: Specific implementation for the ComplyCube KYC provider.

import os
import logging
import httpx
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ComplyCubeVerifier:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ComplyCube API key is required.")
        self.api_key = api_key
        self.base_url = "https://api.complycube.com/v1"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    async def create_verification_session(self, user_id: str, email: str, country_code: str) -> Dict[str, Any]:
        """Create a verification flow for a user"""
        try:
            # Create client profile
            client_data = {
                "type": "person",
                "id": user_id, 
                "email": email,
                "countryCode": country_code
            }
            
            client_response = requests.post(
                f"{self.base_url}/clients",
                headers=self.headers,
                json=client_data
            )
            client_response.raise_for_status()
            client_id = client_response.json()["id"]
            
            # Create flow configuration
            flow_data = {
                "clientId": client_id,
                "language": "en",
                "redirectUrl": os.getenv("KYC_REDIRECT_URL", "https://seamount.io/verify/complete"),
                "steps": ["welcome", "identity", "selfie"]
            }
            
            flow_response = requests.post(
                f"{self.base_url}/flow-sessions",
                headers=self.headers,
                json=flow_data
            )
            flow_response.raise_for_status()
            flow_data = flow_response.json()
            
            return {
                "success": True,
                "client_id": client_id,
                "session_id": flow_data["id"],
                "flow_url": flow_data["url"]
            }
            
        except RequestException as e:
            error_message = str(e)
            if e.response:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("message", str(e))
                except:
                    pass
            
            logger.error(f"Failed to create verification session: {error_message}")
            return {"success": False, "error": error_message}
            
        except Exception as e:
            logger.error(f"Verification session creation failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_verification_status(self, check_id: str) -> Dict[str, Any]:
        """Get status of a verification check"""
        try:
            response = requests.get(
                f"{self.base_url}/checks/{check_id}",
                headers=self.headers
            )
            response.raise_for_status()
            check_data = response.json()
            
            # Normalize status
            status = check_data.get("status", "pending")
            result = check_data.get("outcome", "pending")
            
            return {
                "success": True,
                "status": status,
                "result": result,
                "details": check_data.get("details", {}),
                "completed": status == "completed"
            }
            
        except RequestException as e:
            logger.error(f"Failed to get verification status: {str(e)}")
            return {
                "success": False,
                "status": "error",
                "error": str(e)
            }
            
        except Exception as e:
            logger.error(f"Verification status check failed: {e}")
            return {
                "success": False,
                "status": "error",
                "error": str(e)
            }