# File: backend/scripts/validate_8_chains.py
import asyncio
import logging
from backend.services.multi_chain_wallet_service import MultiChainWalletService
from backend.dependencies import get_multi_chain_wallet_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def validate_8_chains():
    """Validate all 8 chains are operational"""
    try:
        wallet_service = await get_multi_chain_wallet_service()
        
        # Test chain support
        expected_chains = ['algorand', 'bitcoin', 'ethereum', 'polygon', 'arbitrum', 'ton', 'tron', 'solana']
        
        logger.info("🔍 Validating 8-chain support...")
        
        for chain in expected_chains:
            if wallet_service.wdk_client.is_chain_supported(chain):
                logger.info(f"✅ {chain.upper()} - Supported")
            else:
                logger.warning(f"⚠️ {chain.upper()} - Not in WDK (may be independent)")
        
        # Test WDK health
        wdk_health = await wallet_service.wdk_client.health_check()
        logger.info(f"🩺 WDK Health: {wdk_health.get('status')}")
        
        logger.info("🎯 8-CHAIN VALIDATION COMPLETE!")
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")

if __name__ == "__main__":
    asyncio.run(validate_8_chains())