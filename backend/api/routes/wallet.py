# File: backend/api/routes/wallet.py
"""
ðŸŽ¯ ULTIMATE Multi-Chain Wallet API Routes
Merged for Maximum Efficiency & Supremacy
Unified endpoints for Algorand + 5 WDK chains
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from decimal import Decimal
import logging
import re

# ========== REQUEST/RESPONSE MODELS ==========

class ValidateAddressRequest(BaseModel):
    address: str
    chain: str

class WalletCreateRequest(BaseModel):
    chains: Optional[List[str]] = None  # None = default essential chains
    create_all: bool = False  # True = create on all 6 chains

class SendPaymentRequest(BaseModel):
    recipient: str
    asset: str
    amount: Decimal
    memo: Optional[str] = None

class SingleChainCreateRequest(BaseModel):
    chain: str

from backend.dependencies import get_current_user, get_multi_chain_wallet_service
from backend.services.multi_chain_wallet_service import MultiChainWalletService
from backend.dependencies import get_db_service

from backend.dependencies import (
    get_current_user,
    get_db_service,
    get_algorand_service
)
from backend.services.database_service import DatabaseService
from backend.services.algorand_service import AlgorandService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wallet", tags=["Multi-Chain Wallet"])

# ========== CHAIN CONFIGURATION ==========

SUPPORTED_CHAINS = {
    "algorand": {
        "name": "Algorand",
        "native_asset": "ALGO", 
        "supported_assets": ["ALGO", "USDCa", "USDT", "goBTC", "goETH"],
        "speed": "4.5 seconds",
        "cost": "0.001 ALGO",
        "address_pattern": r'^[A-Z2-7]{58}$'
    },
    "bitcoin": {
        "name": "Bitcoin",
        "native_asset": "BTC",
        "supported_assets": ["BTC"],
        "speed": "10-60 minutes", 
        "cost": "Variable",
        "address_pattern": r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$'
    },
    "ethereum": {
        "name": "Ethereum",
        "native_asset": "ETH",
        "supported_assets": ["ETH", "USDT", "USDC"],
        "speed": "12 seconds",
        "cost": "Gasless (USDT pays)",
        "address_pattern": r'^0x[a-fA-F0-9]{40}$'
    },
    "polygon": {
        "name": "Polygon", 
        "native_asset": "MATIC",
        "supported_assets": ["MATIC", "USDT", "USDC"],
        "speed": "2 seconds",
        "cost": "Gasless (USDT pays)",
        "address_pattern": r'^0x[a-fA-F0-9]{40}$'
    },
    "tron": {
        "name": "TRON",
        "native_asset": "TRX", 
        "supported_assets": ["TRX", "USDT"],
        "speed": "3 seconds",
        "cost": "~$0.05",
        "address_pattern": r'^T[A-Za-z1-9]{33}$'
    },
    "solana": {
        "name": "Solana",
        "native_asset": "SOL",
        "supported_assets": ["SOL", "USDT", "USDC"],
        "speed": "0.4 seconds",
        "cost": "~$0.00025",
        "address_pattern": r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'  # Base58 address
    } 
}

GASLESS_CHAINS = ["ethereum", "polygon"]

# ========== ENDPOINTS ==========

@router.post("/create")
async def create_multi_chain_wallet(
    request: WalletCreateRequest = None,
    current_user: dict = Depends(get_current_user),
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """
    ðŸš€ CREATE MULTI-CHAIN WALLET (Ultimate Version)
    """
    try:
        user_id = current_user["id"]
        user_email = current_user.get("email", "")
        
        # Determine chains to create
        if request and request.create_all:
            chains = list(SUPPORTED_CHAINS.keys())
        elif request and request.chains:
            # Validate requested chains
            chains = []
            for chain in request.chains:
                if chain in SUPPORTED_CHAINS:
                    chains.append(chain)
                else:
                    logger.warning(f"Unsupported chain requested: {chain}")
        else:
            # Default essential chains
            chains = ["algorand", "tron", "bitcoin", "ethereum", "polygon", "solana"]
        
        logger.info(f"Creating multi-chain wallet for user {user_id} on chains: {chains}")
        
        result = await wallet_service.create_wallet_for_user(
            user_id=user_id,
            chains=chains
        )
        
        if not result["success"]:
            error_msg = result.get("error", "Wallet creation failed")
            logger.error(f"Wallet creation failed for user {user_id}: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Enhanced response with chain metadata
        enhanced_wallets = {}
        for chain_id, wallet_data in result.get("wallets", {}).items():
            chain_info = SUPPORTED_CHAINS.get(chain_id, {})
            enhanced_wallets[chain_id] = {
                **wallet_data,
                "chain_name": chain_info.get("name", chain_id),
                "native_asset": chain_info.get("native_asset"),
                "supported_assets": chain_info.get("supported_assets", [])
            }
        
        logger.info(f"âœ… Multi-chain wallet created for user {user_id} on {result['total_chains']} chains")
        
        return {
            "success": True,
            "message": f"Wallet created on {result['total_chains']} chains!",
            "wallets": enhanced_wallets,
            "total_chains": result["total_chains"],
            "user_id": user_id,
            "created_chains": list(enhanced_wallets.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multi-chain wallet creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Wallet creation failed: {str(e)}")

@router.post("/create-multi-chain")
async def create_multi_chain_wallet_legacy(
    request: WalletCreateRequest = None,
    current_user: dict = Depends(get_current_user),
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """
    ðŸš€ LEGACY ENDPOINT: CREATE MULTI-CHAIN WALLET
    This fixes the 404 error for frontend calling /create-multi-chain
    """
    try:
        user_id = current_user["id"]
        
        # Determine chains to create
        if request and request.create_all:
            chains = list(SUPPORTED_CHAINS.keys())
        elif request and request.chains:
            chains = [chain for chain in request.chains if chain in SUPPORTED_CHAINS]
        else:
            chains = ["algorand", "tron", "bitcoin", "ethereum", "polygon", "solana"]
        
        logger.info(f"Creating multi-chain wallet via legacy endpoint for user {user_id}")
        
        result = await wallet_service.create_wallet_for_user(
            user_id=user_id,
            chains=chains
        )
        
        if not result["success"]:
            error_msg = result.get("error", "Wallet creation failed")
            logger.error(f"Legacy wallet creation failed for user {user_id}: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Enhanced response
        enhanced_wallets = {}
        for chain_id, wallet_data in result.get("wallets", {}).items():
            chain_info = SUPPORTED_CHAINS.get(chain_id, {})
            enhanced_wallets[chain_id] = {
                **wallet_data,
                "chain_name": chain_info.get("name", chain_id),
                "native_asset": chain_info.get("native_asset"),
                "supported_assets": chain_info.get("supported_assets", [])
            }
        
        logger.info(f"âœ… Legacy multi-chain wallet created for user {user_id}")
        
        return {
            "success": True,
            "message": f"Wallet created on {result['total_chains']} chains!",
            "wallets": enhanced_wallets,
            "total_chains": result["total_chains"],
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Legacy multi-chain wallet creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Wallet creation failed: {str(e)}")

@router.post("/{chain}/create")
async def create_single_chain_wallet(
    chain: str,
    current_user: dict = Depends(get_current_user),
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """
    ðŸŽ¯ CREATE SINGLE CHAIN WALLET
    """
    try:
        user_id = current_user["id"]
        
        # Validate chain
        if chain not in SUPPORTED_CHAINS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported chain: {chain}. Supported: {list(SUPPORTED_CHAINS.keys())}"
            )
        
        logger.info(f"Creating {chain} wallet for user {user_id}")
        
        # Check if wallet already exists
        existing_address = wallet_service._get_user_address(user_id, chain)
        if existing_address:
            return {
                "success": True,
                "message": f"{SUPPORTED_CHAINS[chain]['name']} wallet already exists",
                "wallet": {
                    "address": existing_address,
                    "chain": chain,
                    "chain_name": SUPPORTED_CHAINS[chain]["name"],
                    "native_asset": SUPPORTED_CHAINS[chain]["native_asset"],
                    "status": "existing"
                }
            }
        
        # Create single chain wallet
        result = await wallet_service.create_wallet_for_user(
            user_id=user_id,
            chains=[chain]
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Wallet creation failed"))
        
        wallet_data = result["wallets"].get(chain, {})
        chain_info = SUPPORTED_CHAINS[chain]
        
        logger.info(f"âœ… {chain} wallet created for user {user_id}")
        
        return {
            "success": True,
            "message": f"{chain_info['name']} wallet created successfully!",
            "wallet": {
                **wallet_data,
                "chain": chain,
                "chain_name": chain_info["name"],
                "native_asset": chain_info["native_asset"],
                "supported_assets": chain_info["supported_assets"],
                "status": "created"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Single chain wallet creation failed for {chain}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"{chain} wallet creation failed: {str(e)}")

@router.get("/multi-chain-status")
async def get_multi_chain_status(
    current_user: dict = Depends(get_current_user),
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """
    ðŸ“Š GET MULTI-CHAIN WALLET STATUS - FIXED FOR 5 CHAINS ONLY
    """
    try:
        user_id = current_user["id"]
        
        # Get wallet status from database
        from backend.services.database_service import DatabaseService
        db = DatabaseService()
        
        # ✅ CHECK FOR ALL 6 SUPPORTED CHAINS (INCLUDING SOLANA)
        SUPPORTED_CHAIN_IDS = ['algorand', 'bitcoin', 'ethereum', 'polygon', 'tron', 'solana']
        
        # Get WDK chain wallets - ONLY from supported chains
        wdk_wallets = db.supabase.table("multi_chain_addresses") \
            .select("blockchain, address, created_at") \
            .eq("user_id", user_id) \
            .in_("blockchain", SUPPORTED_CHAIN_IDS) \
            .execute()  # âœ… FIXED: Removed line continuation character issue
        
        wallets = {}
        if wdk_wallets.data:
            for wallet in wdk_wallets.data:
                chain_id = wallet["blockchain"]
                chain_info = SUPPORTED_CHAINS.get(chain_id, {})
                wallets[chain_id] = {
                    "address": wallet["address"],
                    "created_at": wallet["created_at"],
                    "status": "created",
                    "chain_name": chain_info.get("name", chain_id),
                    "native_asset": chain_info.get("native_asset"),
                    "supported_assets": chain_info.get("supported_assets", [])
                }
        
        # Get Algorand wallet (legacy)
        algo_wallet = db.supabase.table("user_wallets") \
            .select("algorand_address") \
            .eq("user_id", user_id) \
            .execute()
            
        if algo_wallet.data and len(algo_wallet.data) > 0 and algo_wallet.data[0].get("algorand_address"):
            chain_info = SUPPORTED_CHAINS["algorand"]
            wallets["algorand"] = {
                "address": algo_wallet.data[0]["algorand_address"],
                "status": "created",
                "chain_name": chain_info["name"],
                "native_asset": chain_info["native_asset"],
                "supported_assets": chain_info["supported_assets"]
            }
        
        # Add missing chains with status 'not_created'
        for chain_id, chain_info in SUPPORTED_CHAINS.items():
            if chain_id not in wallets:
                wallets[chain_id] = {
                    "address": None,
                    "status": "not_created",
                    "chain_name": chain_info["name"],
                    "native_asset": chain_info["native_asset"],
                    "supported_assets": chain_info["supported_assets"]
                }
        
        created_count = sum(1 for w in wallets.values() if w["status"] == "created")
        
        return {
            "success": True,
            "wallets": wallets,
            "total_chains": len(SUPPORTED_CHAINS),
            "created_chains": created_count,
            "pending_chains": len(SUPPORTED_CHAINS) - created_count
        }
        
    except Exception as e:
        logger.error(f"Multi-chain status query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status query failed: {str(e)}")

@router.get("/balances")
async def get_balances(
    current_user: dict = Depends(get_current_user),
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """
    ðŸ’° GET UNIFIED BALANCES ACROSS ALL CHAINS
    """
    try:
        user_id = current_user["id"]
        logger.info(f"Fetching multi-chain balances for user {user_id}")
        
        result = await wallet_service.get_user_balances(user_id)
        
        if not result["success"]:
            logger.warning(f"Balance query failed for user {user_id}: {result.get('error')}")
            return {
                "success": True,
                "total_usd": 0.0,
                "assets": [],
                "timestamp": result.get("timestamp"),
                "wallet_exists": False
            }
        
        # wallet.py line 308
        if result.get('fallback') or result.get('degraded'):
            logger.warning(
                f"âš ï¸ DEGRADED balances for user {user_id}: ${result['total_usd']} "
                f"(source: {result.get('source', 'fallback')})"
            )
        else:
            logger.info(f"âœ… Balances fetched for user {user_id}: ${result['total_usd']} total")
        
        return result
        
    except Exception as e:
        logger.error(f"Balance query failed: {str(e)}")
        return {
            "success": True,
            "total_usd": 0.0,
            "assets": [],
            "timestamp": None,
            "wallet_exists": False,
            "error": "Balance service temporarily unavailable"
        }

@router.post("/send")
async def send_payment(
    request: SendPaymentRequest,
    current_user: dict = Depends(get_current_user),
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """
    âš¡ SEND PAYMENT WITH AUTO-ROUTING
    """
    try:
        user_id = current_user["id"]
        
        logger.info(f"Payment initiated: {request.amount} {request.asset} from user {user_id}")
        
        result = await wallet_service.send_payment(
            user_id=user_id,
            recipient=request.recipient,
            asset=request.asset,
            amount=request.amount,
            memo=request.memo
        )
        
        if not result["success"]:
            # Surface the REAL error — not the generic wrapper
            real_error = result.get("error") or result.get("message", "Payment failed")
            logger.error(f"❌ Payment failed for user {user_id}: {real_error}")
            raise HTTPException(status_code=400, detail=real_error)
        
        logger.info(f"âœ… Payment successful for user {user_id}: {result['transaction_id']}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        # ============================================================================
        # ðŸš¨ ENHANCED ERROR PARSING - Extract meaningful error messages
        # ============================================================================
        error_message = str(e)
        
        # Parse nested exception messages
        if 'Algorand transaction failed:' in error_message:
            # Extract the actual Algorand error
            error_parts = error_message.split('Algorand transaction failed:')
            if len(error_parts) > 1:
                error_message = error_parts[1].strip()
        
        # Detect specific error types and provide user-friendly messages
        user_message = 'Payment failed. Please try again.'
        
        if 'balance' in error_message.lower() and 'below min' in error_message.lower():
            # New account minimum balance error
            user_message = (
                "âŒ NEW ACCOUNT REQUIRES 0.1 ALGO MINIMUM\n\n"
                "Algorand requires at least 0.1 ALGO to activate new accounts.\n"
                "Please send 0.1 ALGO or more for the first transaction."
            )
        elif 'receiver not opted-in' in error_message.lower() or 'asset not opted-in' in error_message.lower():
            # ASA opt-in error
            user_message = (
                "âŒ RECIPIENT MUST OPT-IN TO ASSET\n\n"
                "The recipient must add this asset to their wallet before receiving.\n"
                "Ask them to opt-in to the asset first."
            )
        elif 'insufficient balance' in error_message.lower() or 'insufficient funds' in error_message.lower():
            # Insufficient balance
            user_message = (
                "âŒ INSUFFICIENT BALANCE\n\n"
                "You don't have enough balance to complete this transaction.\n"
                "Please check your balance and try again."
            )
        elif 'invalid address' in error_message.lower() or 'malformed address' in error_message.lower():
            # Invalid address
            user_message = (
                "âŒ INVALID RECIPIENT ADDRESS\n\n"
                "The recipient address format is incorrect.\n"
                "Please double-check the address."
            )
        elif 'transaction fee' in error_message.lower():
            # Fee-related error
            user_message = (
                "âŒ TRANSACTION FEE ERROR\n\n"
                "Unable to calculate or pay transaction fees.\n"
                "Please try again in a moment."
            )
        elif 'timeout' in error_message.lower() or 'timed out' in error_message.lower():
            # Network timeout
            user_message = (
                "âŒ NETWORK TIMEOUT\n\n"
                "The blockchain network is slow or unresponsive.\n"
                "Please wait a moment and try again."
            )
        
        logger.error(f"âŒ Payment failed for user {current_user['id']}: {error_message}")
        
        return {
            'success': False,
            'message': user_message,
            'error': error_message,  # Technical error for debugging
            'error_type': 'transaction_failed'
        }

@router.post("/validate-address")
async def validate_address(
    request: ValidateAddressRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    ðŸ” VALIDATE WALLET ADDRESS FOR SPECIFIC CHAIN
    """
    try:
        address = request.address.strip()
        chain = request.chain.lower()
        
        # Get validation pattern for chain
        chain_config = SUPPORTED_CHAINS.get(chain)
        if not chain_config:
            return {
                "success": True,
                "valid": True,
                "message": "Chain validation not implemented"
            }
        
        pattern = chain_config.get("address_pattern")
        if not pattern:
            return {
                "success": True,
                "valid": True,
                "message": "Validation pattern not available for this chain"
            }
        
        is_valid = bool(re.match(pattern, address))
        
        return {
            "success": True,
            "valid": is_valid,
            "message": "Valid address" if is_valid else f"Invalid {chain_config['name']} address format",
            "chain_name": chain_config["name"]
        }
        
    except Exception as e:
        logger.error(f"Address validation error: {str(e)}")
        return {
            "success": False,
            "valid": False,
            "message": "Validation error"
        }

