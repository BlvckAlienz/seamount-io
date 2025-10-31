# File: backend/api/routes/seed_routes.py
# 🔐 SEED PHRASE RETRIEVAL API ENDPOINTS - WITH DECRYPTION

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any
import logging

from backend.dependencies import (
    get_current_user,
    get_seed_retrieval_service
)
from backend.services.seed_retrieval_service import SeedRetrievalService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/seeds", tags=["seeds"])

@router.get("/recovery")
async def recover_seed_phrases(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    service: SeedRetrievalService = Depends(get_seed_retrieval_service)
) -> Dict[str, Any]:
    """
    🔓 RECOVER DECRYPTED SEED PHRASES
    
    🚨 CRITICAL SECURITY ENDPOINT
    
    This endpoint returns your ACTUAL, UNENCRYPTED seed phrases.
    These are the phrases you need to import your wallets into other platforms.
    
    Security features:
    - Requires JWT authentication
    - Rate limited (3 requests/hour)
    - Audit logged with IP address
    - Seeds decrypted IN-MEMORY only (never saved decrypted)
    - Comprehensive security warnings provided
    
    Response includes:
    - algorand_seed: 25-word Algorand mnemonic (plaintext)
    - wdk_seed: 12-word BIP39 mnemonic for Bitcoin/Ethereum/Polygon/Tron (plaintext)
    - wallet_addresses: All your wallet addresses
    - security_warning: Critical security information
    - backup_instructions: How to safely store your seeds
    """
    try:
        user_id = current_user['id']
        request_ip = request.client.host if request.client else None
        
        logger.warning(f"🔓 SEED RECOVERY REQUEST from user {user_id}, IP: {request_ip}")
        
        result = await service.get_decrypted_seeds(user_id, request_ip)
        
        if not result['success']:
            # Rate limited or error
            status_code = 429 if 'rate limit' in result.get('error', '').lower() else 400
            raise HTTPException(status_code=status_code, detail=result['error'])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Seed recovery endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Failed to recover seeds")


@router.get("/access-log")
async def get_seed_access_log(
    current_user: Dict = Depends(get_current_user),
    service: SeedRetrievalService = Depends(get_seed_retrieval_service)
) -> Dict[str, Any]:
    """
    📜 VIEW SEED ACCESS AUDIT LOG
    
    Returns history of when you accessed your seed phrases,
    including whether they were decrypted or returned encrypted.
    """
    try:
        user_id = current_user['id']
        
        # Query access log
        logs = service.db.supabase.table('seed_access_log')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('accessed_at', desc=True)\
            .limit(20)\
            .execute()
        
        return {
            'success': True,
            'access_history': logs.data if logs.data else [],
            'total_accesses': len(logs.data) if logs.data else 0
        }
        
    except Exception as e:
        logger.error(f"Access log retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve access log")