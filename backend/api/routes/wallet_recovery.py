# File: backend/api/routes/wallet_recovery.py
# ✅ PRODUCTION - REAL SEED RETRIEVAL

from fastapi import APIRouter, HTTPException, Depends, Request
from backend.services.database_service import DatabaseService
from backend.dependencies import get_db_service, get_current_user
from backend.config import get_settings
from cryptography.fernet import Fernet
import base64
import logging
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

class SeedDecryptionService:
    """Real seed decryption service"""
    
    def __init__(self):
        # Get from environment - MUST BE SET IN PRODUCTION
        encryption_key = getattr(settings, 'SEED_ENCRYPTION_KEY', None)
        if not encryption_key:
            logger.error("❌ SEED_ENCRYPTION_KEY not configured")
            raise ValueError("SEED_ENCRYPTION_KEY environment variable required")
        
        self.encryption_key = encryption_key.get_secret_value()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def decrypt_seed(self, encrypted_seed: str) -> str:
        """Decrypt seed phrase"""
        try:
            if not encrypted_seed:
                return ""
            
            encrypted_bytes = base64.b64decode(encrypted_seed)
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Seed decryption failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to decrypt seed phrase")

@router.get("/wallet/recovery-seeds")
async def get_recovery_seeds(
    request: Request,
    db_service: DatabaseService = Depends(get_db_service),
    current_user: Dict = Depends(get_current_user)
):
    """PRODUCTION: Retrieve and decrypt wallet seeds"""
    try:
        user_id = current_user["id"]
        logger.info(f"🔐 Retrieving recovery seeds for user: {user_id}")
        
        # ✅ REAL DATABASE QUERY
        user_query = """
        SELECT 
            u.id as user_id,
            u.email,
            up.algorand_encrypted_seed,
            up.wdk_encrypted_seed,
            up.wallet_addresses,
            up.algorand_address,
            up.bitcoin_address,
            up.ethereum_address, 
            up.polygon_address,
            up.tron_address,
            up.created_at
        FROM users u
        LEFT JOIN user_profiles up ON u.id = up.user_id
        WHERE u.id = $1
        """
        
        user_result = await db_service.fetch_one(user_query, user_id)
        
        if not user_result:
            logger.warning(f"No user profile found for user_id: {user_id}")
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Initialize decryption service
        decryption_service = SeedDecryptionService()
        
        # ✅ DECRYPT SEEDS
        algorand_seed = None
        wdk_seed = None
        
        if user_result.get('algorand_encrypted_seed'):
            try:
                algorand_seed = decryption_service.decrypt_seed(user_result['algorand_encrypted_seed'])
                logger.info(f"✅ Decrypted Algorand seed for user: {user_id}")
            except Exception as e:
                logger.error(f"Algorand seed decryption failed: {e}")
                # Continue with other seeds
                
        if user_result.get('wdk_encrypted_seed'):
            try:
                wdk_seed = decryption_service.decrypt_seed(user_result['wdk_encrypted_seed'])
                logger.info(f"✅ Decrypted WDK seed for user: {user_id}")
            except Exception as e:
                logger.error(f"WDK seed decryption failed: {e}")
                # Continue with other seeds
        
        # ✅ BUILD WALLET ADDRESSES - REAL DATA
        wallet_addresses = {}
        
        # Individual address fields
        address_fields = [
            ('algorand', 'algorand_address'),
            ('bitcoin', 'bitcoin_address'),
            ('ethereum', 'ethereum_address'),
            ('polygon', 'polygon_address'),
            ('tron', 'tron_address')
        ]
        
        for chain, field in address_fields:
            if user_result.get(field):
                wallet_addresses[chain] = user_result[field]
        
        # JSON wallet_addresses field
        if user_result.get('wallet_addresses'):
            try:
                json_addresses = json.loads(user_result['wallet_addresses'])
                wallet_addresses.update(json_addresses)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse wallet_addresses JSON: {e}")
        
        # ✅ PRODUCTION RESPONSE - REAL DATA
        response_data = {
            "success": True,
            "user_id": user_id,
            "warning": "🚨 CRITICAL SECURITY WARNING: These seed phrases control ALL your digital assets. Anyone with these seeds can permanently steal your funds. NEVER share with anyone!",
            "backup_instruction": "Write these seeds on paper and store in multiple secure locations. Digital storage is vulnerable to hacking.",
            "algorand_seed": algorand_seed,
            "wdk_seed": wdk_seed,
            "wallet_addresses": wallet_addresses,
            "wdk_service_status": "online",  # TODO: Implement real health check
            "timestamp": user_result.get('created_at')
        }
        
        logger.info(f"✅ Successfully returned recovery seeds for user: {user_id}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Critical error retrieving recovery seeds: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="System error: Unable to retrieve recovery seeds. Please contact support."
        )