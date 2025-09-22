from fastapi import APIRouter, Depends, HTTPException
from backend.dependencies import get_current_user, get_db_service, get_algorand_service, get_oracle_service
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/summary")
async def get_portfolio_summary(
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    algo_service = Depends(get_algorand_service),
    oracle_service = Depends(get_oracle_service)
):
    try:
        user_id = current_user['id']
        logger.info(f"Fetching REAL portfolio summary for user: {user_id}")

        # 1. Get user's wallet address and balances from DB
        wallet_data = await db_service.get_user_wallet(user_id)
        if not wallet_data:
            raise HTTPException(status_code=404, detail="Wallet not found for user")
        
        wallet_address = wallet_data['wallet_address']
        algo_balance = Decimal(str(wallet_data['algo_balance'] or 0))
        usdt_balance = Decimal(str(wallet_data['usdt_balance'] or 0))
        usdc_balance = Decimal(str(wallet_data['usdc_balance'] or 0))
        gobtc_balance = Decimal(str(wallet_data['gobtc_balance'] or 0))
        goeth_balance = Decimal(str(wallet_data['goeth_balance'] or 0))

        # 2. Get current prices from Oracle
        algo_price, _ = await oracle_service.get_asset_price('algorand') # Requires adding 'algorand' to oracle
        btc_price, _ = await oracle_service.get_asset_price('bitcoin')
        eth_price, _ = await oracle_service.get_asset_price('ethereum')
        # Stablecoins are ~$1
        usdt_price = Decimal('1.0')
        usdc_price = Decimal('1.0')

        # 3. Calculate the value of each holding
        algo_value = algo_balance * algo_price
        usdt_value = usdt_balance * usdt_price
        usdc_value = usdc_balance * usdc_price
        gobtc_value = gobtc_balance * btc_price # goBTC is 1:1 with BTC
        goeth_value = goeth_balance * eth_price # goETH is 1:1 with ETH

        total_value = algo_value + usdt_value + usdc_value + gobtc_value + goeth_value

        # 4. Structure the response
        assets = [
            {"name": "Algorand", "symbol": "ALGO", "balance": float(algo_balance), "value_usd": float(algo_value), "price_usd": float(algo_price)},
            {"name": "Tether USD", "symbol": "USDT", "balance": float(usdt_balance), "value_usd": float(usdt_value), "price_usd": 1.0},
            {"name": "USD Coin", "symbol": "USDCa", "balance": float(usdc_balance), "value_usd": float(usdc_value), "price_usd": 1.0},
            {"name": "Wrapped Bitcoin", "symbol": "goBTC", "balance": float(gobtc_balance), "value_usd": float(gobtc_value), "price_usd": float(btc_price)},
            {"name": "Wrapped Ethereum", "symbol": "goETH", "balance": float(goeth_balance), "value_usd": float(goeth_value), "price_usd": float(eth_price)},
        ]
        # Filter out assets with zero balance for a cleaner response
        non_zero_assets = [asset for asset in assets if asset['balance'] > 0]

        return {
            "total_balance_usd": float(total_value),
            "assets": non_zero_assets,
            # For now, set change to 0. Implement 24h change later.
            "change_24h": 0.0,
            "total_pnl": 0.0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching portfolio summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching portfolio data")