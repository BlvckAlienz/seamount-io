# File: backend/services/wdk_deposit_monitor.py
"""
WDK Deposit Monitor - Polls WDK chains for incoming deposits
Runs as background task to credit wallet balances
"""

import logging
import asyncio
from typing import Dict, List
from decimal import Decimal
from datetime import datetime

from backend.services.database_service import DatabaseService
from backend.config import get_settings

logger = logging.getLogger(__name__)

class WDKDepositMonitor:
    """
    Monitors WDK-enabled wallets for incoming deposits
    Credits balances when transactions confirmed
    """
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.settings = get_settings()
        self.monitored_chains = ["bitcoin", "ethereum", "polygon", "tron"]
        
        logger.info("✅ WDKDepositMonitor initialized")
    
    async def monitor_deposits(self):
        """Main polling loop - runs continuously"""
        
        while True:
            try:
                # Get all users with WDK wallets
                users_query = """
                    SELECT DISTINCT user_id 
                    FROM multi_chain_wallets 
                    WHERE chain IN ('bitcoin', 'ethereum', 'polygon', 'tron')
                    AND address IS NOT NULL
                """
                
                users_result = await self.db.execute_query(users_query)
                
                if not users_result:
                    await asyncio.sleep(30)  # No users, wait 30s
                    continue
                
                for row in users_result:
                    user_id = row["user_id"]
                    await self._check_user_deposits(user_id)
                
                # Poll every 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"💥 Deposit monitor error: {e}")
                await asyncio.sleep(60)  # Error cooldown
    
    async def _check_user_deposits(self, user_id: str):
        """Check deposits for a single user across all WDK chains"""
        
        for chain in self.monitored_chains:
            try:
                # Get user's wallet address for this chain
                wallet_query = """
                    SELECT address, last_checked_tx_height 
                    FROM multi_chain_wallets 
                    WHERE user_id = %s AND chain = %s
                """
                
                wallet_result = await self.db.execute_query(wallet_query, (user_id, chain))
                
                if not wallet_result:
                    continue
                
                address = wallet_result[0]["address"]
                last_height = wallet_result[0].get("last_checked_tx_height", 0)
                
                # Call WDK microservice to get transactions
                import aiohttp
                
                wdk_url = self.settings.WDK_SERVICE_URL
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{wdk_url}/transactions/history",
                        json={
                            "chain": chain,
                            "address": address,
                            "from_height": last_height
                        },
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        
                        if response.status != 200:
                            logger.warning(f"WDK API error for {chain}: {response.status}")
                            continue
                        
                        tx_data = await response.json()
                        
                        if not tx_data.get("success") or not tx_data.get("transactions"):
                            continue
                        
                        # Process new transactions
                        for tx in tx_data["transactions"]:
                            if tx["type"] == "incoming" and tx["confirmations"] >= 3:
                                await self._credit_deposit(
                                    user_id, 
                                    chain, 
                                    tx["asset"], 
                                    Decimal(str(tx["amount"])),
                                    tx["tx_hash"]
                                )
                        
                        # Update last checked height
                        new_height = tx_data.get("current_height", last_height)
                        update_query = """
                            UPDATE multi_chain_wallets 
                            SET last_checked_tx_height = %s, last_checked_at = NOW()
                            WHERE user_id = %s AND chain = %s
                        """
                        await self.db.execute_query(update_query, (new_height, user_id, chain))
                
            except Exception as e:
                logger.error(f"Error checking {chain} for user {user_id}: {e}")
    
    async def _credit_deposit(
        self, 
        user_id: str, 
        chain: str, 
        asset: str, 
        amount: Decimal, 
        tx_hash: str
    ):
        """Credit user's wallet balance for a confirmed deposit"""
        
        try:
            # Check if already processed
            check_query = "SELECT id FROM deposit_credits WHERE tx_hash = %s"
            existing = await self.db.execute_query(check_query, (tx_hash,))
            
            if existing:
                logger.debug(f"Deposit {tx_hash} already credited")
                return
            
            # Update wallet balance
            balance_column = f"{asset.lower()}_balance"
            
            update_query = f"""
                UPDATE wallet_balances 
                SET {balance_column} = {balance_column} + %s, updated_at = NOW()
                WHERE user_id = %s
            """
            
            await self.db.execute_query(update_query, (float(amount), user_id))
            
            # Log the credit
            credit_record = {
                "user_id": user_id,
                "chain": chain,
                "asset": asset,
                "amount": float(amount),
                "tx_hash": tx_hash,
                "credited_at": datetime.utcnow().isoformat()
            }
            
            await self.db.log_event("deposit_credits", credit_record)
            
            logger.info(f"✅ Credited {amount} {asset} to user {user_id[:8]}... (tx: {tx_hash[:10]}...)")
            
        except Exception as e:
            logger.error(f"Failed to credit deposit: {e}")