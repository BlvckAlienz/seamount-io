# File: backend/api/routes/wallet_backup_routes.py
# 🔐 WALLET BACKUP TRACKING ROUTES - PRODUCTION READY

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from backend.services.database_service import DatabaseService
from backend.dependencies import get_current_user, get_db_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/wallet-backup", tags=["wallet-backup"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class MarkBackedUpRequest(BaseModel):
    chains: List[str] = Field(
        ..., 
        description="Chains backed up: ['algorand'] or ['bitcoin', 'ethereum', 'polygon', 'tron']"
    )


class BackupStatusResponse(BaseModel):
    success: bool
    algorand_backed_up: bool
    multichain_backed_up: bool
    all_backups_complete: bool
    algorand_backup_date: Optional[str] = None
    multichain_backup_date: Optional[str] = None
    show_recovery_modal: bool


# ============================================
# ENDPOINTS
# ============================================

@router.post("/mark-backed-up")
async def mark_backup_downloaded(
    request: MarkBackedUpRequest,
    req: Request,
    current_user: dict = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service)
):
    """
    🎯 Mark seed phrases as backed up
    
    Called when user downloads seed files from WalletRecoveryModal.
    Updates database flags and logs the event to audit trail.
    
    Args:
        chains: List of blockchain names that were backed up
        
    Returns:
        Success confirmation with timestamp
    """
    try:
        user_id = current_user['user_id']
        client_ip = req.client.host if hasattr(req, 'client') else 'unknown'
        timestamp = datetime.utcnow().isoformat()
        
        logger.info(f"📥 Backup request from user {user_id}: chains={request.chains}")
        
        # ============================================
        # Update Algorand backup status
        # ============================================
        if 'algorand' in request.chains:
            try:
                result = db.supabase.table('user_wallets')\
                    .update({
                        'algorand_backup_downloaded': True,
                        'algorand_backup_downloaded_at': timestamp,
                        'algorand_backup_ip': client_ip
                    })\
                    .eq('user_id', user_id)\
                    .execute()
                
                if result.data:
                    logger.info(f"✅ Algorand backup marked for user {user_id}")
                else:
                    logger.warning(f"⚠️ No Algorand wallet found for user {user_id}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to mark Algorand backup: {e}")
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to update Algorand backup status"
                )
        
        # ============================================
        # Update multi-chain backup status
        # ============================================
        multichain_chains = [c for c in request.chains if c != 'algorand']
        if multichain_chains:
            try:
                # Update ALL multi-chain addresses (they share same seed)
                result = db.supabase.table('multi_chain_addresses')\
                    .update({
                        'backup_downloaded': True,
                        'backup_downloaded_at': timestamp,
                        'backup_ip': client_ip
                    })\
                    .eq('user_id', user_id)\
                    .execute()
                
                if result.data:
                    updated_count = len(result.data)
                    logger.info(f"✅ Multi-chain backup marked for user {user_id} ({updated_count} addresses)")
                else:
                    logger.warning(f"⚠️ No multi-chain wallets found for user {user_id}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to mark multi-chain backup: {e}")
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to update multi-chain backup status"
                )
        
        # ============================================
        # Log to audit trail
        # ============================================
        try:
            db.supabase.table('seed_access_log')\
                .insert({
                    'user_id': user_id,
                    'accessed_at': timestamp,
                    'request_ip': client_ip,
                    'action': 'BACKUP_DOWNLOADED',
                    'chains_accessed': request.chains,
                    'algorand_accessed': 'algorand' in request.chains,
                    'wdk_accessed': len(multichain_chains) > 0,
                    'decrypted': False  # This is just marking backup, not decryption
                })\
                .execute()
            logger.debug(f"📊 Backup event logged for user {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to log backup event: {e}")
            # Don't fail the request if logging fails
        
        return {
            'success': True,
            'message': f'Backup confirmed for: {", ".join(request.chains)}',
            'timestamp': timestamp,
            'chains': request.chains
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Mark backup failed for user {current_user.get('user_id')}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to mark backup: {str(e)}"
        )


@router.get("/status", response_model=BackupStatusResponse)
async def get_backup_status(
    current_user: dict = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service)
):
    """
    🔍 Get user's wallet backup status
    
    Returns whether user has downloaded seed backups.
    Used by dashboard to decide whether to show recovery modal.
    
    Returns:
        BackupStatusResponse with flags and show_recovery_modal boolean
    """
    try:
        user_id = current_user['user_id']
        
        logger.debug(f"🔍 Checking backup status for user {user_id}")
        
        # ============================================
        # Query backup status using RPC function
        # ============================================
        try:
            status = db.supabase.rpc(
                'get_user_backup_status', 
                {'p_user_id': user_id}
            ).execute()
        except Exception as e:
            logger.error(f"❌ RPC call failed: {e}")
            # Fallback: Query view directly
            status = db.supabase.table('user_wallet_backup_status')\
                .select('*')\
                .eq('user_id', user_id)\
                .execute()
        
        # ============================================
        # Handle no wallets case
        # ============================================
        if not status.data or len(status.data) == 0:
            logger.info(f"ℹ️ No wallets found for user {user_id}")
            return BackupStatusResponse(
                success=True,
                algorand_backed_up=False,
                multichain_backed_up=False,
                all_backups_complete=False,
                show_recovery_modal=False  # Don't show modal if no wallets exist
            )
        
        # ============================================
        # Parse backup status
        # ============================================
        backup_data = status.data[0]
        
        algo_backed = backup_data.get('algorand_backup_downloaded', False)
        multi_backed = backup_data.get('multichain_backup_downloaded', False)
        all_complete = backup_data.get('all_backups_complete', False)
        
        logger.info(
            f"📊 User {user_id} backup status: "
            f"Algo={algo_backed}, Multi={multi_backed}, Complete={all_complete}"
        )
        
        return BackupStatusResponse(
            success=True,
            algorand_backed_up=algo_backed,
            multichain_backed_up=multi_backed,
            all_backups_complete=all_complete,
            algorand_backup_date=backup_data.get('algorand_backup_downloaded_at'),
            multichain_backup_date=backup_data.get('multichain_backup_downloaded_at'),
            show_recovery_modal=not all_complete  # Show modal ONLY if backups incomplete
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get backup status failed for user {current_user.get('user_id')}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get backup status: {str(e)}"
        )


# ============================================
# HEALTH CHECK (for debugging)
# ============================================

@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        'status': 'healthy',
        'service': 'wallet-backup-tracking',
        'endpoints': [
            'POST /api/v1/wallet-backup/mark-backed-up',
            'GET /api/v1/wallet-backup/status'
        ]
    }