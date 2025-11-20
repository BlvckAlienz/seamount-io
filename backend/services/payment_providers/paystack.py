# File Location: backend/services/payment_providers/paystack.py
import logging
import asyncio
import aiohttp
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any

from config import Settings

logger = logging.getLogger(__name__)

class PaystackProvider:  # Changed from PaystackProcessor to PaystackProvider
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
        
        logger.info("✅ PaystackProvider initialized")  # Updated log message
    
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
                    {"display_name": "Payment For", "variable_name": "payment_for", "value": "Crypto Purchase"},
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
        """
        ✅ Initiate bank transfer to Nigerian account
        Uses Paystack Transfer API for instant payouts
        """
        
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
                error_msg = recipient_data.get('message', 'Failed to create recipient')
                logger.error(f"❌ Paystack recipient creation failed: {error_msg}")
                return {"success": False, "message": error_msg}
            
            recipient_code = recipient_data['data']['recipient_code']
            logger.info(f"✅ Paystack recipient created: {recipient_code}")
            
            # Step 2: Initiate transfer
            transfer_url = f"{self.base_url}/transfer"
            transfer_payload = {
                "source": "balance",
                "reason": f"Seamount Withdrawal {tx_ref}",
                "amount": int(float(amount) * 100),  # Convert to kobo
                "recipient": recipient_code,
                "reference": tx_ref
            }
            
            transfer_data = await self._request_with_retry('POST', transfer_url, json=transfer_payload)
            
            if transfer_data.get('status'):
                logger.info(f"✅ Paystack transfer initiated: {tx_ref}")
                return {
                    "success": True,
                    "reference": transfer_data['data']['reference'],
                    "transfer_code": transfer_data['data']['transfer_code'],
                    "message": "Payout initiated successfully"
                }
            else:
                error_msg = transfer_data.get('message', 'Transfer failed')
                logger.error(f"❌ Paystack transfer failed: {error_msg}")
                return {"success": False, "message": error_msg}
                
        except Exception as e:
            logger.error(f"💥 Paystack payout exception: {e}")
            return {"success": False, "message": str(e)}
    
    async def create_transfer_recipient(
        self, 
        account_number: str, 
        account_name: str, 
        bank_code: str
    ) -> Dict[str, Any]:
        """
        ✅ Step 1: Create transfer recipient (beneficiary)
        This recipient_code can be reused for future transfers
        """
        url = f"{self.base_url}/transferrecipient"
        payload = {
            "type": "nuban",  # Nigerian Uniform Bank Account Number
            "name": account_name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN"
        }
        
        try:
            data = await self._request_with_retry('POST', url, json=payload)
            
            if data.get('status') and data.get('data'):
                recipient_code = data['data']['recipient_code']
                logger.info(f"✅ Transfer recipient created: {recipient_code}")
                
                return {
                    "success": True,
                    "recipient_code": recipient_code,
                    "account_name": data['data']['details']['account_name'],
                    "account_number": data['data']['details']['account_number'],
                    "bank_name": data['data']['details']['bank_name']
                }
            else:
                error_msg = data.get('message', 'Recipient creation failed')
                logger.error(f"❌ Paystack recipient creation failed: {error_msg}")
                return {"success": False, "message": error_msg}
                
        except Exception as e:
            logger.error(f"💥 Paystack recipient creation exception: {e}")
            return {"success": False, "message": str(e)}

    async def execute_transfer(
        self, 
        amount: Decimal, 
        recipient_code: str, 
        reference: str,
        reason: str = "Seamount withdrawal"
    ) -> Dict[str, Any]:
        """
        ✅ Step 2: Execute transfer from Paystack balance to user account
        
        REQUIREMENTS:
        - Your Paystack account must have sufficient NGN balance
        - OTP must be disabled for automated transfers
        """
        url = f"{self.base_url}/transfer"
        
        # Convert to kobo (NGN subunit)
        amount_kobo = int(float(amount) * 100)
        
        payload = {
            "source": "balance",  # Transfer from Paystack balance
            "reason": reason,
            "amount": amount_kobo,
            "recipient": recipient_code,
            "reference": reference
        }
        
        try:
            data = await self._request_with_retry('POST', url, json=payload)
            
            if data.get('status') and data.get('data'):
                transfer_data = data['data']
                
                logger.info(
                    f"✅ Paystack transfer initiated: {reference} "
                    f"Status: {transfer_data.get('status')}"
                )
                
                return {
                    "success": True,
                    "transfer_code": transfer_data.get('transfer_code'),
                    "reference": transfer_data.get('reference'),
                    "status": transfer_data.get('status'),  # pending, success, failed
                    "amount": float(amount),
                    "recipient": transfer_data.get('recipient'),
                    "message": data.get('message')
                }
            else:
                error_msg = data.get('message', 'Transfer failed')
                logger.error(f"❌ Paystack transfer failed: {error_msg}")
                return {"success": False, "message": error_msg}
                
        except Exception as e:
            logger.error(f"💥 Paystack transfer exception: {e}")
            return {"success": False, "message": str(e)}

    async def verify_transfer(self, reference: str) -> Dict[str, Any]:
        """
        ✅ Step 3: Verify transfer status
        """
        url = f"{self.base_url}/transfer/verify/{reference}"
        
        try:
            data = await self._request_with_retry('GET', url)
            
            if data.get('status') and data.get('data'):
                transfer_data = data['data']
                status = transfer_data.get('status')
                
                return {
                    "success": status in ['success', 'pending'],
                    "verified": status == 'success',
                    "status": status,
                    "amount": transfer_data.get('amount', 0) / 100,
                    "reference": reference,
                    "failure_reason": transfer_data.get('failure_reason'),
                    "transfer_code": transfer_data.get('transfer_code')
                }
            else:
                return {"success": False, "message": data.get('message')}
                
        except Exception as e:
            logger.error(f"💥 Paystack transfer verification exception: {e}")
            return {"success": False, "message": str(e)}
    
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