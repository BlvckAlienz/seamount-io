# File: backend/services/multi_chain_wallet_service.py
"""
Multi-Chain Wallet Service - PRODUCTION READY v2.0
âœ… Fixed all duplications
âœ… Removed unsupported chains (arbitrum, ton)
âœ… Added Solana support
âœ… Added robust error handling
âœ… Fixed asset key normalization
âœ… Added comprehensive logging
"""

from itertools import chain
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
from backend.services.revenue_tracking_service import RevenueTrackingService

logger = logging.getLogger(__name__)

class MultiChainWalletService:
    """
    Production-ready multi-chain wallet orchestrator
    Supports: Algorand, Bitcoin, Ethereum, Polygon, Tron, Solana (6 chains)
    """
    
    # ========== ASSET-TO-CHAIN MAPPING ==========
    ASSET_CHAIN_MAP = {
        'RLUSD':    'xrp',
        'USDC_XRP': 'xrp',
        'XRP':      'xrp',

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
        'USDT_SOLANA': 'solana',  # NEW
        
        # Native chain assets
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'MATIC': 'polygon',
        'TRX': 'tron',
        'SOL': 'solana',  # NEW
        
        # USDC variants
        'USDC_ETH': 'ethereum',
        'USDC_POLYGON': 'polygon',
        'USDC_SOLANA': 'solana'  # NEW
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
    SUPPORTED_CHAINS = ['algorand', 'bitcoin', 'ethereum', 'polygon', 'tron', 'solana']
    
    def __init__(self, db_service: DatabaseService, algorand_service: AlgorandService, 
                 fee_calculator: FeeCalculatorService, oracle_service: OracleService):
        self.db = db_service
        self.algorand = algorand_service
        self.fees = fee_calculator
        self.oracle = oracle_service
        self.wdk = WDKClient()
        
        logger.info("âœ… MultiChainWalletService initialized")

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
            logger.error(f"âŒ Error getting user address for {chain}: {e}")
            return None

    async def create_single_chain_wallet(self, user_id: str, chain: str) -> Dict[str, Any]:
        """Create wallet for single chain"""
        try:
            # Check if wallet already exists
            existing_address = self._get_user_address(user_id, chain)
            if existing_address:
                logger.info(f"â„¹ï¸ Wallet already exists for {chain}: {existing_address[:10]}...")
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
                
                logger.info(f"âœ… Algorand wallet created: {algo_address[:10]}...")
                return {'success': True, 'address': algo_address, 'chain': chain}
            
            else:
                # Create WDK wallet (Bitcoin, Ethereum, Polygon, Tron, Solana)
                from mnemonic import Mnemonic
                
                # Generate plaintext seed
                mnemo = Mnemonic("english")
                plaintext_seed = mnemo.generate(strength=128)  # 12 words
                
                # Encrypt seed for storage
                encryption_service = SeedEncryptionService()
                encrypted_seed = encryption_service.encrypt_seed(plaintext_seed)
                
                logger.info(f"ðŸ” Generated and encrypted seed for {chain}")
                
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
                
                logger.info(f"âœ… {chain.upper()} wallet created: {wallet_data['address'][:10]}...")
                return {
                    'success': True,
                    'address': wallet_data['address'],
                    'chain': chain,
                    'created_at': wallet_data.get('created_at', datetime.utcnow().isoformat())
                }
                    
        except Exception as e:
            logger.error(f"âŒ Single chain wallet creation failed for {chain}: {e}")
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
            logger.error(f"âŒ Algorand wallet failed: {e}")
            result['errors'].append(f"Algorand: {str(e)}")
            return result
        
        # 2. Determine WDK chains
        if chains:
            wdk_chains = [c for c in chains if c != 'algorand' and c in self.SUPPORTED_CHAINS]
        else:
            # Default: All supported WDK chains
            wdk_chains = ['bitcoin', 'ethereum', 'polygon', 'tron', 'solana']
        
        # ðŸ” DEBUG LOGGING (temporary)
        logger.info(f"ðŸ” DEBUG: Input chains = {chains}")
        logger.info(f"ðŸ” DEBUG: self.SUPPORTED_CHAINS = {self.SUPPORTED_CHAINS}")
        logger.info(f"ðŸ” DEBUG: wdk_chains = {wdk_chains}")
        logger.info(f"ðŸ” DEBUG: About to create {len(wdk_chains)} WDK wallets")
        
        # 3. Create WDK wallets sequentially
        for chain in wdk_chains:
            try:
                logger.info(f"ðŸ”¨ ATTEMPTING {chain.upper()} wallet creation...")
                
                chain_result = await self.create_single_chain_wallet(user_id, chain)
                
                # ðŸš¨ CRITICAL: Log FULL response (not just success/fail)
                logger.info(f"ðŸ“¦ {chain.upper()} creation result: {chain_result}")
                
                if chain_result.get('success'):
                    result['wallets'][chain] = {
                        'address': chain_result['address'],
                        'created_at': chain_result.get('created_at', datetime.utcnow().isoformat())
                    }
                    logger.info(f"âœ… {chain.upper()} wallet: {chain_result['address'][:10]}...")
                else:
                    error_msg = chain_result.get('error', 'Unknown error')
                    logger.error(f"âŒ {chain.upper()} creation FAILED: {error_msg}")
                    result['errors'].append(f"{chain}: {error_msg}")
                    
                    # ðŸš¨ NEW: Raise exception if critical chain fails
                    if chain == 'solana' and chains and 'solana' in chains:
                        raise Exception(f"Solana wallet creation failed: {error_msg}")
                        
            except Exception as e:
                error_details = str(e)
                logger.error(f"âŒ {chain} wallet creation EXCEPTION: {error_details}")
                logger.error(f"   Exception type: {type(e).__name__}")
                logger.error(f"   Full traceback:", exc_info=True)
                
                result['errors'].append(f"{chain}: {error_details}")
                
                # ðŸš¨ NEW: Re-raise if explicitly requested chain
                if chains and chain in chains:
                    raise Exception(f"{chain.upper()} wallet creation failed: {error_details}")
        
        result['total_chains'] = len(result['wallets'])
        result['success'] = len(result['wallets']) > 0
        
        return result

    # ========== BALANCE QUERIES ==========

    # Which tokens to query per chain (beyond native asset)
    CHAIN_TOKEN_MAP = {
        'tron':     ['USDT'],
        'ethereum': ['USDT', 'USDC'],
        'polygon':  ['USDT', 'USDC'],
        'solana':   ['USDT', 'USDC'],
        'bitcoin':  [],  # No token support
    }

    def _get_native_asset(self, chain: str) -> str:
        """Get native asset for chain"""
        native_map = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH',
            'polygon': 'MATIC',
            'tron': 'TRX',
            'algorand': 'ALGO',
            'solana': 'SOL'
        }
        return native_map.get(chain, 'UNKNOWN')

    async def get_user_balances(self, user_id: str) -> Dict[str, Any]:
        """Get unified balance view across ALL chains (native + tokens)"""
        try:
            balances = {}
            total_usd = Decimal('0')

            # 1. Get Algorand balances (native + ASAs)
            try:
                algo_wallet = self.db.supabase.table('user_wallets')\
                    .select('algorand_address')\
                    .eq('user_id', user_id)\
                    .execute()

                if algo_wallet.data and len(algo_wallet.data) > 0:
                    algo_address = algo_wallet.data[0].get('algorand_address')

                    if algo_address:
                        account_info = await self.algorand.get_account_info(algo_address)

                        if account_info:
                            # --- Native ALGO ---
                            algo_balance = Decimal(str(account_info.get('amount', 0))) / Decimal('1000000')
                            try:
                                algo_price = await self.oracle.get_algorand_price()
                                balances['ALGO'] = {
                                    'asset': 'ALGO',
                                    'symbol': 'ALGO',
                                    'balance': float(algo_balance),
                                    'chain': 'algorand',
                                    'usd_value': float(algo_balance * algo_price)
                                }
                                total_usd += algo_balance * algo_price
                            except Exception as price_err:
                                logger.warning(f"⚠️ Price lookup failed for ALGO: {price_err}")
                                balances['ALGO'] = {
                                    'asset': 'ALGO',
                                    'symbol': 'ALGO',
                                    'balance': float(algo_balance),
                                    'chain': 'algorand',
                                    'usd_value': 0.0
                                }

                            # --- ASA Tokens (USDCa, USDT, goBTC, goETH) ---
                            asset_map = {
                                31566704: ('USDCa', 6),
                                312769: ('USDT', 6),
                                386192725: ('goBTC', 8),
                                386195940: ('goETH', 8)
                            }

                            for asset_info in account_info.get('assets', []):
                                asset_id = asset_info.get('asset-id')
                                amount_raw = Decimal(str(asset_info.get('amount', 0)))

                                if asset_id in asset_map:
                                    symbol, decimals = asset_map[asset_id]
                                    balance = amount_raw / (Decimal('10') ** decimals)

                                    if balance > 0:
                                        try:
                                            price, _ = await self.oracle.get_asset_price(symbol.lower())
                                            usd_value = balance * price
                                            balances[symbol] = {
                                                'asset': symbol,
                                                'symbol': symbol,
                                                'balance': float(balance),
                                                'chain': 'algorand',
                                                'usd_value': float(usd_value)
                                            }
                                            total_usd += usd_value
                                        except Exception as price_err:
                                            logger.warning(f"⚠️ Price lookup failed for {symbol}: {price_err}")
                                            balances[symbol] = {
                                                'asset': symbol,
                                                'symbol': symbol,
                                                'balance': float(balance),
                                                'chain': 'algorand',
                                                'usd_value': 0.0
                                            }
                                    else:
                                        # Include zero‑balance entries? (optional)
                                        pass

                        else:
                            logger.info(f"ℹ️ Algorand account {algo_address[:10]}... has 0 balance")
                            balances['ALGO'] = {
                                'asset': 'ALGO',
                                'symbol': 'ALGO',
                                'balance': 0.0,
                                'chain': 'algorand',
                                'usd_value': 0.0
                            }

            except Exception as algo_err:
                logger.warning(f"⚠️ Algorand balance query failed: {algo_err}")
                balances['ALGO'] = {
                    'asset': 'ALGO',
                    'symbol': 'ALGO',
                    'balance': 0.0,
                    'chain': 'algorand',
                    'usd_value': 0.0,
                    'error': str(algo_err)
                }

            # 2. Get WDK chain balances — NATIVE + TOKENS (unchanged)
            try:
                wdk_wallets = self.db.supabase.table('multi_chain_addresses')\
                    .select('blockchain, address')\
                    .eq('user_id', user_id)\
                    .execute()

                if wdk_wallets.data and len(wdk_wallets.data) > 0:
                    for wallet in wdk_wallets.data:
                        chain = wallet['blockchain']
                        address = wallet['address']

                        # Native asset
                        native_asset = self._get_native_asset(chain)
                        try:
                            native_data = await self.wdk.get_balance(address, chain, asset=None)
                            native_balance = Decimal(str(native_data.get('balance', 0)))

                            try:
                                price, _ = await self.oracle.get_asset_price(native_asset.lower())
                                native_usd = native_balance * price
                            except Exception:
                                native_usd = Decimal('0')
                                logger.warning(f"⚠️ Price lookup failed for {native_asset}")

                            balances[native_asset] = {
                                'asset': native_asset,
                                'symbol': native_asset,
                                'balance': float(native_balance),
                                'chain': chain,
                                'usd_value': float(native_usd)
                            }
                            total_usd += native_usd

                        except Exception as native_err:
                            logger.error(f"❌ Native balance failed for {chain}: {native_err}")
                            balances[native_asset] = {
                                'asset': native_asset,
                                'symbol': native_asset,
                                'balance': 0.0,
                                'chain': chain,
                                'usd_value': 0.0,
                                'error': str(native_err)
                            }

                        # Token assets (USDT, USDC)
                        tokens_to_query = self.CHAIN_TOKEN_MAP.get(chain, [])

                        for token in tokens_to_query:
                            balance_key = f"{token}_{chain.upper()}"

                            try:
                                token_data = await self.wdk.get_balance(address, chain, asset=token)
                                token_balance = Decimal(str(token_data.get('balance', 0)))

                                if token in ('USDT', 'USDC'):
                                    token_usd = token_balance
                                else:
                                    try:
                                        price, _ = await self.oracle.get_asset_price(token.lower())
                                        token_usd = token_balance * price
                                    except Exception:
                                        token_usd = Decimal('0')

                                if token_balance > 0:
                                    balances[balance_key] = {
                                        'asset': token,
                                        'symbol': balance_key,
                                        'balance': float(token_balance),
                                        'chain': chain,
                                        'usd_value': float(token_usd)
                                    }
                                    total_usd += token_usd
                                    logger.info(f"✅ {token} on {chain}: {token_balance} (${token_usd})")
                                else:
                                    logger.debug(f"ℹ️ {token} on {chain}: 0 balance, skipping")

                            except Exception as token_err:
                                logger.warning(f"⚠️ Token balance failed for {token} on {chain}: {token_err}")

            except Exception as wdk_err:
                logger.warning(f"⚠️ WDK balance query failed: {wdk_err}")

            # 3. Format response
            assets_list = sorted(
                balances.values(),
                key=lambda x: x.get('usd_value', 0),
                reverse=True
            )

            # After building balances, log the raw response
            logger.info(f"🔥 FINAL BALANCES DICT: {balances}")
            logger.info(f"🔥 TOTAL_USD: {total_usd}")

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
            # ============================================================================
            # STEP 1: VALIDATE INPUTS
            # ============================================================================
            if not asset or len(asset.strip()) == 0:
                raise Exception("Asset cannot be empty")
            
            if amount <= 0:
                raise Exception(f"Amount must be positive, got: {amount}")
            
            if not recipient or len(recipient.strip()) < 20:
                raise Exception("Invalid recipient address format")
            
            logger.info(f"ðŸ’¸ Initiating send: {amount} {asset} to {recipient[:10]}...")
            
            # ============================================================================
            # STEP 2: AUTO-ROUTE TO OPTIMAL CHAIN
            # ============================================================================
            optimal_chain = await self.auto_route_transaction(asset, amount, recipient)
            logger.info(f"ðŸ”€ Auto-routed {asset} to {optimal_chain}")
            
            # ============================================================================
            # STEP 3: CALCULATE FEES
            # ============================================================================
            fee_calc = await self.fees.calculate_transaction_fee(
                transaction_type=TransactionType.P2P_LOCAL,
                amount=amount,
                user_id=user_id,
                from_asset=asset,
                to_asset=asset
            )
            
            # ============================================================================
            # STEP 4: VERIFY WALLET EXISTS (CRITICAL)
            # ============================================================================
            if optimal_chain == 'algorand':
                wallet_check = self.db.supabase.table('user_wallets')\
                    .select('algorand_address')\
                    .eq('user_id', user_id)\
                    .execute()
                
                if not wallet_check.data or len(wallet_check.data) == 0:
                    raise Exception(
                        "NO WALLET FOUND\n\n"
                        "You don't have an Algorand wallet yet.\n"
                        "Please create a wallet first by clicking 'Create Wallet' in the dashboard."
                    )
                
                logger.info(f"Algorand wallet verified for user {user_id}")
            
            # ============================================================================
            # STEP 5: EXECUTE BLOCKCHAIN TRANSACTION
            # ============================================================================
            if optimal_chain == 'algorand':
                result = await self._send_via_algorand(user_id, recipient, asset, amount, memo)
            else:
                result = await self._send_via_wdk(user_id, recipient, asset, amount, optimal_chain)
            
            logger.info(f"Blockchain transaction successful: {result['tx_id']}")
            
            # ============================================================================
            # STEP 6: RECORD TRANSACTION AND FEE (NON-FATAL IF FAILS)
            # ============================================================================
            try:
                from backend.config import CENTRAL_TREASURY_ADDRESSES
                treasury_address = CENTRAL_TREASURY_ADDRESSES.get(optimal_chain, '')

                # ---------- Insert into blockchain_transactions ----------
                transaction_data = {
                    'user_id': user_id,
                    'transaction_type': 'send',
                    'status': 'completed',
                    'amount': float(amount),
                    'asset': asset,
                    'chain': optimal_chain,
                    'txn_hash': result['tx_id'],
                    'to_address': recipient,
                    'network_fee': float(result.get('fee', 0)),
                    'network_fee_asset': self._get_native_asset(optimal_chain),
                    'platform_fee': float(fee_calc['platform_fee']),   # USD value for accounting
                    'metadata': {
                        'memo': memo,
                        'fee_owed': float(fee_calc['platform_fee']),
                        'fee_collected': False
                    },
                    'created_at': datetime.utcnow().isoformat()
                }

                response = self.db.supabase.table('blockchain_transactions').insert(transaction_data).execute()

                if response.data:
                    transaction_id = response.data[0].get('id')
                    logger.info(f"✅ Transaction recorded in DB: {transaction_id}")

                    # Record fee owed (for batch collection) – using percentage of transaction amount
                    try:
                        from backend.config import CENTRAL_TREASURY_ADDRESSES
                        treasury_address = CENTRAL_TREASURY_ADDRESSES.get(optimal_chain)
                        
                        # Get native asset symbol (e.g., 'TRX', 'ALGO', 'BTC')
                        native_asset = self._get_native_asset(optimal_chain)
                        
                        # Get current price of native asset in USD from oracle
                        price, _ = await self.oracle.get_asset_price(native_asset.lower())
                        if price <= 0:
                            logger.warning(f"⚠️ Price for {native_asset} is zero, using fallback 1.0")
                            price = Decimal('1.0')  # fallback – should never happen in production
                        
                        # Seamount fee in USD (from fee_calculator)
                        platform_fee_usd = Decimal(str(fee_calc['platform_fee']))
                        
                        # Convert to native token amount
                        seamount_fee_native = platform_fee_usd / price
                        
                        fee_owed_data = {
                            'user_id': user_id,
                            'transaction_id': transaction_id,
                            'chain': optimal_chain,
                            'asset': native_asset,
                            'fee_amount': float(seamount_fee_native),
                            'treasury_address': treasury_address,
                            'status': 'pending',
                            'created_at': datetime.utcnow().isoformat()
                        }
                        
                        fee_insert = self.db.supabase.table('fees_owed').insert(fee_owed_data).execute()
                        
                        if fee_insert.data:
                            logger.info(f"💰 Fee recorded: {seamount_fee_native:.6f} {native_asset} owed to treasury")
                        else:
                            logger.warning("⚠️ Fee insert returned no data (non-fatal)")
                            
                    except Exception as fee_err:
                        logger.error(f"❌ Failed to record fee owed (non-fatal): {fee_err}")

                    # ---------- Track USD revenue for analytics ----------
                    try:
                        revenue_service = RevenueTrackingService(self.db)
                        await revenue_service.track_transaction_fee(
                            user_id=user_id,
                            transaction_type="p2p_transfer",
                            amount=amount,
                            fee_rate=Decimal("0.007"),
                            platform_fee=Decimal(str(fee_calc['platform_fee'])),
                            network_fee=Decimal(str(fee_calc['network_fee'])),
                            blockchain=optimal_chain,
                            metadata={
                                'transaction_id': result['tx_id'],
                                'asset': asset,
                                'memo': memo,
                                'fee_status': 'pending_collection'
                            }
                        )
                        logger.info("📊 Revenue tracked successfully")
                    except Exception as rev_err:
                        logger.error(f"❌ Revenue tracking failed (non-fatal): {rev_err}")

            except Exception as db_err:
                logger.error(f"❌ Database logging failed (transaction still succeeded on chain): {db_err}")
                
            # ============================================================================
            # STEP 7: RETURN SUCCESS RESPONSE
            # ============================================================================
            return {
                'success': True,
                'message': f'Payment sent! Your {asset} will arrive shortly. âœ”',
                'transaction_id': result['tx_id'],
                'amount': float(amount),
                'asset': asset,
                'fee': float(fee_calc['total_fee']),
                'estimated_arrival': self._estimate_arrival_time(optimal_chain)
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Payment failed for user {user_id}: {error_msg}", exc_info=True)
            return {
                'success': False,
                'message': error_msg,   # real error, not a generic wrapper
                'error':   error_msg
            }
    
    # ========== HELPER METHODS ==========
    
    async def auto_route_transaction(self, asset: str, amount: Decimal, recipient: str) -> str:
        """
        Smart chain selection for 6 supported chains
        Updated to include Solana support
        """
        
        logger.info(f"ðŸ”€ Auto-routing: {asset} (amount: {amount})")
        
        # âœ… Handle chain-suffixed assets first (e.g., USDT_ETH â†’ ethereum)
        if "_" in asset:
            parts = asset.split("_")
            chain_suffix = parts[1].lower()
            
            chain_map = {
                "algo": "algorand",
                "eth": "ethereum",
                "polygon": "polygon",
                "tron": "tron",
                "solana": "solana"  # âœ… NEW
            }
            
            routed_chain = chain_map.get(chain_suffix)
            if routed_chain:
                logger.info(f"âœ… Routed {asset} â†’ {routed_chain} (explicit chain suffix)")
                return routed_chain
        
        # Native Algorand assets
        if asset in ['ALGO', 'USDCa', 'goBTC', 'goETH']:
            logger.info(f"âœ… Routed {asset} â†’ algorand (native)")
            return 'algorand'
        
        # Bitcoin
        if asset == 'BTC':
            logger.info(f"âœ… Routed {asset} â†’ bitcoin")
            return 'bitcoin'
        
        # Ethereum
        if asset == 'ETH':
            logger.info(f"âœ… Routed {asset} â†’ ethereum")
            return 'ethereum'
        
        # Polygon
        if asset == 'MATIC':
            logger.info(f"âœ… Routed {asset} â†’ polygon")
            return 'polygon'
        
        # Tron
        if asset == 'TRX':
            logger.info(f"âœ… Routed {asset} â†’ tron")
            return 'tron'
        
        # Solana (âœ… NEW)
        if asset == 'SOL':
            logger.info(f"âœ… Routed {asset} â†’ solana")
            return 'solana'
        
        # âœ… USDT routing (optimized for 6 chains)
        if asset == 'USDT':
            if amount < Decimal('500'):
                logger.info(f"âœ… Routed USDT â†’ polygon (gasless, amount < $500)")
                return 'polygon'  # Gasless for small amounts
            elif amount < Decimal('5000'):
                logger.info(f"âœ… Routed USDT â†’ solana (lowest fees, amount < $5000)")
                return 'solana'  # âœ… NEW: Lowest fees for medium amounts
            else:
                logger.info(f"âœ… Routed USDT â†’ tron (best liquidity, amount â‰¥ $5000)")
                return 'tron'  # Best for large amounts
        
        # Fallback to ASSET_CHAIN_MAP
        fallback_chain = self.ASSET_CHAIN_MAP.get(asset, 'algorand')
        logger.warning(f"âš ï¸ Using fallback routing: {asset} â†’ {fallback_chain}")
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
        
        # âœ… FIX: Decrypt private key before using
        from backend.services.seed_encryption_service import SeedEncryptionService
        encryption_service = SeedEncryptionService()
        
        encrypted_key = wallet.data[0]['algorand_private_key']
        try:
            decrypted_private_key = encryption_service.decrypt_seed(encrypted_key)
            logger.info(f"ðŸ”“ Successfully decrypted private key for user {user_id}")
        except Exception as decrypt_err:
            logger.error(f"âŒ Private key decryption failed: {decrypt_err}")
            raise Exception(f"Failed to decrypt wallet credentials: {decrypt_err}")
        
        # âœ… Handle both plain and chain-suffixed asset keys
        lookup_key = asset.split('_')[0] if '_' in asset else asset
        asset_id = self.ALGORAND_ASSET_IDS.get(lookup_key)
        
        if asset_id is None:
            available_assets = ', '.join(self.ALGORAND_ASSET_IDS.keys())
            error_msg = f"Asset '{asset}' not supported on Algorand. Available: {available_assets}"
            logger.error(f"âŒ {error_msg}")
            raise Exception(error_msg)
        
        logger.info(f"ðŸ“ Sending {amount} {asset} (ASA ID: {asset_id}) on Algorand")
        
        # Execute transaction with DECRYPTED key
        tx_id = await self.algorand.transfer_asset(
            sender_private_key=decrypted_private_key,  # âœ… NOW USING DECRYPTED KEY
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
            raise Exception(f"No {chain} wallet found for user")
        
        from_address = wallet.data[0]['address']
        encrypted_seed = wallet.data[0]['encrypted_seed']
        
        # ðŸ”¥ CRITICAL FIX: Normalize asset name for WDK
        wdk_asset = asset
        if chain == 'tron' and asset in ['USDT', 'USDT_TRON']:
            wdk_asset = 'USDT'  # WDK expects just 'USDT' for Tron
        elif chain == 'ethereum' and asset == 'USDT_ETH':
            wdk_asset = 'USDT'
        elif chain == 'polygon' and asset == 'USDT_POLYGON':
            wdk_asset = 'USDT'
        
        logger.info(f"ðŸ”’ Sending {amount} {wdk_asset} via WDK on {chain}")
        logger.info(f"   From: {from_address[:10]}...")
        logger.info(f"   To: {recipient[:10]}...")
        logger.info(f"   Asset (normalized): {wdk_asset}")
        
        # Execute transaction via WDK
        try:
            result = await self.wdk.send_transaction(
                from_address=from_address,
                to_address=recipient,
                amount=amount,
                asset=wdk_asset,  # âœ… Use normalized asset name
                chain=chain,
                encrypted_seed=encrypted_seed,
                enable_gasless=True
            )
            
            if not result.get('success'):
                raise Exception(result.get('error', f'{chain} transaction failed'))
            
            logger.info(f"âœ… WDK transaction successful: {result['tx_id']}")
            
            return {
                'tx_id': result['tx_id'],
                'chain': chain,
                'gasless_used': result.get('gasless_used', False),
                'fee': result.get('fee', 0)
            }
            
        except Exception as wdk_error:
            logger.error(f"âŒ WDK send failed: {wdk_error}")
            
            # Enhanced error parsing
            error_msg = str(wdk_error)
            
            if 'insufficient balance' in error_msg.lower():
                # Check actual balance
                try:
                    balance_data = await self.wdk.get_balance(
                        address=from_address,
                        chain=chain,
                        asset=wdk_asset if wdk_asset != 'TRX' else None
                    )
                    actual_balance = Decimal(str(balance_data.get('balance', 0)))
                    error_msg = f"Insufficient {asset} balance. Available: {actual_balance}, Attempted: {amount}"
                except:
                    error_msg = f"Insufficient {asset} balance"
            
            raise Exception(error_msg)
    
    def _estimate_arrival_time(self, chain: str) -> str:
        """Estimate transaction arrival time"""
        times = {
            'algorand': '4.5 seconds',
            'bitcoin': '10-60 minutes',
            'ethereum': '12 seconds',
            'polygon': '2 seconds',
            'tron': '3 seconds',
            'solana': '0.4 seconds'
        }
        return times.get(chain, '1-5 minutes')