# File: backend/services/swap_service.py
"""
Enhanced Swap Service with Real Algorand DEX Integration
Supports Pact, Folks Finance, and other Algorand DEX protocols
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, UTC
from uuid import uuid4
from fastapi import HTTPException

# Core Dependencies
from backend.config import Settings, get_settings
from backend.services.algorand_defi_service import AlgorandDeFiService
from backend.services.algorand_service import AlgorandService
from backend.services.database_service import DatabaseService
from backend.services.multi_chain_wallet_service import MultiChainWalletService as WalletService
from backend.services.revenue_tracking_service import RevenueTrackingService
from backend.services.seed_encryption_service import SeedEncryptionService

logger = logging.getLogger(__name__)

class SwapService:
    """
    Handles all on-chain asset swaps with premium tiered fees.
    NOW WITH REAL ALGORAND DEX INTEGRATION!
    """

    # ➕ ADD THIS MAPPING
    # 🗺️ Frontend-to-Backend Asset Key Mapping
    ASSET_KEY_MAPPING = {
        # Frontend sends simple names, we map to config keys
        "USDT": "USDT_ALGO",
        "USDT_ETH": "USDT_ETH",
        "USDT_POLYGON": "USDT_POLYGON",
        "USDT_TRON": "USDT_TRON",
        "USDC_ETH": "USDC_ETH",
        "USDC_POLYGON": "USDC_POLYGON",
        # Everything else passes through
        "ALGO": "ALGO",
        "USDCa": "USDCa",
        "goBTC": "goBTC",
        "goETH": "goETH",
        "BTC": "BTC",
        "ETH": "ETH",
        "MATIC": "MATIC",
        "TRX": "TRX",
    }

    # ➕ SUPPORTED SWAP PAIRS (Pact Finance MainNet)
    SUPPORTED_PAIRS = {
        "ALGO": ["USDT", "USDCa", "goBTC", "goETH"],
        "USDT": ["ALGO", "USDCa", "goBTC", "goETH"],
        "USDCa": ["ALGO", "USDT", "goBTC", "goETH"],
        "goBTC": ["ALGO", "USDT", "USDCa", "goETH"],
        "goETH": ["ALGO", "USDT", "USDCa", "goBTC"],
    }

    # âœ… NEW COMPETITIVE FEE STRUCTURE
    COMPETITIVE_FEE_STRUCTURE = {
        # TIER 1: Market Rate (Compete on Volume)
        "stable_to_stable": Decimal("0.003"),    # 0.3% (vs Quidax 0.15%)
        "stable_to_volatile": Decimal("0.005"),  # 0.5% (vs Luno 0.25%)
        "volatile_to_volatile": Decimal("0.008"), # 0.8% (vs Busha 0.5-1%)
        
        # TIER 2: Premium Services (Justify Higher Fee)
        "with_yield_stake": Decimal("0.002"),    # 0.2% (discount if staking)
        "high_frequency": Decimal("0.001"),      # 0.1% (>$10k/month volume)
        
        # TIER 3: Cross-Border (Where You Have Edge)
        "cross_border": Decimal("0.012"),        # 1.2% (still cheaper than WU)
    }
    
    # âœ… MINIMUM FEE: $0.50 (vs old $1.00)
    MINIMUM_FEE = Decimal("0.50")
    
    def __init__(
        self, 
        settings: Settings, 
        algorand_service: AlgorandService, 
        db_service: DatabaseService,
        wallet_service: WalletService,
        revenue_service: RevenueTrackingService
    ):
        self.settings = settings
        self.algorand_service = algorand_service
        self.db_service = db_service
        self.wallet_service = wallet_service
        self.revenue_service = revenue_service
        
        # Initialize encryption service
        self.encryption_service = SeedEncryptionService()
        
        # âœ… Initialize real DEX service (MainNet)
        self.dex_service = AlgorandDeFiService(
            algod_client=algorand_service.algod_client
        )
        
        logger.info("âœ… SwapService initialized with competitive fees")

    def _determine_fee_tier(self, from_asset: str, to_asset: str, user_id: str = None) -> Decimal:
        """
        âœ… UPDATED: Competitive fee calculation
        Returns: Fee rate (e.g., 0.003 = 0.3%)
        """
        supported_assets = self.settings.SUPPORTED_ASSETS
        
        # Get asset configs
        from_config = supported_assets.get(from_asset, {})
        to_config = supported_assets.get(to_asset, {})
        
        from_stable = from_config.get("is_stable", False)
        to_stable = to_config.get("is_stable", False)
        
        # âœ… TIER 1: Asset type-based fees
        if from_stable and to_stable:
            fee_rate = self.COMPETITIVE_FEE_STRUCTURE["stable_to_stable"]  # 0.3%
        elif from_stable or to_stable:
            fee_rate = self.COMPETITIVE_FEE_STRUCTURE["stable_to_volatile"]  # 0.5%
        else:
            fee_rate = self.COMPETITIVE_FEE_STRUCTURE["volatile_to_volatile"]  # 0.8%
        
        # âœ… TIER 2: Volume-based discounts (future feature)
        # TODO: Check user monthly volume and apply discounts
        # if user_monthly_volume > 10000:
        #     fee_rate = self.COMPETITIVE_FEE_STRUCTURE["high_frequency"]
        
        # âœ… TIER 3: Yield staking discount (future feature)
        # TODO: Check if user has active yield stakes
        # if user_has_active_stake:
        #     fee_rate = min(fee_rate, self.COMPETITIVE_FEE_STRUCTURE["with_yield_stake"])
        
        logger.info(f"đź'° Fee rate: {float(fee_rate * 100)}% for {from_asset}â†'{to_asset}")
        
        return fee_rate

    async def get_swap_quote(
        self, 
        from_asset: str, 
        to_asset: str, 
        amount: Decimal,
        user_id: str = None  # âœ… NEW: For future volume discounts
    ) -> Dict[str, Any]:
        """
        âœ… UPDATED: Competitive fees + proper rate calculation
        """
        try:
            # Validate swap pair
            if to_asset not in self.SUPPORTED_PAIRS.get(from_asset, []):
                raise HTTPException(
                    status_code=400,
                    detail=f"Swap pair {from_asset}/{to_asset} not supported"
                )
            
            # Get asset configs
            from_asset_config = self.settings.SUPPORTED_ASSETS.get(from_asset)
            to_asset_config = self.settings.SUPPORTED_ASSETS.get(to_asset)
            
            if not from_asset_config or not to_asset_config:
                raise HTTPException(
                    status_code=400,
                    detail="Asset configuration not found"
                )
            
            from_asset_id = from_asset_config["asset_id"]
            to_asset_id = to_asset_config["asset_id"]
            
            logger.info(
                f"đź"Š Fetching quote: {amount} {from_asset} (ID: {from_asset_id}) "
                f"â†' {to_asset} (ID: {to_asset_id})"
            )
            
            # âœ… Get REAL quote from Pact DEX
            dex_quote = await self.dex_service.get_swap_quote(
                from_asset_id=from_asset_id,
                to_asset_id=to_asset_id,
                amount_in=amount
            )
            
            # Extract DEX quote data
            amount_out_before_fees = Decimal(str(dex_quote["amount_out"]))
            price_impact = Decimal(str(dex_quote["price_impact"]))
            exchange_rate = Decimal(str(dex_quote["exchange_rate"]))
            
            # âœ… NEW COMPETITIVE FEE CALCULATION
            fee_rate = self._determine_fee_tier(from_asset, to_asset, user_id)
            
            # Calculate platform fee on OUTPUT amount
            platform_fee = amount_out_before_fees * fee_rate
            
            # Apply minimum fee
            if platform_fee < self.MINIMUM_FEE:
                platform_fee = self.MINIMUM_FEE
            
            # Calculate final amount out
            amount_out = amount_out_before_fees - platform_fee
            
            logger.info(
                f"âœ… Quote generated: {amount} {from_asset} â†' {amount_out} {to_asset} "
                f"(Rate: 1 {from_asset} = {exchange_rate} {to_asset}, "
                f"Fee: {fee_rate*100}% = ${platform_fee})"
            )
            
            return {
                "from_asset": from_asset,
                "to_asset": to_asset,
                "amount_in": float(amount),
                "amount_out": float(amount_out),
                "amount_out_before_fees": float(amount_out_before_fees),  # âœ… NEW
                "fee_amount": float(platform_fee),
                "fee_rate": float(fee_rate),
                "fee_percentage": float(fee_rate * 100),  # âœ… NEW: For UI display
                "exchange_rate": float(exchange_rate),  # âœ… NEW: Explicit rate
                "price_impact": float(price_impact),
                "min_amount_out": float(amount_out * Decimal("0.995")),  # 0.5% buffer
                "dex": dex_quote["dex"],
                "pool_id": dex_quote.get("pool_id"),
                "network_fee": 0.001,  # Algorand network fee
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to generate swap quote: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Swap quote failed: {str(e)}")

    async def execute_swap(
        self, 
        user_id: str, 
        from_asset: str, 
        to_asset: str, 
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Execute an asset swap with real DEX integration.
        âœ… ADDED: Rate validation to prevent bad swaps
        """
        try:
            # âœ… SAFETY CHECK 1: Max swap amount
            MAX_SWAP_AMOUNT = Decimal("1000.00")  # $1000 max
            if amount > MAX_SWAP_AMOUNT:
                raise HTTPException(
                    status_code=400,
                    detail=f"Swap amount exceeds safety limit of ${MAX_SWAP_AMOUNT}"
                )
            
            # Get current wallet balances
            balances = await self.wallet_service.get_wallet_balances(user_id)
            
            # Check if user has sufficient balance
            user_balance = balances.get(from_asset, Decimal("0"))
            if user_balance < amount:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient {from_asset} balance. Available: {user_balance}"
                )
            
            # Get swap quote
            quote = await self.get_swap_quote(from_asset, to_asset, amount, user_id)
            
            # âœ… SAFETY CHECK 2: Validate exchange rate makes sense
            exchange_rate = quote["exchange_rate"]
            
            # Known reasonable ranges (can be expanded)
            RATE_VALIDATIONS = {
                ("USDT", "ALGO"): (1.5, 5.0),    # 1 USDT = 1.5-5 ALGO
                ("ALGO", "USDT"): (0.2, 0.7),    # 1 ALGO = $0.20-$0.70
                ("USDT", "USDCa"): (0.98, 1.02), # 1 USDT = 0.98-1.02 USDC
            }
            
            if (from_asset, to_asset) in RATE_VALIDATIONS:
                min_rate, max_rate = RATE_VALIDATIONS[(from_asset, to_asset)]
                if exchange_rate < min_rate or exchange_rate > max_rate:
                    logger.error(
                        f"âŒ INVALID RATE: 1 {from_asset} = {exchange_rate} {to_asset} "
                        f"(expected {min_rate}-{max_rate})"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Exchange rate outside expected range "
                            f"({exchange_rate:.6f}). Please try again later."
                        )
                    )
            
            # âœ… SAFETY CHECK 3: Price impact limit
            if quote["price_impact"] > 0.10:  # 10% max
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Price impact too high ({quote['price_impact']*100:.1f}%). "
                        f"Try a smaller amount."
                    )
                )
            
            # 🚀 EXECUTE REAL SWAP ON ALGORAND DEX
            swap_tx_id = await self._execute_dex_swap(
                user_id=user_id,
                from_asset=from_asset,
                to_asset=to_asset,
                amount_in=amount,
                min_amount_out=Decimal(str(quote["min_amount_out"]))
            )
            
            # Update balances in database
            from_balance_new = balances[from_asset] - amount
            to_balance_new = balances[to_asset] + Decimal(str(quote["amount_out"]))
            
            # Update from asset balance
            await self.wallet_service.update_asset_balance(user_id, from_asset, from_balance_new)
            # Update to asset balance
            await self.wallet_service.update_asset_balance(user_id, to_asset, to_balance_new)
            
            # Log the swap transaction
            swap_log = {
                "user_id": user_id,
                "from_asset": from_asset,
                "to_asset": to_asset,
                "amount_in": float(amount),
                "amount_out": quote["amount_out"],
                "fee_amount": quote["fee_amount"],
                "fee_rate": quote["fee_rate"],
                "status": "completed",
                "tx_hash": swap_tx_id,
                "dex": quote["dex"],
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            await self.db_service.log_event("swap_transactions", swap_log)
            
            # 🚨 TRACK REVENUE
            await self.revenue_service.track_transaction_fee(
                user_id=user_id,
                transaction_type="swap",
                amount=amount,
                fee_rate=Decimal(str(quote["fee_rate"])),
                platform_fee=Decimal(str(quote["fee_amount"])),
                network_fee=Decimal("0.001"),  # Algorand network fee
                blockchain="algorand",
                metadata={
                    "swap_pair": f"{from_asset}/{to_asset}",
                    "dex": quote["dex"]
                }
            )

            logger.info(
                f"✅ Swap executed: {amount} {from_asset} → {quote['amount_out']} {to_asset} "
                f"(TX: {swap_tx_id})"
            )
            
            return {
                "success": True,
                "tx_id": swap_tx_id,
                "amount_in": float(amount),
                "amount_out": quote["amount_out"],
                "fee_amount": quote["fee_amount"],
                "from_asset_new_balance": float(from_balance_new),
                "to_asset_new_balance": float(to_balance_new)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Swap execution failed for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Swap execution failed")
    
    async def _execute_dex_swap(
        self,
        user_id: str,
        from_asset: str,
        to_asset: str,
        amount_in: Decimal,
        min_amount_out: Decimal
    ) -> str:
        """
        Execute swap on Algorand DEX using our DeFi service
        âœ… PRODUCTION: Uses same encryption pattern as multi_chain_wallet_service
        """
        try:
            # Get user's wallet credentials from database
            wallet_query = """
                SELECT algorand_address, algorand_private_key 
                FROM user_wallets 
                WHERE user_id = %s
            """
            wallet_result = await self.db_service.execute_query(
                wallet_query, 
                (user_id,)
            )
            
            if not wallet_result or len(wallet_result) == 0:
                raise ValueError(
                    "❌ NO WALLET FOUND\n\n"
                    "You don't have an Algorand wallet yet.\n"
                    "Please create a wallet first in the dashboard."
                )
            
            user_address = wallet_result[0]["algorand_address"]
            encrypted_key = wallet_result[0]["algorand_private_key"]
            
            # âœ… DECRYPT PRIVATE KEY (Same pattern as multi_chain_wallet_service)
            try:
                decrypted_private_key = self.encryption_service.decrypt_seed(encrypted_key)
                logger.info(f"🔓 Successfully decrypted key for swap operation")
            except Exception as decrypt_err:
                logger.error(f"❌ Private key decryption failed: {decrypt_err}")
                raise Exception(f"Failed to decrypt wallet credentials: {decrypt_err}")
            
            # Get ASA IDs from config
            from_asa_id = self.settings.SUPPORTED_ASSETS[from_asset]["asa_id"]
            to_asa_id = self.settings.SUPPORTED_ASSETS[to_asset]["asa_id"]
            
            # âœ… Execute swap via DeFi service with DECRYPTED key
            tx_id = await self.dex_service.execute_swap(
                user_address=user_address,
                user_private_key=decrypted_private_key,  # âœ… NOW DECRYPTED
                from_asset_id=from_asa_id,
                to_asset_id=to_asa_id,
                amount_in=amount_in,
                min_amount_out=min_amount_out
            )
            
            logger.info(f"âœ… Swap executed successfully: {tx_id}")
            return tx_id
            
        except Exception as e:
            logger.error(f"DEX swap execution failed: {e}", exc_info=True)
            raise
        
    async def _get_price_ratio(self, from_asset: str, to_asset: str) -> Decimal:
        """
        Fallback: Get price ratio from oracle service
        """
        # Use oracle service for pricing
        from_price = await self.algorand_service.get_asset_price(from_asset)
        to_price = await self.algorand_service.get_asset_price(to_asset)
        
        return from_price / to_price