# File: backend/config.py
"""
SEAMOUNT MULTI-CHAIN BUSINESS MODEL CONFIGURATION
Post-WDK Integration: Algorand + Bitcoin + Ethereum + TON + Lightning Network
Revenue Optimization: B2C + B2B API Licensing
"""

import logging
import os
from typing import List, Optional, Dict, Tuple, Set, Any
from decimal import Decimal
from pydantic import SecretStr, computed_field, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# ENUMS & TYPE DEFINITIONS
# ============================================================================

class LicenseTier(str, Enum):
    """B2B API Licensing Tiers - Premium Pricing"""
    BUILDER = "builder"      # $3,500/month
    SCALE = "scale"          # $7,500/month  
    ENTERPRISE = "enterprise" # $15,000+/month (custom)

class UserTier(str, Enum):
    """B2C User Tiers - Transaction Fee Optimization"""
    STANDARD = "standard"    # 0% discount
    PREMIUM = "premium"      # 10% discount (paid subscription)
    BUSINESS = "business"    # 15% discount (high volume)

class BlockchainNetwork(str, Enum):
    """Supported Blockchain Networks (Post-WDK Integration)"""
    ALGORAND = "algorand"
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    BITCOIN = "bitcoin"
    LIGHTNING = "lightning"  # Bitcoin Lightning Network
    TON = "ton"
    SOLANA = "solana"        # Future
    TRON = "tron"            # Future

class TransactionType(str, Enum):
    """Transaction Types with Different Fee Structures"""
    CROSS_BORDER = "cross_border"
    ON_RAMP = "on_ramp"
    OFF_RAMP = "off_ramp"
    P2P_LOCAL = "p2p_local"
    ASSET_SWAP = "asset_swap"
    LIGHTNING_PAYMENT = "lightning_payment"
    MULTI_CHAIN_BRIDGE = "multi_chain_bridge"

class PricingRegion(str, Enum):
    """Regional Pricing Optimization"""
    NIGERIA = "nigeria"
    KENYA = "kenya"
    GHANA = "ghana"
    SOUTH_AFRICA = "south_africa"
    GLOBAL = "global"

# ============================================================================
# MULTI-CHAIN BUSINESS MODEL CONFIGURATION
# ============================================================================