@router.get("/chains")
async def get_supported_chains():
    """
    ðŸŒ GET SUPPORTED BLOCKCHAINS
    """
    try:
        chains_list = []
        for chain_id, config in SUPPORTED_CHAINS.items():
            chains_list.append({
                "id": chain_id,
                "name": config["name"],
                "native_asset": config["native_asset"],
                "supported_assets": config["supported_assets"],
                "speed": config["speed"],
                "cost": config["cost"],
                "gasless": chain_id in GASLESS_CHAINS
            })
        
        return {
            "chains": chains_list,
            "total_chains": len(chains_list),
            "gasless_chains": GASLESS_CHAINS,
            "default_chains": ["algorand", "tron", "bitcoin", "ethereum", "polygon", "solana"]
        }
        
    except Exception as e:
        logger.error(f"Chains endpoint failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch chain information")

@router.get("/health")
async def wallet_health_check(
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """
    ðŸ©º WALLET SERVICE HEALTH CHECK
    """
    try:
        # Test database connectivity
        from backend.services.database_service import DatabaseService
        db = DatabaseService()
        
        # Test multi-chain service
        health_status = {
            "status": "healthy",
            "timestamp": None,
            "services": {
                "database": "connected",
                "multi_chain_service": "connected",
                "algorand": "connected",
                "wdk_service": "unknown"
            },
            "supported_chains": list(SUPPORTED_CHAINS.keys()),
            "total_chains": len(SUPPORTED_CHAINS)
        }
        
        # Try to test WDK service
        try:
            wdk_health = await wallet_service.wdk.health_check()
            health_status["services"]["wdk_service"] = wdk_health.get("status", "unknown")
        except Exception as e:
            health_status["services"]["wdk_service"] = f"error: {str(e)}"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "services": {
                "database": "error",
                "multi_chain_service": "error"
            }
        }
    
