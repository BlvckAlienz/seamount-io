"""
Seamount.io Cross-Border Payment Platform
KYC Verification Module

This module handles user verification and KYC processes, 
focusing on African regulatory requirements.
"""

import os
import logging
import asyncio
import base64
import time
import hashlib
import json
from typing import Dict, Any, Optional, Union
from datetime import datetime
import aiohttp
from fastapi import HTTPException, UploadFile
from supabase import create_client, Client
import requests
from requests.exceptions import RequestException

# Configure logging
logger = logging.getLogger(__name__)

class ComplyCubeVerifier:
    """ComplyCube KYC verification implementation"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.complycube.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
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
    
    async def verify_documents_manually(
        self, 
        user_id: str, 
        id_document: Union[str, bytes],
        selfie: Union[str, bytes],
        document_type: str = "passport"
    ) -> Dict[str, Any]:
        """Manually submit documents for verification"""
        try:
            # Create client profile if not exists
            client_data = {"type": "person", "id": user_id}
            client_response = requests.post(
                f"{self.base_url}/clients",
                headers=self.headers,
                json=client_data
            )
            client_response.raise_for_status()
            client_id = client_response.json()["id"]
            
            # Convert paths to base64 if strings are provided
            if isinstance(id_document, str) and os.path.isfile(id_document):
                with open(id_document, "rb") as f:
                    id_document = base64.b64encode(f.read()).decode("utf-8")
            
            if isinstance(selfie, str) and os.path.isfile(selfie):
                with open(selfie, "rb") as f:
                    selfie = base64.b64encode(f.read()).decode("utf-8")
            
            # Create document check
            check_data = {
                "clientId": client_id,
                "type": "document_check",
                "document": {
                    "type": document_type,
                    "file": id_document if isinstance(id_document, str) else base64.b64encode(id_document).decode("utf-8")
                },
                "selfie": {
                    "file": selfie if isinstance(selfie, str) else base64.b64encode(selfie).decode("utf-8")
                }
            }
            
            check_response = requests.post(
                f"{self.base_url}/checks",
                headers=self.headers,
                json=check_data
            )
            check_response.raise_for_status()
            check_id = check_response.json()["id"]
            
            return {
                "success": True,
                "check_id": check_id,
                "client_id": client_id,
                "status": "pending"
            }
            
        except RequestException as e:
            error_message = str(e)
            if e.response:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("message", str(e))
                except:
                    pass
            
            logger.error(f"Document verification failed: {error_message}")
            return {"success": False, "error": error_message}
            
        except Exception as e:
            logger.error(f"Document verification failed: {e}")
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

class UserVerificationManager:
    """User verification manager for the Seamount.io platform"""
    
    def __init__(self):
        # Initialize Supabase client
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase = None
        
        if self.supabase_url and self.supabase_key:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # Initialize ComplyCube client if API key is provided
        complycube_api_key = os.getenv("COMPLYCUBE_API_KEY")
        self.complycube = None
        
        if complycube_api_key:
            self.complycube = ComplyCubeVerifier(
                api_key=complycube_api_key,
                base_url=os.getenv("COMPLYCUBE_URL", "https://api.complycube.com/v1")
            )
            logger.info("ComplyCube KYC integration initialized")
        else:
            logger.warning("ComplyCube KYC integration not configured - limited to basic KYC only")
    
    async def start_verification(self, user_id: str, email: str, country_code: str) -> Dict[str, Any]:
        """Start KYC verification process for a user"""
        if not self.complycube:
            return {"success": False, "error": "KYC provider not configured"}
        
        # Create verification session
        session = await self.complycube.create_verification_session(user_id, email, country_code)
        
        # Store session information
        if session.get("success") and self.supabase:
            try:
                # Update user profile with session info
                self.supabase.table("verification_sessions").insert({
                    "user_id": user_id,
                    "session_id": session["session_id"],
                    "client_id": session["client_id"],
                    "status": "initiated",
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
            except Exception as e:
                logger.error(f"Failed to store verification session: {e}")
        
        return session
    
    async def process_documents(
        self,
        user_id: str,
        id_document: UploadFile,
        selfie: UploadFile,
        document_type: str = "passport"
    ) -> Dict[str, Any]:
        """Process user's KYC documents"""
        if not self.complycube:
            return {"success": False, "error": "KYC provider not configured"}
        
        try:
            # Read file contents
            id_document_bytes = await id_document.read()
            selfie_bytes = await selfie.read()
            
            # Submit for verification
            result = await self.complycube.verify_documents_manually(
                user_id,
                id_document_bytes,
                selfie_bytes,
                document_type
            )
            
            # Store verification attempt
            if self.supabase:
                self.supabase.table("verification_attempts").insert({
                    "user_id": user_id,
                    "check_id": result.get("check_id"),
                    "status": result.get("status", "pending"),
                    "document_type": document_type,
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
            
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_verification_status(self, user_id: str) -> Dict[str, Any]:
        """Check verification status for a user"""
        try:
            if not self.supabase:
                return {"success": False, "error": "Database not configured"}
            
            # Get user profile
            profile = self.supabase.table("user_profiles").select(
                "kyc_verified, kyc_level, kyc_last_verified, kyc_details"
            ).eq("id", user_id).execute()
            
            if not profile.data:
                return {"success": False, "error": "User profile not found"}
            
            profile_data = profile.data[0]
            
            # Check for pending verifications
            if not profile_data.get("kyc_verified", False):
                pending = self.supabase.table("verification_attempts").select(
                    "check_id, status, created_at"
                ).eq("user_id", user_id).eq("status", "pending").order("created_at", {"ascending": False}).limit(1).execute()
                
                if pending.data:
                    pending_check = pending.data[0]
                    
                    # Check status if ComplyCube is configured
                    if self.complycube and pending_check.get("check_id"):
                        status = await self.complycube.get_verification_status(pending_check["check_id"])
                        
                        if status.get("completed"):
                            # Update user profile
                            verified = status.get("result") == "clear"
                            new_level = 2 if verified else 0
                            
                            self.supabase.table("user_profiles").update({
                                "kyc_verified": verified,
                                "kyc_level": new_level,
                                "kyc_last_verified": datetime.utcnow().isoformat(),
                                "kyc_details": json.dumps(status.get("details", {}))
                            }).eq("id", user_id).execute()
                            
                            # Update verification attempt
                            self.supabase.table("verification_attempts").update({
                                "status": status.get("status", "completed"),
                                "result": status.get("result")
                            }).eq("check_id", pending_check["check_id"]).execute()
                            
                            return {
                                "success": True,
                                "verified": verified,
                                "level": new_level,
                                "status": status.get("status"),
                                "updated": True
                            }
                        
                        return {
                            "success": True,
                            "verified": profile_data.get("kyc_verified", False),
                            "level": profile_data.get("kyc_level", 0),
                            "status": status.get("status", "pending"),
                            "updated": False
                        }
            
            # Return current status if no pending checks or checks completed
            return {
                "success": True,
                "verified": profile_data.get("kyc_verified", False),
                "level": profile_data.get("kyc_level", 0),
                "last_verified": profile_data.get("kyc_last_verified"),
                "status": "completed",
                "updated": False
            }
            
        except Exception as e:
            logger.error(f"Verification status check failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def upgrade_kyc_level(
        self,
        user_id: str,
        new_level: int,
        admin_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """Manually upgrade KYC level for a user (admin only)"""
        try:
            if not self.supabase:
                return {"success": False, "error": "Database not configured"}
            
            # Get admin info
            admin = self.supabase.table("user_profiles").select("is_admin").eq("id", admin_id).execute()
            
            if not admin.data or not admin.data[0].get("is_admin", False):
                return {"success": False, "error": "Unauthorized - admin access required"}
            
            # Get current KYC level
            user = self.supabase.table("user_profiles").select("kyc_level, kyc_verified").eq("id", user_id).execute()
            
            if not user.data:
                return {"success": False, "error": "User not found"}
            
            current_level = user.data[0].get("kyc_level", 0)
            
            # Update profile
            self.supabase.table("user_profiles").update({
                "kyc_level": new_level,
                "kyc_verified": new_level > 0,
                "kyc_last_verified": datetime.utcnow().isoformat(),
                "kyc_details": f"Manually upgraded by admin: {reason}"
            }).eq("id", user_id).execute()
            
            # Add to KYC history
            self.supabase.table("kyc_verification_history").insert({
                "user_id": user_id,
                "verification_type": "manual",
                "previous_level": current_level,
                "new_level": new_level,
                "verified": new_level > 0,
                "details": f"Manually upgraded by admin {admin_id}: {reason}"
            }).execute()
            
            return {
                "success": True,
                "user_id": user_id,
                "previous_level": current_level,
                "new_level": new_level,
                "verified": new_level > 0
            }
            
        except Exception as e:
            logger.error(f"KYC upgrade failed: {e}")
            return {"success": False, "error": str(e)}

# Initialize user verification manager
user_verification_manager = UserVerificationManager()

async def verify_document_endpoint(
    user_id: str, 
    id_document: UploadFile, 
    selfie: UploadFile, 
    document_type: str
) -> Dict[str, Any]:
    """Endpoint handler for document verification"""
    try:
        result = await user_verification_manager.process_documents(
            user_id, 
            id_document, 
            selfie, 
            document_type
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400, 
                detail=result.get("error", "Document verification failed")
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document verification endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during verification: {str(e)}"
        )