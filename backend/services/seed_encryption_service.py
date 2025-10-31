# File: backend/services/seed_encryption_service.py
# 🔒 BULLETPROOF SEED ENCRYPTION - SINGLE SOURCE OF TRUTH

import logging
import base64
from cryptography.fernet import Fernet
from typing import Optional

logger = logging.getLogger(__name__)

class SeedEncryptionService:
    """
    🎯 SINGLE SOURCE OF TRUTH for seed encryption/decryption
    
    CRITICAL RULES:
    1. Always base64 encode AFTER encryption
    2. Always strip and pad BEFORE decryption
    3. Use SAME key from environment
    4. Log everything for debugging
    """
    
    def __init__(self):
        """Initialize with encryption key from environment"""
        import os
        from backend.config import get_settings
        
        settings = get_settings()
        
        # Get key with fallback chain
        try:
            if hasattr(settings, 'SEED_ENCRYPTION_KEY'):
                encryption_key = settings.SEED_ENCRYPTION_KEY.get_secret_value()
            elif hasattr(settings, 'ENCRYPTION_KEY'):
                encryption_key = settings.ENCRYPTION_KEY.get_secret_value()
            else:
                encryption_key = os.getenv('ENCRYPTION_KEY') or os.getenv('SEED_ENCRYPTION_KEY')
            
            if not encryption_key:
                raise ValueError("❌ No encryption key found!")
            
            # Create cipher suite
            self.cipher_suite = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
            logger.info("✅ SeedEncryptionService initialized")
            
        except Exception as e:
            logger.critical(f"❌ Encryption service init failed: {e}")
            raise
    
    def encrypt_seed(self, seed_phrase: str) -> str:
        """
        🔐 ENCRYPT seed phrase for database storage
        
        Format: plaintext → Fernet encrypt → base64 encode → string
        """
        try:
            if not seed_phrase or not seed_phrase.strip():
                raise ValueError("Empty seed phrase")
            
            # Step 1: Encrypt
            encrypted_bytes = self.cipher_suite.encrypt(seed_phrase.encode('utf-8'))
            
            # Step 2: Base64 encode for database storage
            encrypted_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
            
            logger.debug(f"✅ Seed encrypted (output length: {len(encrypted_b64)})")
            return encrypted_b64
            
        except Exception as e:
            logger.error(f"❌ Seed encryption failed: {e}")
            raise Exception(f"Failed to encrypt seed: {str(e)}")
    
    def decrypt_seed(self, encrypted_seed: str) -> str:
        """
        🔓 DECRYPT seed phrase from database
        
        Format: string → strip → add padding → base64 decode → Fernet decrypt → plaintext
        """
        try:
            if not encrypted_seed or not encrypted_seed.strip():
                raise ValueError("Empty encrypted seed")
            
            # Step 1: Sanitize (remove whitespace/newlines)
            encrypted_clean = encrypted_seed.strip()
            
            # Step 2: Fix base64 padding if needed
            missing_padding = len(encrypted_clean) % 4
            if missing_padding:
                encrypted_clean += '=' * (4 - missing_padding)
                logger.debug(f"🔧 Added {4 - missing_padding} padding chars")
            
            # Step 3: Base64 decode
            try:
                encrypted_bytes = base64.b64decode(encrypted_clean)
            except Exception as b64_err:
                logger.error(f"❌ Base64 decode failed: {b64_err}")
                logger.error(f"   Input length: {len(encrypted_clean)}")
                logger.error(f"   First 50 chars: {encrypted_clean[:50]}")
                raise Exception(f"Invalid base64: {str(b64_err)}")
            
            # Step 4: Fernet decrypt
            try:
                decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
            except Exception as fernet_err:
                logger.error(f"❌ Fernet decrypt failed: {fernet_err}")
                raise Exception(f"Invalid encryption: {str(fernet_err)}")
            
            # Step 5: Decode to string
            seed_phrase = decrypted_bytes.decode('utf-8')
            
            word_count = len(seed_phrase.split())
            logger.debug(f"✅ Seed decrypted ({word_count} words)")
            
            return seed_phrase
            
        except Exception as e:
            logger.error(f"❌ Seed decryption failed: {e}")
            raise Exception(f"Failed to decrypt seed: {str(e)}")
    
    def validate_seed_format(self, seed_phrase: str, expected_words: int) -> bool:
        """Validate seed phrase format"""
        try:
            words = seed_phrase.strip().split()
            if len(words) != expected_words:
                logger.warning(f"⚠️  Expected {expected_words} words, got {len(words)}")
                return False
            return True
        except Exception as e:
            logger.error(f"Seed validation failed: {e}")
            return False