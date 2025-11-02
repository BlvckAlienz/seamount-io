# File: backend/api/routes/wallet_backup.py
# 📍 Wallet backup tracking routes

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import logging
from datetime import datetime

from backend.dependencies import get_current_user, get_database_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/wallet-backup", tags=["wallet-backup"])

@router.get("/status")
async def get_backup_status(
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_database_service)
):
    """Get which wallets have been backed up by user"""
    try:
        user_id = current_user['id']
        
        # Query backup tracking table (Supabase is SYNC, not async)
        result = db_service.supabase.table('wallet_backup_tracking')\
            .select('*')\
            .eq('user_id', user_id)\
            .execute()
        
        backed_up_chains = [r['chain'] for r in result.data] if result.data else []
        
        return {
            'success': True,
            'backed_up_chains': backed_up_chains,
            'needs_backup': len(backed_up_chains) == 0,  # Show modal if nothing backed up
            'user_id': user_id
        }
        
    except Exception as e:
        logger.error(f"Backup status query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mark-backed-up")
async def mark_chains_backed_up(
    chains: List[str],
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_database_service)
):
    """Mark specific chains as backed up"""
    try:
        user_id = current_user['id']
        
        # Insert records for each chain
        records = [{
            'user_id': user_id,
            'chain': chain,
            'backed_up_at': datetime.utcnow().isoformat(),
            'backup_method': 'modal_download'
        } for chain in chains]
        
        db_service.supabase.table('wallet_backup_tracking')\
            .upsert(records)\
            .execute()
        
        logger.info(f"✅ Marked {len(chains)} chains as backed up for user {user_id}")
        
        return {
            'success': True,
            'message': f'Backup recorded for {len(chains)} chains',
            'backed_up_chains': chains
        }
        
    except Exception as e:
        logger.error(f"Backup tracking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))