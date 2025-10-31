# File: backend/services/seed_encryption_service.py
# ✅ PRODUCTION: Encrypt seeds before storing in database

from backend.config import get_settings
from cryptography.fernet import Fernet
import base64
import logging

logger = logging.getLogger(__name__)

class SeedEncryptionService:
    """Production-grade seed encryption service"""
    
    def __init__(self):
        settings = get_settings()
        self.encryption_key = settings.SEED_ENCRYPTION_KEY.get_secret_value()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def encrypt_seed(self, seed_phrase: str) -> str:
        """Encrypt seed phrase for secure database storage"""
        try:
            if not seed_phrase:
                return ""
            
            # Encrypt and encode to base64
            encrypted_bytes = self.cipher_suite.encrypt(seed_phrase.encode('utf-8'))
            return base64.b64encode(encrypted_bytes).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Seed encryption failed: {e}")
            raise Exception("Failed to encrypt seed phrase")
    
    def decrypt_seed(self, encrypted_seed: str) -> str:
        """Decrypt seed phrase from database"""
        try:
            if not encrypted_seed:
                return ""
            
            encrypted_bytes = base64.b64decode(encrypted_seed)
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Seed decryption failed: {e}")
            raise Exception("Failed to decrypt seed phrase")