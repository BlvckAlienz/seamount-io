# File: backend/api/routes/wallet_recovery.py
import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from cryptography.fernet import Fernet

from backend.dependencies import get_current_user, get_supabase_client
from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

@router.get("/seeds")
async def get_wallet_seeds(
    current_user: dict = Depends(get_current_user),
    supabase = Depends(get_supabase_client)
):
    """Retrieve and decrypt ALL wallet seeds for user"""
    
    user_id = current_user.get('id')
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        # Get Algorand wallet data
        algo_wallet = await asyncio.to_thread(
            lambda: supabase.table("user_wallets")
            .select("algorand_mnemonic, algorand_address")
            .eq("user_id", user_id)
            .execute()
        )
        
        # Get WDK multi-chain data
        wdk_wallets = await asyncio.to_thread(
            lambda: supabase.table("multi_chain_addresses")
            .select("blockchain, address, encrypted_seed")
            .eq("user_id", user_id)
            .execute()
        )
        
        if not algo_wallet.data and not wdk_wallets.data:
            raise HTTPException(status_code=404, detail="No wallets found for user")
        
        # Initialize Fernet for decryption
        fernet = Fernet(settings.ENCRYPTION_KEY.get_secret_value())
        
        seeds_data = {
            "user_id": user_id,
            "warning": "🔴 KEEP THESE SEEDS SECRET! DO NOT SHARE WITH ANYONE!",
            "backup_instruction": "Write these down and store in a secure location. These are required to recover your funds.",
            "algorand_seed": None,
            "wdk_seed": None,
            "wallet_addresses": {}
        }
        
        # Decrypt Algorand mnemonic
        if algo_wallet.data and algo_wallet.data[0].get('algorand_mnemonic'):
            try:
                encrypted_algo_mnemonic = algo_wallet.data[0]['algorand_mnemonic']
                seeds_data['algorand_seed'] = fernet.decrypt(encrypted_algo_mnemonic.encode()).decode()
                seeds_data['wallet_addresses']['algorand'] = algo_wallet.data[0]['algorand_address']
            except Exception as e:
                logger.error(f"Failed to decrypt Algorand seed: {e}")
                seeds_data['algorand_seed'] = "🔴 DECRYPTION FAILED - CONTACT SUPPORT"
        
        # Decrypt WDK seed (use first available)
        if wdk_wallets.data:
            for wallet in wdk_wallets.data:
                seeds_data['wallet_addresses'][wallet['blockchain']] = wallet['address']
                
                # Try to decrypt WDK seed
                if wallet.get('encrypted_seed') and not seeds_data['wdk_seed']:
                    try:
                        encrypted_wdk_seed = wallet['encrypted_seed']
                        seeds_data['wdk_seed'] = fernet.decrypt(encrypted_wdk_seed.encode()).decode()
                    except Exception as e:
                        logger.error(f"Failed to decrypt WDK seed for {wallet['blockchain']}: {e}")
            
            if not seeds_data['wdk_seed']:
                seeds_data['wdk_seed'] = "🔴 DECRYPTION FAILED - CONTACT SUPPORT"
        
        return seeds_data
        
    except Exception as e:
        logger.error(f"Seed recovery failed for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve wallet seeds")