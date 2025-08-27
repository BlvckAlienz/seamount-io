import logging
from typing import List, Set, Dict, Any, Optional
from pydantic import Field, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Defines and validates all environment variables for the Seamount API using Pydantic.
    Secrets are automatically handled as SecretStr types.
    """
    # --- Model Configuration ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=False
    )

    # --- Core & Security ---
    # CRITICAL: Define secrets using SecretStr to get the .get_secret_value() method.
    ENCRYPTION_KEY: SecretStr
    IPINFO_TOKEN: SecretStr
    
    # --- Supabase ---
    VITE_SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: SecretStr
    SUPABASE_JWKS_URI: str
    SUPABASE_JWT_ISSUER: str # Important for token validation

    # --- KYC Provider (ComplyCube) ---
    # Making this optional allows the app to run without it for development.
    COMPLYCUBE_API_KEY: Optional[SecretStr] = None
    COMPLYCUBE_WEBHOOK_SECRET: Optional[SecretStr] = None
    
    # --- Algorand Network ---
    ALGORAND_NODE_URL: str
    ALGORAND_INDEXER_URL: str
    ALGORAND_API_KEY: SecretStr
    
    # --- CORS Configuration ---
    # This field reads the comma-separated string from the .env file.
    # It is private and not intended for direct use.
    ALLOWED_ORIGINS_STR: str = Field("", alias='ALLOWED_ORIGINS')

    # --- Operational ---
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # --- Computed Fields ---
    # This is the modern and correct Pydantic V2 way to create a derived property.
    @computed_field
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """
        Parses the ALLOWED_ORIGINS_STR into a list of strings for FastAPI's CORS middleware.
        Provides sensible defaults for local development.
        """
        if not self.ALLOWED_ORIGINS_STR:
            if self.ENVIRONMENT == "development":
                return [
                    "http://localhost:3000", 
                    "http://localhost:5173",
                ]
            return [] # In production, an empty string means no origins are allowed unless explicitly set.
        
        # Split the string by commas and strip any whitespace from each origin.
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_STR.split(',')]

# --- Singleton Pattern for Settings ---
# This ensures that the settings are loaded from the environment only once.
_settings_instance: Optional[Settings] = None

def get_settings() -> Settings:
    """
    Returns a cached instance of the application settings.
    This is the sole entry point for accessing configuration throughout the app.
    """
    global _settings_instance
    if _settings_instance is None:
        try:
            _settings_instance = Settings()
            logger.info("Configuration loaded and validated successfully.")
            # Log key configuration statuses for easier debugging.
            logger.info(f"Environment: {_settings_instance.ENVIRONMENT}")
            logger.info(f"Debug Mode: {_settings_instance.DEBUG}")
            logger.info(f"ComplyCube API Key: {'Configured' if _settings_instance.COMPLYCUBE_API_KEY else 'NOT CONFIGURED'}")
        except Exception as e:
            logger.critical(f"FATAL: FAILED TO LOAD OR VALIDATE CONFIGURATION. Error: {e}", exc_info=True)
            # This will prevent the application from starting if config is invalid.
            raise
    return _settings_instance