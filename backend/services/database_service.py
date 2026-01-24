# File Location: backend/services/database_service.py
# 🚀 DEFINITIVE PRODUCTION READY VERSION

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
    """Production-ready database service with wallet creation support"""
    
    def __init__(self, supabase_client: Optional[Client] = None):
        self.settings = get_settings()
        
        if supabase_client:
            self.supabase = supabase_client
        else:
            if not self.settings.SUPABASE_URL or not self.settings.SUPABASE_SERVICE_KEY:
                raise ValueError("Supabase URL and Service Key must be configured")
            
            self.supabase: Client = create_client(
                self.settings.SUPABASE_URL,
                self.settings.SUPABASE_SERVICE_KEY.get_secret_value()
            )
        
        self.pool: Optional[asyncpg.Pool] = None
        self.max_retries = 3
        self.retry_delay = 1.0
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        
        logger.info("✅ DatabaseService initialized successfully")

    # 🆕 NEW METHODS FOR WALLET CREATION SERVICE
    async def get_user_wallet_response(self, user_id: str) -> Any:
        """
        Get user wallet in Supabase response format for wallet_creation_service
        Returns response with .data attribute for compatibility
        """
        try:
            logger.debug(f"[DB] Fetching user wallet response: {user_id}")
            
            # Use asyncio.to_thread to keep consistent pattern
            response = await asyncio.to_thread(
                lambda: self.supabase.table("user_wallets")
                .select("algorand_address")
                .eq("user_id", user_id)
                .execute()
            )
            
            return response
            
        except Exception as e:
            logger.error(f"[DB] Error fetching user wallet response {user_id}: {str(e)}")
            # Return empty response structure for error handling
            class EmptyResponse:
                def __init__(self):
                    self.data = []
            return EmptyResponse()

    async def get_multi_chain_addresses_response(self, user_id: str) -> Any:
        """
        Get multi-chain addresses in Supabase response format for wallet_creation_service
        Returns response with .data attribute for compatibility
        """
        try:
            logger.debug(f"[DB] Fetching multi-chain addresses response: {user_id}")
            
            # Use asyncio.to_thread to keep consistent pattern
            response = await asyncio.to_thread(
                lambda: self.supabase.table("multi_chain_addresses")
                .select("blockchain, address")
                .eq("user_id", user_id)
                .execute()
            )
            
            return response
            
        except Exception as e:
            logger.error(f"[DB] Error fetching multi-chain addresses response {user_id}: {str(e)}")
            # Return empty response structure for error handling
            class EmptyResponse:
                def __init__(self):
                    self.data = []
            return EmptyResponse()

    async def get_wallet_creation_status(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get wallet creation status records for a user
        """
        try:
            logger.debug(f"[DB] Fetching wallet creation status: {user_id}")
            
            response = await asyncio.to_thread(
                lambda: self.supabase.table("wallet_creation_status")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"[DB] Error fetching wallet creation status {user_id}: {str(e)}")
            return []

    async def upsert_wallet_creation_status(self, status_data: Dict[str, Any]) -> bool:
        """
        Upsert wallet creation status record
        """
        try:
            logger.debug(f"[DB] Upserting wallet creation status: {status_data.get('user_id')}")
            
            response = await asyncio.to_thread(
                lambda: self.supabase.table("wallet_creation_status")
                .upsert(status_data)
                .execute()
            )
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"[DB] Error upserting wallet creation status: {str(e)}")
            return False

    async def insert_wallet_creation_status(self, status_data: Dict[str, Any]) -> bool:
        """
        Insert new wallet creation status record
        """
        try:
            logger.debug(f"[DB] Inserting wallet creation status: {status_data.get('user_id')}")
            
            response = await asyncio.to_thread(
                lambda: self.supabase.table("wallet_creation_status")
                .insert(status_data)
                .execute()
            )
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"[DB] Error inserting wallet creation status: {str(e)}")
            return False

    async def update_wallet_creation_status(self, user_id: str, chain: str, update_data: Dict[str, Any]) -> bool:
        """
        Update wallet creation status for specific user and chain
        """
        try:
            logger.debug(f"[DB] Updating wallet creation status: {user_id}, {chain}")
            
            response = await asyncio.to_thread(
                lambda: self.supabase.table("wallet_creation_status")
                .update(update_data)
                .eq("user_id", user_id)
                .eq("chain", chain)
                .execute()
            )
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"[DB] Error updating wallet creation status {user_id}, {chain}: {str(e)}")
            return False

    async def get_wallet_creation_queue_items(self, batch_size: int = 20) -> List[Dict[str, Any]]:
        """
        Get wallet creation queue items ready for processing
        """
        try:
            logger.debug(f"[DB] Fetching wallet creation queue items, batch: {batch_size}")
            
            response = await asyncio.to_thread(
                lambda: self.supabase.table("wallet_creation_queue")
                .select("*")
                .lte("scheduled_for", datetime.utcnow().isoformat())
                .is_("locked_at", "null")
                .limit(batch_size)
                .execute()
            )
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"[DB] Error fetching wallet creation queue: {str(e)}")
            return []

    async def upsert_wallet_creation_queue(self, queue_data: Dict[str, Any]) -> bool:
        """
        Upsert wallet creation queue item
        """
        try:
            logger.debug(f"[DB] Upserting wallet creation queue: {queue_data.get('user_id')}")
            
            response = await asyncio.to_thread(
                lambda: self.supabase.table("wallet_creation_queue")
                .upsert(queue_data, on_conflict='user_id,chain')
                .execute()
            )
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"[DB] Error upserting wallet creation queue: {str(e)}")
            return False

    async def update_wallet_creation_queue(self, item_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update wallet creation queue item
        """
        try:
            logger.debug(f"[DB] Updating wallet creation queue item: {item_id}")
            
            response = await asyncio.to_thread(
                lambda: self.supabase.table("wallet_creation_queue")
                .update(update_data)
                .eq("id", item_id)
                .execute()
            )
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"[DB] Error updating wallet creation queue item {item_id}: {str(e)}")
            return False

    async def delete_wallet_creation_queue_item(self, item_id: str) -> bool:
        """
        Delete wallet creation queue item
        """
        try:
            logger.debug(f"[DB] Deleting wallet creation queue item: {item_id}")
            
            response = await asyncio.to_thread(
                lambda: self.supabase.table("wallet_creation_queue")
                .delete()
                .eq("id", item_id)
                .execute()
            )
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"[DB] Error deleting wallet creation queue item {item_id}: {str(e)}")
            return False

    # EXISTING METHODS (KEEP ALL YOUR CURRENT FUNCTIONALITY)
    async def create_user_profile(self, profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create user profile with proper user_id population"""
        try:
            user_id = profile_data.get("id")
            if not user_id:
                raise ValueError("User ID is required for profile creation")
            
            if isinstance(user_id, str):
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    raise ValueError(f"Invalid UUID format for user_id: {user_id}")
            else:
                user_uuid = user_id
            
            clean_data = {
                "id": str(user_uuid),
                "email": profile_data.get("email", "").lower().strip(),
                "first_name": profile_data.get("first_name"),
                "last_name": profile_data.get("last_name"),
                "phone": profile_data.get("phone"),
                "country": profile_data.get("country", "USA"),
                "country_code": profile_data.get("country_code"),
                "kyc_status": "not_started",
                "kyc_level": 0,
                "role": profile_data.get("role", "alien"),
                "is_admin": False,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"[DB] Creating user profile: {user_uuid}")
            
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
        """Enhanced user profile retrieval with proper error handling"""
        try:
            logger.debug(f"[DB] Fetching user profile: {user_id}")
            
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

    async def get_user_profile_raw(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get UNFILTERED user profile for internal operations (KYC, compliance)
        Returns all columns from user_profiles table without formatting
        """
        try:
            logger.debug(f"[DB] Fetching RAW user profile: {user_id}")
        
            try:
                user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            except ValueError:
                logger.error(f"[DB] Invalid UUID format: {user_id}")
                return None
            
            response = self.supabase.table("user_profiles").select("*").eq("id", str(user_uuid)).maybe_single().execute()
            
            if response.data:
                logger.debug(f"[DB] Raw profile found with {len(response.data)} fields")
                # Return raw data with NO formatting
                return response.data
            else:
                logger.warning(f"[DB] User profile not found: {user_id}")
                return None
                    
        except Exception as e:
            logger.error(f"[DB] Error fetching raw profile {user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Failed to fetch user profile")
    
    async def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user profile with transaction safety"""
        try:
            logger.info(f"[DB] Updating user profile: {user_id}")
            
            try:
                user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            except ValueError:
                raise ValueError(f"Invalid UUID format: {user_id}")
            
            allowed_fields = {
                "first_name", "last_name", "email", "phone", "country", "country_code",
                "address_line1", "city", "state_province", "postal_code",
                "kyc_status", "kyc_level", "kyc_session_id",
                "kyc_provider", "kyc_started_at", "kyc_completed_at", 
                "kyc_rejection_reason", "security_flags", "last_login_at",
                "failed_login_attempts", "account_locked_until", "bvn", "gender",
                "id_number", "id_type", "algorand_address", "verification_skipped", "role"
            }
            
            clean_update = {}
            for field, value in update_data.items():
                if field in allowed_fields:
                    clean_update[field] = value
            
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
        """Format raw database user profile data - FIXED to preserve actual values"""
        return {
            "id": str(raw_data["id"]),
            "email": raw_data.get("email"),
            "first_name": raw_data.get("first_name"),
            "last_name": raw_data.get("last_name"),
            "phone": raw_data.get("phone"),
            "country": raw_data.get("country", "USA"),
            "country_code": raw_data.get("country_code"),
            # ✅ FIX: Remove defaults - use actual DB values
            "kyc_status": raw_data.get("kyc_status"),
            "kyc_level": raw_data.get("kyc_level"),
            "role": raw_data.get("role"),
            "kyc_provider": raw_data.get("kyc_provider"),
            "is_admin": raw_data.get("is_admin", False),
            "verification_skipped": raw_data.get("verification_skipped", False),
            # ✅ FIX: Add missing fields
            "algorand_address": raw_data.get("algorand_address"),
            "wallet_address": raw_data.get("wallet_address"),
            "bvn": raw_data.get("bvn"),
            "id_number": raw_data.get("id_number"),
            "id_type": raw_data.get("id_type"),
            "kyc_session_id": raw_data.get("kyc_session_id"),
            "kyc_started_at": raw_data.get("kyc_started_at"),
            "kyc_completed_at": raw_data.get("kyc_completed_at"),
            "created_at": raw_data.get("created_at"),
            "updated_at": raw_data.get("updated_at")
        }

    async def get_user_profile_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Alias for get_user_profile"""
        return await self.get_user_profile(user_id)
    
    async def log_kyc_session(self, user_id: str, session_id: str, client_id: str) -> bool:
        """Log KYC verification session"""
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
                logger.info(f"[DB] KYC session logged successfully")
                return True
            else:
                logger.error(f"[DB] Failed to log KYC session")
                return False
                
        except Exception as e:
            logger.error(f"[DB] Error logging KYC session: {str(e)}")
            raise

    async def update_user_kyc_status(self, user_id: str, status: str, level: int) -> bool:
        """Update user KYC status and level"""
        try:
            logger.info(f"[DB] Updating KYC status for user {user_id}: {status} (level {level})")
            
            update_data = {
                "kyc_status": status,
                "kyc_level": level,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if status in ["approved", "verified", "completed"]:
                update_data["kyc_completed_at"] = datetime.utcnow().isoformat()
            elif status in ["pending", "initiated"]:
                update_data["kyc_started_at"] = datetime.utcnow().isoformat()
            
            response = self.supabase.table("user_profiles").update(update_data).eq("id", user_id).execute()
            
            if response.data:
                logger.info(f"[DB] KYC status updated successfully")
                return True
            else:
                logger.error(f"[DB] Failed to update KYC status")
                return False
                
        except Exception as e:
            logger.error(f"[DB] Error updating KYC status: {str(e)}")
            raise

    async def save_encrypted_private_key(self, user_id: str, algorand_address: str, encrypted_pk: str) -> bool:
        """Save user's encrypted private key"""
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
                logger.info(f"[DB] Encrypted private key saved successfully")
                return True
            else:
                logger.error(f"[DB] Failed to save encrypted private key")
                return False
                
        except Exception as e:
            logger.error(f"[DB] Error saving encrypted key: {str(e)}")
            raise

    async def get_encrypted_private_key(self, user_id: str) -> Optional[str]:
        """Retrieve user's encrypted private key"""
        try:
            logger.debug(f"[DB] Retrieving encrypted private key for user {user_id}")
            
            response = self.supabase.table("user_wallets").select("algorand_private_key").eq("user_id", user_id).eq("is_active", True).maybe_single().execute()
            
            if response.data:
                logger.debug(f"[DB] Encrypted private key retrieved")
                return response.data["algorand_private_key"]
            else:
                logger.warning(f"[DB] No encrypted private key found")
                return None
                
        except Exception as e:
            logger.error(f"[DB] Error retrieving encrypted key: {str(e)}")
            raise
    
    async def query(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Universal query wrapper for Supabase tables
        
        🎯 PURPOSE: Yield manager needs this for wallet_balances queries
        
        Args:
            table: Table name (e.g., "wallet_balances", "yield_stakes")
            filters: {"user_id": "abc123", "status": "active"}
            columns: ["usdt_balance", "algo_balance"] or None for all
            order_by: {"created_at": "desc"}
            limit: Max rows to return
        
        Returns:
            List of matching rows as dicts
        
        Example:
            result = await db.query(
                "wallet_balances",
                filters={"user_id": user_id},
                columns=["usdt_balance"]
            )
        """
        try:
            logger.debug(f"[DB] Query: {table} | Filters: {filters}")
            
            # Build query
            if columns:
                query = self.supabase.from_(table).select(",".join(columns))
            else:
                query = self.supabase.from_(table).select("*")
            
            # Apply filters
            if filters:
                for column, value in filters.items():
                    query = query.eq(column, value)
            
            # Apply ordering
            if order_by:
                for column, direction in order_by.items():
                    ascending = (direction.lower() == "asc")
                    query = query.order(column, desc=(not ascending))
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            # Execute using asyncio.to_thread (matches your pattern)
            response = await asyncio.to_thread(lambda: query.execute())
            
            logger.debug(f"[DB] Query returned {len(response.data) if response.data else 0} rows")
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"[DB] Query failed: {table} | {e}")
            logger.error(traceback.format_exc())
            return []

    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> bool:
        """
        Update records matching filters
        
        🎯 PURPOSE: Yield manager needs this for wallet balance updates
        
        Args:
            table: Table name (e.g., "wallet_balances")
            data: {"usdt_balance": 1500.0, "updated_at": "..."}
            filters: {"user_id": "abc123"}
        
        Returns:
            True if successful
        
        Example:
            success = await db.update(
                "wallet_balances",
                data={"usdt_balance": new_balance},
                filters={"user_id": user_id}
            )
        """
        try:
            logger.debug(f"[DB] Update: {table} | Data: {data} | Filters: {filters}")
            
            # Build update query
            query = self.supabase.from_(table).update(data)
            
            # Apply filters
            for column, value in filters.items():
                query = query.eq(column, value)
            
            # Execute using asyncio.to_thread
            response = await asyncio.to_thread(lambda: query.execute())
            
            success = bool(response.data)
            logger.debug(f"[DB] Update {'succeeded' if success else 'failed'}")
            return success
            
        except Exception as e:
            logger.error(f"[DB] Update failed: {table} | {e}")
            logger.error(traceback.format_exc())
            return False
        
    async def get_user_wallet(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete wallet information for user"""
        try:
            logger.debug(f"[DB] Fetching user wallet: {user_id}")
            
            response = self.supabase.table("user_wallets") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("is_active", True) \
                .maybe_single() \
                .execute()
            
            if response and hasattr(response, 'data') and response.data:
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
            logger.error(traceback.format_exc())
            return None

    async def log_event(self, table_name: str, event_data: Dict[str, Any]) -> bool:
        """Generic event logger"""
        try:
            response = self.supabase.table(table_name).insert(event_data).execute()
            return bool(response.data)
        except Exception as e:
            logger.warning(f"[DB] log_event failed: {str(e)}")
            return False

    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            logger.debug("[DB] Performing health check")
            
            response = self.supabase.table("user_profiles").select("count", count="exact").limit(1).execute()
            
            if response.count is not None:
                logger.debug(f"[DB] Health check passed")
                return True
            else:
                logger.error("[DB] Health check failed")
                return False
                
        except Exception as e:
            logger.error(f"[DB] Health check failed: {str(e)}")
            return False

    async def close_connections(self):
        """Gracefully close database connections"""
        try:
            if self.pool and not self.pool._closed:
                await self.pool.close()
                logger.info("[DB] Database connections closed successfully")
        except Exception as e:
            logger.error(f"[DB] Error closing database connections: {str(e)}")

    async def get_last_successful_price(self, currency_pair: str, hours: int = 24) -> Optional[Dict[str, Any]]:
        """
        Get last successful price from price_history within N hours
        Used for emergency fallback when all APIs fail
        """
        try:
            query = """
                SELECT 
                    rate,
                    source,
                    confidence,
                    timestamp
                FROM public.price_history 
                WHERE currency_pair = $1
                AND timestamp > NOW() - INTERVAL '%s hours'
                AND confidence > 0.7
                ORDER BY timestamp DESC 
                LIMIT 1
            """ % hours
            
            result = await self.db.fetchrow(query, currency_pair)
            
            if result:
                return {
                    'rate': Decimal(str(result['rate'])),
                    'source': result['source'],
                    'confidence': result['confidence'],
                    'timestamp': result['timestamp']
                }
                
        except Exception as e:
            logger.error(f"Failed to get last successful price for {currency_pair}: {e}")
        
        return None

SuperDatabaseService = DatabaseService