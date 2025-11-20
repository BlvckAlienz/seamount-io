import logging
import asyncio
import aiohttp
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any
from fastapi import HTTPException

# --- Core Dependencies ---
from backend.config import Settings  # Fixed import path

logger = logging.getLogger(__name__)

class FlutterwaveProvider:
    """
    A modern, dependency-injected, and fully asynchronous service for all
    Flutterwave payment interactions, preserving all original logic.
    """
    
    def __init__(self, settings: Settings):
        """
        Initializes the service with a pre-configured settings object.
        """
        self.settings = settings
        self.public_key = settings.FLUTTERWAVE_PUBLIC_KEY
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY.get_secret_value()
        self.base_url = "https://api.flutterwave.com/v3"

        self._validate_production_config()
    
    def _validate_production_config(self):
        """Validates that production keys are being used."""
        if not all([self.public_key, self.secret_key]):
            raise ValueError("Missing Flutterwave API keys in environment config.")
        
        if "test" in self.secret_key.lower():
            logger.warning("Flutterwave is using a TEST secret key.")
            # In a strict production environment, you would raise a ValueError here.
        
        if "test" in self.public_key.lower():
            logger.warning("Flutterwave is using a TEST public key.")
        
        logger.info("✅ FlutterwaveProvider config validated.")  # Fixed log message
    
    async def initialize_payment(self, amount: float, currency: str, email: str, tx_ref: str, phone: str = None, name: str = "Seamount User") -> Dict[str, Any]:
        """Initializes a Flutterwave payment link asynchronously."""
        url = f"{self.base_url}/payments"
        headers = {"Authorization": f"Bearer {self.secret_key}"}
        payload = {
            "tx_ref": tx_ref,
            "amount": amount,
            "currency": currency,
            "redirect_url": f"https://seamount.io/payment-callback?tx_ref={tx_ref}",
            "payment_options": "card,mobilemoney,ussd,banktransfer",
            "customer": {
                "email": email,
                "phonenumber": phone or "",
                "name": name
            },
            "customizations": {
                "title": "Seamount.io",
                "description": "Fund your wallet",
                "logo": "https://media.licdn.com/dms/image/v2/D4D0BAQEgEyglQJrHzA/company-logo_100_100/B4DZfLaLaAHAAc-/0/1751464327309/seamount_io_logo?e=1764201600&v=beta&t=4BdeX4YYQePr-S6kOqycjQF_0AaoFdiFJxxpUn1gkto"
            }
        }
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(url, json=payload) as response:
                    data = await response.json()
                    response.raise_for_status() # Raises an exception for 4xx/5xx responses
                    
                    if data.get('status') == 'success':
                        logger.info(f"Payment initialized: {data['data']['link']}")
                        return {
                            'status': 'success',
                            'payment_link': data['data']['link'],
                            'tx_ref': tx_ref
                        }
                    else:
                        logger.error(f"Payment init failed with status '{data.get('status')}': {data.get('message')}")
                        return {'status': 'error', 'message': data.get('message', 'Unknown provider error')}
                
        except aiohttp.ClientError as e:
            logger.error(f"Flutterwave API request failed during initialization: {e}")
            raise HTTPException(status_code=503, detail="Payment provider is currently unavailable.")
        except Exception as e:
            logger.error(f"Unexpected error in initialize_payment: {e}", exc_info=True)
            raise

    async def verify_payment(self, tx_ref: str) -> Dict[str, Any]:
        """Verifies a payment with Flutterwave using the transaction reference."""
        url = f"{self.base_url}/transactions/verify_by_reference?tx_ref={tx_ref}"
        headers = {"Authorization": f"Bearer {self.secret_key}"}
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as response:
                    data = await response.json()
                    response.raise_for_status()
                    
                    if data.get('status') == 'success' and data.get('data', {}).get('status') == 'successful':
                        return {
                            'verified': True,
                            'amount': data['data']['amount'],
                            'currency': data['data']['currency'],
                            'customer_email': data['data']['customer']['email']
                        }
                    else:
                        logger.warning(f"Payment verification failed for tx_ref {tx_ref}: {data.get('message')}")
                        return {'verified': False, 'message': data.get('message', 'Verification failed')}
                
        except aiohttp.ClientError as e:
            logger.error(f"Flutterwave API request failed during verification: {e}")
            raise HTTPException(status_code=503, detail="Payment provider is currently unavailable for verification.")
        except Exception as e:
            logger.error(f"Unexpected error in verify_payment: {e}", exc_info=True)
            raise

    async def initiate_payout(
        self, 
        amount: Decimal, 
        bank_details: Dict, 
        tx_ref: str
    ) -> Dict[str, Any]:
        """
        ✅ Initiate fiat payout using Flutterwave Transfer API
        
        REQUIREMENTS:
        - Flutterwave account must have sufficient balance in target currency
        - Transfers must be enabled on your account (Dashboard > Settings > Transfers)
        
        Supports multiple currencies (NGN, KES, GHS, USD, etc.)
        """
        url = f"{self.base_url}/transfers"
        headers = {"Authorization": f"Bearer {self.secret_key}"}
        
        currency = bank_details.get("currency", "NGN")
        account_number = bank_details.get("account_number")
        bank_code = bank_details.get("bank_code")
        
        # Validate required fields
        if not all([account_number, bank_code]):
            return {
                "success": False, 
                "message": "Account number and bank code required"
            }
        
        payload = {
            "account_bank": bank_code,
            "account_number": account_number,
            "amount": float(amount),
            "narration": f"Seamount Withdrawal {tx_ref}",
            "currency": currency,
            "reference": tx_ref,
            "callback_url": f"{self.settings.API_BASE_URL}/webhooks/flutterwave/transfer",
            "debit_currency": currency  # Currency to debit from Flutterwave balance
        }
        
        logger.info(
            f"💳 Initiating Flutterwave transfer: {amount} {currency} "
            f"to {bank_details.get('account_name', 'N/A')}"
        )

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    data = await response.json()
                    
                    if response.status == 200 and data.get("status") == "success":
                        transfer_data = data.get("data", {})
                        
                        logger.info(f"✅ Flutterwave transfer initiated: {tx_ref}")
                        
                        return {
                            "success": True,
                            "id": transfer_data.get("id"),
                            "reference": transfer_data.get("reference"),
                            "status": transfer_data.get("status"),  # NEW, PENDING, SUCCESS, FAILED
                            "message": "Transfer initiated successfully",
                            "amount": float(amount),
                            "currency": currency
                        }
                    else:
                        error_msg = data.get("message", "Transfer failed")
                        
                        # Check for balance issues
                        if "insufficient" in error_msg.lower() or "balance" in error_msg.lower():
                            logger.error(
                                f"❌ CRITICAL: Flutterwave balance insufficient! "
                                f"Required: {amount} {currency}"
                            )
                            return {
                                "success": False,
                                "message": "Payment provider balance low. Contact support.",
                                "error_code": "INSUFFICIENT_BALANCE"
                            }
                        
                        logger.error(f"❌ Flutterwave transfer failed: {error_msg}")
                        return {"success": False, "message": error_msg}
                            
        except aiohttp.ClientError as e:
            logger.error(f"💥 Flutterwave network error: {e}")
            return {
                "success": False, 
                "message": "Payment provider temporarily unavailable"
            }
        except Exception as e:
            logger.error(f"💥 Flutterwave transfer exception: {e}")
            return {"success": False, "message": str(e)}

    async def verify_transfer(self, transfer_id: str) -> Dict[str, Any]:
        """
        ✅ Verify Flutterwave transfer status
        """
        url = f"{self.base_url}/transfers/{transfer_id}"
        headers = {"Authorization": f"Bearer {self.secret_key}"}
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    data = await response.json()
                    
                    if response.status == 200 and data.get("status") == "success":
                        transfer_data = data.get("data", {})
                        status = transfer_data.get("status")
                        
                        return {
                            "success": True,
                            "verified": status in ["SUCCESSFUL", "SUCCESS"],
                            "status": status,
                            "amount": transfer_data.get("amount"),
                            "currency": transfer_data.get("currency"),
                            "complete_message": transfer_data.get("complete_message"),
                            "failure_reason": transfer_data.get("failure_message")
                        }
                    else:
                        return {
                            "success": False, 
                            "message": data.get("message", "Verification failed")
                        }
                        
        except Exception as e:
            logger.error(f"💥 Flutterwave verification failed: {e}")
            return {"success": False, "message": str(e)}