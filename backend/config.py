import logging
import os
from typing import List, Optional, Dict, Tuple, Set, Any
from decimal import Decimal
from pydantic import SecretStr, computed_field, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class LicenseTier(str, Enum):
    """Updated License tiers for Seamount platform based on seamount_business_case.md"""
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"

class PricingRegion(str, Enum):
    """Supported regions with localized pricing"""
    NIGERIA = "nigeria"
    KENYA = "kenya"
    GHANA = "ghana"
    SOUTH_AFRICA = "south_africa"
    DEFAULT = "default"

class BusinessModelConfig:
    """
    Competitively Optimized Fee Structure
    Cross-border: 2.9% (vs Traditional 3-7%, Digital 1-2%)
    Speed Premium: Sub-5-second settlement justifies positioning
    """
    
    # --- OPTIMIZED FEE STRUCTURE ---
    
    # Cross-Border P2P: 2.9% (COMPETITIVE SWEET SPOT)
    # vs Sendwave: ~2% (but 48hr settlement)
    # vs Remitly: 2.5-4% + $3.99
    # vs Western Union: 3-7%
    CROSS_BORDER_FEE_RATE = Decimal("0.029")  # 2.9% - Optimal positioning
    
    # Fiat On-Ramp: 2.5% (PREMIUM BUT JUSTIFIED)
    # vs Quidax: ~1-2%
    # vs Market: 1-3%
    ON_RAMP_FEE_RATE = Decimal("0.025")  # 2.5% - Premium for multi-asset
    
    # Local P2P: 0.8% (COMPETITIVE)
    P2P_FEE_RATE = Decimal("0.008")  # 0.8% - Speed premium over Quidax 0.1%
    
    # Asset Swaps: Tiered by complexity
    SWAP_FEE_STRUCTURE = {
        "stable_stable": Decimal("0.008"),    # 0.8%
        "stable_volatile": Decimal("0.012"),  # 1.2%
        "volatile_volatile": Decimal("0.018") # 1.8%
    }
    
    # --- NETWORK FEE OPTIMIZATION ---
    # Increased markup from 10% to 35% (users won't notice $0.01 vs $0.0135)
    NETWORK_FEE_MARKUP = Decimal("0.35")  # 35% markup (revenue optimization)
    
    BASE_NETWORK_FEES = {
        "algorand_transfer": Decimal("0.0135"),  # $0.0135 (35% markup)
        "asset_transfer": Decimal("0.0135"),
        "opt_in": Decimal("0.0135")
    }
    
    # --- MINIMUM FEES (MAINTAINED) ---
    MINIMUM_FEES = {
        "cross_border": Decimal("2.50"),     # $2.50 minimum
        "on_ramp": Decimal("1.50"),          # $1.50 minimum
        "swap": Decimal("0.75"),             # $0.75 minimum
        "p2p": Decimal("0.50")               # $0.50 minimum
    }
    
    # --- VOLUME-BASED DISCOUNTS (OPTIMIZED) ---
    # Removed starter tier 15% discount - too generous for market entry
    LICENSE_DISCOUNTS = {
        LicenseTier.STARTER: Decimal("0.05"),    # 5% discount (reduced)
        LicenseTier.GROWTH: Decimal("0.20"),     # 20% discount
        LicenseTier.ENTERPRISE: Decimal("0.30")  # 30% discount
    }
    
    # --- PROVIDER COST CALCULATIONS ---
    PROVIDER_COSTS = {
        "cashramp_p2p": Decimal("0.012"),        # 1.2%
        "paystack_onramp": Decimal("0.015"),     # 1.5%
        "kyc_per_user": Decimal("2.00"),         # $2 per KYC
        "operational_buffer": Decimal("0.003")    # 0.3%
    }
    
    # --- COMPETITIVE ANALYSIS METHODS ---
    
    @staticmethod
    def calculate_cross_border_economics(amount_usd: Decimal) -> Dict:
        """
        Calculate competitive positioning for cross-border transfers
        Shows user cost vs competitor alternatives
        """
        # Seamount costs
        seamount_fee = amount_usd * BusinessModelConfig.CROSS_BORDER_FEE_RATE
        network_fee = BusinessModelConfig.BASE_NETWORK_FEES["algorand_transfer"]
        total_seamount_cost = seamount_fee + network_fee
        
        # Provider costs
        cashramp_cost = amount_usd * BusinessModelConfig.PROVIDER_COSTS["cashramp_p2p"]
        operational_cost = amount_usd * BusinessModelConfig.PROVIDER_COSTS["operational_buffer"]
        kyc_cost = BusinessModelConfig.PROVIDER_COSTS["kyc_per_user"] / 10  # Amortized
        
        total_provider_cost = cashramp_cost + operational_cost + kyc_cost
        net_profit = seamount_fee - total_provider_cost
        profit_margin = (net_profit / seamount_fee * 100) if seamount_fee > 0 else 0
        
        # Competitive comparison
        competitors = {
            "western_union": amount_usd * Decimal("0.055"),    # 5.5% average
            "moneygram": amount_usd * Decimal("0.045"),        # 4.5% average
            "remitly_express": amount_usd * Decimal("0.035") + Decimal("3.99"),  # 3.5% + $3.99
            "sendwave": amount_usd * Decimal("0.02"),          # 2% (but 48hr settlement)
        }
        
        savings_vs_traditional = competitors["western_union"] - total_seamount_cost
        savings_percentage = (savings_vs_traditional / competitors["western_union"] * 100)
        
        return {
            "amount_usd": float(amount_usd),
            "seamount": {
                "fee": float(seamount_fee),
                "network_fee": float(network_fee),
                "total_cost": float(total_seamount_cost),
                "settlement_time": "< 5 seconds"
            },
            "economics": {
                "revenue": float(seamount_fee),
                "provider_costs": float(total_provider_cost),
                "net_profit": float(net_profit),
                "profit_margin_percent": float(profit_margin)
            },
            "competitive_analysis": {
                "western_union_cost": float(competitors["western_union"]),
                "remitly_cost": float(competitors["remitly_express"]),
                "sendwave_cost": float(competitors["sendwave"]),
                "savings_vs_traditional": float(savings_vs_traditional),
                "savings_percentage": f"{float(savings_percentage):.1f}%",
                "speed_advantage": "5000x faster than traditional, 17000x faster than Sendwave"
            },
            "value_proposition": {
                "cost_savings": f"{float(savings_percentage):.0f}% cheaper than Western Union",
                "speed": "Instant vs 24-48 hours",
                "ux": "No seed phrases, gas fees, or blockchain complexity"
            }
        }
    
    @staticmethod
    def calculate_monthly_revenue_projection(
        monthly_volume: Decimal,
        cross_border_percentage: Decimal = Decimal("0.70"),  # 70% cross-border
        onramp_percentage: Decimal = Decimal("0.30")         # 30% on-ramp
    ) -> Dict:
        """
        Project monthly revenue with optimized fee structure
        """
        cross_border_volume = monthly_volume * cross_border_percentage
        onramp_volume = monthly_volume * onramp_percentage
        
        # Revenue calculations
        cross_border_revenue = cross_border_volume * BusinessModelConfig.CROSS_BORDER_FEE_RATE
        onramp_revenue = onramp_volume * BusinessModelConfig.ON_RAMP_FEE_RATE
        total_revenue = cross_border_revenue + onramp_revenue
        
        # Cost calculations
        cashramp_costs = cross_border_volume * BusinessModelConfig.PROVIDER_COSTS["cashramp_p2p"]
        paystack_costs = onramp_volume * BusinessModelConfig.PROVIDER_COSTS["paystack_onramp"]
        operational_costs = monthly_volume * BusinessModelConfig.PROVIDER_COSTS["operational_buffer"]
        kyc_costs = Decimal("500")  # $500/month average
        
        total_costs = cashramp_costs + paystack_costs + operational_costs + kyc_costs
        net_profit = total_revenue - total_costs
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            "monthly_volume": float(monthly_volume),
            "revenue_breakdown": {
                "cross_border": float(cross_border_revenue),
                "onramp": float(onramp_revenue),
                "total": float(total_revenue)
            },
            "cost_breakdown": {
                "cashramp": float(cashramp_costs),
                "paystack": float(paystack_costs),
                "operational": float(operational_costs),
                "kyc": float(kyc_costs),
                "total": float(total_costs)
            },
            "profitability": {
                "net_profit": float(net_profit),
                "profit_margin_percent": float(profit_margin),
                "break_even_volume": float(total_costs / (BusinessModelConfig.CROSS_BORDER_FEE_RATE * 0.4))  # Approx
            },
            "scaling_metrics": {
                "revenue_per_user": float(total_revenue / (monthly_volume / 500)),  # Assume $500 avg transaction
                "cost_per_user": float(total_costs / (monthly_volume / 500)),
                "ltv_estimate": float((total_revenue - total_costs) * 12 / (monthly_volume / 500))  # Annual per user
            }
        }
    
    @staticmethod
    def get_fee_for_transaction(
        transaction_type: str,
        amount: Decimal,
        from_asset: Optional[str] = None,
        to_asset: Optional[str] = None,
        user_tier: LicenseTier = LicenseTier.STARTER
    ) -> Dict:
        """
        Calculate exact fee for any transaction type
        This is the core method that will be called by fee_calculator.py
        """
        base_fee = Decimal("0")
        fee_rate = Decimal("0")
        minimum_fee = Decimal("0")
        
        # Determine base fee rate
        if transaction_type == "cross_border":
            fee_rate = BusinessModelConfig.CROSS_BORDER_FEE_RATE
            minimum_fee = BusinessModelConfig.MINIMUM_FEES["cross_border"]
        elif transaction_type == "on_ramp":
            fee_rate = BusinessModelConfig.ON_RAMP_FEE_RATE
            minimum_fee = BusinessModelConfig.MINIMUM_FEES["on_ramp"]
        elif transaction_type == "p2p":
            fee_rate = BusinessModelConfig.P2P_FEE_RATE
            minimum_fee = BusinessModelConfig.MINIMUM_FEES["p2p"]
        elif transaction_type == "swap":
            # Determine swap type based on assets
            if from_asset and to_asset:
                from_stable = from_asset in ["USDT", "USDCa"]
                to_stable = to_asset in ["USDT", "USDCa"]
                
                if from_stable and to_stable:
                    fee_rate = BusinessModelConfig.SWAP_FEE_STRUCTURE["stable_stable"]
                elif from_stable != to_stable:
                    fee_rate = BusinessModelConfig.SWAP_FEE_STRUCTURE["stable_volatile"]
                else:
                    fee_rate = BusinessModelConfig.SWAP_FEE_STRUCTURE["volatile_volatile"]
            else:
                fee_rate = BusinessModelConfig.SWAP_FEE_STRUCTURE["stable_stable"]
            minimum_fee = BusinessModelConfig.MINIMUM_FEES["swap"]
        
        # Calculate base fee
        base_fee = amount * fee_rate
        
        # Apply minimum fee
        if base_fee < minimum_fee:
            base_fee = minimum_fee
        
        # Apply volume discount
        discount_rate = BusinessModelConfig.LICENSE_DISCOUNTS.get(user_tier, Decimal("0"))
        discount_amount = base_fee * discount_rate
        discounted_fee = base_fee - discount_amount
        
        # Add network fee
        network_fee = BusinessModelConfig.BASE_NETWORK_FEES.get("algorand_transfer", Decimal("0.01"))
        total_fee = discounted_fee + network_fee
        
        # Calculate effective rate
        effective_rate = (total_fee / amount * 100) if amount > 0 else 0
        
        return {
            "transaction_type": transaction_type,
            "amount": float(amount),
            "base_fee": float(base_fee),
            "discount_applied": float(discount_amount),
            "discounted_fee": float(discounted_fee),
            "network_fee": float(network_fee),
            "total_fee": float(total_fee),
            "total_amount": float(amount + total_fee),
            "effective_rate_percent": float(effective_rate),
            "user_tier": user_tier.value,
            "fee_breakdown": {
                "platform_fee": float(discounted_fee),
                "network_fee": float(network_fee),
                "discount_savings": float(discount_amount)
            }
        }

