import os
import logging
from supabase import Client
from cryptography.fernet import Fernet, InvalidToken
from algosdk import account, mnemonic
from fastapi import HTTPException
from uuid import uuid4
from datetime import datetime

from config import Settings

logger = logging.getLogger(__name__)

class WalletService:
    """
    Handles the secure creation, encryption, and storage of user wallets
    in the 'wallet_balances' table. Updated to match actual database schema.
    """
    def __init__(self, settings: Settings, supabase_client: Client):
        """
        Initializes the WalletService.
        """
        if not settings.ENCRYPTION_KEY:
            logger.critical("FATAL: ENCRYPTION_KEY is not configured. Wallet service cannot operate securely.")
            raise ValueError("ENCRYPTION_KEY must be set for wallet operations.")

        try:
            encryption_key_bytes = settings.ENCRYPTION_KEY.get_secret_value().encode()
            self.cipher = Fernet(encryption_key_bytes)
        except (ValueError, TypeError) as e:
            logger.critical(f"Invalid ENCRYPTION_KEY provided. Cannot initialize cipher. Error: {e}")
            raise ValueError("Invalid ENCRYPTION_KEY.")

        self.supabase = supabase_client
        logger.info("WalletService initialized successfully in secure mode.")

    def _encrypt(self, data: str) -> str:
        """Encrypts sensitive data using the configured key."""
        return self.cipher.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypts sensitive data using the configured key."""
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except InvalidToken:
            logger.critical("Failed to decrypt wallet data - InvalidToken. The encryption key may have changed or data is corrupt.")
            raise HTTPException(status_code=500, detail="Wallet data decryption failed due to an invalid token.")
        except Exception as e:
            logger.critical(f"An unexpected error occurred during decryption: {e}")
            raise HTTPException(status_code=500, detail="A critical error occurred during wallet data decryption.")

    def create_algorand_wallet(self) -> dict:
        """
        Generates a new, live Algorand keypair and its corresponding mnemonic phrase.
        This is the source of all key material for a new user.
        """
        try:
            logger.info("Generating a new LIVE Algorand keypair and mnemonic phrase.")
            private_key, address = account.generate_account()
            mnemonic_phrase = mnemonic.from_private_key(private_key)
            
            return {
                "address": address,
                "private_key": private_key,       # This is handled ephemerally and encrypted for storage.
                "mnemonic": mnemonic_phrase,      # This is returned to the user ONCE and never stored.
                "is_demo": False
            }
        except Exception as e:
            logger.error(f"Failed to generate Algorand keypair: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Could not generate a new wallet keypair.")

    async def store_encrypted_wallet(self, user_id: str, wallet_data: dict) -> dict:
        """
        Encrypts the private key from the generated wallet data and stores the
        non-sensitive parts in the 'wallet_balances' table.

        **CRITICAL:** This function does NOT handle or store the mnemonic phrase.
        Updated to match the actual wallet_balances table schema.
        """
        logger.info(f"Preparing to store encrypted wallet for user_id: {user_id}")
        
        if "private_key" not in wallet_data or "address" not in wallet_data:
            raise ValueError("Wallet data is missing required keys for storage.")

        try:
            # Step 1: Encrypt the private key for secure storage.
            encrypted_pk = self._encrypt(wallet_data["private_key"])
            
            # Step 2: Prepare data matching the ACTUAL 'wallet_balances' schema.
            # Store encrypted private key in metadata JSONB field
            db_record = {
                "user_id": user_id,
                "wallet_address": wallet_data["address"],
                "algo_balance": 0,
                "usds_balance": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "metadata": {
                "encrypted_private_key": encrypted_pk,
                "is_demo": wallet_data.get("is_demo", False),
                "created_at": datetime.utcnow().isoformat()
               }
            }
            
            # Step 3: Insert into the 'wallet_balances' table.
            response = self.supabase.from_("wallet_balances").insert(db_record).execute()
            
            if not response.data:
                logger.error(f"Supabase insert failed for user {user_id}. Response: {response.error}")
                raise Exception(f"Failed to create wallet record in database: {response.error.message if response.error else 'No data returned'}")
                
            logger.info(f"Successfully stored encrypted wallet for user: {user_id}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Critical error storing wallet for user {user_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="A server error occurred during wallet storage.")

    async def get_decrypted_private_key(self, user_id: str) -> str:
        """
        Securely retrieves and decrypts a user's private key from the 'wallet_balances' table.
        Updated to read from metadata JSONB field.
        """
        logger.warning(f"SECURITY: Requesting decrypted private key for user {user_id}.")
        try:
            # Query the wallet_balances table and extract from metadata
            response = self.supabase.from_("wallet_balances") \
                .select("metadata") \
                .eq("user_id", user_id) \
                .single() \
                .execute()

            if not response.data or not response.data.get("metadata"):
                logger.error(f"No wallet record or metadata found for user {user_id}.")
                raise HTTPException(status_code=404, detail="Secure wallet data not found for user.")

            metadata = response.data["metadata"]
            encrypted_pk = metadata.get("encrypted_private_key")
            
            if not encrypted_pk:
                logger.error(f"No encrypted private key found in metadata for user {user_id}.")
                raise HTTPException(status_code=404, detail="Encrypted private key not found in wallet data.")

            decrypted_pk = self._decrypt(encrypted_pk)
            
            logger.info(f"Successfully decrypted private key for user {user_id} for ephemeral use.")
            return decrypted_pk

        except HTTPException:
            raise
        except Exception as e:
            logger.critical(f"Catastrophic failure retrieving private key for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Could not retrieve secure wallet data.")