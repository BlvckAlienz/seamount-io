import logging
from typing import Dict, Any, List
from pydantic_settings import BaseSettings

# --- Static Business Logic Configuration ---
# This data is part of the application's core logic, not environment-specific.
FEE_STRUCTURE = {
    'conversion': {'base_fee': 0.020}, 'processing': {'tier_1': 0.010, 'tier_2_standard': 0.010, 'tier_2_african': 0.006, 'tier_3': 0.018}, 'network': {'base_fee': 0.00}, 'trading': {'tier_1': 0.002, 'tier_2': 0.0025, 'tier_3': 0.003}, 'swap': {'tier_1': 0.003, 'tier_2': 0.0035, 'tier_3': 0.004}, 'bridge': {'tier_1': 0.0025, 'tier_2': 0.0035, 'tier_3': 0.0045, 'min_fee': 1.50, 'max_fee': 35.00}, 'stability': {'tier_1': 6.5, 'tier_2': 7.5, 'tier_3': 9.0}, 'staking': {'reward_rate': 4.5}
}
GEOGRAPHIC_TIERS = {
    'tier_1': ['US', 'CA', 'GB', 'DE', 'FR', 'AU', 'JP', 'SG', 'NL', 'CH', 'SE', 'NO', 'DK', 'AT', 'BE', 'FI', 'IE', 'LU', 'NZ', 'ZA'], 'tier_2_standard': ['MX', 'BR', 'IN', 'CN', 'KR', 'TH', 'MY', 'PH', 'ID', 'VN', 'TW', 'HK', 'AE', 'SA', 'CL', 'CO', 'PE', 'AR', 'UY'], 'tier_2_african': ['NG', 'KE', 'EG', 'UG', 'ZW', 'TZ'], 'tier_3': ['BD', 'PK', 'LK', 'MM', 'NP', 'ET', 'RW', 'BF', 'ML', 'SN', 'CI', 'GH', 'VE', 'MA', 'DO']
}
VOLUME_DISCOUNTS = {
    'startup': {'threshold': 0, 'discount': 0.00}, 'growth': {'threshold': 100000, 'discount': 0.10}, 'enterprise': {'threshold': 1000000, 'discount': 0.15}, 'institutional': {'threshold': 10000000, 'discount': 0.20}
}

class Settings(BaseSettings):
    """
    Defines and validates all environment variables. This class is a perfect mirror
    of the required variables in the .env file for the backend to run.
    """
    # --- Core & Security ---
    DATABASE_URL: str
    JWT_SECRET: str
    COMPLYCUBE_API_KEY: str
    ENCRYPTION_KEY: str
    TOKEN_EXPIRATION_MINUTES: int
    MAX_LOGIN_ATTEMPTS: int
    
    # --- Supabase ---
    VITE_SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_JWKS_URI: str
    
    # --- External APIs ---
    ALPHA_VANTAGE_KEY: str
    FLUTTERWAVE_SECRET_KEY: str
    FLUTTERWAVE_PUBLIC_KEY: str
    COINGECKO_API_KEY: str
    CHAINLINK_ETH_USD_FEED: str
    CHAINLINK_BTC_USD_FEED: str

    # --- Algorand Network Configuration ---
    ALGORAND_NODE_URL: str
    ALGORAND_INDEXER_URL: str
    ALGORAND_API_KEY: str
    ALGORAND_CREATOR_MNEMONIC: str
    ALGORAND_NETWORK: str
    USDS_ASSET_ID: int

    # --- Treasury (Sensitive) ---
    TREASURY_ADDRESS: str
    TREASURY_PRIVATE_KEY: str

    # --- Redis (Upstash) ---
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str

    # --- Email Service ---
    MAIL_SERVER: str
    MAIL_PORT: int
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool

    # --- Operational ---
    NODE_ENV: str
    API_URL: str
    ENVIRONMENT: str
    MOCK_MODE: bool

    # --- Static Business Logic (Not from .env) ---
    FEE_STRUCTURE: Dict[str, Any] = FEE_STRUCTURE
    GEOGRAPHIC_TIERS: Dict[str, List[str]] = GEOGRAPHIC_TIERS
    VOLUME_DISCOUNTS: Dict[str, Any] = VOLUME_DISCOUNTS
    
    # --- CORS Configuration (Not from .env) ---
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "https://seamount.io",
        "https://www.seamount.io",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

# --- Singleton Accessor ---
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

# --- Centralized Logger ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)