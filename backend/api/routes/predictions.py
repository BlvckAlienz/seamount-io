# File: backend/api/routes/predictions.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from decimal import Decimal
import os
from pathlib import Path
from web3 import Web3
from eth_account import Account
import logging
from backend.dependencies import get_current_user, get_db_service, get_supabase_client
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["Prediction Markets"])

# ========================================================================
# CONFIGURATION
# ========================================================================
# Load .env from backend directory
from dotenv import load_dotenv

# Get backend directory path (3 levels up: routes -> api -> backend)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BACKEND_DIR / ".env"

# Load environment variables from backend/.env
load_dotenv(dotenv_path=ENV_PATH)

CAMP_RPC = os.getenv("CAMP_TESTNET_RPC", "https://rpc.camp-network-testnet.gelato.digital")
CONTRACT_ADDRESS = os.getenv("PREDICTIONS_CONTRACT_ADDRESS")
USDC_ADDRESS = "0x977fdEF62CE095Ae8750Fd3496730F24F60dea7a"  # Camp Testnet USDC

# Web3 setup
w3 = Web3(Web3.HTTPProvider(CAMP_RPC))

# Simplified ABI (add full ABI from your contract)
MARKET_ABI = [
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "_usdcAddress",
				"type": "address"
			}
		],
		"stateMutability": "nonpayable",
		"type": "constructor"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "marketId",
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
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "newYesOdds",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "newNoOdds",
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
				"name": "marketId",
				"type": "uint256"
			}
		],
		"name": "claimWinnings",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "address",
				"name": "by",
				"type": "address"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "timestamp",
				"type": "uint256"
			}
		],
		"name": "ContractPaused",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "address",
				"name": "by",
				"type": "address"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "timestamp",
				"type": "uint256"
			}
		],
		"name": "ContractUnpaused",
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
				"internalType": "string",
				"name": "description",
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
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "address",
				"name": "oldCollector",
				"type": "address"
			},
			{
				"indexed": True,
				"internalType": "address",
				"name": "newCollector",
				"type": "address"
			}
		],
		"name": "FeeCollectorUpdated",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "marketId",
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
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "timestamp",
				"type": "uint256"
			}
		],
		"name": "MarketCreated",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "marketId",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "bool",
				"name": "outcome",
				"type": "bool"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "lockedYesPool",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "lockedNoPool",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "timestamp",
				"type": "uint256"
			}
		],
		"name": "MarketResolved",
		"type": "event"
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
				"name": "marketId",
				"type": "uint256"
			},
			{
				"internalType": "bool",
				"name": "prediction",
				"type": "bool"
			},
			{
				"internalType": "uint256",
				"name": "amount",
				"type": "uint256"
			}
		],
		"name": "placeBet",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "marketId",
				"type": "uint256"
			}
		],
		"name": "recoverUnclaimedFunds",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "marketId",
				"type": "uint256"
			},
			{
				"internalType": "bool",
				"name": "outcome",
				"type": "bool"
			}
		],
		"name": "resolveMarket",
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
				"name": "marketId",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "amount",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "timestamp",
				"type": "uint256"
			}
		],
		"name": "UnclaimedFundsRecovered",
		"type": "event"
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
				"internalType": "address",
				"name": "newCollector",
				"type": "address"
			}
		],
		"name": "updateFeeCollector",
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
				"name": "marketId",
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
				"name": "grossPayout",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "fee",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "netPayout",
				"type": "uint256"
			}
		],
		"name": "WinningsClaimed",
		"type": "event"
	},
	{
		"inputs": [],
		"name": "CLAIM_DEADLINE_DAYS",
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
		"inputs": [],
		"name": "getActiveMarketIds",
		"outputs": [
			{
				"internalType": "uint256[]",
				"name": "",
				"type": "uint256[]"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "getContractStatus",
		"outputs": [
			{
				"internalType": "bool",
				"name": "paused",
				"type": "bool"
			},
			{
				"internalType": "address",
				"name": "owner",
				"type": "address"
			},
			{
				"internalType": "address",
				"name": "collector",
				"type": "address"
			},
			{
				"internalType": "uint256",
				"name": "totalMarkets",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "totalFees",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "contractBalance",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "getCurrentBlockTimestamp",
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
				"name": "marketId",
				"type": "uint256"
			}
		],
		"name": "getMarketDetails",
		"outputs": [
			{
				"internalType": "string",
				"name": "question",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "description",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "endTime",
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
				"internalType": "uint256",
				"name": "totalVolume",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "participantCount",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "yesOdds",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "noOdds",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "timeRemaining",
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
				"name": "marketId",
				"type": "uint256"
			}
		],
		"name": "getMarketOdds",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "yesOdds",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "noOdds",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "yesPercentage",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "noPercentage",
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
				"name": "marketId",
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
				"name": "yesBet",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "noBet",
				"type": "uint256"
			},
			{
				"internalType": "bool",
				"name": "hasClaimed",
				"type": "bool"
			},
			{
				"internalType": "uint256",
				"name": "potentialPayout",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "LIQUIDITY_MULTIPLIER",
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
				"internalType": "string",
				"name": "description",
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
				"internalType": "uint256",
				"name": "lockedYesPool",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "lockedNoPool",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "lockedTotalPool",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "currentYesBets",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "currentNoBets",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "participantCount",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "MAX_FEE_RATE",
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
		"name": "ONE_DAY",
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
		"name": "ONE_HOUR",
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
		"name": "PLATFORM_FEE_RATE",
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
		"name": "totalFeesCollected",
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
		"name": "usdcToken",
		"outputs": [
			{
				"internalType": "contract IERC20",
				"name": "",
				"type": "address"
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
    prediction: bool  # True = YES, False = NO
    amount: Decimal

# ========================================================================
# ROUTES
# ========================================================================

@router.get("/markets")
async def get_active_markets():
    """
    ðŸ"Š GET ACTIVE PREDICTION MARKETS
    Open to ALL users (no authentication required for viewing)
    """
    try:
        if not CONTRACT_ADDRESS:
            raise HTTPException(
                status_code=503, 
                detail="Prediction markets not configured. Set PREDICTIONS_CONTRACT_ADDRESS in .env"
            )
        
        # Connect to contract
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=MARKET_ABI
        )
        
        # Get market count
        market_count = contract.functions.marketCount().call()
        logger.info(f"Total markets: {market_count}")
        
        if market_count == 0:
            return {
                'success': True,
                'markets': [],
                'total': 0,
                'message': 'No markets created yet'
            }
        
        # Fetch all markets
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
                    'totalVolume': str(details[5]),  # Convert to string for JSON
                    'participantCount': details[6],
                    'yesOdds': details[7],
                    'noOdds': details[8],
                    'timeRemaining': details[9],
                    # Human-readable percentages
                    'yesPercent': round(details[7] / 100, 2),  # 5000 basis points = 50.00%
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
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch markets: {str(e)}"
        )

@router.get("/markets/{market_id}")
async def get_market_details(market_id: int):
    """
    ðŸ" GET SPECIFIC MARKET DETAILS
    """
    try:
        if not CONTRACT_ADDRESS:
            raise HTTPException(status_code=503, detail="Prediction markets not configured")
        
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=MARKET_ABI
        )
        
        # Verify market exists
        market_count = contract.functions.marketCount().call()
        if market_id >= market_count:
            raise HTTPException(status_code=404, detail=f"Market {market_id} does not exist")
        
        details = contract.functions.getMarketDetails(market_id).call()
        
        return {
            'success': True,
            'market': {
                'id': market_id,
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
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch market {market_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bet")
async def place_bet(
    request: PlaceBetRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    💰 PLACE BET ON PREDICTION MARKET
    ✅ Authenticated users only
    ✅ Records bet in database
    ✅ Triggers on-chain transaction (future)
    """
    try:
        if not CONTRACT_ADDRESS:
            raise HTTPException(status_code=503, detail="Prediction markets not configured")
        
        # 1️⃣ VALIDATE USER HAS WALLET
        user_id = current_user.get("id")
        supabase = get_supabase_client()
        
        user_profile = supabase.table('user_profiles').select('*').eq('id', user_id).single().execute()
        if not user_profile.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # 2️⃣ VALIDATE MARKET EXISTS
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=MARKET_ABI
        )
        
        market_count = contract.functions.marketCount().call()
        if request.market_id >= market_count:
            raise HTTPException(status_code=404, detail=f"Market {request.market_id} does not exist")
        
        # Check market hasn't ended
        market_details = contract.functions.getMarketDetails(request.market_id).call()
        if market_details[9] <= 0:  # timeRemaining
            raise HTTPException(status_code=400, detail="Market has already ended")
        
        # 3️⃣ VALIDATE BET AMOUNT
        min_bet = Decimal("1.0")  # $1 minimum
        max_bet = Decimal("10000.0")  # $10k maximum
        
        if request.amount < min_bet:
            raise HTTPException(status_code=400, detail=f"Minimum bet is ${min_bet}")
        if request.amount > max_bet:
            raise HTTPException(status_code=400, detail=f"Maximum bet is ${max_bet}")
        
        # 4️⃣ RECORD BET IN DATABASE
        bet_data = {
            "user_id": user_id,
            "market_id": request.market_id,
            "prediction": request.prediction,
            "amount": float(request.amount),
            "status": "pending",
            "tx_hash": None,  # Will be updated after on-chain tx
            "created_at": datetime.utcnow().isoformat()
        }
        
        db_result = supabase.table('prediction_bets').insert(bet_data).execute()
        
        if not db_result.data:
            raise HTTPException(status_code=500, detail="Failed to record bet")
        
        bet_record = db_result.data[0]
        
        logger.info(f"✅ Bet recorded: User {user_id} placed ${request.amount} {request.prediction} on market {request.market_id}")
        
        # 5️⃣ TODO: TRIGGER ON-CHAIN TRANSACTION
        # For now, return success with instructions for manual on-chain bet
        
        return {
            "success": True,
            "message": "Bet recorded successfully! Complete transaction on-chain to finalize.",
            "bet_id": bet_record["id"],
            "bet": bet_record,
            "next_steps": {
                "action": "approve_and_bet",
                "contract_address": CONTRACT_ADDRESS,
                "usdc_address": USDC_ADDRESS,
                "amount_wei": str(int(request.amount * 1_000_000)),  # Convert to 6 decimals
                "instructions": "Use your wallet to approve USDC and call placeBet() on the contract"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Bet placement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bet placement failed: {str(e)}")

@router.get("/my-bets")
async def get_my_bets(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    📊 GET USER'S BET HISTORY
    Returns all bets placed by authenticated user
    """
    try:
        user_id = current_user.get("id")
        supabase = get_supabase_client()
        
        # Fetch user's bets
        bets_result = supabase.table('prediction_bets')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .execute()
        
        if not bets_result.data:
            return {
                "success": True,
                "bets": [],
                "total": 0
            }
        
        # Enrich bets with market details
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
                    "outcome": market_details[4],
                    "current_yes_odds": market_details[7],
                    "current_no_odds": market_details[8]
                }
                
                # Calculate potential payout (simplified)
                if not bet_enriched['resolved']:
                    odds = market_details[7] if bet['prediction'] else market_details[8]
                    bet_enriched['payout'] = float(bet['amount']) * (10000 / odds) * 0.982  # After 1.8% fee
                
                # Determine if user won
                if bet_enriched['resolved']:
                    bet_enriched['won'] = (bet['prediction'] == market_details[4])
                
                enriched_bets.append(bet_enriched)
                
            except Exception as market_err:
                logger.error(f"Failed to enrich bet {bet['id']}: {market_err}")
                enriched_bets.append(bet)
        
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
    âœ… HEALTH CHECK FOR PREDICTION MARKETS
    """
    try:
        if not CONTRACT_ADDRESS:
            return {
                'status': 'not_configured',
                'message': 'Set PREDICTIONS_CONTRACT_ADDRESS in .env file',
                'rpc_connected': w3.is_connected()
            }
        
        # Test RPC connection
        rpc_connected = w3.is_connected()
        
        # Test contract read
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
        logger.error(f"Predictions health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'rpc_connected': w3.is_connected()
        }