# File: backend/api/routes/predictions.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
import os
from web3 import Web3
from eth_account import Account
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["Prediction Markets"])

# ========================================================================
# CONFIGURATION
# ========================================================================
CAMP_RPC = os.getenv("CAMP_TESTNET_RPC", "https://rpc.camp-network-testnet.gelato.digital")
CONTRACT_ADDRESS = os.getenv("PREDICTIONS_CONTRACT_ADDRESS")  # Set this in .env
USDC_ADDRESS = "0x977fdEF62CE095Ae8750Fd3496730F24F60dea7a"  # Camp Testnet USDC

# Web3 setup
w3 = Web3(Web3.HTTPProvider(CAMP_RPC))

# Simplified ABI (add full ABI from your contract)
MARKET_ABI = [
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
async def place_bet(request: PlaceBetRequest):
    """
    ðŸ'° PLACE BET ON PREDICTION MARKET
    TODO: Add authentication when user system is ready
    """
    raise HTTPException(
        status_code=501,
        detail="Betting endpoint not implemented yet. Use Remix IDE to place bets directly on-chain."
    )

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