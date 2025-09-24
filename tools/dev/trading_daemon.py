import asyncio
import logging
import time
import os
from decimal import Decimal
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import json
import traceback
from payment_processor import FlutterwaveProcessor
from seamount_payment_engine import SeamountPaymentEngine
from usds_asset_manager import USDSManager, CollateralType
from seamount_oracle_complete import SeamountOracle
from ai_agents import SeamountTradingAgent, TradingSignal


# External imports with error handling
try:
    from tinyman_client import TinymanClient
    from algosdk import account, mnemonic
    from supabase import create_client, Client
except ImportError as e:
    logging.error(f"Critical dependency missing: {e}")
    raise

# Internal imports
from ai_agents import SeamountTradingAgent, TradingSignal, SeamountPaymentAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingDaemon:
    """
    Production-ready trading daemon for Seamount.io platform
    Handles autonomous trading, compliance, and wallet management
    """
    
    def __init__(self, network: str = "testnet"):
        self.network = network
        self.max_retries = 3
        self.retry_delay = 1.0
        self.trading_wallets: Dict[str, Dict[str, str]] = {}
        self.active_trades: Dict[str, Dict] = {}
        self.last_health_check = 0
        
        # Initialize clients with error handling
        self._initialize_clients()
        
        # Initialize agents
        self.trading_agent = SeamountTradingAgent()
        self.payment_agent = SeamountPaymentAgent()
        
        logger.info(f"TradingDaemon initialized on {network}")

    def _initialize_clients(self):
        """Initialize all external clients with robust error handling"""
        try:
            # Supabase client
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            if not supabase_url or not supabase_key:
                raise ValueError("Missing Supabase credentials")
            
            self.supabase: Client = create_client(supabase_url, supabase_key)
            
            # Tinyman client
            self.tinyman = TinymanClient(network=self.network)
            
            # Validate connections
            self._validate_connections()
            
        except Exception as e:
            logger.error(f"Client initialization failed: {e}")
            raise

    def _validate_connections(self):
        """Validate all external connections"""
        try:
            # Test Supabase connection
            self.supabase.table("users").select("count").limit(1).execute()
            logger.info("Supabase connection validated")
            
            # Test Tinyman connection
            self.tinyman.get_asset_list()
            logger.info("Tinyman connection validated")
            
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            raise

    async def retry_async(self, func, *args, **kwargs):
        """Async retry wrapper with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Max retries exceeded for {func.__name__}: {e}")
                    raise
                
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {wait_time}s")
                await asyncio.sleep(wait_time)

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "components": {},
            "metrics": {}
        }
        
        try:
            # Check Supabase
            start_time = time.time()
            await self.supabase.table("users").select("count").limit(1).execute()
            health_status["components"]["supabase"] = {
                "status": "healthy",
                "response_time": time.time() - start_time
            }
            
            # Check Tinyman
            start_time = time.time()
            self.tinyman.get_asset_list()
            health_status["components"]["tinyman"] = {
                "status": "healthy",
                "response_time": time.time() - start_time
            }
            
            # System metrics
            health_status["metrics"] = {
                "active_wallets": len(self.trading_wallets),
                "active_trades": len(self.active_trades),
                "uptime": time.time() - self.last_health_check
            }
            
            self.last_health_check = time.time()
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            logger.error(f"Health check failed: {e}")
        
        return health_status

    async def check_user_compliance(self, user_id: str, trade_amount: Decimal) -> bool:
        """Enhanced compliance check with detailed logging"""
        try:
            response = await self.supabase.table("users").select(
                "kyc_level, kyc_status, country_code, is_active"
            ).eq("id", user_id).execute()
            
            if not response.data:
                logger.error(f"User not found: {user_id}")
                raise ValueError("User not found")
            
            user_data = response.data[0]
            
            # Check if user is active
            if not user_data.get("is_active", False):
                logger.error(f"User account inactive: {user_id}")
                raise ValueError("User account inactive")
            
            # Check KYC status
            if user_data.get("kyc_status") != "approved":
                logger.error(f"User KYC not approved: {user_id}")
                raise ValueError("KYC not approved")
            
            kyc_level = user_data.get("kyc_level", 0)
            
            # KYC level limits
            limits = {
                0: Decimal("0"),
                1: Decimal("10000"),
                2: Decimal("100000"),
                3: Decimal("1000000")
            }
            
            if trade_amount > limits.get(kyc_level, Decimal("0")):
                logger.error(f"Trade amount {trade_amount} exceeds limit for KYC level {kyc_level}")
                raise ValueError(f"Trade amount exceeds KYC level {kyc_level} limit")
            
            # Log compliance check
            await self.supabase.table("compliance_logs").insert({
                "user_id": user_id,
                "check_type": "trade_compliance",
                "amount": str(trade_amount),
                "kyc_level": kyc_level,
                "status": "passed",
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(f"Compliance check passed for user {user_id}")
            return True
            
        except Exception as e:
            # Log failed compliance check
            try:
                await self.supabase.table("compliance_logs").insert({
                    "user_id": user_id,
                    "check_type": "trade_compliance",
                    "amount": str(trade_amount),
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }).execute()
            except:
                pass
            
            logger.error(f"Compliance check failed for user {user_id}: {e}")
            raise

    async def create_trading_wallet(self, user_id: str) -> Dict[str, str]:
        """Create and securely store trading wallet"""
        try:
            # Generate new account
            private_key, address = account.generate_account()
            mnemonic_phrase = mnemonic.from_private_key(private_key)
            
            # Store wallet info
            wallet_data = {
                "address": address,
                "private_key": private_key,  # In production, encrypt this
                "mnemonic": mnemonic_phrase,  # In production, encrypt this
                "created_at": datetime.utcnow().isoformat(),
                "network": self.network
            }
            
            # Update user record
            await self.supabase.table("users").update({
                "trading_address": address,
                "wallet_created_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            
            # Store in memory
            self.trading_wallets[user_id] = wallet_data
            
            logger.info(f"Created trading wallet for user {user_id}: {address}")
            return wallet_data
            
        except Exception as e:
            logger.error(f"Failed to create trading wallet for user {user_id}: {e}")
            raise

    async def get_trading_wallet(self, user_id: str) -> Dict[str, str]:
        """Get or create trading wallet for user"""
        try:
            # Check memory first
            if user_id in self.trading_wallets:
                return self.trading_wallets[user_id]
            
            # Check database
            response = await self.supabase.table("users").select(
                "trading_address"
            ).eq("id", user_id).execute()
            
            if response.data and response.data[0].get("trading_address"):
                # Wallet exists but not in memory - this is a limitation
                # In production, you'd retrieve encrypted private key from secure storage
                logger.warning(f"Trading wallet exists but private key not in memory for user {user_id}")
                return await self.create_trading_wallet(user_id)
            
            # Create new wallet
            return await self.create_trading_wallet(user_id)
            
        except Exception as e:
            logger.error(f"Failed to get trading wallet for user {user_id}: {e}")
            raise

    async def execute_swap(self, signal: TradingSignal) -> Dict[str, Any]:
        """Execute trading swap with comprehensive error handling"""
        trade_id = f"{signal.user_id}_{int(time.time())}"
        
        try:
            # Compliance check
            await self.check_user_compliance(signal.user_id, Decimal(str(signal.quantity)))
            
            # Get trading wallet
            wallet = await self.get_trading_wallet(signal.user_id)
            
            # Determine swap parameters
            from_token = "USDS" if signal.action == "BUY" else signal.symbol
            to_token = signal.symbol if signal.action == "BUY" else "USDS"
            amount = Decimal(str(signal.quantity))
            
            # Get quote with retry
            quote = await self.retry_async(
                self.tinyman.get_quote,
                amount=amount,
                from_token=from_token,
                to_token=to_token
            )
            
            # Risk checks
            if quote.price_impact > 0.05:  # 5% max slippage
                logger.warning(f"High price impact for swap: {quote.price_impact}")
                raise ValueError("Swap price impact too high")
            
            # Record trade attempt
            trade_record = {
                "id": trade_id,
                "user_id": signal.user_id,
                "signal_id": f"{signal.symbol}_{signal.timestamp}",
                "from_token": from_token,
                "to_token": to_token,
                "amount": str(amount),
                "expected_output": str(quote.amount_out),
                "price_impact": quote.price_impact,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.supabase.table("trades").insert(trade_record).execute()
            self.active_trades[trade_id] = trade_record
            
            # Execute swap
            result = await self.retry_async(
                self.tinyman.execute_swap,
                quote=quote,
                address=wallet["address"],
                private_key=wallet["private_key"]
            )
            
            # Update trade record
            trade_record.update({
                "status": "completed",
                "tx_hash": result.get("tx_hash"),
                "actual_output": str(result.get("amount_out", 0)),
                "fees": str(result.get("fees", 0)),
                "completed_at": datetime.utcnow().isoformat()
            })
            
            await self.supabase.table("trades").update({
                "status": "completed",
                "tx_hash": result.get("tx_hash"),
                "actual_output": str(result.get("amount_out", 0)),
                "fees": str(result.get("fees", 0)),
                "completed_at": datetime.utcnow().isoformat()
            }).eq("id", trade_id).execute()
            
            logger.info(f"Swap executed successfully: {trade_id}")
            return {
                "trade_id": trade_id,
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            # Update trade record as failed
            try:
                await self.supabase.table("trades").update({
                    "status": "failed",
                    "error": str(e),
                    "failed_at": datetime.utcnow().isoformat()
                }).eq("id", trade_id).execute()
            except:
                pass
            
            logger.error(f"Swap execution failed for trade {trade_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                "trade_id": trade_id,
                "status": "failed",
                "error": str(e)
            }

    async def process_trading_signals(self):
        """Main trading loop - process signals from AI agent"""
        try:
            # Generate trading signals
            signals = await self.trading_agent.generate_trading_signals()
            
            if not signals:
                logger.info("No trading signals generated")
                return
            
            # Process each signal
            tasks = []
            for signal in signals:
                task = self.execute_swap(signal)
                tasks.append(task)
            
            # Execute trades concurrently with limit
            semaphore = asyncio.Semaphore(5)  # Max 5 concurrent trades
            
            async def bounded_execute(signal):
                async with semaphore:
                    return await self.execute_swap(signal)
            
            results = await asyncio.gather(*[bounded_execute(s) for s in signals], return_exceptions=True)
            
            # Log results
            successful = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
            failed = len(results) - successful
            
            logger.info(f"Processed {len(signals)} signals: {successful} successful, {failed} failed")
            
        except Exception as e:
            logger.error(f"Trading signal processing failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def run_daemon(self):
        """Main daemon loop with health monitoring"""
        logger.info("Starting trading daemon...")
        
        while True:
            try:
                # Health check every 5 minutes
                if time.time() - self.last_health_check > 300:
                    health = await self.health_check()
                    if health["status"] != "healthy":
                        logger.warning(f"System health check failed: {health}")
                
                # Process trading signals
                await self.process_trading_signals()
                
                # Clean up old trades
                await self.cleanup_old_trades()
                
                # Sleep before next iteration
                await asyncio.sleep(30)  # 30 second intervals
                
            except KeyboardInterrupt:
                logger.info("Daemon shutdown requested")
                break
            except Exception as e:
                logger.error(f"Daemon loop error: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                await asyncio.sleep(60)  # Wait longer on error

    async def cleanup_old_trades(self):
        """Clean up old trade records from memory"""
        try:
            cutoff_time = time.time() - 3600  # 1 hour
            old_trades = [
                trade_id for trade_id, trade in self.active_trades.items()
                if trade.get("created_at") and 
                datetime.fromisoformat(trade["created_at"]).timestamp() < cutoff_time
            ]
            
            for trade_id in old_trades:
                del self.active_trades[trade_id]
            
            if old_trades:
                logger.info(f"Cleaned up {len(old_trades)} old trade records")
                
        except Exception as e:
            logger.error(f"Trade cleanup failed: {e}")

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down trading daemon...")
        
        # Cancel any pending trades
        for trade_id in list(self.active_trades.keys()):
            try:
                await self.supabase.table("trades").update({
                    "status": "cancelled",
                    "cancelled_at": datetime.utcnow().isoformat()
                }).eq("id", trade_id).execute()
            except:
                pass
        
        logger.info("Trading daemon shutdown complete")


# CLI entry point
if __name__ == "__main__":
    import sys
    
    network = sys.argv[1] if len(sys.argv) > 1 else "testnet"
    daemon = TradingDaemon(network=network)
    
    try:
        asyncio.run(daemon.run_daemon())
    except KeyboardInterrupt:
        asyncio.run(daemon.shutdown())
