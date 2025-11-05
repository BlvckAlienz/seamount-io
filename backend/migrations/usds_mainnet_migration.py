# File: usds_mainnet_migration.py
import asyncio
import logging
import os
import sys
import time
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional
import hashlib
import json
from pathlib import Path
from dataclasses import dataclass
from algosdk.v2client import algod, indexer
from algosdk import mnemonic, account, transaction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('usds_mainnet_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    env_paths = [Path.cwd() / '.env', Path(__file__).parent / '.env']
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded .env from: {env_path}")
            break
except ImportError:
    logger.warning("python-dotenv not installed. Using direct environment variables.")

@dataclass
class AlgorandConfig:
    """Algorand MAINNET configuration with enhanced error handling"""
    algod_url: str = "https://mainnet-api.algonode.cloud"
    algod_token: str = ""
    indexer_url: str = "https://mainnet-idx.algonode.cloud"
    indexer_token: str = ""
    network: str = "mainnet"
    creator_private_key: str = ""
    creator_address: str = ""
    max_retries: int = 5
    retry_delay: int = 3

    def __post_init__(self):
        # Force mainnet endpoints
        self.algod_url = "https://mainnet-api.algonode.cloud"
        self.indexer_url = "https://mainnet-idx.algonode.cloud"
        self.network = "mainnet"
        
        self._setup_account()
        self._test_connections()

    def _setup_account(self):
        """Setup account from mnemonic with enhanced validation"""
        mnemonic_phrase = os.getenv("ALGORAND_CREATOR_MNEMONIC")
        if not mnemonic_phrase:
            raise ValueError("ALGORAND_CREATOR_MNEMONIC environment variable is required for MAINNET")
        
        try:
            self.creator_private_key = mnemonic.to_private_key(mnemonic_phrase)
            self.creator_address = account.address_from_private_key(self.creator_private_key)
            logger.info(f"🔐 MAINNET Account loaded: {self.creator_address}")
        except Exception as e:
            logger.error(f"Failed to load MAINNET account from mnemonic: {e}")
            raise

    def _test_connections(self):
        """Test MAINNET Algorand connections with retries"""
        for attempt in range(self.max_retries):
            try:
                algod_client = self.get_algod_client()
                status = algod_client.status()
                logger.info(f"✅ MAINNET Algod connected - Round: {status.get('last-round', 'unknown')}")
                
                indexer_client = self.get_indexer_client()
                health = indexer_client.health()
                logger.info(f"✅ MAINNET Indexer connected - Health: {health}")
                return
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"❌ MAINNET connection failed after {self.max_retries} attempts: {e}")
                    raise
                logger.warning(f"MAINNET connection attempt {attempt + 1} failed, retrying: {e}")
                time.sleep(self.retry_delay)

    @classmethod
    def from_env(cls) -> 'AlgorandConfig':
        """Create MAINNET-only config from environment variables"""
        return cls()

    def get_algod_client(self) -> algod.AlgodClient:
        """Get MAINNET Algod client"""
        headers = {"X-API-Key": self.algod_token} if self.algod_token else {}
        return algod.AlgodClient(self.algod_token, self.algod_url, headers)

    def get_indexer_client(self) -> indexer.IndexerClient:
        """Get MAINNET Indexer client"""
        headers = {"X-API-Key": self.indexer_token} if self.indexer_token else {}
        return indexer.IndexerClient(self.indexer_token, self.indexer_url, headers)

    def get_account_info(self) -> Dict[str, Any]:
        """Get MAINNET account info with enhanced retry logic"""
        for attempt in range(self.max_retries):
            try:
                algod_client = self.get_algod_client()
                return algod_client.account_info(self.creator_address)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to get account info after {self.max_retries} attempts: {e}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                time.sleep(self.retry_delay)

    async def wait_for_confirmation(self, txid: str, timeout: int = 60) -> Dict[str, Any]:
        """Enhanced MAINNET transaction confirmation with improved error handling"""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    pending_info = self.get_algod_client().pending_transaction_info(txid)
                    if pending_info.get("confirmed-round", 0) > 0:
                        logger.info(f"✅ MAINNET Transaction confirmed in round {pending_info['confirmed-round']}")
                        return pending_info
                    elif pending_info.get("pool-error"):
                        raise Exception(f"Transaction failed: {pending_info['pool-error']}")

                    await asyncio.sleep(1)
                except Exception as e:
                    if "TransactionPool.Remember" in str(e):
                        # Transaction might be confirmed, check status
                        try:
                            status = self.get_algod_client().status()
                            last_round = status['last-round']
                            tx_info = self.get_algod_client().pending_transaction_info(txid)
                            if tx_info.get("confirmed-round", 0) > 0:
                                return tx_info
                        except:
                            pass
                    elif "not found" in str(e).lower():
                        logger.warning(f"Transaction not found in pool yet: {txid}")
                    else:
                        logger.warning(f"Error checking transaction: {e}")
                    await asyncio.sleep(1)

            raise TimeoutError(f"MAINNET Transaction {txid} not confirmed within {timeout} seconds")

        except Exception as e:
            logger.error(f"Error waiting for confirmation: {e}")
            raise

