# File: backend/services/payment_providers/harbor.py
"""
Harbor (OwlPay) Payment Provider - Multi-Chain Crypto Gateway
Supports: Ethereum, Polygon, Solana, Bitcoin, Tron
"""

import logging
import aiohttp
import hmac
import hashlib
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)

class HarborProvider:
    """
    Harbor API client for multi-chain crypto payments
    Sandbox: https://sandbox.harbor.owlpay.com/v1
    Production: https://api.harbor.owlpay.com/v1
    """
    
    # Supported blockchains
    SUPPORTED_CHAINS = ['ethereum', 'polygon', 'solana', 'bitcoin', 'tron']
    
    # Chain name mapping (Harbor uses different names)
    CHAIN_MAP = {
        'ethereum': 'ethereum',
        'polygon': 'polygon',
        'solana': 'solana',
        'bitcoin': 'bitcoin',
        'tron': 'tron'
    }
    
    def __init__(self, settings):
        self.settings = settings
        
        # 🚨 CRITICAL: Use sandbox key from your env
        self.api_key = settings.HARBOR_API_KEY
        self.webhook_secret = settings.HARBOR_WEBHOOK_SECRET
        
        # Environment selection
        self.is_sandbox = not settings.HARBOR_API_KEY.startswith('pk_live_')
        
        if self.is_sandbox:
            self.base_url = "https://sandbox-api.harbor.owlpay.com/v1"
            logger.info("🟡 Harbor: Using SANDBOX environment")
        else:
            self.base_url = "https://api.harbor.owlpay.com/v1"
            logger.info("🟢 Harbor: Using PRODUCTION environment")
        
        logger.info(f"✅ Harbor initialized: {self.api_key[:15]}...")
    
    # ========================================================================
    # CORE API METHODS
    # ========================================================================
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Harbor API"""
        
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Harbor-Version": "2024-01-01"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(
                        url, 
                        headers=headers, 
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        response_data = await response.json()
                        
                        if response.status >= 400:
                            logger.error(f"❌ Harbor API error {response.status}: {response_data}")
                            return {
                                "success": False,
                                "error": response_data.get("message", "Harbor API error"),
                                "status_code": response.status
                            }
                        
                        return response_data
                
                else:  # POST, PUT, PATCH
                    async with session.request(
                        method,
                        url,
                        json=data,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        response_data = await response.json()
                        
                        if response.status >= 400:
                            logger.error(f"❌ Harbor API error {response.status}: {response_data}")
                            return {
                                "success": False,
                                "error": response_data.get("message", "Harbor API error"),
                                "status_code": response.status
                            }
                        
                        return response_data
        
        except aiohttp.ClientError as e:
            logger.error(f"❌ Harbor request failed: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========================================================================
    # ON-RAMP (Fiat → Crypto)
    # ========================================================================
    
    async def initialize_onramp(
        self,
        amount_fiat: Decimal,
        currency: str,
        crypto_asset: str,
        blockchain: str,
        wallet_address: str,
        user_email: str,
        tx_ref: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Initialize fiat → crypto on-ramp via Harbor
        
        Args:
            amount_fiat: Amount in fiat currency (e.g., 100.00 USD)
            currency: Fiat currency code (USD, EUR, GBP, etc.)
            crypto_asset: Crypto to receive (BTC, ETH, USDT, etc.)
            blockchain: Target blockchain (ethereum, polygon, solana, etc.)
            wallet_address: User's destination wallet address
            user_email: User's email for Harbor account
            tx_ref: Your internal transaction reference
            metadata: Additional data to attach
        
        Returns:
            {
                "success": True,
                "payment_id": "harbor_pay_xxx",
                "checkout_url": "https://checkout.harbor.owlpay.com/...",
                "estimated_crypto": "0.0001234",
                "expires_at": "2025-01-16T..."
            }
        """
        
        if blockchain not in self.SUPPORTED_CHAINS:
            return {
                "success": False,
                "error": f"Blockchain {blockchain} not supported by Harbor"
            }
        
        logger.info(
            f"💳 Harbor On-Ramp: {amount_fiat} {currency} → "
            f"{crypto_asset} on {blockchain}"
        )
        
        payload = {
            "type": "onramp",
            "amount": float(amount_fiat),
            "currency": currency.upper(),
            "crypto_currency": crypto_asset.upper(),
            "blockchain": self.CHAIN_MAP[blockchain],
            "destination_address": wallet_address,
            "customer": {
                "email": user_email
            },
            "reference": tx_ref,
            "callback_url": self.settings.HARBOR_WEBHOOK_URL,
            "metadata": metadata or {}
        }
        
        result = await self._make_request("POST", "/payments/onramp", data=payload)
        
        if result.get("id"):
            logger.info(f"✅ Harbor on-ramp created: {result['id']}")
            return {
                "success": True,
                "payment_id": result["id"],
                "checkout_url": result.get("checkout_url"),
                "estimated_crypto": result.get("estimated_crypto_amount"),
                "expires_at": result.get("expires_at"),
                "status": result.get("status", "pending")
            }
        
        logger.error(f"❌ Harbor on-ramp failed: {result}")
        return result
    
    # ========================================================================
    # OFF-RAMP (Crypto → Fiat)
    # ========================================================================
    
    async def initialize_offramp(
        self,
        crypto_amount: Decimal,
        crypto_asset: str,
        blockchain: str,
        fiat_currency: str,
        bank_details: Dict[str, str],
        user_email: str,
        tx_ref: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Initialize crypto → fiat off-ramp via Harbor
        
        Args:
            crypto_amount: Amount of crypto to sell
            crypto_asset: Crypto to sell (BTC, ETH, USDT, etc.)
            blockchain: Source blockchain
            fiat_currency: Target fiat currency
            bank_details: {
                "account_number": "...",
                "account_name": "...",
                "bank_code": "...",
                "country": "NG"
            }
            user_email: User's email
            tx_ref: Your internal reference
            metadata: Additional data
        
        Returns:
            {
                "success": True,
                "payment_id": "harbor_payout_xxx",
                "deposit_address": "0x...",  # Where user sends crypto
                "estimated_fiat": "5000.00",
                "status": "awaiting_deposit"
            }
        """
        
        if blockchain not in self.SUPPORTED_CHAINS:
            return {
                "success": False,
                "error": f"Blockchain {blockchain} not supported"
            }
        
        logger.info(
            f"💸 Harbor Off-Ramp: {crypto_amount} {crypto_asset} → "
            f"{fiat_currency} via {blockchain}"
        )
        
        payload = {
            "type": "offramp",
            "crypto_amount": float(crypto_amount),
            "crypto_currency": crypto_asset.upper(),
            "blockchain": self.CHAIN_MAP[blockchain],
            "fiat_currency": fiat_currency.upper(),
            "customer": {
                "email": user_email
            },
            "bank_account": bank_details,
            "reference": tx_ref,
            "callback_url": self.settings.HARBOR_WEBHOOK_URL,
            "metadata": metadata or {}
        }
        
        result = await self._make_request("POST", "/payments/offramp", data=payload)
        
        if result.get("id"):
            logger.info(f"✅ Harbor off-ramp created: {result['id']}")
            return {
                "success": True,
                "payment_id": result["id"],
                "deposit_address": result.get("deposit_address"),
                "estimated_fiat": result.get("estimated_fiat_amount"),
                "status": result.get("status", "awaiting_deposit")
            }
        
        logger.error(f"❌ Harbor off-ramp failed: {result}")
        return result
    
    # ========================================================================
    # CRYPTO TRANSFER (Wallet → Wallet)
    # ========================================================================
    
    async def send_crypto(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
        asset: str,
        blockchain: str,
        private_key: Optional[str] = None,
        tx_ref: str = None
    ) -> Dict[str, Any]:
        """
        Send crypto via Harbor (custodial or non-custodial)
        
        Args:
            from_address: Source wallet address
            to_address: Destination address
            amount: Amount to send
            asset: Asset symbol (ETH, USDT, SOL, etc.)
            blockchain: Blockchain network
            private_key: Optional (for non-custodial mode)
            tx_ref: Your internal reference
        
        Returns:
            {
                "success": True,
                "transaction_hash": "0x...",
                "status": "pending"
            }
        """
        
        if blockchain not in self.SUPPORTED_CHAINS:
            return {
                "success": False,
                "error": f"Blockchain {blockchain} not supported"
            }
        
        logger.info(
            f"🔄 Harbor Transfer: {amount} {asset} on {blockchain} "
            f"from {from_address[:10]}... to {to_address[:10]}..."
        )
        
        payload = {
            "from_address": from_address,
            "to_address": to_address,
            "amount": float(amount),
            "asset": asset.upper(),
            "blockchain": self.CHAIN_MAP[blockchain],
            "reference": tx_ref or f"harbor_tx_{int(datetime.now().timestamp())}"
        }
        
        # Non-custodial mode: include private key (encrypted in transit)
        if private_key:
            payload["signing_key"] = private_key
        
        result = await self._make_request("POST", "/transfers", data=payload)
        
        if result.get("transaction_hash"):
            logger.info(f"✅ Harbor transfer submitted: {result['transaction_hash']}")
            return {
                "success": True,
                "transaction_hash": result["transaction_hash"],
                "status": result.get("status", "pending")
            }
        
        logger.error(f"❌ Harbor transfer failed: {result}")
        return result
    
    # ========================================================================
    # BALANCE QUERY
    # ========================================================================
    
    async def get_balance(
        self,
        address: str,
        blockchain: str,
        asset: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query balance via Harbor indexer
        
        Args:
            address: Wallet address
            blockchain: Blockchain network
            asset: Optional asset symbol (native if not specified)
        
        Returns:
            {
                "success": True,
                "balance": "1.234567",
                "asset": "ETH",
                "blockchain": "ethereum"
            }
        """
        
        if blockchain not in self.SUPPORTED_CHAINS:
            return {
                "success": False,
                "error": f"Blockchain {blockchain} not supported"
            }
        
        params = {
            "address": address,
            "blockchain": self.CHAIN_MAP[blockchain]
        }
        
        if asset:
            params["asset"] = asset.upper()
        
        result = await self._make_request("GET", "/balances", params=params)
        
        if result.get("balance") is not None:
            logger.info(
                f"✅ Harbor balance: {result['balance']} "
                f"{result.get('asset', 'native')} on {blockchain}"
            )
            return {
                "success": True,
                "balance": str(result["balance"]),
                "asset": result.get("asset"),
                "blockchain": blockchain
            }
        
        logger.warning(f"⚠️ Harbor balance query failed: {result}")
        return result
    
    # ========================================================================
    # TRANSACTION STATUS
    # ========================================================================
    
    async def get_transaction_status(
        self,
        payment_id: str
    ) -> Dict[str, Any]:
        """
        Check transaction status via Harbor
        
        Args:
            payment_id: Harbor payment ID
        
        Returns:
            {
                "success": True,
                "status": "completed",
                "transaction_hash": "0x...",
                "amount": "100.00",
                "completed_at": "2025-01-16T..."
            }
        """
        
        result = await self._make_request("GET", f"/payments/{payment_id}")
        
        if result.get("id"):
            logger.info(f"✅ Harbor status: {result['status']} for {payment_id}")
            return {
                "success": True,
                "status": result["status"],
                "transaction_hash": result.get("transaction_hash"),
                "amount": result.get("amount"),
                "completed_at": result.get("completed_at")
            }
        
        logger.error(f"❌ Harbor status check failed: {result}")
        return result
    
    # ========================================================================
    # WEBHOOK VERIFICATION
    # ========================================================================
    
    def verify_webhook_signature(
        self,
        payload: str,
        signature: str
    ) -> bool:
        """
        Verify Harbor webhook signature
        
        Args:
            payload: Raw webhook payload (string)
            signature: X-Harbor-Signature header value
        
        Returns:
            True if signature is valid
        """
        
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            if is_valid:
                logger.info("✅ Harbor webhook signature valid")
            else:
                logger.error("❌ Harbor webhook signature INVALID")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ Webhook verification failed: {e}")
            return False
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def is_chain_supported(self, blockchain: str) -> bool:
        """Check if blockchain is supported"""
        return blockchain.lower() in self.SUPPORTED_CHAINS
    
    async def get_supported_assets(
        self,
        blockchain: str
    ) -> Dict[str, Any]:
        """Get list of supported assets for a blockchain"""
        
        result = await self._make_request(
            "GET",
            f"/assets/{self.CHAIN_MAP[blockchain]}"
        )
        
        if result.get("assets"):
            logger.info(f"✅ Harbor supports {len(result['assets'])} assets on {blockchain}")
            return {
                "success": True,
                "assets": result["assets"]
            }
        
        return result