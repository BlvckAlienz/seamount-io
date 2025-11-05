# File: backend/services/wdk_service.py
"""
Tether WDK (Wallet Development Kit) Integration Service
Enables multi-chain wallet management: BTC, ETH, TON, Lightning Network

CRITICAL DESIGN PRINCIPLE:
- Abstract ALL blockchain complexity from users
- Auto-route transactions to optimal chain
- Never expose gas fees, private keys, or blockchain jargon
- "WhatsApp-level" simplicity for end users
"""

import logging
import aiohttp
import json
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from backend.config import settings, BlockchainNetwork, MultiChainBusinessModel
from backend.services.database_service import DatabaseService
from backend.services.audit_service import AuditService

logger = logging.getLogger(__name__)

class WDKService:
    """
    Tether WDK Wrapper Service
    
    Provides unified interface for:
    - Multi-chain wallet creation (BTC, ETH, TON, Lightning)
    - Asset transfers across chains
    - Balance queries
    - Transaction history
    - Smart routing (optimal chain selection)
    """
    
    def __init__(
        self,
        db_service: DatabaseService,
        audit_service: AuditService
    ):
        self.db = db_service
        self.audit = audit_service
        
        # WDK API Configuration
        self.wdk_api_url = settings.WDK_API_URL
        self.wdk_api_key = settings.WDK_API_KEY.get_secret_value() if settings.WDK_API_KEY else None
        
        # Enabled blockchains
        self.enabled_chains = settings.WDK_ENABLED_CHAINS
        
        # Chain-specific configurations
        self.chain_configs = {
            BlockchainNetwork.ETHEREUM: {
                "name": "Ethereum",
                "native_symbol": "ETH",
                "supports_tokens": True,
                "avg_confirmation_time": "12 seconds"
            },
            BlockchainNetwork.BITCOIN: {
                "name": "Bitcoin",
                "native_symbol": "BTC",
                "supports_tokens": False,
                "avg_confirmation_time": "10 minutes"
            },
            BlockchainNetwork.LIGHTNING: {
                "name": "Lightning Network",
                "native_symbol": "BTC",
                "supports_tokens": False,
                "avg_confirmation_time": "instant"
            },
            BlockchainNetwork.TON: {
                "name": "TON",
                "native_symbol": "TON",
                "supports_tokens": True,
                "avg_confirmation_time": "5 seconds"
            },
            BlockchainNetwork.POLYGON: {
                "name": "Polygon",
                "native_symbol": "MATIC",
                "supports_tokens": True,
                "avg_confirmation_time": "2 seconds"
            }
        }
        
        logger.info(f"WDKService initialized with chains: {self.enabled_chains}")
    
    # ========================================================================
    # MULTI-CHAIN WALLET CREATION (Invisible to Users)
    # ========================================================================
    
    async def create_multi_chain_wallet(
        self, 
        user_id: str,
        email: str,
        requested_chains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create wallets across multiple blockchains
        
        USER EXPERIENCE:
        - User clicks "Create Wallet"
        - We create BTC, ETH, TON wallets automatically
        - User sees: "Your wallet is ready!"
        - ZERO blockchain terminology shown
        
        Returns: Unified wallet object with all chain addresses
        """
        
        try:
            wallet_id = f"WALLET_{uuid4().hex[:12].upper()}"
            chains_to_create = requested_chains or self.enabled_chains
            
            logger.info(f"Creating multi-chain wallet for user {user_id}")
            
            # Create wallets for each chain via WDK API
            created_wallets = {}
            
            for chain in chains_to_create:
                try:
                    wallet_data = await self._create_single_chain_wallet(
                        user_id, chain, wallet_id
                    )
                    created_wallets[chain] = wallet_data
                    
                except Exception as e:
                    logger.error(f"Failed to create {chain} wallet: {e}")
                    # Continue with other chains even if one fails
                    continue
            
            if not created_wallets:
                raise Exception("Failed to create any wallets")
            
            # Store wallet metadata in database
            wallet_record = {
                "id": wallet_id,
                "user_id": user_id,
                "email": email,
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True,
                "chains": list(created_wallets.keys()),
                "wallet_type": "multi_chain"
            }
            
            # Store addresses per chain
            for chain, wallet_info in created_wallets.items():
                address_record = {
                    "wallet_id": wallet_id,
                    "user_id": user_id,
                    "blockchain": chain,
                    "address": wallet_info["address"],
                    "encrypted_private_key": wallet_info["encrypted_key"],
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Insert via Supabase
                await self.db.supabase.table("multi_chain_addresses").insert(address_record).execute()
            
            # Update main wallet record
            await self.db.supabase.table("user_wallets").upsert(wallet_record, on_conflict="user_id").execute()
            
            # Log audit trail
            await self.audit.log_event(
                "MULTI_CHAIN_WALLET_CREATED",
                user_id=user_id,
                resource_id=wallet_id,
                details={
                    "chains": list(created_wallets.keys()),
                    "addresses": {k: v["address"] for k, v in created_wallets.items()}
                }
            )
            
            logger.info(f"Multi-chain wallet created: {wallet_id}")
            
            return {
                "success": True,
                "wallet_id": wallet_id,
                "chains": created_wallets,
                "message": "Your wallet is ready! You can now send and receive on all supported chains.",
                "user_facing_message": "Wallet created successfully! 🎉"  # Simple, no jargon
            }
            
        except Exception as e:
            logger.error(f"Multi-chain wallet creation failed: {e}")
            raise Exception(f"Wallet creation failed: {str(e)}")
    
    async def _create_single_chain_wallet(
        self,
        user_id: str,
        chain: str,
        wallet_id: str
    ) -> Dict[str, Any]:
        """
        Create wallet on specific blockchain via WDK API
        
        WDK API Call Example:
        POST /wallets/create
        {
            "blockchain": "ethereum",
            "user_id": "user_123"
        }
        
        Response:
        {
            "address": "0x...",
            "public_key": "...",
            "encrypted_private_key": "..."
        }
        """
        
        # Call WDK API
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.wdk_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "blockchain": chain,
                "user_id": user_id,
                "wallet_id": wallet_id
            }
            
            # NOTE: This is pseudo-code - actual WDK API endpoints TBD
            async with session.post(
                f"{self.wdk_api_url}/wallets/create",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    raise Exception(f"WDK API error: {response.status}")
                
                data = await response.json()
                
                return {
                    "address": data["address"],
                    "encrypted_key": data["encrypted_private_key"],
                    "public_key": data.get("public_key"),
                    "blockchain": chain
                }
    
    # ========================================================================
    # BALANCE QUERIES (Unified Across All Chains)
    # ========================================================================
    
    async def get_unified_balance(self, user_id: str) -> Dict[str, Any]:
        """
        Get balances across ALL chains in one call
        
        USER SEES:
        ┌─────────────────────────┐
        │  Your Balance: $1,234   │
        ├─────────────────────────┤
        │  USDT: 500              │
        │  BTC: 0.05              │
        │  ETH: 0.2               │
        └─────────────────────────┘
        
        HIDDEN FROM USER:
        - Which chain each asset is on
        - Gas fees
        - Wallet addresses
        - Private keys
        """
        
        try:
            # Get all user's wallet addresses
            addresses_result = await self.db.supabase.table("multi_chain_addresses")\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()
            
            if not addresses_result.data:
                return {
                    "total_usd": 0.0,
                    "balances": {},
                    "wallet_exists": False
                }
            
            # Query each chain for balances
            all_balances = {}
            total_usd = Decimal("0")
            
            for address_record in addresses_result.data:
                chain = address_record["blockchain"]
                address = address_record["address"]
                
                try:
                    chain_balance = await self._query_chain_balance(chain, address)
                    all_balances[chain] = chain_balance
                    total_usd += Decimal(str(chain_balance.get("usd_value", 0)))
                    
                except Exception as e:
                    logger.error(f"Failed to query {chain} balance: {e}")
                    continue
            
            # Aggregate by asset (not by chain)
            asset_balances = self._aggregate_balances_by_asset(all_balances)
            
            return {
                "total_usd": float(total_usd),
                "balances": asset_balances,
                "wallet_exists": True,
                "last_updated": datetime.utcnow().isoformat(),
                "user_friendly_display": {
                    "main_balance": f"${float(total_usd):,.2f}",
                    "assets": [
                        {"symbol": asset, "amount": f"{balance:,.4f}", "chain": "hidden"}
                        for asset, balance in asset_balances.items()
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Unified balance query failed: {e}")
            return {"total_usd": 0.0, "balances": {}, "wallet_exists": False}
    
    async def _query_chain_balance(
        self, 
        chain: str, 
        address: str
    ) -> Dict[str, Any]:
        """
        Query balance on specific blockchain via WDK
        
        WDK API Call:
        GET /wallets/{address}/balance?blockchain={chain}
        """
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.wdk_api_key}",
                "Content-Type": "application/json"
            }
            
            async with session.get(
                f"{self.wdk_api_url}/wallets/{address}/balance",
                headers=headers,
                params={"blockchain": chain}
            ) as response:
                
                if response.status != 200:
                    logger.error(f"WDK balance query failed for {chain}: {response.status}")
                    return {"balance": 0, "usd_value": 0}
                
                data = await response.json()
                
                return {
                    "balance": data.get("balance", 0),
                    "usd_value": data.get("usd_value", 0),
                    "blockchain": chain,
                    "assets": data.get("tokens", [])
                }
    
    def _aggregate_balances_by_asset(
        self, 
        chain_balances: Dict[str, Dict]
    ) -> Dict[str, float]:
        """
        Aggregate balances by asset symbol (hide chain complexity)
        
        Example:
        Input:
        {
            "ethereum": {"USDT": 100, "ETH": 0.5},
            "polygon": {"USDT": 50, "MATIC": 10}
        }
        
        Output:
        {
            "USDT": 150,  # Combined from Ethereum + Polygon
            "ETH": 0.5,
            "MATIC": 10
        }
        """
        
        aggregated = {}
        
        for chain, balance_data in chain_balances.items():
            # Native currency (e.g., ETH, BTC)
            native_symbol = self.chain_configs.get(
                BlockchainNetwork(chain), {}
            ).get("native_symbol")
            
            if native_symbol and balance_data.get("balance"):
                aggregated[native_symbol] = aggregated.get(native_symbol, 0) + float(balance_data["balance"])
            
            # Tokens (e.g., USDT, USDC)
            for token in balance_data.get("assets", []):
                symbol = token.get("symbol")
                amount = float(token.get("balance", 0))
                aggregated[symbol] = aggregated.get(symbol, 0) + amount
        
        return aggregated
    
    # ========================================================================
    # SEND PAYMENT (Auto-Route to Optimal Chain)
    # ========================================================================
    
    async def send_payment(
        self,
        user_id: str,
        recipient_address: str,
        asset: str,
        amount: Decimal,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send payment with AUTOMATIC chain selection
        
        USER FLOW:
        1. User enters: Amount + Recipient
        2. WE auto-select optimal chain
        3. WE handle all blockchain complexity
        4. User sees: "Payment sent! ✓"
        
        SMART ROUTING LOGIC:
        - BTC <$100 → Lightning Network (instant)
        - USDT/USDC → Polygon (cheap)
        - BTC >$10k → Bitcoin mainnet (secure)
        - USDS → Algorand (native)
        """
        
        try:
            transaction_id = f"TX_{uuid4().hex[:12].upper()}"
            
            logger.info(f"Payment initiated: {amount} {asset} from user {user_id}")
            
            # STEP 1: Smart routing (find optimal chain)
            optimal_chain = await self._select_optimal_chain(asset, amount)
            
            # STEP 2: Calculate fees (hidden from user interface)
            fee_calculation = MultiChainBusinessModel.calculate_total_fee(
                transaction_type="p2p_local",
                amount=amount,
                from_asset=asset,
                blockchain=optimal_chain["chain"]
            )
            
            # STEP 3: Get user's wallet on selected chain
            sender_address = await self._get_user_address(user_id, optimal_chain["chain"].value)
            
            if not sender_address:
                raise Exception(f"No wallet found for {optimal_chain['chain'].value}")
            
            # STEP 4: Prepare transaction via WDK
            tx_data = await self._prepare_transaction(
                blockchain=optimal_chain["chain"].value,
                from_address=sender_address,
                to_address=recipient_address,
                asset=asset,
                amount=amount,
                fee=Decimal(str(fee_calculation["network_fee"]))
            )
            
            # STEP 5: Sign and broadcast via WDK
            tx_result = await self._sign_and_send_transaction(
                user_id=user_id,
                tx_data=tx_data,
                blockchain=optimal_chain["chain"].value
            )
            
            # STEP 6: Store transaction record
            tx_record = {
                "id": transaction_id,
                "user_id": user_id,
                "blockchain": optimal_chain["chain"].value,
                "from_address": sender_address,
                "to_address": recipient_address,
                "asset": asset,
                "amount": float(amount),
                "fee": fee_calculation["total_fee"],
                "tx_hash": tx_result["tx_hash"],
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "memo": memo
            }
            
            await self.db.supabase.table("multi_chain_transactions").insert(tx_record).execute()
            
            # Log audit
            await self.audit.log_event(
                "MULTI_CHAIN_PAYMENT_SENT",
                user_id=user_id,
                resource_id=transaction_id,
                details={
                    "asset": asset,
                    "amount": float(amount),
                    "blockchain": optimal_chain["chain"].value,
                    "tx_hash": tx_result["tx_hash"]
                }
            )
            
            logger.info(f"Payment sent: {transaction_id} via {optimal_chain['chain'].value}")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "tx_hash": tx_result["tx_hash"],
                "amount": float(amount),
                "asset": asset,
                "fee": fee_calculation["total_fee"],
                "estimated_confirmation": optimal_chain["estimated_time"],
                # USER-FACING MESSAGE (No technical jargon)
                "user_message": f"Payment sent! Your {asset} will arrive in {optimal_chain['estimated_time']}. 🚀",
                "blockchain_hidden": optimal_chain["chain"].value  # For debugging only
            }
            
        except Exception as e:
            logger.error(f"Payment failed: {e}")
            raise Exception(f"Payment failed: {str(e)}")
    
    async def _select_optimal_chain(
        self, 
        asset: str, 
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Smart routing logic (auto-select best chain)
        """
        
        # Get routing recommendation from business model
        return MultiChainBusinessModel.calculate_optimal_chain(
            transaction_type="p2p_local",
            amount=amount,
            from_asset=asset
        )
    
    async def _get_user_address(
        self, 
        user_id: str, 
        blockchain: str
    ) -> Optional[str]:
        """Get user's wallet address on specific blockchain"""
        
        result = await self.db.supabase.table("multi_chain_addresses")\
            .select("address")\
            .eq("user_id", user_id)\
            .eq("blockchain", blockchain)\
            .maybe_single()\
            .execute()
        
        return result.data["address"] if result.data else None
    
    async def _prepare_transaction(
        self,
        blockchain: str,
        from_address: str,
        to_address: str,
        asset: str,
        amount: Decimal,
        fee: Decimal
    ) -> Dict[str, Any]:
        """
        Prepare unsigned transaction via WDK
        
        WDK API Call:
        POST /transactions/prepare
        {
            "blockchain": "ethereum",
            "from": "0x...",
            "to": "0x...",
            "asset": "USDT",
            "amount": "100",
            "fee": "0.50"
        }
        """
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.wdk_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "blockchain": blockchain,
                "from_address": from_address,
                "to_address": to_address,
                "asset": asset,
                "amount": str(amount),
                "fee": str(fee)
            }
            
            async with session.post(
                f"{self.wdk_api_url}/transactions/prepare",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    raise Exception(f"WDK transaction prep failed: {response.status}")
                
                return await response.json()
    
    async def _sign_and_send_transaction(
        self,
        user_id: str,
        tx_data: Dict[str, Any],
        blockchain: str
    ) -> Dict[str, Any]:
        """
        Sign transaction with user's private key (stored encrypted) and broadcast
        
        SECURITY:
        - Private keys NEVER leave our secure backend
        - Signing happens server-side via WDK
        - User NEVER sees private keys
        """
        
        # Get encrypted private key
        key_result = await self.db.supabase.table("multi_chain_addresses")\
            .select("encrypted_private_key")\
            .eq("user_id", user_id)\
            .eq("blockchain", blockchain)\
            .single()\
            .execute()
        
        encrypted_key = key_result.data["encrypted_private_key"]
        
        # Sign and broadcast via WDK
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.wdk_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "transaction_data": tx_data,
                "encrypted_private_key": encrypted_key,
                "blockchain": blockchain
            }
            
            async with session.post(
                f"{self.wdk_api_url}/transactions/sign-and-send",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    raise Exception(f"WDK sign/send failed: {response.status}")
                
                return await response.json()
    
    # ========================================================================
    # TRANSACTION HISTORY (Unified Across All Chains)
    # ========================================================================
    
    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get transaction history across ALL chains
        
        USER SEES:
        - Simple list of "Sent/Received"
        - No mention of blockchain
        - Clean, WhatsApp-style UX
        """
        
        result = await self.db.supabase.table("multi_chain_transactions")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        transactions = []
        
        for tx in result.data:
            transactions.append({
                "id": tx["id"],
                "type": "sent" if tx["from_address"] else "received",
                "asset": tx["asset"],
                "amount": tx["amount"],
                "status": tx["status"],
                "date": tx["created_at"],
                "fee": tx["fee"],
                # USER-FRIENDLY DISPLAY (No blockchain mention)
                "display": {
                    "title": f"{'Sent' if tx['from_address'] else 'Received'} {tx['asset']}",
                    "subtitle": f"${tx['amount']:.2f}",
                    "time": self._format_time(tx["created_at"]),
                    "status_icon": "✓" if tx["status"] == "confirmed" else "⏳"
                }
            })
        
        return transactions
    
    def _format_time(self, timestamp: str) -> str:
        """Format timestamp user-friendly"""
        # TODO: Implement relative time (e.g., "5 minutes ago")
        return timestamp
    
    # ========================================================================
    # LIGHTNING NETWORK SPECIFIC (Bitcoin Micropayments)
    # ========================================================================
    
    async def create_lightning_invoice(
        self,
        user_id: str,
        amount_sats: int,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create Lightning Network invoice for receiving BTC
        
        USE CASE: Micropayments, tips, instant settlements
        """
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.wdk_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "user_id": user_id,
                "amount_sats": amount_sats,
                "memo": memo or "Seamount payment"
            }
            
            async with session.post(
                f"{self.wdk_api_url}/lightning/create-invoice",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    raise Exception(f"Lightning invoice creation failed: {response.status}")
                
                data = await response.json()
                
                return {
                    "invoice": data["payment_request"],
                    "amount_sats": amount_sats,
                    "amount_usd": amount_sats / 100_000_000 * 60000,  # Approx BTC price
                    "expires_at": data["expires_at"],
                    "qr_code": data.get("qr_code_url"),
                    "user_message": f"Lightning invoice created! Share to receive ${amount_sats / 100_000_000 * 60000:.2f}"
                }
    
    async def pay_lightning_invoice(
        self,
        user_id: str,
        payment_request: str
    ) -> Dict[str, Any]:
        """
        Pay Lightning Network invoice (instant BTC payment)
        """
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.wdk_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "user_id": user_id,
                "payment_request": payment_request
            }
            
            async with session.post(
                f"{self.wdk_api_url}/lightning/pay-invoice",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    raise Exception(f"Lightning payment failed: {response.status}")
                
                data = await response.json()
                
                return {
                    "success": True,
                    "payment_hash": data["payment_hash"],
                    "amount_sats": data["amount_sats"],
                    "fee_sats": data.get("fee_sats", 0),
                    "settled": True,
                    "user_message": "Payment sent instantly via Lightning Network! ⚡"
                }
        
        except Exception as e:
            logger.error(f"Lightning payment failed: {e}")
            raise Exception(f"Lightning payment failed: {str(e)}")
    
    # ========================================================================
    # CROSS-CHAIN BRIDGE (Move Assets Between Chains)
    # ========================================================================
    
    async def bridge_assets(
        self,
        user_id: str,
        asset: str,
        amount: Decimal,
        from_chain: str,
        to_chain: str
    ) -> Dict[str, Any]:
        """
        Bridge assets between blockchains (e.g., USDT from Ethereum → Polygon)
        
        USER FLOW:
        - User never sees "bridge" terminology
        - We auto-detect when bridging is needed
        - User just sees "Moving your USDT..." with progress bar
        """
        
        try:
            bridge_id = f"BRIDGE_{uuid4().hex[:12].upper()}"
            
            logger.info(f"Bridging {amount} {asset} from {from_chain} to {to_chain}")
            
            # Calculate bridge fee
            bridge_fee = MultiChainBusinessModel.BRIDGE_FEES.get(
                f"{from_chain}_to_{to_chain}",
                MultiChainBusinessModel.BRIDGE_FEES["default"]
            )
            
            fee_amount = amount * bridge_fee
            net_amount = amount - fee_amount
            
            # Get user addresses on both chains
            from_address = await self._get_user_address(user_id, from_chain)
            to_address = await self._get_user_address(user_id, to_chain)
            
            if not from_address or not to_address:
                raise Exception("Wallet not found on source or destination chain")
            
            # Execute bridge via WDK
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.wdk_api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "bridge_id": bridge_id,
                    "user_id": user_id,
                    "asset": asset,
                    "amount": str(amount),
                    "from_chain": from_chain,
                    "to_chain": to_chain,
                    "from_address": from_address,
                    "to_address": to_address
                }
                
                async with session.post(
                    f"{self.wdk_api_url}/bridge/transfer",
                    headers=headers,
                    json=payload
                ) as response:
                    
                    if response.status != 200:
                        raise Exception(f"Bridge transfer failed: {response.status}")
                    
                    bridge_result = await response.json()
            
            # Store bridge transaction
            bridge_record = {
                "id": bridge_id,
                "user_id": user_id,
                "asset": asset,
                "amount": float(amount),
                "fee": float(fee_amount),
                "from_chain": from_chain,
                "to_chain": to_chain,
                "status": "pending",
                "tx_hash_source": bridge_result.get("source_tx_hash"),
                "tx_hash_dest": bridge_result.get("dest_tx_hash"),
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.db.supabase.table("bridge_transactions").insert(bridge_record).execute()
            
            logger.info(f"Bridge initiated: {bridge_id}")
            
            return {
                "success": True,
                "bridge_id": bridge_id,
                "amount_sent": float(amount),
                "amount_received": float(net_amount),
                "fee": float(fee_amount),
                "estimated_time": "2-5 minutes",
                "user_message": f"Moving your {asset} to the faster network... ⚡",
                "status_hidden": {
                    "from_chain": from_chain,
                    "to_chain": to_chain,
                    "source_tx": bridge_result.get("source_tx_hash")
                }
            }
            
        except Exception as e:
            logger.error(f"Bridge failed: {e}")
            raise Exception(f"Bridge transfer failed: {str(e)}")
    
    # ========================================================================
    # ACCOUNT ABSTRACTION (Gasless Transactions)
    # ========================================================================
    
    async def execute_gasless_transaction(
        self,
        user_id: str,
        operation: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute transaction without user paying gas (via WDK Account Abstraction)
        
        USE CASES:
        - New users don't need native tokens (ETH, MATIC) to start
        - We sponsor gas fees for small transactions
        - Premium UX - users never see "insufficient gas" errors
        """
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.wdk_api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "user_id": user_id,
                    "operation": operation,
                    "params": params,
                    "sponsor_gas": True
                }
                
                async with session.post(
                    f"{self.wdk_api_url}/account-abstraction/execute",
                    headers=headers,
                    json=payload
                ) as response:
                    
                    if response.status != 200:
                        raise Exception(f"Gasless transaction failed: {response.status}")
                    
                    data = await response.json()
            
            return {
                "success": True,
                "tx_hash": data["tx_hash"],
                "user_message": "Transaction completed! (We covered the fees) 🎁"
            }
            
        except Exception as e:
            logger.error(f"Gasless transaction failed: {e}")
            raise Exception(f"Transaction failed: {str(e)}")
    
    # ========================================================================
    # ASSET DISCOVERY (Show What User Can Do)
    # ========================================================================
    
    async def get_available_assets(self, user_id: str) -> Dict[str, Any]:
        """
        Get list of assets user can interact with
        
        SMART DISPLAY:
        - Show assets with balances first
        - Group by category (stablecoins, crypto, commodities)
        - Hide empty wallets unless user requests
        """
        
        # Get user's current balances
        balances = await self.get_unified_balance(user_id)
        
        # Asset categories
        asset_catalog = {
            "stablecoins": [
                {
                    "symbol": "USDT",
                    "name": "Tether USD",
                    "balance": balances["balances"].get("USDT", 0),
                    "available_on": ["ethereum", "polygon", "algorand"],
                    "icon": "💵"
                },
                {
                    "symbol": "USDC",
                    "name": "USD Coin",
                    "balance": balances["balances"].get("USDC", 0),
                    "available_on": ["ethereum", "polygon"],
                    "icon": "💵"
                },
                {
                    "symbol": 
                    "name": "Seamount USD",
                    "balance": balances["balances"].get( 0),
                    "available_on": ["algorand"],
                    "icon": "🌊",
                    "is_native": True
                }
            ],
            "cryptocurrencies": [
                {
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "balance": balances["balances"].get("BTC", 0),
                    "available_on": ["bitcoin", "lightning"],
                    "icon": "₿"
                },
                {
                    "symbol": "ETH",
                    "name": "Ethereum",
                    "balance": balances["balances"].get("ETH", 0),
                    "available_on": ["ethereum"],
                    "icon": "Ξ"
                }
            ]
        }
        
        return {
            "total_value_usd": balances["total_usd"],
            "assets_by_category": asset_catalog,
            "supported_chains": self.enabled_chains,
            "user_display": {
                "main_balance": f"${balances['total_usd']:,.2f}",
                "top_assets": [
                    f"{asset['icon']} {asset['symbol']}: {asset['balance']:.4f}"
                    for category in asset_catalog.values()
                    for asset in category
                    if asset['balance'] > 0
                ][:3]
            }
        }
    
    # ========================================================================
    # WALLET IMPORT (Connect External Wallets)
    # ========================================================================
    
    async def import_external_wallet(
        self,
        user_id: str,
        blockchain: str,
        address: str,
        wallet_type: str = "watch_only"
    ) -> Dict[str, Any]:
        """
        Import external wallet (MetaMask, Trust Wallet, etc.)
        
        MODES:
        - watch_only: Track balance only (no private key)
        - full_import: Import private key (user provides seed phrase)
        """
        
        try:
            # Verify address is valid
            is_valid = await self._verify_address(blockchain, address)
            
            if not is_valid:
                raise Exception(f"Invalid {blockchain} address")
            
            # Store imported wallet
            import_record = {
                "user_id": user_id,
                "blockchain": blockchain,
                "address": address,
                "wallet_type": wallet_type,
                "is_imported": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.db.supabase.table("multi_chain_addresses").insert(import_record).execute()
            
            # Log audit
            await self.audit.log_event(
                "EXTERNAL_WALLET_IMPORTED",
                user_id=user_id,
                resource_id=address,
                details={
                    "blockchain": blockchain,
                    "wallet_type": wallet_type
                }
            )
            
            logger.info(f"External wallet imported: {address} ({blockchain})")
            
            return {
                "success": True,
                "address": address,
                "blockchain": blockchain,
                "wallet_type": wallet_type,
                "user_message": f"Wallet connected! You can now use your {blockchain} assets on Seamount. 🔗"
            }
            
        except Exception as e:
            logger.error(f"Wallet import failed: {e}")
            raise Exception(f"Wallet import failed: {str(e)}")
    
    async def _verify_address(self, blockchain: str, address: str) -> bool:
        """Verify address format for specific blockchain"""
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.wdk_api_key}",
                "Content-Type": "application/json"
            }
            
            async with session.get(
                f"{self.wdk_api_url}/utils/verify-address",
                headers=headers,
                params={"blockchain": blockchain, "address": address}
            ) as response:
                
                if response.status != 200:
                    return False
                
                data = await response.json()
                return data.get("valid", False)
    
    # ========================================================================
    # SWAP AGGREGATION (Best Rates Across DEXes)
    # ========================================================================
    
    async def get_swap_quote(
        self,
        user_id: str,
        from_asset: str,
        to_asset: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Get best swap rate across multiple DEXes
        
        WDK aggregates:
        - Uniswap
        - SushiSwap
        - PancakeSwap
        - 0x Protocol
        
        USER SEES:
        "You'll receive ~234.56 USDT" (no mention of DEX routing)
        """
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.wdk_api_key}",
                "Content-Type": "application/json"
            }
            
            params = {
                "from_asset": from_asset,
                "to_asset": to_asset,
                "amount": str(amount),
                "user_id": user_id
            }
            
            async with session.get(
                f"{self.wdk_api_url}/swap/quote",
                headers=headers,
                params=params
            ) as response:
                
                if response.status != 200:
                    raise Exception(f"Swap quote failed: {response.status}")
                
                data = await response.json()
        
        # Calculate Seamount fee
        swap_type = self._determine_swap_type(from_asset, to_asset)
        swap_fee_rate = MultiChainBusinessModel.SWAP_FEE_STRUCTURE[swap_type]
        
        seamount_fee = amount * swap_fee_rate
        estimated_receive = Decimal(str(data["estimated_output"])) - seamount_fee
        
        return {
            "from_asset": from_asset,
            "to_asset": to_asset,
            "amount_in": float(amount),
            "estimated_output": float(estimated_receive),
            "exchange_rate": float(Decimal(str(data["estimated_output"])) / amount),
            "fee": float(seamount_fee),
            "slippage": data.get("slippage_percent", 0.5),
            "valid_for_seconds": 30,
            "user_display": {
                "you_pay": f"{amount} {from_asset}",
                "you_receive": f"~{estimated_receive:.4f} {to_asset}",
                "rate": f"1 {from_asset} = {float(Decimal(str(data['estimated_output'])) / amount):.6f} {to_asset}"
            },
            "route_hidden": data.get("route", [])  # DEX routing (hidden from user)
        }
    
    def _determine_swap_type(self, from_asset: str, to_asset: str) -> str:
        """Determine swap type for fee calculation"""
        
        stablecoins = ["USDT", "USDC",  "DAI"]
        
        from_stable = from_asset in stablecoins
        to_stable = to_asset in stablecoins
        
        if from_stable and to_stable:
            return "stable_to_stable"
        elif from_stable:
            return "stable_to_volatile"
        elif to_stable:
            return "volatile_to_stable"
        else:
            return "volatile_to_volatile"
    
    # ========================================================================
    # HEALTH CHECK & MONITORING
    # ========================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Check WDK service health and chain availability"""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.wdk_api_key}",
                    "Content-Type": "application/json"
                }
                
                async with session.get(
                    f"{self.wdk_api_url}/health",
                    headers=headers
                ) as response:
                    
                    if response.status != 200:
                        return {
                            "status": "unhealthy",
                            "wdk_api": "unreachable"
                        }
                    
                    data = await response.json()
            
            return {
                "status": "healthy",
                "wdk_api": "reachable",
                "supported_chains": data.get("supported_chains", []),
                "api_version": data.get("version", "unknown")
            }
            
        except Exception as e:
            logger.error(f"WDK health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }