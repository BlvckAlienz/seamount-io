# File: backend/services/algorand_service.py
# PRODUCTION READY - No AlgorandClient dependency

import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime

from algosdk import account, mnemonic, encoding
from algosdk.v2client import algod
from algosdk.error import AlgodHTTPError
from algosdk.transaction import AssetTransferTxn, PaymentTxn, AssetOptInTxn

logger = logging.getLogger(__name__)

class AlgorandService:
    def __init__(self, settings=None):
        """Initialize Algorand service"""
        from backend.config import get_settings
        
        self.settings = settings or get_settings()
        
        network = getattr(self.settings, 'ALGORAND_NETWORK', 'mainnet')
        algod_address = getattr(self.settings, 'ALGORAND_ALGOD_ADDRESS', 'https://mainnet-api.algonode.cloud')
        algod_token = getattr(self.settings, 'ALGORAND_ALGOD_TOKEN', None)
        
        self.algod_client = algod.AlgodClient(
            algod_token=algod_token.get_secret_value() if hasattr(algod_token, 'get_secret_value') else (algod_token or ""),
            algod_address=algod_address
        )
        
        logger.info(f"✅ AlgorandService initialized for {network}")
        
    async def send_algo(self, sender_key: str, recipient: str, amount: int):
        """Send ALGO"""
        try:
            params = self.algod_client.suggested_params()
            sender_address = account.address_from_private_key(sender_key)
            
            txn = PaymentTxn(sender=sender_address, sp=params, receiver=recipient, amt=amount)
            signed_txn = txn.sign(sender_key)
            tx_id = self.algod_client.send_transaction(signed_txn)
            await self.wait_for_confirmation(tx_id)
            
            return tx_id
        except Exception as e:
            logger.error(f"ALGO transfer failed: {e}")
            raise
    
    async def send_usdt(self, sender_key: str, recipient: str, amount: int):
        """Send USDT"""
        return await self.transfer_asset(
            sender_private_key=sender_key,
            receiver_address=recipient,
            asset_id=312769,
            amount=Decimal(amount) / Decimal(1_000_000)
        )

    async def create_algorand_wallet(self, user_id: str) -> Dict[str, Any]:
        """Create wallet"""
        try:
            from backend.services.seed_encryption_service import SeedEncryptionService
            
            private_key, address = account.generate_account()
            mnemonic_phrase = mnemonic.from_private_key(private_key)
            
            encryption_service = SeedEncryptionService()
            encrypted_private_key = encryption_service.encrypt_seed(private_key)
            encrypted_mnemonic = encryption_service.encrypt_seed(mnemonic_phrase)
            
            return {
                'wallet_address': address,
                'encrypted_private_key': encrypted_private_key,
                'encrypted_mnemonic': encrypted_mnemonic,
                'created_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Wallet creation failed: {e}")
            raise

    async def get_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account info"""
        try:
            return self.algod_client.account_info(address)
        except AlgodHTTPError as e:
            if "account not found" in str(e).lower():
                return None
            raise

    async def get_asset_balance(self, address: str, asset_id: int) -> Decimal:
        """Get asset balance"""
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

    async def transfer_asset(self, sender_private_key: str, receiver_address: str, 
                        asset_id: int, amount: Decimal, memo: str = "") -> str:
        """Transfer asset (handles both ALGO and ASA tokens) with comprehensive validation"""
        try:
            # ✅ STEP 1: Validate receiver address FIRST
            if not encoding.is_valid_address(receiver_address):
                error_msg = f"Invalid receiver address: {receiver_address}"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            logger.info(f"✅ Receiver address validated: {receiver_address[:10]}...")
            
            # ✅ STEP 1.5: Check if receiver account exists and enforce minimum for new accounts
            try:
                receiver_info = await self.get_account_info(receiver_address)
                
                if receiver_info is None:
                    # Account doesn't exist yet
                    logger.warning(f"⚠️ Receiver account does not exist yet: {receiver_address[:10]}...")
                    
                    if asset_id == 0:  # Native ALGO transfer
                        # Enforce 0.1 ALGO minimum for account creation
                        MIN_ACCOUNT_BALANCE = Decimal("0.1")
                        
                        if amount < MIN_ACCOUNT_BALANCE:
                            error_msg = (
                                f"Cannot create new account with {amount} ALGO. "
                                f"Algorand requires minimum {MIN_ACCOUNT_BALANCE} ALGO to activate a new account. "
                                f"Please send at least {MIN_ACCOUNT_BALANCE} ALGO for the first transaction."
                            )
                            logger.error(f"❌ {error_msg}")
                            raise ValueError(error_msg)
                        
                        logger.info(f"✅ Amount {amount} ALGO meets minimum for new account creation")
                    else:
                        # ASA transfer to non-existent account
                        error_msg = (
                            f"Cannot send asset {asset_id} to non-existent account. "
                            f"Receiver must first activate their account with at least 0.1 ALGO."
                        )
                        logger.error(f"❌ {error_msg}")
                        raise ValueError(error_msg)
                else:
                    logger.info(f"✅ Receiver account exists with balance: {receiver_info.get('amount', 0) / 1_000_000} ALGO")
                    
            except ValueError:
                # Re-raise validation errors
                raise
            except Exception as receiver_check_err:
                # Non-critical: if we can't check receiver, proceed anyway
                logger.warning(f"⚠️ Could not verify receiver account status: {receiver_check_err}")
                logger.info("⏭️ Proceeding with transaction anyway...")
                
            # ✅ STEP 2: Get asset config and derive sender address
            asset_config = self._get_asset_config(asset_id)
            decimals = asset_config['decimals']
            
            # Derive sender address from private key
            try:
                sender_address = encoding.encode_address(
                    encoding.decode_address(
                        account.address_from_private_key(sender_private_key)
                    )
                )
                logger.info(f"✅ Sender address derived: {sender_address[:10]}...")
            except Exception as addr_err:
                logger.error(f"❌ Failed to derive sender address: {addr_err}")
                raise ValueError(f"Invalid private key format: {addr_err}")
            
            # ✅ STEP 3: Validate sender address
            if not encoding.is_valid_address(sender_address):
                error_msg = f"Derived sender address is invalid: {sender_address}"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            # ✅ STEP 4: Get network params
            params = self.algod_client.suggested_params()
            
            # ✅ STEP 5: Convert amount to base units
            amount_base_units = int(amount * (10**decimals))
            logger.info(f"💰 Amount: {amount} {asset_config.get('unit_name')} = {amount_base_units} base units")
            
            # ✅ STEP 6: Prepare memo/note properly
            note_bytes = None
            if memo and len(memo.strip()) > 0:
                note_bytes = memo.encode('utf-8')
                logger.info(f"📝 Memo attached: {memo[:20]}...")
            
            # ✅ STEP 7: Create appropriate transaction type
            if asset_id == 0:
                # Native ALGO transfer
                logger.info(f"💰 Creating PaymentTxn for {amount} ALGO")
                txn = PaymentTxn(
                    sender=sender_address,
                    sp=params,
                    receiver=receiver_address,
                    amt=amount_base_units,
                    note=note_bytes
                )
            else:
                # ASA token transfer
                logger.info(f"🪙 Creating AssetTransferTxn for asset {asset_id}")
                txn = AssetTransferTxn(
                    sender=sender_address,
                    sp=params,
                    receiver=receiver_address,
                    amt=amount_base_units,
                    index=asset_id,
                    note=note_bytes
                )
            
            # ✅ STEP 8: Sign transaction
            logger.info(f"✍️ Signing transaction...")
            signed_txn = txn.sign(sender_private_key)
            
            # ✅ STEP 9: Send transaction
            logger.info(f"📤 Broadcasting transaction to network...")
            tx_id = self.algod_client.send_transaction(signed_txn)
            logger.info(f"🚀 Transaction broadcast: {tx_id}")
            
            # ✅ STEP 10: Wait for confirmation
            logger.info(f"⏳ Waiting for confirmation...")
            confirmation = await self.wait_for_confirmation(tx_id)
            
            logger.info(f"✅ Transaction confirmed in round {confirmation.get('confirmed-round')}: {tx_id}")
            return tx_id
            
        except ValueError as val_err:
            # Validation errors (address, amount, etc.)
            logger.error(f"❌ Validation error: {val_err}")
            raise
        except Exception as e:
            # Catch-all for SDK errors
            logger.error(f"❌ Transaction failed: {type(e).__name__}: {str(e)}")
            raise Exception(f"Algorand transaction failed: {str(e)}")

    async def prepare_asset_opt_in(self, user_address: str, asset_id: int) -> Dict[str, Any]:
        """Prepare opt-in"""
        try:
            if not account.is_valid_address(user_address):
                raise ValueError("Invalid address")
            
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
            logger.error(f"Opt-in prep failed: {e}")
            raise

    def _get_asset_config(self, asset_id: int) -> Dict:
        """Get asset config"""
        for asset_key, config in self.settings.SUPPORTED_ASSETS.items():
            if config.get('asset_id') == asset_id:
                return config
        raise ValueError(f"Asset {asset_id} not configured")

    async def wait_for_confirmation(self, tx_id: str) -> Dict[str, Any]:
        """Wait for confirmation"""
        last_round = self.algod_client.status().get("last-round")
        
        for _ in range(10):
            try:
                txinfo = self.algod_client.pending_transaction_info(tx_id)
                if txinfo.get("confirmed-round", 0) > 0:
                    return txinfo
                self.algod_client.status_after_block(last_round + 1)
                last_round += 1
            except AlgodHTTPError:
                pass
        raise TimeoutError(f"Transaction {tx_id} not confirmed")

    async def prepare_payment_txn(self, sender: str, receiver: str, amount: Decimal) -> Dict[str, Any]:
        """Prepare payment"""
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
            logger.error(f"Payment prep failed: {e}")
            raise

    async def prepare_asset_transfer_txn(self, sender: str, receiver: str, 
                                        asset_id: int, amount: Decimal) -> Dict[str, Any]:
        """Prepare asset transfer"""
        try:
            asset_config = self._get_asset_config(asset_id)
            decimals = asset_config['decimals']
            
            params = self.algod_client.suggested_params()
            amount_base_units = int(amount * (10 ** decimals))
            
            txn = AssetTransferTxn(
                sender=sender, sp=params, receiver=receiver, 
                amt=amount_base_units, index=asset_id
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
            logger.error(f"Asset transfer prep failed: {e}")
            raise

    async def submit_transaction(self, signed_txn: str) -> str:
        """Submit transaction"""
        try:
            tx_id = self.algod_client.send_raw_transaction(signed_txn)
            await self.wait_for_confirmation(tx_id)
            return tx_id
        except Exception as e:
            logger.error(f"Transaction submit failed: {e}")
            raise

    async def check_asset_opt_in(self, address: str, asset_id: int) -> bool:
        """Check opt-in"""
        try:
            account_info = await self.get_account_info(address)
            if not account_info:
                return False
            assets = account_info.get('assets', [])
            return any(asset['asset-id'] == asset_id for asset in assets)
        except Exception as e:
            logger.error(f"Opt-in check failed: {e}")
            return False