# File: backend/api/routes/predictions.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from decimal import Decimal
import os
from pathlib import Path
from web3 import Web3
import logging
from backend.dependencies import get_current_user, get_supabase_client
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["Prediction Markets"])

# ========================================================================
# CONFIGURATION
# ========================================================================
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BACKEND_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

CAMP_RPC = os.getenv("CAMP_TESTNET_RPC", "https://rpc.camp-network-testnet.gelato.digital")
CONTRACT_ADDRESS = os.getenv("PREDICTIONS_CONTRACT_ADDRESS")

# Web3 setup
w3 = Web3(Web3.HTTPProvider(CAMP_RPC))

# Full ABI from your contract
MARKET_ABI = [
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"internalType": "bool",
				"name": "prediction",
				"type": "bool"
			}
		],
		"name": "bet",
		"outputs": [],
		"stateMutability": "payable",
		"type": "function"
	},
	{
		"inputs": [],
		"stateMutability": "nonpayable",
		"type": "constructor"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"indexed": True,
				"internalType": "address",
				"name": "user",
				"type": "address"
			},
			{
				"indexed": False,
				"internalType": "bool",
				"name": "prediction",
				"type": "bool"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "amount",
				"type": "uint256"
			}
		],
		"name": "BetPlaced",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			}
		],
		"name": "bootstrapMarket",
		"outputs": [],
		"stateMutability": "payable",
		"type": "function"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "yes",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "no",
				"type": "uint256"
			}
		],
		"name": "Bootstrapped",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			}
		],
		"name": "claim",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"indexed": True,
				"internalType": "address",
				"name": "user",
				"type": "address"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "amount",
				"type": "uint256"
			}
		],
		"name": "Claimed",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "string",
				"name": "question",
				"type": "string"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "endTime",
				"type": "uint256"
			}
		],
		"name": "Created",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "question",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "endTime",
				"type": "uint256"
			}
		],
		"name": "createMarket",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "emergencyWithdraw",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "pause",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			}
		],
		"name": "recover",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"internalType": "bool",
				"name": "outcome",
				"type": "bool"
			}
		],
		"name": "resolve",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "bool",
				"name": "outcome",
				"type": "bool"
			}
		],
		"name": "Resolved",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "a",
				"type": "address"
			}
		],
		"name": "setFeeCollector",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "unpause",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			},
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"name": "claimed",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "DEADLINE",
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
		"inputs": [],
		"name": "feeCollector",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			}
		],
		"name": "getMarket",
		"outputs": [
			{
				"internalType": "string",
				"name": "",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			},
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			}
		],
		"name": "getPools",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			},
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
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"internalType": "address",
				"name": "user",
				"type": "address"
			}
		],
		"name": "getUserBet",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			},
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "HIGH_FEE",
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
		"inputs": [],
		"name": "LOW_FEE",
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
		"inputs": [],
		"name": "marketCount",
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
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"name": "markets",
		"outputs": [
			{
				"internalType": "string",
				"name": "question",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "endTime",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "resolutionTime",
				"type": "uint256"
			},
			{
				"internalType": "bool",
				"name": "resolved",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "outcome",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "bootstrapped",
				"type": "bool"
			},
			{
				"internalType": "uint256",
				"name": "lockedYes",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "lockedNo",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "lockedTotal",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "currentYes",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "currentNo",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "participants",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "MAX_ODDS",
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
		"inputs": [],
		"name": "MED_FEE",
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
		"inputs": [],
		"name": "MIN_BET",
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
		"inputs": [],
		"name": "MIN_BOOT",
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
		"inputs": [],
		"name": "MIN_ODDS",
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
		"inputs": [],
		"name": "MULTIPLIER",
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
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			},
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"name": "noBets",
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
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			}
		],
		"name": "odds",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "yes",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "no",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			},
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"name": "participated",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "totalFees",
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
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			},
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"name": "yesBets",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
]

# ========================================================================
# PYDANTIC MODELS
# ========================================================================
class PlaceBetRequest(BaseModel):
    market_id: int
    prediction: bool
    amount: Decimal
    user_wallet: str  # NEW: User's MetaMask address

class RecordBetRequest(BaseModel):
    market_id: int
    prediction: bool
    amount: Decimal
    user_wallet: str
    tx_hash: str  # Transaction hash from frontend

# ========================================================================
# ROUTES
# ========================================================================

@router.get("/markets")
async def get_active_markets():
    """
    📊 GET ACTIVE PREDICTION MARKETS
    """
    try:
        if not CONTRACT_ADDRESS:
            raise HTTPException(
                status_code=503, 
                detail="Prediction markets not configured"
            )
        
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=MARKET_ABI
        )
        
        market_count = contract.functions.marketCount().call()
        logger.info(f"Total markets: {market_count}")
        
        if market_count == 0:
            return {
                'success': True,
                'markets': [],
                'total': 0,
                'message': 'No markets created yet'
            }
        
        markets = []
        for i in range(market_count):
            try:
                details = contract.functions.getMarketDetails(i).call()
                
                market_data = {
                    'id': i,
                    'question': details[0],
                    'description': details[1],
                    'endTime': details[2],
                    'resolved': details[3],
                    'outcome': details[4],
                    'totalVolume': str(details[5]),
                    'participantCount': details[6],
                    'yesOdds': details[7],
                    'noOdds': details[8],
                    'timeRemaining': details[9],
                    'yesPercent': round(details[7] / 100, 2),
                    'noPercent': round(details[8] / 100, 2)
                }
                
                markets.append(market_data)
                
            except Exception as market_error:
                logger.error(f"Error fetching market {i}: {market_error}")
                continue
        
        return {
            'success': True,
            'markets': markets,
            'total': len(markets),
            'contract_address': CONTRACT_ADDRESS,
            'rpc_url': CAMP_RPC
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bet")
async def place_bet(
    request: PlaceBetRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    💰 RECORD BET INTENT (Frontend will execute via MetaMask)
    """
    try:
        if not CONTRACT_ADDRESS:
            raise HTTPException(status_code=503, detail="Prediction markets not configured")
        
        user_id = current_user.get("id")
        
        # Validate market exists
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=MARKET_ABI
        )
        
        market_count = contract.functions.marketCount().call()
        if request.market_id >= market_count:
            raise HTTPException(status_code=404, detail=f"Market {request.market_id} does not exist")
        
        # Get market details
        market_details = contract.functions.getMarketDetails(request.market_id).call()
        
        if market_details[9] <= 0:  # timeRemaining
            raise HTTPException(status_code=400, detail="Market has already ended")
        
        if market_details[3]:  # resolved
            raise HTTPException(status_code=400, detail="Market already resolved")
        
        # Validate bet amount
        min_bet = Decimal("0.01")
        if request.amount < min_bet:
            raise HTTPException(status_code=400, detail=f"Minimum bet is {min_bet} CAMP")
        
        # Record bet intent in database
        supabase = get_supabase_client()
        
        bet_data = {
            "user_id": user_id,
            "market_id": request.market_id,
            "prediction": request.prediction,
            "amount": float(request.amount),
            "user_wallet": request.user_wallet,
            "status": "pending",
            "tx_hash": None,
            "created_at": datetime.utcnow().isoformat()
        }
        
        db_result = supabase.table('prediction_bets').insert(bet_data).execute()
        
        if not db_result.data:
            raise HTTPException(status_code=500, detail="Failed to record bet")
        
        bet_record = db_result.data[0]
        
        logger.info(f"✅ Bet intent recorded: {user_id} - {request.amount} CAMP on market {request.market_id}")
        
        # Calculate potential payout
        odds = market_details[7] if request.prediction else market_details[8]
        potential_payout = float(request.amount) * (10000 / odds) * 0.982
        
        # Calculate potential payout
        odds = market_details[7] if request.prediction else market_details[8]
        potential_payout = float(request.amount) * (10000 / odds) * 0.982

        # ✅ Convert Decimal to int for wei calculation
        amount_in_wei = int(float(request.amount) * 1e18)

        # ✅ ENCODE THE CONTRACT FUNCTION CALL
        from eth_abi import encode

        # Encode placeBet(uint256 marketId, bool prediction)
        function_signature = "placeBet(uint256,bool)"
        function_selector = w3.keccak(text=function_signature)[:4].hex()

        # Encode parameters
        encoded_params = encode(
            ['uint256', 'bool'],
            [request.market_id, request.prediction]
        ).hex()

        # Combine selector + params
        encoded_data = f"0x{function_selector[2:]}{encoded_params}"

        logger.info(f"📝 Encoded transaction data: {encoded_data}")

        return {
            "success": True,
            "message": "Bet intent recorded. Execute via MetaMask.",
            "bet_id": bet_record["id"],
            "contract_address": CONTRACT_ADDRESS,
            "contract_function": {
                "name": "placeBet",
                "params": [request.market_id, request.prediction],
                "value_in_wei": amount_in_wei,
                "encoded_data": encoded_data  # ✅ NOW ACTUALLY ENCODED
            },
            "potential_payout": round(potential_payout, 4)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Bet placement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confirm-bet")
async def confirm_bet(
    request: RecordBetRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    ✅ CONFIRM BET AFTER ON-CHAIN EXECUTION
    Frontend calls this after MetaMask transaction succeeds
    """
    try:
        user_id = current_user.get("id")
        supabase = get_supabase_client()
        
        # Find pending bet
        pending_bet = supabase.table('prediction_bets')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('market_id', request.market_id)\
            .eq('status', 'pending')\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if not pending_bet.data:
            raise HTTPException(status_code=404, detail="No pending bet found")
        
        bet_id = pending_bet.data[0]['id']
        
        # Update bet with transaction hash
        update_result = supabase.table('prediction_bets').update({
            'tx_hash': request.tx_hash,
            'status': 'confirmed',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', bet_id).execute()
        
        logger.info(f"✅ Bet confirmed: {bet_id} - TX: {request.tx_hash}")
        
        return {
            "success": True,
            "message": "Bet confirmed on-chain!",
            "bet_id": bet_id,
            "tx_hash": request.tx_hash,
            "explorer_url": f"https://camp-network-testnet.blockscout.com/tx/{request.tx_hash}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Bet confirmation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bet/{bet_id}/status")
async def get_bet_status(
    bet_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    🔍 POLL TRANSACTION STATUS
    Returns: pending | confirmed | failed | not_found
    """
    try:
        user_id = current_user.get("id")
        supabase = get_supabase_client()
        
        # 1️⃣ Fetch bet from database
        bet_result = supabase.table('prediction_bets')\
            .select('*')\
            .eq('id', bet_id)\
            .eq('user_id', user_id)\
            .single()\
            .execute()
        
        if not bet_result.data:
            raise HTTPException(status_code=404, detail="Bet not found")
        
        bet = bet_result.data
        tx_hash = bet.get('tx_hash')
        
        if not tx_hash:
            return {
                "success": True,
                "status": "pending",
                "message": "Waiting for transaction signature"
            }
        
        # 2️⃣ Check transaction on blockchain
        try:
            tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
            
            if tx_receipt:
                # Transaction is mined!
                confirmation_status = "confirmed" if tx_receipt['status'] == 1 else "failed"
                block_number = tx_receipt['blockNumber']
                gas_used = tx_receipt['gasUsed']
                
                # 3️⃣ Update database if newly confirmed
                if bet['status'] != confirmation_status:
                    supabase.table('prediction_bets').update({
                        'status': confirmation_status,
                        'block_number': block_number,
                        'gas_used': gas_used,
                        'updated_at': datetime.utcnow().isoformat()
                    }).eq('id', bet_id).execute()
                
                return {
                    "success": True,
                    "status": confirmation_status,
                    "tx_hash": tx_hash,
                    "block_number": block_number,
                    "gas_used": gas_used,
                    "confirmations": w3.eth.block_number - block_number,
                    "explorer_url": f"https://camp-network-testnet.blockscout.com/tx/{tx_hash}",
                    "message": "✅ Transaction confirmed!" if confirmation_status == "confirmed" else "❌ Transaction failed"
                }
            else:
                # Transaction still pending in mempool
                return {
                    "success": True,
                    "status": "pending",
                    "tx_hash": tx_hash,
                    "message": "⏳ Waiting for blockchain confirmation...",
                    "explorer_url": f"https://camp-network-testnet.blockscout.com/tx/{tx_hash}"
                }
                
        except Exception as chain_error:
            # Transaction not found on chain yet
            logger.warning(f"Transaction {tx_hash} not found on chain: {chain_error}")
            return {
                "success": True,
                "status": "pending",
                "tx_hash": tx_hash,
                "message": "⏳ Broadcasting to network...",
                "explorer_url": f"https://camp-network-testnet.blockscout.com/tx/{tx_hash}"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bet status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/my-bets")
async def get_my_bets(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    📊 GET USER'S BET HISTORY (ONLY CONFIRMED BETS)
    """
    try:
        user_id = current_user.get("id")
        supabase = get_supabase_client()
        
        # Fetch confirmed bets only
        bets_result = supabase.table('prediction_bets')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('status', 'confirmed')\
            .order('created_at', desc=True)\
            .execute()
        
        if not bets_result.data:
            return {
                "success": True,
                "bets": [],
                "total": 0
            }
        
        # Enrich with market details
        if not CONTRACT_ADDRESS:
            return {
                "success": True,
                "bets": bets_result.data,
                "total": len(bets_result.data)
            }
        
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=MARKET_ABI
        )
        
        enriched_bets = []
        for bet in bets_result.data:
            try:
                market_details = contract.functions.getMarketDetails(bet['market_id']).call()
                
                bet_enriched = {
                    **bet,
                    "question": market_details[0],
                    "market_end_time": market_details[2],
                    "resolved": market_details[3],
                    "outcome": market_details[4]
                }
                
                # Calculate payout
                if not market_details[3]:  # Not resolved
                    odds = market_details[7] if bet['prediction'] else market_details[8]
                    bet_enriched['payout'] = round(float(bet['amount']) * (10000 / odds) * 0.982, 4)
                    bet_enriched['status'] = 'active'
                else:
                    bet_enriched['won'] = (bet['prediction'] == market_details[4])
                    if bet_enriched['won']:
                        odds = market_details[7] if bet['prediction'] else market_details[8]
                        bet_enriched['payout'] = round(float(bet['amount']) * (10000 / odds) * 0.982, 4)
                        bet_enriched['status'] = 'claimable'
                    else:
                        bet_enriched['payout'] = 0
                        bet_enriched['status'] = 'lost'
                
                enriched_bets.append(bet_enriched)
                
            except Exception as market_err:
                logger.error(f"Failed to enrich bet {bet['id']}: {market_err}")
                continue
        
        return {
            "success": True,
            "bets": enriched_bets,
            "total": len(enriched_bets)
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch user bets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def predictions_health():
    """
    ✅ HEALTH CHECK
    """
    try:
        if not CONTRACT_ADDRESS:
            return {
                'status': 'not_configured',
                'message': 'Set PREDICTIONS_CONTRACT_ADDRESS in .env'
            }
        
        rpc_connected = w3.is_connected()
        
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=MARKET_ABI
        )
        market_count = contract.functions.marketCount().call()
        
        return {
            'status': 'healthy',
            'rpc_connected': rpc_connected,
            'contract_address': CONTRACT_ADDRESS,
            'market_count': market_count,
            'rpc_url': CAMP_RPC
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }