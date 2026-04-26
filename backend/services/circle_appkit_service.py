# FILE: backend/services/circle_appkit_service.py
"""
Circle App Kit Service — Python orchestration layer.
Retrieves user wallet seeds, calls WDK Node.js /appkit/* endpoints,
and records fees + revenue automatically.
"""

import logging
import aiohttp
from decimal import Decimal
from datetime import datetime
from typing import Optional
from uuid import uuid4

from backend.config import get_settings
from backend.services.database_service import DatabaseService
from backend.services.seed_encryption_service import SeedEncryptionService

logger = logging.getLogger(__name__)

# ── Chain → Seamount blockchain key mapping ───────────────────────────────────
# App Kit chain names (PascalCase) → Seamount DB blockchain column (lowercase)
# EVM L2s (Base, Arbitrum, Optimism) use the Ethereum seed — same private key.
APPKIT_TO_BLOCKCHAIN: dict[str, str] = {
    "Ethereum"            : "ethereum",
    "Polygon"             : "polygon",
    "Base"                : "ethereum",   # EVM L2 — same private key as Ethereum
    "Arbitrum"            : "ethereum",   # EVM L2
    "Avalanche"           : "ethereum",   # Avalanche C-Chain = EVM
    "Optimism"            : "ethereum",   # OP Mainnet = EVM L2
    "Unichain"            : "ethereum",   # EVM L2
    "Linea"               : "ethereum",   # EVM L2
    "Sei"                 : "ethereum",   # EVM
    "HyperEVM"            : "ethereum",
    "Plume"               : "ethereum",
    "Solana"              : "solana",
    # Testnets
    "Ethereum_Sepolia"    : "ethereum",
    "Arc_Testnet"         : "ethereum",
    "Base_Sepolia"        : "ethereum",
    "Arbitrum_Sepolia"    : "ethereum",
    "Polygon_Amoy_Testnet": "polygon",
    "Solana_Devnet"       : "solana",
}

# Fee rates — mirror appkit-service.js (single source of truth is the env var;
# these are Python-side defaults for revenue tracking only)
BRIDGE_FEE_RATE = Decimal("0.005")   # 0.5%
SWAP_FEE_BPS    = 50                  # 50 bps = 0.5%
MIN_BRIDGE_FEE  = Decimal("0.25")     # $0.25 minimum


