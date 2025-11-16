# File: backend/services/fee_collection_scheduler.py
"""
Background fee collection scheduler
Runs as part of the main backend process
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional

logger = logging.getLogger(__name__)

class FeeCollectionScheduler:
    """
    Runs fee collection at scheduled times
    Non-blocking background task
    """
    
    def __init__(self, target_hour: int = 3, target_minute: int = 0):
        """
        Args:
            target_hour: Hour to run (0-23, default 3 = 3 AM)
            target_minute: Minute to run (0-59, default 0)
        """
        self.target_hour = target_hour
        self.target_minute = target_minute
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Fee collection scheduler already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        logger.info(f"✅ Fee collection scheduler started (runs daily at {self.target_hour:02d}:{self.target_minute:02d})")
    
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("❌ Fee collection scheduler stopped")
    
    async def _run_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                # Calculate time until next run
                now = datetime.now()
                target = now.replace(
                    hour=self.target_hour,
                    minute=self.target_minute,
                    second=0,
                    microsecond=0
                )
                
                # If target time already passed today, schedule for tomorrow
                if target <= now:
                    target = target.replace(day=target.day + 1)
                
                wait_seconds = (target - now).total_seconds()
                logger.info(f"⏰ Next fee collection in {wait_seconds/3600:.1f} hours (at {target})")
                
                # Wait until target time
                await asyncio.sleep(wait_seconds)
                
                # Run collection
                logger.info("💰 Starting scheduled fee collection...")
                await self._collect_fees()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
                # Wait 1 hour before retrying
                await asyncio.sleep(3600)
    
    async def _collect_fees(self):
        """Execute fee collection"""
        try:
            from backend.scripts.collect_fees import collect_fees_for_chain
            
            chains = ['algorand', 'bitcoin', 'ethereum', 'polygon', 'tron']
            
            for chain in chains:
                try:
                    await collect_fees_for_chain(chain, dry_run=False)
                except Exception as chain_err:
                    logger.error(f"❌ Failed to collect {chain} fees: {chain_err}")
            
            logger.info("✅ Scheduled fee collection completed")
            
        except Exception as e:
            logger.error(f"❌ Fee collection failed: {e}")