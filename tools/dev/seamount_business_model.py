import logging
from typing import List, Optional, Dict, Tuple
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
    Handles pricing, fees, and revenue calculations for African SMBs
    """
    
    # Individual user baseline: 2.6% (2% conversion + 0.6% processing)
    INDIVIDUAL_BASE_RATE = Decimal("0.026")  # Current Seamount individual rate
    
    # One-time License Fees (in local currency) - Premium positioning
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
    
    # SMB Transaction Fees (Volume discounts from 2.6% individual rate)
    TRANSACTION_FEES = {
        LicenseTier.BASIC: Decimal("0.022"),       # 2.2% (15% discount from individual)
        LicenseTier.PRO: Decimal("0.019"),         # 1.9% (27% discount from individual)
        LicenseTier.ENTERPRISE: Decimal("0.016")   # 1.6% (38% discount from individual)
    }
    
    # Fee Caps (in USD equivalent) - Premium structure
    FEE_CAPS = {
        "min_fee_usd": Decimal("2.00"),   # Minimum fee (no hidden costs)
        "max_fee_basic": Decimal("25.00"), # Basic tier cap
        "max_fee_pro": Decimal("50.00"),   # Pro tier cap
        "max_fee_enterprise": Decimal("100.00")  # Enterprise cap
    }
    
    # Employee limits per tier
    EMPLOYEE_LIMITS = {
        LicenseTier.BASIC: 50,
        LicenseTier.PRO: 500,
        LicenseTier.ENTERPRISE: float('inf')  # Unlimited
    }

    @staticmethod
    def get_discount_percentage(tier: LicenseTier) -> float:
        """Calculate discount percentage vs individual rate (2.6%)"""
        individual_rate = BusinessModelConfig.INDIVIDUAL_BASE_RATE
        tier_rate = BusinessModelConfig.TRANSACTION_FEES[tier]
        discount = (individual_rate - tier_rate) / individual_rate
        return float(discount * 100)
    
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
        """Calculate one-time license fee based on tier and region"""
        try:
            region_pricing = BusinessModelConfig.LICENSE_FEES.get(region, 
                                                                BusinessModelConfig.LICENSE_FEES[PricingRegion.DEFAULT])
            return region_pricing[tier]
        except KeyError as e:
            logger.error(f"Invalid tier or region: {e}")
            raise ValueError(f"Invalid pricing configuration: tier={tier}, region={region}")

    @staticmethod
    def calculate_transaction_fee(amount_usd: Decimal, tier: LicenseTier) -> Tuple[Decimal, Dict]:
        """
        Calculate transaction fee with caps and minimums
        Returns: (fee_amount, calculation_details)
        """
        try:
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
                "tier": tier.value,
                "effective_rate": float(final_fee / amount_usd) if amount_usd > 0 else 0
            }
            
            return final_fee, calculation_details
            
        except Exception as e:
            logger.error(f"Fee calculation error: {e}")
            raise ValueError(f"Transaction fee calculation failed: {e}")

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
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=False
    )

    # --- Core & Security ---
    ENCRYPTION_KEY: SecretStr
    IPINFO_TOKEN: SecretStr
    
    # --- Supabase ---
    VITE_SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: SecretStr
    SUPABASE_JWKS_URI: str
    SUPABASE_JWT_ISSUER: str

    # --- KYC Provider (ComplyCube) ---
    COMPLYCUBE_API_KEY: Optional[SecretStr] = None
    COMPLYCUBE_WEBHOOK_SECRET: Optional[SecretStr] = None
    
    # --- Algorand Network ---
    ALGORAND_NODE_URL: str
    ALGORAND_INDEXER_URL: str
    ALGORAND_API_KEY: SecretStr
    
    # --- Email Service ---
    MAIL_SERVER: str
    MAIL_PORT: int = 587
    MAIL_USERNAME: str
    MAIL_PASSWORD: SecretStr
    MAIL_FROM: str
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    
    # --- CORS Configuration ---
    ALLOWED_ORIGINS_STR: str = ""

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

    @computed_field
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Parse ALLOWED_ORIGINS_STR into a list for FastAPI CORS"""
        if not self.ALLOWED_ORIGINS_STR:
            return [
                "http://localhost:3000", 
                "http://localhost:5173", 
                "https://seamount.io", 
                "https://www.seamount.io"
            ]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_STR.split(',')]
    
    @computed_field
    @property
    def business_model(self) -> BusinessModelConfig:
        """Access to business model configuration"""
        return BusinessModelConfig()

# --- Singleton Pattern for Settings ---
_settings_instance: Optional[Settings] = None

def get_settings() -> Settings:
    """Returns cached instance of application settings"""
    global _settings_instance
    if _settings_instance is None:
        try:
            _settings_instance = Settings()
            logger.info("Configuration loaded and validated successfully.")
            logger.info(f"Environment: {_settings_instance.ENVIRONMENT}")
            logger.info(f"Pricing Region: {_settings_instance.DEFAULT_PRICING_REGION.value}")
            logger.info(f"ComplyCube API: {'Configured' if _settings_instance.COMPLYCUBE_API_KEY else 'NOT CONFIGURED'}")
            
            # Log business model validation
            bm = _settings_instance.business_model
            basic_license = bm.calculate_license_fee(LicenseTier.BASIC, _settings_instance.DEFAULT_PRICING_REGION)
            logger.info(f"Basic License Fee: {basic_license} ({_settings_instance.DEFAULT_PRICING_REGION.value})")
            
        except Exception as e:
            logger.critical(f"FATAL: Configuration validation failed. Error: {e}", exc_info=True)
            raise
    return _settings_instance

# --- Business Model Usage Examples ---
def demo_revenue_projections():
    """Demo function showing revenue calculations"""
    
    # Example: Realistic Nigerian SMB distribution
    customer_distribution = {
        LicenseTier.BASIC: 70,      # 70 small businesses (10-50 employees)
        LicenseTier.PRO: 25,        # 25 medium businesses (50-500 employees)
        LicenseTier.ENTERPRISE: 5   # 5 large businesses (500+ employees)
    }
    
    # Realistic monthly transaction volumes based on SMB payroll + treasury
    avg_volumes = {
        LicenseTier.BASIC: Decimal("8000"),      # $8K monthly (small payroll + some treasury)
        LicenseTier.PRO: Decimal("35000"),       # $35K monthly (medium payroll + active treasury)
        LicenseTier.ENTERPRISE: Decimal("150000") # $150K monthly (large payroll + complex treasury)
    }
    
    # Calculate projections with savings analysis
    bm = BusinessModelConfig()
    projections = bm.project_monthly_revenue(
        customer_distribution, 
        avg_volumes, 
        PricingRegion.NIGERIA
    )
    
    # Show savings vs individual rates
    logger.info("=== SMB SAVINGS VS INDIVIDUAL RATES ===")
    for tier in LicenseTier:
        if customer_distribution.get(tier, 0) > 0:
            annual_volume = avg_volumes[tier] * 12
            savings = bm.calculate_annual_savings(tier, annual_volume)
            logger.info(f"{tier.value.title()}: {savings['discount_percentage']:.1f}% discount, "
                       f"${savings['annual_savings']:,.0f} annual savings per customer")
    
    logger.info(f"Total Revenue Projections: {projections}")
    return projections

if __name__ == "__main__":
    # Test the configuration
    settings = get_settings()
    demo_revenue_projections()