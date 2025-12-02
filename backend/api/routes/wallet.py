# File: backend/api/routes/wallet.py
"""
🎯 ULTIMATE Multi-Chain Wallet API Routes
Merged for Maximum Efficiency & Supremacy
Unified endpoints for Algorand + 4 WDK chains
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from decimal import Decimal
import logging
import re
import secrets
import hashlib
from eth_account.messages import encode_defunct
from web3.auto import w3 as web3_instance
from datetime import datetime, timedelta  # ✅ ADD THIS

# ========== REQUEST/RESPONSE MODELS ==========

class ValidateAddressRequest(BaseModel):
    address: str
    chain: str

class WalletCreateRequest(BaseModel):
    chains: Optional[List[str]] = None  # None = default essential chains
    create_all: bool = False  # True = create on all 5 chains

class SendPaymentRequest(BaseModel):
    recipient: str
    asset: str
    amount: Decimal
    memo: Optional[str] = None

class SingleChainCreateRequest(BaseModel):
    chain: str

# ✅ ADD LOGGER
logger = logging.getLogger(__name__)

from backend.dependencies import get_current_user, get_multi_chain_wallet_service
from backend.services.multi_chain_wallet_service import MultiChainWalletService

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
    🚀 CREATE MULTI-CHAIN WALLET (Ultimate Version)
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
            chains = ["algorand", "tron", "bitcoin", "ethereum", "polygon"]
        
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
        
        logger.info(f"✅ Multi-chain wallet created for user {user_id} on {result['total_chains']} chains")
        
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
    🚀 LEGACY ENDPOINT: CREATE MULTI-CHAIN WALLET
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
            chains = ["algorand", "tron", "bitcoin", "ethereum", "polygon"]
        
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
        
        logger.info(f"✅ Legacy multi-chain wallet created for user {user_id}")
        
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
    🎯 CREATE SINGLE CHAIN WALLET
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
        
        logger.info(f"✅ {chain} wallet created for user {user_id}")
        
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
    📊 GET MULTI-CHAIN WALLET STATUS - FIXED FOR 5 CHAINS ONLY
    """
    try:
        user_id = current_user["id"]
        
        # Get wallet status from database
        from backend.services.database_service import DatabaseService
        db = DatabaseService()
        
        # ✅ ONLY CHECK FOR 5 SUPPORTED CHAINS
        SUPPORTED_CHAIN_IDS = ['algorand', 'bitcoin', 'ethereum', 'polygon', 'tron']
        
        # Get WDK chain wallets - ONLY from supported chains
        wdk_wallets = db.supabase.table("multi_chain_addresses") \
            .select("blockchain, address, created_at") \
            .eq("user_id", user_id) \
            .in_("blockchain", SUPPORTED_CHAIN_IDS) \
            .execute()  # ✅ FIXED: Removed line continuation character issue
        
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
    💰 GET UNIFIED BALANCES ACROSS ALL CHAINS
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
                f"⚠️ DEGRADED balances for user {user_id}: ${result['total_usd']} "
                f"(source: {result.get('source', 'fallback')})"
            )
        else:
            logger.info(f"✅ Balances fetched for user {user_id}: ${result['total_usd']} total")
        
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
    ⚡ SEND PAYMENT WITH AUTO-ROUTING
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
            logger.warning(f"Payment failed for user {user_id}: {result.get('message')}")
            raise HTTPException(status_code=400, detail=result.get("message", "Payment failed"))
        
        logger.info(f"✅ Payment successful for user {user_id}: {result['transaction_id']}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        # ============================================================================
        # 🚨 ENHANCED ERROR PARSING - Extract meaningful error messages
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
                "❌ NEW ACCOUNT REQUIRES 0.1 ALGO MINIMUM\n\n"
                "Algorand requires at least 0.1 ALGO to activate new accounts.\n"
                "Please send 0.1 ALGO or more for the first transaction."
            )
        elif 'receiver not opted-in' in error_message.lower() or 'asset not opted-in' in error_message.lower():
            # ASA opt-in error
            user_message = (
                "❌ RECIPIENT MUST OPT-IN TO ASSET\n\n"
                "The recipient must add this asset to their wallet before receiving.\n"
                "Ask them to opt-in to the asset first."
            )
        elif 'insufficient balance' in error_message.lower() or 'insufficient funds' in error_message.lower():
            # Insufficient balance
            user_message = (
                "❌ INSUFFICIENT BALANCE\n\n"
                "You don't have enough balance to complete this transaction.\n"
                "Please check your balance and try again."
            )
        elif 'invalid address' in error_message.lower() or 'malformed address' in error_message.lower():
            # Invalid address
            user_message = (
                "❌ INVALID RECIPIENT ADDRESS\n\n"
                "The recipient address format is incorrect.\n"
                "Please double-check the address."
            )
        elif 'transaction fee' in error_message.lower():
            # Fee-related error
            user_message = (
                "❌ TRANSACTION FEE ERROR\n\n"
                "Unable to calculate or pay transaction fees.\n"
                "Please try again in a moment."
            )
        elif 'timeout' in error_message.lower() or 'timed out' in error_message.lower():
            # Network timeout
            user_message = (
                "❌ NETWORK TIMEOUT\n\n"
                "The blockchain network is slow or unresponsive.\n"
                "Please wait a moment and try again."
            )
        
        logger.error(f"❌ Payment failed for user {current_user['id']}: {error_message}")
        
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
    🔍 VALIDATE WALLET ADDRESS FOR SPECIFIC CHAIN
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
    🌐 GET SUPPORTED BLOCKCHAINS
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
            "default_chains": ["algorand", "tron", "bitcoin", "ethereum", "polygon"]
        }
        
    except Exception as e:
        logger.error(f"Chains endpoint failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch chain information")

