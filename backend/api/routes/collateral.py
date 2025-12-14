# File: backend/api/routes/collateral.py
"""
Seamount Collateral Management API Routes
Manage locked collateral positions, margin calls, and repo trade collateral
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging

from backend.dependencies import (
    get_current_user,
    get_db_service
)
from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/collateral", tags=["Collateral"])

@router.get("/positions")
async def get_positions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    📋 Get user's collateral positions
    
    Returns all locked collateral for repos, DVP settlements, etc.
    """
    try:
        logger.info(f"Fetching collateral positions for user {current_user['id']}")
        
        positions = db_service.supabase.table('collateral_positions')\
            .select('*, tokenized_assets(symbol, name, current_price_usd)')\
            .eq('user_id', current_user['id'])\
            .execute()
        
        # Enrich with asset data
        enriched_positions = []
        for pos in (positions.data or []):
            if pos.get('tokenized_assets'):
                pos['asset_symbol'] = pos['tokenized_assets'].get('symbol')
                pos['asset_name'] = pos['tokenized_assets'].get('name')
            enriched_positions.append(pos)
        
        return {
            "success": True,
            "positions": enriched_positions
        }
    except Exception as e:
        logger.error(f"Failed to fetch collateral positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/release/{position_id}")
async def release_collateral(
    position_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    🔓 Release locked collateral
    
    Only works for non-repo positions. Repo collateral releases automatically on maturity.
    """
    try:
        logger.info(f"Release request for position {position_id} by user {current_user['id']}")
        
        # Verify ownership
        position = db_service.supabase.table('collateral_positions')\
            .select('*')\
            .eq('id', position_id)\
            .eq('user_id', current_user['id'])\
            .single()\
            .execute()
        
        if not position.data:
            raise HTTPException(status_code=404, detail="Position not found or not owned by you")
        
        # Check if it's a repo position (cannot be manually released)
        if position.data.get('lock_type') == 'repo':
            raise HTTPException(
                status_code=400, 
                detail="Repo collateral cannot be manually released. Wait for maturity or repay loan."
            )
        
        # Update status
        db_service.supabase.table('collateral_positions').update({
            'status': 'released'
        }).eq('id', position_id).execute()
        
        logger.info(f"✅ Collateral released: {position_id}")
        
        return {
            "success": True,
            "message": "Collateral released successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to release collateral: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_collateral_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    📊 Get collateral summary metrics
    """
    try:
        positions = db_service.supabase.table('collateral_positions')\
            .select('*')\
            .eq('user_id', current_user['id'])\
            .eq('status', 'active')\
            .execute()
        
        total_value = sum(p.get('current_value_usd', 0) for p in (positions.data or []))
        repo_count = len([p for p in (positions.data or []) if p.get('lock_type') == 'repo'])
        dvp_count = len([p for p in (positions.data or []) if p.get('lock_type') == 'dvp_settlement'])
        
        return {
            "success": True,
            "summary": {
                "total_positions": len(positions.data or []),
                "total_value_usd": total_value,
                "repo_positions": repo_count,
                "dvp_positions": dvp_count
            }
        }
    except Exception as e:
        logger.error(f"Failed to fetch collateral summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))