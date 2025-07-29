"""
Seamount.io Cross-Border Payment Platform
Continuous Transaction Monitoring System

This module provides continuous monitoring of transactions to detect suspicious patterns
across multiple transactions over time, rather than just at transaction time.
"""

// Location: /backend/services/monitoring_service.py

import asyncio
import logging
import os
import time
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import aioredis
from supabase import create_client, Client
from decimal import Decimal
import numpy as np
import pandas as pd

# Import audit logging
from backend.audit_logging import audit_logger, AuditEventType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PatternType:
    """Types of suspicious patterns to detect"""
    STRUCTURING = "structuring"  # Breaking up transactions to avoid reporting thresholds
    VELOCITY = "velocity"  # Unusual transaction speed/frequency
    CYCLING = "cycling"  # Funds moving in circles between related accounts
    LAYERING = "layering"  # Complex movement of funds to hide origin
    SMURFING = "smurfing"  # Multiple small deposits aggregated and withdrawn
    ROUND_NUMBERS = "round_numbers"  # Suspicious use of round numbers
    UNUSUAL_HOURS = "unusual_hours"  # Transactions at unusual hours
    JURISDICTION_RISK = "jurisdiction_risk"  # High-risk jurisdiction involvement
    NESTED_TRANSFERS = "nested_transfers"  # Complex nesting of transfers

