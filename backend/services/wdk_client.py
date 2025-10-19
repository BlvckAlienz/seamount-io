# File: backend/services/wdk_client.py
"""
Python client for WDK Node.js microservice
Replaces the fictional wdk_service.py with real WDK integration
"""

import logging
import aiohttp
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from backend.config import settings
from backend.services.database_service import DatabaseService
from backend.services.audit_service import AuditService

logger = logging.getLogger(__name__)

class WDKClient:
    """
    Python client for WDK Node.js service
    Handles multi-chain wallet operations via REST API
    """
    
    def __init__(
        self,
        db_service: DatabaseService,
        audit_service: AuditService,
        wdk_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.db = db_service
        self.audit = audit_service
        
        # WDK service connection
        self.wdk_url = wdk_url or settings.WDK_SERVICE_URL
        self.api_key = api_key or settings.WDK_API_KEY
        
        if not self.wdk_url or not self.api_key:
            logger.warning("⚠️ WDK service not configured - multi-chain disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"✅ WDK client initialized: {self.wdk_url}")
    
    async def _call_wdk(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to WDK service"""
        
        if not self.enabled:
            raise Exception("WDK service not configured")
        
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        url = f"{self.wdk_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == "POST":
                    async with session.post(url, headers=headers, json=data) as resp:
                        resp.raise_for_status()
                        return await resp.json()
                else:
                    async with session.get(url, headers=headers) as resp:
                        resp.raise_for_status()
                        return await resp.json()
        
        except aiohttp.ClientError as e:
            logger.error(f"❌ WDK API call failed: {e}")
            raise Exception(f"WDK service error: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check WDK service health"""
        try:
            return await self._call_wdk("/health", method="GET")
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def generate_seed_phrase(self, user_id: str) -> Dict[str, Any]:
        """
        Generate new seed phrase for user
        Returns encrypted seed that should be stored securely
        """
        try:
            result = await self._call_wdk("/wallet/generate-seed")
            
            if result.get("success"):
                # Store encrypted seed in database
                await self.db.supabase.table("user_wallets").upsert({
                    "user_id": user_id,
                    "encrypted_seed": result["encrypted_seed"],
                    "wallet_type": "wdk_multi_chain",
                    "created_at": datetime.utcnow().isoformat()
                }, on_conflict="user_id").execute()
                
                logger.info(f"✅ Seed generated for user {user_id}")
                
                return {
                    "success": True,
                    "encrypted_seed": result["encrypted_seed"]
                }
            
            raise Exception("Seed generation failed")
            
        except Exception as e:
            logger.error(f"❌ Seed generation failed: {e}")
            raise
    
    async def create_multi_chain_wallet(
        self,
        user_id: str,
        chains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create wallets across multiple chains for user
        """
        try:
            # Get user's encrypted seed
            wallet_data = await self.db.supabase.table("user_wallets") \
                .select("encrypted_seed") \
                .eq("user_id", user_id) \
                .maybe_single() \
                .execute()
            
            if not wallet_data.data:
                # Generate new seed if doesn't exist
                seed_result = await self.generate_seed_phrase(user_id)
                encrypted_seed = seed_result["encrypted_seed"]
            else:
                encrypted_seed = wallet_data.data["encrypted_seed"]
            
            # Create wallets via WDK
            result = await self._call_wdk("/wallet/create", data={
                "encrypted_seed": encrypted_seed,
                "chains": chains or ["ethereum", "bitcoin", "polygon"]
            })
            
            if result.get("success"):
                # Store wallet addresses
                for chain, wallet_info in result["wallets"].items():
                    await self.db.supabase.table("multi_chain_addresses").insert({
                        "user_id": user_id,
                        "blockchain": chain,
                        "address": wallet_info["address"],
                        "index": wallet_info["index"],
                        "created_at": wallet_info["created_at"]
                    }).execute()
                
                # Audit log
                await self.audit.log_event(
                    "MULTI_CHAIN_WALLET_CREATED",
                    user_id=user_id,
                    details={
                        "chains": list(result["wallets"].keys()),
                        "addresses": {k: v["address"] for k, v in result["wallets"].items()}
                    }
                )
                
                logger.info(f"✅ Multi-chain wallet created for {user_id}")
                
                return {
                    "success": True,
                    "wallets": result["wallets"],
                    "message": "Your wallet is ready! 🎉"
                }
            
            raise Exception("Wallet creation failed")
            
        except Exception as e:
            logger.error(f"❌ Multi-chain wallet creation failed: {e}")
            raise
    
    async def get_balance(
        self,
        user_id: str,
        chain: str,
        index: int = 0
    ) -> Dict[str, Any]:
        """Get balance for specific chain"""
        try:
            # Get encrypted seed
            wallet_data = await self.db.supabase.table("user_wallets") \
                .select("encrypted_seed") \
                .eq("user_id", user_id) \
                .single() \
                .execute()
            
            if not wallet_data.data:
                raise Exception("Wallet not found")
            
            result = await self._call_wdk("/wallet/balance", data={
                "encrypted_seed": wallet_data.data["encrypted_seed"],
                "chain": chain,
                "index": index
            })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Balance query failed: {e}")
            raise
    
    async def get_unified_balance(self, user_id: str) -> Dict[str, Any]:
        """Get balances across all chains"""
        try:
            wallet_data = await self.db.supabase.table("user_wallets") \
                .select("encrypted_seed") \
                .eq("user_id", user_id) \
                .single() \
                .execute()
            
            if not wallet_data.data:
                return {
                    "success": False,
                    "balances": {},
                    "total_usd": 0
                }
            
            result = await self._call_wdk("/wallet/balance-unified", data={
                "encrypted_seed": wallet_data.data["encrypted_seed"],
                "chains": ["ethereum", "bitcoin", "polygon", "ton"]
            })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Unified balance failed: {e}")
            return {
                "success": False,
                "balances": {},
                "total_usd": 0
            }
    
    async def send_transaction(
        self,
        user_id: str,
        chain: str,
        to: str,
        amount: str,
        index: int = 0
    ) -> Dict[str, Any]:
        """Send transaction on specified chain"""
        try:
            wallet_data = await self.db.supabase.table("user_wallets") \
                .select("encrypted_seed") \
                .eq("user_id", user_id) \
                .single() \
                .execute()
            
            if not wallet_data.data:
                raise Exception("Wallet not found")
            
            result = await self._call_wdk("/wallet/send", data={
                "encrypted_seed": wallet_data.data["encrypted_seed"],
                "chain": chain,
                "to": to,
                "amount": amount,
                "index": index
            })
            
            if result.get("success"):
                # Store transaction record
                tx_id = str(uuid4())
                await self.db.supabase.table("multi_chain_transactions").insert({
                    "id": tx_id,
                    "user_id": user_id,
                    "blockchain": chain,
                    "tx_hash": result["tx_hash"],
                    "to_address": to,
                    "amount": amount,
                    "fee": result["fee"],
                    "status": "pending",
                    "created_at": result["timestamp"]
                }).execute()
                
                # Audit log
                await self.audit.log_event(
                    "MULTI_CHAIN_PAYMENT_SENT",
                    user_id=user_id,
                    resource_id=tx_id,
                    details={
                        "chain": chain,
                        "amount": amount,
                        "tx_hash": result["tx_hash"]
                    }
                )
                
                logger.info(f"✅ Transaction sent: {result['tx_hash']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Transaction failed: {e}")
            raise
    
    async def get_fee_estimate(self, chain: str) -> Dict[str, Any]:
        """Get fee estimates for chain"""
        try:
            return await self._call_wdk("/wallet/fee-estimate", data={
                "chain": chain
            })
        except Exception as e:
            logger.error(f"❌ Fee estimate failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def validate_address(
        self,
        chain: str,
        address: str
    ) -> bool:
        """Validate address format for chain"""
        try:
            result = await self._call_wdk("/wallet/validate-address", data={
                "chain": chain,
                "address": address
            })
            return result.get("is_valid", False)
        except Exception as e:
            logger.error(f"❌ Address validation failed: {e}")
            return False