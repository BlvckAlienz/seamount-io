# File: backend/api/routes/admin.py
"""
Admin Dashboard Routes - Transaction Monitoring
🚨 SECURITY: Only users with is_admin=True can access
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel
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
            },
            {
                'name': 'transactions',
                'type': 'transaction',
                'amount_fields': ['amount', 'value', 'transaction_amount'],
                'currency_fields': ['currency', 'asset', 'symbol']
            },
            {
                'name': 'daily_revenue_summary',
                'type': 'revenue',
                'amount_fields': ['total_revenue', 'net_revenue', 'gross_revenue', 'amount'],
                'currency_fields': ['currency']
            },
            {
                'name': 'fees_owed',
                'type': 'fee',
                'amount_fields': ['fee_amount', 'amount', 'owed_amount'],
                'currency_fields': ['asset', 'currency', 'chain']
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
    
@router.get("/revenue/summary")
async def get_revenue_summary(
    days: int = Query(30, ge=1, le=365),
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """
    💰 REVENUE SUMMARY - CORRECTED for actual schema
    
    Schema: revenue_date, total_revenue, transaction_count, avg_transaction_value
    """
    try:
        time_filter = datetime.utcnow() - timedelta(days=days)
        
        # ========== QUERY DAILY REVENUE (using revenue_date) ==========
        try:
            daily_revenue = db.supabase.table('daily_revenue_summary')\
                .select('*')\
                .gte('revenue_date', time_filter.date().isoformat())\
                .order('revenue_date', desc=True)\
                .execute()
            
            total_revenue = sum(
                float(row.get('total_revenue', 0)) 
                for row in (daily_revenue.data or [])
            )
            
            total_transactions = sum(
                int(row.get('transaction_count', 0))
                for row in (daily_revenue.data or [])
            )
            
            avg_transaction = (
                total_revenue / total_transactions 
                if total_transactions > 0 else 0
            )
            
            logger.info(f"💰 Daily revenue records: {len(daily_revenue.data or [])} | Total: ${total_revenue:.2f}")
            
        except Exception as e:
            logger.warning(f"⚠️ Daily revenue query failed: {e}")
            daily_revenue = type('obj', (object,), {'data': []})()
            total_revenue = 0
            total_transactions = 0
            avg_transaction = 0
        
        # ========== QUERY FEES OWED ==========
        try:
            fees_owed = db.supabase.table('fees_owed')\
                .select('*')\
                .eq('status', 'pending')\
                .execute()
            
            total_owed = sum(
                float(row.get('fee_amount', 0)) 
                for row in (fees_owed.data or [])
            )
            
            # Group by chain
            owed_by_chain = {}
            for row in (fees_owed.data or []):
                chain = row.get('chain', 'unknown')
                amount = float(row.get('fee_amount', 0))
                
                if chain not in owed_by_chain:
                    owed_by_chain[chain] = 0
                owed_by_chain[chain] += amount
            
            logger.info(f"💸 Uncollected fees: ${total_owed:.2f}")
            
        except Exception as e:
            logger.warning(f"⚠️ Fees owed query failed: {e}")
            fees_owed = type('obj', (object,), {'data': []})()
            total_owed = 0
            owed_by_chain = {}
        
        # ========== REVENUE BY DATE ==========
        revenue_by_date = {}
        
        if daily_revenue.data:
            for row in daily_revenue.data:
                date_str = str(row.get('revenue_date', 'unknown'))
                revenue_by_date[date_str] = {
                    'revenue': float(row.get('total_revenue', 0)),
                    'transactions': int(row.get('transaction_count', 0)),
                    'avg_value': float(row.get('avg_transaction_value', 0))
                }
        
        # ========== COLLECTION RATE ==========
        total_fees_generated = total_revenue + total_owed
        collection_rate = (
            (total_revenue / total_fees_generated * 100) 
            if total_fees_generated > 0 else 100
        )
        
        return {
            'success': True,
            'time_range_days': days,
            'revenue_summary': {
                'total_collected': round(total_revenue, 2),
                'total_owed': round(total_owed, 2),
                'collection_rate': round(collection_rate, 2),
                'net_position': round(total_revenue - total_owed, 2),
                'total_transactions': total_transactions,
                'avg_transaction_value': round(avg_transaction, 2)
            },
            'uncollected_fees': {
                'total_usd': round(total_owed, 2),
                'count': len(fees_owed.data or []),
                'by_chain': {k: round(v, 2) for k, v in owed_by_chain.items()}
            },
            'revenue_by_date': revenue_by_date,
            'daily_records': len(daily_revenue.data or []),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Revenue summary failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
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

# ============================================================================
# ON-RAMP MONITOR  (onramp_transactions — 94 rows, real data)
# ============================================================================

@router.get("/onramp/summary")
async def get_onramp_summary(
    days: int = Query(30, ge=1, le=365),
    exclude_test: bool = Query(True), 
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """
    On-ramp funnel — conversion rate, stuck payments, provider breakdown.
    Queries: onramp_transactions (status, provider, currency, amount_fiat, seamount_fee)
    """
    try:
        time_filter = (datetime.utcnow() - timedelta(days=days)).isoformat()

        query = db.supabase.table("onramp_transactions") \
            .select(
                "id,user_id,user_email,status,provider,currency,"
                "crypto_asset,amount_fiat,seamount_fee,net_to_user,"
                "created_at,completed_at,failed_at"
            ) \
            .gte("created_at", time_filter) \
            .order("created_at", desc=True) 
        
        # Exclude test records if flagged
        if exclude_test:
            query = query.eq("is_test", False)

        res = query.execute()

        rows = res.data or []

        # Status breakdown
        status_counts: dict = {}
        provider_counts: dict = {}
        currency_counts: dict = {}
        total_fiat = 0.0
        total_fees = 0.0
        completed_fiat = 0.0

        for r in rows:
            s = r.get("status", "unknown")
            p = r.get("provider", "unknown")
            c = r.get("currency", "unknown")
            amt = float(r.get("amount_fiat") or 0)
            fee = float(r.get("seamount_fee") or 0)

            status_counts[s]   = status_counts.get(s, 0) + 1
            provider_counts[p] = provider_counts.get(p, 0) + 1
            currency_counts[c] = currency_counts.get(c, 0) + 1
            total_fiat        += amt
            total_fees        += fee
            if s in ("completed", "success", "confirmed"):
                completed_fiat += amt

        total = len(rows)
        completed = status_counts.get("completed", 0) + status_counts.get("success", 0)
        pending   = status_counts.get("pending_payment", 0) + status_counts.get("pending", 0)
        failed    = status_counts.get("failed", 0) + status_counts.get("cancelled", 0)
        conversion_rate = round(completed / total * 100, 1) if total > 0 else 0

        # Stuck payments: pending_payment for > 2 hours
        stuck_cutoff = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        stuck = [
            {
                "id": r["id"],
                "user_email": r.get("user_email"),
                "currency": r.get("currency"),
                "amount_fiat": float(r.get("amount_fiat") or 0),
                "crypto_asset": r.get("crypto_asset"),
                "provider": r.get("provider"),
                "created_at": r.get("created_at"),
                "checkout_url": None  # not selected for brevity
            }
            for r in rows
            if r.get("status") == "pending_payment"
            and (r.get("created_at") or "") < stuck_cutoff
        ]

        # Recent 20 for live feed
        recent = [
            {
                "id": r["id"],
                "user_email": r.get("user_email"),
                "status": r.get("status"),
                "provider": r.get("provider"),
                "currency": r.get("currency"),
                "amount_fiat": float(r.get("amount_fiat") or 0),
                "seamount_fee": float(r.get("seamount_fee") or 0),
                "crypto_asset": r.get("crypto_asset"),
                "created_at": r.get("created_at"),
                "completed_at": r.get("completed_at"),
            }
            for r in rows[:20]
        ]

        return {
            "success": True,
            "summary": {
                "total_attempts": total,
                "completed": completed,
                "pending_payment": pending,
                "failed": failed,
                "conversion_rate_pct": conversion_rate,
                "total_fiat_initiated": round(total_fiat, 2),
                "total_fiat_completed": round(completed_fiat, 2),
                "total_seamount_fees": round(total_fees, 2),
            },
            "by_status":   status_counts,
            "by_provider": provider_counts,
            "by_currency": currency_counts,
            "stuck_payments": stuck,
            "stuck_count": len(stuck),
            "recent": recent,
        }

    except Exception as e:
        logger.error(f"[Admin] Onramp summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BLOCKCHAIN TRANSACTIONS  (blockchain_transactions — 5 rows, real data)
# ============================================================================

@router.get("/blockchain/summary")
async def get_blockchain_summary(
    days: int = Query(30, ge=1, le=365),
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """
    Blockchain transaction feed + chain/asset breakdown.
    Queries: blockchain_transactions
    (transaction_type, status, amount, asset, chain, txn_hash, platform_fee)
    """
    try:
        time_filter = (datetime.utcnow() - timedelta(days=days)).isoformat()

        res = db.supabase.table("blockchain_transactions") \
            .select(
                "id,user_id,transaction_type,status,amount,asset,chain,"
                "txn_hash,to_address,network_fee,platform_fee,created_at"
            ) \
            .gte("created_at", time_filter) \
            .order("created_at", desc=True) \
            .execute()

        rows = res.data or []

        chain_vol: dict  = {}
        asset_vol: dict  = {}
        status_counts: dict = {}
        total_volume = 0.0
        total_platform_fees = 0.0

        for r in rows:
            chain  = r.get("chain", "unknown")
            asset  = r.get("asset", "unknown")
            status = r.get("status", "unknown")
            amt    = float(r.get("amount") or 0)
            pfee   = float(r.get("platform_fee") or 0)

            chain_vol[chain]   = chain_vol.get(chain, 0) + amt
            asset_vol[asset]   = asset_vol.get(asset, 0) + amt
            status_counts[status] = status_counts.get(status, 0) + 1
            total_volume       += amt
            total_platform_fees += pfee

        # Enrich with user email
        enriched = []
        for r in rows[:20]:
            profile = db.supabase.table("user_profiles") \
                .select("email") \
                .eq("user_id", r["user_id"]) \
                .limit(1).execute()
            email = profile.data[0]["email"] if profile.data else "unknown"
            enriched.append({
                "id": r["id"],
                "user_email": email,
                "transaction_type": r.get("transaction_type"),
                "status": r.get("status"),
                "amount": float(r.get("amount") or 0),
                "asset": r.get("asset"),
                "chain": r.get("chain"),
                "txn_hash": r.get("txn_hash"),
                "to_address": r.get("to_address"),
                "platform_fee": float(r.get("platform_fee") or 0),
                "created_at": r.get("created_at"),
            })

        return {
            "success": True,
            "summary": {
                "total_transactions": len(rows),
                "total_volume": round(total_volume, 6),
                "total_platform_fees": round(total_platform_fees, 6),
                "by_status": status_counts,
                "by_chain": {k: round(v, 6) for k, v in chain_vol.items()},
                "by_asset": {k: round(v, 6) for k, v in asset_vol.items()},
            },
            "recent": enriched,
        }

    except Exception as e:
        logger.error(f"[Admin] Blockchain summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FEE TREASURY  (fees_owed — 6 rows, real data)
# ============================================================================

@router.get("/fees/treasury")
async def get_fee_treasury(
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """
    Fee collection health: collected vs pending vs failed.
    Queries: fees_owed
    (fee_amount, status, chain, asset, collected_tx_id, collected_at)
    """
    try:
        res = db.supabase.table("fees_owed") \
            .select(
                "id,user_id,transaction_id,chain,asset,"
                "fee_amount,status,collected_tx_id,collected_at,created_at"
            ) \
            .order("created_at", desc=True) \
            .execute()

        rows = res.data or []

        by_status: dict = {}
        by_chain:  dict = {}
        collected_total = 0.0
        pending_total   = 0.0
        failed_total    = 0.0

        for r in rows:
            s   = r.get("status", "unknown")
            ch  = r.get("chain", "unknown")
            amt = float(r.get("fee_amount") or 0)

            by_status[s]  = by_status.get(s, 0) + amt
            by_chain[ch]  = by_chain.get(ch, 0) + amt

            if s == "collected":
                collected_total += amt
            elif s == "pending":
                pending_total += amt
            elif s == "failed":
                failed_total += amt

        collection_rate = round(
            collected_total / (collected_total + pending_total + failed_total) * 100, 1
        ) if (collected_total + pending_total + failed_total) > 0 else 0

        return {
            "success": True,
            "summary": {
                "total_records": len(rows),
                "collected": round(collected_total, 6),
                "pending": round(pending_total, 6),
                "failed": round(failed_total, 6),
                "collection_rate_pct": collection_rate,
                "by_status": {k: round(v, 6) for k, v in by_status.items()},
                "by_chain":  {k: round(v, 6) for k, v in by_chain.items()},
            },
            "records": [
                {
                    "id": r["id"],
                    "transaction_id": r.get("transaction_id"),
                    "chain": r.get("chain"),
                    "asset": r.get("asset"),
                    "fee_amount": float(r.get("fee_amount") or 0),
                    "status": r.get("status"),
                    "collected_tx_id": r.get("collected_tx_id"),
                    "collected_at": r.get("collected_at"),
                    "created_at": r.get("created_at"),
                }
                for r in rows
            ],
        }

    except Exception as e:
        logger.error(f"[Admin] Fee treasury error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# USER PIPELINE  (user_profiles — 29 rows, real data)
# ============================================================================

@router.get("/users/pipeline")
async def get_user_pipeline(
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """
    User funnel: signups → KYC → wallet creation → first transaction.
    Queries: user_profiles
    """
    try:
        res = db.supabase.table("user_profiles") \
            .select(
                "user_id,email,first_name,last_name,country_code,"
                "kyc_status,kyc_level,account_type,role,"
                "wallet_creation_complete,onboarding_complete,"
                "cumulative_volume_30d,created_at"
            ) \
            .order("created_at", desc=True) \
            .execute()

        rows = res.data or []

        kyc_breakdown:  dict = {}
        role_breakdown: dict = {}
        acct_breakdown: dict = {}
        wallets_created = 0
        onboarding_done = 0

        for r in rows:
            ks = r.get("kyc_status", "unknown")
            ro = r.get("role", "unknown")
            at = r.get("account_type", "unknown")

            kyc_breakdown[ks]  = kyc_breakdown.get(ks, 0) + 1
            role_breakdown[ro] = role_breakdown.get(ro, 0) + 1
            acct_breakdown[at] = acct_breakdown.get(at, 0) + 1

            if r.get("wallet_creation_complete"):
                wallets_created += 1
            if r.get("onboarding_complete"):
                onboarding_done += 1

        total = len(rows)

        # Recent 10 signups
        recent = [
            {
                "user_id": r["user_id"],
                "email": r.get("email"),
                "name": f"{r.get('first_name', '')} {r.get('last_name', '')}".strip(),
                "country": r.get("country_code"),
                "kyc_status": r.get("kyc_status"),
                "account_type": r.get("account_type"),
                "wallet_ready": r.get("wallet_creation_complete", False),
                "volume_30d": float(r.get("cumulative_volume_30d") or 0),
                "joined": r.get("created_at"),
            }
            for r in rows[:10]
        ]

        return {
            "success": True,
            "summary": {
                "total_users": total,
                "onboarding_complete": onboarding_done,
                "wallets_created": wallets_created,
                "wallets_pending": total - wallets_created,
                "by_kyc_status": kyc_breakdown,
                "by_role": role_breakdown,
                "by_account_type": acct_breakdown,
            },
            "recent_signups": recent,
        }

    except Exception as e:
        logger.error(f"[Admin] User pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# P2P COMMAND CENTER  (p2p_merchants, p2p_listings, p2p_orders)
# ============================================================================

@router.get("/p2p/overview")
async def get_p2p_overview(
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """
    P2P health: merchants by status, live listings, order pipeline.
    Queries: p2p_merchants, p2p_listings, p2p_orders
    """
    try:
        # Merchants
        merchants_res = db.supabase.table("p2p_merchants") \
            .select("id,user_id,display_name,verified,status,is_online,"
                    "total_orders,completion_rate,created_at") \
            .order("created_at", desc=True) \
            .execute()
        merchants = merchants_res.data or []

        merchant_status: dict = {}
        for m in merchants:
            s = m.get("status", "unknown")
            merchant_status[s] = merchant_status.get(s, 0) + 1

        # Pending approvals — enriched with user email
        pending_merchants = []
        for m in merchants:
            if m.get("status") == "pending":
                profile = db.supabase.table("user_profiles") \
                    .select("email") \
                    .eq("user_id", m["user_id"]) \
                    .limit(1).execute()
                email = profile.data[0]["email"] if profile.data else "unknown"
                pending_merchants.append({
                    "id": m["id"],
                    "display_name": m.get("display_name"),
                    "user_email": email,
                    "created_at": m.get("created_at"),
                })

        # Listings
        listings_res = db.supabase.table("p2p_listings") \
            .select("id,token,fiat_currency,price_per_token,"
                    "available_amount,is_active,created_at") \
            .execute()
        listings = listings_res.data or []
        active_listings   = sum(1 for l in listings if l.get("is_active"))
        inactive_listings = len(listings) - active_listings

        # Orders
        orders_res = db.supabase.table("p2p_orders") \
            .select("id,status,token,fiat_amount,token_amount,created_at") \
            .order("created_at", desc=True) \
            .execute()
        orders = orders_res.data or []

        order_status: dict = {}
        total_p2p_volume = 0.0
        for o in orders:
            s = o.get("status", "unknown")
            order_status[s] = order_status.get(s, 0) + 1
            if s == "completed":
                total_p2p_volume += float(o.get("token_amount") or 0)

        return {
            "success": True,
            "merchants": {
                "total": len(merchants),
                "by_status": merchant_status,
                "pending_approval": pending_merchants,
                "all": [
                    {
                        "id": m["id"],
                        "display_name": m.get("display_name"),
                        "status": m.get("status"),
                        "verified": m.get("verified"),
                        "is_online": m.get("is_online"),
                        "total_orders": m.get("total_orders"),
                        "completion_rate": float(m.get("completion_rate") or 0),
                        "created_at": m.get("created_at"),
                    }
                    for m in merchants
                ],
            },
            "listings": {
                "total": len(listings),
                "active": active_listings,
                "inactive": inactive_listings,
            },
            "orders": {
                "total": len(orders),
                "by_status": order_status,
                "total_volume": round(total_p2p_volume, 6),
                "recent": orders[:10],
            },
        }

    except Exception as e:
        logger.error(f"[Admin] P2P overview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MERCHANT APPROVE / REJECT  (already defined above, included for reference)
# This is the endpoint from the merchant approval section.
# If you already added it, skip this block.
# ============================================================================

class MerchantReviewRequest(BaseModel):
    action: str        # 'approved' or 'rejected'
    note: Optional[str] = None

from pydantic import BaseModel
from typing import Optional

@router.patch("/p2p/merchants/{merchant_id}/review")
async def admin_review_merchant(
    merchant_id: str,
    payload: MerchantReviewRequest,
    admin: dict = Depends(require_admin),
    db: DatabaseService = Depends(get_db_service)
):
    """Admin approves or rejects a P2P merchant application."""
    try:
        if payload.action not in ("approved", "rejected"):
            raise HTTPException(status_code=400, detail="action must be 'approved' or 'rejected'")

        db.supabase.table("p2p_merchants").update({
            "status": payload.action,
            "verified": payload.action == "approved",
            "is_online": payload.action == "approved",
        }).eq("id", merchant_id).execute()

        # Log review
        db.supabase.table("p2p_merchant_reviews").insert({
            "merchant_id": merchant_id,
            "admin_id": admin["id"],
            "action": payload.action,
            "note": payload.note,
        }).execute()

        logger.info(f"[Admin] Merchant {merchant_id} {payload.action} by {admin.get('email')}")
        return {"success": True, "action": payload.action}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin] Merchant review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))