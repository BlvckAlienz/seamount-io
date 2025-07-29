# File Location: backend/services/trading_service.py
# Description: Service for handling AI-powered trading signals and execution.

import logging
from typing import List, Dict, Optional
from supabase import Client
from .ai_agents import SeamountTradingAgent # Assuming ai_agents.py is now in this directory

logger = logging.getLogger(__name__)

class TradingService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        # The AI agent is now a component of the service
        self.ai_agent = SeamountTradingAgent(supabase_client)

    async def generate_signals_for_user(self, user_id: str) -> List[Dict]:
        """Generates a list of trading signals for a specific user."""
        try:
            # Fetch user data (risk profile, etc.)
            user_res = await self.supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
            if not user_res.data:
                raise ValueError("User not found")
            
            user_data = user_res.data
            signals = await self.trading_agent.process_user_signals(user_data)
            return [signal.to_dict() for signal in signals]
        except Exception as e:
            logger.error(f"Failed to generate signals for user {user_id}: {e}")
            raise

    async def execute_trade(self, user_id: str, signal: Dict) -> Dict:
        """Executes a specific trade signal for a user."""
        try:
            logger.info(f"Executing trade for user {user_id} based on signal: {signal['symbol']} {signal['action']}")
            # Here, you would call your swap_service (refactored from tinyman_client.py)
            # result = await self.swap_service.execute_swap(user_id, signal)
            
            # Mocking the result for now
            mock_result = {
                "success": True,
                "tx_id": f"trade_tx_{user_id[:4]}_{int(datetime.utcnow().timestamp())}",
                "executed_price": signal['entry_price'] * 1.001,
                "filled_quantity": signal['quantity']
            }

            # Log the trade to the database
            await self.supabase.table("trades").insert({
                "user_id": user_id,
                "signal_id": signal.get("signal_id"),
                "symbol": signal["symbol"],
                "action": signal["action"],
                "amount": signal["quantity"],
                "price": mock_result["executed_price"],
                "status": "completed",
                "tx_hash": mock_result["tx_id"]
            }).execute()

            return mock_result
        except Exception as e:
            logger.error(f"Failed to execute trade for user {user_id}: {e}")
            raise