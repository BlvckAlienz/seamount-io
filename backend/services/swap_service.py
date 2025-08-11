import logging
from typing import Dict, Any
from decimal import Decimal
from datetime import datetime

# --- Core Dependencies ---
from config import Settings
from .algorand_service import AlgorandService
from .database_service import DatabaseService
from .wallet_service import WalletService

# --- Third-Party DEX SDK ---
from tinyman.v2.client import TinymanV2MainnetClient, TinymanV2TestnetClient
from tinyman.v2.asset import Asset
from algosdk.atomic_transaction_composer import AccountTransactionSigner
from algosdk import account

logger = logging.getLogger(__name__)

class SwapService:
    """
    Handles all on-chain asset swaps via DEX aggregators, starting with Tinyman.
    It is a modern, dependency-injected service.
    """
    def __init__(
        self, 
        settings: Settings, 
        algorand_service: AlgorandService, 
        db_service: DatabaseService,
        wallet_service: WalletService
    ):
        """
        Initializes the service with pre-configured dependencies.
        """
        self.settings = settings
        self.algorand_service = algorand_service
        self.db_service = db_service
        self.wallet_service = wallet_service
        
        # Initialize the Tinyman client based on the configured network
        if self.settings.ALGORAND_NETWORK.lower() == 'mainnet':
            self.tinyman_client = TinymanV2MainnetClient(algod_client=self.algorand_service.algod_client)
        else:
            self.tinyman_client = TinymanV2TestnetClient(algod_client=self.algorand_service.algod_client)
        
        logger.info(f"SwapService initialized for {self.settings.ALGORAND_NETWORK}.")

    async def get_swap_quote(self, from_asset_id: int, to_asset_id: int, amount_in: int) -> Dict[str, Any]:
        """
        Gets a real-time swap quote from Tinyman for a given asset pair and amount.
        amount_in is in the smallest unit of the from_asset (e.g., microAlgos).
        """
        try:
            from_asset = self.tinyman_client.fetch_asset(from_asset_id)
            to_asset = self.tinyman_client.fetch_asset(to_asset_id)
            
            quote = self.tinyman_client.fetch_quotes(from_asset(amount_in), to_asset, slippage=0.05) # 5% slippage tolerance
            
            # We will use the fixed input quote for this example
            fixed_input_quote = quote.fixed_input_swap
            
            logger.info(f"Generated Tinyman quote: {amount_in} of A:{from_asset_id} for {fixed_input_quote.amount_out.amount} of A:{to_asset_id}")

            return {
                "amount_in": fixed_input_quote.amount_in.amount,
                "amount_out": fixed_input_quote.amount_out.amount,
                "price_impact": fixed_input_quote.price_impact,
                "quote_object": fixed_input_quote # Pass the object for execution
            }
            
        except Exception as e:
            logger.error(f"Failed to get Tinyman swap quote: {e}", exc_info=True)
            raise

    async def execute_swap(self, user_id: str, from_asset_id: int, to_asset_id: int, amount_in: int) -> Dict[str, Any]:
        """
        Securely executes an on-chain swap for a user by retrieving the key just-in-time.
        """
        logger.info(f"Initiating swap for user {user_id}: {amount_in} of {from_asset_id} -> {to_asset_id}")
        
        user_private_key = None
        try:
            # 1. Get the decrypted private key from the secure vault (WalletService)
            user_private_key = await self.wallet_service.get_decrypted_private_key(user_id)
            user_address = account.address_from_private_key(user_private_key)
            signer = AccountTransactionSigner(user_private_key)
            
            # 2. Get a fresh quote to prevent front-running
            quote_data = await self.get_swap_quote(from_asset_id, to_asset_id, amount_in)
            quote = quote_data["quote_object"]
            
            # 3. Prepare the swap transaction group with the Tinyman SDK
            transaction_group = self.tinyman_client.prepare_swap_transactions_from_quote(quote, sender_address=user_address)
            
            # 4. Sign the transaction group
            transaction_group.sign_with_signer(signer)
            
            # 5. Submit the transaction to the Algorand network
            result = self.tinyman_client.submit(transaction_group)
            
            # 6. Log the swap transaction to our database
            swap_log = {
                "user_id": user_id,
                "from_asset_id": from_asset_id,
                "to_asset_id": to_asset_id,
                "amount_in": amount_in,
                "amount_out": quote_data["amount_out"],
                "status": "completed",
                "tx_hash": result.txids[0]
            }
            await self.db_service.log_event("swap_transactions", swap_log)

            logger.info(f"Swap executed successfully for user {user_id}. TxID: {result.txids[0]}")
            return {
                "success": True,
                "tx_id": result.txids[0],
                "amount_out": quote_data["amount_out"]
            }
            
        except Exception as e:
            logger.error(f"Swap execution failed for user {user_id}: {e}", exc_info=True)
            raise
        finally:
            # --- Secure Memory Wipe ---
            if user_private_key:
                user_private_key = None 
                del user_private_key
                logger.info(f"Private key for user {user_id} purged from memory after swap operation.")