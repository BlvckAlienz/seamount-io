# File: backend/services/multi_chain_wallet_service.py
"""
Multi-Chain Wallet Service - PRODUCTION READY v2.0
✅ Fixed all duplications
✅ Removed unsupported chains (arbitrum, solana, ton)
✅ Added robust error handling
✅ Fixed asset key normalization
✅ Added comprehensive logging
"""

import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime

from backend.services.wdk_client import WDKClient
from backend.services.algorand_service import AlgorandService
from backend.services.database_service import DatabaseService
from backend.services.fee_calculator import FeeCalculatorService, TransactionType
from backend.services.oracle_service import OracleService
from backend.services.seed_encryption_service import SeedEncryptionService

logger = logging.getLogger(__name__)

class MultiChainWalletService:
    """
    Production-ready multi-chain wallet orchestrator
    Supports: Algorand, Bitcoin, Ethereum, Polygon, Tron (5 chains)
    """
    
    # ========== ASSET-TO-CHAIN MAPPING ==========
    ASSET_CHAIN_MAP = {
        # Native Algorand assets
        'ALGO': 'algorand',
        'USDCa': 'algorand',
        'goBTC': 'algorand',
        'goETH': 'algorand',
        
        # USDT variants (default to Tron for best liquidity)
        'USDT': 'tron',  # Default USDT routing
        'USDT_ALGO': 'algorand',
        'USDT_ETH': 'ethereum',
        'USDT_POLYGON': 'polygon',
        'USDT_TRON': 'tron',
        
        # Native chain assets
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'MATIC': 'polygon',
        'TRX': 'tron',
        
        # USDC variants
        'USDC_ETH': 'ethereum',
        'USDC_POLYGON': 'polygon'
    }
    
    # Algorand Asset IDs (ASA)
    ALGORAND_ASSET_IDS = {
        'ALGO': 0,
        'USDCa': 31566704,
        'USDT': 312769,
        'USDT_ALGO': 312769,
        'goBTC': 386192725,
        'goETH': 386195940
    }
    
    # Supported chains
    SUPPORTED_CHAINS = ['algorand', 'bitcoin', 'ethereum', 'polygon', 'tron']
    
    def __init__(self, db_service: DatabaseService, algorand_service: AlgorandService, 
                 fee_calculator: FeeCalculatorService, oracle_service: OracleService):
        self.db = db_service
        self.algorand = algorand_service
        self.fees = fee_calculator
        self.oracle = oracle_service
        self.wdk = WDKClient()
        
        logger.info("✅ MultiChainWalletService initialized")

    # ========== WALLET CREATION ==========
    
    def _get_user_address(self, user_id: str, chain: str) -> Optional[str]:
        """Retrieve user's wallet address for specific chain"""
        try:
            if chain == 'algorand':
                result = self.db.supabase.table('user_wallets')\
                    .select('algorand_address')\
                    .eq('user_id', user_id)\
                    .execute()
                if result.data and len(result.data) > 0:
                    return result.data[0].get('algorand_address')
            else:
                result = self.db.supabase.table('multi_chain_addresses')\
                    .select('address')\
                    .eq('user_id', user_id)\
                    .eq('blockchain', chain)\
                    .execute()
                if result.data and len(result.data) > 0:
                    return result.data[0].get('address')
            return None
        except Exception as e:
            logger.error(f"❌ Error getting user address for {chain}: {e}")
            return None

    async def create_single_chain_wallet(self, user_id: str, chain: str) -> Dict[str, Any]:
        """Create wallet for single chain"""
        try:
            # Check if wallet already exists
            existing_address = self._get_user_address(user_id, chain)
            if existing_address:
                logger.info(f"ℹ️ Wallet already exists for {chain}: {existing_address[:10]}...")
                return {
                    'success': True,
                    'address': existing_address,
                    'message': f'Wallet already exists on {chain}',
                    'chain': chain
                }
            
            if chain == 'algorand':
                # Create Algorand wallet
                algo_wallet = await self.algorand.create_algorand_wallet(user_id)
                algo_address = algo_wallet['wallet_address']
                
                # Store in database
                wallet_data = {
                    'user_id': user_id,
                    'algorand_address': algo_address,
                    'algorand_private_key': algo_wallet['encrypted_private_key'],
                    'algorand_mnemonic': algo_wallet['encrypted_mnemonic'],
                    'created_at': datetime.utcnow().isoformat()
                }
                
                self.db.supabase.table('user_wallets').upsert(
                    wallet_data, on_conflict='user_id'
                ).execute()
                
                logger.info(f"✅ Algorand wallet created: {algo_address[:10]}...")
                return {'success': True, 'address': algo_address, 'chain': chain}
            
            else:
                # Create WDK wallet (Bitcoin, Ethereum, Polygon, Tron)
                from mnemonic import Mnemonic
                
                # Generate plaintext seed
                mnemo = Mnemonic("english")
                plaintext_seed = mnemo.generate(strength=128)  # 12 words
                
                # Encrypt seed for storage
                encryption_service = SeedEncryptionService()
                encrypted_seed = encryption_service.encrypt_seed(plaintext_seed)
                
                logger.info(f"🔐 Generated and encrypted seed for {chain}")
                
                # Create wallet via WDK
                wdk_result = await self.wdk.create_wallet(
                    plaintext_seed=plaintext_seed,
                    chains=[chain],
                    enable_gasless=True
                )
                
                wallet_data = wdk_result.get('wallets', {}).get(chain)
                if not wallet_data:
                    raise Exception(f"WDK returned no wallet data for {chain}")
                
                # Store encrypted seed in database
                self.db.supabase.table('multi_chain_addresses').upsert({
                    'user_id': user_id,
                    'blockchain': chain,
                    'address': wallet_data['address'],
                    'encrypted_seed': encrypted_seed,
                    'wallet_type': 'wdk',
                    'created_at': datetime.utcnow().isoformat()
                }, on_conflict='user_id,blockchain').execute()
                
                logger.info(f"✅ {chain.upper()} wallet created: {wallet_data['address'][:10]}...")
                return {
                    'success': True,
                    'address': wallet_data['address'],
                    'chain': chain,
                    'created_at': wallet_data.get('created_at', datetime.utcnow().isoformat())
                }
                    
        except Exception as e:
            logger.error(f"❌ Single chain wallet creation failed for {chain}: {e}")
            return {'success': False, 'error': str(e), 'chain': chain}

    async def create_wallet_for_user(
        self,
        user_id: str,
        chains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create multi-chain wallet for user"""
        
        result = {
            'user_id': user_id,
            'wallets': {},
            'created_at': datetime.utcnow().isoformat(),
            'success': False,
            'errors': []
        }
        
        # 1. Create Algorand wallet (ALWAYS)
        try:
            algo_result = await self.create_single_chain_wallet(user_id, 'algorand')
            if algo_result['success']:
                result['wallets']['algorand'] = {
                    'address': algo_result['address'],
                    'created_at': algo_result.get('created_at', datetime.utcnow().isoformat()),
                    'supported_assets': ['ALGO', 'USDCa', 'USDT', 'goBTC', 'goETH']
                }
            else:
                raise Exception(algo_result.get('error', 'Algorand wallet creation failed'))
                
        except Exception as e:
            logger.error(f"❌ Algorand wallet failed: {e}")
            result['errors'].append(f"Algorand: {str(e)}")
            return result
        
        # 2. Determine WDK chains
        if chains:
            wdk_chains = [c for c in chains if c != 'algorand' and c in self.SUPPORTED_CHAINS]
        else:
            # Default: All supported WDK chains
            wdk_chains = ['bitcoin', 'ethereum', 'polygon', 'tron']
        
        # 3. Create WDK wallets sequentially
        for chain in wdk_chains:
            try:
                chain_result = await self.create_single_chain_wallet(user_id, chain)
                if chain_result['success']:
                    result['wallets'][chain] = {
                        'address': chain_result['address'],
                        'created_at': chain_result.get('created_at', datetime.utcnow().isoformat())
                    }
                    logger.info(f"✅ {chain.upper()} wallet: {chain_result['address'][:10]}...")
                else:
                    result['errors'].append(f"{chain}: {chain_result.get('error')}")
                    
            except Exception as e:
                logger.error(f"❌ {chain} wallet creation failed: {e}")
                result['errors'].append(f"{chain}: {str(e)}")
        
        result['total_chains'] = len(result['wallets'])
        result['success'] = len(result['wallets']) > 0
        
        return result

    # ========== BALANCE QUERIES ==========
    
    def _get_native_asset(self, chain: str) -> str:
        """Get native asset for chain"""
        native_map = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH',
            'polygon': 'MATIC',
            'tron': 'TRX',
            'algorand': 'ALGO'
        }
        return native_map.get(chain, 'UNKNOWN')

    async def get_user_balances(self, user_id: str) -> Dict[str, Any]:
        """Get unified balance view across ALL chains"""
        try:
            balances = {}
            total_usd = Decimal('0')
            
            # 1. Get Algorand balances
            try:
                algo_wallet = self.db.supabase.table('user_wallets')\
                    .select('algorand_address')\
                    .eq('user_id', user_id)\
                    .execute()
                
                if algo_wallet.data and len(algo_wallet.data) > 0:
                    algo_address = algo_wallet.data[0].get('algorand_address')
                    
                    if algo_address:
                        # Query Algorand account
                        account_info = await self.algorand.get_account_info(algo_address)
                        
                        if account_info:
                            # Native ALGO balance
                            algo_balance = Decimal(str(account_info.get('amount', 0))) / Decimal('1000000')
                            if algo_balance > 0:
                                try:
                                    algo_price = await self.oracle.get_algorand_price()
                                    balances['ALGO'] = {
                                        'balance': float(algo_balance),
                                        'chain': 'algorand',
                                        'usd_value': float(algo_balance * algo_price)
                                    }
                                    total_usd += algo_balance * algo_price
                                except Exception as price_err:
                                    logger.warning(f"⚠️ Price lookup failed for ALGO: {price_err}")
                                    balances['ALGO'] = {
                                        'balance': float(algo_balance),
                                        'chain': 'algorand',
                                        'usd_value': 0.0
                                    }
            
            except Exception as algo_err:
                logger.warning(f"⚠️ Algorand balance query failed: {algo_err}")
            
            # 2. Get WDK chain balances
            try:
                wdk_wallets = self.db.supabase.table('multi_chain_addresses')\
                    .select('blockchain, address')\
                    .eq('user_id', user_id)\
                    .execute()
                
                if wdk_wallets.data and len(wdk_wallets.data) > 0:
                    for wallet in wdk_wallets.data:
                        chain = wallet['blockchain']
                        address = wallet['address']
                        
                        try:
                            # Query balance from WDK
                            balance_data = await self.wdk.get_balance(address, chain)
                            balance = Decimal(str(balance_data.get('balance', 0)))
                            
                            if balance > 0:
                                native_asset = self._get_native_asset(chain)
                                
                                try:
                                    # Get price from oracle
                                    price = await self.oracle.get_asset_price(native_asset.lower())
                                    usd_value = balance * price
                                    
                                    balances[native_asset] = {
                                        'balance': float(balance),
                                        'chain': chain,
                                        'usd_value': float(usd_value)
                                    }
                                    total_usd += usd_value
                                    
                                except Exception as price_error:
                                    logger.warning(f"⚠️ Price lookup failed for {chain}: {price_error}")
                                    balances[native_asset] = {
                                        'balance': float(balance),
                                        'chain': chain,
                                        'usd_value': 0.0
                                    }
                        
                        except Exception as balance_err:
                            logger.error(f"❌ Balance query failed for {chain}: {balance_err}")
                            continue
            
            except Exception as wdk_err:
                logger.warning(f"⚠️ WDK balance query failed: {wdk_err}")
            
            # 3. Format response
            assets_list = sorted(
                balances.values(),
                key=lambda x: x.get('usd_value', 0),
                reverse=True
            )
            
            return {
                'success': True,
                'total_usd': float(total_usd),
                'assets': assets_list,
                'asset_count': len(balances),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Balance query failed: {e}")
            return {
                'success': False,
                'total_usd': 0.0,
                'assets': [],
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    # ========== SEND PAYMENT ==========
    
    async def send_payment(
        self,
        user_id: str,
        recipient: str,
        asset: str,
        amount: Decimal,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send payment with auto-routing"""
        
        try:
            # ✅ Validate inputs
            if not asset or len(asset.strip()) == 0:
                raise Exception("Asset cannot be empty")
            
            if amount <= 0:
                raise Exception(f"Amount must be positive, got: {amount}")
            
            if not recipient or len(recipient.strip()) < 20:
                raise Exception("Invalid recipient address format")
            
            logger.info(f"💸 Initiating send: {amount} {asset} to {recipient[:10]}...")
            
            # Auto-route to optimal chain
            optimal_chain = await self.auto_route_transaction(asset, amount, recipient)
            logger.info(f"🔀 Auto-routed {asset} to {optimal_chain}")
            
            # Calculate fees
            fee_calc = await self.fees.calculate_transaction_fee(
                transaction_type=TransactionType.P2P_LOCAL,
                amount=amount,
                user_id=user_id,
                from_asset=asset,
                to_asset=asset
            )
            
            # Execute transaction
            if optimal_chain == 'algorand':
                result = await self._send_via_algorand(user_id, recipient, asset, amount, memo)
            else:
                result = await self._send_via_wdk(user_id, recipient, asset, amount, optimal_chain)
            
            # Record transaction - mapped to existing schema
            try:
                transaction_data = {
                    'user_id': user_id,
                    'transaction_type': 'transfer',
                    'status': 'completed',
                    'amount': float(amount),
                    'currency': asset,
                    'to_address': recipient,
                    'algorand_txn_id': result['tx_id'],
                    'fee_amount': float(fee_calc['total_fee']),
                    'fee_currency': 'USD',
                    'created_at': datetime.utcnow().isoformat(),
                    'metadata': {
                        'chain': optimal_chain,
                        'asset': asset,
                        'memo': memo if memo else None,
                        'estimated_arrival': self._estimate_arrival_time(optimal_chain)
                    }
                }
                
                # ✅ Supabase client is synchronous, don't use await
                response = self.db.supabase.table('transactions').insert(transaction_data).execute()
                
                if response.data:
                    logger.info(f"✅ Transaction recorded in database: {result['tx_id']} ({asset} on {optimal_chain})")
                else:
                    logger.warning(f"⚠️ Transaction insert returned no data (but may have succeeded)")
                
            except Exception as db_err:
                # Non-fatal: blockchain transaction succeeded, just logging failed
                logger.error(f"❌ Database logging failed (transaction still succeeded on chain): {db_err}")
            
            return {
                'success': True,
                'message': f'Payment sent! Your {asset} will arrive shortly. ✓',
                'transaction_id': result['tx_id'],
                'amount': float(amount),
                'asset': asset,
                'fee': float(fee_calc['total_fee']),
                'estimated_arrival': self._estimate_arrival_time(optimal_chain)
            }
            
        except Exception as e:
            logger.error(f"❌ Payment failed: {e}")
            return {
                'success': False,
                'message': 'Payment failed. Please try again.',
                'error': str(e)
            }
    
    # ========== HELPER METHODS ==========
    
    async def auto_route_transaction(self, asset: str, amount: Decimal, recipient: str) -> str:
        """
        Smart chain selection for 5 supported chains
        Updated to remove unsupported chains (arbitrum, solana, ton)
        """
        
        logger.info(f"🔀 Auto-routing: {asset} (amount: {amount})")
        
        # ✅ Handle chain-suffixed assets first (e.g., USDT_ETH → ethereum)
        if "_" in asset:
            parts = asset.split("_")
            chain_suffix = parts[1].lower()
            
            chain_map = {
                "algo": "algorand",
                "eth": "ethereum",
                "polygon": "polygon",
                "tron": "tron"
            }
            
            routed_chain = chain_map.get(chain_suffix)
            if routed_chain:
                logger.info(f"✅ Routed {asset} → {routed_chain} (explicit chain suffix)")
                return routed_chain
        
        # Native Algorand assets
        if asset in ['ALGO', 'USDCa', 'goBTC', 'goETH']:
            logger.info(f"✅ Routed {asset} → algorand (native)")
            return 'algorand'
        
        # Bitcoin
        if asset == 'BTC':
            logger.info(f"✅ Routed {asset} → bitcoin")
            return 'bitcoin'
        
        # Ethereum
        if asset == 'ETH':
            logger.info(f"✅ Routed {asset} → ethereum")
            return 'ethereum'
        
        # Polygon
        if asset == 'MATIC':
            logger.info(f"✅ Routed {asset} → polygon")
            return 'polygon'
        
        # Tron
        if asset == 'TRX':
            logger.info(f"✅ Routed {asset} → tron")
            return 'tron'
        
        # ✅ USDT routing (optimized for 5 chains only)
        if asset == 'USDT':
            if amount < Decimal('500'):
                logger.info(f"✅ Routed USDT → polygon (gasless, amount < $500)")
                return 'polygon'  # Gasless for small amounts
            elif amount < Decimal('5000'):
                logger.info(f"✅ Routed USDT → tron (low cost, amount < $5000)")
                return 'tron'  # Low fees
            else:
                logger.info(f"✅ Routed USDT → tron (best liquidity, amount ≥ $5000)")
                return 'tron'  # Best for large amounts
        
        # Fallback to ASSET_CHAIN_MAP
        fallback_chain = self.ASSET_CHAIN_MAP.get(asset, 'algorand')
        logger.warning(f"⚠️ Using fallback routing: {asset} → {fallback_chain}")
        return fallback_chain
    
    async def _send_via_algorand(
        self, 
        user_id: str, 
        recipient: str, 
        asset: str, 
        amount: Decimal, 
        memo: Optional[str]
    ) -> Dict:
        """Send transaction via Algorand"""
        
        # Get wallet credentials
        wallet = self.db.supabase.table('user_wallets')\
            .select('algorand_address, algorand_private_key')\
            .eq('user_id', user_id)\
            .execute()
        
        if not wallet.data or len(wallet.data) == 0:
            raise Exception("Algorand wallet not found")
        
        # ✅ FIX: Decrypt private key before using
        from backend.services.seed_encryption_service import SeedEncryptionService
        encryption_service = SeedEncryptionService()
        
        encrypted_key = wallet.data[0]['algorand_private_key']
        try:
            decrypted_private_key = encryption_service.decrypt_seed(encrypted_key)
            logger.info(f"🔓 Successfully decrypted private key for user {user_id}")
        except Exception as decrypt_err:
            logger.error(f"❌ Private key decryption failed: {decrypt_err}")
            raise Exception(f"Failed to decrypt wallet credentials: {decrypt_err}")
        
        # ✅ Handle both plain and chain-suffixed asset keys
        lookup_key = asset.split('_')[0] if '_' in asset else asset
        asset_id = self.ALGORAND_ASSET_IDS.get(lookup_key)
        
        if asset_id is None:
            available_assets = ', '.join(self.ALGORAND_ASSET_IDS.keys())
            error_msg = f"Asset '{asset}' not supported on Algorand. Available: {available_assets}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        logger.info(f"📍 Sending {amount} {asset} (ASA ID: {asset_id}) on Algorand")
        
        # Execute transaction with DECRYPTED key
        tx_id = await self.algorand.transfer_asset(
            sender_private_key=decrypted_private_key,  # ✅ NOW USING DECRYPTED KEY
            receiver_address=recipient,
            asset_id=asset_id,
            amount=amount,
            memo=memo or ""
        )
        
        return {'tx_id': tx_id, 'chain': 'algorand'}
    
    async def _send_via_wdk(
        self, 
        user_id: str, 
        recipient: str, 
        asset: str, 
        amount: Decimal, 
        chain: str
    ) -> Dict:
        """Send transaction via WDK chains"""
        
        # Get wallet credentials
        wallet = self.db.supabase.table('multi_chain_addresses')\
            .select('address, encrypted_seed')\
            .eq('user_id', user_id)\
            .eq('blockchain', chain)\
            .execute()
        
        if not wallet.data or len(wallet.data) == 0:
            raise Exception(f"Wallet not found on {chain}")
        
        logger.info(f"📍 Sending {amount} {asset} via WDK on {chain}")
        
        # Execute transaction
        result = await self.wdk.send_transaction(
            from_address=wallet.data[0]['address'],
            to_address=recipient,
            amount=amount,
            asset=asset,
            chain=chain,
            encrypted_seed=wallet.data[0]['encrypted_seed'],
            enable_gasless=True
        )
        
        return {'tx_id': result['tx_id'], 'chain': chain}
    
    def _estimate_arrival_time(self, chain: str) -> str:
        """Estimate transaction arrival time"""
        times = {
            'algorand': '4.5 seconds',
            'bitcoin': '10-60 minutes',
            'ethereum': '12 seconds',
            'polygon': '2 seconds',
            'tron': '3 seconds'
        }
        return times.get(chain, '1-5 minutes')