# File: backend/config.py
"""
SEAMOUNT MULTI-CHAIN BUSINESS MODEL CONFIGURATION
Post-WDK Integration: Algorand + Bitcoin + Ethereum + Tron + Polygon
Revenue Optimization: B2C + B2B API Licensing
"""

import logging
import os
from typing import List, Optional, Dict, Tuple, Set, Any
from decimal import Decimal
from pydantic import SecretStr, computed_field, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum

from pydantic import SecretStr

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# ENUMS & TYPE DEFINITIONS
# ============================================================================

class LicenseTier(str, Enum):
    """B2B API Licensing Tiers - Premium Pricing"""
    BUILDER = "builder"      # $3,500/year
    SCALE = "scale"          # $7,500/year  
    ENTERPRISE = "enterprise" # $15,000+/year (custom)

class BlockchainNetwork(str, Enum):
    """Supported Blockchain Networks (Post-WDK Integration)"""
    ALGORAND = "algorand"
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    BITCOIN = "bitcoin"
    TRON = "tron"
    SOLANA = "solana"
    XRP = "xrp"

class TransactionType(str, Enum):
    """Transaction Types with Different Fee Structures"""
    CROSS_BORDER = "cross_border"
    ON_RAMP = "on_ramp"
    OFF_RAMP = "off_ramp"
    P2P_LOCAL = "p2p_local"
    ASSET_SWAP = "asset_swap"
    MULTI_CHAIN_BRIDGE = "multi_chain_bridge"

class PricingRegion(str, Enum):
    """Regional Pricing Optimization"""
    NIGERIA = "nigeria"
    KENYA = "kenya"
    GHANA = "ghana"
    SOUTH_AFRICA = "south_africa"
    GLOBAL = "global"

# ── XRP Ledger Configuration ──────────────────────────────────────
XRP_NETWORK: str = "testnet"
XRP_HOT_WALLET_ADDRESS: str = "rDESzopPoPL2WbvEcBKqtZ1ztCs46i9NS1"
XRP_HOT_WALLET_SEED: str = "sEdTyYp1tFcGrnM8qiNUgJRgiHHgDS9"
XRP_DEFI_WALLET_ADDRESS: str = "rJyGL4wLvo1yfntabicJCV6hz8aVxagY71"
XRP_DEFI_WALLET_SEED: str = "sEd75hMDemdDpxASudax5yqqqmPMGvr"
XRP_ADMIN_WALLET_ADDRESS: str = "rMMK8CQ3JCs7gMeVem7FkWfgpGs4d22zeA"
XRP_ADMIN_WALLET_SEED: str = "sEdT8CMDmXnx5qPSav7XvWhM7B8Dr5Z"

# ============================================================================
# MULTI-CHAIN BUSINESS MODEL CONFIGURATION
# ============================================================================

