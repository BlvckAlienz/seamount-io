# File: backend/api/routes/predictions.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from decimal import Decimal

from backend.dependencies import get_current_user, get_db_service
from backend.services.prediction_market_service import PredictionMarketService

router = APIRouter(prefix="/predictions", tags=["Prediction Markets"])

class PlaceBetRequest(BaseModel):
    market_id: int
    prediction: bool  # True = YES, False = NO
    amount: Decimal

@router.get("/markets")
async def get_active_markets(
    db_service = Depends(get_db_service)
):
    """
    📊 GET ACTIVE PREDICTION MARKETS
    Open to ALL users (no authentication required for viewing)
    """
    try:
        # Initialize prediction service with Camp Network config
        prediction_service = PredictionMarketService(
            db_service=db_service,
            web3_provider="https://rpc.camp-network-testnet.gelato.digital",  # Camp Basecamp Testnet RPC
            contract_address="0xc54a1b1ac9890191aB56849B45bA5C0604293A75",  # Deploy contract first
            contract_abi=[
                {
                    "inputs": [
                        {
                            "internalType": "address",
                            "name": "account",
                            "type": "address"
                        }
                    ],
                    "name": "balanceOf",
                    "outputs": [
                        {
                            "internalType": "uint256",
                            "name": "",
                            "type": "uint256"
                        }
                    ],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [
                        {
                            "internalType": "address",
                            "name": "to",
                            "type": "address"
                        },
                        {
                            "internalType": "uint256",
                            "name": "amount",
                            "type": "uint256"
                        }
                    ],
                    "name": "transfer",
                    "outputs": [
                        {
                            "internalType": "bool",
                            "name": "",
                            "type": "bool"
                        }
                    ],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {
                            "internalType": "address",
                            "name": "from",
                            "type": "address"
                        },
                        {
                            "internalType": "address",
                            "name": "to",
                            "type": "address"
                        },
                        {
                            "internalType": "uint256",
                            "name": "amount",
                            "type": "uint256"
                        }
                    ],
                    "name": "transferFrom",
                    "outputs": [
                        {
                            "internalType": "bool",
                            "name": "",
                            "type": "bool"
                        }
                    ],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
        )
        
        markets = await prediction_service.get_active_markets()
        
        return {
            'success': True,
            'markets': markets,
            'total': len(markets)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bet")
async def place_bet(
    request: PlaceBetRequest,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    💰 PLACE BET ON PREDICTION MARKET
    Requires authentication
    """
    try:
        user_id = current_user['id']
        
        # Get user's Camp Network wallet
        wallet = await db_service.execute_query(
            "SELECT algorand_address, algorand_private_key FROM public.user_wallets WHERE user_id = %s",
            (user_id,)
        )
        
        if not wallet:
            raise HTTPException(status_code=400, detail="No wallet found - create wallet first")
        
        prediction_service = PredictionMarketService(
            db_service=db_service,
            web3_provider="https://rpc.camp-network-testnet.gelato.digital",
            contract_address="0xc54a1b1ac9890191aB56849B45bA5C0604293A75",
            contract_abi=[
                {
                    "inputs": [
                        {
                            "internalType": "address",
                            "name": "account",
                            "type": "address"
                        }
                    ],
                    "name": "balanceOf",
                    "outputs": [
                        {
                            "internalType": "uint256",
                            "name": "",
                            "type": "uint256"
                        }
                    ],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [
                        {
                            "internalType": "address",
                            "name": "to",
                            "type": "address"
                        },
                        {
                            "internalType": "uint256",
                            "name": "amount",
                            "type": "uint256"
                        }
                    ],
                    "name": "transfer",
                    "outputs": [
                        {
                            "internalType": "bool",
                            "name": "",
                            "type": "bool"
                        }
                    ],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {
                            "internalType": "address",
                            "name": "from",
                            "type": "address"
                        },
                        {
                            "internalType": "address",
                            "name": "to",
                            "type": "address"
                        },
                        {
                            "internalType": "uint256",
                            "name": "amount",
                            "type": "uint256"
                        }
                    ],
                    "name": "transferFrom",
                    "outputs": [
                        {
                            "internalType": "bool",
                            "name": "",
                            "type": "bool"
                        }
                    ],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
        )
        
        result = await prediction_service.place_bet(
            user_id=user_id,
            market_id=request.market_id,
            prediction=request.prediction,
            amount=request.amount,
            user_wallet_address=wallet[0]['algorand_address'],  # Reusing existing wallet system
            user_private_key=wallet[0]['algorand_private_key']
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-bets")
async def get_my_bets(
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    📜 GET USER'S BET HISTORY & P&L
    """
    try:
        user_id = current_user['id']
        
        prediction_service = PredictionMarketService(
            db_service=db_service,
            web3_provider="https://rpc.camp-network-testnet.gelato.digital",
            contract_address="0xc54a1b1ac9890191aB56849B45bA5C0604293A75",
            contract_abi=[
                {
                    "inputs": [
                        {
                            "internalType": "address",
                            "name": "account",
                            "type": "address"
                        }
                    ],
                    "name": "balanceOf",
                    "outputs": [
                        {
                            "internalType": "uint256",
                            "name": "",
                            "type": "uint256"
                        }
                    ],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [
                        {
                            "internalType": "address",
                            "name": "to",
                            "type": "address"
                        },
                        {
                            "internalType": "uint256",
                            "name": "amount",
                            "type": "uint256"
                        }
                    ],
                    "name": "transfer",
                    "outputs": [
                        {
                            "internalType": "bool",
                            "name": "",
                            "type": "bool"
                        }
                    ],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {
                            "internalType": "address",
                            "name": "from",
                            "type": "address"
                        },
                        {
                            "internalType": "address",
                            "name": "to",
                            "type": "address"
                        },
                        {
                            "internalType": "uint256",
                            "name": "amount",
                            "type": "uint256"
                        }
                    ],
                    "name": "transferFrom",
                    "outputs": [
                        {
                            "internalType": "bool",
                            "name": "",
                            "type": "bool"
                        }
                    ],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
        )
        
        bets = await prediction_service.get_user_bets(user_id)
        
        # Calculate total P&L
        total_wagered = sum(bet['amount'] for bet in bets)
        total_won = sum(bet.get('payout', 0) for bet in bets if bet.get('won'))
        net_profit = total_won - total_wagered
        
        return {
            'success': True,
            'bets': bets,
            'stats': {
                'total_wagered': float(total_wagered),
                'total_won': float(total_won),
                'net_profit': float(net_profit),
                'win_rate': len([b for b in bets if b.get('won')]) / len(bets) if bets else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))