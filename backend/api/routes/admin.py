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
    📊 COMPREHENSIVE TRANSACTION METRICS
    Queries ALL transaction tables: onramp, offramp, multi_chain, cross_border, swaps, payments
    """
    try:
        time_filter = datetime.utcnow() - timedelta(hours=hours)
        all_transactions = []
        
        # ========== TABLE CONFIGURATIONS ==========
        table_configs = [
            {
                'name': 'onramp_transactions',
                'type': 'onramp',
                'amount_fields': ['amount', 'fiat_amount', 'amount_fiat', 'net_to_user', 'amount_paid'],
                'currency_fields': ['currency', 'fiat_currency']
            },
            {
                'name': 'offramp_transactions',
                'type': 'offramp',
                'amount_fields': ['net_fiat_amount', 'amount', 'fiat_amount', 'withdrawal_amount'],
                'currency_fields': ['fiat_currency', 'currency']
            },
            {
                'name': 'multi_chain_transactions',
                'type': 'transfer',
                'amount_fields': ['amount', 'value', 'crypto_amount'],
                'currency_fields': ['asset', 'currency', 'crypto_asset']
            },
            {
                'name': 'cross_border_transfers',
                'type': 'cross_border',
                'amount_fields': ['amount', 'amount_usd', 'value'],
                'currency_fields': ['currency', 'asset']
            },
            {
                'name': 'asset_swaps',
                'type': 'swap',
                'amount_fields': ['from_amount', 'to_amount', 'amount'],
                'currency_fields': ['from_asset', 'to_asset', 'currency']
            },
            {
                'name': 'payment_transactions',
                'type': 'payment',
                'amount_fields': ['amount', 'value'],
                'currency_fields': ['currency', 'asset']
            },
            {
                'name': 'bridge_transactions',
                'type': 'bridge',
                'amount_fields': ['amount', 'value'],
                'currency_fields': ['asset', 'currency']
            }
        ]
        
        # ========== QUERY EACH TABLE ==========
        for config in table_configs:
            try:
                logger.info(f"🔍 Querying {config['name']}...")
                
                result = db.supabase.table(config['name'])\
                    .select('*')\
                    .gte('created_at', time_filter.isoformat())\
                    .execute()
                
                if result.data:
                    logger.info(f"✅ {config['name']}: Found {len(result.data)} transactions")
                    
                    # Log columns for first row (debugging)
                    if len(result.data) > 0:
                        logger.info(f"📋 {config['name']} columns: {list(result.data[0].keys())}")
                    
                    # Extract and normalize data
                    for tx in result.data:
                        # Smart amount detection
                        amount = 0
                        for field in config['amount_fields']:
                            if field in tx and tx[field] is not None:
                                try:
                                    amount = float(tx[field])
                                    break
                                except (ValueError, TypeError):
                                    continue
                        
                        # Smart currency detection
                        currency = 'USD'
                        for field in config['currency_fields']:
                            if field in tx and tx[field]:
                                currency = str(tx[field])
                                break
                        
                        all_transactions.append({
                            'id': tx.get('id'),
                            'type': config['type'],
                            'status': tx.get('status', 'unknown'),
                            'amount': amount,
                            'currency': currency,
                            'created_at': tx.get('created_at'),
                            'user_id': tx.get('user_id')
                        })
                else:
                    logger.info(f"ℹ️ {config['name']}: No transactions found")
                    
            except Exception as table_error:
                logger.warning(f"⚠️ {config['name']} query failed (table may not exist): {table_error}")
                continue
        
        # ========== CALCULATE METRICS ==========
        total_transactions = len(all_transactions)
        
        logger.info(f"📊 Total transactions across all tables: {total_transactions}")
        
        if total_transactions == 0:
            return {
                'success': True,
                'time_range_hours': hours,
                'metrics': {
                    'total_transactions': 0,
                    'success_count': 0,
                    'failed_count': 0,
                    'processing_count': 0,
                    'success_rate': 0,
                    'total_volume_usd': 0,
                    'avg_transaction_size': 0
                },
                'breakdown_by_type': {},
                'timestamp': datetime.utcnow().isoformat(),
                'message': f'No transactions found in the last {hours} hours'
            }
        
        # Status counts
        success_statuses = ['completed', 'success', 'confirmed', 'settled']
        failed_statuses = ['failed', 'cancelled', 'rejected', 'error']
        processing_statuses = ['processing', 'pending', 'pending_payment', 'initiated']
        
        success_count = sum(1 for tx in all_transactions if tx['status'] in success_statuses)
        failed_count = sum(1 for tx in all_transactions if tx['status'] in failed_statuses)
        processing_count = sum(1 for tx in all_transactions if tx['status'] in processing_statuses)
        
        # Calculate volume (only successful)
        total_volume = sum(
            tx['amount'] for tx in all_transactions 
            if tx['status'] in success_statuses and tx['amount'] > 0
        )
        
        success_rate = (success_count / total_transactions * 100) if total_transactions > 0 else 0
        avg_size = (total_volume / success_count) if success_count > 0 else 0
        
        # Breakdown by type
        type_breakdown = {}
        for tx in all_transactions:
            tx_type = tx['type']
            if tx_type not in type_breakdown:
                type_breakdown[tx_type] = {
                    'count': 0,
                    'volume': 0,
                    'successful': 0,
                    'failed': 0
                }
            
            type_breakdown[tx_type]['count'] += 1
            
            if tx['status'] in success_statuses:
                type_breakdown[tx_type]['volume'] += tx['amount']
                type_breakdown[tx_type]['successful'] += 1
            elif tx['status'] in failed_statuses:
                type_breakdown[tx_type]['failed'] += 1
        
        # Format breakdown
        formatted_breakdown = {
            k: {
                'count': v['count'],
                'volume': round(v['volume'], 2),
                'successful': v['successful'],
                'failed': v['failed']
            }
            for k, v in type_breakdown.items()
        }
        
        return {
            'success': True,
            'time_range_hours': hours,
            'metrics': {
                'total_transactions': total_transactions,
                'success_count': success_count,
                'failed_count': failed_count,
                'processing_count': processing_count,
                'success_rate': round(success_rate, 2),
                'total_volume_usd': round(total_volume, 2),
                'avg_transaction_size': round(avg_size, 2)
            },
            'breakdown_by_type': formatted_breakdown,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Admin overview failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to fetch overview: {str(e)}")


@router.get("/transactions/failed")
async def get_failed_transactions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """🚨 FAILED TRANSACTION ANALYSIS - All Tables"""
    try:
        failed_txs = []
        
        # Tables to check for failures
        tables = [
            'onramp_transactions',
            'offramp_transactions', 
            'multi_chain_transactions',
            'cross_border_transfers',
            'payment_transactions'
        ]
        
        for table_name in tables:
            try:
                result = db.supabase.table(table_name)\
                    .select('*')\
                    .in_('status', ['failed', 'cancelled', 'rejected', 'error'])\
                    .order('created_at', desc=True)\
                    .limit(limit)\
                    .execute()
                
                if result.data:
                    for tx in result.data:
                        # Get user info
                        user = db.supabase.table('user_profiles')\
                            .select('email, first_name')\
                            .eq('id', tx.get('user_id'))\
                            .maybe_single()\
                            .execute()
                        
                        # Smart amount detection
                        amount = (
                            tx.get('amount') or 
                            tx.get('fiat_amount') or 
                            tx.get('net_fiat_amount') or 
                            tx.get('crypto_amount') or 
                            0
                        )
                        
                        # Smart currency detection
                        currency = (
                            tx.get('currency') or 
                            tx.get('fiat_currency') or 
                            tx.get('asset') or 
                            'USD'
                        )
                        
                        failed_txs.append({
                            'transaction_id': tx.get('id'),
                            'user_email': user.data.get('email') if user.data else 'Unknown',
                            'user_name': user.data.get('first_name') if user.data else 'Unknown',
                            'type': table_name.replace('_transactions', '').replace('_transfers', ''),
                            'amount': float(amount),
                            'currency': currency,
                            'status': tx.get('status'),
                            'created_at': tx.get('created_at'),
                            'failure_reason': tx.get('error_message') or tx.get('failure_reason') or 'Unknown'
                        })
                        
            except Exception as e:
                logger.warning(f"⚠️ Failed to query {table_name}: {e}")
                continue
        
        # Sort by date
        failed_txs.sort(key=lambda x: x['created_at'], reverse=True)
        
        return {
            'success': True,
            'failed_transactions': failed_txs[:limit],
            'total_returned': len(failed_txs[:limit]),
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
    """💸 LIVE TRANSACTION FEED - All Tables"""
    try:
        feed = []
        
        # Tables to include in live feed
        tables = [
            'onramp_transactions',
            'offramp_transactions',
            'multi_chain_transactions',
            'cross_border_transfers',
            'payment_transactions',
            'asset_swaps'
        ]
        
        for table_name in tables:
            try:
                result = db.supabase.table(table_name)\
                    .select('*')\
                    .order('created_at', desc=True)\
                    .limit(limit)\
                    .execute()
                
                if result.data:
                    for tx in result.data:
                        # Get user email
                        user = db.supabase.table('user_profiles')\
                            .select('email')\
                            .eq('id', tx.get('user_id'))\
                            .maybe_single()\
                            .execute()
                        
                        # Smart amount detection
                        amount = (
                            tx.get('amount') or 
                            tx.get('fiat_amount') or 
                            tx.get('net_fiat_amount') or 
                            tx.get('crypto_amount') or 
                            tx.get('from_amount') or 
                            0
                        )
                        
                        # Smart currency detection
                        currency = (
                            tx.get('currency') or 
                            tx.get('fiat_currency') or 
                            tx.get('asset') or 
                            tx.get('from_asset') or 
                            'USD'
                        )
                        
                        feed.append({
                            'id': tx.get('id'),
                            'user_email': user.data.get('email') if user.data else 'Unknown',
                            'type': table_name.replace('_transactions', '').replace('_transfers', ''),
                            'amount': float(amount),
                            'currency': currency,
                            'status': tx.get('status', 'unknown'),
                            'timestamp': tx.get('created_at')
                        })
                        
            except Exception as e:
                logger.warning(f"⚠️ Failed to query {table_name} for live feed: {e}")
                continue
        
        # Sort by timestamp
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