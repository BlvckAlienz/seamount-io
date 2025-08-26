import logging
from typing import Dict, Any, List, Set, Optional  # Added Optional import
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

# Configure logger first to avoid reference errors
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Static business logic configuration
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

GEOGRAPHIC_TIERS = {
    'tier_1': ['US', 'CA', 'GB', 'DE', 'FR', 'AU', 'JP', 'SG', 'NL', 'CH', 'SE', 'NO', 'DK', 'AT', 'BE', 'FI', 'IE', 'LU', 'NZ', 'ZA'], 
    'tier_2_standard': ['MX', 'BR', 'IN', 'CN', 'KR', 'TH', 'MY', 'PH', 'ID', 'VN', 'TW', 'HK', 'AE', 'SA', 'CL', 'CO', 'PE', 'AR', 'UY'], 
    'tier_2_african': ['NG', 'KE', 'EG', 'UG', 'ZW', 'TZ'], 
    'tier_3': ['BD', 'PK', 'LK', 'MM', 'NP', 'ET', 'RW', 'BF', 'ML', 'SN', 'CI', 'GH', 'VE', 'MA', 'DO']
}

VOLUME_DISCOUNTS = {
    'startup': {'threshold': 0, 'discount': 0.00}, 
    'growth': {'threshold': 100000, 'discount': 0.10}, 
    'enterprise': {'threshold': 1000000, 'discount': 0.15}, 
    'institutional': {'threshold': 10000000, 'discount': 0.20}
}

class Settings(BaseSettings):
    """Defines and validates all environment variables."""
    
    # --- Core & Security ---
    DATABASE_URL: SecretStr
    COMPLYCUBE_API_KEY: SecretStr
    COMPLYCUBE_WEBHOOK_SECRET: SecretStr  # Added missing webhook secret
    ENCRYPTION_KEY: SecretStr
    IPINFO_TOKEN: SecretStr
    
    # --- Supabase ---
    VITE_SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: SecretStr
    SUPABASE_JWKS_URI: str
    
    # --- External APIs ---
    ALPHA_VANTAGE_KEY: SecretStr
    FLUTTERWAVE_SECRET_KEY: SecretStr
    FLUTTERWAVE_PUBLIC_KEY: str
    COINGECKO_API_KEY: SecretStr

    # --- Algorand Network ---
    ALGORAND_NODE_URL: str
    ALGORAND_INDEXER_URL: str
    ALGORAND_API_KEY: SecretStr
    ALGORAND_CREATOR_MNEMONIC: SecretStr
    ALGORAND_NETWORK: str
    USDS_ASSET_ID: int

    # --- Treasury (Sensitive) ---
    TREASURY_ADDRESS: str
    TREASURY_PRIVATE_KEY: SecretStr

    # --- Redis (Upstash) ---
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: SecretStr

    # --- Email Service ---
    MAIL_SERVER: str
    MAIL_PORT: int = 587
    MAIL_USERNAME: str
    MAIL_PASSWORD: SecretStr
    MAIL_FROM: str
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    # --- Operational ---
    ENVIRONMENT: str = "production"
    
    # --- CORS Configuration ---
    ALLOWED_ORIGINS_STR: str = Field("", alias='ALLOWED_ORIGINS')
    
    # --- Whitelabel API Service ---
    WHITELISTED_API_KEYS_STR: str = Field("", alias='WHITELISTED_API_KEYS')

    # --- Static Business Logic (Not from .env) ---
    FEE_STRUCTURE: Dict[str, Any] = FEE_STRUCTURE
    GEOGRAPHIC_TIERS: Dict[str, List[str]] = GEOGRAPHIC_TIERS
    VOLUME_DISCOUNTS: Dict[str, Any] = VOLUME_DISCOUNTS

    # Add validation for critical settings
    VITE_SUPABASE_URL: str = Field(..., env="VITE_SUPABASE_URL")
    SUPABASE_SERVICE_KEY: str = Field(..., env="SUPABASE_SERVICE_KEY")
    
    # Make ComplyCube optional with proper validation
    COMPLYCUBE_API_KEY: Optional[str] = Field(None, env="COMPLYCUBE_API_KEY")
    
    # Add debug mode
    DEBUG: bool = Field(False, env="DEBUG")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

def get_settings():
    settings = Settings()
    
    # Validate critical settings
    if not settings.VITE_SUPABASE_URL:
        raise ValueError("VITE_SUPABASE_URL is required")
    
    if not settings.SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_KEY is required")
    
    # Log configuration status
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Supabase URL: {'Configured' if settings.VITE_SUPABASE_URL else 'Missing'}")
    logger.info(f"ComplyCube API Key: {'Configured' if settings.COMPLYCUBE_API_KEY else 'Missing'}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    
    return settings
    
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        if not self.ALLOWED_ORIGINS_STR:
            # Updated with your production domains
            return [
                "http://localhost:3000", 
                "http://localhost:5173", 
                "https://seamount.io", 
                "https://www.seamount.io",
                "https://seamount.vercel.app"
            ]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_STR.split(',')]
    
    @property
    def WHITELISTED_API_KEYS(self) -> Set[str]:
        if not self.WHITELISTED_API_KEYS_STR:
            return set()
        return {key.strip() for key in self.WHITELISTED_API_KEYS_STR.split(',')}

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

_settings_instance = None

def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        try:
            _settings_instance = Settings()
            logger.info("Configuration loaded and validated successfully.")
        except Exception as e:
            logger.critical(f"FATAL: FAILED TO LOAD OR VALIDATE CONFIGURATION. Error: {e}")
            raise
    return _settings_instance