class Settings(BaseSettings):
    """
    Enhanced Seamount API settings with integrated business model
    Supports both B2B and B2C operations with premium pricing
    """
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), '.env'),
        env_file_encoding='utf-8',
        extra="allow",
        case_sensitive=False
    )

    # --- Core & Security ---
    DATABASE_URL: SecretStr = Field(default="postgresql://user:password@localhost:5432/seamount")
    ENCRYPTION_KEY: SecretStr = Field(default="default-encryption-key-change-in-production")
    IPINFO_TOKEN: Optional[SecretStr] = None
    
    # --- Supabase ---
    SUPABASE_URL: str = Field(default="https://your-supabase-url.supabase.co")
    SUPABASE_SERVICE_KEY: SecretStr = Field(default="your-supabase-service-key")
    SUPABASE_JWKS_URI: str = Field(default="https://your-supabase-url.supabase.co/auth/v1/jwks")
    SUPABASE_JWT_ISSUER: str = Field(default="https://your-supabase-url.supabase.co")

    # --- KYC Provider (ComplyCube) ---
    COMPLYCUBE_API_KEY: Optional[SecretStr] = None
    COMPLYCUBE_WEBHOOK_SECRET: Optional[SecretStr] = None
    
    # --- External APIs ---
    ALPHA_VANTAGE_KEY: Optional[SecretStr] = None
    FLUTTERWAVE_SECRET_KEY: Optional[SecretStr] = None
    FLUTTERWAVE_PUBLIC_KEY: Optional[str] = None
    COINGECKO_API_KEY: Optional[SecretStr] = None
    
    # Add after the existing KYC configuration section:

    # --- Regfyl KYC/AML Provider ---
    REGFYL_API_KEY: Optional[SecretStr] = None
    REGFYL_BASE_URL: str = Field(default="https://api.portal.regfyl.com")
    REGFYL_COMPANY_NAME: str = Field(default="Frontwater-Tech Development Ventures Nigeria Limited")
    REGFYL_RC_NUMBER: str = Field(default="1258168")
    REGFYL_ENVIRONMENT: str = Field(default="PRODUCTION")
    
    # --- Algorand Network ---
    ALGORAND_NODE_URL: str = Field(default="https://mainnet-api.algonode.cloud")
    ALGORAND_INDEXER_URL: str = Field(default="https://mainnet-idx.algonode.cloud")
    ALGORAND_API_KEY: Optional[SecretStr] = None
    ALGORAND_CREATOR_MNEMONIC: Optional[SecretStr] = None
    ALGORAND_NETWORK: str = Field(default="mainnet")

    # --- Phase 1: Multi-Asset Configuration ---
    SUPPORTED_ASSETS: Dict[str, Dict[str, Any]] = {
        "USDT": {
            "asset_id": 312769,
            "name": "Tether USD",
            "unit_name": "USDT",
            "decimals": 6,
            "is_stable": True,
            "fee_tier": "stable",
        },
        "USDCa": {
            "asset_id": 31566704,
            "name": "USD Coin (Algorand)",
            "unit_name": "USDCa",
            "decimals": 6,
            "is_stable": True,
            "fee_tier": "stable",
        },
        "goBTC": {
            "asset_id": 386192725,
            "name": "Wrapped Bitcoin (Algorand)",
            "unit_name": "goBTC",
            "decimals": 8,
            "is_stable": False,
            "fee_tier": "volatile",
            "oracle_symbol": "BTC",
        },
        "goETH": {
            "asset_id": 386195940,
            "name": "Wrapped Ethereum (Algorand)",
            "unit_name": "goETH",
            "decimals": 8,
            "is_stable": False,
            "fee_tier": "volatile",
            "oracle_symbol": "ETH",
        },
    }

    # --- Treasury (Sensitive) ---
    TREASURY_ADDRESS: Optional[str] = None
    TREASURY_PRIVATE_KEY: Optional[SecretStr] = None

    # --- Redis (Upstash) ---
    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[SecretStr] = None
    
    # --- Email Service ---
    MAIL_SERVER: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[SecretStr] = None
    MAIL_FROM: Optional[str] = None
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    
    # --- CORS Configuration ---
    ALLOWED_ORIGINS_STR: str = ""
    
    # --- Whitelabel API Service ---
    WHITELISTED_API_KEYS_STR: str = ""

    # --- Operational ---
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # --- Business Model Configuration ---
    DEFAULT_PRICING_REGION: PricingRegion = PricingRegion.NIGERIA
    ENABLE_DYNAMIC_PRICING: bool = True
    
    # --- Revenue Tracking ---
    TRACK_REVENUE_METRICS: bool = True
    REVENUE_REPORTING_CURRENCY: str = "USD"
    
    # --- Payment Providers ---
    PAYSTACK_PUBLIC_KEY: Optional[SecretStr] = None
    PAYSTACK_SECRET_KEY: Optional[SecretStr] = None
    PAYSTACK_WEBHOOK_SECRET: Optional[SecretStr] = None
    
    # --- API URLs ---
    API_BASE_URL: str = Field(default="http://localhost:8000")
    FRONTEND_URL: str = Field(default="http://localhost:3000")

    @computed_field
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Parse ALLOWED_ORIGINS_STR into a list for FastAPI CORS"""
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
        """Parse WHITELISTED_API_KEYS_STR into a set"""
        if not self.WHITELISTED_API_KEYS_STR:
            return set()
        return {key.strip() for key in self.WHITELISTED_API_KEYS_STR.split(',')}
    
    @computed_field
    @property
    def business_model(self) -> BusinessModelConfig:
        """Access to business model configuration"""
        return BusinessModelConfig()
        
    def validate_supabase_credentials(self):
        """Validate Supabase credentials format"""
        if not self.SUPABASE_URL or self.SUPABASE_URL == "https://your-supabase-url.supabase.co":
            logger.warning("Supabase URL not configured - using default")
            return False
        
        if not self.SUPABASE_SERVICE_KEY or self.SUPABASE_SERVICE_KEY.get_secret_value() == "your-supabase-service-key":
            logger.warning("Supabase Service Key not configured - using default")
            return False
        
        # Check if key looks like a JWT (should start with eyJ)
        key_value = self.SUPABASE_SERVICE_KEY.get_secret_value()
        if not key_value.startswith("eyJ"):
            logger.warning("Supabase Service Key appears malformed - should be a JWT starting with 'eyJ'")
            return False
        
        logger.info("Supabase credentials validated successfully")
        return True

# Create a single settings instance
try:
    settings = Settings()
    logger.info("Settings loaded successfully")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Supabase URL configured: {'Yes' if settings.SUPABASE_URL != 'https://your-supabase-url.supabase.co' else 'No'}")
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    logger.error(f"Working directory: {os.getcwd()}")
    logger.error(f"Config file location: {__file__}")
    # Create a minimal settings object with defaults
    settings = Settings(_env_file=None)

# Export the function as well for backward compatibility
def get_settings() -> Settings:
    return settings

__all__ = ['get_settings', 'settings', 'BusinessModelConfig', 'LicenseTier', 'PricingRegion']