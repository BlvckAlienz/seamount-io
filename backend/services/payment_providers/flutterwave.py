# /backend/services/payment_providers/flutterwave.py

import asyncio
import requests
import hashlib
import hmac
from decimal import Decimal
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class FlutterwaveProcessor:
    """Live Flutterwave payment integration"""
    
    def __init__(self):
        self.public_key = os.getenv('FLW_PUBLIC_KEY')
        self.secret_key = os.getenv('FLW_SECRET_KEY')
        self.base_url = "https://api.flutterwave.com/v3"  # LIVE endpoint
        self.encryption_key = os.getenv('FLW_ENCRYPTION_KEY')

    # PRODUCTION SAFETY CHECKS
        self._validate_production_config()
    
    def _validate_production_config(self):
        """Validate production configuration"""
        if not all([self.public_key, self.secret_key, self.encryption_key]):
            raise ValueError("Missing Flutterwave API keys in environment")
        
        if self.secret_key.startswith('FLWSECK_TEST'):
            raise ValueError("Still using TEST secret key in production!")
            
        if self.public_key.startswith('FLWPUBK_TEST'):
            raise ValueError("Still using TEST public key in production!")
        
        logger.info("✅ Production Flutterwave config validated")
    
    async def initialize_payment(self, amount: int, currency: str, email: str, phone: str = None) -> dict:
        """Initialize Flutterwave payment"""
        try:
            url = f"{self.base_url}/payments"
            
            payload = {
                "tx_ref": f"SEAMOUNT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "amount": amount,
                "currency": currency,
                "redirect_url": "https://seamount.io/payment/callback",
                "payment_options": "card,mobilemoney,ussd,banktransfer",
                "customer": {
                    "email": email,
                    "phonenumber": phone or "",
                    "name": "Seamount User"
                },
                "customizations": {
                    "title": "USDS Purchase",
                    "description": "Buy USDS Stablecoin",
                    "logo": "https://seamount.io/logo.png"
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            result = response.json()
            
            if result.get('status') == 'success':
                logger.info(f"Payment initialized: {result['data']['link']}")
                return {
                    'status': 'success',
                    'payment_link': result['data']['link'],
                    'tx_ref': payload['tx_ref']
                }
            else:
                logger.error(f"Payment init failed: {result}")
                return {'status': 'error', 'message': result.get('message', 'Unknown error')}
                
        except Exception as e:
            logger.error(f"Flutterwave payment failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def verify_payment(self, tx_ref: str) -> dict:
        """Verify payment completion"""
        try:
            url = f"{self.base_url}/transactions/verify_by_reference?tx_ref={tx_ref}"
            headers = {"Authorization": f"Bearer {self.secret_key}"}
            
            response = requests.get(url, headers=headers)
            result = response.json()
            
            if result.get('status') == 'success' and result['data']['status'] == 'successful':
                return {
                    'verified': True,
                    'amount': result['data']['amount'],
                    'currency': result['data']['currency'],
                    'customer_email': result['data']['customer']['email']
                }
            else:
                return {'verified': False}
                
        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            return {'verified': False}

# /seamount/blockchain/algorand_mainnet.py
from algosdk.v2client import algod
from algosdk import account, mnemonic, transaction
from algosdk.atomic_transaction_composer import AtomicTransactionComposer, TransactionWithSigner
import base64
from decimal import Decimal

class AlgorandMainnet:
    """Live Algorand mainnet integration"""
    
    def __init__(self):
        # MainNet connection
        self.algod_client = algod.AlgodClient(
            algod_token="",
            algod_address="https://mainnet-api.algonode.cloud",
            headers={"User-Agent": "seamount-io"}
        )
        
        self.usds_asset_id = None  # Will be created
        self.treasury_sk = os.getenv('ALGORAND_TREASURY_SK')
        self.treasury_address = account.address_from_private_key(self.treasury_sk)
    
    async def create_usds_asset(self) -> int:
        """Create USDS asset on Algorand mainnet"""
        try:
            params = self.algod_client.suggested_params()
            
            txn = transaction.AssetConfigTxn(
                sender=self.treasury_address,
                sp=params,
                total=1000000000000000,  # 1 billion USDS with 6 decimals
                default_frozen=False,
                unit_name="USDS",
                asset_name="Seamount USD Stablecoin",
                manager=self.treasury_address,
                reserve=self.treasury_address,
                freeze=self.treasury_address,
                clawback=self.treasury_address,
                url="https://seamount.io/usds",
                decimals=6
            )
            
            signed_txn = txn.sign(self.treasury_sk)
            txid = self.algod_client.send_transaction(signed_txn)
            
            # Wait for confirmation
            confirmed_txn = transaction.wait_for_confirmation(self.algod_client, txid, 4)
            asset_id = confirmed_txn["asset-index"]
            
            self.usds_asset_id = asset_id
            logger.info(f"USDS created on mainnet: Asset ID {asset_id}")
            
            return asset_id
            
        except Exception as e:
            logger.error(f"USDS creation failed: {e}")
            raise
    
    async def mint_usds(self, recipient_address: str, amount: Decimal) -> str:
        """Mint USDS tokens to recipient"""
        try:
            params = self.algod_client.suggested_params()
            
            # Convert to micro-USDS (6 decimals)
            micro_amount = int(amount * 1000000)
            
            txn = transaction.AssetTransferTxn(
                sender=self.treasury_address,
                sp=params,
                receiver=recipient_address,
                amt=micro_amount,
                index=self.usds_asset_id
            )
            
            signed_txn = txn.sign(self.treasury_sk)
            txid = self.algod_client.send_transaction(signed_txn)
            
            # Wait for confirmation
            transaction.wait_for_confirmation(self.algod_client, txid, 4)
            
            logger.info(f"Minted {amount} USDS to {recipient_address}")
            return txid
            
        except Exception as e:
            logger.error(f"USDS minting failed: {e}")
            raise

# /seamount/trading/free_trading_engine.py
import yfinance as yf
import requests
from decimal import Decimal
import numpy as np
from datetime import datetime, timedelta
import asyncio

class FreeTradingEngine:
    """Free trading engine using public APIs"""
    
    def __init__(self):
        # Free APIs - no subscription needed
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_KEY')  # Free tier: 5 calls/min
        self.polygon_key = os.getenv('POLYGON_KEY')  # Free tier available
        
        self.trading_balance = Decimal('0')
        self.positions = {}
    
    async def get_market_data(self, symbols: list) -> dict:
        """Get real-time market data from free sources"""
        try:
            data = {}
            
            # CoinGecko for crypto (free, no API key needed)
            crypto_map = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'ADA': 'cardano',
                'DOT': 'polkadot'
            }
            
            for symbol in symbols:
                if symbol in crypto_map:
                    url = f"{self.coingecko_base}/simple/price"
                    params = {
                        'ids': crypto_map[symbol],
                        'vs_currencies': 'usd',
                        'include_24hr_change': 'true'
                    }
                    
                    response = requests.get(url, params=params)
                    if response.status_code == 200:
                        result = response.json()
                        coin_data = result[crypto_map[symbol]]
                        
                        data[symbol] = {
                            'price': Decimal(str(coin_data['usd'])),
                            'change_24h': coin_data.get('usd_24h_change', 0),
                            'timestamp': datetime.utcnow()
                        }
                
                # Yahoo Finance for stocks (free)
                else:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    hist = ticker.history(period="2d")
                    
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                        change_pct = ((current_price - prev_price) / prev_price) * 100
                        
                        data[symbol] = {
                            'price': Decimal(str(current_price)),
                            'change_24h': change_pct,
                            'timestamp': datetime.utcnow()
                        }
            
            return data
            
        except Exception as e:
            logger.error(f"Market data fetch failed: {e}")
            return {}
    
    async def generate_ai_signals(self, market_data: dict) -> list:
        """Generate trading signals using simple AI logic"""
        signals = []
        
        try:
            for symbol, data in market_data.items():
                price = data['price']
                change = data['change_24h']
                
                # Simple momentum + mean reversion strategy
                signal_strength = 0
                action = 'HOLD'
                
                # Momentum signals
                if change > 5:  # Strong upward momentum
                    signal_strength += 0.3
                elif change < -5:  # Strong downward momentum - potential reversal
                    signal_strength += 0.4
                    action = 'BUY'
                
                # Volume-price analysis (simplified)
                # In production, you'd use more sophisticated indicators
                if -2 < change < 2:  # Consolidation - prepare for breakout
                    signal_strength += 0.2
                
                # Risk management
                if signal_strength > 0.5:
                    action = 'BUY' if change < 0 else 'SELL'
                    confidence = min(signal_strength, 0.8)  # Cap at 80%
                    
                    signals.append({
                        'symbol': symbol,
                        'action': action,
                        'confidence': confidence,
                        'entry_price': price,
                        'timestamp': datetime.utcnow()
                    })
            
            return signals
            
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            return []
    
    async def simulate_trade_execution(self, signals: list, available_balance: Decimal) -> Decimal:
        """Simulate trade execution for profit calculation"""
        total_profit = Decimal('0')
        
        try:
            for signal in signals:
                if signal['confidence'] > 0.6:
                    # Position sizing (max 10% per trade)
                    position_size = available_balance * Decimal('0.1')
                    
                    # Simulate holding period (in production, use real execution)
                    await asyncio.sleep(1)  # Simulate market movement
                    
                    # Mock profit calculation (replace with real execution)
                    profit_pct = signal['confidence'] * 0.05  # Max 4% profit per trade
                    trade_profit = position_size * Decimal(str(profit_pct))
                    
                    total_profit += trade_profit
                    
                    logger.info(f"Simulated trade: {signal['symbol']} - Profit: {trade_profit}")
            
            return total_profit
            
        except Exception as e:
            logger.error(f"Trade simulation failed: {e}")
            return Decimal('0')

# /seamount/core/revenue_engine.py  
import asyncio
from decimal import Decimal
from datetime import datetime
import logging
import sqlite3
import os

logger = logging.getLogger(__name__)

class RevenueEngine:
    """Production revenue collection and tracking"""
    
    def __init__(self):
        self.db_path = "/seamount/data/revenue.db"
        self.daily_revenue = Decimal('0')
        self.total_revenue = Decimal('0')
        self._init_database()
    
    def _init_database(self):
        """Initialize revenue tracking database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS revenue_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                fee_type TEXT NOT NULL,
                transaction_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'collected'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                date DATE PRIMARY KEY,
                total_revenue REAL,
                transaction_count INTEGER,
                avg_fee REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def collect_payment_fee(self, payment_amount: Decimal, currency: str) -> Decimal:
        """Collect fee from payment processing"""
        try:
            # Fee structure
            fee_rates = {
                'USD': Decimal('0.035'),   # 3.5% for USD
                'NGN': Decimal('0.025'),   # 2.5% for NGN  
                'KES': Decimal('0.030'),   # 3.0% for KES
                'GHS': Decimal('0.030'),   # 3.0% for GHS
            }
            
            fee_rate = fee_rates.get(currency, Decimal('0.035'))
            fee_amount = payment_amount * fee_rate
            
            # Log revenue
            await self._log_revenue(fee_amount, 'payment_processing', f"payment_{currency}")
            
            logger.info(f"Payment fee collected: {fee_amount} from {payment_amount} {currency}")
            return fee_amount
            
        except Exception as e:
            logger.error(f"Payment fee collection failed: {e}")
            return Decimal('0')
    
    async def collect_trading_fee(self, profit_amount: Decimal) -> Decimal:
        """Collect performance fee from trading profits"""
        try:
            performance_fee_rate = Decimal('0.20')  # 20% of profits
            fee_amount = profit_amount * performance_fee_rate
            
            await self._log_revenue(fee_amount, 'trading_performance', 'ai_trading')
            
            logger.info(f"Trading fee collected: {fee_amount} from {profit_amount} profit")
            return fee_amount
            
        except Exception as e:
            logger.error(f"Trading fee collection failed: {e}")
            return Decimal('0')
    
    async def collect_cross_border_fee(self, transfer_amount: Decimal) -> Decimal:
        """Collect fee from cross-border transfers"""
        try:
            # Competitive cross-border fee: 0.75%
            fee_rate = Decimal('0.0075')
            fee_amount = transfer_amount * fee_rate
            
            await self._log_revenue(fee_amount, 'cross_border', 'usds_transfer')
            
            logger.info(f"Cross-border fee collected: {fee_amount}")
            return fee_amount
            
        except Exception as e:
            logger.error(f"Cross-border fee collection failed: {e}")
            return Decimal('0')
    
    async def _log_revenue(self, amount: Decimal, fee_type: str, transaction_id: str):
        """Log revenue to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO revenue_log (amount, fee_type, transaction_id) VALUES (?, ?, ?)",
                (float(amount), fee_type, transaction_id)
            )
            
            conn.commit()
            conn.close()
            
            # Update daily totals
            self.daily_revenue += amount
            self.total_revenue += amount
            
        except Exception as e:
            logger.error(f"Revenue logging failed: {e}")
    
    async def get_revenue_summary(self) -> dict:
        """Get revenue summary for dashboard"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Today's revenue
            cursor.execute(
                "SELECT SUM(amount), COUNT(*) FROM revenue_log WHERE DATE(timestamp) = DATE('now')"
            )
            today_result = cursor.fetchone()
            today_revenue = today_result[0] or 0
            today_count = today_result[1] or 0
            
            # Total revenue
            cursor.execute("SELECT SUM(amount), COUNT(*) FROM revenue_log")
            total_result = cursor.fetchone()
            total_revenue = total_result[0] or 0
            total_count = total_result[1] or 0
            
            conn.close()
            
            return {
                'today_revenue': Decimal(str(today_revenue)),
                'today_transactions': today_count,
                'total_revenue': Decimal(str(total_revenue)),
                'total_transactions': total_count,
                'avg_fee': Decimal(str(total_revenue / total_count)) if total_count > 0 else Decimal('0')
            }
            
        except Exception as e:
            logger.error(f"Revenue summary failed: {e}")
            return {
                'today_revenue': Decimal('0'),
                'today_transactions': 0,
                'total_revenue': Decimal('0'),
                'total_transactions': 0,
                'avg_fee': Decimal('0')
            }