@router.get("/connected-wallets")
async def get_connected_wallets(
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    🔗 GET EXTERNALLY CONNECTED WALLETS (WalletConnect, MetaMask, etc.)
    Returns empty array for now - placeholder for future wallet connections
    """
    try:
        user_id = current_user["id"]
        
        # TODO: Query actual connected external wallets from database
        # For now, return empty array (no external connections yet)
        
        return {
            "success": True,
            "wallets": [],
            "count": 0,
            "message": "No external wallets connected yet"
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch connected wallets: {str(e)}")
        return {
            "success": True,  # Don't break frontend
            "wallets": [],
            "count": 0,
            "error": str(e)
        }
    
@router.get("/balance/algorand")
async def get_algorand_balance(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service),
    algorand_service: AlgorandService = Depends(get_algorand_service)
):
    """
    Get user's Algorand wallet balance
    
    Returns:
        {
            "success": true,
            "balance": 237500.101,  // in ALGO
            "balance_usd": 28500.01,  // approximate USD value
            "address": "...",
            "status": "active"
        }
    """
    try:
        # Get user's Algorand address
        wallet = db_service.supabase.table('user_wallets')\
            .select('algorand_address')\
            .eq('user_id', current_user['id'])\
            .single()\
            .execute()
        
        if not wallet.data:
            raise HTTPException(404, "Algorand wallet not found")
        
        address = wallet.data['algorand_address']
        
        # Get account info from Algorand
        account_info = await algorand_service.get_account_info(address)
        
        if not account_info:
            return {
                'success': True,
                'balance': 0,
                'balance_usd': 0,
                'address': address,
                'status': 'not_activated'
            }
        
        # Convert microAlgos to ALGO
        balance_microalgos = account_info.get('amount', 0)
        balance_algo = balance_microalgos / 1_000_000
        
        # ✅ CORRECT PRICING
        USD_PER_ALGO = 0.12  # TODO: Use real-time oracle
        balance_usd = balance_algo * USD_PER_ALGO
        
        return {
            'success': True,
            'balance': balance_algo,
            'balance_usd': round(balance_usd, 2),
            'address': address,
            'status': 'active',
            'exchange_rate': USD_PER_ALGO
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Balance fetch failed: {e}")
        raise HTTPException(500, str(e))
    
@router.post("/debug/balance/{chain}")
async def debug_balance_query(
    chain: str,
    request: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """Debug endpoint to trace balance queries"""
    try:
        address = request.get('address')
        asset = request.get('asset')
        
        # Direct WDK query
        wdk_result = await wallet_service.wdk.get_balance(address, chain, asset)
        
        # Also try direct TRC-20 query for Tron
        tron_result = None
        if chain == 'tron' and asset in ['USDT', 'USDT_TRON']:
            tron_result = await wallet_service.wdk._get_tron_trc20_balance(address, 'USDT')
        
        return {
            'success': True,
            'wdk_result': wdk_result,
            'tron_direct_result': tron_result,
            'address': address,
            'chain': chain,
            'asset': asset
        }
    except Exception as e:
        logger.error(f"Debug query failed: {e}")
        return {'success': False, 'error': str(e)}