@router.post("/connect-external")
async def connect_external_wallet(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    🔌 CONNECT EXTERNAL WALLET TO USER ACCOUNT
    
    Payload:
    {
        "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "chain": "ethereum",
        "wallet_source": "metamask",
        "signature": "0x123...",  // Optional for verification
        "message": "Sign this message to connect your wallet..."
    }
    
    Returns:
    {
        "success": true,
        "wallet": {
            "address": "0x...",
            "chain": "ethereum",
            "wallet_source": "metamask",
            "status": "connected"
        }
    }
    """
    try:
        user_id = current_user["id"]
        wallet_address = request.get("address", "").strip()
        chain = request.get("chain", "ethereum").lower()
        wallet_source = request.get("wallet_source", "external").lower()
        signature = request.get("signature")  # Optional
        message = request.get("message")  # Optional
        
        # 1️⃣ VALIDATE INPUTS
        if not wallet_address:
            raise HTTPException(status_code=400, detail="Wallet address required")
        
        if chain not in SUPPORTED_CHAINS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported chain: {chain}. Supported: {list(SUPPORTED_CHAINS.keys())}"
            )
        
        # 2️⃣ VALIDATE ADDRESS FORMAT
        chain_config = SUPPORTED_CHAINS[chain]
        pattern = chain_config.get("address_pattern")
        
        if pattern and not re.match(pattern, wallet_address):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {chain_config['name']} address format"
            )
        
        # 3️⃣ OPTIONAL: VERIFY SIGNATURE (if provided)
        if signature and message:
            try:
                # Verify the signature matches the wallet address
                message_hash = encode_defunct(text=message)
                recovered_address = web3_instance.eth.account.recover_message(
                    message_hash, 
                    signature=signature
                )
                
                if recovered_address.lower() != wallet_address.lower():
                    raise HTTPException(
                        status_code=401,
                        detail="Signature verification failed. Wallet address mismatch."
                    )
                
                logger.info(f"✅ Signature verified for wallet {wallet_address}")
                
            except Exception as sig_err:
                logger.error(f"Signature verification failed: {sig_err}")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid signature"
                )
        
        # 4️⃣ CHECK IF WALLET ALREADY CONNECTED
        from backend.services.database_service import DatabaseService
        db = DatabaseService()
        
        # Check if THIS USER already has THIS WALLET connected
        existing_user_wallet = db.supabase.table("multi_chain_addresses") \
            .select("id, user_id, wallet_source, connected_at") \
            .eq("user_id", user_id) \
            .eq("blockchain", chain) \
            .eq("address", wallet_address) \
            .eq("is_external", True) \
            .execute()
        
        if existing_user_wallet.data:
            logger.info(f"Wallet {wallet_address} already connected to user {user_id}")
            return {
                "success": True,
                "message": "Wallet already connected",
                "wallet": {
                    "address": wallet_address,
                    "chain": chain,
                    "chain_name": chain_config["name"],
                    "wallet_source": existing_user_wallet.data[0]["wallet_source"],
                    "connected_at": existing_user_wallet.data[0]["connected_at"],
                    "status": "already_connected"
                }
            }
        
        # 🚨 SECURITY: Check if wallet is connected to ANOTHER user
        existing_other_user = db.supabase.table("multi_chain_addresses") \
            .select("user_id") \
            .eq("blockchain", chain) \
            .eq("address", wallet_address) \
            .eq("is_external", True) \
            .neq("user_id", user_id) \
            .execute()
        
        if existing_other_user.data:
            logger.warning(f"🚨 Wallet {wallet_address} already connected to another user")
            raise HTTPException(
                status_code=409,
                detail="This wallet is already connected to another account"
            )
        
        # 5️⃣ DETECT WALLET TYPE (if not provided)
        if wallet_source == "external":
            # Try to detect from metadata
            wallet_source = "metamask"  # Default fallback
        
        # 6️⃣ SAVE WALLET TO DATABASE
        connection_metadata = {
            "user_agent": request.get("user_agent"),
            "ip_address": request.get("ip_address"),
            "verified": bool(signature),
            "chain_id": chain_config.get("chain_id")
        }
        
        wallet_data = {
            "user_id": user_id,
            "blockchain": chain,
            "address": wallet_address,
            "wallet_source": wallet_source,
            "is_external": True,
            "connected_at": datetime.utcnow().isoformat(),
            "last_used_at": datetime.utcnow().isoformat(),
            "connection_metadata": connection_metadata,
            "created_at": datetime.utcnow().isoformat()
        }
        
        insert_result = db.supabase.table("multi_chain_addresses").insert(wallet_data).execute()
        
        if not insert_result.data:
            raise HTTPException(status_code=500, detail="Failed to save wallet")
        
        logger.info(f"✅ External {chain} wallet connected for user {user_id}: {wallet_address[:8]}...")
        
        # 7️⃣ RETURN SUCCESS
        return {
            "success": True,
            "message": f"{chain_config['name']} wallet connected successfully!",
            "wallet": {
                "address": wallet_address,
                "chain": chain,
                "chain_name": chain_config["name"],
                "native_asset": chain_config["native_asset"],
                "wallet_source": wallet_source,
                "connected_at": wallet_data["connected_at"],
                "verified": bool(signature),
                "status": "connected"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to connect external wallet: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to connect wallet: {str(e)}")


@router.post("/generate-nonce")
async def generate_wallet_nonce(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    🔐 GENERATE NONCE FOR WALLET SIGNATURE VERIFICATION
    
    Payload:
    {
        "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    }
    
    Returns:
    {
        "nonce": "Sign this message to verify wallet ownership: abc123...",
        "expires_at": "2024-12-04T12:00:00Z"
    }
    """
    try:
        wallet_address = request.get("address", "").strip().lower()
        
        if not wallet_address:
            raise HTTPException(status_code=400, detail="Wallet address required")
        
        # Generate cryptographically secure nonce
        nonce_value = secrets.token_hex(16)
        expires_at = datetime.utcnow() + timedelta(minutes=5)  # 5-minute expiry
        
        # Store nonce in database
        from backend.services.database_service import DatabaseService
        db = DatabaseService()
        
        nonce_data = {
            "wallet_address": wallet_address,
            "nonce": nonce_value,
            "expires_at": expires_at.isoformat(),
            "used": False
        }
        
        db.supabase.table("wallet_nonces").insert(nonce_data).execute()
        
        # Create human-readable message
        message = f"Sign this message to verify wallet ownership:\n\nNonce: {nonce_value}\nExpires: {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        logger.info(f"✅ Generated nonce for wallet {wallet_address[:8]}...")
        
        return {
            "success": True,
            "nonce": nonce_value,
            "message": message,
            "expires_at": expires_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Nonce generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate nonce")


@router.get("/external-wallets")
async def get_external_wallets(
    current_user: dict = Depends(get_current_user)
):
    """
    📋 GET ALL EXTERNAL WALLETS CONNECTED TO USER ACCOUNT
    
    Returns:
    {
        "wallets": [
            {
                "address": "0x...",
                "chain": "ethereum",
                "wallet_source": "metamask",
                "connected_at": "2024-12-01T10:00:00Z"
            }
        ],
        "total": 2
    }
    """
    try:
        user_id = current_user["id"]
        
        from backend.services.database_service import DatabaseService
        db = DatabaseService()
        
        wallets_result = db.supabase.table("multi_chain_addresses") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("is_external", True) \
            .order("connected_at", desc=True) \
            .execute()
        
        wallets = []
        for wallet in wallets_result.data:
            chain_config = SUPPORTED_CHAINS.get(wallet["blockchain"], {})
            wallets.append({
                "address": wallet["address"],
                "chain": wallet["blockchain"],
                "chain_name": chain_config.get("name", wallet["blockchain"]),
                "wallet_source": wallet["wallet_source"],
                "connected_at": wallet["connected_at"],
                "last_used_at": wallet.get("last_used_at"),
                "verified": wallet.get("connection_metadata", {}).get("verified", False)
            })
        
        return {
            "success": True,
            "wallets": wallets,
            "total": len(wallets)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch external wallets: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch wallets")


@router.delete("/disconnect-wallet")
async def disconnect_external_wallet(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    🔌 DISCONNECT EXTERNAL WALLET FROM USER ACCOUNT
    
    Payload:
    {
        "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "chain": "ethereum"
    }
    """
    try:
        user_id = current_user["id"]
        wallet_address = request.get("address", "").strip()
        chain = request.get("chain", "ethereum").lower()
        
        if not wallet_address:
            raise HTTPException(status_code=400, detail="Wallet address required")
        
        from backend.services.database_service import DatabaseService
        db = DatabaseService()
        
        # Delete wallet connection
        delete_result = db.supabase.table("multi_chain_addresses") \
            .delete() \
            .eq("user_id", user_id) \
            .eq("address", wallet_address) \
            .eq("blockchain", chain) \
            .eq("is_external", True) \
            .execute()
        
        if not delete_result.data:
            raise HTTPException(status_code=404, detail="Wallet connection not found")
        
        logger.info(f"✅ Disconnected wallet {wallet_address[:8]}... from user {user_id}")
        
        return {
            "success": True,
            "message": "Wallet disconnected successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to disconnect wallet: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to disconnect wallet")
    
@router.get("/health")
async def wallet_health_check(
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """
    🩺 WALLET SERVICE HEALTH CHECK
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