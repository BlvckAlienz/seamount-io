# File: backend/services/multi_chain_wallet_service.py
"""
Multi-Chain Wallet Service - ROCK SOLID Implementation
Algorand + WDK (Bitcoin, Ethereum, Polygon, TON, etc.)
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
from backend.config import get_settings

logger = logging.getLogger(__name__)

class MultiChainWalletService:
    """Production-ready multi-chain wallet orchestrator"""
    
    # Asset-to-chain mapping
    ASSET_CHAIN_MAP = {
        'ALGO': 'algorand',
        'USDCa': 'algorand',
        'goBTC': 'algorand',
        'goETH': 'algorand',
        'USDT': 'polygon',  # Default (gasless)
        'BTC': 'bitcoin',
        'ETH': 'arbitrum',  # Cheaper than mainnet
        'MATIC': 'polygon',
        'TON': 'ton',
        'TRX': 'tron',
        'SOL': 'solana'
    }
    
    def __init__(
        self,
        db_service: DatabaseService,
        algorand_service: AlgorandService,
        fee_calculator: FeeCalculatorService,
        oracle_service: OracleService
    ):
        self.db = db_service
        self.algorand = algorand_service
        self.fees = fee_calculator
        self.oracle = oracle_service
        self.wdk = WDKClient()
        
        logger.info("✅ MultiChainWalletService initialized (Algorand + WDK)")
    
    # ========== WALLET CREATION ==========
    
    async def create_wallet_for_user(
        self,
        user_id: str,
        chains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create multi-chain wallet for user
        DEFAULT: Algorand + essential WDK chains
        """
        
        result = {
            'user_id': user_id,
            'wallets': {},
            'created_at': datetime.utcnow().isoformat(),
            'success': False
        }
        
        # 1. Create Algorand wallet (ALWAYS)
        try:
            # ✅ FIX: Query without maybe_single()
            existing_algo = self.db.supabase.table('user_wallets')\
                .select('algorand_address')\
                .eq('user_id', user_id)\
                .execute()
            
            if existing_algo.data and len(existing_algo.data) > 0 and existing_algo.data[0].get('algorand_address'):
                algo_address = existing_algo.data[0]['algorand_address']
                logger.info(f"✅ Existing Algorand wallet: {algo_address[:10]}...")
            else:
                # Create new Algorand wallet
                algo_wallet = await self.algorand.create_algorand_wallet(user_id)
                algo_address = algo_wallet['wallet_address']
                
                # Store in user_wallets
                wallet_data = {
                    'user_id': user_id,
                    'algorand_address': algo_address,
                    'algorand_private_key': algo_wallet['encrypted_private_key'],
                    'algorand_mnemonic': algo_wallet['encrypted_mnemonic'],
                    'created_at': datetime.utcnow().isoformat()
                }
                
                self.db.supabase.table('user_wallets').upsert(
                    wallet_data, 
                    on_conflict='user_id'
                ).execute()
                
                logger.info(f"✅ New Algorand wallet: {algo_address[:10]}...")
            
            result['wallets']['algorand'] = {
                'address': algo_address,
                'created_at': datetime.utcnow().isoformat(),
                'supported_assets': ['ALGO', 'USDCa', 'USDT', 'goBTC', 'goETH']
            }
            
        except Exception as e:
            logger.error(f"❌ Algorand wallet failed: {e}")
            result['errors'] = [f"Algorand: {str(e)}"]
            return result
        
        # 2. Determine WDK chains
        if chains:
            wdk_chains = [c for c in chains if c != 'algorand']
        else:
            # Default: Essential chains from Tether docs
            wdk_chains = ['bitcoin', 'ethereum', 'polygon', 'ton']
        
        # 3. Create WDK wallets
        if wdk_chains:
            try:
                seed_data = await self.wdk.generate_seed()
                encrypted_seed = seed_data['encrypted_seed']
                
                wdk_result = await self.wdk.create_wallet(
                    encrypted_seed=encrypted_seed,
                    chains=wdk_chains,
                    enable_gasless=True
                )
                
                # Store WDK wallets
                for chain, wallet_data in wdk_result.get('wallets', {}).items():
                    try:
                        self.db.supabase.table('multi_chain_addresses').upsert({
                            'user_id': user_id,
                            'blockchain': chain,
                            'address': wallet_data['address'],
                            'encrypted_seed': encrypted_seed,
                            'wallet_type': 'wdk',
                            'created_at': datetime.utcnow().isoformat()
                        }, on_conflict='user_id,blockchain').execute()
                        
                        result['wallets'][chain] = {
                            'address': wallet_data['address'],
                            'created_at': wallet_data['created_at']
                        }
                        
                        logger.info(f"✅ {chain.upper()} wallet: {wallet_data['address'][:10]}...")
                        
                    except Exception as db_error:
                        logger.error(f"❌ Failed to store {chain} wallet: {db_error}")
                
            except Exception as e:
                logger.error(f"❌ WDK wallet creation failed: {e}")
                if 'errors' not in result:
                    result['errors'] = []
                result['errors'].append(f"WDK: {str(e)}")
        
        result['total_chains'] = len(result['wallets'])
        result['success'] = len(result['wallets']) > 0
        
        return result
    
    # ========== BALANCE QUERIES ==========
    
    async def get_user_balances(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get unified balance view across ALL chains
        """
        
        try:
            balances = {}
            total_usd = Decimal('0')
            
            # 1. Get Algorand balances
            try:
                # ✅ FIX: Proper Supabase query without maybe_single()
                algo_wallet = self.db.supabase.table('user_wallets')\
                    .select('algorand_address')\
                    .eq('user_id', user_id)\
                    .execute()
                
                if algo_wallet.data and len(algo_wallet.data) > 0 and algo_wallet.data[0].get('algorand_address'):
                    algo_address = algo_wallet.data[0]['algorand_address']
                    
                    # Query Algorand account
                    account_info = await self.algorand.get_account_info(algo_address)
                    
                    if account_info:  # ✅ Check account exists
                        # Native ALGO balance
                        algo_balance = Decimal(str(account_info.get('amount', 0))) / Decimal('1000000')
                        if algo_balance > 0:
                            try:
                                algo_price, _ = await self.oracle.get_asset_price('algorand')
                                balances['ALGO'] = {
                                    'balance': float(algo_balance),
                                    'chain': 'algorand',
                                    'usd_value': float(algo_balance * algo_price)
                                }
                                total_usd += algo_balance * algo_price
                            except Exception as price_err:
                                logger.warning(f"Price lookup failed for ALGO: {price_err}")
                                balances['ALGO'] = {
                                    'balance': float(algo_balance),
                                    'chain': 'algorand',
                                    'usd_value': 0.0
                                }
                        
                        # ASA balances (USDCa, USDT, goBTC, goETH)
                        asset_map = {
                            31566704: ('USDCa', 6),
                            312769: ('USDT', 6),
                            386192725: ('goBTC', 8),
                            386195940: ('goETH', 8)
                        }
                        
                        for asset_info in account_info.get('assets', []):
                            asset_id = asset_info.get('asset-id')
                            amount = Decimal(str(asset_info.get('amount', 0)))
                            
                            if asset_id in asset_map:
                                symbol, decimals = asset_map[asset_id]
                                balance = amount / (Decimal('10') ** decimals)
                                
                                if balance > 0:
                                    try:
                                        price, _ = await self.oracle.get_asset_price(symbol.lower())
                                        usd_value = balance * price
                                        
                                        balances[symbol] = {
                                            'balance': float(balance),
                                            'chain': 'algorand',
                                            'usd_value': float(usd_value)
                                        }
                                        total_usd += usd_value
                                    except Exception as price_err:
                                        logger.warning(f"Price lookup failed for {symbol}: {price_err}")
                                        balances[symbol] = {
                                            'balance': float(balance),
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
                            # Query balance
                            balance = await self.wdk.get_balance(
                                address=address,
                                chain=chain,
                                use_indexer=False
                            )
                            
                            if balance > 0:
                                native_asset = self._get_native_asset(chain)
                                
                                try:
                                    # Map chain to oracle asset name
                                    oracle_map = {
                                        'bitcoin': 'bitcoin',
                                        'ethereum': 'ethereum',
                                        'polygon': 'matic-network',
                                        'arbitrum': 'ethereum',
                                        'tron': 'tron',
                                        'ton': 'the-open-network'
                                    }
                                    
                                    oracle_id = oracle_map.get(chain, chain)
                                    price, _ = await self.oracle.get_asset_price(oracle_id)
                                    usd_value = balance * price
                                    
                                    balances[native_asset] = {
                                        'balance': float(balance),
                                        'chain': chain,
                                        'usd_value': float(usd_value)
                                    }
                                    total_usd += usd_value
                                    
                                except Exception as price_error:
                                    logger.warning(f"Price lookup failed for {chain}: {price_error}")
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
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'total_usd': 0.0,
                'assets': [],
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # 2. Get WDK chain balances
            wdk_wallets = await self.db.supabase.table('multi_chain_addresses')\
                .select('blockchain, address')\
                .eq('user_id', user_id)\
                .execute()
            
            if wdk_wallets.data:
                for wallet in wdk_wallets.data:
                    chain = wallet['blockchain']
                    address = wallet['address']
                    
                    try:
                        # ✅ FIX: Pass address and chain correctly
                        balance = await self.wdk.get_balance(
                            address=address,
                            chain=chain,
                            use_indexer=False  # Skip indexer, use direct query
                        )
                        
                        if balance > 0:
                            native_asset = self._get_native_asset(chain)
                            
                            try:
                                # Map chain to oracle asset name
                                oracle_map = {
                                    'bitcoin': 'bitcoin',
                                    'ethereum': 'ethereum',
                                    'polygon': 'matic-network',
                                    'arbitrum': 'ethereum',  # Arbitrum uses ETH
                                    'tron': 'tron',
                                    'ton': 'the-open-network'
                                }
                                
                                oracle_id = oracle_map.get(chain, chain)
                                price, _ = await self.oracle.get_asset_price(oracle_id)
                                usd_value = balance * price
                                
                                balances[native_asset] = {
                                    'balance': float(balance),
                                    'chain': chain,
                                    'usd_value': float(usd_value)
                                }
                                total_usd += usd_value
                                
                            except Exception as price_error:
                                logger.warning(f"Price lookup failed for {chain}: {price_error}")
                                balances[native_asset] = {
                                    'balance': float(balance),
                                    'chain': chain,
                                    'usd_value': 0.0
                                }
                    
                    except Exception as e:
                        logger.error(f"❌ Balance query failed for {chain}: {e}")
                        continue
            
            # 3. Format response
            assets_list = sorted(
                balances.values(),
                key=lambda x: x['usd_value'],
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
                'error': str(e)
            }
            
            # 2. WDK balances
            wdk_wallets = self.db.supabase.table('multi_chain_addresses')\
                .select('blockchain, address')\
                .eq('user_id', user_id)\
                .execute()
            
            if wdk_wallets.data:
                address_map = {w['blockchain']: w['address'] for w in wdk_wallets.data}
                wdk_balances = await self.wdk.get_balances_multi_chain(address_map)
                
                for chain, balance_data in wdk_balances.items():
                    if balance_data.get('balance', 0) > 0:
                        native_asset = self._get_native_asset(chain)
                        balance = Decimal(str(balance_data['balance']))
                        
                        try:
                            price, _ = await self.oracle.get_asset_price(native_asset.lower())
                            usd_value = balance * price
                            
                            balances[native_asset] = {
                                'balance': float(balance),
                                'chain': chain,
                                'usd_value': float(usd_value)
                            }
                            total_usd += usd_value
                        except Exception:
                            balances[native_asset] = {
                                'balance': float(balance),
                                'chain': chain,
                                'usd_value': 0.0
                            }
            
            # Format response
            assets_list = sorted(
                balances.values(),
                key=lambda x: x['usd_value'],
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
                'error': str(e)
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
            # Auto-route
            optimal_chain = await self.auto_route_transaction(asset, amount, recipient)
            logger.info(f" 🔀 Auto-routed {asset} to {optimal_chain}")
            
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
            
            # Record transaction
            await self.db.supabase.table('transactions').insert({
                'user_id': user_id,
                'transaction_type': 'send',
                'asset': asset,
                'amount': float(amount),
                'from_chain': optimal_chain,
                'to_address': recipient,
                'tx_id': result['tx_id'],
                'fee_amount': float(fee_calc['total_fee']),
                'status': 'completed',
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            
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
        """Smart chain selection"""
        
        # Algorand assets
        if asset in ['ALGO', 'USDCa', 'goBTC', 'goETH']:
            return 'algorand'
        
        # Bitcoin
        if asset == 'BTC':
            if amount < Decimal('100') and recipient.lower().startswith('lnbc'):
                return 'lightning'
            return 'bitcoin'
        
        # USDT
        if asset == 'USDT':
            if amount < Decimal('500'):
                return 'polygon'  # Gasless
            return 'tron'  # Best liquidity
        
        # ETH
        if asset == 'ETH':
            return 'arbitrum'
        
        return self.ASSET_CHAIN_MAP.get(asset, 'algorand')
    
    async def _send_via_algorand(self, user_id: str, recipient: str, asset: str, amount: Decimal, memo: Optional[str]) -> Dict:
        """Send via Algorand"""
        wallet = self.db.supabase.table('user_wallets')\
            .select('algorand_address, algorand_private_key')\
            .eq('user_id', user_id)\
            .execute()
        
        if not wallet.data or len(wallet.data) == 0:
            raise Exception("Algorand wallet not found")
        
        asset_id_map = {
            'ALGO': 0,
            'USDCa': 31566704,
            'USDT': 312769,
            'goBTC': 386192725,
            'goETH': 386195940
        }
        
        asset_id = asset_id_map.get(asset)
        if asset_id is None:
            raise Exception(f"Asset {asset} not supported")
        
        tx_id = await self.algorand.transfer_asset(
            sender_private_key=wallet.data[0]['algorand_private_key'],
            receiver_address=recipient,
            asset_id=asset_id,
            amount=amount,
            memo=memo or ""
        )
        
        return {'tx_id': tx_id, 'chain': 'algorand'}
    
    async def _send_via_wdk(self, user_id: str, recipient: str, asset: str, amount: Decimal, chain: str) -> Dict:
        """Send via WDK chains"""
        wallet = self.db.supabase.table('multi_chain_addresses')\
            .select('address, encrypted_seed')\
            .eq('user_id', user_id)\
            .eq('blockchain', chain)\
            .execute()
        
        if not wallet.data or len(wallet.data) == 0:
            raise Exception(f"Wallet not found on {chain}")
        
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
    
    def _get_native_asset(self, chain: str) -> str:
        """Get native asset for chain"""
        native_map = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH',
            'polygon': 'MATIC',
            'arbitrum': 'ETH',
            'ton': 'TON',
            'tron': 'TRX',
            'solana': 'SOL'
        }
        return native_map.get(chain, 'UNKNOWN')
    
    def _estimate_arrival_time(self, chain: str) -> str:
        """Estimate transaction time"""
        times = {
            'algorand': '4.5 seconds',
            'bitcoin': '10-60 minutes',
            'ethereum': '12 seconds',
            'polygon': '2 seconds',
            'arbitrum': '1 second',
            'ton': '5 seconds',
            'tron': '3 seconds',
            'solana': '<1 second'
        }
        return times.get(chain, '1-5 minutes')