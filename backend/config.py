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
    Seamount.io Business Model Configuration
    Updated for Phase 1: Multi-Asset Dollar & Digital Asset Corridor
    Based on seamount_business_case.md premium positioning
    """
    
    # --- PHASE 1: MULTI-ASSET REVENUE MODEL (PREMIUM) ---
    # Fiat-to-Crypto On-Ramp: 2.5% - 3.0% FX spread
    ON_RAMP_FEE_RATE = Decimal("0.030")  # 3.0% (PREMIUM END)
    
    # P2P & Asset Swaps: 0.8% - 1.0% transaction fee
    SWAP_FEE_STRUCTURE = {
        "stable_stable": Decimal("0.010"),  # 1.0% for stable/stable swaps (PREMIUM)
        "stable_volatile": Decimal("0.015"),  # 1.5% for stable/volatile swaps (PREMIUM)
        "volatile_volatile": Decimal("0.020")  # 2.0% for volatile/volatile swaps (PREMIUM)
    }
    
    # P2P Transfer Fees
    P2P_FEE_RATE = Decimal("0.010")  # 1.0% (PREMIUM)
    
    # Minimum and Maximum Fees
    MINIMUM_FEES = {
        "on_ramp": Decimal("2.00"),      # $2 minimum
        "swap": Decimal("1.00"),         # $1 minimum
        "p2p": Decimal("0.50")           # $0.50 minimum
    }
    
    # --- B2B API ACCESS FEES (MONTHLY SUBSCRIPTION) ---
    # From seamount_business_case.md: $299-1K/mo
    API_SUBSCRIPTION_FEES = {
        LicenseTier.STARTER: Decimal("299"),      # $299/month
        LicenseTier.GROWTH: Decimal("650"),       # $650/month (blended avg)
        LicenseTier.ENTERPRISE: Decimal("1000")   # $1000/month
    }
    
    # B2B Employee limits per tier
    EMPLOYEE_LIMITS = {
        LicenseTier.STARTER: 50,
        LicenseTier.GROWTH: 500,
        LicenseTier.ENTERPRISE: float('inf')  # Unlimited
    }

    # B2B Transaction Fee Discounts (vs retail rates)
    LICENSE_DISCOUNTS = {
        LicenseTier.STARTER: Decimal("0.20"),    # 20% discount
        LicenseTier.GROWTH: Decimal("0.35"),     # 35% discount
        LicenseTier.ENTERPRISE: Decimal("0.50")  # 50% discount
    }

    # --- PHASE 2: GOLD CERTIFICATES (SGC) ---
    GOLD_PREMIUM_RATE = Decimal("0.050")  # 5% premium (as per business case)

    # --- PHASE 3: USDS STABLECOIN (FUTURE) ---
    USDS_SEIGNIORAGE_RATES = {
        "retail": Decimal("0.015"),  # 1.5% for retail
        "corporate": Decimal("0.020")  # 2.0% for corporate (PREMIUM)
    }
    
    TREASURY_YIELD_RATE = Decimal("0.30")     # 30% target yield
    TREASURY_TAX_RATE = Decimal("0.30")       # 30% tax rate
    TREASURY_NET_YIELD_RATE = Decimal("0.21")  # 21% net yield after tax

    @staticmethod
    def calculate_on_ramp_fee(amount: Decimal, is_licensed: bool = False, tier: Optional[LicenseTier] = None) -> Tuple[Decimal, Dict]:
        """
        Calculate fiat on-ramp fee with premium pricing
        """
        base_fee = amount * BusinessModelConfig.ON_RAMP_FEE_RATE
        
        # Apply license discount if applicable
        if is_licensed and tier:
            discount = BusinessModelConfig.LICENSE_DISCOUNTS[tier]
            base_fee = base_fee * (Decimal("1.0") - discount)
        
        # Apply minimum fee
        final_fee = max(BusinessModelConfig.MINIMUM_FEES["on_ramp"], base_fee)
        
        calculation_details = {
            "amount": float(amount),
            "base_rate": float(BusinessModelConfig.ON_RAMP_FEE_RATE),
            "base_fee": float(base_fee),
            "min_fee": float(BusinessModelConfig.MINIMUM_FEES["on_ramp"]),
            "final_fee": float(final_fee),
            "effective_rate": float(final_fee / amount),
            "is_licensed": is_licensed,
            "tier": tier.value if tier else None,
            "discount_applied": float(BusinessModelConfig.LICENSE_DISCOUNTS[tier]) if tier else 0.0
        }
        
        return final_fee, calculation_details

    @staticmethod
    def calculate_swap_fee(amount: Decimal, from_asset_type: str, to_asset_type: str, 
                          is_licensed: bool = False, tier: Optional[LicenseTier] = None) -> Tuple[Decimal, Dict]:
        """
        Calculate asset swap fee with premium tiered pricing
        """
        # Determine fee tier based on asset types
        if from_asset_type == "stable" and to_asset_type == "stable":
            base_rate = BusinessModelConfig.SWAP_FEE_STRUCTURE["stable_stable"]
        elif (from_asset_type == "stable" and to_asset_type == "volatile") or \
             (from_asset_type == "volatile" and to_asset_type == "stable"):
            base_rate = BusinessModelConfig.SWAP_FEE_STRUCTURE["stable_volatile"]
        else:
            base_rate = BusinessModelConfig.SWAP_FEE_STRUCTURE["volatile_volatile"]
        
        base_fee = amount * base_rate
        
        # Apply license discount if applicable
        if is_licensed and tier:
            discount = BusinessModelConfig.LICENSE_DISCOUNTS[tier]
            base_fee = base_fee * (Decimal("1.0") - discount)
        
        # Apply minimum fee
        final_fee = max(BusinessModelConfig.MINIMUM_FEES["swap"], base_fee)
        
        calculation_details = {
            "amount": float(amount),
            "from_asset_type": from_asset_type,
            "to_asset_type": to_asset_type,
            "base_rate": float(base_rate),
            "base_fee": float(base_fee),
            "min_fee": float(BusinessModelConfig.MINIMUM_FEES["swap"]),
            "final_fee": float(final_fee),
            "effective_rate": float(final_fee / amount),
            "is_licensed": is_licensed,
            "tier": tier.value if tier else None,
            "discount_applied": float(BusinessModelConfig.LICENSE_DISCOUNTS[tier]) if tier else 0.0
        }
        
        return final_fee, calculation_details

    @staticmethod
    def calculate_api_subscription_fee(tier: LicenseTier) -> Decimal:
        """Calculate monthly API subscription fee based on tier"""
        return BusinessModelConfig.API_SUBSCRIPTION_FEES[tier]

    @staticmethod
    def calculate_annual_revenue_projection(customers_by_tier: Dict[LicenseTier, int],
                                          avg_monthly_volume: Dict[LicenseTier, Decimal]) -> Dict:
        """
        Project annual revenue including both subscription and transaction fees
        """
        annual_revenue = Decimal("0")
        revenue_breakdown = {}
        
        for tier, customer_count in customers_by_tier.items():
            if customer_count == 0:
                continue
                
            # Subscription revenue
            subscription_fee = BusinessModelConfig.calculate_api_subscription_fee(tier)
            annual_subscription = subscription_fee * Decimal("12") * customer_count
            
            # Transaction fee revenue
            avg_volume = avg_monthly_volume.get(tier, Decimal("0"))
            avg_fee_rate = BusinessModelConfig.ON_RAMP_FEE_RATE * (Decimal("1.0") - BusinessModelConfig.LICENSE_DISCOUNTS[tier])
            monthly_fees = avg_volume * avg_fee_rate * customer_count
            annual_fees = monthly_fees * Decimal("12")
            
            tier_annual_revenue = annual_subscription + annual_fees
            
            annual_revenue += tier_annual_revenue
            
            revenue_breakdown[tier.value] = {
                "customers": customer_count,
                "monthly_subscription": float(subscription_fee),
                "annual_subscription": float(annual_subscription),
                "avg_monthly_volume": float(avg_volume),
                "effective_fee_rate": float(avg_fee_rate),
                "annual_transaction_fees": float(annual_fees),
                "total_annual_revenue": float(tier_annual_revenue)
            }
        
        return {
            "total_annual_revenue": float(annual_revenue),
            "monthly_revenue_run_rate": float(annual_revenue / Decimal("12")),
            "revenue_breakdown": revenue_breakdown
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