# File: backend/services/algorand_service.py
import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from algosdk import account, mnemonic, transaction, encoding
from algosdk.v2client import algod
from algosdk.error import AlgodHTTPError
from algosdk.transaction import AssetTransferTxn, PaymentTxn, AssetOptInTxn

from backend.config import settings

logger = logging.getLogger(__name__)

class AlgorandService:
    """Algorand blockchain interaction service using free public nodes"""
    
    def __init__(self, settings):  # Add settings parameter
        self.settings = settings
        # Use free AlgoNode - no API key needed
        self.algod_client = algod.AlgodClient(
            algod_token="",
            algod_address=settings.ALGORAND_NODE_URL,  # Now works
            headers={"User-Agent": "Seamount/1.0"}
        )
    
        if not settings.ALGORAND_CREATOR_MNEMONIC:
            raise ValueError("ALGORAND_CREATOR_MNEMONIC required")
        
        try:
            mnemonic_string = settings.ALGORAND_CREATOR_MNEMONIC.get_secret_value()
            self.treasury_private_key = mnemonic.to_private_key(mnemonic_string)
            self.treasury_address = account.address_from_private_key(self.treasury_private_key)
            logger.info(f"AlgorandService initialized. Treasury: {self.treasury_address}")
        except Exception as e:
            logger.critical(f"Failed to initialize treasury: {e}")
            raise

    async def get_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account information from Algorand blockchain"""
        try:
            account_info = self.algod_client.account_info(address)
            return account_info
        except AlgodHTTPError as e:
            if "account not found" in str(e).lower():
                logger.warning(f"Account {address} not found")
                return None
            logger.error(f"Failed to get account info for {address}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting account info: {e}")
            return None

    async def get_asset_balance(self, address: str, asset_id: int) -> Decimal:
        """Get balance for specific asset"""
        try:
            asset_config = self._get_asset_config(asset_id)
            decimals = asset_config['decimals']
            
            account_info = self.algod_client.account_info(address)
            for asset in account_info.get("assets", []):
                if asset["asset-id"] == asset_id:
                    amount = Decimal(asset["amount"]) / Decimal(10**decimals)
                    return amount.quantize(Decimal('0.' + '0'*decimals))
            return Decimal("0.0")
        except AlgodHTTPError as e:
            if "account not found" in str(e):
                return Decimal("0.0")
            raise

    async def transfer_asset(
        self,
        sender_private_key: str,
        receiver_address: str,
        asset_id: int,
        amount: Decimal,
        memo: str = ""
    ) -> str:
        """Transfer asset between accounts"""
        try:
            asset_config = self._get_asset_config(asset_id)
            decimals = asset_config['decimals']
            
            sender_address = account.address_from_private_key(sender_private_key)
            params = self.algod_client.suggested_params()
            amount_base_units = int(amount * (10**decimals))
            
            txn = AssetTransferTxn(
                sender=sender_address,
                sp=params,
                receiver=receiver_address,
                amt=amount_base_units,
                index=asset_id,
                note=memo.encode()
            )
            
            signed_txn = txn.sign(sender_private_key)
            tx_id = self.algod_client.send_transaction(signed_txn)
            await self.wait_for_confirmation(tx_id)
            
            logger.info(f"Transferred {amount} of asset {asset_id} to {receiver_address}")
            return tx_id
        except Exception as e:
            logger.error(f"Asset transfer failed: {e}")
            raise

    async def prepare_asset_opt_in(self, user_address: str, asset_id: int) -> Dict[str, Any]:
        """Prepare opt-in transaction for user to sign"""
        try:
            if not account.is_valid_address(user_address):
                raise ValueError("Invalid Algorand address")
            
            params = self.algod_client.suggested_params()
            txn = AssetOptInTxn(sender=user_address, sp=params, index=asset_id)
            unsigned_txn_b64 = encoding.msgpack_encode(txn)
            
            return {
                "success": True,
                "unsigned_txn_b64": unsigned_txn_b64,
                "tx_id": txn.get_txid(),
                "asset_id": asset_id
            }
        except Exception as e:
            logger.error(f"Failed to prepare opt-in: {e}")
            raise

    def _get_asset_config(self, asset_id: int) -> Dict:
        """Get asset configuration from settings"""
        for asset_key, config in self.settings.SUPPORTED_ASSETS.items():
            if config['asset_id'] == asset_id:
                return config
        raise ValueError(f"Asset ID {asset_id} not configured")

    async def wait_for_confirmation(self, tx_id: str) -> Dict[str, Any]:
        """Wait for transaction confirmation"""
        logger.info(f"Waiting for confirmation: {tx_id}")
        last_round = self.algod_client.status().get("last-round")
        
        for _ in range(10):
            try:
                txinfo = self.algod_client.pending_transaction_info(tx_id)
                if txinfo.get("confirmed-round") and txinfo.get("confirmed-round") > 0:
                    logger.info(f"Transaction {tx_id} confirmed in round {txinfo.get('confirmed-round')}")
                    return txinfo
                self.algod_client.status_after_block(last_round + 1)
                last_round += 1
            except AlgodHTTPError as e:
                if 'not found' in str(e).lower():
                    pass
        raise TimeoutError(f"Transaction {tx_id} not confirmed")

    async def fund_account_for_opt_in(self, user_address: str) -> Optional[str]:
        """Fund new account with minimum balance for opt-in"""
        try:
            min_balance = 100000  # 0.1 ALGO base
            asset_opt_in_fee = 100000  # 0.1 ALGO per asset
            total_funding = min_balance + asset_opt_in_fee
            
            params = self.algod_client.suggested_params()
            txn = PaymentTxn(
                sender=self.treasury_address,
                sp=params,
                receiver=user_address,
                amt=total_funding,
                note=b"Seamount Account Funding"
            )
            
            signed_txn = txn.sign(self.treasury_private_key)
            tx_id = self.algod_client.send_transaction(signed_txn)
            await self.wait_for_confirmation(tx_id)
            
            logger.info(f"Funded {user_address} with {total_funding} microAlgos")
            return tx_id
        except Exception as e:
            logger.error(f"Account funding failed: {e}")
            raise

    async def prepare_payment_txn(self, sender: str, receiver: str, amount: Decimal) -> Dict[str, Any]:
        """Prepare ALGO payment transaction"""
        try:
            params = self.algod_client.suggested_params()
            amount_microalgos = int(amount * 1_000_000)
            
            txn = PaymentTxn(sender=sender, sp=params, receiver=receiver, amt=amount_microalgos)
            unsigned_txn_b64 = encoding.msgpack_encode(txn)
            
            return {
                "success": True,
                "unsigned_txn_b64": unsigned_txn_b64,
                "tx_id": txn.get_txid(),
                "amount": float(amount)
            }
        except Exception as e:
            logger.error(f"Failed to prepare payment: {e}")
            raise

    async def prepare_asset_transfer_txn(
        self, sender: str, receiver: str, asset_id: int, amount: Decimal
    ) -> Dict[str, Any]:
        """Prepare asset transfer transaction"""
        try:
            asset_config = self._get_asset_config(asset_id)
            decimals = asset_config['decimals']
            
            params = self.algod_client.suggested_params()
            amount_base_units = int(amount * (10 ** decimals))
            
            txn = AssetTransferTxn(
                sender=sender, sp=params, receiver=receiver, amt=amount_base_units, index=asset_id
            )
            
            unsigned_txn_b64 = encoding.msgpack_encode(txn)
            
            return {
                "success": True,
                "unsigned_txn_b64": unsigned_txn_b64,
                "tx_id": txn.get_txid(),
                "asset_id": asset_id,
                "amount": float(amount)
            }
        except Exception as e:
            logger.error(f"Failed to prepare asset transfer: {e}")
            raise

    async def submit_transaction(self, signed_txn: str) -> str:
        """Submit signed transaction to network"""
        try:
            tx_id = self.algod_client.send_raw_transaction(signed_txn)
            await self.wait_for_confirmation(tx_id)
            logger.info(f"Transaction confirmed: {tx_id}")
            return tx_id
        except Exception as e:
            logger.error(f"Transaction submission failed: {e}")
            raise

    async def check_asset_opt_in(self, address: str, asset_id: int) -> bool:
        """Check if address is opted into asset"""
        try:
            account_info = await self.get_account_info(address)
            if not account_info:
                return False
            assets = account_info.get('assets', [])
            return any(asset['asset-id'] == asset_id for asset in assets)
        except Exception as e:
            logger.error(f"Opt-in check failed: {e}")
            return False
        
    async def mint_usdt(self, user_id: str, amount: Decimal, reference: str) -> Dict:
        """Mint USDT to user's Algorand wallet"""
    
    # Get user's wallet address
    wallet_data = await self.db_service.get_user_wallet(user_id)
    recipient_address = wallet_data['algorand_address']
    
    # USDT Asset ID on Algorand Mainnet
    USDT_ASSET_ID = 312769  # Actual Algorand USDT asset
    
    # Transfer USDT from treasury to user
    txn = AssetTransferTxn(
        sender=self.treasury_address,
        sp=self.algod_client.suggested_params(),
        receiver=recipient_address,
        amt=int(amount * 1_000_000),  # 6 decimals
        index=USDT_ASSET_ID
    )
    
    signed_txn = txn.sign(self.treasury_private_key)
    tx_id = self.algod_client.send_transaction(signed_txn)
    
    # Wait for confirmation
    wait_for_confirmation(self.algod_client, tx_id, 4)
    
    return {"txn_id": tx_id, "amount": float(amount)}