class MonitoringSeverity:
    """Monitoring alert severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ContinuousMonitoringService:
    """
    Continuous monitoring service for detecting suspicious patterns
    across transactions and users.
    """
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase = None
        self.redis = None
        
        # Monitoring thresholds
        self.thresholds = {
            PatternType.STRUCTURING: {
                "time_window": 24 * 60 * 60,  # 24 hours in seconds
                "amount_threshold": 10000,  # $10,000
                "min_transactions": 3,
                "severity": MonitoringSeverity.HIGH
            },
            PatternType.VELOCITY: {
                "time_window": 60 * 60,  # 1 hour in seconds
                "transaction_count": 10,
                "severity": MonitoringSeverity.MEDIUM
            },
            PatternType.CYCLING: {
                "time_window": 7 * 24 * 60 * 60,  # 7 days in seconds
                "min_cycle_length": 3,  # Minimum 3 transfers to consider a cycle
                "severity": MonitoringSeverity.HIGH
            },
            PatternType.ROUND_NUMBERS: {
                "min_occurrences": 3,
                "time_window": 24 * 60 * 60,  # 24 hours in seconds
                "severity": MonitoringSeverity.LOW
            },
            PatternType.UNUSUAL_HOURS: {
                "start_hour": 22,  # 10 PM
                "end_hour": 5,     # 5 AM
                "min_transactions": 2,
                "severity": MonitoringSeverity.LOW
            }
        }
        
        # Known high-risk patterns
        self.high_risk_patterns = [
            # Pattern: Multiple small deposits followed by large withdrawal
            {
                "name": "Multiple Deposits Pattern",
                "conditions": [
                    {"stage": "deposit", "min_count": 5, "max_amount": 1000, "time_window": 48},
                    {"stage": "withdrawal", "min_amount": 4000, "time_window": 24}
                ],
                "severity": MonitoringSeverity.HIGH
            },
            # Pattern: Rapid transfers between multiple accounts
            {
                "name": "Rapid Transfer Chain",
                "conditions": [
                    {"unique_recipients": 3, "time_window": 24, "min_amount": 1000}
                ],
                "severity": MonitoringSeverity.MEDIUM
            }
        ]
        
        # Initialize DB connections and caches
        self._initialize_db()
        self.alert_cache = set()  # Avoid duplicate alerts
        
        # Start background tasks
        self.monitoring_task = None
        self.running = False
    
    def _initialize_db(self):
        """Initialize database connections"""
        try:
            if self.supabase_url and self.supabase_key:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                logger.info("Continuous Monitoring: Supabase connected")
            else:
                logger.warning("Continuous Monitoring: No Supabase credentials")
        except Exception as e:
            logger.error(f"Continuous Monitoring DB initialization failed: {e}")
    
    async def initialize_redis(self):
        """Initialize Redis connection"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis = await aioredis.from_url(redis_url)
            logger.info("Continuous Monitoring: Redis connected")
        except Exception as e:
            logger.error(f"Continuous Monitoring Redis connection failed: {e}")
            self.redis = None
    
    async def start(self):
        """Start the continuous monitoring service"""
        if self.running:
            logger.warning("Continuous monitoring already running")
            return
            
        self.running = True
        await self.initialize_redis()
        
        # Start the monitoring loop
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Continuous monitoring service started")
    
    async def stop(self):
        """Stop the continuous monitoring service"""
        self.running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        
        logger.info("Continuous monitoring service stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop that runs periodically"""
        while self.running:
            try:
                # Run all monitoring checks
                await self.check_structuring()
                await self.check_velocity()
                await self.check_cycling()
                await self.check_round_numbers()
                await self.check_unusual_hours()
                await self.check_complex_patterns()
                
                # Sleep for a period before checking again
                # 5 minutes for regular checks
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                # On error, sleep for a minute before retrying
                await asyncio.sleep(60)
    
    async def _get_recent_transactions(self, 
                                      hours: int = 24, 
                                      user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent transactions for monitoring"""
        if not self.supabase:
            return []
            
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Build query
            query = self.supabase.table("payment_transactions").select("*").gte("created_at", cutoff_time.isoformat())
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            # Execute query
            response = await query.execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Failed to get recent transactions: {e}")
            return []
    
    async def check_structuring(self):
        """
        Check for structuring (breaking up transactions to avoid reporting thresholds)
        This is a common money laundering technique.
        """
        try:
            threshold = self.thresholds[PatternType.STRUCTURING]
            time_window = threshold["time_window"]
            amount_threshold = threshold["amount_threshold"]
            min_transactions = threshold["min_transactions"]
            
            # Get transactions in the time window
            transactions = await self._get_recent_transactions(hours=time_window/3600)
            
            if not transactions:
                return
            
            # Group transactions by user
            user_transactions = {}
            for tx in transactions:
                user_id = tx.get("user_id")
                if not user_id:
                    continue
                
                if user_id not in user_transactions:
                    user_transactions[user_id] = []
                user_transactions[user_id].append(tx)
            
            # Check each user for structuring
            for user_id, user_txs in user_transactions.items():
                # Only consider if user has enough transactions
                if len(user_txs) < min_transactions:
                    continue
                
                # Check for transactions just below threshold
                suspicious_txs = [
                    tx for tx in user_txs 
                    if (amount_threshold * 0.7) <= tx.get("amount", 0) < amount_threshold
                ]
                
                if len(suspicious_txs) >= min_transactions:
                    # Calculate total amount of suspicious transactions
                    total_amount = sum(tx.get("amount", 0) for tx in suspicious_txs)
                    
                    # If total exceeds threshold, this could be structuring
                    if total_amount >= amount_threshold:
                        alert_key = f"structuring:{user_id}:{datetime.utcnow().date().isoformat()}"
                        
                        # Avoid duplicate alerts
                        if alert_key in self.alert_cache:
                            continue
                            
                        self.alert_cache.add(alert_key)
                        
                        # Create structuring alert
                        await self._create_alert(
                            pattern_type=PatternType.STRUCTURING,
                            severity=threshold["severity"],
                            user_id=user_id,
                            transactions=[tx.get("id") for tx in suspicious_txs],
                            details={
                                "transaction_count": len(suspicious_txs),
                                "total_amount": total_amount,
                                "threshold": amount_threshold,
                                "time_period_hours": time_window / 3600
                            }
                        )
                        
                        # Log to audit trail
                        await audit_logger.log_event(
                            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                            user_id=user_id,
                            details={
                                "pattern": PatternType.STRUCTURING,
                                "transaction_count": len(suspicious_txs),
                                "total_amount": total_amount
                            },
                            resource_id=alert_key,
                            severity="warning",
                            critical=True
                        )
                        
                        logger.warning(
                            f"Potential structuring detected for user {user_id}: "
                            f"{len(suspicious_txs)} transactions totaling {total_amount}"
                        )
            
        except Exception as e:
            logger.error(f"Structuring check failed: {e}")
    
    async def check_velocity(self):
        """
        Check for unusual transaction velocity
        This could indicate automated systems or fraudulent activity
        """
        try:
            threshold = self.thresholds[PatternType.VELOCITY]
            time_window = threshold["time_window"]
            tx_count_threshold = threshold["transaction_count"]
            
            # Get transactions in the time window (1 hour)
            transactions = await self._get_recent_transactions(hours=time_window/3600)
            
            if not transactions:
                return
            
            # Group transactions by user
            user_transactions = {}
            for tx in transactions:
                user_id = tx.get("user_id")
                if not user_id:
                    continue
                
                if user_id not in user_transactions:
                    user_transactions[user_id] = []
                user_transactions[user_id].append(tx)
            
            # Check each user's transaction velocity
            for user_id, user_txs in user_transactions.items():
                # Only consider if user has enough transactions
                if len(user_txs) >= tx_count_threshold:
                    alert_key = f"velocity:{user_id}:{datetime.utcnow().strftime('%Y%m%d%H')}"
                    
                    # Avoid duplicate alerts
                    if alert_key in self.alert_cache:
                        continue
                        
                    self.alert_cache.add(alert_key)
                    
                    # Create velocity alert
                    await self._create_alert(
                        pattern_type=PatternType.VELOCITY,
                        severity=threshold["severity"],
                        user_id=user_id,
                        transactions=[tx.get("id") for tx in user_txs],
                        details={
                            "transaction_count": len(user_txs),
                            "time_period_hours": time_window / 3600,
                            "threshold": tx_count_threshold
                        }
                    )
                    
                    # Log to audit trail
                    await audit_logger.log_event(
                        event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                        user_id=user_id,
                        details={
                            "pattern": PatternType.VELOCITY,
                            "transaction_count": len(user_txs),
                            "time_window_hours": time_window / 3600
                        },
                        resource_id=alert_key,
                        severity="warning"
                    )
                    
                    logger.warning(
                        f"Unusual transaction velocity for user {user_id}: "
                        f"{len(user_txs)} transactions in {time_window/3600} hours"
                    )
            
        except Exception as e:
            logger.error(f"Velocity check failed: {e}")
    
    async def check_cycling(self):
        """
        Check for funds cycling between accounts
        This could indicate money laundering or wash trading
        """
        try:
            threshold = self.thresholds[PatternType.CYCLING]
            time_window = threshold["time_window"]
            min_cycle_length = threshold["min_cycle_length"]
            
            # Get transactions in the time window (7 days)
            transactions = await self._get_recent_transactions(hours=time_window/3600)
            
            if not transactions:
                return
            
            # Build transaction graph
            graph = {}
            for tx in transactions:
                sender = tx.get("sender_address")
                receiver = tx.get("receiver_address")
                
                if not sender or not receiver:
                    continue
                
                if sender not in graph:
                    graph[sender] = set()
                graph[sender].add(receiver)
            
            # Check for cycles in the graph
            cycles = self._find_cycles(graph, min_cycle_length)
            
            for cycle in cycles:
                # Get all transactions involved in the cycle
                cycle_txs = []
                for i in range(len(cycle)-1):
                    sender = cycle[i]
                    receiver = cycle[i+1]
                    cycle_txs.extend([
                        tx for tx in transactions
                        if tx.get("sender_address") == sender and tx.get("receiver_address") == receiver
                    ])
                
                if not cycle_txs:
                    continue
                
                # Get unique users involved
                user_ids = set()
                for tx in cycle_txs:
                    if tx.get("user_id"):
                        user_ids.add(tx.get("user_id"))
                
                # For each user in the cycle, create an alert
                for user_id in user_ids:
                    alert_key = f"cycling:{user_id}:{'.'.join(cycle)}"
                    
                    # Avoid duplicate alerts
                    if alert_key in self.alert_cache:
                        continue
                        
                    self.alert_cache.add(alert_key)
                    
                    # Create cycling alert
                    await self._create_alert(
                        pattern_type=PatternType.CYCLING,
                        severity=threshold["severity"],
                        user_id=user_id,
                        transactions=[tx.get("id") for tx in cycle_txs],
                        details={
                            "cycle": cycle,
                            "cycle_length": len(cycle),
                            "transaction_count": len(cycle_txs),
                            "time_period_days": time_window / (24 * 3600)
                        }
                    )
                    
                    # Log to audit trail
                    await audit_logger.log_event(
                        event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                        user_id=user_id,
                        details={
                            "pattern": PatternType.CYCLING,
                            "cycle": cycle,
                            "transaction_count": len(cycle_txs)
                        },
                        resource_id=alert_key,
                        severity="warning",
                        critical=True
                    )
                    
                    logger.warning(
                        f"Fund cycling pattern detected for user {user_id}: "
                        f"Cycle: {' -> '.join(cycle)}"
                    )
            
        except Exception as e:
            logger.error(f"Cycling check failed: {e}")
    
    def _find_cycles(self, graph: Dict[str, Set[str]], min_length: int) -> List[List[str]]:
        """
        Find cycles in a transaction graph
        Uses DFS to detect cycles
        """
        cycles = []
        visited = set()
        
        def dfs(node, path, start_node):
            if node in path[1:]:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if len(cycle) >= min_length:
                    cycles.append(cycle)
                return
            
            if node in visited:
                return
                
            visited.add(node)
            
            if node not in graph:
                visited.remove(node)
                return
                
            for neighbor in graph[node]:
                dfs(neighbor, path + [node], start_node)
            
            visited.remove(node)
        
        # Start DFS from each node
        for node in graph:
            dfs(node, [], node)
        
        return cycles
    
    async def check_round_numbers(self):
        """
        Check for suspicious use of round numbers
        This could indicate structuring or other suspicious activity
        """
        try:
            threshold = self.thresholds[PatternType.ROUND_NUMBERS]
            time_window = threshold["time_window"]
            min_occurrences = threshold["min_occurrences"]
            
            # Get transactions in the time window (24 hours)
            transactions = await self._get_recent_transactions(hours=time_window/3600)
            
            if not transactions:
                return
            
            # Group transactions by user
            user_transactions = {}
            for tx in transactions:
                user_id = tx.get("user_id")
                if not user_id:
                    continue
                
                if user_id not in user_transactions:
                    user_transactions[user_id] = []
                user_transactions[user_id].append(tx)
            
            # Check each user for round number patterns
            for user_id, user_txs in user_transactions.items():
                # Check for round numbers
                round_number_txs = []
                for tx in user_txs:
                    amount = tx.get("amount", 0)
                    
                    # Check if amount is a round number
                    is_round = (
                        amount % 1000 == 0 or  # Multiples of 1000
                        amount % 500 == 0 or   # Multiples of 500
                        amount % 100 == 0      # Multiples of 100
                    )
                    
                    if is_round:
                        round_number_txs.append(tx)
                
                # If enough round number transactions, create an alert
                if len(round_number_txs) >= min_occurrences:
                    alert_key = f"round_numbers:{user_id}:{datetime.utcnow().date().isoformat()}"
                    
                    # Avoid duplicate alerts
                    if alert_key in self.alert_cache:
                        continue
                        
                    self.alert_cache.add(alert_key)
                    
                    # Create round numbers alert
                    await self._create_alert(
                        pattern_type=PatternType.ROUND_NUMBERS,
                        severity=threshold["severity"],
                        user_id=user_id,
                        transactions=[tx.get("id") for tx in round_number_txs],
                        details={
                            "transaction_count": len(round_number_txs),
                            "amounts": [tx.get("amount") for tx in round_number_txs],
                            "time_period_hours": time_window / 3600
                        }
                    )
                    
                    # Log to audit trail
                    await audit_logger.log_event(
                        event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                        user_id=user_id,
                        details={
                            "pattern": PatternType.ROUND_NUMBERS,
                            "transaction_count": len(round_number_txs),
                            "amounts": [tx.get("amount") for tx in round_number_txs]
                        },
                        resource_id=alert_key,
                        severity="info"
                    )
                    
                    logger.info(
                        f"Round number pattern detected for user {user_id}: "
                        f"{len(round_number_txs)} transactions with round amounts"
                    )
            
        except Exception as e:
            logger.error(f"Round numbers check failed: {e}")
    
    async def check_unusual_hours(self):
        """
        Check for transactions at unusual hours
        This could indicate automated systems or suspicious activity
        """
        try:
            threshold = self.thresholds[PatternType.UNUSUAL_HOURS]
            start_hour = threshold["start_hour"]  # 10 PM
            end_hour = threshold["end_hour"]      # 5 AM
            min_transactions = threshold["min_transactions"]
            
            # Get transactions in the last 24 hours
            transactions = await self._get_recent_transactions(hours=24)
            
            if not transactions:
                return
            
            # Group transactions by user
            user_transactions = {}
            for tx in transactions:
                user_id = tx.get("user_id")
                if not user_id:
                    continue
                
                if user_id not in user_transactions:
                    user_transactions[user_id] = []
                user_transactions[user_id].append(tx)
            
            # Check each user for unusual hour transactions
            for user_id, user_txs in user_transactions.items():
                # Check for transactions during unusual hours
                unusual_hour_txs = []
                for tx in user_txs:
                    timestamp = tx.get("created_at")
                    if not timestamp:
                        continue
                    
                    try:
                        tx_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        tx_hour = tx_time.hour
                        
                        # Check if transaction occurred during unusual hours
                        is_unusual = (
                            (start_hour <= tx_hour <= 23) or  # 10 PM - midnight
                            (0 <= tx_hour < end_hour)          # midnight - 5 AM
                        )
                        
                        if is_unusual:
                            unusual_hour_txs.append(tx)
                    except ValueError:
                        continue
                
                # If enough unusual hour transactions, create an alert
                if len(unusual_hour_txs) >= min_transactions:
                    alert_key = f"unusual_hours:{user_id}:{datetime.utcnow().date().isoformat()}"
                    
                    # Avoid duplicate alerts
                    if alert_key in self.alert_cache:
                        continue
                        
                    self.alert_cache.add(alert_key)
                    
                    # Create unusual hours alert
                    await self._create_alert(
                        pattern_type=PatternType.UNUSUAL_HOURS,
                        severity=threshold["severity"],
                        user_id=user_id,
                        transactions=[tx.get("id") for tx in unusual_hour_txs],
                        details={
                            "transaction_count": len(unusual_hour_txs),
                            "hours": [datetime.fromisoformat(tx.get("created_at").replace("Z", "+00:00")).hour 
                                    for tx in unusual_hour_txs if tx.get("created_at")],
                            "unusual_range": f"{start_hour}:00-{end_hour}:00"
                        }
                    )
                    
                    # Log to audit trail
                    await audit_logger.log_event(
                        event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                        user_id=user_id,
                        details={
                            "pattern": PatternType.UNUSUAL_HOURS,
                            "transaction_count": len(unusual_hour_txs)
                        },
                        resource_id=alert_key,
                        severity="info"
                    )
                    
                    logger.info(
                        f"Unusual hour pattern detected for user {user_id}: "
                        f"{len(unusual_hour_txs)} transactions during unusual hours"
                    )
            
        except Exception as e:
            logger.error(f"Unusual hours check failed: {e}")
    
    async def check_complex_patterns(self):
        """
        Check for complex suspicious patterns that span multiple transactions
        This is where more sophisticated ML/AI pattern recognition would be used
        """
        try:
            # Get transactions from the last 7 days
            transactions = await self._get_recent_transactions(hours=24*7)
            
            if not transactions:
                return
            
            # Group transactions by user for analysis
            user_transactions = {}
            for tx in transactions:
                user_id = tx.get("user_id")
                if not user_id:
                    continue
                
                if user_id not in user_transactions:
                    user_transactions[user_id] = []
                user_transactions[user_id].append(tx)
            
            # For each user, check all complex patterns
            for user_id, user_txs in user_transactions.items():
                await self._check_multiple_deposits_pattern(user_id, user_txs)
                await self._check_rapid_transfer_chain(user_id, user_txs)
                
                # More advanced patterns would be added here
                
        except Exception as e:
            logger.error(f"Complex pattern check failed: {e}")
    
    async def _check_multiple_deposits_pattern(self, user_id: str, transactions: List[Dict[str, Any]]):
        """
        Check for pattern: Multiple small deposits followed by large withdrawal
        This is a common money laundering technique
        """
        try:
            pattern = next(p for p in self.high_risk_patterns if p["name"] == "Multiple Deposits Pattern")
            
            # Sort transactions by timestamp
            sorted_txs = sorted(transactions, key=lambda x: x.get("created_at", ""))
            
            # Get all deposits in the time window
            deposit_condition = next(c for c in pattern["conditions"] if c["stage"] == "deposit")
            time_window = deposit_condition["time_window"] * 60 * 60  # Convert hours to seconds
            max_amount = deposit_condition["max_amount"]
            min_count = deposit_condition["min_count"]
            
            # Filter small deposits
            small_deposits = [
                tx for tx in sorted_txs 
                if tx.get("payment_type") in ["deposit", "fiat_deposit"] 
                and tx.get("amount", 0) <= max_amount
            ]
            
            if len(small_deposits) < min_count:
                return
            
            # Get withdrawals after deposits
            withdrawal_condition = next(c for c in pattern["conditions"] if c["stage"] == "withdrawal")
            withdrawal_time_window = withdrawal_condition["time_window"] * 60 * 60  # Convert hours to seconds
            min_withdrawal_amount = withdrawal_condition["min_amount"]
            
            # Check if there's a large withdrawal after multiple small deposits
            last_deposit_time = datetime.fromisoformat(small_deposits[-1].get("created_at").replace("Z", "+00:00"))
            withdrawal_cutoff = last_deposit_time + timedelta(seconds=withdrawal_time_window)
            
            large_withdrawals = [
                tx for tx in sorted_txs 
                if tx.get("payment_type") in ["withdrawal", "fiat_withdrawal"]
                and tx.get("amount", 0) >= min_withdrawal_amount
                and datetime.fromisoformat(tx.get("created_at").replace("Z", "+00:00")) <= withdrawal_cutoff
                and datetime.fromisoformat(tx.get("created_at").replace("Z", "+00:00")) >= last_deposit_time
            ]
            
            if not large_withdrawals:
                return
            
            # Pattern detected, create alert
            alert_key = f"multiple_deposits:{user_id}:{datetime.utcnow().date().isoformat()}"
            
            # Avoid duplicate alerts
            if alert_key in self.alert_cache:
                return
                
            self.alert_cache.add(alert_key)
            
            # Get transaction IDs
            deposit_ids = [tx.get("id") for tx in small_deposits]
            withdrawal_ids = [tx.get("id") for tx in large_withdrawals]
            
            # Create alert
            await self._create_alert(
                pattern_type=PatternType.STRUCTURING,  # This is most similar to structuring
                severity=pattern["severity"],
                user_id=user_id,
                transactions=deposit_ids + withdrawal_ids,
                details={
                    "pattern_name": pattern["name"],
                    "small_deposits": {
                        "count": len(small_deposits),
                        "total_amount": sum(tx.get("amount", 0) for tx in small_deposits)
                    },
                    "large_withdrawals": {
                        "count": len(large_withdrawals),
                        "total_amount": sum(tx.get("amount", 0) for tx in large_withdrawals)
                    }
                }
            )
            
            # Log to audit trail
            await audit_logger.log_event(
                event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                user_id=user_id,
                details={
                    "pattern": pattern["name"],
                    "small_deposits_count": len(small_deposits),
                    "large_withdrawals_count": len(large_withdrawals)
                },
                resource_id=alert_key,
                severity="warning",
                critical=True
            )
            
            logger.warning(
                f"Multiple deposits pattern detected for user {user_id}: "
                f"{len(small_deposits)} small deposits followed by {len(large_withdrawals)} large withdrawals"
            )
            
        except Exception as e:
            logger.error(f"Multiple deposits pattern check failed: {e}")
    
    async def _check_rapid_transfer_chain(self, user_id: str, transactions: List[Dict[str, Any]]):
        """
        Check for pattern: Rapid transfers between multiple accounts
        This could indicate layering, a money laundering technique
        """
        try:
            pattern = next(p for p in self.high_risk_patterns if p["name"] == "Rapid Transfer Chain")
            condition = pattern["conditions"][0]
            
            # Filter transfer transactions
            transfer_txs = [
                tx for tx in transactions 
                if tx.get("payment_type") in ["transfer", "cross_border"]
                and tx.get("amount", 0) >= condition["min_amount"]
            ]
            
            if not transfer_txs:
                return
            
            # Sort by timestamp
            sorted_txs = sorted(transfer_txs, key=lambda x: x.get("created_at", ""))
            
            # Get unique recipients
            recipients = set()
            for tx in sorted_txs:
                recipient = tx.get("receiver_address")
                if recipient:
                    recipients.add(recipient)
            
            # Check if enough unique recipients within time window
            if len(recipients) >= condition["unique_recipients"]:
                # Check time window
                time_window = condition["time_window"] * 60 * 60  # Convert hours to seconds
                first_tx_time = datetime.fromisoformat(sorted_txs[0].get("created_at").replace("Z", "+00:00"))
                last_tx_time = datetime.fromisoformat(sorted_txs[-1].get("created_at").replace("Z", "+00:00"))
                
                # If transfers happened within the time window
                if (last_tx_time - first_tx_time).total_seconds() <= time_window:
                    alert_key = f"rapid_transfer:{user_id}:{datetime.utcnow().date().isoformat()}"
                    
                    # Avoid duplicate alerts
                    if alert_key in self.alert_cache:
                        return
                        
                    self.alert_cache.add(alert_key)
                    
                    # Create alert
                    await self._create_alert(
                        pattern_type=PatternType.LAYERING,  # This is most similar to layering
                        severity=pattern["severity"],
                        user_id=user_id,
                        transactions=[tx.get("id") for tx in sorted_txs],
                        details={
                            "pattern_name": pattern["name"],
                            "unique_recipients": len(recipients),
                            "transaction_count": len(sorted_txs),
                            "time_span_hours": (last_tx_time - first_tx_time).total_seconds() / 3600,
                            "total_amount": sum(tx.get("amount", 0) for tx in sorted_txs)
                        }
                    )
                    
                    # Log to audit trail
                    await audit_logger.log_event(
                        event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                        user_id=user_id,
                        details={
                            "pattern": pattern["name"],
                            "transaction_count": len(sorted_txs),
                            "unique_recipients": len(recipients)
                        },
                        resource_id=alert_key,
                        severity="warning"
                    )
                    
                    logger.warning(
                        f"Rapid transfer chain detected for user {user_id}: "
                        f"{len(sorted_txs)} transfers to {len(recipients)} unique recipients "
                        f"in {(last_tx_time - first_tx_time).total_seconds() / 3600:.1f} hours"
                    )
            
        except Exception as e:
            logger.error(f"Rapid transfer chain check failed: {e}")
    
    async def _create_alert(self, 
                           pattern_type: str, 
                           severity: str,
                           user_id: Optional[str] = None,
                           transactions: Optional[List[str]] = None,
                           details: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Create a monitoring alert"""
        if not self.supabase:
            return None
            
        try:
            alert_id = f"alert_{int(time.time())}_{os.urandom(4).hex()}"
            
            alert_data = {
                "id": alert_id,
                "pattern_type": pattern_type,
                "severity": severity,
                "user_id": user_id,
                "transaction_ids": transactions,
                "details": details,
                "status": "new",
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = await self.supabase.table("monitoring_alerts").insert(alert_data).execute()
            
            if hasattr(response, "error") and response.error:
                logger.error(f"Failed to create alert: {response.error}")
                return None
            
            # If Redis is available, publish alert for real-time notifications
            if self.redis:
                try:
                    await self.redis.publish(
                        "monitoring:alerts", 
                        json.dumps(alert_data)
                    )
                except Exception as e:
                    logger.error(f"Failed to publish alert: {e}")
            
            return alert_id
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return None
    
    async def get_user_risk_score(self, user_id: str) -> Dict[str, Any]:
        """Calculate user risk score based on monitoring alerts and activity"""
        if not self.supabase:
            return {"risk_score": 0, "risk_level": "unknown"}
            
        try:
            # Get user's alerts
            alerts = await self.supabase.table("monitoring_alerts").select("*").eq("user_id", user_id).execute()
            
            if not alerts.data:
                return {"risk_score": 0, "risk_level": "low"}
            
            # Calculate base risk score
            severity_weights = {
                MonitoringSeverity.INFO: 1,
                MonitoringSeverity.LOW: 2,
                MonitoringSeverity.MEDIUM: 5,
                MonitoringSeverity.HIGH: 10,
                MonitoringSeverity.CRITICAL: 20
            }
            
            pattern_weights = {
                PatternType.STRUCTURING: 2.0,
                PatternType.VELOCITY: 1.0,
                PatternType.CYCLING: 2.0,
                PatternType.LAYERING: 2.0,
                PatternType.SMURFING: 2.0,
                PatternType.ROUND_NUMBERS: 0.5,
                PatternType.UNUSUAL_HOURS: 0.5,
                PatternType.JURISDICTION_RISK: 1.5,
                PatternType.NESTED_TRANSFERS: 1.5
            }
            
            risk_score = 0
            for alert in alerts.data:
                severity = alert.get("severity", MonitoringSeverity.LOW)
                pattern = alert.get("pattern_type")
                
                severity_weight = severity_weights.get(severity, 1)
                pattern_weight = pattern_weights.get(pattern, 1.0)
                
                # Calculate alert score
                alert_score = severity_weight * pattern_weight
                
                # Reduce impact of older alerts
                age_days = (datetime.utcnow() - datetime.fromisoformat(alert.get("created_at").replace("Z", "+00:00"))).days
                age_factor = max(0.1, 1.0 - (age_days / 30))  # Reduce by 1/30 per day, minimum 0.1
                
                risk_score += alert_score * age_factor
            
            # Normalize risk score (0-100)
            normalized_score = min(100, risk_score)
            
            # Determine risk level
            risk_level = "low"
            if normalized_score >= 75:
                risk_level = "critical"
            elif normalized_score >= 50:
                risk_level = "high"
            elif normalized_score >= 25:
                risk_level = "medium"
            
            return {
                "risk_score": normalized_score,
                "risk_level": risk_level,
                "alerts_count": len(alerts.data),
                "latest_alert": alerts.data[0].get("created_at") if alerts.data else None,
                "highest_severity": max([a.get("severity", "low") for a in alerts.data], key=lambda s: severity_weights.get(s, 0)) if alerts.data else "none"
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate user risk score: {e}")
            return {"risk_score": 0, "risk_level": "error", "error": str(e)}
    
    async def get_alerts(self, 
                        status: Optional[str] = None, 
                        severity: Optional[str] = None,
                        limit: int = 100, 
                        offset: int = 0) -> List[Dict[str, Any]]:
        """Get monitoring alerts with filtering"""
        if not self.supabase:
            return []
            
        try:
            # Build the query
            query = self.supabase.table("monitoring_alerts").select("*")
            
            if status:
                query = query.eq("status", status)
                
            if severity:
                query = query.eq("severity", severity)
                
            # Apply pagination and ordering
            query = query.order("created_at", {"ascending": False}).range(offset, offset + limit - 1)
            
            # Execute query
            response = await query.execute()
            
            if hasattr(response, "error") and response.error:
                logger.error(f"Failed to retrieve alerts: {response.error}")
                return []
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    async def update_alert_status(self, alert_id: str, status: str, notes: Optional[str] = None) -> bool:
        """Update alert status (for compliance officer review)"""
        if not self.supabase:
            return False
            
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if notes:
                update_data["notes"] = notes
                
            response = await self.supabase.table("monitoring_alerts").update(update_data).eq("id", alert_id).execute()
            
            if hasattr(response, "error") and response.error:
                logger.error(f"Failed to update alert: {response.error}")
                return False
            
            # Log to audit trail
            await audit_logger.log_event(
                event_type=AuditEventType.ADMIN_ACTION,
                details={
                    "action": "update_alert_status",
                    "alert_id": alert_id,
                    "new_status": status,
                    "notes": notes
                },
                resource_id=alert_id,
                severity="info"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update alert: {e}")
            return False

# Create singleton instance
monitoring_service = ContinuousMonitoringService()