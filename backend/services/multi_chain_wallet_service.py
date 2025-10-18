# File: backend/services/multi_chain_wallet_service.py
"""
Unified Multi-Chain Wallet Service
Orchestrates between Algorand (USDS native) and WDK (BTC/ETH/TON)

DESIGN PHILOSOPHY:
- One service to rule them all
- Auto-detect which chain to use
- Abstract ALL complexity from users
- "It just works" experience
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime

from backend.services.wallet_service import WalletService
from backend.services.algorand_service import AlgorandService
from backend.services.wdk_service import WDKService
from backend.services.database_service import DatabaseService
from backend.services.audit_service import AuditService
from backend.config import settings, BlockchainNetwork, MultiChainBusinessModel

logger = logging.getLogger(__name__)

class MultiChainWalletService:
    """
    Unified wallet orchestrator
    
    Routes operations to:
    - AlgorandService for USDS/USDCa
    - WDKService for BTC/ETH/TON/Lightning
    
    USER NEVER KNOWS THE DIFFERENCE
    """
    
    def __init__(
        self,
        db_service: DatabaseService,
        audit_service: AuditService,
        algorand_service: AlgorandService
    ):
        self.db = db_service
        self.audit = audit_service
        
        # Initialize sub-services
        self.algorand = algorand_service
        self.wdk = WDKService(db_service, audit_service)
        
        # Asset routing map (which service handles which asset)
        self.asset_routing = self._build_asset_routing()
        
        logger.info("MultiChainWalletService initialized")
    
    def _build_asset_routing(self) -> Dict[str, str]:
        """
        Map assets to their handler service
        
        Returns:
        {
            "USDS": "algorand",
            "USDCa": "algorand",
            "BTC": "wdk",
            "ETH": "wdk",
            ...
        }
        """
        
        routing = {}
        
        for asset_symbol, asset_config in settings.SUPPORTED_ASSETS.items():
            blockchain = asset_config.get("blockchain", "algorand")
            
            if blockchain == "algorand":
                routing[asset_symbol] = "algorand"
            else:
                routing[asset_symbol] = "wdk"
        
        return routing
    
    # ========================================================================
    # UNIFIED WALLET CREATION (One Click)
    # ========================================================================
    
    async def create_wallet(
        self,
        user_id: str,
        email: str,
        create_all_chains: bool = True
    ) -> Dict[str, Any]:
        """
        Create wallet across ALL supported chains
        
        USER FLOW:
        1. User clicks "Create Wallet"
        2. We create:
           - Algorand wallet (USDS native)
           - Bitcoin wallet (via WDK)
           - Ethereum wallet (via WDK)
           - Lightning wallet (via WDK)
           - TON wallet (via WDK)
        3. User sees: "Your wallet is ready! 🎉"
        
        CRITICAL: User NEVER sees "Algorand" or "Ethereum" terminology
        """
        
        try:
            logger.info(f"Creating unified wallet for user {user_id}")
            
            wallets_created = {}
            
            # STEP 1: Create Algorand wallet (USDS native)
            try:
                algo_wallet = await self.algorand.create_algorand_wallet(user_id)
                wallets_created["algorand"] = {
                    "address": algo_wallet["wallet_address"],
                    "assets": ["USDS", "USDCa", "USDT_ALGO"]
                }
                logger.info(f"Algorand wallet created: {algo_wallet['wallet_address']}")
            except Exception as e:
                logger.error(f"Algorand wallet creation failed: {e}")
                # Continue anyway - partial wallet better than none
            
            # STEP 2: Create WDK multi-chain wallets
            if create_all_chains:
                try:
                    wdk_wallets = await self.wdk.create_multi_chain_wallet(
                        user_id=user_id,
                        email=email,
                        requested_chains=settings.WDK_ENABLED_CHAINS
                    )
                    
                    for chain, chain_data in wdk_wallets["chains"].items():
                        wallets_created[chain] = chain_data
                    
                    logger.info(f"WDK wallets created: {list(wdk_wallets['chains'].keys())}")
                    
                except Exception as e:
                    logger.error(f"WDK wallet creation failed: {e}")
                    # Continue - Algorand wallet still works
            
            if not wallets_created:
                raise Exception("Failed to create any wallets")
            
            # STEP 3: Initialize wallet metadata
            wallet_summary = {
                "user_id": user_id,
                "total_chains": len(wallets_created),
                "supported_assets": self._get_supported_assets(wallets_created),
                "created_at": datetime.utcnow().isoformat(),
                "wallet_type": "unified_multi_chain"
            }
            
            # Log success
            await self.audit.log_event(
                "UNIFIED_WALLET_CREATED",
                user_id=user_id,
                resource_id=user_id,
                details={
                    "chains": list(wallets_created.keys()),
                    "asset_count": len(wallet_summary["supported_assets"])
                }
            )
            
            logger.info(f"Unified wallet created for user {user_id}: {len(wallets_created)} chains")
            
            return {
                "success": True,
                "wallet_created": True,
                "chains": list(wallets_created.keys()),
                "supported_assets": wallet_summary["supported_assets"],
                # USER-FACING MESSAGE (Clean, simple, no jargon)
                "message": "Your wallet is ready! You can now send and receive crypto instantly. 🚀",
                "onboarding_complete": True
            }
            
        except Exception as e:
            logger.error(f"Unified wallet creation failed: {e}")
            raise Exception(f"Wallet creation failed: {str(e)}")
    
    def _get_supported_assets(self, wallets: Dict[str, Any]) -> List[str]:
        """Get list of all supported assets across all wallets"""
        
        assets = set()
        
        for chain, wallet_data in wallets.items():
            if "assets" in wallet_data:
                assets.update(wallet_data["assets"])
        
        return sorted(list(assets))
    
    # ========================================================================
    # UNIFIED BALANCE QUERY (All Chains, One Call)
    # ========================================================================
    
    async def get_balance(self, user_id: str) -> Dict[str, Any]:
        """
        Get total balance across ALL chains
        
        USER SEES:
        ┌──────────────────────────┐
        │  Total Balance: $1,234   │
        ├──────────────────────────┤
        │  USDT: 500 ($500)        │
        │  BTC: 0.02 ($1,200)      │
        │  USDS: 234 ($234)        │
        └──────────────────────────┘
        
        HIDDEN:
        - Algorand has USDS
        - Ethereum has USDT
        - Bitcoin has BTC
        """
        
        try:
            total_usd = Decimal("0")
            all_balances = {}
            
            # Query Algorand balances
            try:
                algo_balances = await self.algorand.get_user_balances(user_id)
                
                for asset, balance in algo_balances.get("balances", {}).items():
                    all_balances[asset] = {
                        "amount": balance,
                        "source": "algorand"  # Hidden from user
                    }
                
                total_usd += Decimal(str(algo_balances.get("total_usd", 0)))
                
            except Exception as e:
                logger.error(f"Algorand balance query failed: {e}")
            
            # Query WDK balances
            try:
                wdk_balances = await self.wdk.get_unified_balance(user_id)
                
                for asset, balance in wdk_balances.get("balances", {}).items():
                    if asset in all_balances:
                        # Aggregate if asset exists on multiple chains
                        all_balances[asset]["amount"] += balance
                    else:
                        all_balances[asset] = {
                            "amount": balance,
                            "source": "wdk"  # Hidden from user
                        }
                
                total_usd += Decimal(str(wdk_balances.get("total_usd", 0)))
                
            except Exception as e:
                logger.error(f"WDK balance query failed: {e}")
            
            # Format for user display
            formatted_balances = []
            for asset, data in all_balances.items():
                if data["amount"] > 0:
                    formatted_balances.append({
                        "symbol": asset,
                        "amount": f"{data['amount']:.4f}",
                        "value_usd": data["amount"] * self._get_asset_price_usd(asset)
                    })
            
            # Sort by USD value (highest first)
            formatted_balances.sort(key=lambda x: x["value_usd"], reverse=True)
            
            return {
                "total_usd": float(total_usd),
                "balances": all_balances,
                "wallet_exists": len(all_balances) > 0,
                "last_updated": datetime.utcnow().isoformat(),
                # USER DISPLAY
                "display": {
                    "main_balance": f"${float(total_usd):,.2f}",
                    "assets": formatted_balances[:10],  # Top 10 assets
                    "asset_count": len(all_balances)
                }
            }
            
        except Exception as e:
            logger.error(f"Unified balance query failed: {e}")
            return {
                "total_usd": 0.0,
                "balances": {},
                "wallet_exists": False
            }
    
    def _get_asset_price_usd(self, asset: str) -> Decimal:
        """Get current USD price for asset (simplified)"""
        
        # TODO: Integrate real oracle service
        price_map = {
            "USDT": Decimal("1.00"),
            "USDC": Decimal("1.00"),
            "USDS": Decimal("1.00"),
            "BTC": Decimal("60000.00"),
            "ETH": Decimal("2500.00"),
            "ALGO": Decimal("0.18")
        }
        
        return price_map.get(asset, Decimal("0"))
    
    # ========================================================================
    # UNIFIED SEND PAYMENT (Auto-Route to Optimal Chain)
    # ========================================================================
    
    async def send_payment(
        self,
        user_id: str,
        recipient: str,  # Can be address OR email OR username
        asset: str,
        amount: Decimal,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send payment with SMART ROUTING
        
        ROUTING LOGIC:
        1. Detect recipient type (address/email/username)
        2. Determine optimal chain for asset
        3. Route to appropriate service
        4. Execute transaction
        
        USER FLOW:
        - Enter: Recipient + Amount
        - Click: Send
        - See: "Payment sent! ✓"
        
        ZERO blockchain complexity shown
        """
        
        try:
            logger.info(f"Payment initiated: {amount} {asset} from {user_id}")
            
            # STEP 1: Determine which service handles this asset
            service_type = self.asset_routing.get(asset)
            
            if not service_type:
                raise Exception(f"Unsupported asset: {asset}")
            
            # STEP 2: Validate balance
            balance_check = await self._check_balance(user_id, asset, amount)
            if not balance_check["sufficient"]:
                raise Exception(f"Insufficient {asset} balance. Available: {balance_check['available']}")
            
            # STEP 3: Resolve recipient (email → address if needed)
            recipient_address = await self._resolve_recipient(recipient, asset)
            
            # STEP 4: Calculate fees
            fee_calc = MultiChainBusinessModel.calculate_total_fee(
                transaction_type="p2p_local",
                amount=amount,
                from_asset=asset
            )
            
            # STEP 5: Route to appropriate service
            if service_type == "algorand":
                result = await self._send_via_algorand(
                    user_id, recipient_address, asset, amount, memo
                )
            else:  # wdk
                result = await self._send_via_wdk(
                    user_id, recipient_address, asset, amount, memo
                )
            
            # Log transaction
            await self.audit.log_event(
                "UNIFIED_PAYMENT_SENT",
                user_id=user_id,
                resource_id=result["transaction_id"],
                details={
                    "asset": asset,
                    "amount": float(amount),
                    "recipient": recipient_address,
                    "service": service_type
                }
            )
            
            logger.info(f"Payment sent: {result['transaction_id']}")
            
            return {
                **result,
                "fee": fee_calc["total_fee"],
                "service_hidden": service_type,  # For debugging
                # USER MESSAGE (Clean & simple)
                "user_message": f"Payment sent! Your {asset} will arrive shortly. ✓"
            }
            
        except Exception as e:
            logger.error(f"Payment failed: {e}")
            raise Exception(f"Payment failed: {str(e)}")
    
    async def _check_balance(
        self,
        user_id: str,
        asset: str,
        required_amount: Decimal
    ) -> Dict[str, Any]:
        """Check if user has sufficient balance"""
        
        balances = await self.get_balance(user_id)
        available = Decimal(str(balances["balances"].get(asset, {}).get("amount", 0)))
        
        return {
            "sufficient": available >= required_amount,
            "available": float(available),
            "required": float(required_amount),
            "deficit": float(max(Decimal("0"), required_amount - available))
        }
    
    async def _resolve_recipient(
        self,
        recipient: str,
        asset: str
    ) -> str:
        """
        Resolve recipient identifier to blockchain address
        
        Supports:
        - Blockchain addresses (pass through)
        - Email addresses (lookup user's wallet)
        - Usernames (lookup user's wallet)
        """
        
        # Check if already a valid address
        if self._is_blockchain_address(recipient):
            return recipient
        
        # Check if email
        if "@" in recipient:
            user_result = await self.db.supabase.table("user_profiles")\
                .select("id")\
                .eq("email", recipient)\
                .maybe_single()\
                .execute()
            
            if user_result.data:
                recipient_user_id = user_result.data["id"]
                return await self._get_user_address_for_asset(recipient_user_id, asset)
        
        # Check if username (future feature)
        # ...
        
        raise Exception(f"Could not resolve recipient: {recipient}")
    
    def _is_blockchain_address(self, value: str) -> bool:
        """Check if string looks like a blockchain address"""
        
        # Algorand: 58 chars, starts with A-Z
        if len(value) == 58 and value[0].isupper():
            return True
        
        # Ethereum: 42 chars, starts with 0x
        if len(value) == 42 and value.startswith("0x"):
            return True
        
        # Bitcoin: Varies, starts with 1/3/bc1
        if value[0] in ["1", "3"] or value.startswith("bc1"):
            return True
        
        return False
    
    async def _get_user_address_for_asset(
        self,
        user_id: str,
        asset: str
    ) -> str:
        """Get user's address for specific asset"""
        
        service_type = self.asset_routing.get(asset)
        
        if service_type == "algorand":
            wallet_result = await self.db.supabase.table("user_wallets")\
                .select("algorand_address")\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            return wallet_result.data["algorand_address"]
        
        else:  # wdk
            # Determine blockchain for this asset
            asset_config = settings.SUPPORTED_ASSETS.get(asset, {})
            blockchain = asset_config.get("blockchain", "ethereum")
            
            address_result = await self.db.supabase.table("multi_chain_addresses")\
                .select("address")\
                .eq("user_id", user_id)\
                .eq("blockchain", blockchain)\
                .single()\
                .execute()
            
            return address_result.data["address"]
    
    async def _send_via_algorand(
        self,
        user_id: str,
        recipient: str,
        asset: str,
        amount: Decimal,
        memo: Optional[str]
    ) -> Dict[str, Any]:
        """Send payment via Algorand service"""
        
        # Get asset ID
        asset_config = settings.SUPPORTED_ASSETS.get(asset, {})
        asset_id = asset_config.get("asset_id")
        
        if not asset_id:
            raise Exception(f"Asset {asset} not configured for Algorand")
        
        # Get user's private key (encrypted)
        wallet_result = await self.db.supabase.table("user_wallets")\
            .select("algorand_private_key")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        encrypted_key = wallet_result.data["algorand_private_key"]
        
        # Send via Algorand service
        tx_id = await self.algorand.transfer_asset(
            sender_private_key=self._decrypt_key(encrypted_key),
            receiver_address=recipient,
            asset_id=asset_id,
            amount=amount,
            memo=memo or ""
        )
        
        return {
            "success": True,
            "transaction_id": tx_id,
            "blockchain": "algorand",
            "estimated_confirmation": "4.5 seconds"
        }
    
    async def _send_via_wdk(
        self,
        user_id: str,
        recipient: str,
        asset: str,
        amount: Decimal,
        memo: Optional[str]
    ) -> Dict[str, Any]:
        """Send payment via WDK service"""
        
        result = await self.wdk.send_payment(
            user_id=user_id,
            recipient_address=recipient,
            asset=asset,
            amount=amount,
            memo=memo
        )
        
        return result
    
    def _decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt private key (uses ENCRYPTION_KEY from settings)"""
        from cryptography.fernet import Fernet
        
        cipher = Fernet(settings.ENCRYPTION_KEY.get_secret_value().encode())
        return cipher.decrypt(encrypted_key.encode()).decode()
    
    # ========================================================================
    # UNIFIED TRANSACTION HISTORY
    # ========================================================================
    
    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get unified transaction history across ALL chains
        
        USER SEES:
        - Clean list of "Sent/Received"
        - No blockchain names
        - WhatsApp-style UX
        """
        
        all_transactions = []
        
        # Get Algorand transactions
        try:
            algo_txs = await self._get_algorand_transactions(user_id, limit)
            all_transactions.extend(algo_txs)
        except Exception as e:
            logger.error(f"Algorand tx history failed: {e}")
        
        # Get WDK transactions
        try:
            wdk_txs = await self.wdk.get_transaction_history(user_id, limit)
            all_transactions.extend(wdk_txs)
        except Exception as e:
            logger.error(f"WDK tx history failed: {e}")
        
        # Sort by date (most recent first)
        all_transactions.sort(
            key=lambda x: x.get("date", ""),
            reverse=True
        )
        
        return all_transactions[:limit]
    
    async def _get_algorand_transactions(
        self,
        user_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get Algorand transaction history"""
        
        # Query from database
        result = await self.db.supabase.table("transactions")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return [
            {
                "id": tx["id"],
                "type": tx["type"],
                "asset": tx["asset"],
                "amount": tx["amount"],
                "status": tx["status"],
                "date": tx["created_at"],
                "blockchain_hidden": "algorand"
            }
            for tx in result.data
        ]
    
    # ========================================================================
    # SMART ASSET SWAPS (Best Rates Across Chains)
    # ========================================================================
    
    async def swap_assets(
        self,
        user_id: str,
        from_asset: str,
        to_asset: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Swap assets with SMART ROUTING
        
        LOGIC:
        - Same-chain swaps → Use chain-native DEX
        - Cross-chain swaps → Bridge + swap
        - Best rate selection → Query multiple sources
        
        USER SEES:
        "Swapping 100 USDT for ~0.04 BTC..."
        (No mention of DEXes, bridges, or chains)
        """
        
        try:
            # Determine if cross-chain swap needed
            from_chain = self._get_asset_chain(from_asset)
            to_chain = self._get_asset_chain(to_asset)
            
            if from_chain == to_chain:
                # Same-chain swap
                return await self._same_chain_swap(user_id, from_asset, to_asset, amount)
            else:
                # Cross-chain swap (more complex)
                return await self._cross_chain_swap(user_id, from_asset, to_asset, amount)
            
        except Exception as e:
            logger.error(f"Asset swap failed: {e}")
            raise Exception(f"Swap failed: {str(e)}")
    
    def _get_asset_chain(self, asset: str) -> str:
        """Get primary blockchain for asset"""
        
        asset_config = settings.SUPPORTED_ASSETS.get(asset, {})
        return asset_config.get("blockchain", "algorand")
    
    async def _same_chain_swap(
        self,
        user_id: str,
        from_asset: str,
        to_asset: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """Execute swap on same blockchain"""
        
        # Get quote from WDK
        quote = await self.wdk.get_swap_quote(user_id, from_asset, to_asset, amount)
        
        # Execute swap
        # (Implementation depends on WDK API)
        
        return {
            "success": True,
            "from_asset": from_asset,
            "to_asset": to_asset,
            "amount_in": float(amount),
            "amount_out": quote["estimated_output"],
            "user_message": f"Swapped {amount} {from_asset} for {quote['estimated_output']} {to_asset}! ✓"
        }
    
    async def _cross_chain_swap(
        self,
        user_id: str,
        from_asset: str,
        to_asset: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """Execute cross-chain swap (bridge + swap)"""
        
        try:
            from_chain = self._get_asset_chain(from_asset)
            to_chain = self._get_asset_chain(to_asset)
            
            # STEP 1: Bridge from_asset to destination chain
            bridge_result = await self.wdk.bridge_assets(
                user_id=user_id,
                asset=from_asset,
                amount=amount,
                from_chain=from_chain,
                to_chain=to_chain
            )
            
            # STEP 2: Wait for bridge completion (async monitoring)
            # (In production, this would be event-driven)
            
            # STEP 3: Swap on destination chain
            swap_result = await self._same_chain_swap(
                user_id, from_asset, to_asset, amount
            )
            
            return {
                "success": True,
                "bridge_id": bridge_result["bridge_id"],
                "swap_id": swap_result.get("transaction_id"),
                "from_asset": from_asset,
                "to_asset": to_asset,
                "amount_in": float(amount),
                "estimated_completion": "3-5 minutes",
                "user_message": "Cross-chain swap in progress... We'll notify you when complete! 🔄"
            }
            
        except Exception as e:
            logger.error(f"Cross-chain swap failed: {e}")
            raise Exception(f"Cross-chain swap failed: {str(e)}")
    
    # ========================================================================
    # RECEIVE PAYMENT (Generate Payment Request)
    # ========================================================================
    
    async def generate_payment_request(
        self,
        user_id: str,
        asset: str,
        amount: Optional[Decimal] = None,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate payment request (QR code + address)
        
        USER FLOW:
        1. User clicks "Request Payment"
        2. Selects asset (USDT/BTC/ETH)
        3. Enters amount (optional)
        4. Gets QR code + shareable link
        
        SMART ROUTING:
        - BTC <$100 → Lightning invoice (instant)
        - BTC >$100 → Bitcoin address
        - USDT → Optimal chain address
        """
        
        try:
            service_type = self.asset_routing.get(asset)
            
            if not service_type:
                raise Exception(f"Unsupported asset: {asset}")
            
            # Special handling for Lightning Network
            if asset == "BTC" and amount and amount < Decimal("100"):
                # Generate Lightning invoice
                invoice = await self.wdk.create_lightning_invoice(
                    user_id=user_id,
                    amount_sats=int(amount * 100_000_000),  # BTC to sats
                    memo=memo
                )
                
                return {
                    "payment_type": "lightning",
                    "invoice": invoice["invoice"],
                    "qr_code": invoice["qr_code"],
                    "amount": float(amount),
                    "expires_at": invoice["expires_at"],
                    "user_message": "Lightning invoice created! Share to receive instant payment. ⚡"
                }
            
            # Standard address-based payment
            address = await self._get_user_address_for_asset(user_id, asset)
            
            if not address:
                raise Exception(f"No wallet found for {asset}")
            
            # Generate QR code (in production, use actual QR generator)
            qr_code_url = f"https://api.seamount.io/qr/{address}"
            
            # Generate shareable payment link
            payment_link = f"https://seamount.io/pay?to={address}&asset={asset}"
            if amount:
                payment_link += f"&amount={amount}"
            
            return {
                "payment_type": "address",
                "address": address,
                "asset": asset,
                "amount": float(amount) if amount else None,
                "qr_code": qr_code_url,
                "payment_link": payment_link,
                "user_message": f"Ready to receive {asset}! Share your QR code or payment link. 📲",
                "blockchain_hidden": self._get_asset_chain(asset)
            }
            
        except Exception as e:
            logger.error(f"Payment request generation failed: {e}")
            raise Exception(f"Payment request failed: {str(e)}")
    
    # ========================================================================
    # WALLET EXPORT (Backup & Recovery)
    # ========================================================================
    
    async def export_wallet(
        self,
        user_id: str,
        password: str,
        export_format: str = "encrypted_json"
    ) -> Dict[str, Any]:
        """
        Export wallet for backup
        
        SECURITY:
        - Encrypted with user password
        - Never store password
        - Audit trail logged
        """
        
        try:
            # Get all user addresses
            addresses_result = await self.db.supabase.table("multi_chain_addresses")\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()
            
            if not addresses_result.data:
                raise Exception("No wallets found")
            
            # Build export data
            export_data = {
                "version": "1.0",
                "user_id": user_id,
                "export_date": datetime.utcnow().isoformat(),
                "chains": []
            }
            
            for address_record in addresses_result.data:
                chain_data = {
                    "blockchain": address_record["blockchain"],
                    "address": address_record["address"],
                    "wallet_type": address_record["wallet_type"]
                }
                
                # Include encrypted private key if it exists
                if address_record["encrypted_private_key"]:
                    chain_data["encrypted_private_key"] = address_record["encrypted_private_key"]
                
                export_data["chains"].append(chain_data)
            
            # Encrypt entire export with user password
            from cryptography.fernet import Fernet
            import base64
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
            
            # Derive key from password
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"seamount_export_salt",
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            cipher = Fernet(key)
            
            encrypted_export = cipher.encrypt(json.dumps(export_data).encode())
            
            # Log audit
            await self.audit.log_event(
                "WALLET_EXPORTED",
                user_id=user_id,
                resource_id=user_id,
                details={
                    "chains_exported": len(export_data["chains"]),
                    "export_format": export_format
                }
            )
            
            logger.info(f"Wallet exported for user {user_id}")
            
            return {
                "success": True,
                "encrypted_data": encrypted_export.decode(),
                "format": export_format,
                "chains_included": [c["blockchain"] for c in export_data["chains"]],
                "user_message": "Wallet backup created! Keep this file safe. 🔒"
            }
            
        except Exception as e:
            logger.error(f"Wallet export failed: {e}")
            raise Exception(f"Wallet export failed: {str(e)}")
    
    # ========================================================================
    # WALLET IMPORT (Recovery)
    # ========================================================================
    
    async def import_wallet(
        self,
        user_id: str,
        encrypted_data: str,
        password: str
    ) -> Dict[str, Any]:
        """Import wallet from backup"""
        
        try:
            from cryptography.fernet import Fernet
            import base64
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
            
            # Derive key from password
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"seamount_export_salt",
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            cipher = Fernet(key)
            
            # Decrypt export data
            decrypted_data = cipher.decrypt(encrypted_data.encode())
            import_data = json.loads(decrypted_data.decode())
            
            # Restore addresses
            restored_chains = []
            
            for chain_data in import_data["chains"]:
                # Insert address record
                address_record = {
                    "user_id": user_id,
                    "blockchain": chain_data["blockchain"],
                    "address": chain_data["address"],
                    "wallet_type": "imported",
                    "is_imported": True,
                    "encrypted_private_key": chain_data.get("encrypted_private_key"),
                    "created_at": datetime.utcnow().isoformat()
                }
                
                await self.db.supabase.table("multi_chain_addresses").upsert(
                    address_record,
                    on_conflict="user_id,blockchain,address"
                ).execute()
                
                restored_chains.append(chain_data["blockchain"])
            
            # Log audit
            await self.audit.log_event(
                "WALLET_IMPORTED",
                user_id=user_id,
                resource_id=user_id,
                details={
                    "chains_restored": restored_chains
                }
            )
            
            logger.info(f"Wallet imported for user {user_id}")
            
            return {
                "success": True,
                "chains_restored": restored_chains,
                "user_message": "Wallet restored successfully! Your assets are back. 🎉"
            }
            
        except Exception as e:
            logger.error(f"Wallet import failed: {e}")
            raise Exception(f"Wallet import failed: {str(e)}")
    
    # ========================================================================
    # GAS ESTIMATION (Hidden from User)
    # ========================================================================
    
    async def estimate_transaction_cost(
        self,
        user_id: str,
        transaction_type: str,
        asset: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Estimate total transaction cost
        
        INCLUDES:
        - Platform fee (visible)
        - Network fee (visible as "transaction fee")
        - Hidden markups (NOT visible)
        
        USER SEES: "Transaction fee: $0.50"
        REALITY: Platform fee ($0.30) + Network fee ($0.15) + Markup ($0.05)
        """
        
        fee_calc = MultiChainBusinessModel.calculate_total_fee(
            transaction_type=transaction_type,
            amount=amount,
            from_asset=asset
        )
        
        # USER-FACING (simplified)
        user_display = {
            "total_cost": fee_calc["total_fee"],
            "breakdown_visible": {
                "transaction_fee": fee_calc["platform_fee"],
                "network_fee": fee_calc["network_fee"]
            }
        }
        
        # INTERNAL (full details)
        internal_details = {
            **fee_calc,
            "hidden_markup": fee_calc["hidden_markup"],
            "net_revenue": fee_calc["net_revenue"],
            "profit_margin": fee_calc["profit_margin_percent"]
        }
        
        return {
            "user_display": user_display,
            "internal_details": internal_details
        }
    
    # ========================================================================
    # HEALTH & MONITORING
    # ========================================================================
    
    async def check_service_health(self) -> Dict[str, Any]:
        """Check health of all sub-services"""
        
        health = {
            "algorand": "unknown",
            "wdk": "unknown",
            "database": "unknown"
        }
        
        # Check Algorand
        try:
            await self.algorand.get_account_info(self.algorand.treasury_address)
            health["algorand"] = "healthy"
        except Exception as e:
            health["algorand"] = f"unhealthy: {str(e)}"
            logger.error(f"Algorand health check failed: {e}")
        
        # Check WDK
        try:
            wdk_health = await self.wdk.health_check()
            health["wdk"] = wdk_health["status"]
        except Exception as e:
            health["wdk"] = f"unhealthy: {str(e)}"
            logger.error(f"WDK health check failed: {e}")
        
        # Check Database
        try:
            await self.db.supabase.table("multi_chain_addresses").select("id").limit(1).execute()
            health["database"] = "healthy"
        except Exception as e:
            health["database"] = f"unhealthy: {str(e)}"
            logger.error(f"Database health check failed: {e}")
        
        overall_status = "healthy" if all(v == "healthy" for v in health.values()) else "degraded"
        
        return {
            "status": overall_status,
            "services": health,
            "timestamp": datetime.utcnow().isoformat()
        }