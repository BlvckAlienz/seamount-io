# File: backend/services/xrp_mpt_service.py
"""
XRP MPT Service — FUTURE PLUMBING (NOT in production flow yet)
Activate for:
  1. Seamount custom stablecoin when ready (~$10M TVL threshold)
  2. Institutional white-label token issuance (revenue stream)
"""

import json
import logging
from decimal import Decimal
from typing import Dict, Any

from xrpl.asyncio.clients import AsyncJsonRpcClient
from xrpl.asyncio.transaction import submit_and_wait
from xrpl.wallet import Wallet
from xrpl.models.transactions import MPTokenIssuanceCreate, MPTokenAuthorize, Payment, Clawback

logger = logging.getLogger(__name__)

MAINNET_RPC = "https://s1.ripple.com:51234"
TESTNET_RPC = "https://s.altnet.rippletest.net:51234"

# Flag set for institutional tokens: transfer + requireAuth + clawback + lock
INSTITUTIONAL_FLAGS = 0x0036


class XRPMPTService:
    """Generic MPT issuance for Seamount custom tokens + white-label."""

    def __init__(self, settings=None):
        from backend.config import get_settings
        self.settings = settings or get_settings()
        self.network = getattr(self.settings, 'XRP_NETWORK', 'mainnet')
        self.rpc_url = TESTNET_RPC if self.network == 'testnet' else MAINNET_RPC
        logger.info(f"✅ XRPMPTService [{self.network}] — STANDBY mode")

    async def create_token_issuance(
        self,
        issuer_seed: str,
        symbol: str,
        name: str,
        description: str,
        metadata_uri: str = "",
        asset_scale: int = 6,
        max_supply_units: int = 10_000_000_000_000_000,
        transfer_fee: int = 0,
        flags: int = INSTITUTIONAL_FLAGS,
    ) -> Dict[str, Any]:
        """
        Create MPT issuance. Usable for: custom stablecoins, RWA tokens, white-label.
        🚨 IMMUTABLE after creation. Test on testnet first.
        """
        metadata = {"n": name, "s": symbol, "d": description, "v": "1"}
        if metadata_uri:
            metadata["i"] = metadata_uri
        metadata_hex = json.dumps(metadata, separators=(',', ':')).encode().hex().upper()

        async with AsyncJsonRpcClient(self.rpc_url) as client:
            issuer_wallet = Wallet.from_seed(issuer_seed)
            tx = MPTokenIssuanceCreate(
                account=issuer_wallet.classic_address,
                asset_scale=asset_scale,
                maximum_amount=str(max_supply_units),
                transfer_fee=transfer_fee,
                flags=flags,
                mpt_token_metadata=metadata_hex,
            )
            response = await submit_and_wait(tx, client, issuer_wallet)
            tx_result = response.result.get('meta', {}).get('TransactionResult')
            if tx_result != 'tesSUCCESS':
                raise Exception(f"MPT creation FAILED: {tx_result}")

            mpt_id = None
            for node in response.result.get('meta', {}).get('AffectedNodes', []):
                created = node.get('CreatedNode', {})
                if created.get('LedgerEntryType') == 'MPTokenIssuance':
                    mpt_id = created.get('NewFields', {}).get('MPTokenIssuanceID')
                    break

            logger.info(f"✅ MPT created: {symbol} | ID: {mpt_id}")
            logger.info(f"🚨 PERSIST: XRP_{symbol}_MPT_ID={mpt_id}")
            return {'mpt_issuance_id': mpt_id, 'symbol': symbol, 'tx_hash': response.result['hash']}

    async def authorize_holder(self, issuer_seed: str, mpt_issuance_id: str, holder_address: str) -> Dict[str, Any]:
        async with AsyncJsonRpcClient(self.rpc_url) as client:
            issuer_wallet = Wallet.from_seed(issuer_seed)
            tx = MPTokenAuthorize(
                account=issuer_wallet.classic_address,
                holder=holder_address,
                mpt_issuance_id=mpt_issuance_id,
            )
            response = await submit_and_wait(tx, client, issuer_wallet)
            if response.result.get('meta', {}).get('TransactionResult') == 'tesSUCCESS':
                return {'success': True, 'holder': holder_address, 'tx_hash': response.result['hash']}
            raise Exception("Holder authorization failed")

    async def mint_tokens(self, issuer_seed: str, mpt_issuance_id: str, recipient: str, amount_units: int) -> Dict[str, Any]:
        async with AsyncJsonRpcClient(self.rpc_url) as client:
            issuer_wallet = Wallet.from_seed(issuer_seed)
            payment = Payment(
                account=issuer_wallet.classic_address,
                destination=recipient,
                amount={"mpt_issuance_id": mpt_issuance_id, "value": str(amount_units)},
            )
            response = await submit_and_wait(payment, client, issuer_wallet)
            if response.result.get('meta', {}).get('TransactionResult') == 'tesSUCCESS':
                return {'success': True, 'tx_hash': response.result['hash']}
            raise Exception("Mint failed")