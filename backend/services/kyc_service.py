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
            if current_status in ["approved", "verified", "in_progress"]:
                logger.warning(f"User {user_id} already has KYC status: {current_status}")
                return {
                    "success": False,
                    "error": f"KYC verification already {current_status}",
                    "kyc_status": current_status
                }
            
            # 3. FORCE REGFYL FOR ALL USERS - COMPLETELY REMOVE COMPLYCUBE FALLBACK
            if self.primary_provider == 'regfyl' and 'regfyl' in self.providers:
                # CRITICAL: Refresh profile from DB to get modal data
                fresh_profile = await self.db_service.get_user_profile_by_id(user_id)
                if not fresh_profile:
                    raise HTTPException(status_code=404, detail="Profile not found")
                return await self._start_regfyl_verification(user_id, fresh_profile, country_code)
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
        try:
            callback_url = f"{self.settings.API_BASE_URL}/webhooks/regfyl/screening"
            
            # Use passed profile (already fresh from line 154 fix)
            bvn = (user_profile.get('bvn') or '').strip()
            id_number = (user_profile.get('id_number') or '').strip()
            final_id = bvn or id_number
        
            user_data = {
                'customer_id': user_id,
                'full_name': f"{user_profile.get('first_name', '')} {user_profile.get('last_name', '')}".strip(),
                'year_of_birth': user_profile.get('date_of_birth', '')[:4] if user_profile.get('date_of_birth') else '2000',
                'gender': (user_profile.get('gender') or '').strip(),
                'country': country_code,
                'callback_url': callback_url
            }
        
            if final_id:
                user_data['id_type'] = user_profile.get('id_type', 'BVN')
                user_data['id_number'] = final_id
                logger.info(f"[Regfyl] ✅ ID attached: {user_data['id_type']} = {final_id[:3]}***")
            else:
                logger.warning(f"[Regfyl] ⚠️ NO ID for {user_id}")
        
            # Log sanitized payload
            safe_payload = {k: v for k, v in user_data.items() if k != 'id_number'}
            logger.info(f"[Regfyl] Payload: {json.dumps(safe_payload)}")
        
            regfyl_result = await self.screen_user_with_regfyl(user_id, user_data)
            await self.db_service.update_user_kyc_status(user_id, "pending", 1)
        
            if self.supabase:
                try:
                    self.supabase.table("kyc_sessions").upsert({
                        "user_id": user_id,
                        "applicant_id": f"regfyl_{user_id}",
                        "session_id": regfyl_result.get('screening_result', {}).get('screening', {}).get('reference'),
                        "verification_type": "regfyl_screening",
                        "status": "pending",
                        "response_data": regfyl_result,
                        "created_at": datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    logger.warning(f"Session save: {e}")
        
            return {
                "success": True,
                "provider": "regfyl",
                "session_id": regfyl_result.get('screening_result', {}).get('screening', {}).get('reference'),
                "applicantId": f"regfyl_{user_id}",
                "message": "Verification submitted successfully",
                "status": "pending",
                "next_step": "await_review"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Regfyl failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def health_check(self) -> Dict[str, Any]:
        """Health check for KYC service"""
        try:
            status = {
                "service": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "primary_provider": self.primary_provider,
                "provider_status": "unknown",
                "database_status": "unknown"
            }
            
            # Check provider
            if self.primary_provider and self.primary_provider in self.providers:
                provider = self.providers[self.primary_provider]
                if hasattr(provider, 'health_check'):
                    try:
                        provider_status = await provider.health_check()
                        status["provider_status"] = provider_status.get("status", "unknown")
                    except Exception as e:
                        status["provider_status"] = f"error: {str(e)}"
                        status["service"] = "degraded"
                else:
                    status["provider_status"] = "no_health_check"
            else:
                status["provider_status"] = "no_provider"
                status["service"] = "unhealthy"
            
            # Check database
            if self.supabase:
                try:
                    result = self.supabase.table("user_profiles").select("id", count="exact").limit(1).execute()
                    status["database_status"] = "healthy" if result else "unhealthy"
                except Exception as e:
                    status["database_status"] = f"error: {str(e)}"
                    status["service"] = "unhealthy"
            
            return status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "service": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }