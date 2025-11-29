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
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 7 days
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """
    📊 HIGH-LEVEL TRANSACTION METRICS
    
    Returns:
    - Total transaction count
    - Success/failure rates
    - Total volume (USD)
    - Breakdown by type (onramp, offramp, transfer)
    """
    try:
        time_filter = datetime.utcnow() - timedelta(hours=hours)
        
        # Query main transactions table
        overview_query = """
            SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count,
                COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_count,
                SUM(CASE WHEN status = 'completed' THEN CAST(amount AS NUMERIC) ELSE 0 END) as total_volume,
                transaction_type,
                currency
            FROM transactions
            WHERE created_at >= %s
            GROUP BY transaction_type, currency
        """
        
        # Execute via Supabase RPC or direct query
        # Note: For RLS compliance, this uses service role context
        results = db.supabase.rpc(
            'admin_transaction_overview',
            {'since_timestamp': time_filter.isoformat()}
        ).execute()
        
        if not results.data:
            # Fallback: Direct table query (requires service role)
            results = db.supabase.table('transactions')\
                .select('transaction_type, status, amount, currency')\
                .gte('created_at', time_filter.isoformat())\
                .execute()
        
        # Process results
        total_transactions = 0
        total_volume = Decimal('0')
        success_count = 0
        failed_count = 0
        
        type_breakdown = {}
        
        for row in (results.data or []):
            total_transactions += 1
            status = row.get('status')
            amount = Decimal(str(row.get('amount', 0)))
            tx_type = row.get('transaction_type', 'unknown')
            
            if status == 'completed':
                success_count += 1
                total_volume += amount
            elif status == 'failed':
                failed_count += 1
            
            # Group by type
            if tx_type not in type_breakdown:
                type_breakdown[tx_type] = {'count': 0, 'volume': Decimal('0')}
            
            type_breakdown[tx_type]['count'] += 1
            if status == 'completed':
                type_breakdown[tx_type]['volume'] += amount
        
        success_rate = (success_count / total_transactions * 100) if total_transactions > 0 else 0
        
        return {
            'success': True,
            'time_range_hours': hours,
            'metrics': {
                'total_transactions': total_transactions,
                'success_count': success_count,
                'failed_count': failed_count,
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
    
    Returns recent failed transactions with:
    - User info (email, not sensitive data)
    - Amount and asset
    - Failure reason
    - Timestamp
    """
    try:
        # Query failed transactions across all tables
        failed_txs = db.supabase.table('transactions')\
            .select('id, user_id, transaction_type, amount, currency, status, created_at, metadata')\
            .in_('status', ['failed', 'cancelled', 'rejected'])\
            .order('created_at', desc=True)\
            .limit(limit)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        # Enrich with user emails (non-sensitive)
        enriched = []
        for tx in (failed_txs.data or []):
            user_id = tx.get('user_id')
            
            # Get user email (admins can see this per RLS)
            user_profile = db.supabase.table('user_profiles')\
                .select('email, first_name')\
                .eq('id', user_id)\
                .maybe_single()\
                .execute()
            
            enriched.append({
                'transaction_id': tx['id'],
                'user_email': user_profile.data.get('email') if user_profile.data else 'Unknown',
                'user_name': user_profile.data.get('first_name') if user_profile.data else 'Unknown',
                'type': tx['transaction_type'],
                'amount': float(tx.get('amount', 0)),
                'currency': tx.get('currency'),
                'status': tx['status'],
                'created_at': tx['created_at'],
                'failure_reason': tx.get('metadata', {}).get('error') if tx.get('metadata') else 'Unknown'
            })
        
        return {
            'success': True,
            'failed_transactions': enriched,
            'total_returned': len(enriched),
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
    
    Most recent transactions across all types
    Auto-refreshable for real-time monitoring
    """
    try:
        recent_txs = db.supabase.table('transactions')\
            .select('id, user_id, transaction_type, amount, currency, status, created_at')\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        
        feed = []
        for tx in (recent_txs.data or []):
            # Get user email
            user = db.supabase.table('user_profiles')\
                .select('email')\
                .eq('id', tx['user_id'])\
                .maybe_single()\
                .execute()
            
            feed.append({
                'id': tx['id'],
                'user_email': user.data.get('email') if user.data else 'Unknown',
                'type': tx['transaction_type'],
                'amount': float(tx.get('amount', 0)),
                'currency': tx.get('currency'),
                'status': tx['status'],
                'timestamp': tx['created_at']
            })
        
        return {
            'success': True,
            'transactions': feed,
            'count': len(feed),
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