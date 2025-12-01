# File: backend/services/prediction_market_service.py

import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
from web3 import Web3

logger = logging.getLogger(__name__)

class PredictionMarketService:
    """
    🎯 Seamount Prediction Markets - Camp Network Integration
    Powered by Camp Network Basecamp Testnet
    """
    
    def __init__(self, db_service, web3_provider: str, contract_address: str, contract_abi: List):
        self.db = db_service
        self.w3 = Web3(Web3.HTTPProvider(web3_provider))
        self.contract = self.w3.eth.contract(address=contract_address, abi=contract_abi)
        
        logger.info("✅ Prediction Market Service initialized on Camp Network")
    
    async def get_active_markets(self) -> List[Dict]:
        """
        📊 GET ACTIVE PREDICTION MARKETS
        Returns markets that are still open for betting
        """
        try:
            # Query from Supabase
            query = """
                SELECT * FROM public.prediction_markets 
                WHERE end_time > NOW() 
                AND resolved = FALSE 
                ORDER BY trending_score DESC, total_volume DESC
            """
            
            markets = await self.db.execute_query(query)
            
            # Enrich with live blockchain data from Camp Network
            for market in markets:
                market_id = market['contract_market_id']
                
                # Get live odds from Camp Network contract
                yes_odds, no_odds = self.contract.functions.getMarketOdds(market_id).call()
                
                market['yes_odds'] = yes_odds / 100  # Convert from basis points
                market['no_odds'] = no_odds / 100
                market['yes_probability'] = yes_odds / 10000 * 100
                market['no_probability'] = no_odds / 10000 * 100
            
            return markets
            
        except Exception as e:
            logger.error(f"Failed to get active markets: {e}")
            return []
    
    async def place_bet(
        self, 
        user_id: str, 
        market_id: int, 
        prediction: bool,  # True = YES, False = NO
        amount: Decimal,
        user_wallet_address: str,
        user_private_key: str
    ) -> Dict:
        """
        💰 PLACE BET ON PREDICTION MARKET
        
        Flow:
        1. Validate market is open
        2. Approve USDC spend (Camp Testnet USDC: 0x977fdEF62CE095Ae8750Fd3496730F24F60dea7a)
        3. Call contract.placeBet()
        4. Record in Supabase
        5. Return transaction receipt
        """
        try:
            # 1️⃣ Validate market
            market = await self.db.execute_query(
                "SELECT * FROM public.prediction_markets WHERE id = %s",
                (market_id,)
            )
            
            if not market:
                raise Exception("Market not found")
            
            if market[0]['end_time'] < datetime.utcnow():
                raise Exception("Market has closed")
            
            # 2️⃣ Approve USDC spend (Camp Testnet USDC)
            usdc_contract = self.w3.eth.contract(
                address="0x977fdEF62CE095Ae8750Fd3496730F24F60dea7a",  # Camp Testnet USDC
                abi=self.get_erc20_abi()
            )
            
            # Check allowance
            allowance = usdc_contract.functions.allowance(
                user_wallet_address,
                self.contract.address
            ).call()
            
            amount_wei = self.w3.to_wei(amount, 'mwei')  # USDC has 6 decimals
            
            if allowance < amount_wei:
                # Approve USDC
                approve_tx = usdc_contract.functions.approve(
                    self.contract.address,
                    amount_wei * 2  # Approve 2x for future bets
                ).build_transaction({
                    'from': user_wallet_address,
                    'nonce': self.w3.eth.get_transaction_count(user_wallet_address),
                    'gas': 100000,
                    'gasPrice': self.w3.eth.gas_price
                })
                
                signed_approve = self.w3.eth.account.sign_transaction(approve_tx, user_private_key)
                approve_hash = self.w3.eth.send_raw_transaction(signed_approve.rawTransaction)
                
                logger.info(f"USDC approved: {approve_hash.hex()}")
            
            # 3️⃣ Place bet on Camp Network contract
            contract_market_id = market[0]['contract_market_id']
            
            bet_tx = self.contract.functions.placeBet(
                contract_market_id,
                prediction,
                amount_wei
            ).build_transaction({
                'from': user_wallet_address,
                'nonce': self.w3.eth.get_transaction_count(user_wallet_address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_bet = self.w3.eth.account.sign_transaction(bet_tx, user_private_key)
            bet_hash = self.w3.eth.send_raw_transaction(signed_bet.rawTransaction)
            
            # Wait for confirmation on Camp Network
            receipt = self.w3.eth.wait_for_transaction_receipt(bet_hash)
            
            # 4️⃣ Record in Supabase
            await self.db.execute_query("""
                INSERT INTO public.prediction_bets 
                (user_id, market_id, prediction, amount, tx_hash, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (user_id, market_id, prediction, float(amount), receipt['transactionHash'].hex()))
            
            # Update market volume in Supabase
            await self.db.execute_query("""
                UPDATE public.prediction_markets 
                SET total_volume = total_volume + %s,
                    total_yes_bets = CASE WHEN %s THEN total_yes_bets + %s ELSE total_yes_bets END,
                    total_no_bets = CASE WHEN NOT %s THEN total_no_bets + %s ELSE total_no_bets END
                WHERE id = %s
            """, (float(amount), prediction, float(amount), prediction, float(amount), market_id))
            
            logger.info(f"✅ Bet placed: {amount} USDC on market {market_id}")
            
            return {
                'success': True,
                'tx_hash': receipt['transactionHash'].hex(),
                'bet_id': market_id,
                'prediction': 'YES' if prediction else 'NO',
                'amount': float(amount),
                'explorer_url': f"https://camp.cloud.blockscout.com/tx/{receipt['transactionHash'].hex()}"
            }
            
        except Exception as e:
            logger.error(f"Bet placement failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_user_bets(self, user_id: str) -> List[Dict]:
        """
        📜 GET USER'S BET HISTORY
        Includes P&L calculations
        """
        query = """
            SELECT 
                pb.*, 
                pm.question, 
                pm.end_time, 
                pm.resolved, 
                pm.outcome,
                pm.total_yes_bets,
                pm.total_no_bets
            FROM public.prediction_bets pb
            JOIN public.prediction_markets pm ON pb.market_id = pm.id
            WHERE pb.user_id = %s
            ORDER BY pb.created_at DESC
        """
        
        bets = await self.db.execute_query(query, (user_id,))
        
        # Calculate P&L for each bet
        for bet in bets:
            if bet['resolved']:
                bet['won'] = (bet['prediction'] == bet['outcome'])
                
                if bet['won']:
                    # Parimutuel payout calculation
                    total_pool = bet['total_yes_bets'] + bet['total_no_bets']
                    winning_pool = bet['total_yes_bets'] if bet['outcome'] else bet['total_no_bets']
                    
                    bet['payout'] = (bet['amount'] * total_pool) / winning_pool if winning_pool > 0 else 0
                else:
                    bet['payout'] = 0
            else:
                bet['status'] = 'pending'
        
        return bets
    
    def get_erc20_abi(self) -> List:
        """Standard ERC-20 ABI for USDC interactions"""
        return [
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [
                    {"name": "_owner", "type": "address"},
                    {"name": "_spender", "type": "address"}
                ],
                "name": "allowance",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]