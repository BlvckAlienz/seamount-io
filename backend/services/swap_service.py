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

    # ASSET KEY MAPPING
    ASSET_KEY_MAPPING = {
        "USDT": "USDT_ALGO",
        "USDT_ETH": "USDT_ETH",
        "USDT_POLYGON": "USDT_POLYGON",
        "USDT_TRON": "USDT_TRON",
        "USDC_ETH": "USDC_ETH",
        "USDC_POLYGON": "USDC_POLYGON",
        "ALGO": "ALGO",
        "USDCa": "USDCa",
        "goBTC": "goBTC",
        "goETH": "goETH",
        "BTC": "BTC",
        "ETH": "ETH",
        "MATIC": "MATIC",
        "TRX": "TRX",
    }

    # ✅ FIXED: SUPPORTED SWAP PAIRS (Using backend keys)
    SUPPORTED_PAIRS = {
        "USDT_ALGO": ["ALGO", "USDCa", "goBTC", "goETH"],  # ✅ Changed
        "ALGO": ["USDT_ALGO", "USDCa", "goBTC", "goETH"],  # ✅ Changed
        "USDCa": ["ALGO", "USDT_ALGO", "goBTC", "goETH"],  # ✅ Changed
        "goBTC": ["ALGO", "USDT_ALGO", "USDCa", "goETH"],  # ✅ Changed
        "goETH": ["ALGO", "USDT_ALGO", "USDCa", "goBTC"],  # ✅ Changed
    }

    # NEW COMPETITIVE FEE STRUCTURE
    COMPETITIVE_FEE_STRUCTURE = {
        "stable_to_stable": Decimal("0.003"),
        "stable_to_volatile": Decimal("0.005"),
        "volatile_to_volatile": Decimal("0.008"),
        "with_yield_stake": Decimal("0.002"),
        "high_frequency": Decimal("0.001"),
        "cross_border": Decimal("0.012"),
    }
    
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
        
        # Initialize real DEX service (MainNet)
        self.dex_service = AlgorandDeFiService(
            algod_client=algorand_service.algod_client
        )
        
        logger.info("SwapService initialized with competitive fees")

    def _normalize_asset_key(self, asset: str) -> str:
        """
        Normalize asset key to match config
        Frontend sends: USDT
        Backend expects: USDT_ALGO
        """
        # ✅ ENHANCED: Use ASSET_KEY_MAPPING
        normalized = self.ASSET_KEY_MAPPING.get(asset, asset)
        
        if normalized != asset:
            logger.info(f"Asset normalization: {asset} -> {normalized}")
        
        return normalized

    def _determine_fee_tier(self, from_asset: str, to_asset: str, user_id: str = None) -> Decimal:
        """
        UPDATED: Competitive fee calculation
        Returns: Fee rate (e.g., 0.003 = 0.3%)
        """
        supported_assets = self.settings.SUPPORTED_ASSETS
        
        # Get asset configs
        from_config = supported_assets.get(from_asset, {})
        to_config = supported_assets.get(to_asset, {})
        
        from_stable = from_config.get("is_stable", False)
        to_stable = to_config.get("is_stable", False)
        
        # TIER 1: Asset type-based fees
        if from_stable and to_stable:
            fee_rate = self.COMPETITIVE_FEE_STRUCTURE["stable_to_stable"]
        elif from_stable or to_stable:
            fee_rate = self.COMPETITIVE_FEE_STRUCTURE["stable_to_volatile"]
        else:
            fee_rate = self.COMPETITIVE_FEE_STRUCTURE["volatile_to_volatile"]
        
        logger.info(f"Fee rate: {float(fee_rate * 100)}% for {from_asset}->{to_asset}")
        
        return fee_rate

    async def get_swap_quote(
        self, 
        from_asset: str, 
        to_asset: str, 
        amount: Decimal,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        ✅ UPDATED: With asset normalization
        """
        try:
            # ✅ STORE ORIGINAL NAMES (for frontend response)
            from_asset_original = from_asset
            to_asset_original = to_asset
            
            # ✅ NORMALIZE TO BACKEND KEYS
            from_asset = self._normalize_asset_key(from_asset)
            to_asset = self._normalize_asset_key(to_asset)
            
            logger.info(
                f"Swap quote request: {from_asset_original} -> {to_asset_original} "
                f"(normalized: {from_asset} -> {to_asset})"
            )
            
            # Validate swap pair
            if to_asset not in self.SUPPORTED_PAIRS.get(from_asset, []):
                valid_pairs = self.SUPPORTED_PAIRS.get(from_asset, [])
                logger.error(
                    f"Invalid pair: {from_asset}/{to_asset}. "
                    f"Valid pairs for {from_asset}: {valid_pairs}"
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Swap pair {from_asset_original}/{to_asset_original} not supported"
                )
            
            # Get asset configs
            from_asset_config = self.settings.SUPPORTED_ASSETS.get(from_asset)
            to_asset_config = self.settings.SUPPORTED_ASSETS.get(to_asset)
            
            if not from_asset_config:
                available = list(self.settings.SUPPORTED_ASSETS.keys())
                logger.error(f"Asset '{from_asset}' not in config. Available: {available[:5]}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Asset '{from_asset_original}' not configured"
                )
            
            if not to_asset_config:
                available = list(self.settings.SUPPORTED_ASSETS.keys())
                logger.error(f"Asset '{to_asset}' not in config. Available: {available[:5]}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Asset '{to_asset_original}' not configured"
                )
            
            from_asset_id = from_asset_config["asset_id"]
            to_asset_id = to_asset_config["asset_id"]
            
            logger.info(
                f"Fetching quote: {amount} {from_asset} (ID: {from_asset_id}) "
                f"-> {to_asset} (ID: {to_asset_id})"
            )
            
            # ✅ STEP 1: Get TRUE market rates from Oracle (95% confidence)
            logger.info(f"🔍 Fetching Oracle prices for {from_asset}/{to_asset}")

            try:
                # Get USD prices for both assets
                from_asset_oracle = from_asset_config.get("oracle_symbol", from_asset.lower())
                to_asset_oracle = to_asset_config.get("oracle_symbol", to_asset.lower())
                
                # Use our battle-tested Oracle service
                from_price_usd, from_meta = await self.algorand_service.oracle_service.get_asset_price(from_asset_oracle)
                to_price_usd, to_meta = await self.algorand_service.oracle_service.get_asset_price(to_asset_oracle)
                
                # Calculate TRUE exchange rate
                oracle_exchange_rate = from_price_usd / to_price_usd
                oracle_amount_out = amount * oracle_exchange_rate
                
                logger.info(
                    f"📊 Oracle Rates:\n"
                    f"  {from_asset}: ${from_price_usd} (source: {from_meta.get('source')})\n"
                    f"  {to_asset}: ${to_price_usd} (source: {to_meta.get('source')})\n"
                    f"  Exchange Rate: 1 {from_asset} = {oracle_exchange_rate:.6f} {to_asset}\n"
                    f"  Expected Output: {oracle_amount_out:.6f} {to_asset}"
                )
                
            except Exception as oracle_err:
                logger.error(f"❌ Oracle price fetch failed: {oracle_err}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Price oracle unavailable: {str(oracle_err)}"
                )

            # ✅ STEP 2: Get Pact DEX quote (for liquidity/fees info)
            try:
                dex_quote = await self.dex_service.get_swap_quote(
                    from_asset_id=from_asset_id,
                    to_asset_id=to_asset_id,
                    amount_in=amount
                )
                
                # Extract Pact data
                pact_amount_out = Decimal(str(dex_quote["amount_out"]))
                pact_exchange_rate = Decimal(str(dex_quote.get("exchange_rate", 0)))
                price_impact = Decimal(str(dex_quote["price_impact"]))
                
                logger.info(
                    f"🔗 Pact DEX Quote:\n"
                    f"  Amount Out: {pact_amount_out:.6f} {to_asset}\n"
                    f"  Exchange Rate: {pact_exchange_rate:.6f}\n"
                    f"  Price Impact: {price_impact:.2f}%"
                )
                
            except Exception as pact_err:
                logger.warning(f"⚠️ Pact DEX failed: {pact_err}. Using Oracle-only quote.")
                # Fallback: Use pure Oracle quote
                pact_amount_out = oracle_amount_out
                pact_exchange_rate = oracle_exchange_rate
                price_impact = Decimal("0")

            # ✅ STEP 3: VALIDATE Pact vs Oracle (detect inversions)
            rate_difference_pct = abs(
                (pact_exchange_rate - oracle_exchange_rate) / oracle_exchange_rate * 100
            )

            logger.info(f"🔍 Rate Validation: {rate_difference_pct:.2f}% difference")

            # 🚨 CRITICAL: Detect inverted or broken rates
            if rate_difference_pct > 50:  # More than 50% off = likely inverted
                logger.error(
                    f"❌ INVERTED RATE DETECTED!\n"
                    f"  Oracle Rate: 1 {from_asset} = {oracle_exchange_rate:.6f} {to_asset}\n"
                    f"  Pact Rate:   1 {from_asset} = {pact_exchange_rate:.6f} {to_asset}\n"
                    f"  Difference: {rate_difference_pct:.2f}%\n"
                    f"  🔧 Using Oracle rate instead!"
                )
                
                # Use Oracle rate as truth
                exchange_rate = oracle_exchange_rate
                amount_out_before_fees = oracle_amount_out
                
                # Recalculate price impact based on liquidity (estimate)
                price_impact = min(Decimal("5"), amount / Decimal("10000")) # Rough estimate
                
            elif rate_difference_pct > 10:  # 10-50% off = warning
                logger.warning(
                    f"⚠️ Large rate discrepancy ({rate_difference_pct:.2f}%)\n"
                    f"  Using Oracle rate for safety"
                )
                exchange_rate = oracle_exchange_rate
                amount_out_before_fees = oracle_amount_out
                
            else:  # Within 10% = Pact is reliable
                logger.info(f"✅ Pact rate validated ({rate_difference_pct:.2f}% difference)")
                exchange_rate = oracle_exchange_rate  # Still use Oracle as base
                amount_out_before_fees = pact_amount_out  # But trust Pact's actual output
            
            # NEW COMPETITIVE FEE CALCULATION
            fee_rate = self._determine_fee_tier(from_asset, to_asset, user_id)
            
            # Calculate platform fee on OUTPUT amount
            platform_fee = amount_out_before_fees * fee_rate
            
            # Apply minimum fee
            if platform_fee < self.MINIMUM_FEE:
                platform_fee = self.MINIMUM_FEE
            
            # Calculate final amount out
            amount_out = amount_out_before_fees - platform_fee
            
            logger.info(
                f"Quote generated: {amount} {from_asset} -> {amount_out} {to_asset} "
                f"(Rate: 1 {from_asset} = {exchange_rate} {to_asset}, "
                f"Fee: {fee_rate*100}% = ${platform_fee})"
            )
            
            return {
                "from_asset": from_asset_original,  # ✅ Return original names
                "to_asset": to_asset_original,
                "amount_in": float(amount),
                "amount_out": float(amount_out),
                "amount_out_before_fees": float(amount_out_before_fees),
                "fee_amount": float(platform_fee),
                "fee_rate": float(fee_rate),
                "fee_percentage": float(fee_rate * 100),
                "exchange_rate": float(exchange_rate),
                "price_impact": float(price_impact),
                "min_amount_out": float(amount_out * Decimal("0.995")),
                "dex": dex_quote["dex"],
                "pool_id": dex_quote.get("pool_id"),
                "network_fee": 0.001,
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
        ADDED: Rate validation to prevent bad swaps
        """
        try:
            # ✅ NORMALIZE ASSET KEYS
            from_asset_original = from_asset
            to_asset_original = to_asset
            from_asset = self._normalize_asset_key(from_asset)
            to_asset = self._normalize_asset_key(to_asset)
            
            logger.info(
                f"Executing swap: {amount} {from_asset_original} -> {to_asset_original} "
                f"(normalized: {from_asset} -> {to_asset})"
            )
            
            # SAFETY CHECK 1: Max swap amount
            MAX_SWAP_AMOUNT = Decimal("1000.00")
            if amount > MAX_SWAP_AMOUNT:
                raise HTTPException(
                    status_code=400,
                    detail=f"Swap amount exceeds safety limit of ${MAX_SWAP_AMOUNT}"
                )
            
            # Get current wallet balances
            balances = await self.wallet_service.get_user_balances(user_id)
            
            # Check if user has sufficient balance (use original asset name for balance lookup)
            user_balance = balances.get(from_asset_original, Decimal("0"))
            if user_balance < amount:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient {from_asset_original} balance. Available: {user_balance}"
                )
            
            # Get swap quote (using original names, will normalize inside)
            quote = await self.get_swap_quote(from_asset_original, to_asset_original, amount, user_id)
            
            # SAFETY CHECK 2: Validate exchange rate makes sense
            exchange_rate = quote["exchange_rate"]
            
            RATE_VALIDATIONS = {
                ("USDT_ALGO", "ALGO"): (1.5, 5.0),    # 1 USDT = 1.5-5 ALGO
                ("ALGO", "USDT_ALGO"): (0.2, 0.7),    # 1 ALGO = $0.20-$0.70
                ("USDT_ALGO", "USDCa"): (0.98, 1.02), # 1 USDT = 0.98-1.02 USDC
            }
            
            if (from_asset, to_asset) in RATE_VALIDATIONS:
                min_rate, max_rate = RATE_VALIDATIONS[(from_asset, to_asset)]
                if exchange_rate < min_rate or exchange_rate > max_rate:
                    logger.error(
                        f"INVALID RATE: 1 {from_asset} = {exchange_rate} {to_asset} "
                        f"(expected {min_rate}-{max_rate})"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Exchange rate outside expected range "
                            f"({exchange_rate:.6f}). Please try again later."
                        )
                    )
            
            # SAFETY CHECK 3: Price impact limit
            if quote["price_impact"] > 0.10:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Price impact too high ({quote['price_impact']*100:.1f}%). "
                        f"Try a smaller amount."
                    )
                )
            
            # Execute real swap on Algorand DEX (use normalized keys)
            swap_tx_id = await self._execute_dex_swap(
                user_id=user_id,
                from_asset=from_asset,  # ✅ Use normalized key
                to_asset=to_asset,      # ✅ Use normalized key
                amount_in=amount,
                min_amount_out=Decimal(str(quote["min_amount_out"]))
            )
            
            # Update balances in database
            from_balance_new = balances[from_asset_original] - amount
            to_balance_new = balances.get(to_asset_original, Decimal("0")) + Decimal(str(quote["amount_out"]))
            
            # Log the swap transaction
            swap_log = {
                "user_id": user_id,
                "from_asset": from_asset_original,  # ✅ Log original names
                "to_asset": to_asset_original,
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
            
            # Track revenue
            await self.revenue_service.track_transaction_fee(
                user_id=user_id,
                transaction_type="swap",
                amount=amount,
                fee_rate=Decimal(str(quote["fee_rate"])),
                platform_fee=Decimal(str(quote["fee_amount"])),
                network_fee=Decimal("0.001"),
                blockchain="algorand",
                metadata={
                    "swap_pair": f"{from_asset_original}/{to_asset_original}",
                    "dex": quote["dex"]
                }
            )

            logger.info(
                f"Swap executed: {amount} {from_asset_original} -> {quote['amount_out']} {to_asset_original} "
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
        from_asset: str,  # Already normalized
        to_asset: str,    # Already normalized
        amount_in: Decimal,
        min_amount_out: Decimal
    ) -> str:
        """
        Execute swap on Algorand DEX using our DeFi service
        PRODUCTION: Uses same encryption pattern as multi_chain_wallet_service
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
                    "NO WALLET FOUND\n\n"
                    "You don't have an Algorand wallet yet.\n"
                    "Please create a wallet first in the dashboard."
                )
            
            user_address = wallet_result[0]["algorand_address"]
            encrypted_key = wallet_result[0]["algorand_private_key"]
            
            # DECRYPT PRIVATE KEY (Same pattern as multi_chain_wallet_service)
            try:
                decrypted_private_key = self.encryption_service.decrypt_seed(encrypted_key)
                logger.info(f"Successfully decrypted key for swap operation")
            except Exception as decrypt_err:
                logger.error(f"Private key decryption failed: {decrypt_err}")
                raise Exception(f"Failed to decrypt wallet credentials: {decrypt_err}")
            
            # Get ASA IDs from config (assets already normalized)
            from_asa_id = self.settings.SUPPORTED_ASSETS[from_asset]["asset_id"]
            to_asa_id = self.settings.SUPPORTED_ASSETS[to_asset]["asset_id"]
            
            # Execute swap via DeFi service with DECRYPTED key
            tx_id = await self.dex_service.execute_swap(
                user_address=user_address,
                user_private_key=decrypted_private_key,
                from_asset_id=from_asa_id,
                to_asset_id=to_asa_id,
                amount_in=amount_in,
                min_amount_out=min_amount_out
            )
            
            logger.info(f"Swap executed successfully: {tx_id}")
            return tx_id
            
        except Exception as e:
            logger.error(f"DEX swap execution failed: {e}", exc_info=True)
            raise