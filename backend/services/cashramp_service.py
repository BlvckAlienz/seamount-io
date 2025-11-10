# File: backend/services/cashramp_service.py
"""
Cashramp Integration Service - PRIMARY PAYMENT PROVIDER
Core cross-border payment engine with P2P liquidity for African markets
"""

import logging
import aiohttp
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, UTC

from backend.config import get_settings
from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class CashrampService:
    """
    PRIMARY payment provider for Seamount
    Enables fast, cheap USDT/USDCa settlement with local payment methods
    """
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.settings = get_settings()
        
        # API Configuration
        self.base_url = "https://staging.api.useaccrue.com/cashramp/api"
        self.graphql_endpoint = f"{self.base_url}/graphql"
        self.rest_endpoint = f"{self.base_url}/v1"
        
        # Get API credentials from settings
        self.api_key = getattr(self.settings, 'CASHRAMP_API_KEY', None)
        self.public_key = getattr(self.settings, 'CASHRAMP_PUBLIC_KEY', None)
        self.webhook_secret = getattr(self.settings, 'CASHRAMP_WEBHOOK_SECRET', None)
        
        # Check if Cashramp is configured
        if not self.api_key or not self.public_key:
            logger.warning(
                "⚠️ CASHRAMP NOT CONFIGURED! "
                "Add CASHRAMP_API_KEY and CASHRAMP_PUBLIC_KEY to .env"
            )
        else:
            logger.info("✅ CashrampService initialized (PRIMARY PROVIDER)")
        
        # Supported payment methods per country
        self.payment_methods = {
            "NG": ["bank_transfer", "mobile_money", "card"],
            "KE": ["mpesa", "bank_transfer", "airtel_money"],
            "GH": ["momo", "bank_transfer", "card"],
            "ZA": ["eft", "bank_transfer", "card"]
        }
    
    def is_available(self) -> bool:
        """Check if Cashramp is configured and available"""
        return bool(self.api_key and self.public_key)
    
    async def create_ngn_onramp(
        self,
        user_id: str,
        asset: str,
        amount_ngn: Decimal,
        payment_method: str = "paystack"
    ) -> Dict[str, Any]:
        """
        Create NGN on-ramp to buy USDT/USDCa
        
        Args:
            user_id: User ID
            asset: Crypto asset to purchase (USDT, USDCa)
            amount_ngn: Amount in Nigerian Naira
            payment_method: Payment method (default: paystack)
        
        Returns:
            Dict with payment_url, onramp_id, etc.
        """
        
        # Check if Cashramp is configured
        if not self.is_available():
            raise Exception(
                "Cashramp not configured. Please add CASHRAMP_API_KEY "
                "and CASHRAMP_PUBLIC_KEY to your .env file"
            )
        
        try:
            # Get current NGN/USD rate
            exchange_rate = await self.get_exchange_rate(asset, "NG")
            if not exchange_rate:
                raise Exception("Could not get exchange rate")
            
            amount_usd = amount_ngn / exchange_rate["rate"]
            
            # Create on-ramp request
            onramp_data = {
                "user_id": user_id,
                "asset": asset,
                "amount_ngn": float(amount_ngn),
                "amount_usd": float(amount_usd),
                "payment_method": payment_method,
                "country": "NG"
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key.get_secret_value() if hasattr(self.api_key, 'get_secret_value') else self.api_key}",
                "Content-Type": "application/json",
                "X-Public-Key": self.public_key.get_secret_value() if hasattr(self.public_key, 'get_secret_value') else self.public_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.rest_endpoint}/onramp",
                    headers=headers,
                    json=onramp_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 201:
                        result = await response.json()
                        
                        logger.info(
                            f"✅ Cashramp on-ramp created: {result.get('id')} "
                            f"for user {user_id[:8]}..."
                        )
                        
                        return {
                            "success": True,
                            "onramp_id": result.get("id"),
                            "asset": asset,
                            "amount_ngn": float(amount_ngn),
                            "amount_usd": float(amount_usd),
                            # 🎯 CRITICAL FIX: Return ALL possible URL fields for frontend extraction
                            "payment_url": result.get("payment_url"),
                            "checkout_url": result.get("payment_url"),  # Same as payment_url for consistency
                            "link": result.get("payment_url"),          # Another alias
                            "url": result.get("payment_url"),           # Another alias  
                            "expires_at": result.get("expires_at")
                        }
                    else:
                        error_data = await response.json()
                        error_msg = error_data.get("message", "Unknown error")
                        logger.error(f"Cashramp API error: {error_msg}")
                        raise Exception(f"Cashramp API error: {error_msg}")
                        
        except aiohttp.ClientError as e:
            logger.error(f"Cashramp network error: {e}")
            raise Exception(f"Network error connecting to Cashramp: {str(e)}")
        except Exception as e:
            logger.error(f"Cashramp on-ramp failed: {e}")
            raise Exception(f"Cashramp on-ramp failed: {str(e)}")
    
    async def send_cross_border_payment(
        self,
        sender_user_id: str,
        recipient_country: str,
        asset: str,
        amount_usd: Decimal,
        recipient_details: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Send cross-border payment via Cashramp
        
        Args:
            sender_user_id: Sender's user ID
            recipient_country: ISO country code (e.g., "KE")
            asset: Crypto asset (USDT, USDCa)
            amount_usd: Amount in USD
            recipient_details: Recipient payment details
        
        Returns:
            Transaction result with transfer_id
        """
        
        if not self.is_available():
            raise Exception("Cashramp not configured")
        
        try:
            # Get exchange rate
            exchange_rate = await self.get_exchange_rate(asset, recipient_country)
            if not exchange_rate:
                raise Exception(f"No exchange rate for {recipient_country}")
            
            local_amount = amount_usd * exchange_rate["rate"]
            
            # Create transfer request
            transfer_request = {
                "type": "CROSS_BORDER_TRANSFER",
                "sender_id": sender_user_id,
                "amount_usd": float(amount_usd),
                "asset": asset,
                "recipient": {
                    "country": recipient_country,
                    "amount_local": float(local_amount),
                    "currency": exchange_rate["local_currency"],
                    "payment_method": recipient_details.get("payment_method", "bank_transfer"),
                    "account_details": recipient_details
                },
                "estimated_fee_usd": float(amount_usd * Decimal("0.026")),
                "settlement_time": "< 5 seconds"
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Public-Key": self.public_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.rest_endpoint}/transfers",
                    headers=headers,
                    json=transfer_request,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 201:
                        result = await response.json()
                        
                        # Store transaction
                        await self.db_service.log_event("cross_border_payment", {
                            "transfer_id": result.get("id"),
                            "sender_user_id": sender_user_id,
                            "amount_usd": float(amount_usd),
                            "asset": asset,
                            "recipient_country": recipient_country,
                            "local_amount": float(local_amount),
                            "status": "pending",
                            "created_at": datetime.now(UTC).isoformat()
                        })
                        
                        logger.info(
                            f"✅ Cross-border payment sent: {result.get('id')} "
                            f"({amount_usd} USD → {local_amount} {exchange_rate['local_currency']})"
                        )
                        
                        return {
                            "success": True,
                            "transfer_id": result.get("id"),
                            "amount_usd": float(amount_usd),
                            "local_amount": float(local_amount),
                            "local_currency": exchange_rate["local_currency"],
                            "estimated_arrival": "< 5 seconds",
                            "fee_usd": float(amount_usd * Decimal("0.026")),
                            "tracking_url": result.get("tracking_url")
                        }
                    else:
                        error_data = await response.json()
                        raise Exception(f"Cashramp API error: {error_data}")
                        
        except Exception as e:
            logger.error(f"Cross-border payment failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_exchange_rate(
        self,
        asset: str,
        country_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get real-time exchange rate for country
        
        Args:
            asset: Crypto asset (USDT, USDCa)
            country_code: ISO country code (e.g., "NG")
        
        Returns:
            Dict with rate, currency, last_updated
        """
        
        # Currency mapping
        currency_map = {
            "NG": "NGN", "KE": "KES", "GH": "GHS", "ZA": "ZAR",
            "UG": "UGX", "TZ": "TZS", "EG": "EGP"
        }
        
        local_currency = currency_map.get(country_code, "USD")
        
        # If Cashramp not available, use fallback rates
        if not self.is_available():
            logger.warning("Using fallback exchange rates (Cashramp not configured)")
            fallback_rates = {
                "NGN": 1600.0, "KES": 150.0, "GHS": 12.0, "ZAR": 18.0,
                "UGX": 3700.0, "TZS": 2600.0, "EGP": 31.0
            }
            
            return {
                "rate": Decimal(str(fallback_rates.get(local_currency, 1.0))),
                "local_currency": local_currency,
                "last_updated": datetime.now(UTC).isoformat(),
                "spread": 0.026,
                "source": "fallback"
            }
        
        # Try to get real rate from Cashramp
        try:
            query = """
            query GetExchangeRate($asset: String!, $currency: String!) {
                exchangeRate(asset: $asset, currency: $currency) {
                    rate
                    currency
                    lastUpdated
                    spread
                }
            }
            """
            
            variables = {"asset": asset, "currency": local_currency}
            response_data = await self._make_graphql_request(query, variables)
            
            if response_data and "exchangeRate" in response_data.get("data", {}):
                rate_data = response_data["data"]["exchangeRate"]
                return {
                    "rate": Decimal(str(rate_data["rate"])),
                    "local_currency": local_currency,
                    "last_updated": rate_data["lastUpdated"],
                    "spread": rate_data.get("spread", 0.026),
                    "source": "cashramp"
                }
            
        except Exception as e:
            logger.warning(f"Failed to get Cashramp rate, using fallback: {e}")
        
        # Fallback to static rates
        fallback_rates = {
            "NGN": 1600.0, "KES": 150.0, "GHS": 12.0, "ZAR": 18.0
        }
        
        return {
            "rate": Decimal(str(fallback_rates.get(local_currency, 1.0))),
            "local_currency": local_currency,
            "last_updated": datetime.now(UTC).isoformat(),
            "spread": 0.026,
            "source": "fallback"
        }
    
    async def track_transfer_status(self, transfer_id: str) -> Dict[str, Any]:
        """Track status of cross-border transfer"""
        
        if not self.is_available():
            return {"success": False, "error": "Cashramp not configured"}
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.rest_endpoint}/transfers/{transfer_id}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        transfer_data = await response.json()
                        
                        status_mapping = {
                            "pending": "processing",
                            "processing": "processing",
                            "completed": "completed",
                            "failed": "failed",
                            "cancelled": "cancelled"
                        }
                        
                        cashramp_status = transfer_data.get("status", "pending")
                        internal_status = status_mapping.get(cashramp_status, "processing")
                        
                        return {
                            "success": True,
                            "transfer_id": transfer_id,
                            "status": internal_status,
                            "cashramp_status": cashramp_status,
                            "recipient_received": transfer_data.get("recipient_received", False),
                            "completion_time": transfer_data.get("completed_at"),
                            "tracking_info": transfer_data.get("tracking_info", {})
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Transfer not found: {transfer_id}"
                        }
                        
        except Exception as e:
            logger.error(f"Transfer tracking failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _make_graphql_request(
        self,
        query: str,
        variables: Dict = None
    ) -> Optional[Dict]:
        """Make GraphQL request to Cashramp API"""
        
        if not self.is_available():
            return None
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key.get_secret_value() if hasattr(self.api_key, 'get_secret_value') else self.api_key}",
                "X-Public-Key": self.public_key.get_secret_value() if hasattr(self.public_key, 'get_secret_value') else self.public_key
            }
            
            payload = {
                "query": query,
                "variables": variables or {}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.graphql_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Cashramp GraphQL error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"GraphQL request failed: {e}")
            return None