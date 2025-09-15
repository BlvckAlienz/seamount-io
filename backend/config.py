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
    """License tiers for Seamount platform"""
    BASIC = "basic"
    PRO = "pro" 
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
    Handles pricing, fees, and revenue calculations for both B2B and B2C models
    """
    
    # B2C Individual user baseline: 2.6% (2% conversion + 0.6% processing)
    INDIVIDUAL_BASE_RATE = Decimal("0.026")
    
    # B2B One-time License Fees (in local currency)
    LICENSE_FEES = {
        PricingRegion.NIGERIA: {
            LicenseTier.BASIC: Decimal("800000"),      # ₦800K (~$530)
            LicenseTier.PRO: Decimal("1600000"),       # ₦1.6M (~$1,060)
            LicenseTier.ENTERPRISE: Decimal("3200000") # ₦3.2M (~$2,120)
        },
        PricingRegion.KENYA: {
            LicenseTier.BASIC: Decimal("80000"),       # KSh80K (~$530)
            LicenseTier.PRO: Decimal("160000"),        # KSh160K (~$1,060)
            LicenseTier.ENTERPRISE: Decimal("320000")  # KSh320K (~$2,120)
        },
        PricingRegion.DEFAULT: {
            LicenseTier.BASIC: Decimal("530"),         # $530 USD
            LicenseTier.PRO: Decimal("1060"),          # $1,060 USD
            LicenseTier.ENTERPRISE: Decimal("2120")    # $2,120 USD
        }
    }
    
    # B2B SMB Transaction Fees (Volume discounts from 2.6% individual rate)
    TRANSACTION_FEES = {
        LicenseTier.BASIC: Decimal("0.022"),       # 2.2% (15% discount from individual)
        LicenseTier.PRO: Decimal("0.019"),         # 1.9% (27% discount from individual)
        LicenseTier.ENTERPRISE: Decimal("0.016")   # 1.6% (38% discount from individual)
    }
    
    # B2B Fee Caps (in USD equivalent)
    FEE_CAPS = {
        "min_fee_usd": Decimal("2.00"),   # Minimum fee (no hidden costs)
        "max_fee_basic": Decimal("25.00"), # Basic tier cap
        "max_fee_pro": Decimal("50.00"),   # Pro tier cap
        "max_fee_enterprise": Decimal("100.00")  # Enterprise cap
    }
    
    # B2B Employee limits per tier
    EMPLOYEE_LIMITS = {
        LicenseTier.BASIC: 50,
        LicenseTier.PRO: 500,
        LicenseTier.ENTERPRISE: float('inf')  # Unlimited
    }

    # B2C Fee Structure
    FEE_STRUCTURE = {
        'conversion': {'base_fee': 0.020}, 
        'processing': {'tier_1': 0.010, 'tier_2_standard': 0.010, 'tier_2_african': 0.006, 'tier_3': 0.018}, 
        'network': {'base_fee': 0.00}, 
        'trading': {'tier_1': 0.002, 'tier_2': 0.0025, 'tier_3': 0.003}, 
        'swap': {'tier_1': 0.003, 'tier_2': 0.0035, 'tier_3': 0.004}, 
        'bridge': {'tier_1': 0.0025, 'tier_2': 0.0035, 'tier_3': 0.0045, 'min_fee': 1.50, 'max_fee': 35.00}, 
        'stability': {'tier_1': 6.5, 'tier_2': 7.5, 'tier_3': 9.0}, 
        'staking': {'reward_rate': 4.5}
    }

    # B2C Geographic Tiers
    GEOGRAPHIC_TIERS = {
        'tier_1': ['US', 'CA', 'GB', 'DE', 'FR', 'AU', 'JP', 'SG', 'NL', 'CH', 'SE', 'NO', 'DK', 'AT', 'BE', 'FI', 'IE', 'LU', 'NZ', 'ZA'], 
        'tier_2_standard': ['MX', 'BR', 'IN', 'CN', 'KR', 'TH', 'MY', 'PH', 'ID', 'VN', 'TW', 'HK', 'AE', 'SA', 'CL', 'CO', 'PE', 'AR', 'UY'], 
        'tier_2_african': ['NG', 'KE', 'EG', 'UG', 'ZW', 'TZ'], 
        'tier_3': ['BD', 'PK', 'LK', 'MM', 'NP', 'ET', 'RW', 'BF', 'ML', 'SN', 'CI', 'GH', 'VE', 'MA', 'DO']
    }

    # B2C Volume Discounts
    VOLUME_DISCOUNTS = {
        'startup': {'threshold': 0, 'discount': 0.00}, 
        'growth': {'threshold': 100000, 'discount': 0.10}, 
        'enterprise': {'threshold': 1000000, 'discount': 0.15}, 
        'institutional': {'threshold': 10000000, 'discount': 0.20}
    }

    @staticmethod
    def get_discount_percentage(tier: LicenseTier) -> float:
        """Calculate discount percentage vs individual rate (2.6%)"""
        individual_rate = BusinessModelConfig.INDIVIDUAL_BASE_RATE
        tier_rate = BusinessModelConfig.TRANSACTION_FEES[tier]
        discount = (individual_rate - tier_rate) / individual_rate
        return float(discount * 100)
    
    @staticmethod
    def calculate_license_fee(tier: LicenseTier, region: PricingRegion) -> Decimal:
        """Calculate one-time license fee based on tier and region"""
        try:
            region_pricing = BusinessModelConfig.LICENSE_FEES.get(region, 
                                                                BusinessModelConfig.LICENSE_FEES[PricingRegion.DEFAULT])
            return region_pricing[tier]
        except KeyError as e:
            logger.error(f"Invalid tier or region: {e}")
            raise ValueError(f"Invalid pricing configuration: tier={tier}, region={region}")

    @staticmethod
    def calculate_annual_savings(tier: LicenseTier, annual_volume_usd: Decimal) -> Dict:
        """Calculate annual savings vs individual rate"""
        individual_rate = BusinessModelConfig.INDIVIDUAL_BASE_RATE
        tier_rate = BusinessModelConfig.TRANSACTION_FEES[tier]
        
        individual_cost = annual_volume_usd * individual_rate
        smb_cost = annual_volume_usd * tier_rate
        annual_savings = individual_cost - smb_cost
        
        return {
            "annual_volume": float(annual_volume_usd),
            "individual_cost": float(individual_cost),
            "smb_tier_cost": float(smb_cost),
            "annual_savings": float(annual_savings),
            "discount_percentage": BusinessModelConfig.get_discount_percentage(tier),
            "tier": tier.value
        }

    @staticmethod
    def calculate_transaction_fee(amount_usd: Decimal, tier: Optional[LicenseTier] = None) -> Tuple[Decimal, Dict]:
        """
        Calculate transaction fee with caps and minimums
        Supports both B2C (individual) and B2B (licensed) users
        """
        try:
            # Use individual rate if no tier provided (B2C)
            if tier is None:
                base_rate = BusinessModelConfig.INDIVIDUAL_BASE_RATE
                calculated_fee = amount_usd * base_rate
                min_fee = Decimal("0.50")  # Lower minimum for B2C
                max_fee = Decimal("50.00")  # Standard maximum for B2C
            else:
                # Use tiered rate for B2B
                base_rate = BusinessModelConfig.TRANSACTION_FEES[tier]
                calculated_fee = amount_usd * base_rate
                
                # Apply minimum fee
                min_fee = BusinessModelConfig.FEE_CAPS["min_fee_usd"]
                
                # Apply maximum fee based on tier
                if tier == LicenseTier.BASIC:
                    max_fee = BusinessModelConfig.FEE_CAPS["max_fee_basic"]
                elif tier == LicenseTier.PRO:
                    max_fee = BusinessModelConfig.FEE_CAPS["max_fee_pro"]
                else:  # ENTERPRISE
                    max_fee = BusinessModelConfig.FEE_CAPS["max_fee_enterprise"]
            
            # Final fee calculation with caps
            final_fee = max(min_fee, min(calculated_fee, max_fee))
            
            calculation_details = {
                "amount_usd": float(amount_usd),
                "base_rate": float(base_rate),
                "calculated_fee": float(calculated_fee),
                "min_fee": float(min_fee),
                "max_fee": float(max_fee),
                "final_fee": float(final_fee),
                "tier": tier.value if tier else "individual",
                "effective_rate": float(final_fee / amount_usd) if amount_usd > 0 else 0
            }
            
            return final_fee, calculation_details
            
        except Exception as e:
            logger.error(f"Fee calculation error: {e}")
            raise ValueError(f"Transaction fee calculation failed: {e}")

    @staticmethod
    def calculate_b2c_fee(amount: Decimal, country_code: str, service_type: str) -> Dict[str, Any]:
        """Calculate B2C fee based on country and service type"""
        # Determine geographic tier
        geo_tier = None
        for tier, countries in BusinessModelConfig.GEOGRAPHIC_TIERS.items():
            if country_code in countries:
                geo_tier = tier
                break
        
        if not geo_tier:
            geo_tier = 'tier_3'  # Default to highest fee tier
        
        # Get fee rate based on service and tier
        if service_type in BusinessModelConfig.FEE_STRUCTURE:
            service_fees = BusinessModelConfig.FEE_STRUCTURE[service_type]
            if geo_tier in service_fees:
                fee_rate = Decimal(str(service_fees[geo_tier]))
            else:
                fee_rate = Decimal(str(service_fees.get('base_fee', 0.02)))
        else:
            fee_rate = Decimal("0.02")  # Default fallback
        
        calculated_fee = amount * fee_rate
        
        # Apply min/max fees if specified
        min_fee = Decimal(str(BusinessModelConfig.FEE_STRUCTURE.get(service_type, {}).get('min_fee', 0)))
        max_fee = Decimal(str(BusinessModelConfig.FEE_STRUCTURE.get(service_type, {}).get('max_fee', float('inf'))))
        
        final_fee = max(min_fee, min(calculated_fee, max_fee))
        
        return {
            "amount": float(amount),
            "country_code": country_code,
            "service_type": service_type,
            "geo_tier": geo_tier,
            "fee_rate": float(fee_rate),
            "calculated_fee": float(calculated_fee),
            "min_fee": float(min_fee),
            "max_fee": float(max_fee if max_fee != float('inf') else 0),
            "final_fee": float(final_fee),
            "effective_rate": float(final_fee / amount) if amount > 0 else 0
        }

    @staticmethod
    def project_monthly_revenue(customers_by_tier: Dict[LicenseTier, int], 
                              avg_transaction_volume_usd: Dict[LicenseTier, Decimal],
                              region: PricingRegion = PricingRegion.NIGERIA) -> Dict:
        """
        Project monthly recurring revenue from transaction fees
        (License fees are one-time, tracked separately)
        """
        monthly_revenue = Decimal("0")
        revenue_breakdown = {}
        
        for tier, customer_count in customers_by_tier.items():
            if customer_count == 0:
                continue
                
            avg_volume = avg_transaction_volume_usd.get(tier, Decimal("0"))
            fee_per_transaction, _ = BusinessModelConfig.calculate_transaction_fee(avg_volume, tier)
            
            # Assume average transactions per customer per month
            transactions_per_month = {
                LicenseTier.BASIC: 20,      # Small businesses
                LicenseTier.PRO: 100,       # Medium businesses  
                LicenseTier.ENTERPRISE: 500  # Large businesses
            }
            
            tier_monthly_revenue = (
                customer_count * 
                transactions_per_month[tier] * 
                fee_per_transaction
            )
            
            monthly_revenue += tier_monthly_revenue
            
            revenue_breakdown[tier.value] = {
                "customers": customer_count,
                "avg_transaction_volume": float(avg_volume),
                "fee_per_transaction": float(fee_per_transaction),
                "transactions_per_month": transactions_per_month[tier],
                "tier_monthly_revenue": float(tier_monthly_revenue)
            }
        
        # Calculate license fee revenue (one-time)
        total_license_revenue = Decimal("0")
        for tier, customer_count in customers_by_tier.items():
            license_fee = BusinessModelConfig.calculate_license_fee(tier, region)
            total_license_revenue += license_fee * customer_count
        
        return {
            "monthly_transaction_revenue": float(monthly_revenue),
            "annual_transaction_revenue": float(monthly_revenue * 12),
            "one_time_license_revenue": float(total_license_revenue),
            "total_first_year_revenue": float(monthly_revenue * 12 + total_license_revenue),
            "revenue_breakdown": revenue_breakdown,
            "region": region.value
        }

class Settings(BaseSettings):
    """
    Enhanced Seamount API settings with integrated business model
    Supports both B2B and B2C operations
    """
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), '..', '.env'),
        env_file_encoding='utf-8',
        extra="allow",
        case_sensitive=False
    )

    # --- Core & Security ---
    DATABASE_URL: SecretStr = Field(default="postgresql://user:password@localhost:5432/seamount")
    ENCRYPTION_KEY: SecretStr = Field(default="default-encryption-key-change-in-production")
    IPINFO_TOKEN: Optional[SecretStr] = None
    
    # --- Supabase ---
    VITE_SUPABASE_URL: str = Field(default="https://your-supabase-url.supabase.co")
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
    USDS_ASSET_ID: int = Field(default=0)

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
    LICENSE_FEE_GRACE_PERIOD_DAYS: int = 30
    
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

# Create a single settings instance
try:
    settings = Settings()
    logger.info("Settings loaded successfully")
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    # Create a minimal settings object with defaults
    settings = Settings(_env_file=None)

# Export the function as well for backward compatibility
def get_settings() -> Settings:
    return settings

__all__ = ['get_settings', 'settings', 'BusinessModelConfig', 'LicenseTier', 'PricingRegion']