# File: backend/services/onramp_aggregator_service.py
"""
On-Ramp Aggregator - Multi-Provider Fiat→Crypto Gateway
Integrates TransFi, MoonPay, Transak, Alchemy Pay without API keys
Revenue: 2.5% on all conversions
"""

import logging
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime
from uuid import uuid4
import aiohttp
from fastapi import HTTPException

from backend.config import settings
from backend.services.database_service import DatabaseService
from backend.services.audit_service import AuditService

logger = logging.getLogger(__name__)

class OnRampProvider:
    """Base provider configuration"""
    TRANSFI = "transfi"
    MOONPAY = "moonpay"
    TRANSAK = "transak"
    ALCHEMY_PAY = "alchemy_pay"
    ONRAMP_MONEY = "onramp_money"

class OnRampAggregatorService:
    """
    Production-ready on-ramp aggregator with intelligent routing
    No API keys needed - uses public checkout URLs + webhook monitoring
    """
    
    def __init__(self, db_service: DatabaseService, audit_service: AuditService):
        self.db = db_service
        self.audit = audit_service
        
        # Revenue configuration
        self.fee_rate = Decimal("0.025")  # 2.5%
        self.min_fee = Decimal("1.50")  # $1.50 minimum
        
        # Provider configs (public endpoints)
        self.providers = {
            OnRampProvider.TRANSFI: {
                "name": "TransFi",
                "checkout_url": "https://checkout.transfi.com",
                "supported_currencies": ["NGN", "KES", "GHS", "ZAR", "USD", "EUR", "GBP"],
                "supported_crypto": ["USDT", "USDCa", "ALGO"],
                "fee_estimate": "1.5%",
                "settlement_time": "5-15 minutes",
                "limits": {"min": 10, "max": 10000}
            },
            OnRampProvider.MOONPAY: {
                "name": "MoonPay",
                "checkout_url": "https://buy.moonpay.com",
                "supported_currencies": ["NGN", "KES", "USD", "EUR", "GBP"],
                "supported_crypto": ["USDT", "USDCa", "ALGO"],
                "fee_estimate": "3.5%",
                "settlement_time": "10-20 minutes",
                "limits": {"min": 20, "max": 20000}
            },
            OnRampProvider.TRANSAK: {
                "name": "Transak",
                "checkout_url": "https://global.transak.com",
                "supported_currencies": ["NGN", "KES", "GHS", "ZAR", "USD", "EUR", "GBP"],
                "supported_crypto": ["USDT", "USDCa", "ALGO"],
                "fee_estimate": "2.5%",
                "settlement_time": "5-10 minutes",
                "limits": {"min": 30, "max": 15000}
            },
            OnRampProvider.ALCHEMY_PAY: {
                "name": "Alchemy Pay",
                "checkout_url": "https://ramp.alchemypay.org",
                "supported_currencies": ["NGN", "KES", "USD", "EUR"],
                "supported_crypto": ["USDT", "USDCa"],
                "fee_estimate": "2.0%",
                "settlement_time": "10-15 minutes",
                "limits": {"min": 10, "max": 50000}
            },
            OnRampProvider.ONRAMP_MONEY: {
                "name": "Onramp.money",
                "checkout_url": "https://app.onramp.money",
                "supported_currencies": ["NGN", "KES", "GHS", "ZAR", "USD"],
                "supported_crypto": ["USDT", "USDCa", "ALGO"],
                "fee_estimate": "1.8%",
                "settlement_time": "5-10 minutes",
                "limits": {"min": 15, "max": 25000}
            }
        }
        
        logger.info("OnRampAggregatorService initialized with 5 providers")
    
    def _calculate_seamount_fee(self, amount_usd: Decimal) -> Dict[str, Decimal]:
        """Calculate Seamount's 2.5% revenue fee"""
        fee = amount_usd * self.fee_rate
        if fee < self.min_fee:
            fee = self.min_fee
        
        net_amount = amount_usd - fee
        
        return {
            "gross_amount": amount_usd,
            "seamount_fee": fee,
            "net_to_user": net_amount,
            "effective_rate": (fee / amount_usd * 100) if amount_usd > 0 else Decimal("0")
        }
    
    def _select_optimal_provider(
        self, 
        currency: str, 
        crypto: str, 
        amount_usd: float,
        user_country: str
    ) -> str:
        """
        Intelligent provider selection based on:
        - Currency support
        - Fees
        - Limits
        - Geographic optimization
        """
        
        viable_providers = []
        
        for provider_id, config in self.providers.items():
            # Check currency and crypto support
            if currency not in config["supported_currencies"]:
                continue
            if crypto not in config["supported_crypto"]:
                continue
            
            # Check limits
            if amount_usd < config["limits"]["min"] or amount_usd > config["limits"]["max"]:
                continue
            
            viable_providers.append((provider_id, config))
        
        if not viable_providers:
            raise ValueError(f"No provider supports {currency}→{crypto} for ${amount_usd}")
        
        # Geographic optimization
        priority_map = {
            "NG": [OnRampProvider.ALCHEMY_PAY, OnRampProvider.TRANSFI, OnRampProvider.ONRAMP_MONEY],
            "KE": [OnRampProvider.TRANSFI, OnRampProvider.ONRAMP_MONEY, OnRampProvider.MOONPAY],
            "GH": [OnRampProvider.TRANSAK, OnRampProvider.TRANSFI],
            "ZA": [OnRampProvider.MOONPAY, OnRampProvider.TRANSAK]
        }
        
        country_priorities = priority_map.get(user_country, [])
        
        # Return highest priority provider
        for priority_provider in country_priorities:
            if any(p[0] == priority_provider for p in viable_providers):
                return priority_provider
        
        # Fallback: lowest fee provider
        return min(viable_providers, key=lambda x: float(x[1]["fee_estimate"].replace("%", "")))[0]
    
    async def initialize_onramp(
        self,
        user_id: str,
        user_email: str,
        amount_fiat: float,
        currency: str,
        crypto_asset: str,
        user_wallet_address: str,
        user_country: str = "NG"
    ) -> Dict[str, Any]:
        """
        Initialize on-ramp transaction with optimal provider
        Returns checkout URL for user to complete payment
        """
        
        try:
            # Generate unique transaction ID
            transaction_id = f"ONRAMP_{uuid4().hex[:12].upper()}"
            
            # Calculate fees
            amount_usd = Decimal(str(amount_fiat))  # Assuming USD equivalent
            fee_breakdown = self._calculate_seamount_fee(amount_usd)
            
            # Select optimal provider
            provider_id = self._select_optimal_provider(
                currency, crypto_asset, float(amount_usd), user_country
            )
            
            provider_config = self.providers[provider_id]
            
            # Generate provider checkout URL (public, no API key)
            checkout_url = self._generate_checkout_url(
                provider_id=provider_id,
                transaction_id=transaction_id,
                wallet_address=user_wallet_address,
                crypto=crypto_asset,
                currency=currency,
                amount=float(amount_usd),
                user_email=user_email
            )
            
            # Store transaction in database
            tx_data = {
                "id": transaction_id,
                "user_id": user_id,
                "type": "onramp",
                "status": "pending_payment",
                "provider": provider_id,
                "provider_name": provider_config["name"],
                "currency": currency,
                "crypto_asset": crypto_asset,
                "amount_fiat": float(amount_usd),
                "seamount_fee": float(fee_breakdown["seamount_fee"]),
                "net_to_user": float(fee_breakdown["net_to_user"]),
                "wallet_address": user_wallet_address,
                "checkout_url": checkout_url,
                "user_email": user_email,
                "user_country": user_country,
                "estimated_settlement": provider_config["settlement_time"],
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.db.log_event("onramp_transactions", tx_data)
            
            # Log audit event
            await self.audit.log_event(
                "ONRAMP_INITIATED",
                user_id=user_id,
                resource_id=transaction_id,
                details={
                    "provider": provider_id,
                    "amount_fiat": float(amount_usd),
                    "currency": currency,
                    "crypto": crypto_asset,
                    "seamount_fee": float(fee_breakdown["seamount_fee"])
                }
            )
            
            logger.info(f"On-ramp initialized: {transaction_id} via {provider_id}")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "checkout_url": checkout_url,
                "provider": provider_config["name"],
                "amount_fiat": float(amount_usd),
                "currency": currency,
                "crypto_asset": crypto_asset,
                "seamount_fee": float(fee_breakdown["seamount_fee"]),
                "net_amount": float(fee_breakdown["net_to_user"]),
                "estimated_crypto_amount": float(fee_breakdown["net_to_user"]),  # 1:1 for stables
                "estimated_settlement": provider_config["settlement_time"],
                "expires_at": (datetime.utcnow().timestamp() + 3600)  # 1 hour expiry
            }
            
        except Exception as e:
            logger.error(f"On-ramp initialization failed: {e}")
            raise HTTPException(status_code=500, detail=f"On-ramp initialization failed: {str(e)}")
    
    def _generate_checkout_url(
        self,
        provider_id: str,
        transaction_id: str,
        wallet_address: str,
        crypto: str,
        currency: str,
        amount: float,
        user_email: str
    ) -> str:
        """
        Generate provider-specific checkout URL (public, no API)
        """
        
        base_url = self.providers[provider_id]["checkout_url"]
        
        # Provider-specific URL construction
        if provider_id == OnRampProvider.TRANSFI:
            return (
                f"{base_url}?"
                f"cryptoCurrency={crypto}"
                f"&fiatCurrency={currency}"
                f"&fiatAmount={amount}"
                f"&walletAddress={wallet_address}"
                f"&email={user_email}"
                f"&network=algorand"
                f"&redirectURL={settings.FRONTEND_URL}/onramp/success?tx={transaction_id}"
            )
        
        elif provider_id == OnRampProvider.MOONPAY:
            return (
                f"{base_url}?"
                f"currencyCode={crypto.lower()}"
                f"&baseCurrencyCode={currency.lower()}"
                f"&baseCurrencyAmount={amount}"
                f"&walletAddress={wallet_address}"
                f"&email={user_email}"
                f"&externalTransactionId={transaction_id}"
                f"&redirectURL={settings.FRONTEND_URL}/onramp/success"
            )
        
        elif provider_id == OnRampProvider.TRANSAK:
            return (
                f"{base_url}?"
                f"cryptoCurrencyCode={crypto}"
                f"&fiatCurrency={currency}"
                f"&fiatAmount={amount}"
                f"&walletAddress={wallet_address}"
                f"&email={user_email}"
                f"&network=algorand"
                f"&partnerOrderId={transaction_id}"
                f"&redirectURL={settings.FRONTEND_URL}/onramp/success"
            )
        
        elif provider_id == OnRampProvider.ALCHEMY_PAY:
            return (
                f"{base_url}?"
                f"crypto={crypto}"
                f"&fiat={currency}"
                f"&amount={amount}"
                f"&address={wallet_address}"
                f"&email={user_email}"
                f"&network=ALGO"
                f"&orderId={transaction_id}"
            )
        
        elif provider_id == OnRampProvider.ONRAMP_MONEY:
            return (
                f"{base_url}?"
                f"asset={crypto}"
                f"&currency={currency}"
                f"&amount={amount}"
                f"&wallet={wallet_address}"
                f"&email={user_email}"
                f"&ref={transaction_id}"
            )
        
        else:
            raise ValueError(f"Unknown provider: {provider_id}")
    
    async def handle_webhook(self, provider: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle provider webhook callbacks
        Updates transaction status and credits user balance
        """
        
        try:
            # Extract transaction ID from payload (provider-specific)
            transaction_id = self._extract_transaction_id(provider, payload)
            
            if not transaction_id:
                raise ValueError("Transaction ID not found in webhook payload")
            
            # Get transaction from database
            query = "SELECT * FROM onramp_transactions WHERE id = %s"
            result = await self.db.execute_query(query, (transaction_id,))
            
            if not result:
                raise ValueError(f"Transaction not found: {transaction_id}")
            
            tx_data = result[0]
            
            # Determine webhook event type
            event_status = self._parse_webhook_status(provider, payload)
            
            if event_status == "completed":
                # Credit user balance
                await self._credit_user_balance(
                    user_id=tx_data["user_id"],
                    crypto_asset=tx_data["crypto_asset"],
                    amount=Decimal(str(tx_data["net_to_user"])),
                    transaction_id=transaction_id
                )
                
                # Update transaction status
                update_query = """
                    UPDATE onramp_transactions 
                    SET status = 'completed', completed_at = NOW(), webhook_data = %s
                    WHERE id = %s
                """
                await self.db.execute_query(update_query, (str(payload), transaction_id))
                
                # Record revenue
                await self._record_revenue(
                    user_id=tx_data["user_id"],
                    transaction_id=transaction_id,
                    amount=Decimal(str(tx_data["seamount_fee"])),
                    source="onramp_fee"
                )
                
                logger.info(f"On-ramp completed: {transaction_id}")
                
            elif event_status == "failed":
                update_query = """
                    UPDATE onramp_transactions 
                    SET status = 'failed', failed_at = NOW(), webhook_data = %s
                    WHERE id = %s
                """
                await self.db.execute_query(update_query, (str(payload), transaction_id))
                
                logger.warning(f"On-ramp failed: {transaction_id}")
            
            return {"success": True, "transaction_id": transaction_id, "status": event_status}
            
        except Exception as e:
            logger.error(f"Webhook handling failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _extract_transaction_id(self, provider: str, payload: Dict) -> Optional[str]:
        """Extract transaction ID from provider webhook payload"""
        
        mapping = {
            OnRampProvider.TRANSFI: "externalId",
            OnRampProvider.MOONPAY: "externalTransactionId",
            OnRampProvider.TRANSAK: "partnerOrderId",
            OnRampProvider.ALCHEMY_PAY: "orderId",
            OnRampProvider.ONRAMP_MONEY: "reference"
        }
        
        field = mapping.get(provider)
        return payload.get(field) if field else None
    
    def _parse_webhook_status(self, provider: str, payload: Dict) -> str:
        """Parse webhook status into standardized format"""
        
        status = payload.get("status", "").lower()
        
        completed_statuses = ["completed", "success", "finished", "settled"]
        failed_statuses = ["failed", "cancelled", "rejected", "expired"]
        
        if any(s in status for s in completed_statuses):
            return "completed"
        elif any(s in status for s in failed_statuses):
            return "failed"
        else:
            return "pending"
    
    async def _credit_user_balance(
        self, 
        user_id: str, 
        crypto_asset: str, 
        amount: Decimal,
        transaction_id: str
    ):
        """Credit user's wallet balance"""
        
        # Get current balance
        query = f"SELECT {crypto_asset.lower()}_balance FROM wallet_balances WHERE user_id = %s"
        result = await self.db.execute_query(query, (user_id,))
        
        current_balance = Decimal(str(result[0][f"{crypto_asset.lower()}_balance"])) if result else Decimal("0")
        new_balance = current_balance + amount
        
        # Update balance
        update_query = f"""
            UPDATE wallet_balances 
            SET {crypto_asset.lower()}_balance = %s, updated_at = NOW()
            WHERE user_id = %s
        """
        await self.db.execute_query(update_query, (float(new_balance), user_id))
        
        logger.info(f"Credited {amount} {crypto_asset} to user {user_id}")
    
    async def _record_revenue(
        self, 
        user_id: str, 
        transaction_id: str, 
        amount: Decimal, 
        source: str
    ):
        """Record revenue in analytics"""
        
        revenue_data = {
            "user_id": user_id,
            "transaction_id": transaction_id,
            "amount": float(amount),
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.db.log_event("revenue", revenue_data)
    
    async def get_supported_providers(
        self, 
        currency: Optional[str] = None, 
        crypto: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of supported providers with filtering"""
        
        providers_list = []
        
        for provider_id, config in self.providers.items():
            # Apply filters
            if currency and currency not in config["supported_currencies"]:
                continue
            if crypto and crypto not in config["supported_crypto"]:
                continue
            
            providers_list.append({
                "id": provider_id,
                "name": config["name"],
                "supported_currencies": config["supported_currencies"],
                "supported_crypto": config["supported_crypto"],
                "fee_estimate": config["fee_estimate"],
                "settlement_time": config["settlement_time"],
                "limits": config["limits"]
            })
        
        return providers_list