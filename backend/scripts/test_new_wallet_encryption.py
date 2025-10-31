# File: backend/scripts/test_new_wallet_encryption.py
# 🧪 ISOLATED ENCRYPTION TEST - NO SERVICE DEPENDENCIES

import sys
import os
import logging
import base64
from cryptography.fernet import Fernet

# Direct import without triggering service chain
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import only what we need
from algosdk import account, mnemonic

class TestEncryptionService:
    """Standalone encryption for testing"""
    
    def __init__(self):
        # Get key from environment
        encryption_key = os.getenv('ENCRYPTION_KEY') or os.getenv('SEED_ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("No ENCRYPTION_KEY in environment")
        
        self.cipher_suite = Fernet(
            encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        )
        logger.info("Test encryption service initialized")
    
    def encrypt_seed(self, seed_phrase: str) -> str:
        """Encrypt seed phrase"""
        encrypted_bytes = self.cipher_suite.encrypt(seed_phrase.encode('utf-8'))
        encrypted_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
        return encrypted_b64
    
    def decrypt_seed(self, encrypted_seed: str) -> str:
        """Decrypt seed phrase"""
        # Strip whitespace
        encrypted_clean = encrypted_seed.strip()
        
        # Fix padding
        missing_padding = len(encrypted_clean) % 4
        if missing_padding:
            encrypted_clean += '=' * (4 - missing_padding)
        
        # Decode and decrypt
        encrypted_bytes = base64.b64decode(encrypted_clean)
        decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
        return decrypted_bytes.decode('utf-8')

def test_encryption_roundtrip():
    """Test encrypt -> decrypt cycle"""
    print("=" * 70)
    print("TESTING ENCRYPTION ROUND-TRIP")
    print("=" * 70)
    
    # Initialize service
    encryption_service = TestEncryptionService()
    
    # Generate test Algorand wallet
    private_key, address = account.generate_account()
    original_mnemonic = mnemonic.from_private_key(private_key)
    
    print("\nOriginal mnemonic:")
    print(f"   Words: {len(original_mnemonic.split())}")
    print(f"   First 50 chars: {original_mnemonic[:50]}...")
    
    # Encrypt
    print("\nEncrypting...")
    encrypted = encryption_service.encrypt_seed(original_mnemonic)
    print(f"   Encrypted length: {len(encrypted)}")
    print(f"   First 50 chars: {encrypted[:50]}...")
    
    # Decrypt
    print("\nDecrypting...")
    decrypted = encryption_service.decrypt_seed(encrypted)
    print(f"   Decrypted words: {len(decrypted.split())}")
    print(f"   First 50 chars: {decrypted[:50]}...")
    
    # Verify match
    if original_mnemonic == decrypted:
        print("\nSUCCESS! Encryption/decryption works perfectly!")
        print("   Original == Decrypted")
        return True
    else:
        print("\nFAILURE! Mismatch detected!")
        print(f"   Original: {original_mnemonic[:100]}...")
        print(f"   Decrypted: {decrypted[:100]}...")
        return False

if __name__ == "__main__":
    success = test_encryption_roundtrip()
    sys.exit(0 if success else 1)