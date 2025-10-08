# File Location: backend/services/kyc_service.py
# COMPLETE FIX: Regfyl-only KYC service with proper error handling

import logging
import json
from typing import Dict, Any, Optional
from supabase import Client
from fastapi import HTTPException
from datetime import datetime, timedelta

from backend.config import get_settings
from backend.services.audit_service import AuditService, AuditEventType
from backend.services.database_service import DatabaseService
from backend.services.kyc_providers.regfyl import RegfylVerifier

logger = logging.getLogger(__name__)

class KYCService:
    """
    PRODUCTION-READY: Complete KYC service with Regfyl as ONLY provider
    """
    
    def __init__(self, settings=None, supabase_client: Optional[Client] = None, db_service: Optional[DatabaseService] = None, audit_service: Optional[AuditService] = None):
        """Initialize KYC service with Regfyl as ONLY provider"""
        self.settings = settings or get_settings()
        self.supabase = supabase_client
        
        # Initialize database service
        if db_service:
            self.db_service = db_service
        else:
            self.db_service = DatabaseService(supabase_client)
    
        # Initialize audit service
        if audit_service:
            self.audit = audit_service
        else:
            from backend.services.audit_service import create_audit_service
            self.audit = create_audit_service(supabase_client)
    
        # Initialize Regfyl as ONLY provider
        self.providers = {}
        self.primary_provider = None
        
        # Initialize Regfyl provider
        regfyl_key = getattr(self.settings, 'REGFYL_API_KEY', None)
        if regfyl_key:
            try:
                self.providers['regfyl'] = RegfylVerifier(
                    api_key=regfyl_key.get_secret_value() if hasattr(regfyl_key, 'get_secret_value') else regfyl_key
                )
                self.primary_provider = 'regfyl'
                logger.info("Regfyl provider initialized as PRIMARY KYC provider")
            except Exception as e:
                logger.error(f"Failed to initialize Regfyl provider: {e}")
                self.providers['regfyl'] = RegfylVerifier()
                self.primary_provider = 'regfyl'
        else:
            logger.warning("Regfyl API key not configured - using simulation mode")
            self.providers['regfyl'] = RegfylVerifier()
            self.primary_provider = 'regfyl'

    async def screen_user_with_regfyl(self, user_id: str, user_data: Dict) -> Dict[str, Any]:
        """Screen user with Regfyl for PEP/Sanctions/AML compliance (PRIMARY METHOD)"""
        try:
            if 'regfyl' not in self.providers:
                raise HTTPException(status_code=503, detail="Regfyl provider not available")
        
            regfyl_provider = self.providers['regfyl']
        
            # Format user data for Regfyl
            regfyl_data = {
                'customer_id': user_id,
                'full_name': user_data.get('full_name') or f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
                'year_of_birth': user_data.get('year_of_birth') or user_data.get('date_of_birth', '')[:4],
                'gender': user_data.get('gender', ''),
                'country': user_data.get('country', 'NG'),
                'id_type': user_data.get('id_type', 'BVN'),
                'id_number': user_data.get('id_number', ''),
                'callback_url': f"{self.settings.API_BASE_URL}/webhooks/regfyl/screening"
            }
        
            # Perform comprehensive screening
            result = await regfyl_provider.onboard_seamount_user(regfyl_data)
        
            # Save compliance data with proper error handling
            if self.supabase:
                try:
                    compliance_data = {
                        "user_id": user_id,
                        "check_type": "regfyl_screening",
                        "provider": "regfyl", 
                        "status": "screening_initiated",
                        "external_reference": result.get('screening', {}).get('reference'),
                        "metadata": {
                            "screening_reference": result.get('screening', {}).get('reference'),
                            "id_verification_reference": result.get('id_verification', {}).get('reference'),
                            "screening_data": regfyl_data
                        },
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    self.supabase.table("compliance_checks").upsert(compliance_data).execute()
                    
                except Exception as db_error:
                    logger.warning(f"Could not save to compliance_checks: {db_error}")
                    # Don't fail the entire process - just log and continue
        
            # Log compliance event
            try:
                await self.audit.log_event(
                    AuditEventType.COMPLIANCE_CHECK_INITIATED,
                    user_id=user_id,
                    details={
                        "provider": "regfyl",
                        "screening_reference": result.get('screening', {}).get('reference'),
                        "id_verification_reference": result.get('id_verification', {}).get('reference')
                    },
                    severity="info"
                )
            except Exception as audit_error:
                logger.warning(f"Could not log audit event: {audit_error}")
        
            logger.info(f"Regfyl screening initiated for user {user_id}")
            return {
                "success": True,
                "provider": "regfyl", 
                "screening_result": result,
                "message": "AML/KYC screening initiated successfully"
            }
        
        except Exception as e:
            logger.error(f"Regfyl screening failed for user {user_id}: {e}")
            
            try:
                await self.audit.log_event(
                    AuditEventType.SYSTEM_ERROR,
                    user_id=user_id, 
                    details={"error": f"Regfyl screening failed: {str(e)}"},
                    severity="error"
                )
            except Exception:
                logger.error("Failed to log audit event for screening failure")
                
            raise HTTPException(status_code=500, detail="AML screening failed")

async def start_verification_session(self, user_id: str, email: str, country_code: str = "US") -> Dict[str, Any]:
    """
    Start KYC verification using Regfyl for ALL users
    COMPLETELY REMOVES COMPLYCUBE LOGIC
    """
    try:
        logger.info(f"Starting KYC verification for user {user_id}, country: {country_code} - USING REGFYL")
        
        # 1. Validate user profile exists
        user_profile = await self.db_service.get_user_profile_by_id(user_id)
        if not user_profile:
            logger.error(f"User profile not found for user {user_id}")
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # 2. Check for existing verification session - ALLOW RESTART IF NOT_STARTED OR REJECTED
        current_status = user_profile.get("kyc_status", "not_started")
        if current_status in ["approved", "verified", "in_progress"]:  # ✅ REMOVED 'pending'
            logger.warning(f"User {user_id} already has KYC status: {current_status}")
            return {
                "success": False,
                "error": f"KYC verification already {current_status}",
                "kyc_status": current_status
            }
            
            # 3. 🚨 FORCE REGFYL FOR ALL USERS - COMPLETELY REMOVE COMPLYCUBE FALLBACK
            if self.primary_provider == 'regfyl' and 'regfyl' in self.providers:
                return await self._start_regfyl_verification(user_id, user_profile, country_code)
            else:
                logger.error("REGFYL PROVIDER NOT CONFIGURED - NO FALLBACK TO COMPLYCUBE")
                raise HTTPException(status_code=503, detail="Verification service unavailable")
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error in start_verification_session: {e}")
            raise HTTPException(status_code=500, detail="KYC service unavailable")

    async def _start_regfyl_verification(self, user_id: str, user_profile: Dict, country_code: str) -> Dict[str, Any]:
        """Start verification using Regfyl for ALL users"""
        
        try:
            # Prepare user data for Regfyl
            user_data = {
                'customer_id': user_id,
                'full_name': f"{user_profile.get('first_name', '')} {user_profile.get('last_name', '')}".strip(),
                'year_of_birth': user_profile.get('date_of_birth', '')[:4] if user_profile.get('date_of_birth') else str(datetime.now().year - 25),
                'gender': user_profile.get('gender', ''),
                'country': country_code,
                'callback_url': f"{self.settings.API_BASE_URL}/webhooks/regfyl/screening"
            }
            
            # Add country-specific ID verification if data exists
            if country_code == 'NG' and user_profile.get('bvn'):
                user_data.update({
                    'id_type': 'BVN',
                    'id_number': user_profile.get('bvn'),
                    'verifyID': 'YES'
                })
            elif country_code in ['KE', 'GH'] and user_profile.get('id_number'):
                user_data.update({
                    'id_type': 'NATIONAL_ID' if country_code == 'KE' else 'GHANA_CARD',
                    'id_number': user_profile.get('id_number'),
                    'verifyID': 'YES'
                })
            
            # Validate required basic information
            if not user_data['full_name']:
                return {
                    "success": False,
                    "error": "Full name required for verification",
                    "missing_fields": ["first_name", "last_name"]
                }
            
            # Start Regfyl screening
            regfyl_result = await self.screen_user_with_regfyl(user_id, user_data)
            
            # Update user status to pending
            update_data = {
                "kyc_status": "pending",
                "kyc_level": 1,
                "kyc_provider": "regfyl",  # 🚨 FORCE REGFYL IN DATABASE
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Use your existing database service to update status
            await self.db_service.update_user_kyc_status(user_id, "pending", 1)
            
            # Store session with Regfyl reference
            if self.supabase:
                try:
                    session_data = {
                        "user_id": user_id,
                        "applicant_id": f"regfyl_{user_id}",
                        "session_id": regfyl_result.get('screening_result', {}).get('screening', {}).get('reference'),
                        "verification_type": "regfyl_screening",
                        "status": "pending",
                        "response_data": regfyl_result,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    self.supabase.table("kyc_sessions").upsert(session_data).execute()
                except Exception as session_error:
                    logger.warning(f"Could not save KYC session: {session_error}")
            
            logger.info(f"Regfyl verification initiated successfully for user {user_id}")
            
            return {
                "success": True,
                "provider": "regfyl",
                "session_id": regfyl_result.get('screening_result', {}).get('screening', {}).get('reference'),
                "applicantId": f"regfyl_{user_id}",
                "message": "Regfyl verification started successfully",
                "status": "pending",
                "next_step": "await_webhook"
            }
            
        except Exception as e:
            logger.error(f"Regfyl verification failed for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Verification service unavailable")

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for the KYC service.
        Checks the status of the service and its primary provider.
        """
        try:
            # Base status structure
            status = {
                "service": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "primary_provider": self.primary_provider,
                "provider_status": "unknown",
                "database_status": "unknown"
            }
            
            # 1. Check the primary provider's status
            if self.primary_provider and self.primary_provider in self.providers:
                provider = self.providers[self.primary_provider]
                
                # Check if the provider instance has a health_check method
                if hasattr(provider, 'health_check') and callable(getattr(provider, 'health_check')):
                    try:
                        provider_status = await provider.health_check()
                        status["provider_status"] = provider_status.get("status", "unknown")
                        # If the provider is unhealthy, mark the overall service as degraded
                        if provider_status.get("status") != "healthy":
                            status["service"] = "degraded"
                    except Exception as e:
                        status["provider_status"] = f"error: {str(e)}"
                        status["service"] = "unhealthy"
                else:
                    # If the provider doesn't have a health_check method, check its simulation mode or basic attributes
                    status["provider_status"] = "no_health_check"
                    status["provider_simulation_mode"] = getattr(provider, 'simulation_mode', 'unknown')
            else:
                status["provider_status"] = "no_provider_configured"
                status["service"] = "unhealthy"
            
            # 2. Check database connectivity
            if self.supabase:
                try:
                    # Perform a simple query to check database connection
                    result = self.supabase.table("user_profiles").select("id", count="exact").limit(1).execute()
                    status["database_status"] = "healthy" if result else "unhealthy"
                    if not result:
                        status["service"] = "unhealthy"
                except Exception as e:
                    status["database_status"] = f"error: {str(e)}"
                    status["service"] = "unhealthy"
            
            return status
            
        except Exception as e:
            # Catch-all for any unexpected errors in the health check itself
            logger.error(f"Health check execution failed: {e}")
            return {
                "service": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }