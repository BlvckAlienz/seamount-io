# File: backend/services/wallet_recovery_service.py
# 🛡️ SAFE RECOVERY SERVICE - BACKWARD COMPATIBLE

import logging
from typing import Dict, List, Optional
from datetime import datetime
from cryptography.fernet import Fernet
from backend.config import get_settings
from backend.services.database_service import DatabaseService, EncryptedSeed

logger = logging.getLogger(__name__)

class SafeRecoveryService:
    """Safe wallet recovery service - works with any table structure"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.settings = get_settings()
        self.fernet = Fernet(self.settings.ENCRYPTION_KEY.get_secret_value())
    
    async def recover_wallet_seeds(self, user_id: str) -> Dict[str, any]:
        """
        Safe recovery method - works with any table structure
        """
        try:
            logger.info(f"🛡️ Starting safe recovery for: {user_id}")
            
            # 1. Get user profile using safe method
            user_profile = await self.db_service.get_or_create_user_profile(user_id)
            if not user_profile:
                return {
                    "success": False,
                    "error": "User profile not found or could not be created",
                    "user_id": user_id
                }
            
            # 2. Get encrypted seeds using safe method
            encrypted_seeds = await self.db_service.get_encrypted_seeds(user_id)
            if not encrypted_seeds:
                return {
                    "success": False,
                    "error": "No encrypted seeds found. Wallets may not be created yet.",
                    "user_id": user_id,
                    "user_email": getattr(user_profile, 'email', ''),
                    "user_name": f"{getattr(user_profile, 'first_name', '')} {getattr(user_profile, 'last_name', '')}".strip()
                }
            
            # 3. Get wallet addresses for context
            wallet_addresses = await self.db_service.get_wallet_addresses(user_id)
            
            # 4. Decrypt seeds safely
            decrypted_data = await self._decrypt_seeds_safely(encrypted_seeds)
            
            # 5. Return recovery data
            return {
                "success": True,
                "user_id": user_id,
                "user_email": getattr(user_profile, 'email', ''),
                "user_name": f"{getattr(user_profile, 'first_name', '')} {getattr(user_profile, 'last_name', '')}".strip(),
                "warning": "🔴 CRITICAL SECURITY: These seed phrases control access to your digital assets. Never share with anyone!",
                "backup_instruction": "Write these down and store in multiple secure locations. Losing these means permanent loss of funds.",
                **decrypted_data,
                "wallet_addresses": wallet_addresses,
                "recovery_timestamp": datetime.utcnow().isoformat(),
                "seeds_found": len(encrypted_seeds)
            }
            
        except Exception as e:
            logger.error(f"❌ Safe recovery failed for {user_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Recovery system error: {str(e)}",
                "user_id": user_id
            }
    
    async def _decrypt_seeds_safely(self, encrypted_seeds: List[EncryptedSeed]) -> Dict[str, any]:
        """Safe decryption with comprehensive error handling"""
        algorand_seed = None
        wdk_seed = None
        decryption_errors = []
        
        for seed_data in encrypted_seeds:
            try:
                if not seed_data.encrypted_seed:
                    continue
                
                # Decrypt the seed safely
                decrypted_seed = self.fernet.decrypt(seed_data.encrypted_seed.encode()).decode()
                
                # Categorize by blockchain
                if seed_data.blockchain == 'algorand':
                    algorand_seed = decrypted_seed
                    logger.info(f"✅ Decrypted Algorand seed for address: {getattr(seed_data, 'address', 'Unknown')}")
                elif seed_data.blockchain in ['bitcoin', 'ethereum', 'polygon', 'tron']:
                    # Use the first WDK seed we find (they should be the same)
                    if not wdk_seed:
                        wdk_seed = decrypted_seed
                        logger.info(f"✅ Decrypted WDK seed from {seed_data.blockchain} for address: {getattr(seed_data, 'address', 'Unknown')}")
                        
            except Exception as e:
                error_msg = f"Failed to decrypt {seed_data.blockchain} seed: {str(e)}"
                decryption_errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
                continue
        
        return {
            "algorand_seed": algorand_seed,
            "wdk_seed": wdk_seed,
            "decryption_status": {
                "algorand_decrypted": algorand_seed is not None,
                "wdk_decrypted": wdk_seed is not None,
                "errors": decryption_errors,
                "total_seeds_processed": len(encrypted_seeds),
                "successful_decryptions": (1 if algorand_seed else 0) + (1 if wdk_seed else 0)
            }
        }
    
    async def check_recovery_readiness(self, user_id: str) -> Dict[str, any]:
        """Check if user can recover wallets safely"""
        try:
            ecosystem_status = await self.db_service.verify_wallet_ecosystem(user_id)
            user_profile = await self.db_service.get_or_create_user_profile(user_id)
            
            return {
                "user_id": user_id,
                "user_ready": bool(user_profile),
                "user_has_name": bool(getattr(user_profile, 'first_name', None)),
                "ecosystem_status": ecosystem_status,
                "recovery_ready": ecosystem_status["recovery_ready"],
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Recovery readiness check failed: {str(e)}")
            return {
                "user_id": user_id,
                "user_ready": False,
                "user_has_name": False,
                "ecosystem_status": {},
                "recovery_ready": False,
                "error": str(e)
            }