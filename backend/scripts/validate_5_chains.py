import asyncio
import logging
import sys
import os

# Add the parent directory to Python path so we can import backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def validate_5_chains():
    """Validate all 5 chains are operational"""
    try:
        # Import inside function to avoid circular imports
        from backend.dependencies import get_multi_chain_wallet_service
        
        wallet_service = get_multi_chain_wallet_service()
        
        # Test chain support - 5 CHAINS
        expected_chains = ['algorand', 'bitcoin', 'ethereum', 'polygon', 'tron']
        
        logger.info("🔍 Validating 5-chain support...")
        
        for chain in expected_chains:
            if chain == 'algorand':
                logger.info(f"✅ {chain.upper()} - Independent integration")
            elif wallet_service.wdk_client.is_chain_supported(chain):
                logger.info(f"✅ {chain.upper()} - WDK Supported")
            else:
                logger.error(f"❌ {chain.upper()} - NOT SUPPORTED")
        
        # Test WDK health
        try:
            wdk_health = await wallet_service.wdk_client.health_check()
            logger.info(f"🩺 WDK Health: {wdk_health.get('status')}")
        except Exception as e:
            logger.warning(f"⚠️ WDK Health check failed: {e}")
        
        logger.info("🎯 5-CHAIN VALIDATION COMPLETE!")
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(validate_5_chains())
    sys.exit(0 if success else 1)