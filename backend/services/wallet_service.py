import os
import logging
import traceback
from supabase import Client
from cryptography.fernet import Fernet, InvalidToken
from algosdk import account, mnemonic
from fastapi import HTTPException
from uuid import uuid4
from datetime import datetime
from decimal import Decimal

from backend.config import Settings, get_settings

logger = logging.getLogger(__name__)

class WalletService:
    """
    Handles the secure creation, encryption, and storage of user wallets
    Updated for Phase 1: Multi-Asset Support (USDT, USDCa, goBTC, goETH)
    """

    def __init__(self, settings: Settings, supabase_client: Client):
        """
        Initializes the WalletService with multi-asset support.
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

        self.settings = settings
        self.supabase = supabase_client
        logger.info("WalletService initialized successfully with multi-asset support.")

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
        non-sensitive parts in the 'wallet_balances' table with multi-asset support.

        **CRITICAL:** This function does NOT handle or store the mnemonic phrase.
        Updated to match the actual wallet_balances table schema with Phase 1 assets.
        """
        logger.info(f"Preparing to store encrypted wallet for user_id: {user_id}")
        
        if "private_key" not in wallet_data or "address" not in wallet_data:
            raise ValueError("Wallet data is missing required keys for storage.")

        try:
            # Step 1: Encrypt the private key for secure storage.
            encrypted_pk = self._encrypt(wallet_data["private_key"])
            
            # Step 2: Prepare data matching the ACTUAL 'wallet_balances' schema with Phase 1 assets.
            db_record = {
                "user_id": user_id,
                "wallet_address": wallet_data["address"],
                "algo_balance": 0,
                "usds_balance": 0,
                "usdt_balance": 0,  # NEW: Phase 1 asset
                "usdc_balance": 0,  # NEW: Phase 1 asset
                "gobtc_balance": 0, # NEW: Phase 1 asset
                "goeth_balance": 0, # NEW: Phase 1 asset
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

    async def get_wallet_balances(self, user_id: str) -> dict:
        """
        Retrieves all wallet balances for a user, including Phase 1 assets.
        """
        try:
            response = self.supabase.from_("wallet_balances") \
                .select("*") \
                .eq("user_id", user_id) \
                .single() \
                .execute()

            if not response.data:
                logger.error(f"No wallet found for user {user_id}")
                raise HTTPException(status_code=404, detail="Wallet not found for user.")

            wallet_data = response.data
            
            # Format balances with proper decimal places
            balances = {
                "algo": Decimal(str(wallet_data.get("algo_balance", 0))),
                "usds": Decimal(str(wallet_data.get("usds_balance", 0))),
                "usdt": Decimal(str(wallet_data.get("usdt_balance", 0))),
                "usdc": Decimal(str(wallet_data.get("usdc_balance", 0))),
                "gobtc": Decimal(str(wallet_data.get("gobtc_balance", 0))),
                "goeth": Decimal(str(wallet_data.get("goeth_balance", 0))),
                "wallet_address": wallet_data.get("wallet_address"),
                "last_updated": wallet_data.get("last_updated")
            }
            
            return balances
            
        except Exception as e:
            logger.error(f"Failed to get wallet balances for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Could not retrieve wallet balances.")

    async def update_asset_balance(self, user_id: str, asset: str, amount: Decimal) -> bool:
        """
        Updates a specific asset balance for a user.
        Supports: algo, usds, usdt, usdc, gobtc, goeth
        """
        try:
            # Validate asset type
            valid_assets = ["algo", "usds", "usdt", "usdc", "gobtc", "goeth"]
            if asset not in valid_assets:
                raise ValueError(f"Invalid asset type: {asset}. Must be one of {valid_assets}")
            
            # Convert to database column name
            column_name = f"{asset}_balance"
            
            # Update the balance
            response = self.supabase.from_("wallet_balances") \
                .update({column_name: float(amount)}) \
                .eq("user_id", user_id) \
                .execute()
            
            if not response.data:
                logger.error(f"Failed to update {asset} balance for user {user_id}")
                return False
                
            logger.info(f"Successfully updated {asset} balance for user {user_id}: {amount}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating {asset} balance for user {user_id}: {e}")
            return False

    async def create_wallet_for_user(self, user_id: str):
        """
        Create a wallet for a user and return the mnemonic for backup
        """
        try:
            logger.info(f"🚀 Attempting to create wallet for user: {user_id}")
            logger.info(f"📊 Using table: wallet_balances for storage")
            
            # Generate the wallet
            algo_wallet = self.create_algorand_wallet()
            logger.info(f"✅ Algorand wallet generated for user: {user_id}")
            
            # Store encrypted version using the same method as store_encrypted_wallet
            encrypted_pk = self._encrypt(algo_wallet["private_key"])
            logger.info(f"🔒 Private key encrypted successfully")
            
            # Prepare data for wallet_balances table with Phase 1 assets
            db_record = {
                "user_id": user_id,
                "wallet_address": algo_wallet["address"],
                "algo_balance": 0,
                "usds_balance": 0,
                "usdt_balance": 0,  # NEW: Phase 1 asset
                "usdc_balance": 0,  # NEW: Phase 1 asset
                "gobtc_balance": 0, # NEW: Phase 1 asset
                "goeth_balance": 0, # NEW: Phase 1 asset
                "last_updated": datetime.utcnow().isoformat(),
                "metadata": {
                    "encrypted_private_key": encrypted_pk,
                    "is_demo": False,
                    "created_at": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"💾 Attempting to insert wallet record into wallet_balances table")
            
            # Store in database
            result = self.supabase.from_("wallet_balances").insert(db_record).execute()
            
            if not result.data:
                logger.error(f"❌ Failed to create wallet record in database for user: {user_id}")
                raise Exception("Failed to create wallet record")
                
            logger.info(f"✅ Successfully created wallet for user: {user_id}")
            logger.info(f"📝 Wallet address: {algo_wallet['address']}")
            
            # Return success with mnemonic for user backup
            return {
                "success": True,
                "address": algo_wallet["address"],
                "mnemonic": algo_wallet["mnemonic"]
            }
            
        except Exception as e:
            logger.error(f"💥 Wallet creation failed for user {user_id}: {str(e)}")
            logger.error(f"📝 Stack trace: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e)
            }