"""
NIBSS Instant Payment (NIP) Integration
Real-time NGN settlements for Seamount tokenized asset purchases
"""

import httpx
import hmac
import hashlib
from typing import Dict, Optional
from datetime import datetime
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

class NIBSSConnector:
    """
    Production NIBSS NIP integration
    
    Partnership Options:
    1. Direct Integration: $10M+ setup, 6-12 months (NOT VIABLE)
    2. Bank Partner: Stanbic IBTC, Access Bank (RECOMMENDED)
    3. Fintech Aggregator: Paystack, Flutterwave (FASTEST)
    
    Recommended: Partner with Paystack for MVP
    """
    
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        environment: str = "sandbox"  # sandbox | production
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = (
            "https://api.paystack.co" if environment == "production"
            else "https://api.paystack.co"  # Paystack doesn't have separate sandbox
        )
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for request validation"""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
    
    async def verify_account(
        self,
        account_number: str,
        bank_code: str
    ) -> Dict[str, any]:
        """
        Verify Nigerian bank account via NIBSS Name Enquiry
        
        Bank Codes:
        - Access Bank: 044
        - GTBank: 058
        - Zenith Bank: 057
        - UBA: 033
        - First Bank: 011
        - Stanbic IBTC: 221
        """
        try:
            url = f"{self.base_url}/bank/resolve"
            params = {
                "account_number": account_number,
                "bank_code": bank_code
            }
            
            response = await self.client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "account_name": data["data"]["account_name"],
                    "account_number": data["data"]["account_number"],
                    "bank_code": bank_code
                }
            
            return {
                "success": False,
                "error": "Account verification failed"
            }
            
        except Exception as e:
            logger.error(f"❌ NIBSS account verification failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def initiate_transfer(
        self,
        recipient_account: str,
        recipient_bank_code: str,
        amount_ngn: Decimal,
        reference: str,
        narration: str
    ) -> Dict[str, any]:
        """
        Initiate NIBSS NIP transfer
        
        Use Case: Seller receives NGN when buyer purchases tokenized asset
        """
        try:
            # Create transfer recipient
            recipient_url = f"{self.base_url}/transferrecipient"
            recipient_payload = {
                "type": "nuban",
                "name": "Asset Seller",  # Get from DB
                "account_number": recipient_account,
                "bank_code": recipient_bank_code,
                "currency": "NGN"
            }
            
            recipient_response = await self.client.post(
                recipient_url,
                json=recipient_payload,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            
            if recipient_response.status_code != 201:
                raise Exception("Failed to create transfer recipient")
            
            recipient_code = recipient_response.json()["data"]["recipient_code"]
            
            # Initiate transfer
            transfer_url = f"{self.base_url}/transfer"
            transfer_payload = {
                "source": "balance",  # Seamount Paystack balance
                "amount": int(amount_ngn * 100),  # Paystack uses kobo (1 NGN = 100 kobo)
                "recipient": recipient_code,
                "reference": reference,
                "reason": narration
            }
            
            transfer_response = await self.client.post(
                transfer_url,
                json=transfer_payload,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            
            if transfer_response.status_code == 200:
                data = transfer_response.json()["data"]
                return {
                    "success": True,
                    "transfer_code": data["transfer_code"],
                    "reference": data["reference"],
                    "status": data["status"],  # pending | success | failed
                    "amount": float(amount_ngn),
                    "recipient": recipient_account
                }
            
            return {
                "success": False,
                "error": "Transfer initiation failed"
            }
            
        except Exception as e:
            logger.error(f"❌ NIBSS transfer failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def verify_transfer(self, reference: str) -> Dict[str, any]:
        """Verify transfer status"""
        try:
            url = f"{self.base_url}/transfer/verify/{reference}"
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            
            if response.status_code == 200:
                data = response.json()["data"]
                return {
                    "success": True,
                    "status": data["status"],
                    "amount": data["amount"] / 100,  # Convert kobo to NGN
                    "transferred_at": data.get("transferred_at")
                }
            
            return {"success": False, "error": "Verification failed"}
            
        except Exception as e:
            logger.error(f"❌ Transfer verification failed: {e}")
            return {"success": False, "error": str(e)}