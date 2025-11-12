# File: backend/services/payment_providers/pretium.py
"""
Pretium Africa Payment Provider - Tron USDT Exclusive
Supports 7 African countries with instant settlement
Fee Structure: 2.0% (NGN) | 2.5% (KES/GHS) | 3.0% (UGX)
"""

import logging
import aiohttp
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime

from backend.config import get_settings

logger = logging.getLogger(__name__)

class PretiumProvider:
    """
    Production-ready Pretium integration for Tron USDT transactions
    """
    
    # Country-specific configurations from Pretium docs
    SUPPORTED_COUNTRIES = {
        "NG": {
            "currency": "NGN",
            "endpoint": "/v1/pay/NGN",
            "onramp_endpoint": "/v1/onramp/NGN",
            "methods": ["bank_transfer"],
            "fee_rate": Decimal("0.020"),  # 2.0%
            "limits": {"min": 100, "max": 2000000}
        },
        "KE": {
            "currency": "KES",
            "endpoint": "/v1/pay/KES",
            "onramp_endpoint": "/v1/onramp/KES",
            "methods": ["mobile_money"],
            "mobile_networks": ["Safaricom"],  # M-Pesa
            "fee_rate": Decimal("0.025"),  # 2.5%
            "limits": {"min": 20, "max": 250000}
        },
        "UG": {
            "currency": "UGX",
            "endpoint": "/v1/pay/UGX",
            "onramp_endpoint": "/v1/onramp/UGX",
            "methods": ["mobile_money"],
            "mobile_networks": ["MTN", "Airtel"],
            "fee_rate": Decimal("0.030"),  # 3.0%
            "limits": {"min": 500, "max": 5000000}
        },
        "GH": {
            "currency": "GHS",
            "endpoint": "/v1/pay/GHS",
            "onramp_endpoint": "/v1/onramp/GHS",
            "methods": ["mobile_money"],
            "mobile_networks": ["Airtel go"],
            "fee_rate": Decimal("0.025"),  # 2.5%
            "limits": {"min": 5, "max": 1000}
        },
        "MW": {
            "currency": "MWK",
            "endpoint": "/v1/pay/MWK",
            "onramp_endpoint": "/v1/onramp/MWK",
            "methods": ["mobile_money"],
            "mobile_networks": ["Airtel Money"],
            "fee_rate": Decimal("0.025"),  # 2.5%
            "limits": {"min": 100, "max": 5000000}
        },
        "ET": {
            "currency": "ETB",
            "endpoint": "/v1/pay/ETB",
            "methods": ["mobile_money"],
            "mobile_networks": ["Telebirr"],
            "fee_rate": Decimal("0.025"),  # 2.5%
            "limits": {"min": 10, "max": None}
        },
        "CD": {
            "currency": "CDF",
            "endpoint": "/v1/pay/CDF",
            "onramp_endpoint": "/v1/onramp/CDF",
            "methods": ["mobile_money"],
            "mobile_networks": ["Telebirr"],
            "fee_rate": Decimal("0.030"),  # 3.0%
            "limits": {"min": 2800, "max": 280}
        }
    }
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        
        # API credentials from .env
        self.consumer_key = self.settings.PRETIUM_CONSUMER_KEY
        self.secret_key = self.settings.PRETIUM_SECRET_KEY.get_secret_value()
        self.base_url = self.settings.PRETIUM_BASE_URL
        self.settlement_wallet = self.settings.PRETIUM_SETTLEMENT_WALLET
        
        # Validate credentials
        self._validate_config()
        
        logger.info("✅ PretiumProvider initialized for Tron USDT")

    def _validate_config(self):
        """Validate Pretium API credentials"""
        if not all([self.consumer_key, self.secret_key, self.base_url]):
            raise ValueError("Missing Pretium API credentials in .env")
        
        if "test" in self.secret_key.lower():
            logger.warning("⚠️ Pretium using TEST credentials")
        
        logger.info(f"🔑 Pretium API Key: {self.consumer_key[:10]}...")
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Pretium API"""
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "x-api-key": self.consumer_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == "POST":
                    async with session.post(
                        url, 
                        json=data, 
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        result = await response.json()
                        
                        if response.status != 200:
                            logger.error(f"❌ Pretium API error: {result}")
                            return {"success": False, "error": result.get("message")}
                        
                        return result
                else:  # GET
                    async with session.get(
                        url, 
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        result = await response.json()
                        
                        if response.status != 200:
                            logger.error(f"❌ Pretium API error: {result}")
                            return {"success": False, "error": result.get("message")}
                        
                        return result
                        
        except aiohttp.ClientError as e:
            logger.error(f"❌ Pretium network error: {e}")
            return {"success": False, "error": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"💥 Pretium request failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_exchange_rate(self, currency_code: str) -> Dict[str, Any]:
        """Get live exchange rate from Pretium"""
        
        payload = {"currency_code": currency_code}
        result = await self._make_request("POST", "/v1/exchange-rate", payload)
        
        if result.get("code") == 200:
            rate_data = result.get("data", {})
            return {
                "success": True,
                "buying_rate": rate_data.get("buying_rate"),
                "selling_rate": rate_data.get("selling_rate"),
                "quoted_rate": rate_data.get("quoted_rate")
            }
        
        return {"success": False, "error": result.get("message")}
    
    async def initialize_onramp(
        self,
        user_id: str,
        amount: float,
        currency: str,
        wallet_address: str,
        phone_number: str,
        mobile_network: str = "Safaricom"
    ) -> Dict[str, Any]:
        """
        Initialize fiat → USDT_TRON on-ramp via Pretium
        
        User pays fiat → Receives USDT on Tron blockchain
        """
        
        # Get country config
        country = self._get_country_from_currency(currency)
        if not country:
            return {"success": False, "error": f"Currency {currency} not supported by Pretium"}
        
        config = self.SUPPORTED_COUNTRIES[country]
        
        # Validate amount limits
        if not self._validate_limits(amount, config):
            return {
                "success": False, 
                "error": f"Amount outside limits: {config['limits']['min']}-{config['limits']['max']} {currency}"
            }
        
        # Calculate Seamount fee (will be collected by Pretium on our behalf)
        seamount_fee = float(Decimal(str(amount)) * config["fee_rate"])
        
        # Prepare request
        tx_ref = f"ONRAMP_PRETIUM_{user_id[:8]}_{int(datetime.now().timestamp())}"
        
        payload = {
            "shortcode": phone_number,
            "amount": int(amount),
            "mobile_network": mobile_network,
            "chain": "Tron",
            "asset": "USDT",
            "address": wallet_address,
            "fee": int(seamount_fee),  # Pretium collects this for us
            "callback_url": f"{self.settings.PRETIUM_WEBHOOK_URL}/status"
        }
        
        logger.info(f"📤 Pretium on-ramp: {amount} {currency} → USDT_TRON")
        
        # Call Pretium API
        result = await self._make_request(
            "POST", 
            config["onramp_endpoint"], 
            payload
        )
        
        if result.get("code") == 200:
            data = result.get("data", {})
            
            return {
                "success": True,
                "transaction_code": data.get("transaction_code"),
                "status": data.get("status", "PENDING"),
                "message": data.get("message"),
                "reference": tx_ref,
                "amount": amount,
                "currency": currency,
                "seamount_fee": seamount_fee,
                "estimated_settlement": "5-10 minutes"
            }
        
        logger.error(f"❌ Pretium on-ramp failed: {result}")
        return {"success": False, "error": result.get("message", "On-ramp initialization failed")}
    
    async def initialize_offramp(
        self,
        user_id: str,
        amount: float,
        currency: str,
        transaction_hash: str,
        recipient_details: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Initialize USDT_TRON → fiat off-ramp via Pretium
        
        User sends USDT → Receives local currency (bank/mobile money)
        """
        
        # Get country config
        country = self._get_country_from_currency(currency)
        if not country:
            return {"success": False, "error": f"Currency {currency} not supported by Pretium"}
        
        config = self.SUPPORTED_COUNTRIES[country]
        
        # Validate amount limits
        if not self._validate_limits(amount, config):
            return {
                "success": False,
                "error": f"Amount outside limits: {config['limits']['min']}-{config['limits']['max']} {currency}"
            }
        
        # Calculate Seamount fee
        seamount_fee = float(Decimal(str(amount)) * config["fee_rate"])
        
        # Prepare request based on payment method
        tx_ref = f"OFFRAMP_PRETIUM_{user_id[:8]}_{int(datetime.now().timestamp())}"
        
        if recipient_details.get("payment_method") == "bank_transfer":
            # Nigeria bank transfers
            payload = {
                "transaction_hash": transaction_hash,
                "account_number": recipient_details.get("account_number"),
                "account_name": recipient_details.get("account_name"),
                "amount": str(int(amount)),
                "fee": str(int(seamount_fee)),
                "bank_name": recipient_details.get("bank_name"),
                "bank_code": recipient_details.get("bank_code"),
                "chain": "TRON",
                "callback_url": f"{self.settings.PRETIUM_WEBHOOK_URL}/status"
            }
        else:
            # Mobile money (Kenya, Uganda, Ghana, etc.)
            payload = {
                "transaction_hash": transaction_hash,
                "shortcode": recipient_details.get("phone_number"),
                "amount": str(int(amount)),
                "fee": str(int(seamount_fee)),
                "mobile_network": recipient_details.get("mobile_network"),
                "chain": "Tron",
                "callback_url": f"{self.settings.PRETIUM_WEBHOOK_URL}/status"
            }
            
            # Ghana requires account_name
            if country == "GH":
                payload["account_name"] = recipient_details.get("account_name", "User")
        
        logger.info(f"📤 Pretium off-ramp: USDT_TRON → {amount} {currency}")
        
        # Call Pretium API
        result = await self._make_request(
            "POST",
            config["endpoint"],
            payload
        )
        
        if result.get("code") == 200:
            data = result.get("data", {})
            
            return {
                "success": True,
                "transaction_code": data.get("transaction_code"),
                "status": data.get("status", "PENDING"),
                "message": data.get("message"),
                "reference": tx_ref,
                "amount": amount,
                "currency": currency,
                "seamount_fee": seamount_fee,
                "estimated_settlement": "1-2 hours"
            }
        
        logger.error(f"❌ Pretium off-ramp failed: {result}")
        return {"success": False, "error": result.get("message", "Off-ramp initialization failed")}
    
    async def verify_transaction(
        self, 
        transaction_code: str, 
        currency: str
    ) -> Dict[str, Any]:
        """Verify transaction status via Pretium"""
        
        country = self._get_country_from_currency(currency)
        if not country:
            return {"success": False, "error": "Invalid currency"}
        
        payload = {"transaction_code": transaction_code}
        
        result = await self._make_request(
            "POST",
            f"/v1/status/{currency}",
            payload
        )
        
        if result.get("code") == 200:
            data = result.get("data", {})
            
            return {
                "success": True,
                "transaction_code": data.get("transaction_code"),
                "status": data.get("status"),
                "amount": data.get("amount"),
                "currency": data.get("currency_code"),
                "receipt_number": data.get("receipt_number"),
                "message": data.get("message")
            }
        
        return {"success": False, "error": result.get("message")}
    
    def _get_country_from_currency(self, currency: str) -> Optional[str]:
        """Map currency to country code"""
        currency_map = {
            "NGN": "NG",
            "KES": "KE",
            "UGX": "UG",
            "GHS": "GH",
            "MWK": "MW",
            "ETB": "ET",
            "CDF": "CD"
        }
        return currency_map.get(currency)
    
    def _validate_limits(self, amount: float, config: Dict) -> bool:
        """Validate amount against Pretium limits"""
        limits = config.get("limits", {})
        min_amount = limits.get("min", 0)
        max_amount = limits.get("max")
        
        if amount < min_amount:
            return False
        
        if max_amount and amount > max_amount:
            return False
        
        return True
    
    def get_fee_rate(self, currency: str) -> Decimal:
        """Get Seamount fee rate for currency"""
        country = self._get_country_from_currency(currency)
        if not country:
            return Decimal("0.025")  # Default 2.5%
        
        return self.SUPPORTED_COUNTRIES[country]["fee_rate"]