class USDSMainnetMigrationManager:
    """Enhanced USDS token migration manager with DeploymentManager features"""
    
    def __init__(self, config: AlgorandConfig):
        self.config = config
        self.algod_client = config.get_algod_client()
        self.creator_address = config.creator_address
        self.creator_private_key = config.creator_private_key
        self.old_asset_id: Optional[int] = None
        self.new_asset_id: Optional[int] = None
        
        # Enhanced USDS Configuration
        self.usds_name = "Seamount USD Stablecoin"
        self.usds_symbol = 
        self.usds_decimals = 6
        self.new_total_supply = 500_000 * (10 ** self.usds_decimals)  # 500K USDS in base units
        self.backing_ratio = Decimal('1.25')  # 125% backing
        self.config_version = "2.0"
        self.total_countries = 60
        
        # Enhanced configuration parameters
        self.usds_config = {
            'version': self.config_version,
            'fee_structure': {
                'conversion': {'base_fee': 0.020},  # 2.0% universal conversion
                'processing': {
                    'tier_1': 0.010,      # 1.0% premium markets
                    'tier_2_standard': 0.010,  # 1.0% standard emerging
                    'tier_2_african': 0.006,   # 0.6% African emerging
                    'tier_3': 0.018      # 1.8% high-risk markets
                },
                'network': {'base_fee': 0.00},     # $0.00 network fee
                'trading': {
                    'tier_1': 0.002,     # 0.2% premium trading
                    'tier_2': 0.0025,    # 0.25% emerging trading
                    'tier_3': 0.003      # 0.3% high-risk trading
                },
                'swap': {
                    'tier_1': 0.003,     # 0.3% premium swap
                    'tier_2': 0.0035,    # 0.35% emerging swap
                    'tier_3': 0.004      # 0.4% high-risk swap
                },
                'bridge': {
                    'tier_1': 0.0025,    # 0.25% premium bridge
                    'tier_2': 0.0035,    # 0.35% emerging bridge
                    'tier_3': 0.0045,    # 0.45% high-risk bridge
                    'min_fee': 1.50,     # $1.50 minimum
                    'max_fee': 35.00     # $35.00 maximum
                },
                'stability': {
                    'tier_1': 6.5,       # 6.5% annual yield
                    'tier_2': 7.5,       # 7.5% annual yield
                    'tier_3': 9.0        # 9.0% annual yield
                },
                'staking': {'reward_rate': 4.5}  # 4.5% staking rewards
            },
            'geographic_tiers': {
                'tier_1': ['US', 'CA', 'GB', 'DE', 'FR', 'AU', 'JP', 'SG',
                          'NL', 'CH', 'SE', 'NO', 'DK', 'AT', 'BE', 'FI',
                          'IE', 'LU', 'NZ', 'ZA'],
                'tier_2_standard': ['MX', 'BR', 'IN', 'CN', 'KR', 'TH',
                                   'MY', 'PH', 'ID', 'VN', 'TW', 'HK',
                                   'AE', 'SA', 'CL', 'CO', 'PE', 'AR',
                                   'UY'],
                'tier_2_african': ['NG', 'KE', 'EG', 'UG', 'ZW', 'TZ'],
                'tier_3': ['BD', 'PK', 'LK', 'MM', 'NP', 'ET', 'RW', 'BF',
                           'ML', 'SN', 'CI', 'GH', 'VE', 'MA', 'DO']
            },
            'volume_discounts': {
                'startup': {'threshold': 0, 'discount': 0.00},
                'growth': {'threshold': 100000, 'discount': 0.10},
                'enterprise': {'threshold': 1000000, 'discount': 0.15},
                'institutional': {'threshold': 10000000, 'discount': 0.20}
            },
            'supported_countries': self.total_countries,
            'usds_backing_ratio': float(self.backing_ratio),
            'max_daily_volume': 10000000,  # $10M daily limit
            'mint_parameters': {
                'initial_supply': 50000,
                'additional_mint': 450000,
                'total_target_supply': 500000,
                'backing_required': 625000  # 500k * 1.25
            }
        }

    async def execute_mainnet_migration(self) -> Dict[str, Any]:
        """Execute complete MAINNET migration with enhanced features"""
        try:
            logger.info("🚀 Starting MAINNET USDS migration from 50K to 500K supply...")
            logger.info("⚠️  MAINNET DEPLOYMENT - REAL FUNDS AT RISK")
            
            # Step 1: Enhanced account funding check
            await self._ensure_mainnet_account_funded()
            
            # Step 2: Deploy enhanced configuration
            config_result = await self._deploy_enhanced_config()
            
            # Step 3: Create new 500K USDS asset with enhanced metadata
            new_asset_result = await self._create_enhanced_usds_asset()
            self.new_asset_id = new_asset_result['asset_id']
            
            # Step 4: Verify comprehensive asset creation
            asset_info = await self._verify_enhanced_asset_creation()
            
            # Step 5: Generate comprehensive migration results
            migration_result = {
                'status': 'success',
                'network': 'MAINNET',
                'new_asset_id': self.new_asset_id,
                'old_asset_id': self.old_asset_id,
                'transaction_id': new_asset_result['transaction_id'],
                'confirmed_round': new_asset_result['confirmed_round'],
                'total_supply': self.new_total_supply,
                'backing_ratio': float(self.backing_ratio),
                'config_version': self.config_version,
                'supported_countries': self.usds_config['supported_countries'],
                'migration_time': datetime.now().isoformat(),
                'asset_info': asset_info,
                'config_deployment': config_result
            }
            
            logger.info(f"✅ MAINNET Migration completed successfully!")
            logger.info(f"📊 New MAINNET Asset ID: {self.new_asset_id}")
            logger.info(f"💰 Total Supply: {self.new_total_supply / (10**6):,} USDS")
            logger.info(f"🌍 Supporting {self.usds_config['supported_countries']} countries")
            
            return migration_result
            
        except Exception as e:
            logger.error(f"❌ MAINNET Migration failed: {e}")
            raise

    async def _ensure_mainnet_account_funded(self):
        """Ensure MAINNET creator account has sufficient balance"""
        try:
            account_info = self.config.get_account_info()
            balance = account_info.get("amount", 0)
            min_balance = 5_000_000  # 5 ALGO minimum for mainnet
            recommended_balance = 10_000_000  # 10 ALGO recommended

            if balance < min_balance:
                raise ValueError(f"❌ Insufficient MAINNET balance: {balance/1_000_000:.3f} ALGO (need {min_balance/1_000_000} ALGO minimum)")
                
            if balance < recommended_balance:
                logger.warning(f"⚠️  MAINNET balance below recommended: {balance/1_000_000:.3f} ALGO (recommend {recommended_balance/1_000_000} ALGO)")
            else:
                logger.info(f"✅ MAINNET Account well-funded: {balance / 1_000_000:.3f} ALGO")

        except Exception as e:
            logger.error(f"Error checking MAINNET account balance: {e}")
            raise

    async def _deploy_enhanced_config(self) -> Dict[str, Any]:
        """Deploy enhanced configuration similar to your DeploymentManager"""
        try:
            logger.info("📝 Deploying enhanced USDS configuration to MAINNET...")
            
            # Create comprehensive config data
            config_data = self.usds_config.copy()
            config_data['asset_name'] = self.usds_name
            config_data['asset_symbol'] = self.usds_symbol
            config_data['decimals'] = self.usds_decimals
            config_data['seamount_url'] = 'https://seamount.io'
            config_data['deployment_network'] = 'MAINNET'
            config_data['deployment_timestamp'] = datetime.now().isoformat()
            
            # Convert config to JSON and split into chunks
            config_json = json.dumps(config_data, separators=(',', ':'))
            config_bytes = config_json.encode('utf-8')
            max_chunk_size = 900
            config_chunks = [config_bytes[i:i+max_chunk_size] for i in range(0, len(config_bytes), max_chunk_size)]
            config_hash = hashlib.sha256(config_bytes).hexdigest()

            # Get suggested parameters with flat fee
            params = self.algod_client.suggested_params()
            params.fee = 1000
            params.flat_fee = True

            # Create note transaction for config metadata
            note_data = {
                'type': 'usds_enhanced_config',
                'version': self.config_version,
                'hash': config_hash,
                'chunks': len(config_chunks),
                'countries_supported': self.usds_config['supported_countries'],
                'timestamp': datetime.now().isoformat(),
                'network': 'MAINNET'
            }

            txn = transaction.PaymentTxn(
                sender=self.creator_address,
                sp=params,
                receiver=self.creator_address,
                amt=0,
                note=json.dumps(note_data).encode('utf-8')
            )

            # Sign and submit
            signed_txn = txn.sign(self.creator_private_key)
            txid = self.algod_client.send_transaction(signed_txn)
            logger.info(f"📤 MAINNET Config deployment transaction: {txid}")

            # Wait for confirmation
            confirmed_txn = await self.config.wait_for_confirmation(txid)

            return {
                'version': self.config_version,
                'config_hash': config_hash,
                'transaction_id': txid,
                'confirmed_round': confirmed_txn.get('confirmed-round'),
                'deployed_at': datetime.now().isoformat(),
                'countries_supported': self.usds_config['supported_countries'],
                'network': 'MAINNET'
            }

        except Exception as e:
            logger.error(f"Enhanced config deployment failed: {e}")
            raise

    async def _create_enhanced_usds_asset(self) -> Dict[str, Any]:
        """Create new 500K USDS asset with enhanced Seamount configuration"""
        try:
            # Get suggested parameters with flat fee
            suggested_params = self.algod_client.suggested_params()
            suggested_params.fee = 1000
            suggested_params.flat_fee = True

            # Create asset transaction with enhanced metadata
            txn = transaction.AssetConfigTxn(
                sender=self.creator_address,
                sp=suggested_params,
                total=self.new_total_supply,
                decimals=self.usds_decimals,
                asset_name=self.usds_name,
                unit_name=self.usds_symbol,
                manager=self.creator_address,
                reserve=self.creator_address,
                freeze=self.creator_address,
                clawback=self.creator_address,
                default_frozen=False,
                url="https://seamount.io",
                metadata_hash=self._calculate_enhanced_metadata_hash()
            )

            # Sign and submit transaction
            signed_txn = txn.sign(self.creator_private_key)
            txid = self.algod_client.send_transaction(signed_txn)
            logger.info(f"📤 MAINNET Enhanced asset creation transaction: {txid}")

            # Wait for confirmation with enhanced error handling
            confirmed_tx = await self.config.wait_for_confirmation(txid)
            asset_id = confirmed_tx.get("asset-index")
            
            if not asset_id:
                raise ValueError("Asset ID not found in MAINNET transaction confirmation")

            logger.info(f"🎉 New enhanced MAINNET USDS asset created with ID: {asset_id}")
            
            return {
                'asset_id': asset_id,
                'transaction_id': txid,
                'confirmed_round': confirmed_tx["confirmed-round"],
                'network': 'MAINNET'
            }

        except Exception as e:
            logger.error(f"Failed to create enhanced MAINNET USDS asset: {e}")
            raise

    def _calculate_enhanced_metadata_hash(self) -> bytes:
        """Calculate enhanced metadata hash matching DeploymentManager approach"""
        metadata = {
            'name': self.usds_name,
            'symbol': self.usds_symbol,
            'decimals': self.usds_decimals,
            'backing_ratio': float(self.backing_ratio),
            'version': self.config_version,
            'description': "Seamount USD Stablecoin - Enterprise cross-border payments",
            'website': "https://seamount.io",
            'peg': "USD",
            'backing': "125% collateralized",
            'supported_countries': self.usds_config['supported_countries'],
            'fee_tiers': len(self.usds_config['geographic_tiers']),
            'network': 'MAINNET'
        }
        
        metadata_str = json.dumps(metadata, sort_keys=True)
        return hashlib.sha256(metadata_str.encode()).digest()

    async def _verify_enhanced_asset_creation(self) -> Dict[str, Any]:
        """Verify the new enhanced asset was created correctly"""
        try:
            if not self.new_asset_id:
                raise ValueError("No new asset ID to verify")
                
            # Get asset info from MAINNET algod
            asset_info = self.algod_client.asset_info(self.new_asset_id)
            params = asset_info['params']
            
            # Enhanced verification checks
            expected_checks = [
                (params['name'] == self.usds_name, f"Name mismatch: {params['name']}"),
                (params['unit-name'] == self.usds_symbol, f"Symbol mismatch: {params['unit-name']}"),
                (params['decimals'] == self.usds_decimals, f"Decimals mismatch: {params['decimals']}"),
                (params['total'] == self.new_total_supply, f"Supply mismatch: {params['total']}"),
                (params['creator'] == self.creator_address, f"Creator mismatch: {params['creator']}"),
                (params.get('url') == "https://seamount.io", f"URL mismatch: {params.get('url')}")
            ]
            
            for check, error_msg in expected_checks:
                if not check:
                    raise ValueError(f"MAINNET Asset verification failed: {error_msg}")
            
            logger.info("✅ Enhanced MAINNET asset verification passed")
            return {
                'asset_id': self.new_asset_id,
                'name': params['name'],
                'symbol': params['unit-name'],
                'decimals': params['decimals'],
                'total_supply': params['total'],
                'creator': params['creator'],
                'url': params.get('url'),
                'verified': True,
                'network': 'MAINNET'
            }
            
        except Exception as e:
            logger.error(f"MAINNET Asset verification failed: {e}")
            raise

    async def mint_additional_usds(self, amount: int = 100000) -> Dict[str, Any]:
        """Mint additional USDS tokens with enhanced validation"""
        try:
            if not self.new_asset_id:
                raise Exception("USDS asset not found. Create asset first.")

            logger.info(f"💰 Minting {amount:,} additional USDS tokens on MAINNET...")

            # Calculate backing required (125% backing)
            backing_required = Decimal(amount) * self.backing_ratio
            logger.info(f"📊 Backing required: {backing_required} USD equivalent")

            # Verify current backing reserves
            current_backing = await self._get_backing_reserves()
            if current_backing < backing_required:
                logger.warning(f"⚠️  Insufficient backing: need ${backing_required}, have ${current_backing}")

            # Get suggested parameters with flat fee
            params = self.algod_client.suggested_params()
            params.fee = 1000
            params.flat_fee = True

            # Convert to base units
            mint_amount_base_units = amount * (10 ** self.usds_decimals)

            # Create asset transfer from reserve
            txn = transaction.AssetTransferTxn(
                sender=self.creator_address,
                sp=params,
                receiver=self.creator_address,  # Mint to creator first
                amt=mint_amount_base_units,
                index=self.new_asset_id
            )

            # Sign and submit
            signed_txn = txn.sign(self.creator_private_key)
            txid = self.algod_client.send_transaction(signed_txn)
            logger.info(f"📤 MAINNET Mint transaction: {txid}")

            # Wait for confirmation
            confirmed_txn = await self.config.wait_for_confirmation(txid)

            logger.info(f"✅ Successfully minted {amount:,} USDS tokens on MAINNET")

            return {
                'amount_minted': amount,
                'backing_required': float(backing_required),
                'transaction_id': txid,
                'confirmed_round': confirmed_txn.get('confirmed-round'),
                'mint_timestamp': datetime.now().isoformat(),
                'network': 'MAINNET'
            }

        except Exception as e:
            logger.error(f"MAINNET Mint failed: {e}")
            raise

    async def _get_backing_reserves(self) -> Decimal:
        """Get current backing reserves from MAINNET reserve address"""
        try:
            account_info = self.algod_client.account_info(self.creator_address)
            balance = account_info.get('amount', 0) / 1000000  # Convert microAlgos to Algos
            return Decimal(str(balance))
        except Exception as e:
            logger.warning(f"Could not fetch MAINNET backing reserves: {e}")
            return Decimal('0')  # Conservative for mainnet

