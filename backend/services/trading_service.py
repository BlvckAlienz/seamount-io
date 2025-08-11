import logging
from typing import List, Dict, Any
from supabase import Client
from datetime import datetime
from fastapi import HTTPException

# --- Core Dependencies ---
from config import Settings
from .database_service import DatabaseService
from .algorand_service import AlgorandService
from .swap_service import SwapService

logger = logging.getLogger(__name__)

# --- AI AGENT LOGIC (INTEGRATED) ---
class SeamountTradingAgent:
    def __init__(self, settings: Settings, db_service: DatabaseService):
        self.settings = settings
        self.db_service = db_service

    async def process_user_signals(self, user_profile: Dict) -> List[Dict]:
        mock_signal = {
            "symbol": "ALGO-USD", "action": "BUY", "confidence": 0.75,
            "entry_price": 0.18, "quantity": 1000,
            "signal_id": f"sig_{int(datetime.utcnow().timestamp())}"
        }
        return [mock_signal]

# --- MAIN TRADING SERVICE ---
class TradingService:
    def __init__(self, settings: Settings, supabase_client: Client, db_service: DatabaseService, algorand_service: AlgorandService, swap_service: SwapService):
        self.settings = settings
        self.supabase = supabase_client
        self.db_service = db_service
        self.algorand_service = algorand_service
        self.swap_service = swap_service
        self.ai_agent = SeamountTradingAgent(settings, db_service)
        logger.info("TradingService initialized successfully.")

    async def generate_signals_for_user(self, user_id: str) -> List[Dict]:
        try:
            user_profile = await self.db_service.get_user_profile_by_id(user_id)
            if not user_profile:
                raise ValueError("User not found")
            signals = await self.ai_agent.process_user_signals(user_profile)
            return signals
        except Exception as e:
            logger.error(f"Failed to generate signals for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Could not generate trading signals.")

    async def execute_trade(self, user_id: str, signal: Dict) -> Dict[str, Any]:
        try:
            logger.info(f"Executing trade for user {user_id} based on signal: {signal.get('symbol')} {signal.get('action')}")
            
            # This is where you would call the swap_service for a real trade
            # For now, we simulate and log
            
            mock_result = {
                "success": True,
                "tx_id": f"trade_tx_{user_id[:4]}_{int(datetime.utcnow().timestamp())}",
                "executed_price": signal.get('entry_price', 0) * 1.001,
                "filled_quantity": signal.get('quantity', 0)
            }

            trade_log = {
                "user_id": user_id, "signal_id": signal.get("signal_id"),
                "symbol": signal.get("symbol"), "action": signal.get("action"),
                "amount": mock_result["filled_quantity"], "price": mock_result["executed_price"],
                "status": "completed_simulated", "tx_hash": mock_result["tx_id"]
            }
            await self.db_service.log_event("trades", trade_log)

            return mock_result
        except Exception as e:
            logger.error(f"Failed to execute trade for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Trade execution failed.")