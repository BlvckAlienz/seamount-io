# File: backend/services/multi_chain_wallet_service.py
"""
Multi-Chain Wallet Service - Master Orchestrator
Manages Algorand + 8 WDK chains (Bitcoin, Lightning, Ethereum, Polygon, Arbitrum, TON, TRON, Solana)
REPLACES old wallet_service.py
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
    """
    Production-ready multi-chain wallet orchestrator
    Abstracts ALL blockchain complexity from users
    """
    
    # Supported assets and their optimal chains
    ASSET_CHAIN_MAP = {
        # Algorand native (our moat)
        'ALGO': 'algorand',
        'USDCa': 'algorand',
        'goBTC': 'algorand',
        'goETH': 'algorand',
        
        # Multi-chain assets (prioritize cheapest/fastest)
        'USDT': 'polygon',  # Default to Polygon (gasless + cheap)
        'BTC': 'bitcoin',   # Use Lightning for <$100
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
        
        # Initialize WDK client
        self.wdk = WDKClient()
        
        logger.info("✅ MultiChainWalletService initialized (Algorand + 8 WDK chains)")
    
    # ========== WALLET CREATION (Replaces old wallet_service.create_wallet) ==========
    
    async def create_wallet_for_user(
        self,
        user_id: str,
        chains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create multi-chain wallet for user
        
        DEFAULT: Algorand + essential chains (Bitcoin, Lightning, Ethereum, Polygon, TRON)
        OPTIONAL: Specify custom chain list
        """
        
        result = {
            'user_id': user_id,
            'wallets': {},
            'created_at': datetime.utcnow().isoformat(),
            'success': False
        }
        
        # 1. ALWAYS create Algorand wallet first (our moat - USDCa, USDT, goBTC, goETH)
        try:
            # Check if Algorand wallet already exists
            existing_algo = await self.db.supabase.table('user_wallets')\
                .select('algorand_address')\
                .eq('user_id', user_id)\
                .maybe_single()\
                .execute()
            
            if existing_algo.data and existing_algo.data.get('algorand_address'):
                algo_address = existing_algo.data['algorand_address']
                logger.info(f"✅ Existing Algorand wallet found: {algo_address[:10]}...")
            else:
                # Create new Algorand wallet
                algo_wallet = await self.algorand.create_algorand_wallet(user_id)
                algo_address = algo_wallet['wallet_address']
                logger.info(f"✅ New Algorand wallet created: {algo_address[:10]}...")
            
            result['wallets']['algorand'] = {
                'address': algo_address,
                'created_at': datetime.utcnow().isoformat(),
                'supported_assets': ['ALGO', 'USDCa', 'USDT', 'goBTC', 'goETH']
            }
            
        except Exception as e:
            logger.error(f"❌ Algorand wallet creation failed: {e}")
            result['errors'] = [f"Algorand: {str(e)}"]
            return result  # Stop if Algorand fails (core asset)
        
        # 2. Determine WDK chains to create
        if chains:
            wdk_chains = [c for c in chains if c != 'algorand']
        else:
            # Default essential chains for optimal UX
            wdk_chains = ['bitcoin', 'lightning', 'ethereum', 'polygon', 'tron']
        
        # 3. Create WDK multi-chain wallets
        if wdk_chains:
            try:
                # Generate encrypted seed phrase
                seed_data = await self.wdk.generate_seed()
                encrypted_seed = seed_data['encrypted_seed']
                
                # Create wallets on all WDK chains
                wdk_result = await self.wdk.create_wallet(
                    encrypted_seed=encrypted_seed,
                    chains=wdk_chains,
                    enable_gasless=True  # Enable Account Abstraction
                )
                
                # Store WDK wallets in database
                for chain, wallet_data in wdk_result.get('wallets', {}).items():
                    try:
                        # Insert into multi_chain_addresses table
                        await self.db.supabase.table('multi_chain_addresses').upsert({
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
                        
                        logger.info(f"✅ {chain.upper()} wallet created: {wallet_data['address'][:10]}...")
                        
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
    
    # ========== BALANCE QUERIES (Replaces old wallet_service.get_balances) ==========
    
    async def get_user_balances(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get unified balance view across ALL chains
        
        Returns user-friendly summary with USD values
        """
        
        try:
            # 1. Get Algorand balances
            algo_wallet = await self.db.supabase.table('user_wallets')\
                .select('algorand_address')\
                .eq('user_id', user_id)\
                .maybe_single()\
                .execute()
            
            balances = {}
            total_usd = Decimal('0')
            
            if algo_wallet.data and algo_wallet.data.get('algorand_address'):
                algo_address = algo_wallet.data['algorand_address']
                
                # Query Algorand account
                account_info = await self.algorand.get_account_info(algo_address)
                
                # Native ALGO balance
                algo_balance = Decimal(str(account_info.get('amount', 0))) / Decimal('1000000')
                if algo_balance > 0:
                    algo_price, _ = await self.oracle.get_asset_price('algorand')
                    balances['ALGO'] = {
                        'balance': float(algo_balance),
                        'chain': 'algorand',
                        'usd_value': float(algo_balance * algo_price)
                    }
                    total_usd += algo_balance * algo_price
                
                # ASA balances (USDCa, USDT, goBTC, goETH)
                for asset_info in account_info.get('assets', []):
                    asset_id = asset_info.get('asset-id')
                    amount = Decimal(str(asset_info.get('amount', 0)))
                    
                    # Map asset ID to symbol
                    asset_map = {
                        31566704: ('USDCa', 6),
                        312769: ('USDT', 6),
                        386192725: ('goBTC', 8),
                        386195940: ('goETH', 8)
                    }
                    
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
                            except Exception:
                                balances[symbol] = {
                                    'balance': float(balance),
                                    'chain': 'algorand',
                                    'usd_value': 0.0
                                }
            
            # 2. Get WDK chain balances
            wdk_wallets = await self.db.supabase.table('multi_chain_addresses')\
                .select('blockchain, address')\
                .eq('user_id', user_id)\
                .execute()
            
            if wdk_wallets.data:
                # Build address map for batch query
                address_map = {w['blockchain']: w['address'] for w in wdk_wallets.data}
                
                # Query balances via WDK Indexer (batch query)
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
    
    # ========== SEND PAYMENT (Replaces old wallet_service.transfer) ==========
    
    async def send_payment(
        self,
        user_id: str,
        recipient: str,
        asset: str,
        amount: Decimal,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send payment with auto-routing
        
        USER EXPERIENCE:
        - Enter: Recipient + Amount
        - Backend auto-selects optimal chain
        - User sees: "Sending 100 USDT... ✓ Sent!"
        - NO blockchain jargon exposed
        """
        
        try:
            # 1. Auto-route to optimal chain
            optimal_chain = await self.auto_route_transaction(asset, amount, recipient)
            logger.info(f"🔀 Auto-routed {asset} to {optimal_chain}")
            
            # 2. Calculate fees (includes hidden markup)
            fee_calc = await self.fees.calculate_transaction_fee(
                transaction_type=TransactionType.P2P_LOCAL,
                amount=amount,
                user_id=user_id,
                from_asset=asset,
                to_asset=asset
            )
            
            # 3. Execute on appropriate chain
            if optimal_chain == 'algorand':
                result = await self._send_via_algorand(user_id, recipient, asset, amount, memo)
            elif optimal_chain == 'lightning':
                result = await self._send_via_lightning(user_id, recipient, amount)
            else:
                result = await self._send_via_wdk(user_id, recipient, asset, amount, optimal_chain)
            
            # 4. Record transaction
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
            
            # 5. User-friendly response
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
    
    # ========== AUTO-ROUTING (Smart Chain Selection) ==========
    
    async def auto_route_transaction(
        self,
        asset: str,
        amount: Decimal,
        recipient: str
    ) -> str:
        """
        Smart routing: Select optimal chain based on asset, amount, recipient
        
        LOGIC:
        - Algorand assets → Always Algorand
        - BTC <$100 → Lightning (instant + cheap)
        - BTC >$100 → Bitcoin mainnet (secure)
        - USDT <$500 → Polygon (gasless)
        - USDT >$500 → TRON (best liquidity)
        - ETH → Arbitrum (cheaper than mainnet)
        """
        
        # Algorand native assets
        if asset in ['ALGO', 'USDCa', 'goBTC', 'goETH']:
            return 'algorand'
        
        # Bitcoin routing
        if asset == 'BTC':
            # Lightning for small amounts (instant, nearly free)
            if amount < Decimal('100'):
                # Check if recipient is Lightning invoice
                if recipient.lower().startswith('lnbc'):
                    return 'lightning'
            return 'bitcoin'
        
        # USDT routing (optimize for cost + speed)
        if asset == 'USDT':
            if amount < Decimal('500'):
                return 'polygon'  # Gasless + cheap
            else:
                return 'tron'  # USDT native chain
        
        # ETH routing
        if asset == 'ETH':
            return 'arbitrum'  # Cheaper than Ethereum mainnet
        
        # Default to asset's primary chain
        return self.ASSET_CHAIN_MAP.get(asset, 'algorand')
    
    # ========== HELPER METHODS ==========
    
    async def _send_via_algorand(
        self,
        user_id: str,
        recipient: str,
        asset: str,
        amount: Decimal,
        memo: Optional[str]
    ) -> Dict[str, Any]:
        """Send via Algorand"""
        
        # Get user's Algorand wallet
        wallet = await self.db.supabase.table('user_wallets')\
            .select('algorand_address, algorand_private_key')\
            .eq('user_id', user_id)\
            .single()\
            .execute()
        
        if not wallet.data:
            raise Exception("Algorand wallet not found")
        
        # Get asset ID
        asset_id_map = {
            'ALGO': 0,
            'USDCa': 31566704,
            'USDT': 312769,
            'goBTC': 386192725,
            'goETH': 386195940
        }
        
        asset_id = asset_id_map.get(asset)
        if asset_id is None:
            raise Exception(f"Asset {asset} not supported on Algorand")
        
        # Send transaction
        tx_id = await self.algorand.transfer_asset(
            sender_private_key=wallet.data['algorand_private_key'],
            receiver_address=recipient,
            asset_id=asset_id,
            amount=amount,
            memo=memo or ""
        )
        
        return {'tx_id': tx_id, 'chain': 'algorand'}
    
    async def _send_via_lightning(
        self,
        user_id: str,
        invoice: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """Send via Lightning Network"""
        
        # Get encrypted seed
        seed_data = await self.db.supabase.table('multi_chain_addresses')\
            .select('encrypted_seed')\
            .eq('user_id', user_id)\
            .eq('blockchain', 'lightning')\
            .single()\
            .execute()
        
        if not seed_data.data:
            raise Exception("Lightning wallet not found")
        
        result = await self.wdk.pay_lightning_invoice(
            invoice=invoice,
            encrypted_seed=seed_data.data['encrypted_seed']
        )
        
        return {'tx_id': result['payment_hash'], 'chain': 'lightning'}
    
    async def _send_via_wdk(
        self,
        user_id: str,
        recipient: str,
        asset: str,
        amount: Decimal,
        chain: str
    ) -> Dict[str, Any]:
        """Send via WDK chains (Bitcoin, Ethereum, Polygon, etc.)"""
        
        # Get wallet data
        wallet = await self.db.supabase.table('multi_chain_addresses')\
            .select('address, encrypted_seed')\
            .eq('user_id', user_id)\
            .eq('blockchain', chain)\
            .single()\
            .execute()
        
        if not wallet.data:
            raise Exception(f"Wallet not found on {chain}")
        
        result = await self.wdk.send_transaction(
            from_address=wallet.data['address'],
            to_address=recipient,
            amount=amount,
            asset=asset,
            chain=chain,
            encrypted_seed=wallet.data['encrypted_seed'],
            enable_gasless=True
        )
        
        return {'tx_id': result['tx_id'], 'chain': chain}
    
    def _get_native_asset(self, chain: str) -> str:
        """Get native asset symbol for chain"""
        native_map = {
            'bitcoin': 'BTC',
            'lightning': 'BTC',
            'ethereum': 'ETH',
            'polygon': 'MATIC',
            'arbitrum': 'ETH',
            'ton': 'TON',
            'tron': 'TRX',
            'solana': 'SOL'
        }
        return native_map.get(chain, 'UNKNOWN')
    
    def _estimate_arrival_time(self, chain: str) -> str:
        """Estimate transaction arrival time"""
        times = {
            'algorand': '4.5 seconds',
            'lightning': 'Instant',
            'bitcoin': '10-60 minutes',
            'ethereum': '12 seconds',
            'polygon': '2 seconds',
            'arbitrum': '1 second',
            'ton': '5 seconds',
            'tron': '3 seconds',
            'solana': '<1 second'
        }
        return times.get(chain, '1-5 minutes')