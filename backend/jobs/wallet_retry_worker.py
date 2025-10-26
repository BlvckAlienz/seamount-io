# File: backend/jobs/wallet_retry_worker.py

import asyncio
import logging
from backend.dependencies import initialize_dependencies, get_wallet_creation_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("🔄 Starting wallet retry worker...")
    
    # Initialize dependencies
    initialize_dependencies()
    
    # Get service
    service = get_wallet_creation_service()
    
    # Process queue
    await service.process_retry_queue(batch_size=20)
    
    logger.info("✅ Wallet retry worker completed")

if __name__ == "__main__":
    asyncio.run(main())