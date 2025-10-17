# File: backend/services/wallet_connect_service.py
"""
Wallet Connect Orchestrator - Universal Wallet Integration
Supports exchange withdrawals (Binance, Coinbase, OKX, etc.) without APIs
Monitors incoming transactions via Algorand Indexer
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
import asyncio
import aiohttp
from algosdk import encoding
from algosdk.v2client import algod, indexer

from backend.config import settings
from backend.services.database_service import DatabaseService
from backend.services.audit_service import AuditService

logger = logging.getLogger(__name__)

class WalletConnectService:
    """
    Production-ready wallet orchestrator
    Enables deposits from any exchange/wallet without API integration
    """
    
    def __init__(
        self,
        db_service: DatabaseService,
        audit_service: AuditService,
        algod_client: algod.AlgodClient,
        indexer_client: indexer.IndexerClient
    ):
        self.db = db_service
        self.audit = audit_service
        self.algod = algod_client
        self.indexer = indexer_client
        
        # Supported assets with Algorand ASA IDs
        self.supported_assets = {
            "ALGO": {"asset_id": 0, "decimals": 6, "name": "Algorand"},
            "USDT": {"asset_id": 312769, "decimals": 6, "name": "Tether USD"},
            "USDCa": {"asset_id": 31566704, "decimals": 6, "name": "USD Coin"},
            "goBTC": {"asset_id": 386192725, "decimals": 8, "name": "Wrapped Bitcoin"},
            "goETH": {"asset_id": 386195940, "decimals": 8, "name": "Wrapped Ethereum"}
        }
        
        # Transaction monitoring state
        self.monitoring_active = False
        self.last_checked_round = None
        
        logger.info("WalletConnectService initialized")
    
    async def generate_deposit_address(
        self, 
        user_id: str, 
        asset: str = "USDT"
    ) -> Dict[str, Any]:
        """
        Generate unique deposit address for user
        Returns existing wallet address from user_wallets table
        """
        
        try:
            if asset not in self.supported_assets:
                raise ValueError(f"Unsupported asset: {asset}. Supported: {list(self.supported_assets.keys())}")
            
            # Get user's Algorand wallet
            query = "SELECT algorand_address FROM user_wallets WHERE user_id = %s"
            result = await self.db.execute_query(query, (user_id,))
            
            if not result:
                raise ValueError("User wallet not found. Create wallet first.")
            
            wallet_address = result[0]["algorand_address"]
            
            # Verify address is valid
            if not self._is_valid_algorand_address(wallet_address):
                raise ValueError("Invalid Algorand address in database")
            
            # Generate deposit tracking ID
            deposit_id = f"DEP_{uuid4().hex[:12].upper()}"
            
            # Store deposit expectation
            deposit_data = {
                "id": deposit_id,
                "user_id": user_id,
                "wallet_address": wallet_address,
                "asset": asset,
                "asset_id": self.supported_assets[asset]["asset_id"],
                "status": "awaiting_deposit",
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }
            
            await self.db.log_event("pending_deposits", deposit_data)
            
            # Log audit
            await self.audit.log_event(
                "DEPOSIT_ADDRESS_GENERATED",
                user_id=user_id,
                resource_id=deposit_id,
                details={"asset": asset, "address": wallet_address}
            )
            
            logger.info(f"Deposit address generated for user {user_id}: {wallet_address}")
            
            return {
                "success": True,
                "deposit_id": deposit_id,
                "address": wallet_address,
                "asset": asset,
                "network": "Algorand",
                "asset_id": self.supported_assets[asset]["asset_id"],
                "instructions": {
                    "step_1": f"Open your exchange (Binance, Coinbase, OKX, etc.)",
                    "step_2": f"Go to Withdraw → {asset}",
                    "step_3": "Select Network: Algorand",
                    "step_4": f"Paste address: {wallet_address}",
                    "step_5": "Confirm withdrawal",
                    "step_6": "Your balance will update in 5-30 seconds"
                },
                "important_notes": [
                    "Only send on Algorand network",
                    f"Only send {asset} to this address",
                    "Transactions are typically confirmed in 4.5 seconds",
                    "Minimum deposit: 1 USDT equivalent"
                ],
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Deposit address generation failed: {e}")
            raise
    
    def _is_valid_algorand_address(self, address: str) -> bool:
        """Validate Algorand address format"""
        try:
            encoding.decode_address(address)
            return True
        except Exception:
            return False
    
    async def get_withdrawal_address_info(
        self, 
        user_id: str, 
        destination_address: str, 
        asset: str
    ) -> Dict[str, Any]:
        """
        Validate user's exchange withdrawal address
        Provides instructions for sending to their exchange
        """
        
        try:
            if not self._is_valid_algorand_address(destination_address):
                raise ValueError("Invalid Algorand address format")
            
            if asset not in self.supported_assets:
                raise ValueError(f"Unsupported asset: {asset}")
            
            # Check if address is opted into ASA (for non-ALGO assets)
            if asset != "ALGO":
                is_opted_in = await self._check_asset_opt_in(
                    destination_address, 
                    self.supported_assets[asset]["asset_id"]
                )
                
                if not is_opted_in:
                    return {
                        "success": False,
                        "error": "Address not opted into asset",
                        "instructions": {
                            "issue": f"The address {destination_address} has not opted into {asset}",
                            "solution": "In your exchange, ensure you've enabled/added this asset first",
                            "note": "Most exchanges auto-opt-in when you generate a deposit address"
                        }
                    }
            
            withdrawal_id = f"WITH_{uuid4().hex[:12].upper()}"
            
            return {
                "success": True,
                "withdrawal_id": withdrawal_id,
                "destination_address": destination_address,
                "asset": asset,
                "network": "Algorand",
                "ready_to_send": True,
                "estimated_arrival": "4.5 seconds",
                "exchange_instructions": {
                    "binance": "Funds appear in Spot Wallet instantly",
                    "coinbase": "Check your Algorand wallet after 1 confirmation",
                    "okx": "Funds credited after 1 network confirmation",
                    "general": "Most exchanges credit after 1-3 confirmations (5-15 seconds)"
                }
            }
            
        except Exception as e:
            logger.error(f"Withdrawal address validation failed: {e}")
            raise
    
    async def _check_asset_opt_in(self, address: str, asset_id: int) -> bool:
        """Check if address has opted into ASA"""
        
        try:
            account_info = self.algod.account_info(address)
            
            if asset_id == 0:  # ALGO is always available
                return True
            
            # Check if asset exists in account's assets
            for asset in account_info.get("assets", []):
                if asset["asset-id"] == asset_id:
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Asset opt-in check failed: {e}")
            return False
    
    async def start_transaction_monitor(self):
        """
        Start background monitoring for incoming deposits
        Checks Algorand Indexer every 5 seconds for new transactions
        """
        
        if self.monitoring_active:
            logger.warning("Transaction monitor already running")
            return
        
        self.monitoring_active = True
        logger.info("🔍 Starting transaction monitor...")
        
        # Start monitoring loop
        asyncio.create_task(self._monitor_transactions())
    
    async def _monitor_transactions(self):
        """Background task to monitor incoming transactions"""
        
        while self.monitoring_active:
            try:
                await self._check_for_new_deposits()
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Transaction monitoring error: {e}")
                await asyncio.sleep(10)  # Back off on error
    
    async def _check_for_new_deposits(self):
        """Check indexer for new deposits to tracked addresses"""
        
        try:
            # Get all pending deposits
            query = """
                SELECT id, user_id, wallet_address, asset, asset_id, created_at
                FROM pending_deposits 
                WHERE status = 'awaiting_deposit' 
                AND expires_at > NOW()
            """
            pending = await self.db.execute_query(query)
            
            if not pending:
                return
            
            # Get current round
            status = self.algod.status()
            current_round = status["last-round"]
            
            # Set initial round if first check
            if not self.last_checked_round:
                self.last_checked_round = current_round - 100  # Look back 100 rounds (~8 minutes)
            
            # Check each pending deposit
            for deposit in pending:
                await self._check_address_transactions(
                    deposit["wallet_address"],
                    deposit["asset_id"],
                    deposit["user_id"],
                    deposit["id"],
                    deposit["asset"]
                )
            
            self.last_checked_round = current_round
            
        except Exception as e:
            logger.error(f"Deposit check failed: {e}")
    
    async def _check_address_transactions(
        self, 
        address: str, 
        asset_id: int, 
        user_id: str, 
        deposit_id: str,
        asset: str
    ):
        """Check specific address for new transactions"""
        
        try:
            # Query indexer for recent transactions to this address
            if asset_id == 0:  # ALGO
                response = self.indexer.search_transactions(
                    address=address,
                    address_role="receiver",
                    min_round=self.last_checked_round
                )
            else:  # ASA
                response = self.indexer.search_asset_transactions(
                    asset_id=asset_id,
                    address=address,
                    address_role="receiver",
                    min_round=self.last_checked_round
                )
            
            transactions = response.get("transactions", [])
            
            for tx in transactions:
                await self._process_incoming_transaction(
                    tx, user_id, deposit_id, asset, asset_id
                )
                
        except Exception as e:
            logger.error(f"Address transaction check failed for {address}: {e}")
    
    async def _process_incoming_transaction(
        self, 
        tx: Dict, 
        user_id: str, 
        deposit_id: str, 
        asset: str,
        asset_id: int
    ):
        """Process detected incoming transaction"""
        
        try:
            tx_id = tx["id"]
            
            # Check if already processed
            check_query = "SELECT id FROM processed_deposits WHERE tx_id = %s"
            existing = await self.db.execute_query(check_query, (tx_id,))
            
            if existing:
                return  # Already processed
            
            # Extract amount
            if asset_id == 0:  # ALGO
                amount = tx["payment-transaction"]["amount"] / 1_000_000  # microAlgos to ALGO
            else:  # ASA
                amount = tx["asset-transfer-transaction"]["amount"]
                decimals = self.supported_assets[asset]["decimals"]
                amount = amount / (10 ** decimals)
            
            # Minimum deposit check
            min_deposit = Decimal("1.0")  # 1 USDT equivalent
            if Decimal(str(amount)) < min_deposit:
                logger.warning(f"Deposit below minimum: {amount} {asset}")
                return
            
            # Credit user balance
            await self._credit_deposit(user_id, asset, Decimal(str(amount)), tx_id, deposit_id)
            
            # Mark pending deposit as completed
            update_query = """
                UPDATE pending_deposits 
                SET status = 'completed', completed_at = NOW(), tx_id = %s, amount = %s
                WHERE id = %s
            """
            await self.db.execute_query(update_query, (tx_id, float(amount), deposit_id))
            
            # Mark transaction as processed
            processed_data = {
                "tx_id": tx_id,
                "user_id": user_id,
                "deposit_id": deposit_id,
                "asset": asset,
                "amount": float(amount),
                "processed_at": datetime.utcnow().isoformat()
            }
            await self.db.log_event("processed_deposits", processed_data)
            
            # Log audit
            await self.audit.log_event(
                "DEPOSIT_RECEIVED",
                user_id=user_id,
                resource_id=tx_id,
                details={
                    "asset": asset,
                    "amount": float(amount),
                    "deposit_id": deposit_id,
                    "tx_id": tx_id
                }
            )
            
            logger.info(f"✅ Deposit processed: {amount} {asset} for user {user_id} (tx: {tx_id})")
            
        except Exception as e:
            logger.error(f"Transaction processing failed: {e}")
    
    async def _credit_deposit(
        self, 
        user_id: str, 
        asset: str, 
        amount: Decimal, 
        tx_id: str,
        deposit_id: str
    ):
        """Credit user balance with deposit"""
        
        # Get current balance
        query = f"SELECT {asset.lower()}_balance FROM wallet_balances WHERE user_id = %s"
        result = await self.db.execute_query(query, (user_id,))
        
        if not result:
            # Create balance record if doesn't exist
            create_query = """
                INSERT INTO wallet_balances (user_id, algo_balance, usdt_balance, usdc_balance, gobtc_balance, goeth_balance)
                VALUES (%s, 0, 0, 0, 0, 0)
            """
            await self.db.execute_query(create_query, (user_id,))
            current_balance = Decimal("0")
        else:
            current_balance = Decimal(str(result[0][f"{asset.lower()}_balance"]))
        
        new_balance = current_balance + amount
        
        # Update balance
        update_query = f"""
            UPDATE wallet_balances 
            SET {asset.lower()}_balance = %s, updated_at = NOW()
            WHERE user_id = %s
        """
        await self.db.execute_query(update_query, (float(new_balance), user_id))
        
        logger.info(f"Credited {amount} {asset} to user {user_id}. New balance: {new_balance}")
    
    async def stop_transaction_monitor(self):
        """Stop transaction monitoring"""
        self.monitoring_active = False
        logger.info("Transaction monitor stopped")
    
    async def get_supported_exchanges(self) -> List[Dict[str, Any]]:
        """Get list of supported exchanges (all exchanges with Algorand support)"""
        
        return [
            {
                "name": "Binance",
                "logo": "binance",
                "supported_assets": ["ALGO", "USDT", "USDCa"],
                "instructions_url": "https://www.binance.com/en/how-to-deposit/algorand"
            },
            {
                "name": "Coinbase",
                "logo": "coinbase",
                "supported_assets": ["ALGO", "USDT", "USDCa"],
                "instructions_url": "https://help.coinbase.com/en/coinbase/trading-and-funding/cryptocurrency-trading-pairs/algorand"
            },
            {
                "name": "OKX",
                "logo": "okx",
                "supported_assets": ["ALGO", "USDT", "USDCa"],
                "instructions_url": "https://www.okx.com/support/algorand"
            },
            {
                "name": "Kraken",
                "logo": "kraken",
                "supported_assets": ["ALGO"],
                "instructions_url": "https://support.kraken.com/hc/en-us/articles/algorand"
            },
            {
                "name": "Kucoin",
                "logo": "kucoin",
                "supported_assets": ["ALGO", "USDT"],
                "instructions_url": "https://www.kucoin.com/support/algorand"
            },
            {
                "name": "Bybit",
                "logo": "bybit",
                "supported_assets": ["ALGO", "USDT"],
                "instructions_url": "https://www.bybit.com/en-US/help-center/algorand"
            },
            {
                "name": "Gate.io",
                "logo": "gateio",
                "supported_assets": ["ALGO", "USDT", "USDCa"],
                "instructions_url": "https://www.gate.io/help/algorand"
            },
            {
                "name": "HTX (Huobi)",
                "logo": "htx",
                "supported_assets": ["ALGO", "USDT"],
                "instructions_url": "https://www.htx.com/support/algorand"
            },
            {
                "name": "MEXC",
                "logo": "mexc",
                "supported_assets": ["ALGO", "USDT"],
                "instructions_url": "https://www.mexc.com/support/algorand"
            },
            {
                "name": "Bitfinex",
                "logo": "bitfinex",
                "supported_assets": ["ALGO"],
                "instructions_url": "https://support.bitfinex.com/hc/en-us/articles/algorand"
            }
        ]