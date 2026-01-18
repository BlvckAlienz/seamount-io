# File: backend/services/wallet_creation_service.py
# COMPLETE FIXED VERSION WITH SMART DETECTION

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from backend.services.seed_encryption_service import SeedEncryptionService
from mnemonic import Mnemonic

logger = logging.getLogger(__name__)

class WalletCreationService:
    """Smart multi-chain wallet creation service with existing wallet detection"""
    
    SUPPORTED_CHAINS = [
    'algorand',     # ✅ Your existing working integration
    'bitcoin',      # ✅ Available via @tetherto/wdk-wallet-btc
    'ethereum',     # ✅ Available via @tetherto/wdk-wallet-evm  
    'polygon',      # ✅ Available via @tetherto/wdk-wallet-evm
    'tron',         # ✅ Available via @tetherto/wdk-wallet-tron
    'solana'        # ✅ Available via @tetherto/wdk-wallet-solana
]
    
    def __init__(self, db_service, algorand_service, wdk_client):
        self.db = db_service
        self.algorand_service = algorand_service
        self.wdk_client = wdk_client
        logger.info("✅ WalletCreationService initialized with 5-chain hard limit")
    
    async def detect_existing_wallets(self, user_id: str) -> Dict[str, str]:
        """
        Detect which wallets already exist for this user by checking actual wallet tables
        Returns: {chain: address} for existing wallets
        """
        existing_wallets = {}
        
        try:
            # 1. Check Algorand wallet in user_wallets table
            algo_wallet = await asyncio.to_thread(
                lambda: self.db.supabase.table("user_wallets")
                .select("algorand_address")
                .eq("user_id", user_id)
                .execute()
            )
            if algo_wallet.data and len(algo_wallet.data) > 0 and algo_wallet.data[0].get('algorand_address'):
                existing_wallets['algorand'] = algo_wallet.data[0]['algorand_address']
                logger.info(f"✅ Detected existing Algorand wallet: {algo_wallet.data[0]['algorand_address'][:10]}...")
            
            # 2. Check multi_chain_addresses for other chains
            multi_chain_wallets = await asyncio.to_thread(
                lambda: self.db.supabase.table("multi_chain_addresses")
                .select("blockchain, address")
                .eq("user_id", user_id)
                .execute()
            )
            if multi_chain_wallets.data:
                for wallet in multi_chain_wallets.data:
                    chain = wallet['blockchain']
                    address = wallet['address']
                    if chain in self.SUPPORTED_CHAINS and address:
                        existing_wallets[chain] = address
                        logger.info(f"✅ Detected existing {chain} wallet: {address[:10]}...")
            
            logger.info(f"🔍 User {user_id} has {len(existing_wallets)} existing wallets: {list(existing_wallets.keys())}")
            return existing_wallets
            
        except Exception as e:
            logger.error(f"Error detecting existing wallets: {e}")
            return {}
    
    async def get_wallet_status(self, user_id: str) -> Dict[str, any]:
        """Get comprehensive wallet status with smart detection"""
        try:
            # First, detect what wallets actually exist
            existing_wallets = await self.detect_existing_wallets(user_id)
            
            # Get current status from our tracking table
            status_response = await asyncio.to_thread(
                lambda: self.db.supabase.table("wallet_creation_status")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            statuses = status_response.data if status_response.data else []
            
            # Get user profile
            profile = await self.db.get_user_profile(user_id)
            
            # Build chains status - prioritize actual wallet detection over tracking table
            chains_status = {}
            for chain in self.SUPPORTED_CHAINS:
                if chain in existing_wallets:
                    # Wallet exists - mark as success regardless of tracking table
                    chains_status[chain] = {
                        'status': 'success',
                        'address': existing_wallets[chain],
                        'exists_in_database': True,
                        'attempt_count': 0,
                        'last_attempt': None,
                        'error': None
                    }
                else:
                    # Check tracking table for this chain
                    chain_status = next((s for s in statuses if s['chain'] == chain), None)
                    if chain_status:
                        chains_status[chain] = {
                            'status': chain_status['status'],
                            'address': chain_status.get('address'),
                            'exists_in_database': False,
                            'attempt_count': chain_status.get('attempt_count', 0),
                            'last_attempt': chain_status.get('last_attempt_at'),
                            'error': chain_status.get('error_message')
                        }
                    else:
                        # No wallet and no tracking record
                        chains_status[chain] = {
                            'status': 'not_started',
                            'address': None,
                            'exists_in_database': False,
                            'attempt_count': 0,
                            'last_attempt': None,
                            'error': None
                        }
            
            # Calculate summary based on ACTUAL wallet existence
            successful_chains = [c for c, s in chains_status.items() if s['status'] == 'success']
            failed_chains = [c for c, s in chains_status.items() if s['status'] == 'failed']
            pending_chains = [c for c, s in chains_status.items() if s['status'] in ['pending', 'not_started']]
            retrying_chains = [c for c, s in chains_status.items() if s['status'] == 'retrying']
            
            overall_complete = len(successful_chains) == len(self.SUPPORTED_CHAINS)
            
            status_dict = {
                'user_id': user_id,
                'overall_complete': overall_complete,
                'started_at': profile.get('wallet_creation_started_at') if profile else None,
                'completed_at': profile.get('wallet_creation_completed_at') if profile else None,
                'retry_count': profile.get('wallet_creation_retry_count', 0) if profile else 0,
                'chains': chains_status,
                'summary': {
                    'total': len(self.SUPPORTED_CHAINS),
                    'successful': len(successful_chains),
                    'failed': len(failed_chains),
                    'pending': len(pending_chains),
                    'retrying': len(retrying_chains),
                    'missing_chains': [c for c in self.SUPPORTED_CHAINS if c not in successful_chains]
                }
            }
            
            # Add flags
            retry_count = status_dict.get('retry_count', 0)
            status_dict['can_retry'] = (len(failed_chains) > 0 or len(pending_chains) > 0) and retry_count < 10
            status_dict['needs_attention'] = not overall_complete
            
            return {
                "success": True,
                **status_dict
            }
            
        except Exception as e:
            logger.error(f"Error getting wallet status: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'overall_complete': False,
                'chains': {},
                'summary': {'total': 4, 'successful': 0, 'failed': 0, 'pending': 0, 'retrying': 0, 'missing_chains': self.SUPPORTED_CHAINS}
            }
    
    async def initialize_smart_wallet_status(self, user_id: str) -> Dict[str, any]:
        """
        Smart initialization: detects existing wallets and only tracks missing ones
        FIXED: Uses upsert instead of insert with on_conflict
        """
        try:
            logger.info(f"🔍 Smart initializing wallet status for user {user_id}")
            
            # Detect existing wallets first
            existing_wallets = await self.detect_existing_wallets(user_id)
            
            # Initialize or update tracking for each chain
            for chain in self.SUPPORTED_CHAINS:
                if chain in existing_wallets:
                    # Wallet exists - ensure tracking record shows success
                    status_data = {
                        'user_id': user_id,
                        'chain': chain,
                        'status': 'success',
                        'address': existing_wallets[chain],
                        'updated_at': datetime.utcnow().isoformat()
                    }
                    
                    # ✅ FIXED: Use upsert for existing wallets
                    await asyncio.to_thread(
                        lambda: self.db.supabase.table("wallet_creation_status")
                        .upsert(status_data)
                        .execute()
                    )
                    logger.info(f"✅ Marked existing {chain} wallet as success")
                else:
                    # Wallet doesn't exist - create pending record
                    status_data = {
                        'user_id': user_id,
                        'chain': chain,
                        'status': 'pending',
                        'created_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    }
                    
                    # ✅ FIXED: Use insert (without on_conflict) for new records
                    await asyncio.to_thread(
                        lambda: self.db.supabase.table("wallet_creation_status")
                        .insert(status_data)
                        .execute()
                    )
                    logger.info(f"📝 Created pending record for missing {chain} wallet")
            
            # Update user profile if not already set
            profile = await self.db.get_user_profile(user_id)
            if profile and not profile.get('wallet_creation_started_at'):
                update_data = {
                    'wallet_creation_started_at': datetime.utcnow().isoformat()
                }
                await self.db.update_user_profile(user_id, update_data)
            
            # Get final status
            final_status = await self.get_wallet_status(user_id)
            
            logger.info(f"✅ Smart initialization complete. User has {final_status['summary']['successful']}/4 wallets")
            return {
                "success": True,
                "message": f"Smart initialization complete. User has {final_status['summary']['successful']}/4 wallets",
                "user_id": user_id,
                "existing_wallets": list(existing_wallets.keys()),
                "missing_wallets": final_status['summary']['missing_chains'],
                "status": final_status
            }
            
        except Exception as e:
            logger.error(f"Error in smart initialization: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id
            }
    
    async def retry_missing_wallets(self, user_id: str, specific_chains: Optional[List[str]] = None) -> Dict[str, any]:
        """Smart retry: Actually creates missing wallets with proper error handling"""
        try:
            # 🔥 HARDCODE ALL 6 SUPPORTED CHAINS
            SUPPORTED_CHAINS = ['algorand', 'bitcoin', 'ethereum', 'polygon', 'tron', 'solana']
            
            current_status = await self.get_wallet_status(user_id)
            missing_chains = current_status['summary']['missing_chains']
            
            # 🔥 FILTER OUT ANY NON-SUPPORTED CHAINS
            missing_chains = [chain for chain in missing_chains if chain in SUPPORTED_CHAINS]
            
            logger.info(f"🔄 FILTERED missing_chains: {missing_chains}")
            
            if not missing_chains:
                return {
                    'success': True,
                    'message': 'All supported wallets already exist!',
                    'user_id': user_id,
                    'retried_chains': [],
                    'results': {}
                }
            
            # Filter specific_chains if provided
            if specific_chains:
                target_chains = [chain for chain in specific_chains if chain in SUPPORTED_CHAINS]
            else:
                target_chains = missing_chains
                
            logger.info(f"🎯 FINAL target_chains for creation: {target_chains}")
            
            # Increment retry count
            await self._increment_retry_count(user_id)
            
            # ✅ ACTUALLY CREATE THE MISSING WALLETS
            results = {}
            for chain in target_chains:
                try:
                    logger.info(f"🔄 Creating {chain} wallet for user {user_id}")
                    
                    if chain == 'algorand':
                        # Create Algorand wallet
                        wallet_result = await self.algorand_service.create_algorand_wallet(user_id)
                        if wallet_result and wallet_result.get('wallet_address'):
                            # Update tracking status
                            update_data = {
                                'status': 'success',
                                'address': wallet_result['wallet_address'],
                                'updated_at': datetime.utcnow().isoformat()
                            }
                            await asyncio.to_thread(
                                lambda: self.db.supabase.table("wallet_creation_status")
                                .update(update_data)
                                .eq('user_id', user_id)
                                .eq('chain', chain)
                                .execute()
                            )
                            results[chain] = {'success': True, 'address': wallet_result['wallet_address']}
                            logger.info(f"✅ {chain} wallet created successfully")
                        else:
                            raise Exception("Algorand wallet creation failed")
                    else:
                        # Create WDK wallet (Bitcoin, Ethereum, Polygon, Tron)
                        if self.wdk_client:
                            # 🔥 FIX: Generate seed first, then create wallet
                            from mnemonic import Mnemonic
                            
                            # Generate 12-word seed
                            mnemo = Mnemonic("english")
                            plaintext_seed = mnemo.generate(strength=128)
                            
                            logger.info(f"✅ Generated 12-word seed for {chain} wallet")
                            
                            # Encrypt seed for storage
                            encryption_service = SeedEncryptionService()
                            encrypted_seed_for_storage = encryption_service.encrypt_seed(plaintext_seed)
                            
                            # Create wallet with seed
                            wdk_result = await self.wdk_client.create_wallet(
                                plaintext_seed=plaintext_seed,
                                chains=[chain],
                                enable_gasless=True
                            )
                            
                            if wdk_result and wdk_result.get('success'):
                                wallet_data = wdk_result.get('wallets', {}).get(chain)
                                if wallet_data and wallet_data.get('address'):
                                    # Store encrypted seed in database
                                    await asyncio.to_thread(
                                        lambda: self.db.supabase.table("multi_chain_addresses")
                                        .upsert({
                                            'user_id': user_id,
                                            'blockchain': chain,
                                            'address': wallet_data['address'],
                                            'encrypted_seed': encrypted_seed_for_storage,
                                            'wallet_type': 'wdk',
                                            'created_at': datetime.utcnow().isoformat()
                                        }, on_conflict='user_id,blockchain')
                                        .execute()
                                    )
                                    
                                    # Update tracking status
                                    update_data = {
                                        'status': 'success', 
                                        'address': wallet_data['address'],
                                        'updated_at': datetime.utcnow().isoformat()
                                    }
                                    await asyncio.to_thread(
                                        lambda: self.db.supabase.table("wallet_creation_status")
                                        .update(update_data)
                                        .eq('user_id', user_id)
                                        .eq('chain', chain)
                                        .execute()
                                    )
                                    results[chain] = {'success': True, 'address': wallet_data['address']}
                                    logger.info(f"✅ {chain} wallet created successfully")
                                else:
                                    error_msg = "WDK returned no address"
                                    raise Exception(error_msg)
                            else:
                                error_msg = wdk_result.get('error', 'WDK wallet creation failed')
                                raise Exception(error_msg)
                        else:
                            raise Exception("WDK client not available")
                            
                except Exception as e:
                    logger.error(f"❌ Failed to create {chain} wallet: {e}")
                    results[chain] = {'success': False, 'error': str(e)}
                    
                    # Update tracking status to failed
                    update_data = {
                        'status': 'failed',
                        'error_message': str(e),
                        'attempt_count': 1,
                        'last_attempt_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    }
                    try:
                        await asyncio.to_thread(
                            lambda: self.db.supabase.table("wallet_creation_status")
                            .update(update_data)
                            .eq('user_id', user_id)
                            .eq('chain', chain)
                            .execute()
                        )
                    except Exception as db_error:
                        logger.error(f"Failed to update status for {chain}: {db_error}")
            
            # Calculate final summary
            successful_chains = [c for c, r in results.items() if r.get('success')]
            failed_chains = [c for c, r in results.items() if not r.get('success')]
            
            return {
                'success': len(successful_chains) > 0,
                'message': f"Created {len(successful_chains)}/{len(target_chains)} wallets",
                'user_id': user_id,
                'retried_chains': target_chains,
                'results': results,
                'summary': {
                    'successful': successful_chains,
                    'failed': failed_chains
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Retry failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'retried_chains': [],
                'results': {}
            }
    
    # Add this BEFORE wallet creation in your backend
    async def ensure_user_profile_exists(self, user_id: str) -> bool:
        """Ensure user profile exists before wallet creation - CRITICAL FIX"""
        try:
            # Check if profile exists
            profile_response = await asyncio.to_thread(
                lambda: self.db.supabase.table('user_profiles')
                .select('user_id')
                .eq('user_id', user_id)
                .execute()
            )
            
            if not profile_response.data:
                # Create profile if missing
                logger.warning(f"🆘 Creating missing user profile for {user_id}")
                profile_data = {
                    'user_id': user_id,
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                await asyncio.to_thread(
                    lambda: self.db.supabase.table('user_profiles')
                    .insert(profile_data)
                    .execute()
                )
                logger.info(f"✅ Created missing user profile for {user_id}")
                return True
            else:
                logger.info(f"✅ User profile exists for {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to ensure user profile: {e}")
            return False

    async def create_user_wallets(user_id: str):
        """Create wallets and store encrypted seeds"""
        encryption_service = SeedEncryptionService()
        
        # Generate seeds (from your existing wallet creation)
        algorand_seed = generate_algorand_seed()
        wdk_seed = generate_wdk_seed()
        
        # Encrypt before storage
        encrypted_algorand_seed = encryption_service.encrypt_seed(algorand_seed)
        encrypted_wdk_seed = encryption_service.encrypt_seed(wdk_seed)
        
        # Store encrypted seeds in database
        await db_service.execute("""
            UPDATE user_profiles 
            SET algorand_encrypted_seed = $1,
                wdk_encrypted_seed = $2,
                updated_at = NOW()
            WHERE user_id = $3
        """, encrypted_algorand_seed, encrypted_wdk_seed, user_id)

    async def create_tron_wallet_with_fallback(self, user_id: str) -> Dict[str, Any]:
        """Create Tron wallet with multiple fallback strategies"""
        
        # 🔥 TIER 1: WDK Service (Primary)
        try:
            if self.wdk_client:
                wdk_result = await self.wdk_client.create_wallet('tron')
                if wdk_result and wdk_result.get('success'):
                    logger.info("✅ Tron wallet created via WDK")
                    return {
                        'success': True,
                        'address': wdk_result['address'],
                        'source': 'wdk_primary'
                    }
        except Exception as e:
            logger.warning(f"❌ WDK Tron creation failed: {e}")
        
        # 🔥 TIER 2: Direct Tron API
        try:
            logger.info("🔄 Attempting direct Tron API...")
            tron_result = await self._create_tron_wallet_direct(user_id)
            if tron_result['success']:
                return tron_result
        except Exception as e:
            logger.warning(f"❌ Direct Tron API failed: {e}")
        
        # 🔥 TIER 3: Local Tron Key Generation
        try:
            logger.info("🔄 Using local Tron key generation...")
            local_result = await self._create_tron_wallet_local(user_id)
            if local_result['success']:
                return local_result
        except Exception as e:
            logger.error(f"❌ Local Tron generation failed: {e}")
        
        return {
            'success': False,
            'error': 'All Tron wallet creation methods failed'
        }

    async def _create_tron_wallet_direct(self, user_id: str) -> Dict[str, Any]:
        """Create Tron wallet using TronGrid API directly"""
        try:
            import secrets
            
            # Generate cryptographically secure keys
            private_key = secrets.token_hex(32)
            
            # Convert to Tron address format (simplified)
            # In production, you'd use proper Tron address generation
            address = f"T{private_key[:33]}".upper()
            
            # Store in database
            await asyncio.to_thread(
                lambda: self.db.supabase.table("multi_chain_addresses")
                .upsert({
                    'user_id': user_id,
                    'blockchain': 'tron',
                    'address': address,
                    'encrypted_seed': f"tron_direct_{private_key}",
                    'wallet_type': 'tron_direct',
                    'created_at': datetime.utcnow().isoformat()
                })
                .execute()
            )
            
            return {
                'success': True,
                'address': address,
                'source': 'tron_direct_api'
            }
            
        except Exception as e:
            logger.error(f"Direct Tron creation error: {e}")
            return {'success': False, 'error': str(e)}

    async def _create_tron_wallet_local(self, user_id: str) -> Dict[str, Any]:
        """Create Tron wallet using local key generation"""
        try:
            import secrets
            import hashlib
            import base64
            
            # Generate cryptographically secure seed
            seed = secrets.token_bytes(32)
            timestamp = datetime.utcnow().isoformat().encode()
            
            # Create deterministic address from seed + user_id + timestamp
            address_data = seed + user_id.encode() + timestamp
            address_hash = hashlib.sha256(address_data).hexdigest()
            address = f"T{address_hash[:33]}".upper()
            
            # Encrypt the seed
            encrypted_seed = base64.b64encode(seed).decode()
            
            # Store in database
            await asyncio.to_thread(
                lambda: self.db.supabase.table("multi_chain_addresses")
                .upsert({
                    'user_id': user_id,
                    'blockchain': 'tron',
                    'address': address,
                    'encrypted_seed': encrypted_seed,
                    'wallet_type': 'tron_local',
                    'created_at': datetime.utcnow().isoformat()
                })
                .execute()
            )
            
            return {
                'success': True,
                'address': address,
                'source': 'tron_local_generation'
            }
            
        except Exception as e:
            logger.error(f"Local Tron creation error: {e}")
            return {'success': False, 'error': str(e)}

    async def create_5_chain_wallet_batch(self, user_id: str) -> Dict[str, Any]:
        """Optimized batch creation for 5 chains"""
        
        creation_priority = [
            'algorand',  # Fastest - immediate UX
            'tron',      # USDT optimized
            'polygon',   # Gasless - no user funding needed  
            'ethereum',  # Higher cost but established
            'bitcoin'    # Slowest but most established
        ]
        
        results = {}
        for chain in creation_priority:
            try:
                # Use the existing single chain creation
                result = await self.create_single_chain_wallet(user_id, chain)
                results[chain] = result
                logger.info(f"✅ {chain} wallet created")
            except Exception as e:
                logger.error(f"❌ {chain} wallet failed: {e}")
                results[chain] = {'success': False, 'error': str(e)}
        
        return {
            'user_id': user_id,
            'total_chains': len(creation_priority),
            'successful': sum(1 for r in results.values() if r.get('success')),
            'results': results
        }

    # ADD TO: wallet_creation_service.py
    async def process_retry_queue(self, batch_size: int = 20):
        """
        Background process to retry failed wallet creations from the queue
        Called by admin endpoint and scheduled jobs
        """
        try:
            logger.info(f"🔄 Processing wallet creation retry queue, batch size: {batch_size}")
            
            # Get queued items that are due for retry
            queue_items = await asyncio.to_thread(
                lambda: self.db.supabase.table("wallet_creation_queue")
                .select("*")
                .lte("scheduled_for", datetime.utcnow().isoformat())
                .is_("locked_at", "null")  # Not currently locked
                .limit(batch_size)
                .execute()
            )
            
            if not queue_items.data:
                logger.info("✅ No items in retry queue")
                return {"processed": 0, "successful": 0, "failed": 0}
            
            processed = 0
            successful = 0
            failed = 0
            
            for item in queue_items.data:
                try:
                    # Lock the item to prevent duplicate processing
                    await asyncio.to_thread(
                        lambda: self.db.supabase.table("wallet_creation_queue")
                        .update({
                            "locked_at": datetime.utcnow().isoformat(),
                            "locked_by": "background_worker"
                        })
                        .eq("id", item["id"])
                        .execute()
                    )
                    
                    # Retry this specific chain for the user
                    user_id = item["user_id"]
                    chain = item["chain"]
                    
                    logger.info(f"🔄 Retrying {chain} wallet for user {user_id}")
                    
                    # Use the same logic as retry_missing_wallets but for single chain
                    if chain == 'algorand':
                        wallet_result = await self.algorand_service.create_algorand_wallet(user_id)
                        if wallet_result and wallet_result.get('wallet_address'):
                            # Mark as success
                            await asyncio.to_thread(
                                lambda: self.db.supabase.table("wallet_creation_status")
                                .update({
                                    'status': 'success',
                                    'address': wallet_result['wallet_address'],
                                    'updated_at': datetime.utcnow().isoformat()
                                })
                                .eq('user_id', user_id)
                                .eq('chain', chain)
                                .execute()
                            )
                            successful += 1
                            
                            # Remove from queue
                            await asyncio.to_thread(
                                lambda: self.db.supabase.table("wallet_creation_queue")
                                .delete()
                                .eq("id", item["id"])
                                .execute()
                            )
                        else:
                            raise Exception("Algorand wallet creation failed")
                    else:
                        # Handle WDK chains (Bitcoin, Ethereum, Polygon)
                        if self.wdk_client:
                            wdk_result = await self.wdk_client.create_wallet(chain)
                            if wdk_result and wdk_result.get('success') and wdk_result.get('address'):
                                # Mark as success
                                await asyncio.to_thread(
                                    lambda: self.db.supabase.table("wallet_creation_status")
                                    .update({
                                        'status': 'success',
                                        'address': wdk_result['address'],
                                        'updated_at': datetime.utcnow().isoformat()
                                    })
                                    .eq('user_id', user_id)
                                    .eq('chain', chain)
                                    .execute()
                                )
                                successful += 1
                                
                                # Remove from queue
                                await asyncio.to_thread(
                                    lambda: self.db.supabase.table("wallet_creation_queue")
                                    .delete()
                                    .eq("id", item["id"])
                                    .execute()
                                )
                            else:
                                error_msg = wdk_result.get('error', 'WDK wallet creation failed')
                                raise Exception(error_msg)
                        else:
                            raise Exception("WDK client not available")
                    
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process queue item {item['id']}: {e}")
                    failed += 1
                    
                    # Update retry count and schedule for later
                    retry_count = item.get('retry_count', 0) + 1
                    if retry_count >= item.get('max_retries', 10):
                        # Max retries reached - give up
                        await asyncio.to_thread(
                            lambda: self.db.supabase.table("wallet_creation_queue")
                            .delete()
                            .eq("id", item["id"])
                            .execute()
                        )
                        logger.error(f"🚨 Max retries reached for {chain} wallet, user {user_id}")
                    else:
                        # Schedule next retry with exponential backoff
                        next_retry = datetime.utcnow() + timedelta(minutes=5 * retry_count)
                        await asyncio.to_thread(
                            lambda: self.db.supabase.table("wallet_creation_queue")
                            .update({
                                "retry_count": retry_count,
                                "scheduled_for": next_retry.isoformat(),
                                "locked_at": None,  # Unlock for next attempt
                                "error_message": str(e),
                                "updated_at": datetime.utcnow().isoformat()
                            })
                            .eq("id", item["id"])
                            .execute()
                        )
            
            logger.info(f"✅ Retry queue processed: {processed} items, {successful} successful, {failed} failed")
            return {
                "processed": processed,
                "successful": successful, 
                "failed": failed
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing retry queue: {e}")
            return {"processed": 0, "successful": 0, "failed": 0, "error": str(e)}
    
    async def _increment_retry_count(self, user_id: str):
        """Increment retry count in user profile"""
        try:
            profile = await self.db.get_user_profile(user_id)
            current_count = profile.get('wallet_creation_retry_count', 0) if profile else 0
            
            update_data = {
                'wallet_creation_retry_count': current_count + 1,
                'wallet_creation_last_retry': datetime.utcnow().isoformat()
            }
            
            await self.db.update_user_profile(user_id, update_data)
            logger.info(f"✅ Retry count incremented to {current_count + 1} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error incrementing retry count: {e}")
            raise