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

from backend.services.seed_encryption_service import SeedEncryptionService
encryption_service = SeedEncryptionService()

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
                
            # ============================================================================
            # STEP 2: Get asset config and NORMALIZE private key format
            # ============================================================================
            asset_config = self._get_asset_config(asset_id)
            decimals = asset_config['decimals']
            
            # 🔧 CRITICAL: Algorand SDK requires Base64-encoded private keys
            # Convert hex to Base64 if needed
            import base64
            import re
            
            private_key_to_use = sender_private_key
            
            # Detect if it's hex format (64 chars, 0-9a-f)
            if len(sender_private_key) == 64 and re.match(r'^[0-9a-fA-F]{64}$', sender_private_key):
                logger.info(f"🔑 Detected hex private key, converting to Base64...")
                try:
                    # Convert hex to bytes, then to Base64
                    key_bytes = bytes.fromhex(sender_private_key)
                    if len(key_bytes) != 32:
                        raise ValueError(f"Hex key decoded to {len(key_bytes)} bytes, expected 32")
                    private_key_to_use = base64.b64encode(key_bytes).decode('utf-8')
                    logger.info(f"✅ Converted hex → Base64 ({len(private_key_to_use)} chars)")
                except Exception as conv_err:
                    logger.error(f"❌ Hex to Base64 conversion failed: {conv_err}")
                    raise ValueError(f"Failed to convert hex key: {conv_err}")
            else:
                logger.info(f"🔑 Using private key as-is (assumed Base64, {len(private_key_to_use)} chars)")
            
            # Derive sender address from private key
            try:
                sender_address = account.address_from_private_key(private_key_to_use)
                
                # Validate address
                if not encoding.is_valid_address(sender_address):
                    raise ValueError(f"Derived address is invalid: {sender_address}")
                
                logger.info(f"✅ Sender address derived: {sender_address[:10]}...")
                
            except Exception as addr_err:
                logger.error(f"❌ Failed to derive sender address: {addr_err}")
                logger.error(f"   Original key length: {len(sender_private_key)} chars")
                logger.error(f"   Converted key length: {len(private_key_to_use)} chars")
                raise ValueError(f"Invalid private key format: {addr_err}")
            
            # ============================================================================
            # STEP 3: Validate sender address
            # ============================================================================
            if not encoding.is_valid_address(sender_address):
                error_msg = f"Derived sender address is invalid: {sender_address}"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            # ============================================================================
            # STEP 4: Get network params
            # ============================================================================
            params = self.algod_client.suggested_params()
            
            # ============================================================================
            # STEP 5: Convert amount to base units
            # ============================================================================
            amount_base_units = int(amount * (10**decimals))
            logger.info(f"💰 Amount: {amount} {asset_config.get('unit_name')} = {amount_base_units} base units")
            
            # ============================================================================
            # STEP 6: Prepare memo/note properly
            # ============================================================================
            note_bytes = None
            if memo and len(memo.strip()) > 0:
                note_bytes = memo.encode('utf-8')
                logger.info(f"📝 Memo attached: {memo[:20]}...")
            
            # ============================================================================
            # STEP 7: Create appropriate transaction type
            # ============================================================================
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
            
            # ============================================================================
            # STEP 8: Sign transaction (use converted Base64 key)
            # ============================================================================
            logger.info(f"✍️ Signing transaction...")
            signed_txn = txn.sign(private_key_to_use)  # ✅ Use Base64 format
            logger.info(f"✅ Transaction signed successfully")
            
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
    
    async def opt_in_asset(
        self,
        account_private_key: str,
        asset_id: int,
        is_encrypted: bool = True
    ) -> str:
        """
        Opt-in to an Algorand Standard Asset (ASA)
        
        Args:
            account_private_key: Private key (encrypted, mnemonic, or hex)
            asset_id: ASA ID to opt into
            is_encrypted: If False, key is already decrypted (skip decryption)
        
        Returns:
            Transaction ID
        """
        try:
            logger.info(f"🔄 Opting into ASA {asset_id}")
            
            # ✅ STEP 1: Determine if key needs decryption
            if is_encrypted:
                # Key might be encrypted - try to decrypt
                if len(account_private_key.split()) == 25:
                    # Already a 25-word mnemonic - use directly
                    logger.info(f"✅ Key already decrypted (25-word mnemonic)")
                    decrypted_key = account_private_key
                elif len(account_private_key) == 64 and all(c in '0123456789abcdef' for c in account_private_key.lower()):
                    # Already a 64-char hex private key - use directly
                    logger.info(f"✅ Key already decrypted (hex format)")
                    decrypted_key = account_private_key
                else:
                    # Looks encrypted - try to decrypt
                    try:
                        decrypted_key = encryption_service.decrypt_seed(account_private_key)
                        logger.info(f"✅ Successfully decrypted private key")
                    except Exception as decrypt_err:
                        # If decryption fails, maybe it's raw and use as-is
                        logger.warning(f"⚠️ Decryption failed, using key as-is: {decrypt_err}")
                        decrypted_key = account_private_key
            else:
                # ✅ Key is already decrypted - use directly
                logger.info(f"✅ Using pre-decrypted key (is_encrypted=False)")
                decrypted_key = account_private_key
            
            # ====================================================================
            # ✅ STEP 2: Convert to private key format (WITH PUBLIC KEY DERIVATION)
            # ====================================================================
            if len(decrypted_key.split()) == 25:
                # It's a mnemonic phrase
                private_key = mnemonic.to_private_key(decrypted_key)
                account_address = account.address_from_private_key(private_key)
                
            elif len(decrypted_key) == 64:
                # It's a 64-char hex private key (32 bytes)
                import base64
                from nacl.signing import SigningKey
                
                # Convert hex to bytes
                private_key_bytes = bytes.fromhex(decrypted_key)
                
                # ✅ CRITICAL: Derive public key from private key
                signing_key = SigningKey(private_key_bytes)
                verify_key = signing_key.verify_key
                public_key_bytes = bytes(verify_key)
                
                # Concatenate: private (32) + public (32) = 64 bytes
                full_key_bytes = private_key_bytes + public_key_bytes
                
                # Encode to Base64 (88 chars)
                private_key = base64.b64encode(full_key_bytes).decode('utf-8')
                
                # Derive address
                account_address = account.address_from_private_key(private_key)
                
                logger.info(f"✅ Derived public key for opt-in (Base64: {len(private_key)} chars)")
                
            else:
                raise ValueError(f"Invalid key format: expected 25-word mnemonic or 64-char hex key, got {len(decrypted_key)} chars")
            
        except Exception as e:
            logger.error(f"❌ ASA opt-in failed: {e}")
            raise Exception(f"ASA opt-in failed: {str(e)}")
    
    def _get_asset_config(self, asset_id: int) -> Dict:
        """
        Get asset config - supports both static (USDC/USDT) and dynamic (tokenized) assets
        """
        # First check static SUPPORTED_ASSETS
        for asset_key, config in self.settings.SUPPORTED_ASSETS.items():
            if config.get('asset_id') == asset_id:
                return config
        
        # 🆕 If not found, check if it's a dynamic tokenized asset
        logger.info(f"Asset {asset_id} not in SUPPORTED_ASSETS, checking tokenized_assets table...")
        
        try:
            from backend.dependencies import get_db_service
            db_service = get_db_service()
            
            # Query tokenized_assets table
            asset_result = db_service.supabase.table('tokenized_assets')\
                .select('*')\
                .eq('asset_id', asset_id)\
                .single()\
                .execute()
            
            if asset_result.data:
                # Return a config dict compatible with existing logic
                asset_data = asset_result.data
                logger.info(f"✅ Found dynamic asset: {asset_data['symbol']} (ASA {asset_id})")
                
                return {
                    'asset_id': asset_id,
                    'unit_name': asset_data['symbol'][:8],
                    'name': asset_data['name'],
                    'decimals': 0,  # Tokenized equities use whole numbers
                    'type': 'tokenized_equity'
                }
            else:
                raise ValueError(f"Asset {asset_id} not found in SUPPORTED_ASSETS or tokenized_assets")
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch dynamic asset config: {e}")
            raise ValueError(f"Asset {asset_id} not configured and DB lookup failed: {e}")

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
    
    async def get_account_info(self, address: str) -> Dict[str, Any]:
        """
        Get account information from Algorand
        
        Returns account balance, assets, etc.
        """
        try:
            account_info = self.algod_client.account_info(address)
            return account_info
        except Exception as e:
            logger.error(f"❌ Failed to get account info for {address}: {e}")
            return {}
    
    async def get_health(self) -> bool:
        """
        Check Algorand node health
        
        Returns:
            bool: True if node is healthy and responsive, False otherwise
        """
        try:
            # Query node status (lightweight health check)
            status = self.algod_client.status()
            
            # Verify we got a valid response with required fields
            if not status:
                logger.warning("⚠️ Algorand node returned empty status")
                return False
            
            # Check for last-round field (indicates node is syncing)
            last_round = status.get('last-round')
            if last_round is None or last_round <= 0:
                logger.warning(f"⚠️ Algorand node last-round invalid: {last_round}")
                return False
            
            logger.info(f"✅ Algorand node healthy (round {last_round})")
            return True
            
        except AlgodHTTPError as http_err:
            logger.error(f"❌ Algorand node HTTP error: {http_err}")
            return False
        except Exception as e:
            logger.error(f"❌ Algorand health check failed: {type(e).__name__}: {e}")
            return False

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