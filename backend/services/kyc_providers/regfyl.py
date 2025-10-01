# File Location: backend/services/kyc_providers/regfyl.py
# PRODUCTION READY: Regfyl KYC/AML Provider Integration

import asyncio
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import aiohttp
from fastapi import HTTPException

from backend.config import get_settings

logger = logging.getLogger(__name__)


class RegfylVerifier:
    """
    Production-ready Regfyl KYC/AML provider integration
    Handles customer screening, ID verification, and transaction monitoring
    """
    
    def __init__(self, api_key: str = None):
        settings = get_settings()
        self.api_key = api_key or settings.REGFYL_API_KEY
        self.base_url = getattr(settings, 'REGFYL_BASE_URL', "https://api.portal.regfyl.com")  # Fixed: added default
        self.company_name = getattr(settings, 'REGFYL_COMPANY_NAME', '')
        self.rc_number = getattr(settings, 'REGFYL_RC_NUMBER', '')
        self.environment = getattr(settings, 'REGFYL_ENVIRONMENT', 'production')
        
        self.max_retries = 3
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.last_health_check = None
        self.health_status = "unknown"
        
        if not self.api_key:
            logger.warning("Regfyl API key not configured - operating in simulation mode")
            self.simulation_mode = True
            self.initialization_status = "api_key_missing"
        else:
            self.simulation_mode = False
            self.initialization_status = "initialized"
            logger.info("Regfyl service initialized successfully")
    
    def _generate_signature(self, payload: str) -> str:
        """Generate HMAC-SHA256 signature for API requests"""
        api_key = self.api_key.get_secret_value() if hasattr(self.api_key, 'get_secret_value') else self.api_key
        return hmac.new(
            api_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _get_headers(self, payload: str = "") -> Dict[str, str]:
        """Generate headers with signature"""
        api_key = self.api_key.get_secret_value() if hasattr(self.api_key, 'get_secret_value') else self.api_key
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': api_key
        }
        if payload:
            headers['x-Signature'] = self._generate_signature(payload)
        return headers
    
    async def _make_request(self, endpoint: str, payload: Dict, retries: int = 0) -> Dict:
        """Make API request with robust retry logic"""
        if self.simulation_mode:
            return self._simulate_response(endpoint, payload)
        
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('/') else f"{self.base_url}{endpoint}"
        payload_str = json.dumps(payload, separators=(',', ':'))
        headers = self._get_headers(payload_str)
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, headers=headers, data=payload_str) as response:
                    response_data = await response.json()
                    
                    if response.status in [200, 201]:
                        self.health_status = "healthy"
                        logger.info(f"Regfyl API success: {endpoint}")
                        return response_data
                    elif response.status == 401:
                        self.health_status = "auth_failed"
                        logger.error(f"Regfyl authentication failed: {response_data}")
                        raise HTTPException(status_code=401, detail="Regfyl authentication failed")
                    elif response.status == 429:
                        if retries < self.max_retries:
                            wait_time = 2 ** retries
                            logger.warning(f"Rate limited, retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            return await self._make_request(endpoint, payload, retries + 1)
                        else:
                            raise HTTPException(status_code=429, detail="Rate limit exceeded")
                    else:
                        error_msg = response_data.get('message', f'HTTP {response.status}')
                        logger.error(f"Regfyl API error: {error_msg}")
                        raise HTTPException(status_code=500, detail=f"Regfyl error: {error_msg}")
                        
        except asyncio.TimeoutError:
            if retries < self.max_retries:
                await asyncio.sleep(2 ** retries)
                return await self._make_request(endpoint, payload, retries + 1)
            raise HTTPException(status_code=408, detail="Regfyl service timeout")
        except Exception as e:
            logger.error(f"Regfyl API request failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Regfyl service unavailable")
    
    def _simulate_response(self, endpoint: str, data: Dict) -> Dict:
        """Simulate Regfyl responses for testing"""
        if "customerScreening" in endpoint:
            return {
                "reference": f"REG_SIM_{uuid.uuid4().hex[:8]}",
                "status": "success",
                "message": "Customer screening initiated (simulation)",
                "customerID": data.get("customerID")
            }
        elif "postTransaction" in endpoint:
            return {
                "reference": f"TXN_SIM_{uuid.uuid4().hex[:8]}",
                "status": "success", 
                "message": "Transaction monitoring initiated (simulation)",
                "transactionReference": data.get("transactionReference")
            }
        elif "postRiskAssessment" in endpoint:
            return {
                "reference": f"BIZ_SIM_{uuid.uuid4().hex[:8]}",
                "status": "success",
                "message": "Business screening initiated (simulation)"
            }
        return {"status": "simulated", "message": "Running in simulation mode"}
    
    # ============================================================================
    # CUSTOMER SCREENING METHODS
    # ============================================================================
    
    async def screen_individual_customer(
        self, 
        customer_id: str, 
        customer_name: str, 
        year_of_birth: str,
        gender: str = '',
        callback_url: str = None
    ) -> Dict:
        """Screen individual customer for PEP, Sanctions, and Adverse Media"""
        settings = get_settings()
        callback_url = callback_url or f"{settings.API_BASE_URL}/webhooks/regfyl/screening"
        
        payload = {
            'companyName': self.company_name,
            'rcNumber': self.rc_number,
            'customerID': customer_id,
            'customerType': 'INDIVIDUAL',
            'customerName': customer_name,
            'YOB': year_of_birth,
            'gender': gender,
            'recurringCheck': 'NO',
            'environment': self.environment,
            'callbackURL': callback_url
        }
        
        try:
            result = await self._make_request('postCustomerScreening', payload)  # Fixed endpoint
            logger.info(f"Customer screening initiated for {customer_id}")
            return result
        except Exception as e:
            logger.error(f"Customer screening failed for {customer_id}: {e}")
            raise

    async def verify_nigerian_id(
        self, 
        customer_id: str, 
        customer_name: str, 
        year_of_birth: str,
        id_type: str,  # 'BVN', 'NIN', 'PHONE_NUMBER'
        id_number: str,
        callback_url: str = None
    ) -> Dict:
        """Verify Nigerian ID (BVN/NIN) with comprehensive screening"""
        settings = get_settings()
        callback_url = callback_url or f"{settings.API_BASE_URL}/webhooks/regfyl/id-verification"
        
        payload = {
            'companyName': self.company_name,
            'rcNumber': self.rc_number,
            'customerID': customer_id,
            'customerType': 'INDIVIDUAL',
            'customerName': customer_name,
            'YOB': year_of_birth,
            'verifyID': 'YES',
            'country': 'NG',
            'idType': id_type,
            'idNumber': id_number,
            'environment': self.environment,
            'callbackURL': callback_url
        }
        
        try:
            result = await self._make_request('customerScreening', payload)
            logger.info(f"ID verification initiated for {customer_id}")
            return result
        except Exception as e:
            logger.error(f"ID verification failed for {customer_id}: {e}")
            raise

    # ============================================================================
    # TRANSACTION MONITORING METHODS
    # ============================================================================
    
    async def monitor_transaction(
        self,
        customer_id: str,
        customer_name: str,
        transaction_amount: float,
        currency: str,
        transaction_type: str,  # 'INFLOW' or 'OUTFLOW'
        transaction_channel: str,  # 'VIRTUAL_WALLET'
        transaction_reference: str,
        customer_dob: str = None,
        customer_gender: str = None,
        customer_nationality: str = None,
        phone_number: str = None,
        transaction_location: str = None,
        transaction_country: str = 'NG',
        destination_country: str = None,
        purpose: str = None,
        callback_url: str = None,
        **kwargs
    ) -> Dict:
        """Monitor transaction for suspicious activity and AML compliance"""
        settings = get_settings()
        callback_url = callback_url or f"{settings.API_BASE_URL}/webhooks/regfyl/transaction-monitoring"
        
        payload = {
            'companyName': self.company_name,
            'rcNumber': self.rc_number,
            'customerID': customer_id,
            'transactionAmount': transaction_amount,
            'currency': currency,
            'transactionStatus': 'SUCCESSFUL',
            'transactionChannel': transaction_channel,
            'authenticated': 'YES',
            'customerType': 'INDIVIDUAL',
            'transactionType': transaction_type,
            'environment': self.environment,
            'customerName': customer_name,
            'transactionReference': transaction_reference,
            'callbackURL': callback_url
        }
        
        # Add optional fields
        optional_fields = {
            'customerDOB': customer_dob,
            'customerGender': customer_gender,
            'customerNationality': customer_nationality,
            'phoneNo': phone_number,
            'transactionLocation': transaction_location,
            'transactionCountry': transaction_country,
            'destinationCountry': destination_country,
            'purpose': purpose
        }
        
        for key, value in optional_fields.items():
            if value:
                payload[key] = value
        
        try:
            result = await self._make_request('postTransaction', payload)
            logger.info(f"Transaction monitoring completed for {transaction_reference}")
            return result
        except Exception as e:
            logger.error(f"Transaction monitoring failed for {transaction_reference}: {e}")
            raise

    # ============================================================================
    # BUSINESS SCREENING METHODS
    # ============================================================================
    
    async def screen_business(
        self,
        customer_id: str,
        registration_country: str,
        registration_number: str,
        address_verification: bool = False,
        monitoring_frequency: str = 'once-off',
        callback_url: str = None
    ) -> Dict:
        """Screen business entity for compliance"""
        settings = get_settings()
        callback_url = callback_url or f"{settings.API_BASE_URL}/webhooks/regfyl/business-screening"
        
        payload = {
            'companyName': self.company_name,
            'rcNumber': self.rc_number,
            'customerID': customer_id,
            'formType': 'C-GRA',
            'environment': self.environment,
            'registrationCountry': registration_country,
            'registrationNumber': registration_number,
            'addressVerification': 'Yes' if address_verification else 'No',
            'monitoringFrequency': monitoring_frequency,
            'callbackURL': callback_url
        }
        
        try:
            result = await self._make_request('postRiskAssessment', payload)
            logger.info(f"Business screening initiated for {customer_id}")
            return result
        except Exception as e:
            logger.error(f"Business screening failed for {customer_id}: {e}")
            raise

    # ============================================================================
    # SEAMOUNT.IO INTEGRATION HELPERS
    # ============================================================================
    
    async def onboard_seamount_user(self, user_data: Dict) -> Dict:
        """Complete onboarding flow for Seamount.io users"""
        customer_id = user_data['customer_id']
        results = {}
        
        try:
            # Basic customer screening
            screening_result = await self.screen_individual_customer(
                customer_id=customer_id,
                customer_name=user_data['full_name'],
                year_of_birth=user_data['year_of_birth'],
                gender=user_data.get('gender', ''),
                callback_url=user_data.get('callback_url')
            )
            results['screening'] = screening_result
            
            # Nigerian ID verification
            if user_data.get('country') == 'NG' and user_data.get('id_number'):
                id_result = await self.verify_nigerian_id(
                    customer_id=customer_id,
                    customer_name=user_data['full_name'],
                    year_of_birth=user_data['year_of_birth'],
                    id_type=user_data['id_type'],
                    id_number=user_data['id_number'],
                    callback_url=user_data.get('callback_url')
                )
                results['id_verification'] = id_result
            
            logger.info(f"Seamount user onboarding initiated for {customer_id}")
            return results
            
        except Exception as e:
            logger.error(f"Seamount user onboarding failed for {customer_id}: {e}")
            raise

    async def monitor_seamount_transaction(self, transaction_data: Dict) -> Dict:
        """Monitor Seamount.io transactions (USDS transfers, swaps, etc.)"""
        return await self.monitor_transaction(
            customer_id=transaction_data['user_id'],
            customer_name=transaction_data['user_name'],
            transaction_amount=transaction_data['amount'],
            currency=transaction_data.get('currency', 'USD'),
            transaction_type='OUTFLOW' if transaction_data['type'] == 'send' else 'INFLOW',
            transaction_channel='VIRTUAL_WALLET',
            transaction_reference=transaction_data['transaction_id'],
            customer_dob=transaction_data.get('date_of_birth'),
            phone_number=transaction_data.get('phone'),
            transaction_country=transaction_data.get('sender_country', 'NG'),
            destination_country=transaction_data.get('recipient_country'),
            purpose=transaction_data.get('purpose', 'Cross-border payment')
        )

    # ============================================================================
    # HEALTH & MONITORING
    # ============================================================================
    
    async def health_check(self) -> Dict:
        """Check service health without making API calls"""
        try:
            self.last_health_check = datetime.utcnow().isoformat()
            
            if self.simulation_mode:
                self.health_status = "simulation_mode"
                return {"status": "healthy", "mode": "simulation"}
            
            # Validate configuration
            if not all([self.api_key, self.company_name, self.rc_number]):
                self.health_status = "config_incomplete"
                return {"status": "unhealthy", "error": "Configuration incomplete"}
            
            self.health_status = "healthy"
            return {"status": "healthy", "provider": "regfyl"}
            
        except Exception as e:
            self.health_status = "error"
            return {"status": "unhealthy", "error": str(e)}
    
    def get_health_status(self) -> Dict:
        """Get comprehensive health status"""
        return {
            "service": "Regfyl KYC/AML",
            "status": self.health_status,
            "simulation_mode": self.simulation_mode,
            "initialization_status": self.initialization_status,
            "last_health_check": self.last_health_check,
            "api_key_configured": bool(self.api_key),
            "company_configured": bool(self.company_name and self.rc_number),
            "base_url": self.base_url,
            "environment": self.environment
        }
    
    def parse_callback(self, callback_data: Dict) -> Dict:
        """Parse and categorize Regfyl callback data"""
        check_type = callback_data.get('checkType', '')
        status = callback_data.get('status', '')
        
        result = {
            'customer_id': callback_data.get('customerID'),
            'reference': callback_data.get('reference'),
            'check_type': check_type,
            'status': status,
            'action_required': False,
            'risk_level': callback_data.get('rulePriority', 'LOW')
        }
        
        # Determine action requirements
        action_statuses = [
            'Reviewed - Further action required',
            'Reviewed - Declined', 
            'Reviewed - Ready for filing'
        ]
        
        if status in action_statuses or callback_data.get('likelyFraud') == 'Yes':
            result['action_required'] = True
            result['risk_level'] = 'HIGH'
        
        return result

# Export service instance
regfyl_service = RegfylVerifier()