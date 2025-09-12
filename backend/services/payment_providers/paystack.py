# File Location: backend/services/payment_providers/paystack.py
import logging
import asyncio
import aiohttp
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any

from config import Settings

logger = logging.getLogger(__name__)

class PaystackProcessor:
    """
    Paystack integration for local Nigerian NGN payments.
    Targets 1.2% fees vs Flutterwave's 2.15%.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.secret_key = settings.PAYSTACK_SECRET_KEY.get_secret_value()
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
        self.base_url = "https://api.paystack.co"
        
        self._validate_config()
        
        # Rate limiting & retry config
        self.max_retries = 3
        self.retry_delay = 2.0
    
    def _validate_config(self):
        if not all([self.secret_key, self.public_key]):
            raise ValueError("Missing Paystack API keys")
        
        if "test" in self.secret_key.lower():
            logger.warning("⚠️ Paystack using TEST keys")
        
        logger.info("✅ PaystackProcessor initialized")
    
    async def _request_with_retry(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """HTTP request with exponential backoff retry"""
        headers = kwargs.get('headers', {})
        headers.update({
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        })
        kwargs['headers'] = headers
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(method, url, **kwargs) as response:
                        data = await response.json()
                        
                        if response.status == 200 and data.get('status'):
                            return data
                        
                        # Rate limiting
                        if response.status == 429:
                            wait_time = self.retry_delay * (2 ** attempt)
                            logger.warning(f"Rate limited. Retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                        
                        # Other errors
                        logger.error(f"Paystack API error: {response.status} - {data}")
                        if attempt == self.max_retries - 1:
                            return data
                        
            except aiohttp.ClientError as e:
                logger.error(f"HTTP error attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        raise Exception("Max retries exceeded")
    
    async def initialize_payment(self, amount: float, currency: str, email: str, tx_ref: str, phone: str = None, name: str = "Seamount User") -> Dict[str, Any]:
        """Initialize Paystack payment - LOCAL NIGERIA ONLY"""
        
        # Validate Nigeria-only
        if currency != "NGN":
            raise ValueError(f"Paystack only supports NGN, got {currency}")
        
        url = f"{self.base_url}/transaction/initialize"
        payload = {
            "email": email,
            "amount": int(amount * 100),  # Convert to kobo
            "currency": "NGN",
            "reference": tx_ref,
            "callback_url": f"https://seamount.io/payment-callback?tx_ref={tx_ref}",
            "channels": ["card", "bank", "ussd", "qr", "mobile_money", "bank_transfer"],
            "metadata": {
                "custom_fields": [
                    {"display_name": "Payment For", "variable_name": "payment_for", "value": "USDS Purchase"},
                    {"display_name": "Platform", "variable_name": "platform", "value": "Seamount.io"}
                ],
                "tx_ref": tx_ref
            }
        }
        
        try:
            data = await self._request_with_retry('POST', url, json=payload)
            
            if data.get('status') and data.get('data'):
                logger.info(f"✅ Paystack payment initialized: {tx_ref}")
                return {
                    'status': 'success',
                    'payment_link': data['data']['authorization_url'],
                    'access_code': data['data']['access_code'],
                    'tx_ref': tx_ref
                }
            else:
                error_msg = data.get('message', 'Payment initialization failed')
                logger.error(f"❌ Paystack init failed: {error_msg}")
                return {'status': 'error', 'message': error_msg}
                
        except Exception as e:
            logger.error(f"💥 Paystack init exception: {e}")
            raise
    
    async def verify_payment(self, tx_ref: str) -> Dict[str, Any]:
        """Verify payment completion"""
        url = f"{self.base_url}/transaction/verify/{tx_ref}"
        
        try:
            data = await self._request_with_retry('GET', url)
            
            if data.get('status') and data.get('data'):
                tx_data = data['data']
                
                if tx_data.get('status') == 'success' and tx_data.get('gateway_response') == 'Successful':
                    return {
                        'verified': True,
                        'amount': tx_data['amount'] / 100,  # Convert from kobo
                        'currency': tx_data['currency'],
                        'customer_email': tx_data['customer']['email'],
                        'fees': tx_data.get('fees', 0) / 100,
                        'authorization_code': tx_data.get('authorization', {}).get('authorization_code')
                    }
                else:
                    logger.warning(f"⚠️ Payment not successful: {tx_data.get('status')} - {tx_data.get('gateway_response')}")
                    return {'verified': False, 'message': f"Payment status: {tx_data.get('status')}"}
            else:
                return {'verified': False, 'message': data.get('message', 'Verification failed')}
                
        except Exception as e:
            logger.error(f"💥 Paystack verify exception: {e}")
            raise
    
    async def initiate_payout(self, amount: Decimal, bank_details: Dict, tx_ref: str) -> Dict[str, Any]:
        """Initiate bank transfer to Nigerian account"""
        
        # Step 1: Create transfer recipient
        recipient_url = f"{self.base_url}/transferrecipient"
        recipient_payload = {
            "type": "nuban",
            "name": bank_details.get("account_name"),
            "account_number": bank_details.get("account_number"),
            "bank_code": bank_details.get("bank_code"),
            "currency": "NGN"
        }
        
        try:
            recipient_data = await self._request_with_retry('POST', recipient_url, json=recipient_payload)
            
            if not recipient_data.get('status'):
                return {"success": False, "message": f"Failed to create recipient: {recipient_data.get('message')}"}
            
            recipient_code = recipient_data['data']['recipient_code']
            
            # Step 2: Initiate transfer
            transfer_url = f"{self.base_url}/transfer"
            transfer_payload = {
                "source": "balance",
                "reason": f"Seamount Withdrawal {tx_ref}",
                "amount": int(float(amount) * 100),  # Convert to kobo
                "recipient": recipient_code,
                "reference": f"payout_{tx_ref}"
            }
            
            transfer_data = await self._request_with_retry('POST', transfer_url, json=transfer_payload)
            
            if transfer_data.get('status'):
                return {
                    "success": True,
                    "reference": transfer_data['data']['reference'],
                    "transfer_code": transfer_data['data']['transfer_code'],
                    "message": "Payout initiated successfully"
                }
            else:
                return {"success": False, "message": transfer_data.get('message', 'Transfer failed')}
                
        except Exception as e:
            logger.error(f"💥 Paystack payout exception: {e}")
            raise
    
    async def verify_payout(self, reference: str) -> Dict[str, Any]:
        """Verify payout status"""
        url = f"{self.base_url}/transfer/verify/{reference}"
        
        try:
            data = await self._request_with_retry('GET', url)
            
            if data.get('status') and data.get('data'):
                transfer_data = data['data']
                status = transfer_data.get('status')
                
                return {
                    'verified': status == 'success',
                    'status': status,
                    'amount': transfer_data.get('amount', 0) / 100,
                    'reference': reference,
                    'failure_reason': transfer_data.get('failure_reason')
                }
            else:
                return {'verified': False, 'message': data.get('message')}
                
        except Exception as e:
            logger.error(f"💥 Paystack payout verify exception: {e}")
            raise