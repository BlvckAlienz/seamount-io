# File Location: backend/services/database_service.py
# CRITICAL: Super-powered database service combining Supabase client with async PostgreSQL pooling
# Best of both worlds: Supabase auth integration + raw PostgreSQL performance

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from decimal import Decimal
from contextlib import asynccontextmanager

import asyncpg
from supabase import create_client, Client
from postgrest import APIError
from fastapi import HTTPException

from backend.config import settings

logger = logging.getLogger(__name__)

class SuperDatabaseService:
    """
    The ultimate database service combining:
    - Supabase client for auth integration and convenience
    - Raw asyncpg pool for high-performance operations
    - Bulletproof retry logic and connection management
    - Self-healing mechanisms and circuit breakers
    """
    
    def __init__(self):
        # Supabase client for auth and convenience operations
        if not settings.VITE_SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise ValueError("Supabase URL and Service Key must be configured")
        
        self.supabase: Client = create_client(
            settings.VITE_SUPABASE_URL, 
            settings.SUPABASE_SERVICE_KEY
        )
        
        # AsyncPG pool for high-performance operations
        self.pool: Optional[asyncpg.Pool] = None
        self.max_retries = 3
        self.retry_delay = 1.0
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        
        logger.info("SuperDatabaseService initialized with dual-client architecture")
    
    async def initialize_pool(self):
        """Initialize high-performance PostgreSQL connection pool"""
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Extract PostgreSQL URL from Supabase settings
                db_url = settings.DATABASE_URL or self._build_postgres_url()
                
                self.pool = await asyncpg.create_pool(
                    db_url,
                    min_size=2,
                    max_size=20,
                    max_queries=50000,
                    max_inactive_connection_lifetime=300,
                    timeout=30,
                    command_timeout=60,
                    server_settings={
                        'application_name': 'seamount_backend',
                        'tcp_keepalives_idle': '600',
                        'tcp_keepalives_interval': '30',
                        'tcp_keepalives_count': '3'
                    }
                )
                
                self.circuit_breaker_failures = 0
                logger.info("High-performance database pool initialized successfully")
                return
                
            except Exception as e:
                attempt += 1
                self.circuit_breaker_failures += 1
                logger.error(f"Database pool initialization attempt {attempt} failed: {str(e)}")
                
                if attempt >= max_attempts:
                    raise Exception(f"Failed to initialize database pool after {max_attempts} attempts")
                
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    def _build_postgres_url(self) -> str:
        """Build PostgreSQL URL from Supabase settings"""
        # Extract database details from Supabase URL
        import re
        from urllib.parse import urlparse
        
        supabase_url = settings.VITE_SUPABASE_URL
        if not supabase_url.startswith('https://'):
            raise ValueError("Invalid Supabase URL format")
        
        # Parse project ID from Supabase URL
        parsed = urlparse(supabase_url)
        project_id = parsed.hostname.split('.')[0]
        
        return f"postgresql://postgres:{settings.SUPABASE_SERVICE_KEY}@db.{project_id}.supabase.co:5432/postgres"
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection with circuit breaker and retry logic"""
        if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
            raise Exception("Circuit breaker OPEN - database temporarily unavailable")
        
        if not self.pool:
            await self.initialize_pool()
        
        connection = None
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                connection = await self.pool.acquire(timeout=30)
                yield connection
                self.circuit_breaker_failures = max(0, self.circuit_breaker_failures - 1)
                return
                
            except (asyncpg.ConnectionDoesNotExistError, asyncpg.InterfaceError) as e:
                retry_count += 1
                self.circuit_breaker_failures += 1
                logger.warning(f"Connection attempt {retry_count} failed: {str(e)}")
                
                if retry_count >= self.max_retries:
                    raise Exception(f"Database connection failed after {self.max_retries} attempts")
                
                await asyncio.sleep(self.retry_delay * retry_count)
                
            except Exception as e:
                self.circuit_breaker_failures += 1
                logger.error(f"Unexpected database error: {str(e)}")
                raise
                
            finally:
                if connection:
                    try:
                        await self.pool.release(connection)
                    except Exception as e:
                        logger.error(f"Error releasing connection: {str(e)}")
    
    def _handle_supabase_error(self, error: APIError, context: str):
        """Centralized Supabase error handler"""
        self.circuit_breaker_failures += 1
        logger.error(f"Supabase error during {context}: {error.message}")
        raise HTTPException(status_code=500, detail=f"Database error: {context}")
    
    async def execute_with_retry(self, query: str, *args, use_pool: bool = True) -> Any:
        """Execute query with automatic retry mechanism"""
        if use_pool and self.pool:
            return await self._execute_pool_query(query, *args)
        else:
            return await self._execute_supabase_query(query, *args)
    
    async def _execute_pool_query(self, query: str, *args) -> Any:
        """Execute query using high-performance pool"""
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                async with self.get_connection() as conn:
                    result = await conn.fetch(query, *args)
                    return result
                    
            except (asyncpg.ConnectionDoesNotExistError, asyncpg.InterfaceError) as e:
                retry_count += 1
                logger.warning(f"Pool query attempt {retry_count} failed: {str(e)}")
                
                if retry_count >= self.max_retries:
                    raise Exception(f"Query execution failed after {self.max_retries} attempts")
                
                await asyncio.sleep(self.retry_delay * retry_count)
                
            except Exception as e:
                logger.error(f"Database query error: {str(e)}")
                raise
    
    async def _execute_supabase_query(self, query: str, *args) -> Any:
        """Fallback to Supabase client for complex operations"""
        # This is for operations that need Supabase's auth integration
        # Implementation depends on specific query type
        pass
    
    # =============================================================================
    # User & Profile Management (High Performance)
    # =============================================================================
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        CRITICAL: Fetch user profile with maximum performance and resilience
        """
        try:
            query = """
                SELECT 
                    id, first_name, last_name, email, phone, 
                    kyc_status, kyc_level, kyc_started_at, kyc_completed_at, 
                    kyc_rejection_reason, kyc_session_id, kyc_provider,
                    security_flags, last_login_at, failed_login_attempts,
                    account_locked_until, created_at, updated_at
                FROM user_profiles 
                WHERE id = $1
            """
            
            result = await self.execute_with_retry(query, user_id)
            
            if result:
                row = result[0]
                return {
                    "id": str(row["id"]),
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "email": row["email"],
                    "phone": row["phone"],
                    "kyc_status": row["kyc_status"],
                    "kyc_level": row["kyc_level"],
                    "kyc_started_at": row["kyc_started_at"].isoformat() if row["kyc_started_at"] else None,
                    "kyc_completed_at": row["kyc_completed_at"].isoformat() if row["kyc_completed_at"] else None,
                    "kyc_rejection_reason": row["kyc_rejection_reason"],
                    "kyc_session_id": row["kyc_session_id"],
                    "kyc_provider": row["kyc_provider"],
                    "security_flags": row["security_flags"] or {},
                    "last_login_at": row["last_login_at"].isoformat() if row["last_login_at"] else None,
                    "failed_login_attempts": row["failed_login_attempts"] or 0,
                    "account_locked_until": row["account_locked_until"].isoformat() if row["account_locked_until"] else None,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching user profile {user_id}: {str(e)}")
            raise
    
    async def get_user_profile_by_algorand_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Get user profile by Algorand wallet address"""
        try:
            query = """
                SELECT up.id, up.first_name, up.last_name, up.email, up.phone,
                       up.kyc_status, up.kyc_level, up.created_at, up.updated_at,
                       uw.algorand_address
                FROM user_profiles up
                JOIN user_wallets uw ON up.id = uw.user_id
                WHERE uw.algorand_address = $1
            """
            
            result = await self.execute_with_retry(query, address)
            
            if result:
                row = result[0]
                return {
                    "id": str(row["id"]),
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "email": row["email"],
                    "phone": row["phone"],
                    "kyc_status": row["kyc_status"],
                    "kyc_level": row["kyc_level"],
                    "algorand_address": row["algorand_address"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching user by address {address}: {str(e)}")
            raise
    
    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        CRITICAL: Update user profile with transaction safety and performance
        """
        try:
            # Build dynamic update query
            update_fields = []
            values = []
            param_count = 1
            
            allowed_fields = [
                "first_name", "last_name", "email", "phone", 
                "kyc_status", "kyc_level", "kyc_session_id", "kyc_provider",
                "security_flags", "last_login_at", "failed_login_attempts",
                "account_locked_until"
            ]
            
            for field, value in profile_data.items():
                if field in allowed_fields:
                    update_fields.append(f"{field} = ${param_count}")
                    values.append(value)
                    param_count += 1
            
            if not update_fields:
                raise ValueError("No valid fields to update")
            
            # Add updated_at field
            update_fields.append(f"updated_at = ${param_count}")
            values.append(datetime.utcnow())
            values.append(user_id)  # For WHERE clause
            
            query = f"""
                UPDATE user_profiles 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count + 1}
                RETURNING 
                    id, first_name, last_name, email, phone,
                    kyc_status, kyc_level, kyc_started_at, kyc_completed_at,
                    kyc_rejection_reason, kyc_session_id, kyc_provider,
                    security_flags, created_at, updated_at
            """
            
            async with self.get_connection() as conn:
                async with conn.transaction():
                    result = await conn.fetch(query, *values)
                    
                    if result:
                        row = result[0]
                        return {
                            "id": str(row["id"]),
                            "first_name": row["first_name"],
                            "last_name": row["last_name"],
                            "email": row["email"],
                            "phone": row["phone"],
                            "kyc_status": row["kyc_status"],
                            "kyc_level": row["kyc_level"],
                            "kyc_started_at": row["kyc_started_at"].isoformat() if row["kyc_started_at"] else None,
                            "kyc_completed_at": row["kyc_completed_at"].isoformat() if row["kyc_completed_at"] else None,
                            "kyc_rejection_reason": row["kyc_rejection_reason"],
                            "kyc_session_id": row["kyc_session_id"],
                            "kyc_provider": row["kyc_provider"],
                            "security_flags": row["security_flags"] or {},
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                        }
                    
                    return None
            
        except Exception as e:
            logger.error(f"Error updating user profile {user_id}: {str(e)}")
            raise
    
    # =============================================================================
    # Secure Wallet Management
    # =============================================================================
    
    async def save_encrypted_private_key(self, user_id: str, algorand_address: str, encrypted_pk: str) -> bool:
        """Save user's encrypted private key with maximum security"""
        try:
            query = """
                INSERT INTO user_wallets (user_id, algorand_address, algorand_private_key)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    algorand_address = EXCLUDED.algorand_address,
                    algorand_private_key = EXCLUDED.algorand_private_key,
                    updated_at = NOW()
            """
            
            async with self.get_connection() as conn:
                await conn.execute(query, user_id, algorand_address, encrypted_pk)
                return True
            
        except Exception as e:
            logger.error(f"Error saving encrypted key for {user_id}: {str(e)}")
            raise
    
    async def get_encrypted_private_key(self, user_id: str) -> Optional[str]:
        """Retrieve user's encrypted private key"""
        try:
            query = """
                SELECT algorand_private_key 
                FROM user_wallets 
                WHERE user_id = $1 AND is_active = true
            """
            
            result = await self.execute_with_retry(query, user_id)
            
            if result:
                return result[0]["algorand_private_key"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving encrypted key for {user_id}: {str(e)}")
            raise
    
    async def get_user_wallet(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete wallet information for user"""
        try:
            query = """
                SELECT id, user_id, algorand_address, wallet_type, 
                       is_active, created_at, updated_at
                FROM user_wallets 
                WHERE user_id = $1 AND is_active = true
            """
            
            result = await self.execute_with_retry(query, user_id)
            
            if result:
                row = result[0]
                return {
                    "id": str(row["id"]),
                    "user_id": str(row["user_id"]),
                    "algorand_address": row["algorand_address"],
                    "wallet_type": row["wallet_type"],
                    "is_active": row["is_active"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Error fetching user wallet {user_id}: {str(e)}")
            raise
    
    # =============================================================================
    # Transaction Management (Ultra High Performance)
    # =============================================================================
    
    async def create_transaction_record(self, transaction_data: Dict[str, Any]) -> str:
        """
        CRITICAL: Create transaction record with ACID compliance and performance
        """
        try:
            query = """
                INSERT INTO transactions (
                    user_id, transaction_type, amount, currency, 
                    algorand_txn_id, from_address, to_address,
                    status, fee, metadata, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id, created_at
            """
            
            values = [
                transaction_data.get("user_id"),
                transaction_data.get("transaction_type"),
                Decimal(str(transaction_data.get("amount", 0))),
                transaction_data.get("currency", "USDS"),
                transaction_data.get("algorand_txn_id"),
                transaction_data.get("from_address"),
                transaction_data.get("to_address"),
                transaction_data.get("status", "pending"),
                Decimal(str(transaction_data.get("fee", 0))),
                json.dumps(transaction_data.get("metadata", {})),
                datetime.utcnow()
            ]
            
            async with self.get_connection() as conn:
                result = await conn.fetchrow(query, *values)
                return str(result["id"])
            
        except Exception as e:
            logger.error(f"Error creating transaction record: {str(e)}")
            raise
    
    async def update_transaction_status(self, txn_id: str, status: str, metadata: Dict[str, Any] = None) -> bool:
        """Update transaction status with metadata"""
        try:
            query = """
                UPDATE transactions 
                SET status = $2, metadata = $3, updated_at = $4
                WHERE id = $1
            """
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            async with self.get_connection() as conn:
                result = await conn.execute(query, txn_id, status, metadata_json, datetime.utcnow())
                return result == "UPDATE 1"
            
        except Exception as e:
            logger.error(f"Error updating transaction {txn_id}: {str(e)}")
            raise
    
    async def get_user_transactions(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get paginated user transactions with performance optimization"""
        try:
            query = """
                SELECT 
                    id, transaction_type, amount, currency, algorand_txn_id,
                    from_address, to_address, status, fee, metadata,
                    created_at, updated_at
                FROM transactions 
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            
            result = await self.execute_with_retry(query, user_id, limit, offset)
            
            transactions = []
            for row in result:
                transactions.append({
                    "id": str(row["id"]),
                    "transaction_type": row["transaction_type"],
                    "amount": float(row["amount"]),
                    "currency": row["currency"],
                    "algorand_txn_id": row["algorand_txn_id"],
                    "from_address": row["from_address"],
                    "to_address": row["to_address"],
                    "status": row["status"],
                    "fee": float(row["fee"]) if row["fee"] else 0,
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                })
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error fetching transactions for user {user_id}: {str(e)}")
            raise
    
    # =============================================================================
    # KYC & Compliance Management
    # =============================================================================
    
    async def update_kyc_session(self, user_id: str, kyc_data: Dict[str, Any]) -> bool:
        """Update KYC session with compliance tracking"""
        try:
            query = """
                UPDATE user_profiles 
                SET 
                    kyc_status = $2,
                    kyc_level = $3,
                    kyc_session_id = $4,
                    kyc_provider = $5,
                    kyc_started_at = COALESCE(kyc_started_at, $6),
                    kyc_completed_at = $7,
                    kyc_rejection_reason = $8,
                    updated_at = $9
                WHERE id = $1
            """
            
            values = [
                user_id,
                kyc_data.get("status"),
                kyc_data.get("level"),
                kyc_data.get("session_id"),
                kyc_data.get("provider", "complycube"),
                datetime.utcnow() if kyc_data.get("status") == "started" else None,
                datetime.utcnow() if kyc_data.get("status") == "completed" else None,
                kyc_data.get("rejection_reason"),
                datetime.utcnow()
            ]
            
            async with self.get_connection() as conn:
                result = await conn.execute(query, *values)
                return result == "UPDATE 1"
            
        except Exception as e:
            logger.error(f"Error updating KYC for user {user_id}: {str(e)}")
            raise
    
    async def get_pending_kyc_reviews(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get pending KYC reviews for admin dashboard"""
        try:
            query = """
                SELECT 
                    id, first_name, last_name, email, kyc_status,
                    kyc_session_id, kyc_provider, kyc_started_at,
                    created_at
                FROM user_profiles 
                WHERE kyc_status IN ('pending', 'review_required', 'submitted')
                ORDER BY kyc_started_at ASC
                LIMIT $1
            """
            
            result = await self.execute_with_retry(query, limit)
            
            reviews = []
            for row in result:
                reviews.append({
                    "user_id": str(row["id"]),
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "email": row["email"],
                    "kyc_status": row["kyc_status"],
                    "kyc_session_id": row["kyc_session_id"],
                    "kyc_provider": row["kyc_provider"],
                    "kyc_started_at": row["kyc_started_at"].isoformat() if row["kyc_started_at"] else None,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None
                })
            
            return reviews
            
        except Exception as e:
            logger.error(f"Error fetching pending KYC reviews: {str(e)}")
            raise
    
    # =============================================================================
    # Portfolio & Investment Management
    # =============================================================================
    
    async def get_user_portfolio(self, user_id: str) -> Dict[str, Any]:
        """
        CRITICAL: Get comprehensive user portfolio with real-time calculations
        """
        try:
            # Get wallet balances
            balance_query = """
                SELECT 
                    asset_id, asset_name, balance, last_updated
                FROM user_balances 
                WHERE user_id = $1 AND balance > 0
                ORDER BY balance DESC
            """
            
            # Get transaction history for PnL calculation
            pnl_query = """
                SELECT 
                    transaction_type, amount, currency, fee, created_at
                FROM transactions 
                WHERE user_id = $1 AND status = 'confirmed'
                ORDER BY created_at DESC
                LIMIT 1000
            """
            
            async with self.get_connection() as conn:
                # Execute both queries concurrently
                balance_result, pnl_result = await asyncio.gather(
                    conn.fetch(balance_query, user_id),
                    conn.fetch(pnl_query, user_id)
                )
                
                # Process balances
                balances = []
                total_value = Decimal('0')
                
                for row in balance_result:
                    balance_value = Decimal(str(row["balance"]))
                    balances.append({
                        "asset_id": str(row["asset_id"]),
                        "asset_name": row["asset_name"],
                        "balance": float(balance_value),
                        "last_updated": row["last_updated"].isoformat() if row["last_updated"] else None
                    })
                    total_value += balance_value
                
                # Calculate basic PnL metrics
                total_deposits = Decimal('0')
                total_withdrawals = Decimal('0')
                total_fees = Decimal('0')
                
                for row in pnl_result:
                    amount = Decimal(str(row["amount"]))
                    fee = Decimal(str(row["fee"])) if row["fee"] else Decimal('0')
                    
                    if row["transaction_type"] in ["deposit", "buy"]:
                        total_deposits += amount
                    elif row["transaction_type"] in ["withdrawal", "sell"]:
                        total_withdrawals += amount
                    
                    total_fees += fee
                
                return {
                    "user_id": user_id,
                    "total_value": float(total_value),
                    "balances": balances,
                    "pnl_metrics": {
                        "total_deposits": float(total_deposits),
                        "total_withdrawals": float(total_withdrawals),
                        "total_fees": float(total_fees),
                        "unrealized_pnl": float(total_value - total_deposits + total_withdrawals)
                    },
                    "last_updated": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error fetching portfolio for user {user_id}: {str(e)}")
            raise
    
    async def update_user_balance(self, user_id: str, asset_id: str, balance: Decimal) -> bool:
        """Update user balance with atomic operation"""
        try:
            query = """
                INSERT INTO user_balances (user_id, asset_id, balance, last_updated)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, asset_id)
                DO UPDATE SET 
                    balance = EXCLUDED.balance,
                    last_updated = EXCLUDED.last_updated
            """
            
            async with self.get_connection() as conn:
                await conn.execute(query, user_id, asset_id, balance, datetime.utcnow())
                return True
            
        except Exception as e:
            logger.error(f"Error updating balance for user {user_id}: {str(e)}")
            raise
    
    # =============================================================================
    # Analytics & Reporting
    # =============================================================================
    
    async def get_platform_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        CRITICAL: Get comprehensive platform metrics for dashboard
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            metrics_query = """
                WITH user_metrics AS (
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(CASE WHEN created_at >= $1 THEN 1 END) as new_users,
                        COUNT(CASE WHEN kyc_status = 'completed' THEN 1 END) as verified_users
                    FROM user_profiles
                ),
                transaction_metrics AS (
                    SELECT 
                        COUNT(*) as total_transactions,
                        COUNT(CASE WHEN created_at >= $1 THEN 1 END) as recent_transactions,
                        SUM(CASE WHEN created_at >= $1 THEN amount ELSE 0 END) as recent_volume,
                        SUM(CASE WHEN created_at >= $1 THEN fee ELSE 0 END) as recent_fees
                    FROM transactions
                    WHERE status = 'confirmed'
                ),
                balance_metrics AS (
                    SELECT 
                        SUM(balance) as total_tvl,
                        COUNT(DISTINCT user_id) as active_holders
                    FROM user_balances
                    WHERE balance > 0
                )
                SELECT * FROM user_metrics, transaction_metrics, balance_metrics
            """
            
            result = await self.execute_with_retry(metrics_query, cutoff_date)
            
            if result:
                row = result[0]
                return {
                    "period_days": days,
                    "user_metrics": {
                        "total_users": row["total_users"],
                        "new_users": row["new_users"],
                        "verified_users": row["verified_users"],
                        "verification_rate": (row["verified_users"] / max(row["total_users"], 1)) * 100
                    },
                    "transaction_metrics": {
                        "total_transactions": row["total_transactions"],
                        "recent_transactions": row["recent_transactions"],
                        "recent_volume": float(row["recent_volume"]) if row["recent_volume"] else 0,
                        "recent_fees": float(row["recent_fees"]) if row["recent_fees"] else 0
                    },
                    "balance_metrics": {
                        "total_tvl": float(row["total_tvl"]) if row["total_tvl"] else 0,
                        "active_holders": row["active_holders"]
                    },
                    "generated_at": datetime.utcnow().isoformat()
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching platform metrics: {str(e)}")
            raise
    
    # =============================================================================
    # Admin & Monitoring Functions
    # =============================================================================
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health metrics"""
        try:
            health_data = {
                "database": {
                    "pool_status": "healthy" if self.pool and not self.pool._closed else "degraded",
                    "circuit_breaker_failures": self.circuit_breaker_failures,
                    "circuit_breaker_status": "closed" if self.circuit_breaker_failures < self.circuit_breaker_threshold else "open"
                },
                "supabase": {
                    "client_status": "healthy" if self.supabase else "unavailable"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Test database connectivity
            try:
                test_query = "SELECT 1 as health_check"
                await self.execute_with_retry(test_query)
                health_data["database"]["connectivity"] = "healthy"
            except Exception:
                health_data["database"]["connectivity"] = "failed"
            
            return health_data
            
        except Exception as e:
            logger.error(f"Error checking system health: {str(e)}")
            return {
                "database": {"status": "error", "error": str(e)},
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def cleanup_old_records(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Cleanup old records with configurable retention"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            cleanup_queries = [
                ("DELETE FROM audit_logs WHERE created_at < $1", "audit_logs"),
                ("DELETE FROM sessions WHERE expires_at < $1 AND expires_at < NOW()", "sessions"),
                ("UPDATE user_profiles SET security_flags = '{}' WHERE last_login_at < $1", "security_flags")
            ]
            
            cleanup_results = {}
            
            async with self.get_connection() as conn:
                async with conn.transaction():
                    for query, table_name in cleanup_queries:
                        try:
                            result = await conn.execute(query, cutoff_date)
                            # Extract number of affected rows from result string
                            affected = int(result.split()[-1]) if result.split()[-1].isdigit() else 0
                            cleanup_results[table_name] = affected
                        except Exception as e:
                            logger.warning(f"Cleanup failed for {table_name}: {str(e)}")
                            cleanup_results[table_name] = 0
            
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise
    
    async def close_connections(self):
        """Gracefully close all database connections"""
        try:
            if self.pool and not self.pool._closed:
                await self.pool.close()
                logger.info("Database pool closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")

# Initialize global database service instance
database_service = SuperDatabaseService()