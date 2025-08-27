import logging
from typing import List, Optional
from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Defines and validates all environment variables for the Seamount API using Pydantic.
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
    
    # --- Email Service (NEWLY ADDED AND REQUIRED) ---
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

    @computed_field
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """
        Parses the ALLOWED_ORIGINS_STR into a list for FastAPI's CORS middleware.
        """
        if not self.ALLOWED_ORIGINS_STR:
            # Provides sensible defaults if the env var is not set.
            return ["http://localhost:3000", "http://localhost:5173", "https://seamount.io", "https://www.seamount.io"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_STR.split(',')]

# --- Singleton Pattern for Settings ---
_settings_instance: Optional[Settings] = None

def get_settings() -> Settings:
    """
    Returns a cached instance of the application settings.
    """
    global _settings_instance
    if _settings_instance is None:
        try:
            _settings_instance = Settings()
            logger.info("Configuration loaded and validated successfully.")
            logger.info(f"Environment: {_settings_instance.ENVIRONMENT}")
            logger.info(f"ComplyCube API Key: {'Configured' if _settings_instance.COMPLYCUBE_API_KEY else 'NOT CONFIGURED'}")
        except Exception as e:
            logger.critical(f"FATAL: FAILED TO LOAD OR VALIDATE CONFIGURATION. Error: {e}", exc_info=True)
            raise
    return _settings_instance