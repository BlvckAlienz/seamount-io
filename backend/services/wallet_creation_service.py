# File: backend/services/wallet_creation_service.py
# 🎯 BULLETPROOF MULTI-CHAIN WALLET CREATION WITH RETRY SYSTEM

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import WalletCreationStatus, WalletCreationQueue, UserProfile
from backend.services.algorand_service import AlgorandService
from backend.services.wdk_client import WDKClient
from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class WalletCreationService:
    """
    Bulletproof multi-chain wallet creation service with:
    - Per-chain status tracking
    - Automatic retry with exponential backoff
    - Background job queue for failed wallets
    - Circuit breaker awareness
    - User-facing retry API
    """
    
    SUPPORTED_CHAINS = ['algorand', 'bitcoin', 'ethereum', 'polygon']
    MAX_CONCURRENT_RETRIES = 3
    RETRY_INTERVALS = [30, 300, 900, 3600, 7200]  # 30s, 5m, 15m, 1h, 2h
    
    def __init__(
        self,
        db_service: DatabaseService,
        algorand_service: AlgorandService,
        wdk_client: WDKClient
    ):
        self.db = db_service
        self.algorand_service = algorand_service
        self.wdk_client = wdk_client
        logger.info("✅ WalletCreationService initialized")
    
    async def create_all_wallets(
        self,
        user_id: str,
        background: bool = False
    ) -> Dict[str, any]:
        """
        Create wallets for all 4 chains with robust error handling.
        
        Args:
            user_id: User UUID
            background: If True, queue failures for background retry
        
        Returns:
            Dict with success status and per-chain results
        """
        logger.info(f"🚀 Starting wallet creation for user {user_id}")
        
        # Initialize status tracking
        await self._initialize_wallet_status(user_id)
        
        results = {
            'user_id': user_id,
            'overall_success': False,
            'chains': {},
            'failures': [],
            'queued_for_retry': []
        }
        
        # Create wallets for each chain
        for chain in self.SUPPORTED_CHAINS:
            try:
                result = await self._create_wallet_for_chain(user_id, chain)
                results['chains'][chain] = result
                
                if not result['success'] and background:
                    # Queue for background retry
                    await self._queue_for_retry(user_id, chain, result.get('error'))
                    results['queued_for_retry'].append(chain)
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error creating {chain} wallet: {e}")
                results['chains'][chain] = {
                    'success': False,
                    'error': str(e),
                    'chain': chain
                }
                results['failures'].append(chain)
        
        # Check overall success
        successful_chains = [
            chain for chain, result in results['chains'].items() 
            if result.get('success')
        ]
        results['overall_success'] = len(successful_chains) == 4
        results['successful_count'] = len(successful_chains)
        results['failed_count'] = 4 - len(successful_chains)
        
        logger.info(
            f"✅ Wallet creation completed for {user_id}: "
            f"{results['successful_count']}/4 successful"
        )
        
        return results
    
    async def _create_wallet_for_chain(
        self,
        user_id: str,
        chain: str
    ) -> Dict[str, any]:
        """Create wallet for specific chain with status tracking."""
        
        # Update status to 'creating'
        await self._update_status(user_id, chain, 'creating')
        
        try:
            if chain == 'algorand':
                # Algorand wallet creation (always works)
                wallet = await self.algorand_service.create_wallet()
                address = wallet['address']
                encrypted_key = wallet.get('encrypted_private_key')
                
            else:
                # WDK wallet creation (can fail)
                wallet = await self._create_wdk_wallet(user_id, chain)
                if not wallet or not wallet.get('success'):
                    raise Exception(wallet.get('error', 'WDK wallet creation failed'))
                
                address = wallet['address']
                encrypted_key = wallet.get('encrypted_key')
            
            # Store wallet in database
            await self._store_wallet(user_id, chain, address, encrypted_key)
            
            # Update status to 'success'
            await self._update_status(
                user_id, chain, 'success',
                address=address,
                encrypted_key=encrypted_key
            )
            
            logger.info(f"✅ {chain.upper()} wallet created: {address[:12]}...")
            
            return {
                'success': True,
                'chain': chain,
                'address': address,
                'encrypted_key': encrypted_key
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ {chain.upper()} wallet creation failed: {error_msg}")
            
            # Update status to 'failed'
            await self._update_status(
                user_id, chain, 'failed',
                error_message=error_msg
            )
            
            return {
                'success': False,
                'chain': chain,
                'error': error_msg
            }
    
    async def _create_wdk_wallet(
        self,
        user_id: str,
        chain: str,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """
        Create WDK wallet with immediate retries.
        Uses circuit breaker bypass for critical wallet creation.
        """
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🔄 WDK {chain} wallet creation attempt {attempt}/{max_retries}")
                
                # Try to create wallet (circuit breaker aware)
                wallet = await self.wdk_client.create_wallet(chain)
                
                if wallet and wallet.get('success'):
                    return wallet
                
                # If circuit breaker open, wait and retry
                if self.wdk_client.circuit_breaker.is_open:
                    wait_time = min(2 ** attempt, 10)  # Max 10 seconds
                    logger.warning(
                        f"⚠️ Circuit breaker open, waiting {wait_time}s before retry"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                
            except Exception as e:
                logger.error(f"❌ WDK wallet creation attempt {attempt} failed: {e}")
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': 'Max retries exceeded'}
    
    async def retry_failed_wallets(
        self,
        user_id: str,
        chains: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        Manually retry failed wallet creations.
        Called from API endpoint by user.
        """
        logger.info(f"🔄 Manual retry requested by user {user_id}")
        
        # Get failed chains if not specified
        if not chains:
            chains = await self._get_failed_chains(user_id)
        
        if not chains:
            return {
                'success': True,
                'message': 'All wallets already created',
                'retried_chains': []
            }
        
        # Increment retry counter
        await self._increment_retry_count(user_id)
        
        # Retry each failed chain
        results = {
            'user_id': user_id,
            'retried_chains': chains,
            'results': {}
        }
        
        for chain in chains:
            result = await self._create_wallet_for_chain(user_id, chain)
            results['results'][chain] = result
        
        # Check if all succeeded
        all_succeeded = all(
            result.get('success') for result in results['results'].values()
        )
        
        results['success'] = all_succeeded
        results['message'] = (
            "All wallets created successfully!" if all_succeeded
            else f"Retry completed. {len([r for r in results['results'].values() if r.get('success')])} succeeded."
        )
        
        return results
    
    async def get_wallet_status(self, user_id: str) -> Dict[str, any]:
        """Get comprehensive wallet creation status for user."""
        
        async with self.db.get_session() as session:
            # Get wallet creation status for all chains
            result = await session.execute(
                select(WalletCreationStatus).where(
                    WalletCreationStatus.user_id == user_id
                )
            )
            statuses = result.scalars().all()
            
            # Get user profile
            profile_result = await session.execute(
                select(UserProfile).where(UserProfile.id == user_id)
            )
            profile = profile_result.scalar_one_or_none()
            
            status_dict = {
                'user_id': user_id,
                'overall_complete': profile.wallet_creation_complete if profile else False,
                'started_at': profile.wallet_creation_started_at.isoformat() if profile and profile.wallet_creation_started_at else None,
                'completed_at': profile.wallet_creation_completed_at.isoformat() if profile and profile.wallet_creation_completed_at else None,
                'retry_count': profile.wallet_creation_retry_count if profile else 0,
                'chains': {}
            }
            
            for status in statuses:
                status_dict['chains'][status.chain] = {
                    'status': status.status,
                    'address': status.address,
                    'attempt_count': status.attempt_count,
                    'last_attempt': status.last_attempt_at.isoformat() if status.last_attempt_at else None,
                    'error': status.error_message
                }
            
            # Add summary
            status_dict['summary'] = {
                'total': 4,
                'successful': sum(1 for s in statuses if s.status == 'success'),
                'failed': sum(1 for s in statuses if s.status == 'failed'),
                'pending': sum(1 for s in statuses if s.status == 'pending'),
                'retrying': sum(1 for s in statuses if s.status == 'retrying')
            }
            
            return status_dict
    
    async def _initialize_wallet_status(self, user_id: str):
        """Initialize status tracking for all chains."""
        async with self.db.get_session() as session:
            for chain in self.SUPPORTED_CHAINS:
                status = WalletCreationStatus(
                    user_id=user_id,
                    chain=chain,
                    status='pending'
                )
                session.add(status)
            
            # Update user profile
            await session.execute(
                update(UserProfile)
                .where(UserProfile.id == user_id)
                .values(wallet_creation_started_at=datetime.utcnow())
            )
            
            await session.commit()
    
    async def _update_status(
        self,
        user_id: str,
        chain: str,
        status: str,
        address: Optional[str] = None,
        encrypted_key: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update wallet creation status."""
        async with self.db.get_session() as session:
            update_values = {
                'status': status,
                'last_attempt_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            if address:
                update_values['address'] = address
            if encrypted_key:
                update_values['encrypted_key'] = encrypted_key
            if error_message:
                update_values['error_message'] = error_message
            
            # Increment attempt count
            stmt = select(WalletCreationStatus).where(
                and_(
                    WalletCreationStatus.user_id == user_id,
                    WalletCreationStatus.chain == chain
                )
            )
            result = await session.execute(stmt)
            current_status = result.scalar_one_or_none()
            
            if current_status:
                update_values['attempt_count'] = current_status.attempt_count + 1
            
            await session.execute(
                update(WalletCreationStatus)
                .where(
                    and_(
                        WalletCreationStatus.user_id == user_id,
                        WalletCreationStatus.chain == chain
                    )
                )
                .values(**update_values)
            )
            
            await session.commit()
    
    async def _store_wallet(
        self,
        user_id: str,
        chain: str,
        address: str,
        encrypted_key: Optional[str]
    ):
        """Store wallet in appropriate database table."""
        # Implementation depends on your database schema
        # This is a placeholder
        logger.info(f"💾 Storing {chain} wallet for user {user_id}")
        pass
    
    async def _queue_for_retry(
        self,
        user_id: str,
        chain: str,
        error: Optional[str]
    ):
        """Add failed wallet to retry queue."""
        async with self.db.get_session() as session:
            queue_item = WalletCreationQueue(
                user_id=user_id,
                chain=chain,
                priority=5,
                scheduled_for=datetime.utcnow() + timedelta(seconds=30),
                error_message=error
            )
            session.add(queue_item)
            await session.commit()
            
        logger.info(f"📋 Queued {chain} wallet retry for user {user_id}")
    
    async def _get_failed_chains(self, user_id: str) -> List[str]:
        """Get list of failed chain wallets."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(WalletCreationStatus.chain).where(
                    and_(
                        WalletCreationStatus.user_id == user_id,
                        WalletCreationStatus.status.in_(['failed', 'pending'])
                    )
                )
            )
            return [row[0] for row in result]
    
    async def _increment_retry_count(self, user_id: str):
        """Increment user's wallet creation retry count."""
        async with self.db.get_session() as session:
            await session.execute(
                update(UserProfile)
                .where(UserProfile.id == user_id)
                .values(
                    wallet_creation_retry_count=UserProfile.wallet_creation_retry_count + 1,
                    wallet_creation_last_retry=datetime.utcnow()
                )
            )
            await session.commit()
    
    # ========================================================================
    # BACKGROUND JOB SYSTEM
    # ========================================================================
    
    async def process_retry_queue(self, batch_size: int = 10):
        """
        Background job to process retry queue.
        Run this periodically (e.g., every 5 minutes via cron).
        """
        logger.info("🔄 Processing wallet creation retry queue...")
        
        async with self.db.get_session() as session:
            # Get pending retry items
            result = await session.execute(
                select(WalletCreationQueue)
                .where(
                    and_(
                        WalletCreationQueue.locked_at.is_(None),
                        WalletCreationQueue.scheduled_for <= datetime.utcnow(),
                        WalletCreationQueue.retry_count < WalletCreationQueue.max_retries
                    )
                )
                .limit(batch_size)
            )
            queue_items = result.scalars().all()
            
            if not queue_items:
                logger.info("✅ No pending wallet retries")
                return
            
            logger.info(f"📋 Processing {len(queue_items)} wallet retry items")
            
            for item in queue_items:
                try:
                    # Lock item
                    item.locked_at = datetime.utcnow()
                    item.locked_by = 'wallet_retry_worker'
                    await session.commit()
                    
                    # Attempt wallet creation
                    result = await self._create_wallet_for_chain(
                        str(item.user_id),
                        item.chain
                    )
                    
                    if result['success']:
                        # Remove from queue
                        await session.delete(item)
                        logger.info(f"✅ Retry successful for {item.chain} wallet")
                    else:
                        # Increment retry count and reschedule
                        item.retry_count += 1
                        item.locked_at = None
                        
                        # Exponential backoff
                        next_retry_seconds = self.RETRY_INTERVALS[
                            min(item.retry_count, len(self.RETRY_INTERVALS) - 1)
                        ]
                        item.scheduled_for = datetime.utcnow() + timedelta(seconds=next_retry_seconds)
                        item.error_message = result.get('error')
                        
                        logger.warning(
                            f"⚠️ Retry {item.retry_count} failed for {item.chain}, "
                            f"rescheduling in {next_retry_seconds}s"
                        )
                    
                    await session.commit()
                    
                except Exception as e:
                    logger.error(f"❌ Error processing queue item {item.id}: {e}")
                    # Unlock item for next attempt
                    item.locked_at = None
                    await session.commit()