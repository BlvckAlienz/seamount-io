import os
import logging
from supabase import Client
from cryptography.fernet import Fernet, InvalidToken
from algosdk import account, mnemonic
from fastapi import HTTPException
from postgrest import APIError

# Assumes config.py is in the root of the backend directory
from config import Settings

logger = logging.getLogger(__name__)

class WalletService:
    """
    Handles the secure creation, encryption, and storage of user wallets.
    This service is the gatekeeper for all sensitive key material.
    """
    def __init__(self, settings: Settings, supabase_client: Client):
        """
        Initializes the WalletService with necessary configurations and clients.
        """
        if not settings.ENCRYPTION_KEY:
            raise ValueError("ENCRYPTION_KEY is not configured in the environment. Cannot proceed securely.")
        
        self.supabase = supabase_client
        try:
            # --- THE CRITICAL FIX IS HERE ---
            # We must call .get_secret_value() to access the raw string from the SecretStr object
            # before we can encode it for the Fernet cipher.
            encryption_key_bytes = settings.ENCRYPTION_KEY.get_secret_value().encode()
            self.cipher = Fernet(encryption_key_bytes)
        except (ValueError, TypeError):
            raise ValueError("Invalid ENCRYPTION_KEY. Please generate a valid key using Fernet.generate_key().")

        logger.info("WalletService initialized successfully.")

    def _encrypt(self, data: str) -> str:
        """Encrypts sensitive data (like a private key) using Fernet symmetric encryption."""
        return self.cipher.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """
        Decrypts sensitive data. This method should be used sparingly and only in secure,
        ephemeral contexts (e.g., just-in-time for signing a transaction).
        """
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except InvalidToken:
            logger.critical("Failed to decrypt wallet data - InvalidToken. This could indicate a key mismatch or data corruption.")
            raise HTTPException(status_code=500, detail="Wallet data decryption failed due to a key error.")

    def create_algorand_wallet(self) -> dict:
        """
        Generates a new Algorand account keypair and mnemonic.
        """
        try:
            private_key, address = account.generate_account()
            mnemonic_phrase = mnemonic.from_private_key(private_key)
            return {
                "address": address,
                "private_key": private_key,
                "mnemonic": mnemonic_phrase,
            }
        except Exception as e:
            logger.error(f"Failed to generate Algorand keypair: {e}")
            raise HTTPException(status_code=500, detail="Could not generate a new wallet.")

    async def provision_user_wallet(self, user_id: str) -> dict:
        """
        Atomically provisions and saves a new Algorand wallet for a user.
        """
        logger.info(f"Attempting to provision wallet for user_id: {user_id}")
        try:
            algo_wallet = self.create_algorand_wallet()
            encrypted_pk = self._encrypt(algo_wallet["private_key"])
            
            response = await self.supabase.rpc('provision_user_wallet', {
                'user_id_input': user_id,
                'algorand_address_input': algo_wallet['address'],
                'encrypted_pk_input': encrypted_pk
            }).execute()

            if response.error:
                raise APIError(response.error.message, code=response.error.code, details=response.error.details, hint=response.error.hint)

            logger.info(f"Successfully and atomically provisioned Algorand wallet for user {user_id}")
            return { "algorand_address": algo_wallet["address"] }
        except APIError as e:
            logger.error(f"Supabase RPC error during wallet provisioning for user {user_id}: {e.message}")
            raise HTTPException(status_code=500, detail="Database error during wallet provisioning.")
        except Exception as e:
            logger.error(f"A critical error occurred during wallet provisioning for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="A critical error occurred during wallet provisioning.")

    async def get_decrypted_private_key(self, user_id: str) -> str:
        """
        Securely retrieves and decrypts a user's private key.
        """
        logger.warning(f"SECURITY: Requesting decrypted private key for user {user_id}.")
        try:
            response = await self.supabase.table("user_wallets").select("algorand_private_key").eq("user_id", user_id).single().execute()

            if not response.data or not response.data.get("algorand_private_key"):
                raise ValueError(f"No private key found for user {user_id}.")

            encrypted_pk = response.data["algorand_private_key"]
            decrypted_pk = self._decrypt(encrypted_pk)
            
            logger.info(f"Successfully decrypted private key for user {user_id} for ephemeral use.")
            return decrypted_pk

        except ValueError as ve:
            logger.error(f"Value error while retrieving private key for user {user_id}: {ve}")
            raise HTTPException(status_code=404, detail="Secure wallet data not found for user.")
        except Exception as e:
            logger.critical(f"Catastrophic failure retrieving private key for user {user_gand_service.pyid}: {e}")
            raise HTTPException(status_code=500, detail="Could not retrieve secure wallet data.")