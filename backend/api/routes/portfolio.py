# File: backend/api/routes/marketData.py
from fastapi import APIRouter, Depends, HTTPException
from backend.dependencies import get_current_user, get_db_service, get_algorand_service, get_oracle_service
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/marketData/summary")
async def get_marketData_summary(
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    algo_service = Depends(get_algorand_service),
    oracle_service = Depends(get_oracle_service)
):
    try:
        user_id = current_user['id']
        logger.info(f"Fetching marketData summary for user: {user_id}")

        # Get user's wallet - FIX: use algorand_address not wallet_address
        wallet_data = await db_service.get_user_wallet(user_id)
        if not wallet_data:
            # Return empty marketData instead of error
            return {
                "total_balance_usd": 0.0,
                "assets": [],
                "change_24h": 0.0,
                "total_pnl": 0.0,
                "wallet_exists": False
            }
        
        # FIX: Use correct column name from database
        wallet_address = wallet_data.get('algorand_address')  # NOT wallet_address
        if not wallet_address:
            logger.error(f"Wallet data missing algorand_address: {wallet_data}")
            return {
                "total_balance_usd": 0.0,
                "assets": [],
                "change_24h": 0.0,
                "total_pnl": 0.0,
                "wallet_exists": False
            }

        # Get balances from wallet_balances table
        try:
            balance_query = """
                SELECT algo_balance, usdt_balance, usdc_balance, 
                       gobtc_balance, goeth_balance
                FROM wallet_balances 
                WHERE user_id = %s
            """
            balance_result = await db_service.execute_query(balance_query, (user_id,))
            
            if balance_result and len(balance_result) > 0:
                balances = balance_result[0]
                algo_balance = Decimal(str(balances.get('algo_balance', 0)))
                usdt_balance = Decimal(str(balances.get('usdt_balance', 0)))
                usdc_balance = Decimal(str(balances.get('usdc_balance', 0)))
                gobtc_balance = Decimal(str(balances.get('gobtc_balance', 0)))
                goeth_balance = Decimal(str(balances.get('goeth_balance', 0)))
            else:
                # Default to zero balances
                algo_balance = usdt_balance = usdc_balance = gobtc_balance = goeth_balance = Decimal('0')
        except Exception as e:
            logger.warning(f"Failed to get cached balances, using zeros: {e}")
            algo_balance = usdt_balance = usdc_balance = gobtc_balance = goeth_balance = Decimal('0')

        # Get current prices from Oracle
        try:
            algo_price, _ = await oracle_service.get_asset_price('algorand')
            btc_price, _ = await oracle_service.get_asset_price('bitcoin')
            eth_price, _ = await oracle_service.get_asset_price('ethereum')
        except Exception as e:
            logger.warning(f"Oracle price fetch failed, using defaults: {e}")
            algo_price = Decimal('0.18')
            btc_price = Decimal('63500.0')
            eth_price = Decimal('2650.0')
        
        # Stablecoins are ~$1
        usdt_price = usdc_price = Decimal('1.0')

        # Calculate the value of each holding
        algo_value = algo_balance * algo_price
        usdt_value = usdt_balance * usdt_price
        usdc_value = usdc_balance * usdc_price
        gobtc_value = gobtc_balance * btc_price
        goeth_value = goeth_balance * eth_price

        total_value = algo_value + usdt_value + usdc_value + gobtc_value + goeth_value

        # Structure the response
        assets = [
            {
                "name": "Algorand", 
                "symbol": "ALGO", 
                "balance": float(algo_balance), 
                "value_usd": float(algo_value), 
                "price_usd": float(algo_price)
            },
            {
                "name": "Tether USD", 
                "symbol": "USDT", 
                "balance": float(usdt_balance), 
                "value_usd": float(usdt_value), 
                "price_usd": 1.0
            },
            {
                "name": "USD Coin", 
                "symbol": "USDCa", 
                "balance": float(usdc_balance), 
                "value_usd": float(usdc_value), 
                "price_usd": 1.0
            },
            {
                "name": "Wrapped Bitcoin", 
                "symbol": "goBTC", 
                "balance": float(gobtc_balance), 
                "value_usd": float(gobtc_value), 
                "price_usd": float(btc_price)
            },
            {
                "name": "Wrapped Ethereum", 
                "symbol": "goETH", 
                "balance": float(goeth_balance), 
                "value_usd": float(goeth_value), 
                "price_usd": float(eth_price)
            },
        ]
        
        # Filter out assets with zero balance
        non_zero_assets = [asset for asset in assets if asset['balance'] > 0]

        return {
            "total_balance_usd": float(total_value),
            "assets": non_zero_assets,
            "change_24h": 0.0,  # TODO: Implement 24h tracking
            "total_pnl": 0.0,
            "wallet_exists": True,
            "wallet_address": wallet_address
        }
        
    except Exception as e:
        logger.error(f"Error fetching marketData summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching marketData data")