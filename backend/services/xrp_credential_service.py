# File: backend/services/xrp_credential_service.py
"""
XRP Credential Service — on-chain KYC badges for Seamount.io
XLS-70 (Credentials) is LIVE. Issues verifiable on-chain compliance credentials.
"""

import asyncio
import logging
import time
from typing import Dict, Any

from xrpl.asyncio.clients import AsyncJsonRpcClient
from xrpl.asyncio.transaction import submit_and_wait
from xrpl.wallet import Wallet
from xrpl.models.transactions import CredentialCreate, CredentialDelete

logger = logging.getLogger(__name__)

MAINNET_RPC = "https://s1.ripple.com:51234"
TESTNET_RPC = "https://s.altnet.rippletest.net:51234"
RIPPLE_EPOCH = 946684800
MAX_RETRIES = 3
RETRY_DELAY = 2

CREDENTIAL_TYPES = {
    "KYC_BASIC":           "4B59435F4241534943",
    "KYC_ENHANCED":        "4B59435F454E48414E434544",
    "ACCREDITED_INVESTOR": "414343524544495445445F494E564553544F52",
}


class XRPCredentialService:
    def __init__(self, settings=None):
        from backend.config import get_settings
        self.settings = settings or get_settings()
        self.network = getattr(self.settings, 'XRP_NETWORK', 'mainnet')
        self.rpc_url = TESTNET_RPC if self.network == 'testnet' else MAINNET_RPC
        _seed = getattr(self.settings, 'XRP_ADMIN_WALLET_SEED', None)
        self._admin_seed = _seed.get_secret_value() if hasattr(_seed, 'get_secret_value') else _seed
        self.admin_address = getattr(self.settings, 'XRP_ADMIN_WALLET_ADDRESS', None)
        logger.info(f"✅ XRPCredentialService [{self.network}]")

    async def issue_credential(
        self, subject_address: str, credential_type: str = "KYC_BASIC", expiry_days: int = 365
    ) -> Dict[str, Any]:
        """Issue on-chain KYC credential post-verification."""
        type_hex = CREDENTIAL_TYPES.get(credential_type)
        if not type_hex:
            raise ValueError(f"Unknown credential type: {credential_type}")
        expiry_xrpl = int(time.time()) - RIPPLE_EPOCH + (expiry_days * 86400)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with AsyncJsonRpcClient(self.rpc_url) as client:
                    admin_wallet = Wallet.from_seed(self._admin_seed)
                    tx = CredentialCreate(
                        account=admin_wallet.classic_address,
                        subject=subject_address,
                        credential_type=type_hex,
                        expiration=expiry_xrpl,
                    )
                    response = await submit_and_wait(tx, client, admin_wallet)
                    tx_result = response.result.get('meta', {}).get('TransactionResult')
                    if tx_result == 'tesSUCCESS':
                        logger.info(f"✅ Credential issued: {credential_type} → {subject_address[:10]}...")
                        return {
                            'success': True, 'credential_type': credential_type,
                            'subject': subject_address, 'tx_hash': response.result['hash'],
                            'expires_days': expiry_days,
                        }
                    raise Exception(f"Credential failed: {tx_result}")
            except Exception as e:
                if attempt == MAX_RETRIES:
                    raise
                await asyncio.sleep(RETRY_DELAY * attempt)

    async def revoke_credential(self, subject_address: str, credential_type: str) -> Dict[str, Any]:
        """Revoke credential (sanction/compliance action)."""
        type_hex = CREDENTIAL_TYPES[credential_type]
        async with AsyncJsonRpcClient(self.rpc_url) as client:
            admin_wallet = Wallet.from_seed(self._admin_seed)
            tx = CredentialDelete(
                account=admin_wallet.classic_address,
                subject=subject_address,
                credential_type=type_hex,
            )
            response = await submit_and_wait(tx, client, admin_wallet)
            if response.result.get('meta', {}).get('TransactionResult') == 'tesSUCCESS':
                return {'success': True, 'tx_hash': response.result['hash']}
            raise Exception("Revocation failed")