class MultiChainBusinessModel:
    """
    Enhanced Business Model with Multi-Chain Revenue Streams
    
    KEY PRINCIPLES:
    1. Abstract ALL blockchain complexity from users
    2. Optimize routing for lowest cost + fastest settlement
    3. Premium B2B API pricing ($3.5k-$15k/year)
    4. Competitive B2C transaction fees (1.2-1.8%)
    5. Hidden revenue optimization (gas markups, spreads)
    """
    
    # ========================================================================
    # B2C TRANSACTION FEES (User-Facing) - UPDATED COMPETITIVE PRICING
    # ========================================================================
    
    TRANSACTION_FEES = {
        TransactionType.CROSS_BORDER: Decimal("0.012"),     # 1.2% (was 2.9%)
        TransactionType.ON_RAMP: Decimal("0.018"),          # 1.8% (was 2.5%)
        TransactionType.OFF_RAMP: Decimal("0.018"),         # 1.8% (was 2.8%)
        TransactionType.P2P_LOCAL: Decimal("0.007"),        # 0.7% (was 0.8%)
        TransactionType.ASSET_SWAP: Decimal("0.012"),       # 1.2% (unchanged)
        TransactionType.MULTI_CHAIN_BRIDGE: Decimal("0.015") # 1.5% (unchanged)
    }
    
    # Updated Minimum Fees - KEEP $2.00 FOR CASH-RAMP DEPENDENT TRANSACTIONS
    MINIMUM_FEES = {
        TransactionType.CROSS_BORDER: Decimal("2.00"),      # $2.00 min (Cashramp cap hedge)
        TransactionType.ON_RAMP: Decimal("0.75"),           # $0.75 min (was $1.50)
        TransactionType.OFF_RAMP: Decimal("2.00"),          # $2.00 min (Cashramp cap hedge)
        TransactionType.P2P_LOCAL: Decimal("0.25"),         # $0.25 min (was $0.50)
        TransactionType.ASSET_SWAP: Decimal("0.50"),        # $0.50 min (was $0.75)
        TransactionType.MULTI_CHAIN_BRIDGE: Decimal("0.75") # $0.75 min (was $1.00)
    }
    
    # ===================================================================
    # SEAMOUNT NET MARGINS (Investor-Grade: Profitable from Day 1)
    # These are OUR revenue after provider costs are paid
    # ===================================================================
    SEAMOUNT_NET_MARGINS = {
        "paystack_card": Decimal("0.005"),        # 0.5% net margin
        "paystack_bank": Decimal("0.005"),        # 0.5% net margin
        "flutterwave_card_local": Decimal("0.005"),   # 0.5% net margin
        "flutterwave_mobile_money": Decimal("0.006"), # 0.6% net margin
        "flutterwave_card_intl": Decimal("0.002")     # 0.2% net margin (still profitable)
    }

    # Provider actual costs (verified from testing + agreements)
    PROVIDER_BASE_COSTS = {
        "paystack": {
            "base_rate": Decimal("0.015"),      # 1.5%
            "flat_fee_ngn": Decimal("100"),     # NGN 100 flat
            "cap_ngn": Decimal("2000")          # Max NGN 2,000 cap
        },
        "flutterwave": {
            "card_local": Decimal("0.020"),          # 2.0% (verified from your testing)
            "card_intl": Decimal("0.038"),           # 3.8% international
            "mobile_money": Decimal("0.029"),        # 2.9% (verified from your testing)
            "bank": Decimal("0.020")                 # 2.0% bank transfer
        }
    }

    # Total user-facing fees (provider cost + Seamount margin)
    # These are what customers see in checkout
    USER_FACING_FEES = {
        "paystack_card": Decimal("0.025"),           # 2.5% total (2.0% Paystack avg + 0.5% Seamount)
        "paystack_bank": Decimal("0.025"),           # 2.5% total
        "flutterwave_card_local": Decimal("0.025"),  # 2.5% total (2.0% FW + 0.5% Seamount)
        "flutterwave_mobile_money": Decimal("0.035"), # 3.5% total (2.9% FW + 0.6% Seamount)
        "flutterwave_card_intl": Decimal("0.040")    # 4.0% total (3.8% FW + 0.2% Seamount)
    }
    # ========================================================================
    # HIDDEN REVENUE OPTIMIZATION (Backend Only - Never Shown to Users)
    # ========================================================================
    
    # Gas Fee Markups (Users see "Network Fee", we pocket the markup)
    GAS_FEE_MARKUPS = {
        BlockchainNetwork.ALGORAND: Decimal("0.50"),    # 50% markup ($0.001 → $0.0015)
        BlockchainNetwork.ETHEREUM: Decimal("0.25"),    # 25% markup (high base cost)
        BlockchainNetwork.POLYGON: Decimal("0.40"),     # 40% markup
        BlockchainNetwork.BITCOIN: Decimal("0.30"),     # 30% markup
        BlockchainNetwork.TRON: Decimal("0.35")         # 35% markup
    }
    
    # Base Gas Costs (Actual blockchain costs - we add markup on top)
    BASE_GAS_COSTS = {
        BlockchainNetwork.ALGORAND: Decimal("0.001"),
        BlockchainNetwork.ETHEREUM: Decimal("0.50"),    # Variable, this is conservative
        BlockchainNetwork.POLYGON: Decimal("0.01"),
        BlockchainNetwork.BITCOIN: Decimal("0.25"),     # Variable
        BlockchainNetwork.TRON: Decimal("0.001")
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
        "algorand_to_tron": Decimal("0.015"),
        "tron_to_algorand": Decimal("0.015"),
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
        "operational_buffer": Decimal("0.003")
    }
    
    # ========================================================================
    # SMART ROUTING LOGIC (Optimize Cost + Speed)
    # ========================================================================
    
    @staticmethod
    def calculate_total_fee(
        transaction_type: TransactionType,
        amount: Decimal,
        from_asset: Optional[str] = None,
        to_asset: Optional[str] = None,
        blockchain: Optional[BlockchainNetwork] = None
    ) -> Dict[str, Decimal]:
        """
        Calculate complete fee breakdown
        
        ✅ B2C users pay standard rates (NO TIERS, NO DISCOUNTS)
        ✅ B2B API users handled separately via licensing_service
        
        Returns:
        - platform_fee: User-visible transaction fee
        - network_fee: User-visible "blockchain fee" (includes markup)
        - total_fee: Total charged to user
        - hidden_markup: Our profit margin (NEVER shown)
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
        
        # ❌ REMOVED: All user tier discount logic
        # B2C users pay standard rates - NO DISCOUNTS
        platform_fee_final = platform_fee
        
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
        total_fee_user = platform_fee_final + network_fee_charged
        
        # Calculate provider costs
        provider_cost = MultiChainBusinessModel._estimate_provider_cost(
            transaction_type, amount
        )
        
        # Net revenue (our actual profit)
        net_revenue = platform_fee_final + hidden_gas_markup - provider_cost - network_fee_actual
        
        return {
            "platform_fee": float(platform_fee_final),
            "network_fee": float(network_fee_charged),
            "total_fee": float(total_fee_user),
            "discount_applied": 0.0,  # ✅ Always 0 for B2C
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
    
    # ✅ ADD: Separate method for B2B API customers (if needed):
    @staticmethod
    def calculate_api_customer_fee(
        transaction_type: str,
        amount: Decimal,
        license_tier: "LicenseTier",
        from_asset: Optional[str] = None,
        to_asset: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate fees for B2B API customers (different rates)
        """
        tier_config = MultiChainBusinessModel.API_LICENSE_PRICING[license_tier]
        transaction_fee_rate = tier_config["transaction_fee_rate"]
        
        platform_fee = amount * transaction_fee_rate
        
        # Minimum fee
        minimum_fee = Decimal("0.25")  # Lower for API customers
        if platform_fee < minimum_fee:
            platform_fee = minimum_fee
        
        # Network fees same as B2C
        base_gas = Decimal("0.01")
        network_fee = base_gas * Decimal("1.35")
        
        total_fee = platform_fee + network_fee
        
        return {
            "platform_fee": float(platform_fee),
            "network_fee": float(network_fee),
            "total_fee": float(total_fee),
            "license_tier": license_tier.value,
            "effective_rate": float(transaction_fee_rate)
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
        - Tier: SCALE ($7,500/year)
        - API Calls: 150,000/month
        - Volume: $5M/month
        
        Revenue: $40,000 (0.8% × $5M) = $40,000/month
        """
        
        tier_config = MultiChainBusinessModel.API_LICENSE_PRICING[license_tier]
        
        # Base license fee
        license_revenue = tier_config["yearly_fee"]
        
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
        total_monthly_revenue = overage_revenue + transaction_revenue
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
# KYC THRESHOLD CONFIGURATION (Phase 2)
# ============================================================================

class KYCConfig:
    """KYC requirement thresholds and enforcement rules"""
    
    # Cumulative transaction threshold
    THRESHOLD_USD = Decimal("100000.00")  # $100K cumulative (90 days)
    
    # Grace period before enforcement
    GRACE_PERIOD_DAYS = 90
    
    # Tracking window (rolling)
    TRACKING_WINDOW_DAYS = 90
    
    # Exemptions (for testing/VIP)
    EXEMPTED_USER_IDS: Set[str] = set()
    
    # Prompt timing
    WARNING_THRESHOLD = Decimal("90000.00")  # Show warning at $90K
    SOFT_BLOCK_THRESHOLD = Decimal("95000.00")  # Require acknowledgment at $95K
    HARD_BLOCK_THRESHOLD = Decimal("100000.00")  # Block transactions at $100K
    
    @staticmethod
    def calculate_remaining_limit(cumulative: Decimal) -> Decimal:
        """Calculate remaining transaction capacity"""
        return max(Decimal("0"), KYCConfig.THRESHOLD_USD - cumulative)
    
    @staticmethod
    def get_urgency_level(cumulative: Decimal) -> str:
        """Determine UI urgency level"""
        remaining = KYCConfig.calculate_remaining_limit(cumulative)
        
        if remaining <= Decimal("1000"):
            return "critical"  # Red banner
        elif remaining <= Decimal("5000"):
            return "warning"  # Orange banner
        elif remaining <= Decimal("10000"):
            return "info"  # Blue banner
        return "none"

# ============================================================================
# CENTRAL TREASURY ADDRESSES (Revenue Collection)
# Stored outside Settings class to avoid Pydantic validation
# ============================================================================
CENTRAL_TREASURY_ADDRESSES: Dict[str, str] = {
    'algorand': 'A2UV35WC4YB7BS2PXBCGMTCE2CM5N7HFUVZTD74B7UCCEY63KBKU6JUPLE',
    'bitcoin': 'bc1qcz6lh9zg0y8v2k9cns8napzqenu0ak5lx3pf03',
    'ethereum': '0x35186f2C63550f0EF35C28670947A0425879942b',
    'polygon': '0x561e9a01999dEFB7956D455053F3FE6f88D47291',
    'tron': 'TCX2tuTEoF5HKHpX4Sd7MZPNF1gum8Kox5'
}

# Validation function
def validate_treasury_addresses() -> bool:
    """Validate all treasury addresses are non-empty"""
    for chain, address in CENTRAL_TREASURY_ADDRESSES.items():
        if not address or len(address) < 20:
            logger.warning(f"⚠️ Treasury address for {chain} is empty or invalid")
            return False
    return True

# Validate on module load
if not validate_treasury_addresses():
    logger.error("❌ Some treasury addresses are invalid or missing")

# ============================================================================
# PYDANTIC SETTINGS CLASS (Environment Configuration)
# ============================================================================

class Settings(BaseSettings):
    """Enhanced Seamount Settings with WDK Integration"""
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), '.env'),
        env_file_encoding='utf-8',
        extra="allow",
        case_sensitive=False  # ✅ Match .env variable casing
    )

    # Core Security
    DATABASE_URL: SecretStr = Field(default="postgresql://user:password@localhost:5432/seamount")
    ENCRYPTION_KEY: SecretStr = Field(default="default-encryption-key-change-in-production")
    IPINFO_TOKEN: Optional[SecretStr] = None
    GROQ_API_KEY: Optional[SecretStr] = None
    
    # Supabase
    SUPABASE_URL: str = Field(default="https://your-supabase-url.supabase.co")
    SUPABASE_SERVICE_KEY: SecretStr = Field(default="your-supabase-service-key")
    SUPABASE_JWKS_URI: str = Field(default="https://your-supabase-url.supabase.co/auth/v1/jwks")
    SUPABASE_JWT_ISSUER: str = Field(default="https://your-supabase-url.supabase.co")

    # Etherscan API Keys (Rotation Pool)
    ETHERSCAN_API_KEY_1: Optional[SecretStr] = None
    ETHERSCAN_API_KEY_2: Optional[SecretStr] = None
    ETHERSCAN_API_KEY_3: Optional[SecretStr] = None
    
    # Legacy single key (for backward compatibility)
    ETHERSCAN_API_KEY: Optional[SecretStr] = None
    
    # KYC Configuration
    KYC_THRESHOLD_USD: Decimal = Field(
        default=Decimal("5000.00"),
        description="Cumulative transaction limit before KYC required"
    )
    
    KYC_GRACE_PERIOD_DAYS: int = Field(
        default=30,
        description="Days to complete KYC after triggering"
    )
    
    KYC_TRACKING_WINDOW_DAYS: int = Field(
        default=30,
        description="Rolling window for cumulative volume tracking"
    )

    # ========================================================================
    # TETHER WDK CONFIGURATION
    # ========================================================================
    WDK_SERVICE_URL: str = Field(
        default="https://seamount-wdk-ne5i.onrender.com",
        description="Your deployed WDK microservice (Node.js)"
    )

    WDK_API_URL: str = Field(
        default="https://wdk-api.tether.io",
        description="Official Tether WDK Indexer API for blockchain queries"
    )

    WDK_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description="Tether WDK API Key from https://wdk-api.tether.io"
    )

    WDK_NODE_API_KEY: Optional[SecretStr] = None  # For direct node access if needed (optional)

    # UPDATED: Only include our 5 supported chains
    WDK_ENABLED_CHAINS: List[str] = Field(default=[
        "bitcoin", "ethereum", "polygon", "tron"
    ])

    WDK_DEFAULT_CHAIN: str = Field(default="ethereum")

    # Alchemy Configuration (for Ethereum, Polygon)
    ALCHEMY_API_KEY_ETHEREUM: Optional[SecretStr] = Field(
        default=None,
        description="Alchemy API key for Ethereum mainnet"
    )

    ALCHEMY_API_KEY_POLYGON: Optional[SecretStr] = Field(
        default=None,
        description="Alchemy API key for Polygon"
    )

    SOLANA_RPC_URL: Optional[str] = "https://api.mainnet-beta.solana.com"
    
    # ========================================================================
    # ALGORAND CONFIGURATION
    # ========================================================================
    ALGORAND_ALGOD_ADDRESS: str = Field(default="https://mainnet-api.algonode.cloud")
    ALGORAND_INDEXER_ADDRESS: str = Field(default="https://mainnet-idx.algonode.cloud")
    ALGORAND_ALGOD_TOKEN: Optional[SecretStr] = Field(default=None)
    ALGORAND_API_KEY: Optional[SecretStr] = Field(default=None)
    ALGORAND_CREATOR_MNEMONIC: Optional[SecretStr] = None
    ALGORAND_NETWORK: str = Field(default="mainnet")

    # ========================================================================
    # TRON CONFIGURATION
    # ========================================================================
    TRON_NETWORK_URL: str = Field(default="https://api.trongrid.io")
    TRON_API_KEY: Optional[SecretStr] = Field(default=None)

    # Supported Assets (Multi-Chain) - ALL CHAINS INCLUDING WDK
    SUPPORTED_ASSETS: Dict[str, Dict[str, Any]] = {
        # ========== ALGORAND NATIVE ==========
        "ALGO": {
            "blockchain": "algorand",
            "asset_id": 0,  # Native ALGO
            "name": "Algorand",
            "unit_name": "ALGO",
            "decimals": 6,
            "is_stable": False,
            "oracle_symbol": "algorand"
        },
        "USDT_ALGO": {
            "blockchain": "algorand",
            "asset_id": 312769,
            "name": "Tether USD (Algorand)",
            "unit_name": "USDT",
            "decimals": 6,
            "is_stable": True,
            "oracle_symbol": "tether"
        },
        "USDCa": {
            "blockchain": "algorand",
            "asset_id": 31566704,
            "name": "USD Coin (Algorand)",
            "unit_name": "USDCa",
            "decimals": 6,
            "is_stable": True,
            "oracle_symbol": "tether"  # Use USDT oracle for stable
        },
        "goBTC": {
            "blockchain": "algorand",
            "asset_id": 386192725,  # goMint wrapped BTC
            "name": "Wrapped Bitcoin (Algorand)",
            "unit_name": "goBTC",
            "decimals": 8,
            "is_stable": False,
            "oracle_symbol": "bitcoin"
        },
        "goETH": {
            "blockchain": "algorand",
            "asset_id": 386195940,  # goMint wrapped ETH
            "name": "Wrapped Ethereum (Algorand)",
            "unit_name": "goETH",
            "decimals": 8,
            "is_stable": False,
            "oracle_symbol": "ethereum"
        },
        
        # ========== BITCOIN (WDK) ==========
        "BTC": {
            "blockchain": "bitcoin",
            "name": "Bitcoin",
            "unit_name": "BTC",
            "decimals": 8,
            "is_stable": False,
            "oracle_symbol": "bitcoin",
            "wdk_enabled": True
        },
        
        # ========== ETHEREUM (WDK) ==========
        "ETH": {
            "blockchain": "ethereum",
            "name": "Ethereum",
            "unit_name": "ETH",
            "decimals": 18,
            "is_stable": False,
            "oracle_symbol": "ethereum",
            "wdk_enabled": True
        },
        "USDT_ETH": {
            "blockchain": "ethereum",
            "contract_address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
            "name": "Tether USD (Ethereum)",
            "unit_name": "USDT",
            "decimals": 6,
            "is_stable": True,
            "oracle_symbol": "tether",
            "wdk_enabled": True
        },
        "USDC_ETH": {
            "blockchain": "ethereum",
            "contract_address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            "name": "USD Coin (Ethereum)",
            "unit_name": "USDC",
            "decimals": 6,
            "is_stable": True,
            "oracle_symbol": "tether",
            "wdk_enabled": True
        },
        
        # ========== POLYGON (WDK) ==========
        "MATIC": {
            "blockchain": "polygon",
            "name": "Polygon",
            "unit_name": "MATIC",
            "decimals": 18,
            "is_stable": False,
            "oracle_symbol": "matic",
            "wdk_enabled": True
        },
        "USDT_POLYGON": {
            "blockchain": "polygon",
            "contract_address": "0xc2132d05d31c914a87c6611c10748aeb04b58e8f",
            "name": "Tether USD (Polygon)",
            "unit_name": "USDT",
            "decimals": 6,
            "is_stable": True,
            "oracle_symbol": "tether",
            "wdk_enabled": True
        },
        "USDC_POLYGON": {
            "blockchain": "polygon",
            "contract_address": "0x2791bca1f2de4661ed88a30c99a7a9449aa84174",
            "name": "USD Coin (Polygon)",
            "unit_name": "USDC",
            "decimals": 6,
            "is_stable": True,
            "oracle_symbol": "tether",
            "wdk_enabled": True
        },
        
        # ========== TRON (WDK) ==========
        "TRX": {
            "blockchain": "tron",
            "name": "TRON",
            "unit_name": "TRX",
            "decimals": 6,
            "is_stable": False,
            "oracle_symbol": "tron",
            "wdk_enabled": True
        },
        "USDT_TRON": {
            "blockchain": "tron",
            "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            "name": "Tether USD (Tron)",
            "unit_name": "USDT",
            "decimals": 6,
            "is_stable": True,
            "oracle_symbol": "tether",
            "wdk_enabled": True
        },
        
        # ========== SOLANA (WDK) ========== ✅ NEW
        "SOL": {
            "blockchain": "solana",
            "name": "Solana",
            "unit_name": "SOL",
            "decimals": 9,
            "is_stable": False,
            "oracle_symbol": "solana",
            "wdk_enabled": True
        },
        "USDT_SOLANA": {
            "blockchain": "solana",
            "contract_address": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "name": "Tether USD (Solana)",
            "unit_name": "USDT",
            "decimals": 6,
            "is_stable": True,
            "oracle_symbol": "tether",
            "wdk_enabled": True
        },
        "USDC_SOLANA": {
            "blockchain": "solana",
            "contract_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "name": "USD Coin (Solana)",
            "unit_name": "USDC",
            "decimals": 6,
            "is_stable": True,
            "oracle_symbol": "usd-coin",
            "wdk_enabled": True
        }
    }  

    # Treasury
    TREASURY_ADDRESS: Optional[str] = None
    TREASURY_PRIVATE_KEY: Optional[SecretStr] = None

    # Payment Providers
    PAYSTACK_PUBLIC_KEY: Optional[SecretStr] = None
    PAYSTACK_SECRET_KEY: Optional[SecretStr] = None
    PAYSTACK_WEBHOOK_SECRET: Optional[SecretStr] = None
    CASHRAMP_API_KEY: Optional[SecretStr] = None
    CASHRAMP_PUBLIC_KEY: Optional[SecretStr] = None
    CASHRAMP_WEBHOOK_SECRET: Optional[SecretStr] = None
    FLUTTERWAVE_SECRET_KEY: Optional[SecretStr] = None
    FLUTTERWAVE_PUBLIC_KEY: Optional[str] = None

    # Harbor (OwlPay) - Multi-chain crypto gateway
    HARBOR_API_KEY: Optional[SecretStr] = Field(None, env="HARBOR_API_KEY")
    HARBOR_WEBHOOK_URL: Optional[str] = Field(
        "https://seamount-io-pr8a.onrender.comapi/v1/webhooks/owlpay",
        env="HARBOR_WEBHOOK_URL"
    )
    # ✅ Webhook secret is OPTIONAL (Harbor doesn't provide one)
    HARBOR_WEBHOOK_SECRET: Optional[SecretStr] = Field(None, env="HARBOR_WEBHOOK_SECRET")

    # Commodity & Forex API Keys (Optional - improves rate limits)
    ALPHA_VANTAGE_API_KEY: Optional[SecretStr] = None  # Free: 500 req/day
    TWELVE_DATA_API_KEY: Optional[SecretStr] = None     # Free: 800 req/day
    FMP_API_KEY: Optional[SecretStr] = None             # Free: 250 req/day
    # Metals & Commodities APIs (FREE tier, high reliability)
    METALS_DEV_API_KEY: Optional[SecretStr] = None       # Free: 100 req/month
    
    # ============================================================================
    # PRETIUM AFRICA CONFIGURATION (Tron USDT Exclusive)
    # ============================================================================
    PRETIUM_CONSUMER_KEY: str = Field(
        default="",
        description="Pretium API consumer key (x-api-key header)"
    )
    PRETIUM_SECRET_KEY: SecretStr = Field(
        default=SecretStr(""),
        description="Pretium API secret key (not used in requests, for future)"
    )
    PRETIUM_BASE_URL: str = Field(
        default="https://api.xwift.africa",
        description="Pretium API base URL"
    )
    PRETIUM_SETTLEMENT_WALLET: str = Field(
        default="0x8005ee53E57aB11E11eAA4EFe07Ee3835Dc02F98",
        description="Pretium Tron settlement wallet address"
    )
    PRETIUM_WEBHOOK_URL: str = Field(
        default="https://seamount-io-pr8a.onrender.comwebhooks/pretium",
        description="Pretium webhook callback URL"
    )
    PRETIUM_CALLBACK_URL: str = Field(
        default="https://seamount.io/payment-callback",
        description="User redirect after payment"
    )

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
    API_BASE_URL: str = Field(default="https://seamount-io-pr8a.onrender.com")
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

    def validate_wdk_configuration(self) -> bool:
        """Validate WDK configuration on startup"""
        if not self.WDK_API_KEY:
            logger.warning("WDK_API_KEY not configured - indexer features disabled")
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
    'BlockchainNetwork',
    'TransactionType',
    'PricingRegion'
]

# ✅ DEBUG: Verify .env is loaded
if __name__ == "__main__":
    test_settings = get_settings()
    print(f"🔍 WDK_API_URL from config: {test_settings.WDK_API_URL}")
    print(f"🔍 WDK_API_KEY present: {bool(test_settings.WDK_API_KEY)}")