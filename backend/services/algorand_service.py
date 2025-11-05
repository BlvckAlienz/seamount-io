# File: backend/services/algorand_service.py
# PRODUCTION READY - All duplicates removed

import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime

from algosdk import account, mnemonic, transaction, encoding
from algosdk.v2client import algod, indexer
from algosdk.error import AlgodHTTPError
from algosdk.transaction import AssetTransferTxn, PaymentTxn, AssetOptInTxn
from algokit import AlgorandClient
from algokit_utils import AccountManager

from backend.config import settings

logger = logging.getLogger(__name__)

class AlgorandService:
    def __init__(self, settings=None):
        """Initialize Algorand service with optional settings"""
        from backend.config import get_settings
        
        self.settings = settings or get_settings()
        
        # Initialize AlgoKit client (mainnet by default)
        network = getattr(self.settings, 'ALGORAND_NETWORK', 'mainnet')
        if network == 'testnet':
            self.client = AlgorandClient.testnet()
        elif network == 'localnet':
            self.client = AlgorandClient.localnet()
        else:
            self.client = AlgorandClient.mainnet()
        
        # Initialize direct algod client for advanced operations
        algod_address = getattr(self.settings, 'ALGORAND_ALGOD_ADDRESS', 'https://mainnet-api.algonode.cloud')
        algod_token = getattr(self.settings, 'ALGORAND_ALGOD_TOKEN', None)
        
        self.algod_client = algod.AlgodClient(
            algod_token=algod_token.get_secret_value() if hasattr(algod_token, 'get_secret_value') else (algod_token or ""),
            algod_address=algod_address
        )
        
        logger.info(f"✅ AlgorandService initialized for {network}")
        
    async def send_algo(self, sender_key: str, recipient: str, amount: int):
        """Send ALGO to recipient"""
        result = await self.client.transactions.payment({
            'sender': sender_key,
            'receiver': recipient,
            'amount': amount  # microAlgos
        })
        return result.tx_id
    
    async def send_usdt(self, sender_key: str, recipient: str, amount: int):
        """Send USDT (ASA) on Algorand"""
        # USDT ASA ID: 312769 (mainnet)
        result = await self.client.transactions.asset_transfer({
            'sender': sender_key,
            'receiver': recipient,
            'asset_id': 312769,
            'amount': amount
        })
        return result.tx_id

    async def create_algorand_wallet(self, user_id: str) -> Dict[str, Any]:
        """Create new Algorand wallet for user - NO TEST FUNDING"""
        try:
            from backend.services.seed_encryption_service import SeedEncryptionService
            
            private_key, address = account.generate_account()
            mnemonic_phrase = mnemonic.from_private_key(private_key)
            
            logger.info(f"Generated Algorand wallet: {address[:10]}...")
            logger.info(f"✅ Wallet created (no test funding): {address[:10]}...")
            
            encryption_service = SeedEncryptionService()
            encrypted_private_key = encryption_service.encrypt_seed(private_key)
            encrypted_mnemonic = encryption_service.encrypt_seed(mnemonic_phrase)
            
            logger.info(f"✅ Algorand seeds encrypted (mnemonic length: {len(encrypted_mnemonic)})")
            
            return {
                'wallet_address': address,
                'encrypted_private_key': encrypted_private_key,
                'encrypted_mnemonic': encrypted_mnemonic,
                'created_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Algorand wallet creation failed for user {user_id}: {e}")
            raise Exception(f"Failed to create Algorand wallet: {str(e)}")

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
        """🆕 DISABLED: Funding removed for production"""
        logger.info(f"🆕 Funding disabled for production: {user_address[:10]}...")
        return None

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