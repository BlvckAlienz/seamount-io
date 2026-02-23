# File: backend/api/routes/wallet_creation_routes.py
# 🔌 API ENDPOINTS FOR WALLET CREATION STATUS & RETRY

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
import logging
import asyncio 

from backend.dependencies import (
    get_current_user,
    get_wallet_creation_service
)
from backend.services.wallet_creation_service import WalletCreationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/wallet-creation", tags=["wallet-creation"])

@router.get("/status")
async def get_wallet_creation_status(
    current_user: dict = Depends(get_current_user),
    service: WalletCreationService = Depends(get_wallet_creation_service)
):
    """Get wallet creation status with smart detection"""
    try:
        user_id = current_user['id']
        status = await service.get_wallet_status(user_id)
        return status
    except Exception as e:
        logger.error(f"Error fetching wallet creation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/smart-initialize")
async def smart_initialize_wallet_creation(
    current_user: dict = Depends(get_current_user),
    service: WalletCreationService = Depends(get_wallet_creation_service)
):
    """
    Smart initialization: detects existing wallets and only tracks missing ones
    """
    try:
        user_id = current_user['id']
        result = await service.initialize_smart_wallet_status(user_id)
        return result
    except Exception as e:
        logger.error(f"Error in smart initialization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/retry-missing")
async def retry_missing_wallets(
    chains: Optional[List[str]] = None,
    current_user: dict = Depends(get_current_user),
    service: WalletCreationService = Depends(get_wallet_creation_service)
):
    """
    Smart retry: Only retry wallets that are actually missing
    """
    try:
        user_id = current_user['id']
        result = await service.retry_missing_wallets(user_id, chains)
        return result
    except Exception as e:
        logger.error(f"Error retrying missing wallets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry")
async def retry_wallet_creation(
    chains: Optional[List[str]] = None,
    current_user: dict = Depends(get_current_user),
    service: WalletCreationService = Depends(get_wallet_creation_service)
):
    """
    Manually retry failed wallet creations.
    
    Args:
        chains: Optional list of specific chains to retry. If None, retries all failed.
    
    Returns:
        {
            "success": bool,
            "message": "...",
            "retried_chains": ["bitcoin", "ethereum"],
            "results": {
                "bitcoin": {"success": true, "address": "..."},
                "ethereum": {"success": false, "error": "..."}
            }
        }
    """
    try:
        user_id = current_user['id']
        
        logger.info(f"🔄 User {user_id} requesting wallet retry for chains: {chains or 'all failed'}")
        
        # Check current status first
        current_status = await service.get_wallet_status(user_id)
        
        if current_status['overall_complete']:
            return {
                "success": True,
                "message": "All wallets already created successfully!",
                "retried_chains": [],
                "results": {}
            }
        
        # Check retry limit
        if current_status.get('retry_count', 0) >= 10:
            raise HTTPException(
                status_code=429,
                detail="Maximum retry attempts reached. Please contact support."
            )
        
        # Validate chain names if provided
        if chains:
            valid_chains = ['algorand', 'bitcoin', 'ethereum', 'polygon', 'tron', 'solana', 'xrp']
            invalid_chains = [c for c in chains if c not in valid_chains]
            if invalid_chains:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid chain names: {invalid_chains}"
                )
        
        # Perform retry
        result = await service.retry_missing_wallets(user_id, chains)
        
        return {
            "success": True,
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying wallet creation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incomplete-users")
async def get_incomplete_users(
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    service: WalletCreationService = Depends(get_wallet_creation_service)
):
    """
    Admin endpoint: Get list of users with incomplete wallet creation.
    Requires admin privileges.
    """
    # Check if user is admin
    if not current_user.get('is_admin'):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # This would query users with incomplete wallet creation
        # Implementation depends on your admin system
        return {
            "success": True,
            "message": "Admin endpoint for monitoring incomplete wallets",
            "users": []  # Implement actual query
        }
    except Exception as e:
        logger.error(f"Error fetching incomplete users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/background-retry")
async def trigger_background_retry(
    current_user: dict = Depends(get_current_user),
    service: WalletCreationService = Depends(get_wallet_creation_service)
):
    """
    Admin endpoint: Manually trigger background retry queue processing.
    """
    if not current_user.get('is_admin'):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        await service.process_retry_queue()
        return {
            "success": True,
            "message": "Background retry queue processed"
        }
    except Exception as e:
        logger.error(f"Error processing retry queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize")
async def initialize_wallet_creation(
    force: bool = False,
    current_user: dict = Depends(get_current_user),
    service: WalletCreationService = Depends(get_wallet_creation_service)
):
    """
    Initialize wallet creation status for current user.
    This creates the 4 chain status records.
    
    Args:
        force: If True, will reinitialize even if already initialized
    """
    try:
        user_id = current_user['id']
        logger.info(f"🔄 Initializing wallet creation status for user {user_id} (force: {force})")
        
        # Check if already initialized
        profile = await service.db.get_user_profile(user_id)
        
        if not force and profile and profile.get('wallet_creation_started_at') is not None:
            current_status = await service.get_wallet_status(user_id)
            return {
                "success": True,
                "message": "Wallet status already initialized. Use force=true to reinitialize.",
                "user_id": user_id,
                "existing_chains": list(current_status['chains'].keys()),
                "started_at": profile.get('wallet_creation_started_at')
            }
        
        # If force=true, delete existing records first
        if force:
            logger.info(f"🔄 Force reinitializing - clearing existing records for {user_id}")
            await asyncio.to_thread(
                lambda: service.db.supabase.table("wallet_creation_status")
                .delete()
                .eq("user_id", user_id)
                .execute()
            )
        
        # Initialize wallet status
        await service._initialize_wallet_status(user_id)
        
        # Get updated status
        updated_status = await service.get_wallet_status(user_id)
        
        action = "reinitialized" if force else "initialized"
        return {
            "success": True,
            "message": f"Wallet creation status {action} successfully",
            "user_id": user_id,
            "initialized_chains": list(updated_status['chains'].keys()),
            "status": updated_status
        }
        
    except Exception as e:
        logger.error(f"Error initializing wallet creation: {e}")
        raise HTTPException(status_code=500, detail=str(e))