import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from algosdk import account, mnemonic, transaction, encoding
from algosdk.v2client import algod
from algosdk.error import AlgodHTTPError
from algosdk.transaction import (
    AssetTransferTxn,
    PaymentTxn,
    AssetOptInTxn,
)
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import Settings

logger = logging.getLogger(__name__)

class AlgorandService:
    """
    The single source of truth for all interactions with the Algorand blockchain.
    This service handles raw on-chain operations like transfers, minting, and balance checks.
    """
    def __init__(self, settings: Settings):
        """
        Initializes the service with a pre-configured settings object,
        following a clean dependency injection pattern.
        """
        self.settings = settings
        self.algod_client = algod.AlgodClient(
            settings.ALGORAND_API_KEY.get_secret_value(), 
            settings.ALGORAND_NODE_URL
        )
        self.usds_asset_id = settings.USDS_ASSET_ID
        self.decimals = 6

        if not settings.ALGORAND_CREATOR_MNEMONIC:
            raise ValueError("ALGORAND_CREATOR_MNEMONIC is not configured in environment.")
        
        try:
            mnemonic_string = settings.ALGORAND_CREATOR_MNEMONIC.get_secret_value()
            self.treasury_private_key = mnemonic.to_private_key(mnemonic_string)
            self.treasury_address = account.address_from_private_key(self.treasury_private_key)
            logger.info(f"AlgorandService initialized. Treasury Address: {self.treasury_address}")
        except Exception as e:
            logger.critical(f"Failed to derive treasury account from mnemonic: {e}", exc_info=True)
            raise

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def wait_for_confirmation(self, tx_id: str) -> Dict[str, Any]:
        """
        Waits for a transaction to be confirmed on the Algorand network with exponential backoff.
        """
        logger.info(f"Waiting for confirmation of transaction: {tx_id}")
        last_round = self.algod_client.status().get("last-round")
        for _ in range(10): # Check up to 10 rounds
            try:
                txinfo = self.algod_client.pending_transaction_info(tx_id)
                if txinfo.get("confirmed-round") and txinfo.get("confirmed-round") > 0:
                    logger.info(f"Transaction {tx_id} confirmed in round {txinfo.get('confirmed-round')}.")
                    return txinfo
                
                self.algod_client.status_after_block(last_round + 1)
                last_round += 1
            except AlgodHTTPError as e:
                if 'not found' in str(e).lower():
                    logger.warning(f"Pending transaction {tx_id} not found, it might already be confirmed.")
                    # In a production system with an indexer, you would query it here as a fallback.
                    pass 
        raise TimeoutError(f"Transaction {tx_id} was not confirmed after multiple rounds.")

    async def get_usds_balance(self, address: str) -> Decimal:
        """
        Gets the USDS balance for a given Algorand address.
        """
        try:
            account_info = self.algod_client.account_info(address)
            for asset in account_info.get("assets", []):
                if asset["asset-id"] == self.usds_asset_id:
                    amount = Decimal(asset["amount"]) / Decimal(10**self.decimals)
                    return amount.quantize(Decimal('0.000001'))
            return Decimal("0.0")
        except AlgodHTTPError as e:
            if "account not found" in str(e):
                logger.warning(f"Account {address} not found on-chain. Returning zero balance.")
                return Decimal("0.0")
            logger.error(f"Failed to get balance for {address}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while getting balance for {address}: {e}")
            raise

    async def send_usds(self, sender_private_key: str, receiver_address: str, amount: Decimal, memo: str) -> str:
        """
        Transfers USDS from a user's account to another. Requires the user's private key.
        This is a highly sensitive operation.
        """
        try:
            sender_address = account.address_from_private_key(sender_private_key)
            params = self.algod_client.suggested_params()
            amount_base_units = int(amount * (10**self.decimals))

            txn = AssetTransferTxn(
                sender=sender_address, sp=params, receiver=receiver_address,
                amt=amount_base_units, index=self.usds_asset_id, note=memo.encode()
            )
            signed_txn = txn.sign(sender_private_key)
            tx_id = self.algod_client.send_transaction(signed_txn)
            await self.wait_for_confirmation(tx_id)
            logger.info(f"Successfully sent {amount} USDS from {sender_address} to {receiver_address}. TxID: {tx_id}")
            return tx_id
        except Exception as e:
            logger.error(f"Failed to send USDS: {e}", exc_info=True)
            raise

    async def mint_usds(self, recipient_address: str, amount: Decimal, fiat_reference: str) -> str:
        """
        Mints new USDS from the treasury account to a recipient.
        """
        try:
            params = self.algod_client.suggested_params()
            amount_base_units = int(amount * (10**self.decimals))

            txn = AssetTransferTxn(
                sender=self.treasury_address, sp=params, receiver=recipient_address,
                amt=amount_base_units, index=self.usds_asset_id, note=f"USDS Mint. Ref: {fiat_reference}".encode()
            )
            signed_txn = txn.sign(self.treasury_private_key)
            tx_id = self.algod_client.send_transaction(signed_txn)
            await self.wait_for_confirmation(tx_id)
            logger.info(f"Successfully minted {amount} USDS to {recipient_address}. TxID: {tx_id}")
            return tx_id
        except Exception as e:
            logger.error(f"Failed to mint USDS: {e}", exc_info=True)
            raise

    async def burn_usds(self, user_private_key: str, amount: Decimal, fiat_reference: str) -> str:
        """
        Burns USDS by transferring it from a user's account back to the treasury.
        """
        try:
            user_address = account.address_from_private_key(user_private_key)
            params = self.algod_client.suggested_params()
            amount_base_units = int(amount * (10**self.decimals))

            txn = AssetTransferTxn(
                sender=user_address, sp=params, receiver=self.treasury_address,
                amt=amount_base_units, index=self.usds_asset_id, note=f"USDS Burn. Ref: {fiat_reference}".encode()
            )
            signed_txn = txn.sign(user_private_key)
            tx_id = self.algod_client.send_transaction(signed_txn)
            await self.wait_for_confirmation(tx_id)
            logger.info(f"Successfully burned {amount} USDS from {user_address}. TxID: {tx_id}")
            return tx_id
        except Exception as e:
            logger.error(f"Failed to burn USDS: {e}", exc_info=True)
            raise

    async def prepare_opt_in_transaction(self, user_address: str) -> Dict[str, Any]:
        """
        Prepares a USDS opt-in transaction for the user to sign on the frontend.
        """
        try:
            if not account.is_valid_address(user_address):
                raise ValueError("Invalid Algorand address provided for opt-in.")
            
            params = self.algod_client.suggested_params()
            txn = AssetOptInTxn(sender=user_address, sp=params, index=self.usds_asset_id)
            
            unsigned_txn_b64 = encoding.msgpack_encode(txn)
            
            return {
                "success": True,
                "unsigned_txn_b64": unsigned_txn_b64,
                "tx_id": txn.get_txid()
            }
        except Exception as e:
            logger.error(f"Failed to prepare opt-in transaction for {user_address}: {e}", exc_info=True)
            raise

    async def fund_account_for_opt_in(self, user_address: str) -> Optional[str]:
        """
        Funds a new user account with the minimum balance required for an asset opt-in.
        """
        try:
            min_balance = 100000  # 0.1 ALGO for base account
            asset_opt_in_fee = 100000  # 0.1 ALGO for asset holding
            total_funding = min_balance + asset_opt_in_fee

            params = self.algod_client.suggested_params()
            txn = PaymentTxn(
                sender=self.treasury_address, sp=params, receiver=user_address,
                amt=total_funding, note=b"Seamount Account Funding for USDS Opt-in"
            )
            signed_txn = txn.sign(self.treasury_private_key)
            tx_id = self.algod_client.send_transaction(signed_txn)
            await self.wait_for_confirmation(tx_id)
            logger.info(f"Successfully funded {user_address} with {total_funding} microAlgos. TxID: {tx_id}")
            return tx_id
        except Exception as e:
            logger.error(f"Failed to fund account {user_address}: {e}", exc_info=True)
            raise