class CircleAppKitService:
    """
    Orchestrates Circle App Kit operations:
    1. Resolve & decrypt user wallet seeds for involved chains
    2. Call WDK Node.js /appkit/* endpoints
    3. Log fees to revenue_events + fees_owed tables
    """

    def __init__(self, db_service: DatabaseService):
        self.db         = db_service
        self.encryption = SeedEncryptionService()
        self.settings   = get_settings()

    # ── Internal helpers ─────────────────────────────────────────────────────

    @property
    def _wdk_url(self) -> str:
        base = getattr(self.settings, "WDK_SERVICE_URL", None) \
            or getattr(self.settings, "WDK_API_URL",      None) \
            or "https://seamount-wdk-ne5i.onrender.com"
        return base.rstrip("/")

    @property
    def _api_key(self) -> str:
        wdk_key = getattr(self.settings, "WDK_API_KEY", None)
        return wdk_key.get_secret_value() if wdk_key else ""

    async def _call_wdk(self, method: str, endpoint: str, payload: dict) -> dict:
        """Low-level call to WDK Node.js service with retry."""
        url     = f"{self._wdk_url}{endpoint}"
        headers = {"X-API-Key": self._api_key, "Content-Type": "application/json"}
        timeout = aiohttp.ClientTimeout(total=120)  # bridges can take 2+ minutes

        for attempt in range(1, 4):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    fn = getattr(session, method)
                    async with fn(url, json=payload, headers=headers) as resp:
                        data = await resp.json()
                        if resp.status == 401:
                            raise ValueError("WDK API key rejected")
                        if resp.status >= 500:
                            raise RuntimeError(f"WDK 5xx: {data.get('error', resp.status)}")
                        return data
            except (aiohttp.ClientConnectorError, RuntimeError) as err:
                if attempt == 3:
                    raise
                logger.warning(f"[CircleAppKit] attempt {attempt} failed: {err}")
        raise RuntimeError("All WDK retry attempts exhausted")

    async def _get_seed(self, user_id: str, appkit_chain: str) -> str:
        """
        Fetch & decrypt the user's wallet seed for the given App Kit chain name.
        Falls back to 'ethereum' seed for any unknown EVM chain.
        """
        blockchain = APPKIT_TO_BLOCKCHAIN.get(appkit_chain, "ethereum")

        result = self.db.supabase.table("multi_chain_addresses") \
            .select("encrypted_seed") \
            .eq("user_id", user_id) \
            .eq("blockchain", blockchain) \
            .execute()

        if not result.data:
            # Try generic ethereum fallback for any unmapped EVM chain
            if blockchain not in ("solana",):
                result = self.db.supabase.table("multi_chain_addresses") \
                    .select("encrypted_seed") \
                    .eq("user_id", user_id) \
                    .eq("blockchain", "ethereum") \
                    .execute()

        if not result.data:
            raise ValueError(
                f"No wallet found for user {user_id[:8]}... on chain '{appkit_chain}' "
                f"(blockchain='{blockchain}'). Create wallet first."
            )

        return self.encryption.decrypt_seed(result.data[0]["encrypted_seed"])

    def _compute_bridge_fee(self, amount: Decimal) -> Decimal:
        return max(amount * BRIDGE_FEE_RATE, MIN_BRIDGE_FEE)

    async def _log_bridge_fee(
        self,
        user_id:      str,
        transaction_id: str,
        amount:       Decimal,
        from_chain:   str,
        seamount_fee: Decimal,
        result:       dict,
    ) -> None:
        """Record bridge transaction and fee for revenue tracking."""
        try:
            from backend.config import CENTRAL_TREASURY_ADDRESSES
            blockchain = APPKIT_TO_BLOCKCHAIN.get(from_chain, "ethereum")
            treasury   = CENTRAL_TREASURY_ADDRESSES.get(blockchain, "")

            # 1. Bridge transaction record
            self.db.supabase.table("circle_bridge_transactions").insert({
                "id"            : transaction_id,
                "user_id"       : user_id,
                "from_chain"    : from_chain,
                "to_chain"      : result.get("to_chain", ""),
                "amount"        : float(amount),
                "token"         : result.get("token", "USDC"),
                "seamount_fee"  : float(seamount_fee),
                "state"         : result.get("state", "pending"),
                "steps"         : result.get("steps", []),
                "provider"      : result.get("provider", "circle_cctp"),
                "created_at"    : datetime.utcnow().isoformat(),
            }).execute()

            # 2. Fee owed record (for batch collection)
            self.db.supabase.table("fees_owed").insert({
                "user_id"          : user_id,
                "transaction_id"   : transaction_id,
                "chain"            : blockchain,
                "asset"            : "USDC",
                "fee_amount"       : float(seamount_fee),
                "treasury_address" : treasury,
                "status"           : "collected",  # USDC fee collected on-chain by App Kit
                "created_at"       : datetime.utcnow().isoformat(),
            }).execute()

            # 3. Revenue event (analytics)
            self.db.supabase.table("revenue_events").insert({
                "user_id"       : user_id,
                "revenue_type"  : "bridge_fee",
                "transaction_type": "circle_bridge",
                "amount"        : float(amount),
                "fee_rate"      : float(BRIDGE_FEE_RATE),
                "platform_fee"  : float(seamount_fee),
                "network_fee"   : 0.0,
                "blockchain"    : blockchain,
                "metadata"      : {"from_chain": from_chain, "to_chain": result.get("to_chain"), "provider": "circle_cctp"},
                "created_at"    : datetime.utcnow().isoformat(),
            }).execute()

            logger.info(f"✅ Bridge fee logged: ${seamount_fee:.4f} USDC | tx={transaction_id[:8]}")

        except Exception as e:
            # Non-fatal — don't block the user response
            logger.error(f"❌ Bridge fee logging failed (non-fatal): {e}")

    async def _log_swap_fee(
        self,
        user_id:      str,
        chain:        str,
        amount_in:    Decimal,
        result:       dict,
    ) -> None:
        """Record Circle App Kit swap transaction and fee."""
        try:
            fee_rate   = Decimal(str(SWAP_FEE_BPS)) / Decimal("10000")
            fee_amount = amount_in * fee_rate
            blockchain = APPKIT_TO_BLOCKCHAIN.get(chain, "ethereum")

            self.db.supabase.table("circle_swap_transactions").insert({
                "id"          : str(uuid4()),
                "user_id"     : user_id,
                "chain"       : chain,
                "token_in"    : result.get("token_in", ""),
                "token_out"   : result.get("token_out", ""),
                "amount_in"   : float(amount_in),
                "amount_out"  : float(result.get("amount_out") or 0),
                "seamount_fee": float(fee_amount),
                "tx_hash"     : result.get("tx_hash", ""),
                "explorer_url": result.get("explorer_url", ""),
                "state"       : "success",
                "created_at"  : datetime.utcnow().isoformat(),
            }).execute()

            self.db.supabase.table("revenue_events").insert({
                "user_id"      : user_id,
                "revenue_type" : "swap_fee",
                "transaction_type": "circle_swap",
                "amount"       : float(amount_in),
                "fee_rate"     : float(fee_rate),
                "platform_fee" : float(fee_amount),
                "network_fee"  : 0.0,
                "blockchain"   : blockchain,
                "metadata"     : {"chain": chain, "token_in": result.get("token_in"), "token_out": result.get("token_out")},
                "created_at"   : datetime.utcnow().isoformat(),
            }).execute()

            logger.info(f"✅ Swap fee logged: ${fee_amount:.4f} USDC | chain={chain}")

        except Exception as e:
            logger.error(f"❌ Swap fee logging failed (non-fatal): {e}")

    # ── Public API ────────────────────────────────────────────────────────────

    async def estimate_bridge(
        self,
        user_id:    str,
        from_chain: str,
        to_chain:   str,
        amount:     str,
    ) -> dict:
        """Get fee breakdown before user confirms bridge."""
        from_seed = await self._get_seed(user_id, from_chain)
        to_seed   = await self._get_seed(user_id, to_chain)

        result = await self._call_wdk("post", "/appkit/bridge/estimate", {
            "from_seed" : from_seed,
            "to_seed"   : to_seed,
            "from_chain": from_chain,
            "to_chain"  : to_chain,
            "amount"    : amount,
        })
        return result

    async def bridge_usdc(
        self,
        user_id:            str,
        from_chain:         str,
        to_chain:           str,
        amount:             str,
        recipient_address:  Optional[str] = None,
        transfer_speed:     str = "FAST",
        use_forwarder:      bool = False,
    ) -> dict:
        """Execute CCTP USDC bridge. Fee auto-collected on-chain by App Kit."""
        from_seed = await self._get_seed(user_id, from_chain)
        to_seed   = await self._get_seed(user_id, to_chain)

        payload = {
            "from_seed"        : from_seed,
            "to_seed"          : to_seed,
            "from_chain"       : from_chain,
            "to_chain"         : to_chain,
            "amount"           : amount,
            "transfer_speed"   : transfer_speed,
            "use_forwarder"    : use_forwarder,
        }
        if recipient_address:
            payload["recipient_address"] = recipient_address

        result = await self._call_wdk("post", "/appkit/bridge", payload)

        if result.get("success"):
            tx_id        = str(uuid4())
            seamount_fee = self._compute_bridge_fee(Decimal(str(amount)))
            result["from_chain"] = from_chain
            result["to_chain"]   = to_chain
            await self._log_bridge_fee(
                user_id=user_id,
                transaction_id=tx_id,
                amount=Decimal(str(amount)),
                from_chain=from_chain,
                seamount_fee=seamount_fee,
                result=result,
            )

        return result

    async def retry_bridge(
        self,
        user_id:       str,
        bridge_result: dict,
    ) -> dict:
        """Resume a partial bridge (mint failed after burn succeeded)."""
        from_chain = bridge_result.get("source", {}).get("chain") or bridge_result.get("from_chain", "Ethereum")
        to_chain   = bridge_result.get("destination", {}).get("chain") or bridge_result.get("to_chain", "Ethereum")
        from_seed  = await self._get_seed(user_id, from_chain)
        to_seed    = await self._get_seed(user_id, to_chain)

        return await self._call_wdk("post", "/appkit/bridge/retry", {
            "from_seed"    : from_seed,
            "to_seed"      : to_seed,
            "bridge_result": bridge_result,
        })

    async def estimate_swap(
        self,
        user_id:   str,
        chain:     str,
        token_in:  str,
        token_out: str,
        amount_in: str,
    ) -> dict:
        """Preview Circle App Kit swap output."""
        from_seed = await self._get_seed(user_id, chain)
        return await self._call_wdk("post", "/appkit/swap/estimate", {
            "from_seed": from_seed,
            "chain"    : chain,
            "token_in" : token_in,
            "token_out": token_out,
            "amount_in": amount_in,
        })

    async def swap_tokens(
        self,
        user_id:     str,
        chain:       str,
        token_in:    str,
        token_out:   str,
        amount_in:   str,
        slippage_bps: int = 300,
        stop_limit:  Optional[str] = None,
    ) -> dict:
        """Execute Circle App Kit same-chain swap. Fee auto-collected on-chain."""
        from_seed = await self._get_seed(user_id, chain)

        payload = {
            "from_seed"  : from_seed,
            "chain"      : chain,
            "token_in"   : token_in,
            "token_out"  : token_out,
            "amount_in"  : amount_in,
            "slippage_bps": slippage_bps,
        }
        if stop_limit:
            payload["stop_limit"] = stop_limit

        result = await self._call_wdk("post", "/appkit/swap", payload)

        if result.get("success"):
            await self._log_swap_fee(
                user_id=user_id,
                chain=chain,
                amount_in=Decimal(str(amount_in)),
                result=result,
            )

        return result

    async def get_supported_chains(self, operation_type: Optional[str] = None) -> dict:
        """Get App Kit supported chains. Cached in Node.js."""
        endpoint = "/appkit/supported-chains"
        if operation_type:
            endpoint += f"?type={operation_type}"
        return await self._call_wdk("get", endpoint, {})

    async def health_check(self) -> dict:
        return await self._call_wdk("get", "/appkit/health", {})