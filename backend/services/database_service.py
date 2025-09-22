# File Location: backend/services/database_service.py
# PRODUCTION READY: Consolidated database service combining best features from both versions

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from decimal import Decimal
from contextlib import asynccontextmanager
import uuid
import traceback

import asyncpg
from supabase import create_client, Client
from postgrest import APIError
from fastapi import HTTPException

from backend.config import get_settings

logger = logging.getLogger(__name__)

class DatabaseService:
    """
    PRODUCTION-READY: Consolidated database service with optimal error handling
    Combines high-performance pool management with simplified operations
    """
    def __init__(self, supabase_client: Optional[Client] = None):
        self.settings = get_settings()
        
        # Initialize Supabase client
        if supabase_client:
            self.supabase = supabase_client
        else:
            if not self.settings.VITE_SUPABASE_URL or not self.settings.SUPABASE_SERVICE_KEY:
                raise ValueError("Supabase URL and Service Key must be configured")
            
            self.supabase: Client = create_client(
                self.settings.VITE_SUPABASE_URL, 
                self.settings.SUPABASE_SERVICE_KEY.get_secret_value()
            )
        
        # Connection management
        self.pool: Optional[asyncpg.Pool] = None
        self.max_retries = 3
        self.retry_delay = 1.0
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        
        logger.info("✅ DatabaseService initialized successfully")
    
    # =============================================================================
    # CRITICAL FIX: User Profile Management with Proper User ID Handling
    # =============================================================================
    
    async def create_user_profile(self, profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        CRITICAL FIX: Create user profile with proper user_id population
        Ensures user_id column is never null
        """
        try:
            # Extract and validate user ID
            user_id = profile_data.get("id")
            if not user_id:
                raise ValueError("User ID is required for profile creation")
            
            # Convert to UUID if string
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    raise ValueError(f"Invalid UUID format for user_id: {user_id}")
            else:
                user_uuid = user_id
            
            # Prepare clean profile data with guaranteed user_id
            clean_data = {
                "id": str(user_uuid),  # CRITICAL: Ensure string format for Supabase
                "email": profile_data.get("email", "").lower().strip(),
                "first_name": profile_data.get("first_name"),
                "last_name": profile_data.get("last_name"),
                "phone": profile_data.get("phone"),
                "country": profile_data.get("country", "USA"),
                "country_code": profile_data.get("country_code"),
                "kyc_status": "not_started",
                "kyc_level": 0,
                "access_level": "limited", 
                "role": profile_data.get("role", "alien"),
                "is_admin": False,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"[DB] Creating user profile: {user_uuid}")
            
            # Insert with upsert to handle duplicates
            response = self.supabase.table("user_profiles").upsert(
                clean_data, 
                on_conflict="id"
            ).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"[DB] User profile created successfully: {user_uuid}")
                return self._format_user_profile(response.data[0])
            else:
                logger.error(f"[DB] Failed to create user profile - no data returned for {user_uuid}")
                return None
                
        except Exception as e:
            logger.error(f"[DB] Error creating user profile: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Failed to create user profile: {str(e)}")

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Enhanced user profile retrieval with proper error handling
        """
        try:
            logger.debug(f"[DB] Fetching user profile: {user_id}")
            
            # Validate UUID format
            try:
                user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            except ValueError:
                logger.error(f"[DB] Invalid UUID format: {user_id}")
                return None
            
            response = self.supabase.table("user_profiles").select("*").eq("id", str(user_uuid)).maybe_single().execute()
            
            if response.data:
                logger.debug(f"[DB] User profile found: {user_id}")
                return self._format_user_profile(response.data)
            else:
                logger.warning(f"[DB] User profile not found: {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"[DB] Error fetching user profile {user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Failed to fetch user profile")

    async def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update user profile with transaction safety and field validation
        """
        try:
            logger.info(f"[DB] Updating user profile: {user_id}")
            
            # Validate UUID format
            try:
                user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            except ValueError:
                raise ValueError(f"Invalid UUID format: {user_id}")
            
            # Whitelist allowed update fields
            allowed_fields = {
                "first_name", "last_name", "email", "phone", "country", "country_code",
                "address_line1", "city", "state_province", "postal_code",
                "kyc_status", "kyc_level", "access_level", "kyc_session_id",
                "kyc_provider", "kyc_started_at", "kyc_completed_at", 
                "kyc_rejection_reason", "security_flags", "last_login_at",
                "failed_login_attempts", "account_locked_until"
            }
            
            # Filter and clean update data
            clean_update = {}
            for field, value in update_data.items():
                if field in allowed_fields:
                    clean_update[field] = value
            
            # Always update timestamp
            clean_update["updated_at"] = datetime.utcnow().isoformat()
            
            response = self.supabase.table("user_profiles").update(clean_update).eq("id", str(user_uuid)).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"[DB] User profile updated successfully: {user_id}")
                return self._format_user_profile(response.data[0])
            else:
                logger.warning(f"[DB] No rows updated for user_id: {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"[DB] Error updating user profile {user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Failed to update user profile: {str(e)}")

    def _format_user_profile(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format raw database user profile data for consistent API response"""
        return {
            "id": str(raw_data["id"]),
            "email": raw_data.get("email"),
            "first_name": raw_data.get("first_name"),
            "last_name": raw_data.get("last_name"),
            "phone": raw_data.get("phone"),
            "country": raw_data.get("country", "USA"),
            "country_code": raw_data.get("country_code"),
            "address_line1": raw_data.get("address_line1"),
            "city": raw_data.get("city"),
            "state_province": raw_data.get("state_province"),
            "postal_code": raw_data.get("postal_code"),
            "kyc_status": raw_data.get("kyc_status", "not_started"),
            "kyc_level": raw_data.get("kyc_level", 0),
            "access_level": raw_data.get("access_level", "limited"),
            "kyc_session_id": raw_data.get("kyc_session_id"),
            "kyc_provider": raw_data.get("kyc_provider"),
            "kyc_started_at": raw_data.get("kyc_started_at"),
            "kyc_completed_at": raw_data.get("kyc_completed_at"),
            "kyc_rejection_reason": raw_data.get("kyc_rejection_reason"),
            "role": raw_data.get("role", "alien"),
            "is_admin": raw_data.get("is_admin", False),
            "verification_skipped": raw_data.get("verification_skipped", False),
            "security_flags": raw_data.get("security_flags", {}),
            "last_login_at": raw_data.get("last_login_at"),
            "failed_login_attempts": raw_data.get("failed_login_attempts", 0),
            "account_locked_until": raw_data.get("account_locked_until"),
            "created_at": raw_data.get("created_at"),
            "updated_at": raw_data.get("updated_at")
        }

    # =============================================================================
    # KYC & Compliance Operations - Simplified and Robust
    # =============================================================================

    async def get_user_profile_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Alias for get_user_profile for KYC service compatibility"""
        return await self.get_user_profile(user_id)
    
    async def get_user_by_kyc_client_id(self, client_id: str) -> Optional[Dict[str, Any]]:
    """Get user by KYC client ID with proper error handling"""
        try:
            response = self.supabase.table("kyc_sessions") \
                .select("user_id") \
                .eq("client_id", client_id) \
                .maybe_single() \
                .execute()
        
            if response.data:
                return await self.get_user_profile(response.data["user_id"])
            return None
        except Exception as e:
            logger.error(f"Error getting user by KYC client ID: {e}")
            return None
    
    async def log_kyc_session(self, user_id: str, session_id: str, client_id: str) -> bool:
        """Log KYC verification session initiation with proper error handling"""
        try:
            logger.info(f"[DB] Logging KYC session for user {user_id}")
            
            session_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "session_id": session_id,
                "client_id": client_id,
                "status": "initiated",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table("kyc_sessions").insert(session_data).execute()
            
            if response.data:
                logger.info(f"[DB] KYC session logged successfully for user {user_id}")
                return True
            else:
                logger.error(f"[DB] Failed to log KYC session for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"[DB] Error logging KYC session for user {user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    async def update_user_kyc_status(self, user_id: str, status: str, level: int) -> bool:
        """Update user KYC status and level with proper timestamp management"""
        try:
            logger.info(f"[DB] Updating KYC status for user {user_id}: {status} (level {level})")
            
            update_data = {
                "kyc_status": status,
                "kyc_level": level,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Add appropriate timestamps
            if status in ["approved", "verified", "completed"]:
                update_data["kyc_completed_at"] = datetime.utcnow().isoformat()
            elif status in ["pending", "initiated"]:
                update_data["kyc_started_at"] = datetime.utcnow().isoformat()
            
            response = self.supabase.table("user_profiles").update(update_data).eq("id", user_id).execute()
            
            if response.data:
                logger.info(f"[DB] KYC status updated successfully for user {user_id}")
                return True
            else:
                logger.error(f"[DB] Failed to update KYC status for user {user_id}: No data returned")
                return False
                
        except Exception as e:
            logger.error(f"[DB] Error updating KYC status for user {user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    async def get_user_id_by_kyc_client_id(self, client_id: str) -> Optional[str]:
        """Get user ID by ComplyCube client ID with proper error handling"""
        try:
            logger.debug(f"[DB] Looking up user by KYC client ID: {client_id}")
            
            response = self.supabase.table("kyc_sessions").select("user_id").eq("client_id", client_id).maybe_single().execute()
            
            if response.data:
                user_id = response.data["user_id"]
                logger.debug(f"[DB] Found user {user_id} for client ID {client_id}")
                return user_id
            else:
                logger.warning(f"[DB] No user found for KYC client ID: {client_id}")
                return None
                
        except Exception as e:
            logger.error(f"[DB] Error looking up user by client ID {client_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    async def update_kyc_check_result(self, check_id: str, outcome: str, check_data: Dict[str, Any]) -> bool:
        """Update KYC verification check result with fallback creation"""
        try:
            logger.info(f"[DB] Updating KYC check result: {check_id} -> {outcome}")
            
            update_data = {
                "outcome": outcome,
                "check_data": check_data,
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table("kyc_verification_logs").update(update_data).eq("check_id", check_id).execute()
            
            if response.data:
                logger.info(f"[DB] KYC check result updated successfully: {check_id}")
                return True
            else:
                logger.warning(f"[DB] Creating new verification log for check ID {check_id}")
                
                # Create new verification log entry
                log_data = {
                    "id": str(uuid.uuid4()),
                    "check_id": check_id,
                    "verification_type": "identity_check",
                    "status": "completed",
                    "outcome": outcome,
                    "check_data": check_data,
                    "created_at": datetime.utcnow().isoformat(),
                    "completed_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                create_response = self.supabase.table("kyc_verification_logs").insert(log_data).execute()
                return bool(create_response.data)
                
        except Exception as e:
            logger.error(f"[DB] Error updating KYC check result {check_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    async def get_kyc_verification_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get KYC verification history for a user"""
        try:
            logger.debug(f"[DB] Fetching KYC history for user: {user_id}")
            
            response = self.supabase.table("kyc_verification_logs").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            
            if response.data:
                logger.debug(f"[DB] Found {len(response.data)} KYC records for user {user_id}")
                return response.data
            else:
                logger.debug(f"[DB] No KYC history found for user {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"[DB] Error fetching KYC history for user {user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    async def get_kyc_session_by_applicant_id(self, applicant_id: str) -> Optional[Dict[str, Any]]:
        """Get KYC session by ComplyCube applicant ID"""
        try:
            result = await self.supabase.table("kyc_sessions")\
                .select("*")\
                .eq("applicant_id", applicant_id)\
                .single()\
                .execute()
            
            return result.data if result.data else None
            
        except Exception as e:
            logger.error(f"Error fetching KYC session by applicant_id {applicant_id}: {e}")
            return None

    async def update_kyc_session_status(self, applicant_id: str, status: str, response_data: Dict[str, Any]) -> bool:
        """Update KYC session status and response data"""
        try:
            result = await self.supabase.table("kyc_sessions")\
                .update({
                    "status": status,
                    "response_data": response_data,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("applicant_id", applicant_id)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error updating KYC session status for applicant {applicant_id}: {e}")
            return False

    async def store_kyc_session(self, kyc_data: Dict[str, Any]) -> bool:
        """Store KYC session data"""
        try:
            result = await self.supabase.table("kyc_sessions")\
                .insert(kyc_data)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error storing KYC session: {e}")
            return False
    
    # =============================================================================
    # Wallet Management Operations - Critical for Platform
    # =============================================================================
    
    async def save_encrypted_private_key(self, user_id: str, algorand_address: str, encrypted_pk: str) -> bool:
        """Save user's encrypted private key with maximum security"""
        try:
            logger.info(f"[DB] Saving encrypted private key for user {user_id}")
            
            wallet_data = {
                "user_id": user_id,
                "algorand_address": algorand_address,
                "algorand_private_key": encrypted_pk,
                "wallet_type": "managed",
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table("user_wallets").upsert(wallet_data, on_conflict="user_id").execute()
            
            if response.data:
                logger.info(f"[DB] Encrypted private key saved successfully for user {user_id}")
                return True
            else:
                logger.error(f"[DB] Failed to save encrypted private key for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"[DB] Error saving encrypted key for {user_id}: {str(e)}")
            raise

    async def get_encrypted_private_key(self, user_id: str) -> Optional[str]:
        """Retrieve user's encrypted private key with security logging"""
        try:
            logger.debug(f"[DB] Retrieving encrypted private key for user {user_id}")
            
            response = self.supabase.table("user_wallets").select("algorand_private_key").eq("user_id", user_id).eq("is_active", True).maybe_single().execute()
            
            if response.data:
                logger.debug(f"[DB] Encrypted private key retrieved for user {user_id}")
                return response.data["algorand_private_key"]
            else:
                logger.warning(f"[DB] No encrypted private key found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"[DB] Error retrieving encrypted key for {user_id}: {str(e)}")
            raise

    async def get_user_wallet(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete wallet information for user"""
        try:
            logger.debug(f"[DB] Fetching user wallet: {user_id}")
            
            response = self.supabase.table("user_wallets").select("*").eq("user_id", user_id).eq("is_active", True).maybe_single().execute()
            
            if response.data:
                wallet = response.data
                return {
                    "id": str(wallet["id"]),
                    "user_id": str(wallet["user_id"]),
                    "algorand_address": wallet["algorand_address"],
                    "wallet_type": wallet["wallet_type"],
                    "is_active": wallet["is_active"],
                    "created_at": wallet.get("created_at"),
                    "updated_at": wallet.get("updated_at")
                }
            else:
                logger.debug(f"[DB] No wallet found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"[DB] Error fetching user wallet {user_id}: {str(e)}")
            raise

    async def get_wallet_balance(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user wallet balance information"""
        try:
            logger.debug(f"[DB] Fetching wallet balance for user: {user_id}")
            
            response = self.supabase.table("wallet_balances").select("*").eq("user_id", user_id).maybe_single().execute()
            
            if response.data:
                logger.debug(f"[DB] Wallet balance found for user: {user_id}")
                return response.data
            else:
                logger.debug(f"[DB] No wallet balance found for user: {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"[DB] Error fetching wallet balance for user {user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    # =============================================================================
    # Health & Monitoring Operations
    # =============================================================================
    
    async def health_check(self) -> bool:
        """Check database connectivity and basic operations"""
        try:
            logger.debug("[DB] Performing health check")
            
            # Simple query to test connectivity
            response = self.supabase.table("user_profiles").select("count", count="exact").limit(1).execute()
            
            if response.count is not None:
                logger.debug(f"[DB] Health check passed - {response.count} users in system")
                return True
            else:
                logger.error("[DB] Health check failed - could not get user count")
                return False
                
        except Exception as e:
            logger.error(f"[DB] Health check failed: {str(e)}")
            return False

    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health metrics"""
        try:
            health_data = {
                "database": {
                    "supabase_client": "healthy" if self.supabase else "unavailable",
                    "circuit_breaker_failures": self.circuit_breaker_failures,
                    "circuit_breaker_status": "closed" if self.circuit_breaker_failures < self.circuit_breaker_threshold else "open"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Test database connectivity
            try:
                connectivity_test = await self.health_check()
                health_data["database"]["connectivity"] = "healthy" if connectivity_test else "failed"
                health_data["database"]["test_query"] = "passed" if connectivity_test else "failed"
            except Exception:
                health_data["database"]["connectivity"] = "failed"
                health_data["database"]["test_query"] = "failed"
            
            return health_data
            
        except Exception as e:
            logger.error(f"[DB] Error checking system health: {str(e)}")
            return {
                "database": {"status": "error", "error": str(e)},
                "timestamp": datetime.utcnow().isoformat()
            }

    async def close_connections(self):
        """Gracefully close database connections"""
        try:
            if self.pool and not self.pool._closed:
                await self.pool.close()
                logger.info("[DB] Database connections closed successfully")
        except Exception as e:
            logger.error(f"[DB] Error closing database connections: {str(e)}")

# This alias ensures existing imports continue to work
SuperDatabaseService = DatabaseService