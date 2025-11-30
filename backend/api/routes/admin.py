# File: backend/api/routes/admin.py
"""
Admin Dashboard Routes - Transaction Monitoring
🚨 SECURITY: Only users with is_admin=True can access
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from backend.dependencies import get_current_user, get_db_service
from backend.services.database_service import DatabaseService

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)

# ============================================================================
# ADMIN ACCESS CONTROL (CRITICAL)
# ============================================================================

def require_admin(current_user: dict = Depends(get_current_user)):
    """
    🚨 SECURITY: Verify user is admin
    Checks both is_admin flag AND role='tribe' (verified users only)
    """
    is_admin = current_user.get('is_admin', False)
    role = current_user.get('role', 'alien')
    
    if not is_admin:
        logger.warning(f"⚠️ Non-admin access attempt: {current_user.get('id')}")
        raise HTTPException(
            status_code=403,
            detail="Admin access required. Contact support to request admin privileges."
        )
    
    if role != 'tribe':
        logger.warning(f"⚠️ Unverified admin attempt: {current_user.get('id')}")
        raise HTTPException(
            status_code=403,
            detail="Admin access requires verified account (Tribe member)"
        )
    
    logger.info(f"✅ Admin access granted: {current_user.get('email')}")
    return current_user

# ============================================================================
# TRANSACTION MONITORING ENDPOINTS
# ============================================================================

@router.get("/transactions/overview")
async def get_transactions_overview(
    hours: int = Query(24, ge=1, le=168),
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """
    📊 HIGH-LEVEL TRANSACTION METRICS
    
    Returns:
    - Total transaction count
    - Success/failure rates
    - Total volume (USD)
    - Breakdown by type (onramp, offramp)
    """
    try:
        time_filter = datetime.utcnow() - timedelta(hours=hours)
        
        # ✅ Query onramp_transactions (using CORRECT column names)
        try:
            onramp_txs = db.supabase.table('onramp_transactions')\
                .select('id, type, status, fiat_amount, fiat_currency, created_at')\
                .gte('created_at', time_filter.isoformat())\
                .execute()
            
            logger.info(f"📊 Onramp transactions found: {len(onramp_txs.data or [])}")
        except Exception as e:
            logger.error(f"❌ Onramp query failed: {e}")
            onramp_txs = type('obj', (object,), {'data': []})()
        
        # ✅ Query offramp_transactions (using CORRECT column names)
        try:
            offramp_txs = db.supabase.table('offramp_transactions')\
                .select('id, type, status, net_fiat_amount, fiat_currency, created_at')\
                .gte('created_at', time_filter.isoformat())\
                .execute()
            
            logger.info(f"📊 Offramp transactions found: {len(offramp_txs.data or [])}")
        except Exception as e:
            logger.error(f"❌ Offramp query failed: {e}")
            offramp_txs = type('obj', (object,), {'data': []})()
        
        # ✅ Combine and normalize data
        all_transactions = []
        
        # Add onramp transactions
        if onramp_txs.data:
            all_transactions.extend([{
                'id': tx['id'],
                'transaction_type': 'onramp',
                'status': tx['status'],
                'amount': float(tx.get('fiat_amount', 0)),  # ✅ CORRECT column
                'currency': tx.get('fiat_currency', 'USD'),  # ✅ CORRECT column
                'created_at': tx['created_at']
            } for tx in onramp_txs.data])
        
        # Add offramp transactions
        if offramp_txs.data:
            all_transactions.extend([{
                'id': tx['id'],
                'transaction_type': 'offramp',
                'status': tx['status'],
                'amount': float(tx.get('net_fiat_amount', 0)),  # ✅ CORRECT column
                'currency': tx.get('fiat_currency', 'USD'),  # ✅ CORRECT column
                'created_at': tx['created_at']
            } for tx in offramp_txs.data])
        
        # ✅ Calculate metrics
        total_transactions = len(all_transactions)
        total_volume = Decimal('0')
        success_count = 0
        failed_count = 0
        processing_count = 0
        
        type_breakdown = {}
        
        for tx in all_transactions:
            status = tx.get('status', 'unknown')
            amount = Decimal(str(tx.get('amount', 0)))
            tx_type = tx.get('transaction_type', 'unknown')
            
            # Count statuses
            if status in ['completed', 'success']:
                success_count += 1
                total_volume += amount
            elif status in ['failed', 'cancelled', 'rejected']:
                failed_count += 1
            elif status in ['processing', 'pending', 'pending_payment']:
                processing_count += 1
            
            # Group by type
            if tx_type not in type_breakdown:
                type_breakdown[tx_type] = {'count': 0, 'volume': Decimal('0')}
            
            type_breakdown[tx_type]['count'] += 1
            if status in ['completed', 'success']:
                type_breakdown[tx_type]['volume'] += amount
        
        success_rate = (success_count / total_transactions * 100) if total_transactions > 0 else 0
        
        return {
            'success': True,
            'time_range_hours': hours,
            'metrics': {
                'total_transactions': total_transactions,
                'success_count': success_count,
                'failed_count': failed_count,
                'processing_count': processing_count,
                'success_rate': round(success_rate, 2),
                'total_volume_usd': float(total_volume),
                'avg_transaction_size': float(total_volume / success_count) if success_count > 0 else 0
            },
            'breakdown_by_type': {
                k: {'count': v['count'], 'volume': float(v['volume'])}
                for k, v in type_breakdown.items()
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Admin overview failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch overview: {str(e)}")


@router.get("/transactions/failed")
async def get_failed_transactions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """
    🚨 FAILED TRANSACTION ANALYSIS
    """
    try:
        # Query failed onramp transactions
        failed_onramp = db.supabase.table('onramp_transactions')\
            .select('id, user_id, type, fiat_amount, fiat_currency, status, created_at')\
            .in_('status', ['failed', 'cancelled', 'rejected'])\
            .order('created_at', desc=True)\
            .limit(limit)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        # Query failed offramp transactions
        failed_offramp = db.supabase.table('offramp_transactions')\
            .select('id, user_id, type, net_fiat_amount, fiat_currency, status, created_at')\
            .in_('status', ['failed', 'cancelled', 'rejected'])\
            .order('created_at', desc=True)\
            .limit(limit)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        # Combine results
        all_failed = []
        
        # Process onramp failures
        if failed_onramp.data:
            for tx in failed_onramp.data:
                user = db.supabase.table('user_profiles')\
                    .select('email, first_name')\
                    .eq('id', tx['user_id'])\
                    .maybe_single()\
                    .execute()
                
                all_failed.append({
                    'transaction_id': tx['id'],
                    'user_email': user.data.get('email') if user.data else 'Unknown',
                    'user_name': user.data.get('first_name') if user.data else 'Unknown',
                    'type': 'onramp',
                    'amount': float(tx.get('fiat_amount', 0)),
                    'currency': tx.get('fiat_currency', 'USD'),
                    'status': tx['status'],
                    'created_at': tx['created_at'],
                    'failure_reason': 'Payment provider error'  # Default reason
                })
        
        # Process offramp failures
        if failed_offramp.data:
            for tx in failed_offramp.data:
                user = db.supabase.table('user_profiles')\
                    .select('email, first_name')\
                    .eq('id', tx['user_id'])\
                    .maybe_single()\
                    .execute()
                
                all_failed.append({
                    'transaction_id': tx['id'],
                    'user_email': user.data.get('email') if user.data else 'Unknown',
                    'user_name': user.data.get('first_name') if user.data else 'Unknown',
                    'type': 'offramp',
                    'amount': float(tx.get('net_fiat_amount', 0)),
                    'currency': tx.get('fiat_currency', 'USD'),
                    'status': tx['status'],
                    'created_at': tx['created_at'],
                    'failure_reason': 'Withdrawal failed'  # Default reason
                })
        
        # Sort by date (newest first)
        all_failed.sort(key=lambda x: x['created_at'], reverse=True)
        
        return {
            'success': True,
            'failed_transactions': all_failed[:limit],
            'total_returned': len(all_failed[:limit]),
            'offset': offset,
            'limit': limit
        }
        
    except Exception as e:
        logger.error(f"❌ Failed transactions query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions/live-feed")
async def get_live_transaction_feed(
    limit: int = Query(20, ge=1, le=100),
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """
    💸 LIVE TRANSACTION FEED
    """
    try:
        # Get recent onramp transactions
        recent_onramp = db.supabase.table('onramp_transactions')\
            .select('id, user_id, type, fiat_amount, fiat_currency, status, created_at')\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        
        # Get recent offramp transactions
        recent_offramp = db.supabase.table('offramp_transactions')\
            .select('id, user_id, type, net_fiat_amount, fiat_currency, status, created_at')\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        
        # Combine and format
        feed = []
        
        # Add onramp transactions
        if recent_onramp.data:
            for tx in recent_onramp.data:
                user = db.supabase.table('user_profiles')\
                    .select('email')\
                    .eq('id', tx['user_id'])\
                    .maybe_single()\
                    .execute()
                
                feed.append({
                    'id': tx['id'],
                    'user_email': user.data.get('email') if user.data else 'Unknown',
                    'type': 'onramp',
                    'amount': float(tx.get('fiat_amount', 0)),
                    'currency': tx.get('fiat_currency', 'USD'),
                    'status': tx['status'],
                    'timestamp': tx['created_at']
                })
        
        # Add offramp transactions
        if recent_offramp.data:
            for tx in recent_offramp.data:
                user = db.supabase.table('user_profiles')\
                    .select('email')\
                    .eq('id', tx['user_id'])\
                    .maybe_single()\
                    .execute()
                
                feed.append({
                    'id': tx['id'],
                    'user_email': user.data.get('email') if user.data else 'Unknown',
                    'type': 'offramp',
                    'amount': float(tx.get('net_fiat_amount', 0)),
                    'currency': tx.get('fiat_currency', 'USD'),
                    'status': tx['status'],
                    'timestamp': tx['created_at']
                })
        
        # Sort by timestamp (newest first)
        feed.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            'success': True,
            'transactions': feed[:limit],
            'count': len(feed[:limit]),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Live feed failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/revenue/uncollected-fees")
async def get_uncollected_fees(
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """
    💰 UNCOLLECTED FEE TRACKING
    
    Shows fees owed by users (from fees_owed table)
    Critical for treasury management
    """
    try:
        pending_fees = db.supabase.table('fees_owed')\
            .select('user_id, chain, asset, fee_amount, status, created_at')\
            .eq('status', 'pending')\
            .execute()
        
        total_owed = Decimal('0')
        by_chain = {}
        
        for fee in (pending_fees.data or []):
            amount = Decimal(str(fee.get('fee_amount', 0)))
            total_owed += amount
            
            chain = fee.get('chain', 'unknown')
            if chain not in by_chain:
                by_chain[chain] = Decimal('0')
            by_chain[chain] += amount
        
        return {
            'success': True,
            'uncollected_fees': {
                'total_usd': float(total_owed),
                'count': len(pending_fees.data or []),
                'by_chain': {k: float(v) for k, v in by_chain.items()}
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Fee tracking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))