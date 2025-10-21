# File: backend/api/routes/wallet.py
"""
Multi-Chain Wallet API Routes
Unified endpoints for Algorand + 8 WDK chains
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal

from backend.dependencies import get_current_user, get_multi_chain_wallet_service
from backend.services.multi_chain_wallet_service import MultiChainWalletService

router = APIRouter(prefix="/wallet", tags=["Multi-Chain Wallet"])

# ========== REQUEST/RESPONSE MODELS ==========

class WalletCreateRequest(BaseModel):
    chains: Optional[List[str]] = None  # None = default essential chains
    create_all: bool = False  # True = create on all 9 chains

class SendPaymentRequest(BaseModel):
    recipient: str
    asset: str
    amount: Decimal
    memo: Optional[str] = None

# ========== ENDPOINTS ==========

@router.post("/create")
async def create_multi_chain_wallet(
    request: WalletCreateRequest,
    current_user: dict = Depends(get_current_user),
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """
    Create multi-chain wallet for user
    
    DEFAULT: Algorand + essential chains (Bitcoin, Lightning, Ethereum, Polygon, TRON)
    OPTIONAL: Specify custom chains or create_all=True for all 9 chains
    """
    
    result = await wallet_service.create_wallet_for_user(
        user_id=current_user["id"],
        chains=request.chains
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail="Wallet creation failed")
    
    return {
        "success": True,
        "message": f"Wallet created on {result['total_chains']} chains!",
        "wallets": result["wallets"],
        "total_chains": result["total_chains"]
    }

@router.get("/balances")
async def get_balances(
    current_user: dict = Depends(get_current_user),
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """
    Get unified balance view across ALL chains
    
    Returns:
    - Total USD value
    - Asset balances with USD values
    - Chain information (hidden from UI)
    """
    
    result = await wallet_service.get_user_balances(current_user["id"])
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Balance query failed"))
    
    return result

@router.post("/send")
async def send_payment(
    request: SendPaymentRequest,
    current_user: dict = Depends(get_current_user),
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """
    Send payment with auto-routing
    
    USER NEVER SEES:
    - Chain selection (auto-routed)
    - Gas fees (abstracted as "transaction fee")
    - Technical errors
    
    USER SEES:
    - "Sending 100 USDT..."
    - "✓ Payment sent!"
    - "Fee: $2.90"
    """
    
    result = await wallet_service.send_payment(
        user_id=current_user["id"],
        recipient=request.recipient,
        asset=request.asset,
        amount=request.amount,
        memo=request.memo
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("message", "Payment failed"))
    
    return result

@router.get("/chains")
async def get_supported_chains():
    """Get list of supported blockchains"""
    
    return {
        "chains": [
            {
                "id": "algorand",
                "name": "Algorand",
                "native_asset": "ALGO",
                "supported_assets": ["ALGO", "USDCa", "USDT", "goBTC", "goETH"],
                "speed": "4.5 seconds",
                "cost": "0.001 ALGO"
            },
            {
                "id": "bitcoin",
                "name": "Bitcoin",
                "native_asset": "BTC",
                "supported_assets": ["BTC"],
                "speed": "10-60 minutes",
                "cost": "Variable"
            },
            {
                "id": "lightning",
                "name": "Lightning Network",
                "native_asset": "BTC",
                "supported_assets": ["BTC"],
                "speed": "Instant",
                "cost": "<$0.01"
            },
            {
                "id": "ethereum",
                "name": "Ethereum",
                "native_asset": "ETH",
                "supported_assets": ["ETH", "USDT", "USDC"],
                "speed": "12 seconds",
                "cost": "Gasless (USDT pays)"
            },
            {
                "id": "polygon",
                "name": "Polygon",
                "native_asset": "MATIC",
                "supported_assets": ["MATIC", "USDT", "USDC"],
                "speed": "2 seconds",
                "cost": "Gasless (USDT pays)"
            },
            {
                "id": "arbitrum",
                "name": "Arbitrum",
                "native_asset": "ETH",
                "supported_assets": ["ETH", "USDT", "USDC"],
                "speed": "1 second",
                "cost": "Gasless (USDT pays)"
            },
            {
                "id": "ton",
                "name": "TON",
                "native_asset": "TON",
                "supported_assets": ["TON", "USDT"],
                "speed": "5 seconds",
                "cost": "~$0.01"
            },
            {
                "id": "tron",
                "name": "TRON",
                "native_asset": "TRX",
                "supported_assets": ["TRX", "USDT"],
                "speed": "3 seconds",
                "cost": "~$0.05"
            },
            {
                "id": "solana",
                "name": "Solana",
                "native_asset": "SOL",
                "supported_assets": ["SOL", "USDT", "USDC"],
                "speed": "<1 second",
                "cost": "~$0.001"
            }
        ],
        "total_chains": 9,
        "gasless_chains": ["ethereum", "polygon", "arbitrum"]
    }