# File: backend/services/offramp_service.py
"""
Off-Ramp Service - Crypto→Fiat Withdrawals
Integrates Paystack (NGN banks), Cashramp (M-Pesa/Airtel Money)
Revenue: 2.8% on all withdrawals
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException

from backend.config import settings
from backend.services.database_service import DatabaseService
from backend.services.audit_service import AuditService
from backend.services.payment_providers.paystack import PaystackProvider
from backend.services.cashramp_service import CashrampService
from backend.services.oracle_service import EnhancedOracleService

logger = logging.getLogger(__name__)

class OfframpChannel:
    BANK_TRANSFER = "bank_transfer"
    MOBILE_MONEY = "mobile_money"
    CARD = "card"

class OfframpService:
    """
    Production-ready off-ramp service with intelligent routing
    Handles bank withdrawals and mobile money payouts
    """
    
    def __init__(
        self, 
        db_service: DatabaseService, 
        audit_service: AuditService,
        paystack: PaystackProvider,
        cashramp: CashrampService,
        oracle: EnhancedOracleService
    ):
        self.db = db_service
        self.audit = audit_service
        self.paystack = paystack
        self.cashramp = cashramp
        self.oracle = oracle
        
        # Revenue configuration
        self.fee_rate = Decimal("0.018")  # 1.8%
        self.min_fee = Decimal("2.00")  # $2.00 minimum
        
        # Channel configurations
        self.channels = {
            "NG": {
                "bank_transfer": {
                    "provider": "paystack",
                    "currencies": ["NGN"],
                    "settlement_time": "10-30 minutes",
                    "limits": {"min": 1000, "max": 5000000}  # 1K-5M NGN
                }
            },
            "KE": {
                "mobile_money": {
                    "provider": "cashramp",
                    "currencies": ["KES"],
                    "networks": ["mpesa", "airtel_money"],
                    "settlement_time": "1-5 minutes",
                    "limits": {"min": 100, "max": 500000}  # 100-500K KES
                }
            },
            "UG": {
                "mobile_money": {
                    "provider": "cashramp",
                    "currencies": ["UGX"],
                    "networks": ["airtel_money", "mtn_money"],
                    "settlement_time": "1-5 minutes",
                    "limits": {"min": 5000, "max": 5000000}  # 5K-5M UGX
                }
            },
            "GH": {
                "mobile_money": {
                    "provider": "cashramp",
                    "currencies": ["GHS"],
                    "networks": ["mtn_momo", "vodafone_cash"],
                    "settlement_time": "1-5 minutes",
                    "limits": {"min": 10, "max": 50000}  # 10-50K GHS
                }
            },
            "ZA": {
                "bank_transfer": {
                    "provider": "cashramp",
                    "currencies": ["ZAR"],
                    "settlement_time": "5-15 minutes",
                    "limits": {"min": 100, "max": 500000}  # 100-500K ZAR
                }
            }
        }
        
        logger.info("OfframpService initialized with multi-channel support")
    
    def _calculate_seamount_fee(self, amount_crypto: Decimal, asset: str) -> Dict[str, Decimal]:
        """Calculate Seamount's 2.8% withdrawal fee"""
        fee = amount_crypto * self.fee_rate
        if fee < self.min_fee:
            fee = self.min_fee
        
        net_amount = amount_crypto - fee
        
        return {
            "gross_amount": amount_crypto,
            "seamount_fee": fee,
            "net_to_user": net_amount,
            "effective_rate": (fee / amount_crypto * 100) if amount_crypto > 0 else Decimal("0")
        }
    
    async def _get_fiat_equivalent(
        self, 
        crypto_amount: Decimal, 
        crypto_asset: str, 
        fiat_currency: str
    ) -> Decimal:
        """Convert crypto to fiat using oracle prices"""
        
        # Get crypto USD price
        if crypto_asset in ["USDT", "USDCa", ]:
            usd_value = crypto_amount  # Stablecoins are 1:1
        else:
            asset_map = {"goBTC": "bitcoin", "goETH": "ethereum", "ALGO": "algorand"}
            oracle_asset = asset_map.get(crypto_asset, crypto_asset.lower())
            
            price, _ = await self.oracle.get_asset_price(oracle_asset)
            usd_value = crypto_amount * price
        
        # Convert USD to target fiat
        if fiat_currency == "USD":
            return usd_value
        
        # Get fiat exchange rate
        fiat_rates = {
            "NGN": Decimal("1620"),  # USD/NGN
            "KES": Decimal("150"),   # USD/KES
            "GHS": Decimal("12"),    # USD/GHS
            "ZAR": Decimal("18"),    # USD/ZAR
            "UGX": Decimal("3700")   # USD/UGX
        }
        
        rate = fiat_rates.get(fiat_currency, Decimal("1"))
        return usd_value * rate
    
    def _select_withdrawal_channel(
        self, 
        country: str, 
        payment_method: str
    ) -> Dict[str, Any]:
        """Select optimal withdrawal channel based on country and method"""
        
        country_channels = self.channels.get(country)
        if not country_channels:
            raise ValueError(f"Off-ramp not supported for country: {country}")
        
        channel = country_channels.get(payment_method)
        if not channel:
            available = list(country_channels.keys())
            raise ValueError(f"Payment method {payment_method} not available. Use: {available}")
        
        return channel
    
    async def initialize_withdrawal(
        self,
        user_id: str,
        crypto_asset: str,
        crypto_amount: float,
        recipient_details: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Initialize crypto→fiat withdrawal
        
        recipient_details format:
        - For bank: {country, currency, account_number, account_name, bank_code, payment_method}
        - For mobile: {country, currency, phone_number, network, payment_method}
        """
        
        try:
            transaction_id = f"OFFRAMP_{uuid4().hex[:12].upper()}"
            
            # Validate user balance
            amount = Decimal(str(crypto_amount))
            await self._validate_balance(user_id, crypto_asset, amount)
            
            # Calculate fees
            fee_breakdown = self._calculate_seamount_fee(amount, crypto_asset)
            
            # Get fiat equivalent
            country = recipient_details["country"]
            currency = recipient_details["currency"]
            payment_method = recipient_details["payment_method"]
            
            fiat_amount = await self._get_fiat_equivalent(
                fee_breakdown["net_to_user"], 
                crypto_asset, 
                currency
            )
            
            # Select channel
            channel = self._select_withdrawal_channel(country, payment_method)
            
            # Check limits
            if fiat_amount < channel["limits"]["min"] or fiat_amount > channel["limits"]["max"]:
                raise ValueError(
                    f"Amount {fiat_amount} {currency} outside limits: "
                    f"{channel['limits']['min']}-{channel['limits']['max']}"
                )
            
            # Store transaction
            tx_data = {
                "id": transaction_id,
                "user_id": user_id,
                "type": "offramp",
                "status": "processing",
                "crypto_asset": crypto_asset,
                "crypto_amount": float(amount),
                "seamount_fee": float(fee_breakdown["seamount_fee"]),
                "net_crypto_amount": float(fee_breakdown["net_to_user"]),
                "fiat_currency": currency,
                "fiat_amount": float(fiat_amount),
                "country": country,
                "payment_method": payment_method,
                "provider": channel["provider"],
                "recipient_details": recipient_details,
                "estimated_settlement": channel["settlement_time"],
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.db.log_event("offramp_transactions", tx_data)
            
            # Debit user balance immediately
            await self._debit_user_balance(user_id, crypto_asset, amount, transaction_id)
            
            # Execute withdrawal via provider
            if channel["provider"] == "paystack":
                result = await self._execute_paystack_withdrawal(
                    transaction_id, recipient_details, fiat_amount
                )
            elif channel["provider"] == "cashramp":
                result = await self._execute_cashramp_withdrawal(
                    transaction_id, recipient_details, fiat_amount, crypto_asset, payment_method
                )
            else:
                raise ValueError(f"Unknown provider: {channel['provider']}")
            
            # Update with provider reference
            update_query = """
                UPDATE offramp_transactions 
                SET provider_tx_id = %s, provider_response = %s
                WHERE id = %s
            """
            await self.db.execute_query(
                update_query, 
                (result.get("reference"), str(result), transaction_id)
            )
            
            # Log audit
            await self.audit.log_event(
                "OFFRAMP_INITIATED",
                user_id=user_id,
                resource_id=transaction_id,
                details={
                    "crypto_asset": crypto_asset,
                    "crypto_amount": float(amount),
                    "fiat_currency": currency,
                    "fiat_amount": float(fiat_amount),
                    "seamount_fee": float(fee_breakdown["seamount_fee"])
                }
            )
            
            logger.info(f"Off-ramp initialized: {transaction_id}")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": "processing",
                "crypto_amount": float(amount),
                "crypto_asset": crypto_asset,
                "fiat_amount": float(fiat_amount),
                "fiat_currency": currency,
                "seamount_fee": float(fee_breakdown["seamount_fee"]),
                "net_crypto_amount": float(fee_breakdown["net_to_user"]),
                "estimated_settlement": channel["settlement_time"],
                "provider": channel["provider"]
            }
            
        except Exception as e:
            logger.error(f"Withdrawal initialization failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _validate_balance(self, user_id: str, asset: str, amount: Decimal):
        """Validate user has sufficient balance"""
        
        query = f"SELECT {asset.lower()}_balance FROM wallet_balances WHERE user_id = %s"
        result = await self.db.execute_query(query, (user_id,))
        
        if not result:
            raise HTTPException(status_code=400, detail="Wallet not found")
        
        balance = Decimal(str(result[0][f"{asset.lower()}_balance"]))
        
        if balance < amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient {asset} balance. Available: {balance}, Required: {amount}"
            )
    
    async def _debit_user_balance(
        self, 
        user_id: str, 
        asset: str, 
        amount: Decimal,
        transaction_id: str
    ):
        """Debit user wallet balance"""
        
        query = f"SELECT {asset.lower()}_balance FROM wallet_balances WHERE user_id = %s"
        result = await self.db.execute_query(query, (user_id,))
        
        current_balance = Decimal(str(result[0][f"{asset.lower()}_balance"]))
        new_balance = current_balance - amount
        
        update_query = f"""
            UPDATE wallet_balances 
            SET {asset.lower()}_balance = %s, updated_at = NOW()
            WHERE user_id = %s
        """
        await self.db.execute_query(update_query, (float(new_balance), user_id))
        
        logger.info(f"Debited {amount} {asset} from user {user_id}")
    
    async def _execute_paystack_withdrawal(
        self, 
        transaction_id: str, 
        recipient_details: Dict, 
        amount: Decimal
    ) -> Dict[str, Any]:
        """Execute NGN bank withdrawal via Paystack"""
        
        bank_details = {
            "account_name": recipient_details["account_name"],
            "account_number": recipient_details["account_number"],
            "bank_code": recipient_details["bank_code"]
        }
        
        result = await self.paystack.initiate_payout(
            amount=amount,
            bank_details=bank_details,
            tx_ref=transaction_id
        )
        
        if not result.get("success"):
            raise Exception(f"Paystack payout failed: {result.get('message')}")
        
        return result
    
    async def _execute_cashramp_withdrawal(
        self,
        transaction_id: str,
        recipient_details: Dict,
        amount: Decimal,
        crypto_asset: str,
        payment_method: str
    ) -> Dict[str, Any]:
        """Execute withdrawal via Cashramp (mobile money or bank)"""
        
        result = await self.cashramp.send_cross_border_payment(
            sender_user_id=transaction_id,  # Use tx_id as sender reference
            recipient_country=recipient_details["country"],
            asset=crypto_asset,
            amount_usd=amount,
            recipient_details=recipient_details
        )
        
        if not result.get("success"):
            raise Exception(f"Cashramp payout failed: {result.get('error')}")
        
        return result
    
    async def handle_payout_webhook(
        self, 
        provider: str, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle provider payout webhooks"""
        
        try:
            # Extract transaction ID
            if provider == "paystack":
                tx_id = payload.get("data", {}).get("reference")
                status = payload.get("data", {}).get("status")
            elif provider == "cashramp":
                tx_id = payload.get("transfer_id")
                status = payload.get("status")
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            if not tx_id:
                raise ValueError("Transaction ID not found in webhook")
            
            # Get transaction
            query = "SELECT * FROM offramp_transactions WHERE id = %s"
            result = await self.db.execute_query(query, (tx_id,))
            
            if not result:
                raise ValueError(f"Transaction not found: {tx_id}")
            
            tx_data = result[0]
            
            # Process webhook event
            if status in ["success", "completed"]:
                # Mark as completed
                update_query = """
                    UPDATE offramp_transactions 
                    SET status = 'completed', completed_at = NOW(), webhook_data = %s
                    WHERE id = %s
                """
                await self.db.execute_query(update_query, (str(payload), tx_id))
                
                # Record revenue
                await self._record_revenue(
                    user_id=tx_data["user_id"],
                    transaction_id=tx_id,
                    amount=Decimal(str(tx_data["seamount_fee"])),
                    source="offramp_fee"
                )
                
                logger.info(f"Off-ramp completed: {tx_id}")
                
            elif status in ["failed", "cancelled"]:
                # Refund user balance
                await self._refund_balance(
                    user_id=tx_data["user_id"],
                    asset=tx_data["crypto_asset"],
                    amount=Decimal(str(tx_data["crypto_amount"])),
                    transaction_id=tx_id
                )
                
                update_query = """
                    UPDATE offramp_transactions 
                    SET status = 'failed', failed_at = NOW(), webhook_data = %s
                    WHERE id = %s
                """
                await self.db.execute_query(update_query, (str(payload), tx_id))
                
                logger.warning(f"Off-ramp failed, balance refunded: {tx_id}")
            
            return {"success": True, "transaction_id": tx_id, "status": status}
            
        except Exception as e:
            logger.error(f"Webhook handling failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _refund_balance(
        self, 
        user_id: str, 
        asset: str, 
        amount: Decimal,
        transaction_id: str
    ):
        """Refund balance on failed withdrawal"""
        
        query = f"SELECT {asset.lower()}_balance FROM wallet_balances WHERE user_id = %s"
        result = await self.db.execute_query(query, (user_id,))
        
        current_balance = Decimal(str(result[0][f"{asset.lower()}_balance"]))
        new_balance = current_balance + amount
        
        update_query = f"""
            UPDATE wallet_balances 
            SET {asset.lower()}_balance = %s, updated_at = NOW()
            WHERE user_id = %s
        """
        await self.db.execute_query(update_query, (float(new_balance), user_id))
        
        logger.info(f"Refunded {amount} {asset} to user {user_id}")
    
    async def _record_revenue(
        self, 
        user_id: str, 
        transaction_id: str, 
        amount: Decimal, 
        source: str
    ):
        """Record revenue"""
        
        revenue_data = {
            "user_id": user_id,
            "transaction_id": transaction_id,
            "amount": float(amount),
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.db.log_event("revenue", revenue_data)
    
    async def get_withdrawal_limits(self, country: str) -> Dict[str, Any]:
        """Get withdrawal limits for a country"""
        
        if country not in self.channels:
            raise ValueError(f"Off-ramp not supported for: {country}")
        
        channels = self.channels[country]
        limits = {}
        
        for method, config in channels.items():
            limits[method] = {
                "currency": config["currencies"][0],
                "min": config["limits"]["min"],
                "max": config["limits"]["max"],
                "settlement_time": config["settlement_time"]
            }
        
        return limits