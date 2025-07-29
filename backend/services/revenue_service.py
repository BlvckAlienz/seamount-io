// Location: /backend/services/revenue_service.py

import asyncio
import logging
import functools
from typing import List, Dict, Optional
from decimal import Decimal
from supabase import create_client, Client
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Add retry decorator
def retry(max_attempts=3, backoff_factor=2):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        # Last attempt failed, re-raise the exception
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise
                    # Calculate backoff time
                    backoff_time = backoff_factor ** attempt
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {backoff_time}s: {e}")
                    await asyncio.sleep(backoff_time)
        return wrapper
    return decorator

class TradingSignal:
    def __init__(self, symbol: str, action: str, entry_price: float, stop_loss: float, 
                 take_profit: float, confidence: float, timeframe: str, setup_type: str, 
                 risk_profile: str, quantity: float, timestamp: float, user_id: str):
        self.symbol = symbol
        self.action = action
        self.entry_price = float(entry_price)
        self.stop_loss = float(stop_loss)
        self.take_profit = float(take_profit)
        self.confidence = confidence
        self.timeframe = timeframe
        self.setup_type = setup_type
        self.risk_profile = risk_profile
        self.quantity = float(quantity)
        self.timestamp = timestamp
        self.user_id = user_id

class SeamountTradingAgent:
    def __init__(self):
        self.supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        self.logger = logger
        self.max_retries = 3
        # Initialize database connection early
        self._init_database()
        
    def _init_database(self):
        """Initialize database connection with error handling"""
        try:
            if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
                self.logger.warning("Supabase credentials missing, using demo mode")
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")

    @retry(max_attempts=3, backoff_factor=2)
    async def generate_trading_signals(self) -> List[TradingSignal]:
        market_data = await self.fetch_market_data()
        signals = []
        
        user_response = await self.supabase.table("users").select("id").execute()
        user_ids = [row["id"] for row in user_response.data]
        
        for user_id in user_ids:
            for symbol, data in market_data.items():
                signal = self._generate_signal(symbol, data, user_id)
                if signal:
                    signals.append(signal)
        
        self.logger.info(f"Generated {len(signals)} trading signals")
        return signals

    def _generate_signal(self, symbol: str, data: Dict, user_id: str) -> Optional[TradingSignal]:
        try:
            price = data["price"]
            ma_24h = data["ma_24h"]
            timestamp = datetime.utcnow().timestamp()
            
            if price > ma_24h:
                return TradingSignal(
                    symbol=symbol,
                    action="BUY",
                    entry_price=price,
                    stop_loss=price * 0.98,
                    take_profit=price * 1.05,
                    confidence=0.7,
                    timeframe="1h",
                    setup_type="momentum",
                    risk_profile="medium",
                    quantity=1000.0,
                    timestamp=timestamp,
                    user_id=user_id
                )
            elif price < ma_24h:
                return TradingSignal(
                    symbol=symbol,
                    action="SELL",
                    entry_price=price,
                    stop_loss=price * 1.02,
                    take_profit=price * 0.95,
                    confidence=0.7,
                    timeframe="1h",
                    setup_type="momentum",
                    risk_profile="medium",
                    quantity=1000.0,
                    timestamp=timestamp,
                    user_id=user_id
                )
            return None
        except Exception as e:
            self.logger.error(f"Signal generation failed for {symbol}: {e}")
            return None

    async def fetch_market_data(self) -> Dict:
        try:
            response = await self.supabase.table("market_data").select("*").execute()
            if response.data:
                return {row["symbol"]: row for row in response.data}
            else:
                return {
                    "ALGO-USDS": {"price": 0.15, "ma_24h": 0.14, "volume": 100000},
                    "USDT-USDS": {"price": 1.0, "ma_24h": 1.01, "volume": 50000}
                }
        except Exception as e:
            self.logger.error(f"Market data fetch failed: {e}")
            raise

class SeamountPaymentAgent:
    def __init__(self):
        self.supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        self.logger = logger
        self.max_retries = 3
        self._init_database()

    def _init_database(self):
        """Initialize database connection with error handling"""
        try:
            if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
                self.logger.warning("Supabase credentials missing, using demo mode")
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")

    @retry(max_attempts=3, backoff_factor=2)
    async def optimize_route(self, sender_address: str, receiver_address: str, amount: float) -> Dict:
        if not await self.check_aml(sender_address) or not await self.check_aml(receiver_address):
            raise ValueError("AML compliance check failed")
        
        route = {
            "route": [sender_address, receiver_address],
            "estimated_fee": amount * Decimal("0.001"),
            "estimated_time": 10,
            "compliance_status": "approved"
        }
        
        self.logger.info(f"Optimized payment route for {amount} USDS")
        return route

    async def check_aml(self, address: str) -> bool:
        try:
            response = await self.supabase.table("sanctions_list").select("address").eq("address", address).execute()
            is_clean = len(response.data) == 0
            self.logger.info(f"AML check for {address}: {'PASSED' if is_clean else 'FAILED'}")
            return is_clean
        except Exception as e:
            self.logger.error(f"AML check failed for {address}: {e}")
            return False

class RevenueTracker:
    def __init__(self):
        self.supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        self.logger = logger
        self.max_retries = 3
        self._init_database()

    def _init_database(self):
        """Initialize database connection with error handling"""
        try:
            if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
                self.logger.warning("Supabase credentials missing, using demo mode")
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")

    @retry(max_attempts=3, backoff_factor=2)
    async def record_fee(self, fee_type: str, amount: Decimal, transaction_id: str) -> bool:
        await self.supabase.table("revenue").insert({
            "revenue_type": fee_type,
            "amount": float(amount),
            "currency": "USDS",
            "transaction_id": transaction_id,
            "timestamp": datetime.utcnow().isoformat(),
            "month": datetime.utcnow().month,
            "year": datetime.utcnow().year
        }).execute()
        
        self.logger.info(f"Recorded {fee_type} fee: {amount} USDS")
        await self.update_daily_revenue(datetime.utcnow().date().isoformat(), fee_type, amount)
        return True

    async def update_daily_revenue(self, date: str, fee_type: str, amount: Decimal) -> None:
        try:
            response = await self.supabase.table("daily_revenue").select("*").eq("date", date).execute()
            
            if response.data:
                existing = response.data[0]
                update_data = {
                    f"{fee_type}_fees": float(existing.get(f"{fee_type}_fees", 0) + amount),
                    "total": float(existing.get("total", 0) + amount)
                }
                await self.supabase.table("daily_revenue").update(update_data).eq("date", date).execute()
            else:
                await self.supabase.table("daily_revenue").insert({
                    "date": date,
                    f"{fee_type}_fees": float(amount),
                    "total": float(amount),
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
                
            self.logger.info(f"Updated daily revenue for {date}")
            
        except Exception as e:
            self.logger.error(f"Daily revenue update failed: {e}")
            raise

    async def get_monthly_target(self, month: int, year: int) -> Optional[Decimal]:
        try:
            response = await self.supabase.table("monthly_targets").select("target_amount").eq("month", month).eq("year", year).execute()
            if response.data:
                return Decimal(str(response.data[0]["target_amount"]))
            return None
        except Exception as e:
            self.logger.error(f"Monthly target fetch failed: {e}")
            return None