class MultiChainBusinessModel:
    """
    Enhanced Business Model with Multi-Chain Revenue Streams
    
    KEY PRINCIPLES:
    1. Abstract ALL blockchain complexity from users
    2. Optimize routing for lowest cost + fastest settlement
    3. Premium B2B API pricing ($3.5k-$15k/month)
    4. Competitive B2C transaction fees (2.5-2.9%)
    5. Hidden revenue optimization (gas markups, spreads)
    """
    
    # ========================================================================
    # B2C TRANSACTION FEES (User-Facing)
    # ========================================================================
    
    TRANSACTION_FEES = {
        TransactionType.CROSS_BORDER: Decimal("0.029"),      # 2.9% (competitive)
        TransactionType.ON_RAMP: Decimal("0.025"),           # 2.5% (premium justified)
        TransactionType.OFF_RAMP: Decimal("0.028"),          # 2.8% (bank withdrawal)
        TransactionType.P2P_LOCAL: Decimal("0.008"),         # 0.8% (speed premium)
        TransactionType.ASSET_SWAP: Decimal("0.012"),        # 1.2% (average)
        TransactionType.LIGHTNING_PAYMENT: Decimal("0.005"), # 0.5% (micropayments)
        TransactionType.MULTI_CHAIN_BRIDGE: Decimal("0.015") # 1.5% (bridge fee)
    }
    
    # Minimum Fees (Prevent dust transactions)
    MINIMUM_FEES = {
        TransactionType.CROSS_BORDER: Decimal("2.50"),
        TransactionType.ON_RAMP: Decimal("1.50"),
        TransactionType.OFF_RAMP: Decimal("2.00"),
        TransactionType.P2P_LOCAL: Decimal("0.50"),
        TransactionType.ASSET_SWAP: Decimal("0.75"),
        TransactionType.LIGHTNING_PAYMENT: Decimal("0.10"),
        TransactionType.MULTI_CHAIN_BRIDGE: Decimal("1.00")
    }
    
    # User Tier Discounts (Loyalty rewards)
    USER_TIER_DISCOUNTS = {
        UserTier.STANDARD: Decimal("0.00"),   # 0% discount
        UserTier.PREMIUM: Decimal("0.10"),    # 10% discount ($9.99/month subscription)
        UserTier.BUSINESS: Decimal("0.15")    # 15% discount (>$50k monthly volume)
    }
    
    # ========================================================================
    # HIDDEN REVENUE OPTIMIZATION (Backend Only - Never Shown to Users)
    # ========================================================================
    
    # Gas Fee Markups (Users see "Network Fee", we pocket the markup)
    GAS_FEE_MARKUPS = {
        BlockchainNetwork.ALGORAND: Decimal("0.50"),    # 50% markup ($0.001 → $0.0015)
        BlockchainNetwork.ETHEREUM: Decimal("0.25"),    # 25% markup (high base cost)
        BlockchainNetwork.POLYGON: Decimal("0.40"),     # 40% markup
        BlockchainNetwork.ARBITRUM: Decimal("0.35"),    # 35% markup
        BlockchainNetwork.BITCOIN: Decimal("0.30"),     # 30% markup
        BlockchainNetwork.LIGHTNING: Decimal("0.60"),   # 60% markup (tiny amounts)
        BlockchainNetwork.TON: Decimal("0.45")          # 45% markup
    }
    
    # Base Gas Costs (Actual blockchain costs - we add markup on top)
    BASE_GAS_COSTS = {
        BlockchainNetwork.ALGORAND: Decimal("0.001"),
        BlockchainNetwork.ETHEREUM: Decimal("0.50"),    # Variable, this is conservative
        BlockchainNetwork.POLYGON: Decimal("0.01"),
        BlockchainNetwork.ARBITRUM: Decimal("0.05"),
        BlockchainNetwork.BITCOIN: Decimal("0.25"),     # Variable
        BlockchainNetwork.LIGHTNING: Decimal("0.001"),  # Micropayment fees
        BlockchainNetwork.TON: Decimal("0.01")
    }
    
    # FX Spread Capture (Hidden in exchange rates)
    FX_SPREAD_MARKUP = Decimal("0.004")  # 0.4% hidden spread on FX conversions
    
    # Yield Spread (Staking/DeFi earnings - we share portion with users)
    YIELD_SHARING = {
        "user_share": Decimal("0.75"),      # Users get 75% of yield
        "platform_share": Decimal("0.25")    # We keep 25%
    }
    
    # ========================================================================
    # B2B API LICENSING (Premium Enterprise Pricing)
    # ========================================================================
    
    API_LICENSE_PRICING = {
        LicenseTier.BUILDER: {
            "monthly_fee": Decimal("3500.00"),
            "api_call_limit": 50_000,
            "volume_cap_usd": Decimal("1_000_000"),
            "chains_included": [BlockchainNetwork.ALGORAND],
            "support_sla_hours": 48,
            "transaction_fee_rate": Decimal("0.012"),  # 1.2%
            "features": [
                "Basic API access",
                "Standard documentation",
                "Community support",
                "Single chain integration",
                "Email support"
            ]
        },
        LicenseTier.SCALE: {
            "monthly_fee": Decimal("7500.00"),
            "api_call_limit": 200_000,
            "volume_cap_usd": Decimal("10_000_000"),
            "chains_included": "all",  # All supported chains
            "support_sla_hours": 12,
            "transaction_fee_rate": Decimal("0.008"),  # 0.8%
            "features": [
                "Full API access",
                "Multi-chain integration",
                "Priority support",
                "Custom branding/whitelabeling",
                "Dedicated account manager",
                "Advanced analytics dashboard",
                "Webhook notifications",
                "Sandbox environment"
            ]
        },
        LicenseTier.ENTERPRISE: {
            "monthly_fee": Decimal("15000.00"),  # Base price
            "api_call_limit": None,  # Unlimited
            "volume_cap_usd": None,  # Unlimited
            "chains_included": "all",
            "support_sla_hours": 4,
            "transaction_fee_rate": Decimal("0.005"),  # 0.5%
            "features": [
                "Unlimited API access",
                "All chains + priority access to new chains",
                "24/7 premium support",
                "99.9% uptime SLA",
                "Custom feature development",
                "Regulatory compliance assistance",
                "Dedicated infrastructure",
                "White-glove onboarding",
                "Custom rate limits",
                "Advanced security features"
            ]
        }
    }
    
    # API Usage Overage Fees (When limits exceeded)
    API_OVERAGE_PRICING = {
        LicenseTier.BUILDER: Decimal("0.05"),   # $0.05 per additional API call
        LicenseTier.SCALE: Decimal("0.03"),     # $0.03 per additional API call
        LicenseTier.ENTERPRISE: Decimal("0.00")  # No overage (unlimited)
    }
    
    # ========================================================================
    # MULTI-CHAIN SWAP FEES (Asset Exchange)
    # ========================================================================
    
    SWAP_FEE_STRUCTURE = {
        "stable_to_stable": Decimal("0.008"),        # USDT ↔ USDCa (0.8%)
        "stable_to_volatile": Decimal("0.012"),      # USDT → BTC (1.2%)
        "volatile_to_stable": Decimal("0.012"),      # BTC → USDT (1.2%)
        "volatile_to_volatile": Decimal("0.018"),    # BTC ↔ ETH (1.8%)
        "cross_chain_swap": Decimal("0.020")         # BTC (Bitcoin) → ETH (Ethereum) (2.0%)
    }
    
    # Bridge Fees (Moving assets between chains)
    BRIDGE_FEES = {
        "algorand_to_ethereum": Decimal("0.015"),
        "ethereum_to_algorand": Decimal("0.015"),
        "bitcoin_to_lightning": Decimal("0.005"),
        "lightning_to_bitcoin": Decimal("0.005"),
        "default": Decimal("0.015")
    }
    
    # ========================================================================
    # PROVIDER COST TRACKING (For Profitability Analysis)
    # ========================================================================
    
    PROVIDER_COSTS = {
        "wdk_api_call": Decimal("0.001"),           # Estimated Tether WDK cost
        "algorand_node": Decimal("0.001"),
        "cashramp_p2p": Decimal("0.012"),
        "paystack_onramp": Decimal("0.015"),
        "kyc_per_user": Decimal("2.00"),
        "lightning_node": Decimal("0.0005"),
        "operational_buffer": Decimal("0.003")
    }
    
    # ========================================================================
    # SMART ROUTING LOGIC (Optimize Cost + Speed)
    # ========================================================================
    
    @staticmethod
    def calculate_optimal_chain(
        transaction_type: TransactionType,
        amount: Decimal,
        from_asset: Optional[str] = None,
        to_asset: Optional[str] = None,
        destination_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Smart routing: Select optimal blockchain for transaction
        
        PRIORITY:
        1. Lightning Network for BTC micropayments (<$100)
        2. Polygon for Ethereum-based stablecoins (low gas)
        3. Algorand for USDS/USDCa transfers (native)
        4. Bitcoin for large BTC transfers (>$10k)
        5. Ethereum for DeFi integrations
        """
        
        # Lightning for small Bitcoin payments
        if from_asset == "BTC" and amount < Decimal("100"):
            return {
                "chain": BlockchainNetwork.LIGHTNING,
                "estimated_fee": MultiChainBusinessModel.BASE_GAS_COSTS[BlockchainNetwork.LIGHTNING],
                "estimated_time": "instant (<1 second)",
                "reason": "Lightning Network optimal for Bitcoin micropayments"
            }
        
        # Algorand for USDS native operations
        if from_asset in ["USDS", "USDCa"] or to_asset in ["USDS", "USDCa"]:
            return {
                "chain": BlockchainNetwork.ALGORAND,
                "estimated_fee": MultiChainBusinessModel.BASE_GAS_COSTS[BlockchainNetwork.ALGORAND],
                "estimated_time": "4.5 seconds",
                "reason": "Algorand native for USDS/USDCa"
            }
        
        # Polygon for Ethereum stablecoins (cheap gas)
        if from_asset in ["USDT", "USDC"] and transaction_type != TransactionType.MULTI_CHAIN_BRIDGE:
            return {
                "chain": BlockchainNetwork.POLYGON,
                "estimated_fee": MultiChainBusinessModel.BASE_GAS_COSTS[BlockchainNetwork.POLYGON],
                "estimated_time": "2 seconds",
                "reason": "Polygon L2 for low-cost stablecoin transfers"
            }
        
        # Bitcoin for large BTC transfers
        if from_asset == "BTC" and amount >= Decimal("10000"):
            return {
                "chain": BlockchainNetwork.BITCOIN,
                "estimated_fee": MultiChainBusinessModel.BASE_GAS_COSTS[BlockchainNetwork.BITCOIN],
                "estimated_time": "10 minutes (1 confirmation)",
                "reason": "Bitcoin mainnet for large, secure transfers"
            }
        
        # Default to Algorand (our moat)
        return {
            "chain": BlockchainNetwork.ALGORAND,
            "estimated_fee": MultiChainBusinessModel.BASE_GAS_COSTS[BlockchainNetwork.ALGORAND],
            "estimated_time": "4.5 seconds",
            "reason": "Algorand default - fast, cheap, reliable"
        }
    
    # ========================================================================
    # FEE CALCULATION ENGINE (CRITICAL - Used by all services)
    # ========================================================================
    
    @staticmethod
    def calculate_total_fee(
        transaction_type: TransactionType,
        amount: Decimal,
        user_tier: UserTier = UserTier.STANDARD,
        from_asset: Optional[str] = None,
        to_asset: Optional[str] = None,
        blockchain: Optional[BlockchainNetwork] = None
    ) -> Dict[str, Decimal]:
        """
        Calculate complete fee breakdown (ABSTRACT FROM USERS)
        
        Returns:
        - platform_fee: User-visible transaction fee
        - network_fee: User-visible "blockchain fee" (includes our markup)
        - total_fee: Total charged to user
        - hidden_markup: Our profit margin (NEVER shown to user)
        - net_revenue: Actual profit after provider costs
        """
        
        # Get base fee rate
        base_fee_rate = MultiChainBusinessModel.TRANSACTION_FEES.get(
            transaction_type, 
            Decimal("0.015")
        )
        
        # Calculate platform fee
        platform_fee = amount * base_fee_rate
        
        # Apply minimum fee
        minimum_fee = MultiChainBusinessModel.MINIMUM_FEES.get(
            transaction_type,
            Decimal("0.50")
        )
        if platform_fee < minimum_fee:
            platform_fee = minimum_fee
        
        # Apply user tier discount
        discount_rate = MultiChainBusinessModel.USER_TIER_DISCOUNTS[user_tier]
        discount_amount = platform_fee * discount_rate
        platform_fee_discounted = platform_fee - discount_amount
        
        # Determine blockchain (if not specified)
        if not blockchain:
            routing = MultiChainBusinessModel.calculate_optimal_chain(
                transaction_type, amount, from_asset, to_asset
            )
            blockchain = routing["chain"]
        
        # Calculate network fee (actual cost + markup)
        base_gas_cost = MultiChainBusinessModel.BASE_GAS_COSTS.get(
            blockchain,
            Decimal("0.01")
        )
        gas_markup = MultiChainBusinessModel.GAS_FEE_MARKUPS.get(
            blockchain,
            Decimal("0.35")
        )
        
        network_fee_actual = base_gas_cost
        network_fee_charged = base_gas_cost * (Decimal("1") + gas_markup)
        hidden_gas_markup = network_fee_charged - network_fee_actual
        
        # Total fee shown to user
        total_fee_user = platform_fee_discounted + network_fee_charged
        
        # Calculate provider costs
        provider_cost = MultiChainBusinessModel._estimate_provider_cost(
            transaction_type, amount
        )
        
        # Net revenue (our actual profit)
        net_revenue = platform_fee_discounted + hidden_gas_markup - provider_cost - network_fee_actual
        
        return {
            "platform_fee": float(platform_fee_discounted),
            "network_fee": float(network_fee_charged),
            "total_fee": float(total_fee_user),
            "discount_applied": float(discount_amount),
            "hidden_markup": float(hidden_gas_markup),
            "net_revenue": float(net_revenue),
            "profit_margin_percent": float((net_revenue / total_fee_user * 100)) if total_fee_user > 0 else 0,
            "blockchain": blockchain.value,
            "breakdown": {
                "user_pays": float(total_fee_user),
                "actual_cost": float(provider_cost + network_fee_actual),
                "profit": float(net_revenue)
            }
        }
    
    @staticmethod
    def calculate_cross_border_economics(
        amount: Decimal = Decimal("1000.00"),
        from_currency: str = "NGN",
        to_currency: str = "USD",
        from_country: str = "nigeria",
        to_country: str = "kenya"
    ) -> Dict[str, Any]:
        """
        Calculate cross-border payment economics
        Used for business model validation during startup
        """
        
        # Base cross-border fee
        fee_rate = MultiChainBusinessModel.TRANSACTION_FEES[TransactionType.CROSS_BORDER]
        platform_fee = amount * fee_rate
        
        # Apply minimum fee
        min_fee = MultiChainBusinessModel.MINIMUM_FEES[TransactionType.CROSS_BORDER]
        if platform_fee < min_fee:
            platform_fee = min_fee
        
        # FX spread (hidden revenue)
        fx_spread = amount * MultiChainBusinessModel.FX_SPREAD_MARKUP
        
        # Network fee (with markup)
        network_fee_actual = Decimal("0.001")  # Algorand default
        network_fee_charged = network_fee_actual * Decimal("1.50")  # 50% markup
        
        # Total to user
        total_fee = platform_fee + network_fee_charged + fx_spread
        
        # Revenue breakdown
        gross_revenue = platform_fee + fx_spread + (network_fee_charged - network_fee_actual)
        provider_cost = amount * Decimal("0.012")  # Cashramp P2P cost
        net_revenue = gross_revenue - provider_cost - network_fee_actual
        
        return {
            "amount": float(amount),
            "platform_fee": float(platform_fee),
            "fx_spread": float(fx_spread),
            "network_fee": float(network_fee_charged),
            "total_fee": float(total_fee),
            "gross_revenue": float(gross_revenue),
            "net_revenue": float(net_revenue),
            "profit_margin": float((net_revenue / total_fee * 100)) if total_fee > 0 else 0,
            "route": "Algorand",
            "from_country": from_country,
            "to_country": to_country
        }

    @staticmethod
    def _estimate_provider_cost(transaction_type: TransactionType, amount: Decimal) -> Decimal:
        """Estimate provider costs for profitability tracking"""
        
        if transaction_type == TransactionType.CROSS_BORDER:
            return amount * MultiChainBusinessModel.PROVIDER_COSTS["cashramp_p2p"]
        elif transaction_type == TransactionType.ON_RAMP:
            return amount * MultiChainBusinessModel.PROVIDER_COSTS["paystack_onramp"]
        elif transaction_type == TransactionType.LIGHTNING_PAYMENT:
            return MultiChainBusinessModel.PROVIDER_COSTS["lightning_node"]
        else:
            return amount * MultiChainBusinessModel.PROVIDER_COSTS["operational_buffer"]
    
    # ========================================================================
    # B2B API REVENUE PROJECTIONS
    # ========================================================================
    
    @staticmethod
    def project_api_revenue(
        license_tier: LicenseTier,
        monthly_api_calls: int,
        monthly_volume_usd: Decimal
    ) -> Dict[str, Any]:
        """
        Calculate monthly revenue from API licensing client
        
        Example: Kenyan Microfinance Bank
        - Tier: SCALE ($7,500/month)
        - API Calls: 150,000/month
        - Volume: $5M/month
        
        Revenue: $7,500 (license) + $40,000 (0.8% × $5M) = $47,500/month
        """
        
        tier_config = MultiChainBusinessModel.API_LICENSE_PRICING[license_tier]
        
        # Base license fee
        license_revenue = tier_config["monthly_fee"]
        
        # API overage fees
        overage_revenue = Decimal("0")
        call_limit = tier_config["api_call_limit"]
        if call_limit and monthly_api_calls > call_limit:
            overage_calls = monthly_api_calls - call_limit
            overage_rate = MultiChainBusinessModel.API_OVERAGE_PRICING[license_tier]
            overage_revenue = Decimal(str(overage_calls)) * overage_rate
        
        # Transaction fees on volume
        transaction_fee_rate = tier_config["transaction_fee_rate"]
        transaction_revenue = monthly_volume_usd * transaction_fee_rate
        
        # Total revenue
        total_monthly_revenue = license_revenue + overage_revenue + transaction_revenue
        annual_revenue = total_monthly_revenue * 12
        
        return {
            "license_tier": license_tier.value,
            "revenue_breakdown": {
                "license_fee": float(license_revenue),
                "overage_fees": float(overage_revenue),
                "transaction_fees": float(transaction_revenue),
                "total_monthly": float(total_monthly_revenue),
                "total_annual": float(annual_revenue)
            },
            "usage_stats": {
                "api_calls": monthly_api_calls,
                "volume_usd": float(monthly_volume_usd),
                "overage_calls": monthly_api_calls - call_limit if call_limit else 0
            },
            "economics": {
                "effective_rate": float(transaction_fee_rate),
                "avg_revenue_per_call": float(total_monthly_revenue / monthly_api_calls) if monthly_api_calls > 0 else 0
            }
        }

# ============================================================================
# PYDANTIC SETTINGS CLASS (Environment Configuration)
# ============================================================================

class Settings(BaseSettings):
    """Enhanced Seamount Settings with WDK Integration"""
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), '.env'),
        env_file_encoding='utf-8',
        extra="allow",
        case_sensitive=False
    )

    # Core Security
    DATABASE_URL: SecretStr = Field(default="postgresql://user:password@localhost:5432/seamount")
    ENCRYPTION_KEY: SecretStr = Field(default="default-encryption-key-change-in-production")
    IPINFO_TOKEN: Optional[SecretStr] = None
    
    # Supabase
    SUPABASE_URL: str = Field(default="https://your-supabase-url.supabase.co")
    SUPABASE_SERVICE_KEY: SecretStr = Field(default="your-supabase-service-key")
    SUPABASE_JWKS_URI: str = Field(default="https://your-supabase-url.supabase.co/auth/v1/jwks")
    SUPABASE_JWT_ISSUER: str = Field(default="https://your-supabase-url.supabase.co")

    # ========================================================================
    # TETHER WDK CONFIGURATION (NEW)
    # ========================================================================
    # Your deployed WDK microservice (handles wallet creation, signing)
    WDK_SERVICE_URL: str = Field(
        default="https://seamount-wdk.onrender.com",
        description="Your deployed WDK microservice (Node.js)"
    )

    # Official Tether WDK Indexer API (balances, transfers, history)
    WDK_API_URL: str = Field(
        default="https://wdk-api.tether.io",
        description="Official Tether WDK Indexer API for blockchain queries"
    )

    # WDK API Key - Get from: https://wdk-api.tether.io/register
    WDK_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description="Tether WDK API Key from https://wdk-api.tether.io"
    )

    # Supported chains via WDK
    WDK_ENABLED_CHAINS: List[str] = Field(default=[
        "bitcoin", "lightning", "ethereum", "polygon", 
        "arbitrum", "ton", "tron", "solana"
    ])

    # Alchemy Configuration (for Ethereum, Polygon, Arbitrum)
    ALCHEMY_API_KEY_ETHEREUM: Optional[SecretStr] = Field(
        default=None,
        description="Alchemy API key for Ethereum mainnet"
    )

    ALCHEMY_API_KEY_POLYGON: Optional[SecretStr] = Field(
        default=None,
        description="Alchemy API key for Polygon"
    )

    ALCHEMY_API_KEY_ARBITRUM: Optional[SecretStr] = Field(
        default=None,
        description="Alchemy API key for Arbitrum"
    )

    # Default chain for new wallets
    WDK_DEFAULT_CHAIN: str = Field(default="ethereum")
    
    # ========================================================================
    # ALGORAND CONFIGURATION (Existing - Keep)
    # ========================================================================
    ALGORAND_ALGOD_ADDRESS: str = Field(default="https://mainnet-api.algonode.cloud")
    ALGORAND_INDEXER_ADDRESS: str = Field(default="https://mainnet-idx.algonode.cloud")
    ALGORAND_ALGOD_TOKEN: Optional[SecretStr] = Field(default=None)
    ALGORAND_API_KEY: Optional[SecretStr] = Field(default=None)
    ALGORAND_CREATOR_MNEMONIC: Optional[SecretStr] = None
    ALGORAND_NETWORK: str = Field(default="mainnet")

    # Supported Assets (Multi-Chain)
    SUPPORTED_ASSETS: Dict[str, Dict[str, Any]] = {
        # Algorand Assets
        "USDS": {
            "blockchain": "algorand",
            "asset_id": 3127280978,
            "name": "Seamount USD",
            "unit_name": "USDS",
            "decimals": 6,
            "is_stable": True
        },
        "USDT_ALGO": {
            "blockchain": "algorand",
            "asset_id": 312769,
            "name": "Tether USD (Algorand)",
            "unit_name": "USDT",
            "decimals": 6,
            "is_stable": True
        },
        "USDCa": {
            "blockchain": "algorand",
            "asset_id": 31566704,
            "name": "USD Coin (Algorand)",
            "unit_name": "USDCa",
            "decimals": 6,
            "is_stable": True
        },
        # Ethereum Assets (via WDK)
        "USDT_ETH": {
            "blockchain": "ethereum",
            "contract_address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
            "name": "Tether USD (Ethereum)",
            "decimals": 6,
            "is_stable": True
        },
        "USDC_ETH": {
            "blockchain": "ethereum",
            "contract_address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            "name": "USD Coin (Ethereum)",
            "decimals": 6,
            "is_stable": True
        },
        # Bitcoin (via WDK)
        "BTC": {
            "blockchain": "bitcoin",
            "name": "Bitcoin",
            "decimals": 8,
            "is_stable": False
        },
        # Ethereum (via WDK)
        "ETH": {
            "blockchain": "ethereum",
            "name": "Ethereum",
            "decimals": 18,
            "is_stable": False
        }
    }

    # Treasury
    TREASURY_ADDRESS: Optional[str] = None
    TREASURY_PRIVATE_KEY: Optional[SecretStr] = None

    # Payment Providers
    PAYSTACK_PUBLIC_KEY: Optional[SecretStr] = None
    PAYSTACK_SECRET_KEY: Optional[SecretStr] = None
    PAYSTACK_WEBHOOK_SECRET: Optional[SecretStr] = None
    FLUTTERWAVE_SECRET_KEY: Optional[SecretStr] = None
    FLUTTERWAVE_PUBLIC_KEY: Optional[str] = None
    
    # KYC Provider (Regfyl)
    REGFYL_API_KEY: Optional[SecretStr] = None
    REGFYL_BASE_URL: str = Field(default="https://api.portal.regfyl.com")
    REGFYL_COMPANY_NAME: str = Field(default="Frontwater-Tech Development Ventures Nigeria Limited")
    REGFYL_RC_NUMBER: str = Field(default="1258168")
    
    # Redis (Upstash)
    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[SecretStr] = None
    
    # Email
    MAIL_SERVER: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[SecretStr] = None
    MAIL_FROM: Optional[str] = None
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    
    # CORS
    ALLOWED_ORIGINS_STR: str = ""
    
    # API Keys (B2B)
    WHITELISTED_API_KEYS_STR: str = ""

    # Operational
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_BASE_URL: str = Field(default="https://seamount-api.onrender.com")
    FRONTEND_URL: str = Field(default="http://localhost:3000")
    
    # Business Model
    DEFAULT_PRICING_REGION: PricingRegion = PricingRegion.NIGERIA
    ENABLE_DYNAMIC_PRICING: bool = True
    TRACK_REVENUE_METRICS: bool = True
    
    def validate_supabase_credentials(self) -> bool:
        """Validate Supabase credentials are present and properly formatted"""
        if not self.SUPABASE_URL or not self.SUPABASE_SERVICE_KEY:
            logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        
        # Check URL format
        if not self.SUPABASE_URL.startswith("https://"):
            logger.error("Invalid SUPABASE_URL format")
            return False
        
        # Check key is not default
        key_value = self.SUPABASE_SERVICE_KEY.get_secret_value()
        if key_value == "your-supabase-service-key" or len(key_value) < 20:
            logger.error("Invalid SUPABASE_SERVICE_KEY")
            return False
        
        logger.info("✅ Supabase credentials validated")
        return True

    @computed_field
    @property
    def business_model(self) -> MultiChainBusinessModel:
        """Access to multi-chain business model"""
        return MultiChainBusinessModel()
    
    @computed_field
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Parse ALLOWED_ORIGINS_STR"""
        if not self.ALLOWED_ORIGINS_STR:
            return [
                "http://localhost:3000", 
                "http://localhost:5173", 
                "https://seamount.io", 
                "https://www.seamount.io",
                "https://seamount.vercel.app"
            ]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_STR.split(',')]
    
    @computed_field
    @property
    def WHITELISTED_API_KEYS(self) -> Set[str]:
        """Parse WHITELISTED_API_KEYS_STR"""
        if not self.WHITELISTED_API_KEYS_STR:
            return set()
        return {key.strip() for key in self.WHITELISTED_API_KEYS_STR.split(',')}

# Create settings instance
try:
    settings = Settings()
    logger.info("Settings loaded successfully")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"WDK Enabled: {bool(settings.WDK_API_KEY)}")
    logger.info(f"Supported Chains: Algorand + {', '.join(settings.WDK_ENABLED_CHAINS)}")
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    settings = Settings(_env_file=None)

def get_settings() -> Settings:
    return settings

BusinessModelConfig = MultiChainBusinessModel  # Backward compatibility

__all__ = [
    'get_settings', 
    'settings', 
    'MultiChainBusinessModel', 
    'LicenseTier',
    'UserTier', 
    'BlockchainNetwork',
    'TransactionType',
    'PricingRegion'
]