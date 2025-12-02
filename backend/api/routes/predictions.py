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
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    💰 PLACE BET ON PREDICTION MARKET
    ✅ Authenticated users only
    ✅ Records bet in database
    ✅ Returns transaction instructions
    """
    try:
        if not CONTRACT_ADDRESS:
            raise HTTPException(status_code=503, detail="Prediction markets not configured")
        
        user_id = current_user.get("id")
        
        # 1️⃣ VALIDATE MARKET EXISTS & IS ACTIVE
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=MARKET_ABI
        )
        
        market_count = contract.functions.marketCount().call()
        if request.market_id >= market_count:
            raise HTTPException(status_code=404, detail=f"Market {request.market_id} does not exist")
        
        # Get market details
        market_details = contract.functions.getMarketDetails(request.market_id).call()
        
        # Check market is still open
        if market_details[9] <= 0:  # timeRemaining
            raise HTTPException(status_code=400, detail="Market has already ended")
        
        if market_details[3]:  # resolved
            raise HTTPException(status_code=400, detail="Market already resolved")
        
        # 2️⃣ VALIDATE BET AMOUNT
        min_bet = Decimal("1.0")
        max_bet = Decimal("10000.0")
        
        if request.amount < min_bet:
            raise HTTPException(status_code=400, detail=f"Minimum bet is ${min_bet}")
        if request.amount > max_bet:
            raise HTTPException(status_code=400, detail=f"Maximum bet is ${max_bet}")
        
        # 3️⃣ RECORD BET IN DATABASE
        supabase = get_supabase_client()
        
        bet_data = {
            "user_id": user_id,
            "market_id": request.market_id,
            "prediction": request.prediction,
            "amount": float(request.amount),
            "status": "pending",
            "tx_hash": None,
            "created_at": datetime.utcnow().isoformat()
        }
        
        db_result = supabase.table('prediction_bets').insert(bet_data).execute()
        
        if not db_result.data:
            raise HTTPException(status_code=500, detail="Failed to record bet")
        
        bet_record = db_result.data[0]
        
        logger.info(f"✅ Bet recorded: User {user_id} placed ${request.amount} ({request.prediction}) on market {request.market_id}")
        
        # 4️⃣ CALCULATE POTENTIAL PAYOUT
        odds = market_details[7] if request.prediction else market_details[8]
        potential_payout = float(request.amount) * (10000 / odds) * 0.982  # After 1.8% fee
        
        return {
            "success": True,
            "message": "Bet recorded successfully! Complete on-chain transaction to finalize.",
            "bet_id": bet_record["id"],
            "bet": {
                **bet_record,
                "potential_payout": round(potential_payout, 2),
                "market_question": market_details[0]
            },
            "on_chain_instructions": {
                "step_1": "Approve USDC spending",
                "step_2": "Call placeBet() on contract",
                "contract_address": CONTRACT_ADDRESS,
                "usdc_address": USDC_ADDRESS,
                "amount_wei": int(request.amount * 1_000_000)  # Convert to 6 decimals
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Bet placement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bet placement failed: {str(e)}")

@router.post("/approve-usdc")
async def approve_usdc_spending(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    🔐 APPROVE USDC SPENDING FOR PREDICTION MARKETS
    
    This endpoint signs an USDC approval transaction on behalf of the user
    (using their encrypted wallet seed) to allow the prediction market contract
    to spend USDC.
    
    ✅ Security: Seed never leaves backend, encrypted at rest
    """
    try:
        bet_id = request.get('bet_id')
        amount = Decimal(str(request.get('amount', 0)))
        
        if not bet_id or amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid bet_id or amount")
        
        user_id = current_user.get("id")
        
        # 1️⃣ GET USER'S ENCRYPTED ETHEREUM WALLET SEED
        from backend.services.database_service import DatabaseService
        db = DatabaseService()
        
        wallet_result = db.supabase.table('multi_chain_addresses')\
            .select('encrypted_seed')\
            .eq('user_id', user_id)\
            .eq('blockchain', 'ethereum')\
            .execute()
        
        if not wallet_result.data or len(wallet_result.data) == 0:
            raise HTTPException(status_code=404, detail="No Ethereum wallet found")
        
        encrypted_seed = wallet_result.data[0]['encrypted_seed']
        
        # 2️⃣ DECRYPT SEED (server-side only)
        from backend.services.seed_encryption_service import SeedEncryptionService
        encryption_service = SeedEncryptionService()
        plaintext_seed = encryption_service.decrypt_seed(encrypted_seed)
        
        # 3️⃣ PREPARE USDC APPROVAL TRANSACTION
        from web3 import Web3
        from eth_account import Account
        
        w3 = Web3(Web3.HTTPProvider("https://rpc-campnetwork.xyz"))
        
        # Derive private key from seed (using BIP39/BIP44 standard)
        # NOTE: This requires hdwallet library
        from hdwallet import HDWallet
        from hdwallet.symbols import ETH
        
        hdwallet = HDWallet(symbol=ETH)
        hdwallet.from_mnemonic(plaintext_seed)
        hdwallet.from_path("m/44'/60'/0'/0/0")  # Standard Ethereum derivation path
        
        private_key = hdwallet.private_key()
        account = Account.from_key(private_key)
        
        # USDC Contract ABI (approve function)
        usdc_abi = [
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]
        
        usdc_contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=usdc_abi
        )
        
        # Convert amount to 6 decimals (USDC precision)
        amount_wei = int(amount * 1_000_000)
        
        # Build transaction
        approve_tx = usdc_contract.functions.approve(
            Web3.to_checksum_address(CONTRACT_ADDRESS),
            amount_wei * 2  # Approve 2x for gas buffer
        ).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 100000,
            'gasPrice': w3.eth.gas_price
        })
        
        # 4️⃣ SIGN AND SEND TRANSACTION
        signed_tx = account.sign_transaction(approve_tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for confirmation (up to 30 seconds)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
        
        if receipt['status'] != 1:
            raise Exception("USDC approval transaction failed on-chain")
        
        logger.info(f"✅ USDC approved: {tx_hash.hex()} for bet {bet_id}")
        
        return {
            "success": True,
            "tx_hash": tx_hash.hex(),
            "message": "USDC spending approved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ USDC approval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")

@router.post("/execute-bet")
async def execute_on_chain_bet(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    ⚡ EXECUTE ON-CHAIN BET (Call placeBet() on smart contract)
    
    Prerequisites:
    - USDC must be approved first (via /approve-usdc)
    - Bet must exist in database
    """
    try:
        bet_id = request.get('bet_id')
        market_id = request.get('market_id')
        prediction = request.get('prediction')
        amount = Decimal(str(request.get('amount', 0)))
        
        if bet_id is None or market_id is None or prediction is None or amount <= 0:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        user_id = current_user.get("id")
        
        # 1️⃣ GET USER'S WALLET
        from backend.services.database_service import DatabaseService
        db = DatabaseService()
        
        wallet_result = db.supabase.table('multi_chain_addresses')\
            .select('encrypted_seed')\
            .eq('user_id', user_id)\
            .eq('blockchain', 'ethereum')\
            .execute()
        
        if not wallet_result.data:
            raise HTTPException(status_code=404, detail="No Ethereum wallet")
        
        encrypted_seed = wallet_result.data[0]['encrypted_seed']
        
        # 2️⃣ DECRYPT SEED
        from backend.services.seed_encryption_service import SeedEncryptionService
        encryption_service = SeedEncryptionService()
        plaintext_seed = encryption_service.decrypt_seed(encrypted_seed)
        
        # 3️⃣ DERIVE PRIVATE KEY
        from web3 import Web3
        from eth_account import Account
        from hdwallet import HDWallet
        from hdwallet.symbols import ETH
        
        w3 = Web3(Web3.HTTPProvider("https://rpc-campnetwork.xyz"))
        
        hdwallet = HDWallet(symbol=ETH)
        hdwallet.from_mnemonic(plaintext_seed)
        hdwallet.from_path("m/44'/60'/0'/0/0")
        
        private_key = hdwallet.private_key()
        account = Account.from_key(private_key)
        
        # 4️⃣ CALL placeBet() ON SMART CONTRACT
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=MARKET_ABI
        )
        
        amount_wei = int(amount * 1_000_000)  # 6 decimals for USDC
        
        place_bet_tx = contract.functions.placeBet(
            market_id,
            prediction,
            amount_wei
        ).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 300000,
            'gasPrice': w3.eth.gas_price
        })
        
        # 5️⃣ SIGN AND SEND
        signed_tx = account.sign_transaction(place_bet_tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        
        if receipt['status'] != 1:
            raise Exception("Bet transaction failed on-chain")
        
        # 6️⃣ UPDATE DATABASE BET RECORD
        supabase = get_supabase_client()
        
        update_result = supabase.table('prediction_bets').update({
            'tx_hash': tx_hash.hex(),
            'status': 'confirmed',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', bet_id).execute()
        
        logger.info(f"✅ On-chain bet placed: {tx_hash.hex()} for bet {bet_id}")
        
        return {
            "success": True,
            "tx_hash": tx_hash.hex(),
            "message": "Bet placed on-chain successfully",
            "explorer_url": f"https://camp.cloud.blockscout.com/tx/{tx_hash.hex()}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ On-chain bet execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")
        
@router.get("/my-bets")
async def get_my_bets(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    📊 GET USER'S BET HISTORY
    Returns all bets with enriched market data
    """
    try:
        user_id = current_user.get("id")
        supabase = get_supabase_client()
        
        # Fetch user's bets from database
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
        
        # Enrich with on-chain market details
        if not CONTRACT_ADDRESS:
            return {
                "success": True,
                "bets": bets_result.data,
                "total": len(bets_result.data),
                "warning": "Contract not configured, showing database records only"
            }
        
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=MARKET_ABI
        )
        
        enriched_bets = []
        for bet in bets_result.data:
            try:
                # Get live market data
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
                
                # Calculate potential/actual payout
                if not market_details[3]:  # Market not resolved
                    odds = market_details[7] if bet['prediction'] else market_details[8]
                    bet_enriched['payout'] = round(float(bet['amount']) * (10000 / odds) * 0.982, 2)
                    bet_enriched['status'] = 'pending'
                else:  # Market resolved
                    bet_enriched['won'] = (bet['prediction'] == market_details[4])
                    
                    if bet_enriched['won']:
                        # Calculate winnings
                        odds = market_details[7] if bet['prediction'] else market_details[8]
                        bet_enriched['payout'] = round(float(bet['amount']) * (10000 / odds) * 0.982, 2)
                        bet_enriched['status'] = 'claimable' if not bet.get('claimed') else 'claimed'
                    else:
                        bet_enriched['payout'] = 0
                        bet_enriched['status'] = 'lost'
                
                enriched_bets.append(bet_enriched)
                
            except Exception as market_err:
                logger.error(f"Failed to enrich bet {bet['id']}: {market_err}")
                # Return bet without enrichment
                enriched_bets.append({
                    **bet,
                    "error": "Failed to fetch market details"
                })
        
        # Calculate portfolio summary
        total_staked = sum(float(b['amount']) for b in enriched_bets)
        active_bets = [b for b in enriched_bets if b.get('status') == 'pending']
        won_bets = [b for b in enriched_bets if b.get('won')]
        total_winnings = sum(b.get('payout', 0) for b in won_bets)
        
        return {
            "success": True,
            "bets": enriched_bets,
            "total": len(enriched_bets),
            "summary": {
                "total_staked": round(total_staked, 2),
                "active_bets": len(active_bets),
                "won_bets": len(won_bets),
                "total_winnings": round(total_winnings, 2),
                "roi": round(((total_winnings - total_staked) / total_staked * 100), 2) if total_staked > 0 else 0
            }
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