# File Location: backend/services/database_service.py
# Description: The definitive, production-ready service for all Supabase database interactions.

import logging
from typing import Dict, Any, Optional, List
from supabase import create_client, Client
from postgrest import APIError
from decimal import Decimal
from fastapi import HTTPException
from datetime import datetime

# Assumes config.py is in the root of the backend directory
from config import Settings

logger = logging.getLogger(__name__)

class DatabaseService:
    """
    Centralized database service acting as the single source of truth for all Supabase interactions.
    Enforces data consistency, handles robust error logging, and provides a clean API for other services.
    """
    def __init__(self, settings: Settings):
        if not settings.VITE_SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise ValueError("Supabase URL and Service Key must be configured.")
        
        self.supabase: Client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        logger.info("DatabaseService initialized successfully.")

    def _handle_supabase_error(self, error: APIError, context: str):
        """Centralized handler for Supabase API errors."""
        logger.error(f"Supabase error during {context}: {error.message}")
        # You can add more specific error handling here based on PostgREST error codes
        raise HTTPException(status_code=500, detail=f"A database error occurred: {context}")

    # =============================================================================
    # User & Profile Management
    # =============================================================================

    async def get_user_profile_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a user's complete profile by their UUID."""
        try:
            response = self.supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
            return response.data
        except APIError as e:
            self._handle_supabase_error(e, f"get_user_profile_by_id for {user_id}")
        except Exception as e:
            logger.error(f"Unexpected error in get_user_profile_by_id for {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Could not retrieve user profile.")

    async def get_user_profile_by_algorand_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Retrieves a user's profile by their Algorand wallet address."""
        try:
            response = self.supabase.table("user_profiles").select("*").eq("algorand_address", address).single().execute()
            return response.data
        except APIError as e:
            self._handle_supabase_error(e, f"get_user_profile_by_algorand_address for {address}")
        except Exception as e:
            logger.error(f"Unexpected error in get_user_profile_by_algorand_address for {address}: {e}")
            raise HTTPException(status_code=500, detail="Could not retrieve user profile by address.")
            
    async def update_user_kyc_status(self, user_id: str, new_status: str, new_level: int) -> Dict[str, Any]:
        """Updates a user's KYC status and level in their profile."""
        try:
            response = self.supabase.table("user_profiles").update({
                "kyc_status": new_status,
                "kyc_level": new_level,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            return response.data[0]
        except APIError as e:
            self._handle_supabase_error(e, f"update_user_kyc_status for {user_id}")
        except Exception as e:
            logger.error(f"Unexpected error in update_user_kyc_status for {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Could not update KYC status.")

    # =============================================================================
    # Secure Wallet Management
    # =============================================================================
    
    async def save_encrypted_private_key(self, user_id: str, encrypted_pk: str) -> bool:
        """Saves a user's encrypted private key to the secure user_wallets table."""
        try:
            await self.supabase.table("user_wallets").insert({
                "user_id": user_id,
                "algorand_private_key": encrypted_pk
            }).execute()
            return True
        except APIError as e:
            self._handle_supabase_error(e, f"save_encrypted_private_key for {user_id}")
        except Exception as e:
            logger.error(f"Unexpected error saving private key for {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Could not save secure wallet data.")
            
    async def get_encrypted_private_key(self, user_id: str) -> Optional[str]:
        """Retrieves a user's encrypted private key from the secure user_wallets table."""
        try:
            response = self.supabase.table("user_wallets").select("algorand_private_key").eq("user_id", user_id).single().execute()
            if response.data:
                return response.data.get("algorand_private_key")
            return None
        except APIError as e:
            # It's common for a GET to find nothing, don't raise 500 unless it's a real server error
            if "PGRST116" not in e.message: # "PGRST116" is PostgREST code for "queried row does not exist"
                self._handle_supabase_error(e, f"get_encrypted_private_key for {user_id}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting private key for {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Could not retrieve secure wallet data.")

    # =============================================================================
    # Transaction & Payment Logging
    # =============================================================================

    async def create_payment_transaction(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new record in the payment_transactions table."""
        try:
            response = self.supabase.table("payment_transactions").insert(tx_data).execute()
            return response.data[0]
        except APIError as e:
            self._handle_supabase_error(e, "create_payment_transaction")
        except Exception as e:
            logger.error(f"Unexpected error creating payment transaction: {e}")
            raise HTTPException(status_code=500, detail="Could not create payment record.")

    async def update_payment_transaction_status(self, transaction_id: str, status: str, error_message: Optional[str] = None, tx_hash: Optional[str] = None) -> Dict[str, Any]:
        """Updates the status of an existing payment transaction."""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            if error_message:
                update_data["error_message"] = error_message
            if tx_hash:
                update_data["tx_hash"] = tx_hash
                update_data["completed_at"] = datetime.utcnow().isoformat()

            response = self.supabase.table("payment_transactions").update(update_data).eq("id", transaction_id).execute()
            return response.data[0]
        except APIError as e:
            self._handle_supabase_error(e, f"update_payment_transaction_status for {transaction_id}")
        except Exception as e:
            logger.error(f"Unexpected error updating payment transaction {transaction_id}: {e}")
            raise HTTPException(status_code=500, detail="Could not update payment record.")

    async def get_payment_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves a user's payment history."""
        try:
            response = self.supabase.table("payment_transactions").select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True).limit(limit).execute()
            return response.data
        except APIError as e:
            self._handle_supabase_error(e, f"get_payment_history for {user_id}")
        except Exception as e:
            logger.error(f"Unexpected error getting payment history for {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Could not retrieve payment history.")

    # =============================================================================
    # Generic Logging for Other Services (Audit, Monitoring, etc.)
    # =============================================================================

    async def log_event(self, table_name: str, event_data: Dict[str, Any]) -> bool:
        """
        A generic method for services like Audit and Monitoring to write their logs.
        """
        try:
            self.supabase.table(table_name).insert(event_data).execute()
            return True
        except APIError as e:
            self._handle_supabase_error(e, f"log_event to {table_name}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error logging event to {table_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Could not log event to {table_name}.")