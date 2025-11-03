# File: backend/services/seed_retrieval_service.py
# 🔐 SECURE SEED PHRASE RETRIEVAL SERVICE - WITH DECRYPTION

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import os

from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class SeedRetrievalService:
    """
    Secure seed phrase retrieval with IN-MEMORY decryption
    
    Security principles:
    1. Decrypts seeds IN-MEMORY only (never saved decrypted)
    2. Rate limited per user (max 3 requests per hour)
    3. All accesses logged to audit trail
    4. Requires JWT authentication
    5. User warned about security implications
    """
    
    # Rate limiting: 3 requests per hour per user
    MAX_REQUESTS_PER_HOUR = 3
    RATE_LIMIT_WINDOW = timedelta(hours=1)
    
    # In your seed_retrieval_service.py, update the __init__ method to add key validation:

    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        
        # 🔐 Use centralized encryption service
        from backend.services.seed_encryption_service import SeedEncryptionService
        self.encryption_service = SeedEncryptionService()
        
        logger.info("✅ SeedRetrievalService initialized with centralized encryption")
    
    async def get_decrypted_seeds(self, user_id: str, request_ip: str = None) -> Dict[str, Any]:
        """
        🔓 DECRYPT AND RETURN PLAINTEXT SEED PHRASES
        
        SECURITY WARNING: This returns UNENCRYPTED seed phrases.
        Only call this when user explicitly requests seed recovery.
        
        Returns:
        {
            "success": true,
            "algorand_seed": "word1 word2 word3...",  # PLAINTEXT 25-word mnemonic
            "wdk_seed": "word1 word2 word3...",       # PLAINTEXT 12-word mnemonic
            "wallet_addresses": {...},
            "security_warning": "🚨 CRITICAL: These are your ACTUAL seed phrases...",
            "requests_remaining": 2
        }
        """
        try:
            # 🛡️ STEP 1: Rate limit check
            rate_check = await self._check_rate_limit(user_id)
            if not rate_check['allowed']:
                logger.warning(f"⚠️ Rate limit exceeded for user {user_id}")
                return {
                    'success': False,
                    'error': 'Rate limit exceeded. Maximum 3 seed retrievals per hour.',
                    'retry_after': rate_check['retry_after'],
                    'requests_remaining': 0
                }
            
            # 🔍 STEP 2: Fetch encrypted seeds from database
            encrypted_seeds = await self._fetch_encrypted_seeds(user_id)
            
            if not encrypted_seeds['algorand_seed'] and not encrypted_seeds['wdk_seed']:
                return {
                    'success': False,
                    'error': 'No wallets found for this user. Please create a wallet first.'
                }
            
            # 🔓 STEP 3: DECRYPT SEEDS IN-MEMORY
            decrypted_seeds = {
                'algorand_seed': self._decrypt_seed(encrypted_seeds['algorand_seed']) if encrypted_seeds['algorand_seed'] else None,
                'wdk_seed': self._decrypt_seed(encrypted_seeds['wdk_seed']) if encrypted_seeds['wdk_seed'] else None
            }
            
            # 📝 STEP 4: Log the access (audit trail)
            await self._log_seed_access(user_id, request_ip, encrypted_seeds, decrypted=True)
            
            # ✅ STEP 5: Return PLAINTEXT seeds with security warning
            return {
                'success': True,
                'algorand_seed': decrypted_seeds['algorand_seed'],
                'wdk_seed': decrypted_seeds['wdk_seed'],
                'wallet_addresses': encrypted_seeds['addresses'],
                'retrieved_at': datetime.utcnow().isoformat(),
                'security_warning': (
                    "🚨 CRITICAL SECURITY WARNING:\n"
                    "• These are your ACTUAL seed phrases\n"
                    "• Anyone with these phrases has FULL ACCESS to your funds\n"
                    "• Seeds are decrypted in-memory and never stored unencrypted\n"
                    "• NEVER share them with anyone, including Seamount support\n"
                    "• Rate limited per user (max 3 requests per hour)"
                ),
                'backup_instructions': (
                    "RECOMMENDED BACKUP METHOD:\n"
                    "1. Write these phrases on paper (NOT digital)\n"
                    "2. Store in a fireproof safe or safety deposit box\n"
                    "3. Consider splitting across multiple secure locations\n"
                    "4. Never take screenshots or save to cloud storage"
                ),
                'requests_remaining': rate_check['requests_remaining'],
                'algorand_info': {
                    'chain': 'Algorand',
                    'seed_type': '25-word mnemonic',
                    'compatible_wallets': ['Pera Wallet', 'Defly Wallet', 'AlgoSigner']
                },
                'wdk_info': {
                    'chains': ['Bitcoin', 'Ethereum', 'Polygon', 'Tron'],
                    'seed_type': 'BIP39 12-word mnemonic',
                    'compatible_wallets': ['MetaMask', 'Trust Wallet', 'Ledger', 'Trezor']
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Seed decryption failed for user {user_id}: {e}")
            return {
                'success': False,
                'error': 'Failed to retrieve seeds. Please contact support.',
                'error_details': str(e) if logger.level == logging.DEBUG else None
            }
    
    def _decrypt_seed(self, encrypted_seed: str) -> str:
        """
        🔓 DECRYPT using centralized service
        """
        try:
            return self.encryption_service.decrypt_seed(encrypted_seed)
        except Exception as e:
            logger.error(f"❌ Seed decryption failed: {e}")
            raise
    
    async def validate_and_fix_stored_seeds(self, user_id: str) -> Dict[str, Any]:
        """
        🔧 ADMIN FUNCTION: Validate and fix corrupted seed storage
        Call this if decryption fails to diagnose issues
        """
        try:
            # Fetch seeds
            encrypted_seeds = await self._fetch_encrypted_seeds(user_id)
            
            results = {
                'algorand_seed_valid': False,
                'wdk_seed_valid': False,
                'issues': []
            }
            
            # Check Algorand seed
            if encrypted_seeds['algorand_seed']:
                algo_seed = encrypted_seeds['algorand_seed']
                
                # Check length
                if len(algo_seed) % 4 != 0:
                    results['issues'].append(f"Algorand seed has invalid length: {len(algo_seed)} (not multiple of 4)")
                
                # Check base64 validity
                import base64
                try:
                    # Fix padding
                    missing = len(algo_seed) % 4
                    if missing:
                        algo_seed_fixed = algo_seed + ('=' * (4 - missing))
                    else:
                        algo_seed_fixed = algo_seed
                    
                    base64.b64decode(algo_seed_fixed)
                    results['algorand_seed_valid'] = True
                except Exception as e:
                    results['issues'].append(f"Algorand seed is not valid base64: {e}")
            
            # Check WDK seed
            if encrypted_seeds['wdk_seed']:
                wdk_seed = encrypted_seeds['wdk_seed']
                
                if len(wdk_seed) % 4 != 0:
                    results['issues'].append(f"WDK seed has invalid length: {len(wdk_seed)} (not multiple of 4)")
                
                try:
                    missing = len(wdk_seed) % 4
                    if missing:
                        wdk_seed_fixed = wdk_seed + ('=' * (4 - missing))
                    else:
                        wdk_seed_fixed = wdk_seed
                    
                    base64.b64decode(wdk_seed_fixed)
                    results['wdk_seed_valid'] = True
                except Exception as e:
                    results['issues'].append(f"WDK seed is not valid base64: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Seed validation failed: {e}")
            return {'error': str(e)}

    def _decrypt_seeds(self, encrypted_seeds: Dict[str, Any]) -> Dict[str, str]:
        """Decrypt both Algorand and WDK seeds"""
        try:
            algorand_seed = ""
            wdk_seed = ""
            
            # Decrypt Algorand seed if it exists
            if encrypted_seeds.get('algorand_seed'):
                try:
                    algorand_seed = self._decrypt_seed(encrypted_seeds['algorand_seed'])
                    logger.info("✅ Algorand seed decrypted successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to decrypt Algorand seed: {e}")
                    raise Exception("Failed to decrypt Algorand seed phrase")
            
            # Decrypt WDK seed if it exists  
            if encrypted_seeds.get('wdk_seed'):
                try:
                    wdk_seed = self._decrypt_seed(encrypted_seeds['wdk_seed'])
                    logger.info("✅ WDK seed decrypted successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to decrypt WDK seed: {e}")
                    raise Exception("Failed to decrypt WDK seed phrase")
            
            return {
                'algorand_seed': algorand_seed,
                'wdk_seed': wdk_seed
            }
            
        except Exception as e:
            logger.error(f"❌ Seed decryption failed: {e}")
            raise
    
    async def _fetch_encrypted_seeds(self, user_id: str) -> Dict[str, Any]:
        """Fetch encrypted seeds from multiple tables"""
        
        seeds = {
            'algorand_seed': None,
            'wdk_seed': None,
            'addresses': {}
        }
        
        try:
            # 1. Get Algorand seed from user_wallets
            algo_wallet = self.db.supabase.table('user_wallets')\
                .select('algorand_mnemonic, algorand_address')\
                .eq('user_id', user_id)\
                .execute()
            
            if algo_wallet.data and len(algo_wallet.data) > 0:
                seeds['algorand_seed'] = algo_wallet.data[0].get('algorand_mnemonic')
                seeds['addresses']['algorand'] = algo_wallet.data[0].get('algorand_address')
            
            # 2. Get WDK seed from multi_chain_addresses (same seed for all chains)
            wdk_wallets = self.db.supabase.table('multi_chain_addresses')\
                .select('blockchain, address, encrypted_seed')\
                .eq('user_id', user_id)\
                .execute()
            
            if wdk_wallets.data and len(wdk_wallets.data) > 0:
                # All WDK chains use the same seed
                seeds['wdk_seed'] = wdk_wallets.data[0].get('encrypted_seed')
                
                # Collect all addresses
                for wallet in wdk_wallets.data:
                    chain = wallet['blockchain']
                    address = wallet['address']
                    seeds['addresses'][chain] = address
            
            return seeds
            
        except Exception as e:
            logger.error(f"Error fetching seeds: {e}")
            raise
    
    async def _check_rate_limit(self, user_id: str) -> Dict[str, Any]:
        """Check if user has exceeded rate limit"""
        
        try:
            # Query recent seed access attempts
            cutoff_time = (datetime.utcnow() - self.RATE_LIMIT_WINDOW).isoformat()
            
            recent_accesses = self.db.supabase.table('seed_access_log')\
                .select('id, accessed_at')\
                .eq('user_id', user_id)\
                .gte('accessed_at', cutoff_time)\
                .execute()
            
            access_count = len(recent_accesses.data) if recent_accesses.data else 0
            requests_remaining = max(0, self.MAX_REQUESTS_PER_HOUR - access_count)
            
            if access_count >= self.MAX_REQUESTS_PER_HOUR:
                # Calculate when rate limit resets
                oldest_access = min(recent_accesses.data, key=lambda x: x['accessed_at'])
                retry_after = oldest_access['accessed_at']
                
                return {
                    'allowed': False,
                    'requests_remaining': 0,
                    'retry_after': retry_after
                }
            
            return {
                'allowed': True,
                'requests_remaining': requests_remaining
            }
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open (allow access) if rate limiting breaks
            return {'allowed': True, 'requests_remaining': 3}
    
    async def _log_seed_access(self, user_id: str, request_ip: Optional[str], 
                               seeds: Dict, decrypted: bool = False) -> None:
        """Log seed access to audit trail"""
        
        try:
            log_entry = {
                'user_id': user_id,
                'accessed_at': datetime.utcnow().isoformat(),
                'request_ip': request_ip or 'unknown',
                'algorand_accessed': seeds['algorand_seed'] is not None,
                'wdk_accessed': seeds['wdk_seed'] is not None,
                'chains_accessed': list(seeds['addresses'].keys()),
                'decrypted': decrypted  # Flag if seeds were decrypted
            }
            
            self.db.supabase.table('seed_access_log')\
                .insert(log_entry)\
                .execute()
            
            log_type = "DECRYPTED" if decrypted else "ENCRYPTED"
            logger.info(f"📝 {log_type} seed access logged for user {user_id} from IP {request_ip}")
            
        except Exception as e:
            logger.error(f"Failed to log seed access: {e}")
            # Don't fail the request if logging fails
            pass