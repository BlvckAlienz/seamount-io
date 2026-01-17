# File: backend/services/payment_providers/harbor.py
"""
Harbor (OwlPay) Payment Provider - Corrected API Integration
Based on actual Harbor API documentation
"""

import logging
import aiohttp
import hmac
import hashlib
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class HarborProvider:
    """
    Harbor API client - Corrected implementation
    
    API Documentation: https://harbor-developers.owlpay.com/docs
    
    Key differences from standard payment providers:
    - Uses /transfer endpoint for BOTH on-ramp and off-ramp
    - Requires customer UUID (not just email)
    - No separate balance query endpoint
    """
    
    # Supported blockchains
    SUPPORTED_CHAINS = ['ethereum', 'polygon', 'solana', 'bitcoin', 'tron']
    
    def __init__(self, settings):
        self.settings = settings
        
        # 🔑 Extract API key (REQUIRED)
        if not hasattr(settings, 'HARBOR_API_KEY') or not settings.HARBOR_API_KEY:
            logger.error("❌ HARBOR_API_KEY not configured in environment!")
            raise ValueError("Harbor API key is required")
        
        self.api_key = settings.HARBOR_API_KEY.get_secret_value()
        
        # 🔐 Webhook secret (OPTIONAL - Harbor doesn't provide one)
        self.webhook_secret = None
        if hasattr(settings, 'HARBOR_WEBHOOK_SECRET') and settings.HARBOR_WEBHOOK_SECRET:
            self.webhook_secret = settings.HARBOR_WEBHOOK_SECRET.get_secret_value()
            logger.info("✅ Harbor webhook secret configured")
        else:
            logger.info("ℹ️  Harbor webhook secret not configured (using alternative verification)")
        
        # 🌐 Determine environment (sandbox vs production)
        self.is_sandbox = not self.api_key.startswith('pk_live_')
        
        # ✅ CORRECT URLs from Harbor documentation
        if self.is_sandbox:
            self.base_url = "https://harbor-sandbox.owlpay.com/api/v1"
            logger.info("🟡 Harbor: Using SANDBOX environment")
        else:
            self.base_url = "https://harbor.owlpay.com/api/v1"
            logger.info("🟢 Harbor: Using PRODUCTION environment")
        
        logger.info(f"✅ Harbor initialized: {self.api_key[:15]}...")
    
    # ========================================================================
    # CORE API METHODS (Corrected to match Harbor's actual API)
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
        
        # ✅ CORRECT headers from Harbor documentation
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-KEY": self.api_key,  # Harbor uses X-API-KEY, not Bearer token
        }
        
        # Add idempotency key for POST requests
        if method in ["POST", "PUT", "PATCH"]:
            headers["X-Idempotency-Key"] = str(uuid.uuid4())
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(
                        url, 
                        headers=headers, 
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        response_text = await response.text()
                        
                        # Try to parse as JSON
                        try:
                            response_data = await response.json()
                        except:
                            # Harbor returned HTML (error page)
                            logger.error(f"❌ Harbor returned HTML (status {response.status}): {response_text[:200]}")
                            return {
                                "success": False,
                                "error": f"Harbor API error: {response.status}",
                                "status_code": response.status,
                                "raw_response": response_text[:500]
                            }
                        
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
                        response_text = await response.text()
                        
                        # Try to parse as JSON
                        try:
                            response_data = await response.json()
                        except:
                            # Harbor returned HTML (error page)
                            logger.error(f"❌ Harbor returned HTML (status {response.status}): {response_text[:200]}")
                            return {
                                "success": False,
                                "error": f"Harbor API error: {response.status}",
                                "status_code": response.status,
                                "raw_response": response_text[:500]
                            }
                        
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
    # CUSTOMER MANAGEMENT (Required by Harbor)
    # ========================================================================
    
    async def create_customer(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone_country_code: str = "US",
        phone_number: str = "",
        birth_date: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a customer in Harbor (required before transfers)
        
        Returns:
            {
                "success": True,
                "customer_uuid": "cus_xxx",
                "verification_link": "https://...",
                "agreement_link": "https://..."
            }
        """
        
        logger.info(f"👤 Creating Harbor customer: {first_name} {last_name} ({email})")
        
        payload = {
            "type": "individual",
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone_country_code": phone_country_code,
            "phone_number": phone_number or "000-000-0000",  # Default if not provided
        }
        
        if birth_date:
            payload["birth_date"] = birth_date
        
        if description:
            payload["description"] = description
        
        result = await self._make_request("POST", "/customers", data=payload)
        
        if result.get("data"):
            customer_data = result["data"]
            logger.info(f"✅ Harbor customer created: {customer_data['uuid']}")
            
            return {
                "success": True,
                "customer_uuid": customer_data["uuid"],
                "status": customer_data.get("status", "deactivated"),
                "verification_link": customer_data.get("verification_link"),
                "agreement_link": customer_data.get("agreement_link"),
                "email": customer_data.get("email")
            }
        
        logger.error(f"❌ Harbor customer creation failed: {result}")
        return {
            "success": False,
            "error": result.get("error", "Customer creation failed")
        }
    
    # ========================================================================
    # TRANSFER API (Harbor's unified on-ramp/off-ramp endpoint)
    # ========================================================================
    
    async def initialize_onramp(
        self,
        amount_fiat: Decimal,
        currency: str,
        crypto_asset: str,
        blockchain: str,
        wallet_address: str,
        customer_uuid: str,  # ✅ Harbor requires this
        tx_ref: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Initialize fiat → crypto on-ramp via Harbor's /transfer endpoint
        
        Args:
            amount_fiat: Amount in fiat (e.g., 100.00 USD)
            currency: Fiat currency (USD, EUR, etc.)
            crypto_asset: Crypto to receive (USDC, ETH, BTC, etc.)
            blockchain: Target blockchain
            wallet_address: Destination crypto address
            customer_uuid: Harbor customer UUID (required!)
            tx_ref: Your internal reference
            metadata: Additional data
        """
        
        if blockchain not in self.SUPPORTED_CHAINS:
            return {
                "success": False,
                "error": f"Blockchain {blockchain} not supported by Harbor"
            }
        
        logger.info(
            f"💳 Harbor On-Ramp: {amount_fiat} {currency} → "
            f"{crypto_asset} on {blockchain} for customer {customer_uuid[:10]}..."
        )
        
        # ✅ Harbor's actual transfer payload structure
        payload = {
            "on_behalf_of": customer_uuid,  # Required!
            "commission": {
                "percentage": "0.01",  # 1% commission (adjust as needed)
                "amount": "0.00"
            },
            "source": {
                "asset": currency.upper(),  # "USD"
                "amount": str(amount_fiat)
            },
            "destination": {
                "asset": crypto_asset.upper(),  # "USDC"
                "chain": blockchain,  # "ethereum"
                "address": wallet_address,
                "transfer_purpose": "Payment",  # Required
                "is_self_transfer": True  # Assume self-transfer
            },
            "application_transfer_uuid": tx_ref
        }
        
        result = await self._make_request("POST", "/transfers", data=payload)
        
        if result.get("data"):
            transfer_data = result["data"]
            logger.info(f"✅ Harbor on-ramp created: {transfer_data['uuid']}")
            
            return {
                "success": True,
                "payment_id": transfer_data["uuid"],
                "status": transfer_data.get("status"),
                "transfer_instructions": transfer_data.get("transfer_instructions"),
                "receipt": transfer_data.get("receipt")
            }
        
        logger.error(f"❌ Harbor on-ramp failed: {result}")
        return result
    
    async def initialize_offramp(
        self,
        crypto_amount: Decimal,
        crypto_asset: str,
        blockchain: str,
        fiat_currency: str,
        bank_details: Dict[str, str],
        customer_uuid: str,  # ✅ Harbor requires this
        tx_ref: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Initialize crypto → fiat off-ramp via Harbor's /transfer endpoint
        """
        
        if blockchain not in self.SUPPORTED_CHAINS:
            return {
                "success": False,
                "error": f"Blockchain {blockchain} not supported"
            }
        
        logger.info(
            f"💸 Harbor Off-Ramp: {crypto_amount} {crypto_asset} → "
            f"{fiat_currency} for customer {customer_uuid[:10]}..."
        )
        
        # ✅ Harbor's actual off-ramp payload
        payload = {
            "on_behalf_of": customer_uuid,
            "commission": {
                "percentage": "0.01",
                "amount": "0.00"
            },
            "source": {
                "chain": blockchain,
                "asset": crypto_asset.upper(),
                "amount": str(crypto_amount)
            },
            "destination": {
                "asset": fiat_currency.upper(),
                **bank_details,  # Spread bank account details
                "transfer_purpose": "Payment",
                "is_self_transfer": True
            },
            "application_transfer_uuid": tx_ref
        }
        
        result = await self._make_request("POST", "/transfers", data=payload)
        
        if result.get("data"):
            transfer_data = result["data"]
            logger.info(f"✅ Harbor off-ramp created: {transfer_data['uuid']}")
            
            return {
                "success": True,
                "payment_id": transfer_data["uuid"],
                "status": transfer_data.get("status"),
                "deposit_address": transfer_data.get("transfer_instructions", {}).get("instruction_address"),
                "receipt": transfer_data.get("receipt")
            }
        
        logger.error(f"❌ Harbor off-ramp failed: {result}")
        return result
    
    # ========================================================================
    # TRANSACTION STATUS
    # ========================================================================
    
    async def get_transaction_status(
        self,
        transfer_uuid: str
    ) -> Dict[str, Any]:
        """
        Get transfer status from Harbor
        
        Args:
            transfer_uuid: Harbor transfer UUID (transfer_xxx)
        """
        
        result = await self._make_request("GET", f"/transfers/{transfer_uuid}")
        
        if result.get("data"):
            transfer_data = result["data"]
            logger.info(f"✅ Harbor status: {transfer_data['status']} for {transfer_uuid}")
            
            return {
                "success": True,
                "status": transfer_data["status"],
                "uuid": transfer_data["uuid"],
                "receipt": transfer_data.get("receipt")
            }
        
        logger.error(f"❌ Harbor status check failed: {result}")
        return result
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def is_chain_supported(self, blockchain: str) -> bool:
        """Check if blockchain is supported"""
        return blockchain.lower() in self.SUPPORTED_CHAINS
    
    def verify_webhook_signature(
        self,
        payload: str,
        signature: str
    ) -> bool:
        """
        Verify Harbor webhook signature (if secret provided)
        """
        
        if not self.webhook_secret:
            logger.warning(
                "⚠️  Webhook signature verification skipped - no secret configured"
            )
            return True
        
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