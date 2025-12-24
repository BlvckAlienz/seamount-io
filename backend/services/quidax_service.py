# backend/services/quidax_service.py
"""
Quidax API Integration Service
Handles instant orders, withdrawals, and webhook verification
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, Tuple
from uuid import uuid4

import requests
from supabase import Client

logger = logging.getLogger(__name__)


class QuidaxService:
    """
    Quidax API Service for on/off-ramp operations
    
    Supported operations:
    - Get market quotes (buy/sell crypto)
    - Create instant orders (execute trades)
    - Confirm instant orders
    - Withdraw crypto to external wallet
    - Verify webhook signatures
    """
    
    BASE_URL = "https://app.quidax.io/api/v1"
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.secret_key = os.getenv("QUIDAX_SECRET_KEY")
        self.webhook_secret = os.getenv("QUIDAX_WEBHOOK_SECRET")
        
        if not self.secret_key:
            logger.error("❌ QUIDAX_SECRET_KEY not configured")
            raise ValueError("QUIDAX_SECRET_KEY not found in environment")
        
        # ✅ ADDED: Warn if webhook secret missing (won't break API calls, but webhooks will fail)
        if not self.webhook_secret:
            logger.warning("⚠️ QUIDAX_WEBHOOK_SECRET not configured - webhook signature verification will fail!")
    
    # ========================================================================
    # AUTHENTICATION
    # ========================================================================
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authenticated request headers"""
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    # ========================================================================
    # MARKET DATA
    # ========================================================================
    
    async def get_markets(self) -> Dict:
        """Get list of all available markets"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/markets",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Failed to fetch markets: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_ticker(self, market: str) -> Dict:
        """
        Get current ticker for a market
        
        Args:
            market: Market pair (e.g., 'usdtngn', 'btcngn')
        """
        try:
            # ✅ Quidax API uses /markets/tickers/{market_id} (plural 'tickers')
            response = requests.get(
                f"{self.BASE_URL}/markets/tickers/{market}",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            raw_data = response.json()
            
            # 🚨 CRITICAL: Quidax wraps ticker in "data" object
            ticker_data = raw_data.get("data", {}).get("ticker", {})
            
            # 🚨 CRITICAL: Quidax uses "buy"/"sell" (not "bid"/"ask")
            return {
                "success": True,
                "market": market,
                "bid": float(ticker_data.get("buy", 0)),      # buy = bid price
                "ask": float(ticker_data.get("sell", 0)),     # sell = ask price
                "last": float(ticker_data.get("last", 0)),
                "volume": float(ticker_data.get("vol", 0)),   # "vol" not "volume"
                "high": float(ticker_data.get("high", 0)),
                "low": float(ticker_data.get("low", 0)),
                "open": float(ticker_data.get("open", 0))
            }
        except Exception as e:
            logger.error(f"❌ Failed to fetch ticker for {market}: {e}")
            return {"success": False, "error": str(e)}
    
    # ========================================================================
    # QUOTES & PRICING
    # ========================================================================
    
    async def get_quote(
        self,
        user_id: str,
        market: str,
        quote_type: str,  # 'buy' or 'sell'
        amount: float,
        amount_type: str = "fiat"  # 'fiat' or 'crypto'
    ) -> Dict:
        """
        Get instant order quote
        
        Args:
            user_id: Seamount user ID
            market: Market pair (e.g., 'usdtngn')
            quote_type: 'buy' (NGN → crypto) or 'sell' (crypto → NGN)
            amount: Amount in fiat or crypto
            amount_type: 'fiat' (amount in NGN) or 'crypto' (amount in crypto)
        
        Returns:
            {
                "success": True,
                "quote_reference": "quote_xxx",
                "market": "usdtngn",
                "unit_price": 1650.50,
                "crypto_amount": 10.0,
                "fiat_amount": 16505.00,
                "fee": 165.05,
                "total": 16670.05,
                "expires_at": "2025-01-01T12:05:00Z"
            }
        """
        try:
            # Get current ticker
            ticker = await self.get_ticker(market)
            if not ticker.get("success"):
                return ticker
            
            # Calculate quote based on type
            if quote_type == "buy":
                unit_price = ticker["ask"]  # Buy at ask price
                fee_rate = 0.01  # 1% fee (Quidax default, verify actual rate)
            else:  # sell
                unit_price = ticker["bid"]  # Sell at bid price
                fee_rate = 0.01
            
            # Calculate amounts
            if amount_type == "fiat":
                fiat_amount = float(amount)
                crypto_amount = fiat_amount / unit_price
            else:  # crypto
                crypto_amount = float(amount)
                fiat_amount = crypto_amount * unit_price
            
            # Calculate fee
            fee = fiat_amount * fee_rate
            total = fiat_amount + fee if quote_type == "buy" else fiat_amount - fee
            
            # Generate quote reference
            quote_reference = f"quote_{uuid4().hex[:12]}"
            
            # Store quote in database (expires in 5 minutes)
            expires_at = datetime.utcnow() + timedelta(minutes=5)
            
            quote_data = {
                "user_id": user_id,
                "market": market,
                "quote_type": quote_type,
                "fiat_amount": float(fiat_amount),
                "crypto_amount": float(crypto_amount),
                "unit_price": float(unit_price),
                "quidax_fee": float(fee),
                "total_amount": float(total),
                "expires_at": expires_at.isoformat(),
                "quote_reference": quote_reference
            }
            
            self.supabase.table("quidax_quotes").insert(quote_data).execute()
            
            logger.info(f"✅ Generated quote {quote_reference} for user {user_id[:8]}...")
            
            return {
                "success": True,
                "quote_reference": quote_reference,
                "market": market,
                "quote_type": quote_type,
                "unit_price": unit_price,
                "crypto_amount": crypto_amount,
                "fiat_amount": fiat_amount,
                "fee": fee,
                "total": total,
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate quote: {e}")
            return {"success": False, "error": str(e)}
    
    # ========================================================================
    # INSTANT ORDERS (Buy/Sell Crypto)
    # ========================================================================
    
    async def create_instant_order(
        self,
        user_id: str,
        quote_reference: str
    ) -> Dict:
        """
        Create instant order from quote
        
        This initiates the payment flow. User will be redirected to
        Quidax payment page to complete NGN payment.
        
        Args:
            user_id: Seamount user ID
            quote_reference: Quote reference from get_quote()
        
        Returns:
            {
                "success": True,
                "order_id": "instant_order_xxx",
                "payment_url": "https://quidax.com/pay/...",
                "status": "pending"
            }
        """
        try:
            # Fetch quote from database
            quote_result = self.supabase.table("quidax_quotes")\
                .select("*")\
                .eq("quote_reference", quote_reference)\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            if not quote_result.data:
                return {"success": False, "error": "Quote not found or expired"}
            
            quote = quote_result.data
            
            # Check if quote expired
            from datetime import timezone
            expires_at = datetime.fromisoformat(quote["expires_at"])
            now = datetime.now(timezone.utc)

            # Make both timezone-aware for comparison
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)

            if expires_at < now:
                return {"success": False, "error": "Quote has expired"}
            
            # Check if quote already used
            if quote["is_used"]:
                return {"success": False, "error": "Quote already used"}
            
            # Create instant order via Quidax API
            market = quote["market"]
            quote_type = quote["quote_type"]
            
            # 🚨 CRITICAL FIX: Quidax instant order payload
            # For BUY: send "volume" (amount in NGN)
            # For SELL: send "unit" (amount in crypto)
            
            if quote_type == "buy":
                # User pays NGN, receives crypto
                payload = {
                    "market": market,
                    "volume": str(quote["fiat_amount"]),  # Amount in NGN (must be string)
                    "type": "buy",
                    "callback_url": f"https://seamount-api.onrender.com/api/v1/webhooks/quidax"
                }
            else:  # sell
                # User sells crypto, receives NGN
                payload = {
                    "market": market,
                    "unit": str(quote["crypto_amount"]),  # Amount in crypto (must be string)
                    "type": "sell",
                    "callback_url": f"https://seamount-api.onrender.com/api/v1/webhooks/quidax"
                }
            
            logger.info(f"🔵 Quidax order payload: {payload}")
            
            response = requests.post(
                f"{self.BASE_URL}/users/me/instant_orders",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            order_data = response.json()
            
            # Extract order details
            order = order_data.get("data", {})
            order_id = order.get("id")
            payment_url = order.get("payment_url")
            
            # Store in onramp_transactions
            onramp_data = {
                "user_id": user_id,
                "provider": "quidax",
                "status": "pending",
                "fiat_currency": "NGN",
                "fiat_amount": quote["fiat_amount"],
                "crypto_currency": market.replace("ngn", "").upper(),
                "crypto_amount": quote["crypto_amount"],
                "net_crypto_amount": quote["crypto_amount"],
                "quidax_order_id": order_id,
                "quote_data": json.dumps(quote),
                "metadata": json.dumps({
                    "quote_reference": quote_reference,
                    "unit_price": quote["unit_price"],
                    "fee": quote["quidax_fee"],
                    "quidax_order": order
                }),
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.supabase.table("onramp_transactions").insert(onramp_data).execute()
            
            # Mark quote as used
            self.supabase.table("quidax_quotes")\
                .update({"is_used": True})\
                .eq("quote_reference", quote_reference)\
                .execute()
            
            logger.info(f"✅ Created instant order {order_id} for user {user_id[:8]}...")
            
            return {
                "success": True,
                "order_id": order_id,
                "payment_url": payment_url,
                "status": "pending",
                "amount": quote["total_amount"],
                "crypto_amount": quote["crypto_amount"]
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = e.response.json().get("message", str(e))
            logger.error(f"❌ Quidax API error: {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"❌ Failed to create instant order: {e}")
            return {"success": False, "error": str(e)}
    
    # ========================================================================
    # ORDER STATUS & VERIFICATION
    # ========================================================================
    
    async def get_order_status(self, order_id: str) -> Dict:
        """
        Get instant order status from Quidax
        
        Always verify order status from API before crediting user
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/users/me/instant_orders/{order_id}",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            order = response.json().get("data", {})
            
            return {
                "success": True,
                "order_id": order_id,
                "status": order.get("status"),  # pending, processing, done, cancelled
                "type": order.get("type"),
                "market": order.get("market"),
                "price": float(order.get("price", 0)),
                "total": float(order.get("total", 0)),
                "filled": float(order.get("filled", 0))
            }
        except Exception as e:
            logger.error(f"❌ Failed to fetch order status: {e}")
            return {"success": False, "error": str(e)}
    
    # ========================================================================
    # WITHDRAWALS (Send Crypto to External Wallet)
    # ========================================================================
    
    async def withdraw_crypto(
        self,
        user_id: str,
        currency: str,  # 'usdt', 'btc', etc.
        amount: float,
        destination_address: str,
        network: str = "trc20"  # For USDT: 'trc20', 'erc20', etc.
    ) -> Dict:
        """
        Withdraw crypto from Quidax wallet to external address
        
        This is used to auto-withdraw purchased crypto to user's WDK wallet
        """
        try:
            payload = {
                "currency": currency.lower(),
                "amount": str(amount),
                "address": destination_address
            }
            
            # Add network for tokens
            if currency.upper() in ["USDT", "USDC"]:
                payload["network"] = network
            
            response = requests.post(
                f"{self.BASE_URL}/users/me/withdraws",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            withdrawal = response.json().get("data", {})
            
            withdrawal_id = withdrawal.get("id")
            
            logger.info(f"✅ Initiated withdrawal {withdrawal_id} for {amount} {currency.upper()}")
            
            return {
                "success": True,
                "withdrawal_id": withdrawal_id,
                "currency": currency.upper(),
                "amount": amount,
                "destination": destination_address,
                "status": withdrawal.get("state"),  # submitted, processing, done, rejected
                "fee": float(withdrawal.get("fee", 0))
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = e.response.json().get("message", str(e))
            logger.error(f"❌ Withdrawal failed: {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"❌ Withdrawal failed: {e}")
            return {"success": False, "error": str(e)}
    
    # ========================================================================
    # WEBHOOK VERIFICATION
    # ========================================================================
    
    def verify_webhook_signature(
        self,
        payload: str,
        signature_header: str
    ) -> bool:
        """
        Verify Quidax webhook signature
        
        Signature format: "t=timestamp,v1=signature"
        Algorithm: HMAC-SHA256(timestamp.payload, webhook_secret)
        
        Args:
            payload: Raw request body (JSON string)
            signature_header: Value of 'quidax-signature' header
        
        Returns:
            True if signature is valid
        """
        try:
            if not self.webhook_secret:
                logger.error("❌ QUIDAX_WEBHOOK_SECRET not configured")
                return False
            
            # ✅ IMPROVED: Parse signature header into dict for easier access
            # 🔍 DEBUG: Log what we're receiving
            logger.debug(f"📋 Raw signature header: {signature_header}")

            try:
                parts = dict(item.split('=', 1) for item in signature_header.split(','))
                timestamp = parts.get('t')
                provided_signature = parts.get('v1')

                # 🔍 DEBUG: Log parsed values
                logger.info(f"📋 Parsed - t={timestamp}, v1={provided_signature}")

            except (ValueError, AttributeError) as parse_error:
                logger.error(f"❌ Failed to parse signature header: {parse_error}")
                logger.debug(f"Raw signature header: {signature_header}")
                return False
            
            if not timestamp or not provided_signature:
                logger.error("❌ Missing timestamp or signature in header")
                logger.debug(f"Parsed parts: t={timestamp}, v1={provided_signature}")
                return False
            
            # ✅ ADDED: Timestamp validation (prevent replay attacks)
            try:
                timestamp_int = int(timestamp)
                current_time = int(datetime.utcnow().timestamp())
                time_diff = abs(current_time - timestamp_int)
                
                # Allow 5 minutes tolerance
                if time_diff > 300:
                    logger.warning(f"⚠️ Webhook timestamp too old: {time_diff}s difference")
                    # Don't reject in dev mode, but log for production awareness
                    if os.getenv("ENVIRONMENT") == "production":
                        return False
            except ValueError:
                logger.error(f"❌ Invalid timestamp format: {timestamp}")
                return False
            
            # Construct signed payload (Quidax format: timestamp.payload)
            signed_payload = f"{timestamp}.{payload}"
            
            # ✅ IMPROVED: Calculate expected signature with better error handling
            try:
                expected_signature = hmac.new(
                    self.webhook_secret.encode('utf-8'),
                    signed_payload.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
            except Exception as hmac_error:
                logger.error(f"❌ HMAC calculation failed: {hmac_error}")
                return False
            
            # ✅ SECURE: Use constant-time comparison
            is_valid = hmac.compare_digest(expected_signature, provided_signature)
            
            if not is_valid:
                logger.warning("❌ Webhook signature verification failed")
                logger.debug(f"Expected signature: {expected_signature}")
                logger.debug(f"Provided signature: {provided_signature}")
                logger.debug(f"Signed payload: {signed_payload[:100]}...")  # First 100 chars only
                logger.debug(f"Webhook secret length: {len(self.webhook_secret)} chars")
            else:
                logger.info("✅ Webhook signature verified successfully")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ Signature verification error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    # ========================================================================
    # WALLET MANAGEMENT
    # ========================================================================
    
    async def get_wallets(self) -> Dict:
        """Get all Quidax sub-account wallets"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/users/me/wallets",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Failed to fetch wallets: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_deposit_address(self, currency: str) -> Dict:
        """Generate deposit address for a currency"""
        try:
            response = requests.post(
                f"{self.BASE_URL}/users/me/wallets/{currency.lower()}/addresses",
                headers=self._get_headers(),
                timeout=15
            )
            response.raise_for_status()
            address_data = response.json().get("data", {})
            
            return {
                "success": True,
                "currency": currency.upper(),
                "address": address_data.get("address"),
                "memo": address_data.get("payment_id")  # For coins that need memo
            }
        except Exception as e:
            logger.error(f"❌ Failed to generate deposit address: {e}")
            return {"success": False, "error": str(e)}
        
    # ========================================================================
    # FIAT WITHDRAWALS (Offramp)
    # ========================================================================
    
    async def withdraw_fiat(
        self,
        user_id: str,
        currency: str,  # 'ngn'
        amount: float,
        bank_account: str,
        bank_code: str,
        account_name: str
    ) -> Dict:
        """
        Withdraw fiat (NGN) from Quidax to user's bank account
        
        This is used for offramp: sell crypto → receive NGN
        """
        try:
            # Step 1: Create recipient
            recipient_payload = {
                "account_number": bank_account,
                "account_name": account_name,
                "bank_code": bank_code,
                "currency": currency.upper()
            }
            
            recipient_response = requests.post(
                f"{self.BASE_URL}/users/me/recipients",
                headers=self._get_headers(),
                json=recipient_payload,
                timeout=15
            )
            
            if recipient_response.status_code in [200, 201]:
                recipient_data = recipient_response.json().get("data", {})
                recipient_code = recipient_data.get("recipient_code")
            elif recipient_response.status_code == 422:
                # Recipient already exists, get from list
                recipients_response = requests.get(
                    f"{self.BASE_URL}/users/me/recipients",
                    headers=self._get_headers(),
                    timeout=10
                )
                recipients = recipients_response.json().get("data", [])
                recipient_code = next(
                    (r["recipient_code"] for r in recipients if r["account_number"] == bank_account),
                    None
                )
                if not recipient_code:
                    raise Exception("Recipient exists but could not be retrieved")
            else:
                raise Exception(f"Recipient creation failed: {recipient_response.text}")
            
            logger.info(f"✅ Quidax recipient created/retrieved: {recipient_code}")
            
            # Step 2: Execute transfer
            transfer_payload = {
                "recipient": recipient_code,
                "amount": str(amount),
                "currency": currency.upper(),
                "narration": f"Seamount withdrawal - {user_id[:8]}"
            }
            
            transfer_response = requests.post(
                f"{self.BASE_URL}/users/me/transfers",
                headers=self._get_headers(),
                json=transfer_payload,
                timeout=30
            )
            transfer_response.raise_for_status()
            transfer_data = transfer_response.json().get("data", {})
            
            withdrawal_id = transfer_data.get("id")
            
            logger.info(f"✅ Quidax fiat transfer initiated: {withdrawal_id}")
            
            return {
                "success": True,
                "withdrawal_id": withdrawal_id,
                "currency": currency.upper(),
                "amount": amount,
                "destination": f"{bank_account} ({account_name})",
                "status": transfer_data.get("status", "processing"),
                "estimated_settlement": "1-2 hours"
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = e.response.json().get("message", str(e))
            logger.error(f"❌ Quidax fiat withdrawal failed: {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"❌ Quidax fiat withdrawal failed: {e}")
            return {"success": False, "error": str(e)}