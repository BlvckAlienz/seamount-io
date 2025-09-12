# File Location: backend/services/payment_providers/sterling_bank.py

import httpx
import logging
import hashlib
import hmac
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SterlingBankProvider:
    """Sterling Bank payment provider for international transfers"""
    
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://api.sterling.ng"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        
    def _generate_signature(self, payload: str, timestamp: str) -> str:
        """Generate HMAC signature for Sterling Bank API"""
        message = f"{timestamp}{payload}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_headers(self, payload: str = "") -> Dict[str, str]:
        """Generate request headers with authentication"""
        timestamp = str(int(datetime.now().timestamp()))
        signature = self._generate_signature(payload, timestamp)
        
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "User-Agent": "Seamount.io/1.0"
        }
    
    async def initiate_transfer(self, transfer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initiate international transfer via Sterling Bank
        
        Args:
            transfer_data: {
                "amount": 100.00,
                "currency": "USD",
                "recipient": {
                    "account_number": "1234567890",
                    "account_name": "John Doe", 
                    "bank_code": "SWIFT_CODE",
                    "country": "US"
                },
                "reference": "seamount_tx_123",
                "narration": "Cross-border payment"
            }
        """
        try:
            endpoint = f"{self.base_url}/v1/transfers/international"
            
            payload = {
                "amount": str(transfer_data["amount"]),
                "currency": transfer_data["currency"],
                "beneficiary": {
                    "account_number": transfer_data["recipient"]["account_number"],
                    "account_name": transfer_data["recipient"]["account_name"],
                    "bank_code": transfer_data["recipient"]["bank_code"],
                    "country_code": transfer_data["recipient"]["country"]
                },
                "reference": transfer_data["reference"],
                "narration": transfer_data.get("narration", "Seamount cross-border payment"),
                "callback_url": "https://seamount.io/webhooks/sterling"
            }
            
            headers = self._get_headers(str(payload))
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "provider_tx_id": result.get("reference"),
                        "status": "processing",
                        "estimated_completion": "2-5 business days",
                        "fee": result.get("fee", 0),
                        "exchange_rate": result.get("exchange_rate"),
                        "raw_response": result
                    }
                else:
                    logger.error(f"Sterling transfer failed: {response.text}")
                    return {
                        "success": False,
                        "error": response.json().get("message", "Transfer failed"),
                        "error_code": response.status_code
                    }
                    
        except Exception as e:
            logger.error(f"Sterling transfer exception: {str(e)}")
            return {
                "success": False,
                "error": f"Transfer failed: {str(e)}"
            }
    
    async def check_transfer_status(self, provider_tx_id: str) -> Dict[str, Any]:
        """Check status of Sterling Bank transfer"""
        try:
            endpoint = f"{self.base_url}/v1/transfers/{provider_tx_id}/status"
            headers = self._get_headers()
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(endpoint, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Map Sterling status to our status
                    status_mapping = {
                        "processing": "processing",
                        "successful": "completed", 
                        "failed": "failed",
                        "pending": "pending"
                    }
                    
                    return {
                        "success": True,
                        "status": status_mapping.get(result.get("status"), "pending"),
                        "provider_tx_id": provider_tx_id,
                        "amount": result.get("amount"),
                        "fee": result.get("fee"),
                        "raw_response": result
                    }
                else:
                    return {"success": False, "error": "Status check failed"}
                    
        except Exception as e:
            logger.error(f"Sterling status check failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_exchange_rates(self, from_currency: str = "NGN", to_currencies: list = None) -> Dict[str, Any]:
        """Get current exchange rates from Sterling Bank"""
        if to_currencies is None:
            to_currencies = ["USD", "EUR", "GBP"]
            
        try:
            endpoint = f"{self.base_url}/v1/rates"
            params = {
                "from": from_currency,
                "to": ",".join(to_currencies)
            }
            
            headers = self._get_headers()
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(endpoint, headers=headers, params=params)
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "rates": response.json().get("rates", {}),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {"success": False, "error": "Rate fetch failed"}
                    
        except Exception as e:
            logger.error(f"Sterling rates fetch failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def calculate_transfer_fee(self, amount: float, currency: str = "USD") -> float:
        """Calculate Sterling Bank transfer fee"""
        # Sterling Bank typical international transfer fees
        if currency == "USD":
            base_fee = 25.0  # $25 base fee
            percentage_fee = amount * 0.015  # 1.5%
            return min(base_fee + percentage_fee, amount * 0.05)  # Cap at 5%
        else:
            return amount * 0.02  # 2% for other currencies