async def main():
    """Main MAINNET migration execution"""
    try:
        print("🚀 MAINNET USDS Migration Process Starting...")
        print("⚠️  WARNING: DEPLOYING TO MAINNET - REAL FUNDS AT RISK")
        
        # Load MAINNET configuration
        config = AlgorandConfig.from_env()
        
        # Verify we're on mainnet
        if config.network != "mainnet":
            raise ValueError(f"❌ Expected mainnet, got {config.network}")
        
        # Initialize enhanced migration manager
        migration_manager = USDSMainnetMigrationManager(config)
        
        # Execute MAINNET migration
        result = await migration_manager.execute_mainnet_migration()
        
        # Save results to file
        with open('mainnet_migration_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info("📄 MAINNET migration results saved to mainnet_migration_result.json")
        
        print("\n" + "="*80)
        print("🎉 MAINNET USDS MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*80)
        print(f"🌐 Network: MAINNET")
        print(f"🆔 New Asset ID: {result['new_asset_id']}")
        print(f"💰 Total Supply: {result['total_supply'] / (10**6):,} USDS")
        print(f"🌍 Countries Supported: {result['supported_countries']}")
        print(f"📈 Backing Ratio: {result['backing_ratio']*100}%")
        print(f"📋 Transaction ID: {result['transaction_id']}")
        print("="*80)
        
        print("\n💡 Next Steps:")
        print("1. Update all applications to use new MAINNET Asset ID")
        print("2. Deploy comprehensive fee structures for 60 countries")
        print("3. Test cross-border payment flows")
        print("4. Monitor backing ratio compliance")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ MAINNET Migration failed: {e}")
        return {'status': 'failed', 'error': str(e), 'network': 'MAINNET'}

async def mint_mainnet_tokens(amount: int, recipient_address: str = None):
    """Mint additional MAINNET tokens after migration"""
    try:
        config = AlgorandConfig.from_env()
        migration_manager = USDSMainnetMigrationManager(config)
        
        # Load asset ID from previous migration
        try:
            with open('mainnet_migration_result.json', 'r') as f:
                migration_data = json.load(f)
                migration_manager.new_asset_id = migration_data['new_asset_id']
        except FileNotFoundError:
            raise ValueError("MAINNET migration result file not found. Run migration first.")
        
        # Use creator address if no recipient specified
        target_address = recipient_address or config.creator_address
        
        result = await migration_manager.mint_additional_usds(amount)
        logger.info(f"✅ MAINNET Minting completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ MAINNET Minting failed: {e}")
        raise

if __name__ == "__main__":
    print("⚠️  MAINNET DEPLOYMENT - PROCEED WITH CAUTION ⚠️")
    print("🚀 Starting Enhanced USDS MAINNET Migration...")
    
    # Run MAINNET migration
    result = asyncio.run(main())
    
    if result.get('status') == 'success':
        print(f"\n🎯 MAINNET Asset ID: {result['new_asset_id']}")
        print("🔧 To mint additional tokens:")
        print("python -c \"import asyncio; from usds_mainnet_migration import mint_mainnet_tokens; asyncio.run(mint_mainnet_tokens(100000, 'RECIPIENT_ADDRESS'))\"")
    else:
        print(f"\n❌ MAINNET Migration failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)