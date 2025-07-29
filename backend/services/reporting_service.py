"""
Seamount.io Cross-Border Payment Platform
Regulatory Reporting Engine

Generates automated regulatory reports required by African central banks
and financial authorities, including suspicious activity reports (SARs)
and currency transaction reports (CTRs).
"""

// Location: /backend/services/reporting_service.py

import logging
import os
import json
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import csv
import io
from decimal import Decimal
from supabase import create_client, Client
import aioredis
from dateutil import parser

# Import audit logging
from backend.audit_logging import audit_logger, AuditEventType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportType:
    """Types of regulatory reports"""
    SUSPICIOUS_ACTIVITY = "sar"  # Suspicious Activity Report
    CURRENCY_TRANSACTION = "ctr"  # Currency Transaction Report
    CROSS_BORDER_WIRE = "cbw"    # Cross-Border Wire Transfer
    MONTHLY_SUMMARY = "summary"  # Monthly Activity Summary
    DAILY_TRANSACTIONS = "daily" # Daily Transaction Report
    
class ReportFormat:
    """Output formats for regulatory reports"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    XLSX = "xlsx"
    
class ReportStatus:
    """Status of report generation"""
    SCHEDULED = "scheduled"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    
class RegulatoryReportingEngine:
    """
    Generates regulatory reports for African financial authorities
    with support for country-specific requirements.
    """
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase = None
        self.redis = None
        
        # Country-specific regulatory thresholds
        self.thresholds = {
            "KE": {  # Kenya
                ReportType.CURRENCY_TRANSACTION: 10000,  # $10,000 USD equivalent
                ReportType.SUSPICIOUS_ACTIVITY: 5000,    # $5,000 USD equivalent
            },
            "NG": {  # Nigeria
                ReportType.CURRENCY_TRANSACTION: 5000,   # $5,000 USD equivalent
                ReportType.SUSPICIOUS_ACTIVITY: 1000,    # $1,000 USD equivalent
            },
            "ZA": {  # South Africa
                ReportType.CURRENCY_TRANSACTION: 25000,  # R25,000 (~$1,500 USD)
                ReportType.SUSPICIOUS_ACTIVITY: 5000,    # R5,000 (~$300 USD)
            },
            "GH": {  # Ghana
                ReportType.CURRENCY_TRANSACTION: 10000,  # $10,000 USD equivalent
                ReportType.SUSPICIOUS_ACTIVITY: 3000,    # $3,000 USD equivalent
            }
        }
        
        # Default global thresholds
        self.default_thresholds = {
            ReportType.CURRENCY_TRANSACTION: 10000,  # $10,000 USD
            ReportType.SUSPICIOUS_ACTIVITY: 5000,    # $5,000 USD
        }
        
        # Initialize DB connections
        self._initialize_db()
        
        # Scheduled reports configuration
        self.scheduled_reports = [
            {
                "report_type": ReportType.CURRENCY_TRANSACTION,
                "frequency": "daily",
                "time": "23:59:59",
                "formats": [ReportFormat.JSON, ReportFormat.CSV],
                "country_codes": ["KE", "NG", "ZA", "GH"]
            },
            {
                "report_type": ReportType.DAILY_TRANSACTIONS,
                "frequency": "daily",
                "time": "23:59:59",
                "formats": [ReportFormat.JSON, ReportFormat.CSV],
                "country_codes": ["KE", "NG", "ZA", "GH"]
            },
            {
                "report_type": ReportType.SUSPICIOUS_ACTIVITY,
                "frequency": "weekly",
                "day": "Monday",
                "time": "00:00:01",
                "formats": [ReportFormat.JSON],
                "country_codes": ["KE", "NG", "ZA", "GH"]
            },
            {
                "report_type": ReportType.MONTHLY_SUMMARY,
                "frequency": "monthly",
                "day": 1,
                "time": "00:00:01",
                "formats": [ReportFormat.JSON, ReportFormat.CSV],
                "country_codes": ["KE", "NG", "ZA", "GH"]
            }
        ]
        
        # Start background scheduler
        self.scheduler_task = None
        self.running = False
    
    def _initialize_db(self):
        """Initialize database connections"""
        try:
            if self.supabase_url and self.supabase_key:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                logger.info("Regulatory Reporting: Supabase connected")
            else:
                logger.warning("Regulatory Reporting: No Supabase credentials")
        except Exception as e:
            logger.error(f"Regulatory Reporting DB initialization failed: {e}")
    
    async def initialize_redis(self):
        """Initialize Redis connection"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis = await aioredis.from_url(redis_url)
            logger.info("Regulatory Reporting: Redis connected")
        except Exception as e:
            logger.error(f"Regulatory Reporting Redis connection failed: {e}")
            self.redis = None
    
    async def start_scheduler(self):
        """Start the report scheduler"""
        if self.running:
            logger.warning("Report scheduler already running")
            return
            
        self.running = True
        await self.initialize_redis()
        
        # Start the scheduler loop
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Regulatory report scheduler started")
    
    async def stop_scheduler(self):
        """Stop the report scheduler"""
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
            self.scheduler_task = None
        
        logger.info("Regulatory report scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop that runs periodically"""
        while self.running:
            try:
                # Check for reports that need to be generated
                now = datetime.utcnow()
                
                for report_config in self.scheduled_reports:
                    frequency = report_config["frequency"]
                    
                    # Check if report should be generated now
                    should_generate = False
                    
                    if frequency == "daily":
                        # Parse scheduled time
                        scheduled_time = datetime.strptime(report_config["time"], "%H:%M:%S").time()
                        scheduled_datetime = datetime.combine(now.date(), scheduled_time)
                        
                        # Check if it's time to generate (within the last 5 minutes)
                        time_diff = (now - scheduled_datetime).total_seconds()
                        should_generate = 0 <= time_diff < 300
                        
                    elif frequency == "weekly" and report_config.get("day"):
                        # Check day of week (0 = Monday, 6 = Sunday)
                        days = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
                        scheduled_day = days.get(report_config["day"], 0)
                        
                        if now.weekday() == scheduled_day:
                            # Parse scheduled time
                            scheduled_time = datetime.strptime(report_config["time"], "%H:%M:%S").time()
                            scheduled_datetime = datetime.combine(now.date(), scheduled_time)
                            
                            # Check if it's time to generate (within the last 5 minutes)
                            time_diff = (now - scheduled_datetime).total_seconds()
                            should_generate = 0 <= time_diff < 300
                        
                    elif frequency == "monthly" and report_config.get("day"):
                        scheduled_day = report_config["day"]
                        
                        if now.day == scheduled_day:
                            # Parse scheduled time
                            scheduled_time = datetime.strptime(report_config["time"], "%H:%M:%S").time()
                            scheduled_datetime = datetime.combine(now.date(), scheduled_time)
                            
                            # Check if it's time to generate (within the last 5 minutes)
                            time_diff = (now - scheduled_datetime).total_seconds()
                            should_generate = 0 <= time_diff < 300
                    
                    # Generate reports for each country
                    if should_generate:
                        for country_code in report_config["country_codes"]:
                            report_type = report_config["report_type"]
                            formats = report_config["formats"]
                            
                            # Check if report was already generated today
                            report_key = f"report:{country_code}:{report_type}:{now.date().isoformat()}"
                            
                            if self.redis:
                                already_generated = await self.redis.exists(report_key)
                                if already_generated:
                                    continue
                                    
                                # Mark as generated to avoid duplicates
                                await self.redis.set(report_key, "1", ex=86400)  # Expires in 24 hours
                            
                            # Determine date range for the report
                            if frequency == "daily":
                                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
                                end_date = start_date.replace(hour=23, minute=59, second=59)
                            elif frequency == "weekly":
                                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
                                end_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
                            elif frequency == "monthly":
                                # First day of previous month
                                if now.month == 1:
                                    start_date = datetime(now.year - 1, 12, 1)
                                else:
                                    start_date = datetime(now.year, now.month - 1, 1)
                                    
                                # Last day of previous month
                                end_date = datetime(now.year, now.month, 1) - timedelta(seconds=1)
                            
                            # Generate the report
                            for format in formats:
                                await self.generate_report(
                                    report_type=report_type,
                                    country_code=country_code,
                                    start_date=start_date.isoformat(),
                                    end_date=end_date.isoformat(),
                                    format=format
                                )
                            
                            logger.info(f"Scheduled report generated: {report_type} for {country_code}")
                
                # Sleep for a minute before checking again
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(300)  # On error, sleep for 5 minutes before retrying
    
    async def generate_report(self,
                            report_type: str,
                            country_code: str,
                            start_date: str,
                            end_date: str,
                            format: str = ReportFormat.JSON,
                            request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a regulatory report
        
        Args:
            report_type: Type of report (see ReportType)
            country_code: Country code (e.g. 'KE' for Kenya)
            start_date: Start date in ISO format
            end_date: End date in ISO format
            format: Output format (json, csv, etc)
            request_id: Optional request ID for tracking
            
        Returns:
            Report data and metadata
        """
        if not self.supabase:
            return {"error": "No database connection"}
            
        # If no request ID provided, generate one
        if not request_id:
            request_id = f"report_{int(time.time())}_{os.urandom(4).hex()}"
        
        try:
            # Store report record
            report_record = {
                "id": request_id,
                "report_type": report_type,
                "country_code": country_code,
                "start_date": start_date,
                "end_date": end_date,
                "format": format,
                "status": ReportStatus.GENERATING,
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.supabase.table("regulatory_reports").insert(report_record).execute()
            
            # Log report generation to audit trail
            await audit_logger.log_event(
                event_type=AuditEventType.ADMIN_ACTION,
                details={
                    "action": "generate_report",
                    "report_type": report_type,
                    "country_code": country_code,
                    "start_date": start_date,
                    "end_date": end_date
                },
                resource_id=request_id,
                severity="info"
            )
            
            # Generate the appropriate report type
            report_data = None
            
            if report_type == ReportType.CURRENCY_TRANSACTION:
                report_data = await self._generate_ctr_report(country_code, start_date, end_date)
            elif report_type == ReportType.SUSPICIOUS_ACTIVITY:
                report_data = await self._generate_sar_report(country_code, start_date, end_date)
            elif report_type == ReportType.CROSS_BORDER_WIRE:
                report_data = await self._generate_cbw_report(country_code, start_date, end_date)
            elif report_type == ReportType.MONTHLY_SUMMARY:
                report_data = await self._generate_monthly_summary(country_code, start_date, end_date)
            elif report_type == ReportType.DAILY_TRANSACTIONS:
                report_data = await self._generate_daily_transactions(country_code, start_date, end_date)
            else:
                raise ValueError(f"Unsupported report type: {report_type}")
                
            # Format the report
            formatted_report = await self._format_report(report_data, format)
            
            # Store the report content
            file_name = f"{report_type}_{country_code}_{start_date.split('T')[0]}_{end_date.split('T')[0]}.{format}"
            
            if format in [ReportFormat.JSON, ReportFormat.CSV]:
                report_content = formatted_report
            else:
                # For binary formats, store a placeholder
                report_content = "Binary report data not stored in database"
            
            # Update report record
            update_data = {
                "status": ReportStatus.COMPLETED,
                "file_name": file_name,
                "completed_at": datetime.utcnow().isoformat(),
                "record_count": report_data.get("record_count", 0),
                "report_content": report_content if format in [ReportFormat.JSON, ReportFormat.CSV] else None
            }
            
            await self.supabase.table("regulatory_reports").update(update_data).eq("id", request_id).execute()
            
            # Return report metadata
            return {
                "id": request_id,
                "status": ReportStatus.COMPLETED,
                "report_type": report_type,
                "country_code": country_code,
                "start_date": start_date,
                "end_date": end_date,
                "format": format,
                "file_name": file_name,
                "record_count": report_data.get("record_count", 0),
                "completed_at": update_data["completed_at"]
            }
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            
            # Update report status to failed
            try:
                if self.supabase:
                    await self.supabase.table("regulatory_reports").update({
                        "status": ReportStatus.FAILED,
                        "error_message": str(e)
                    }).eq("id", request_id).execute()
            except Exception as update_error:
                logger.error(f"Failed to update report status: {update_error}")
            
            return {"error": str(e), "id": request_id, "status": ReportStatus.FAILED}
    
    async def _generate_ctr_report(self, 
                                 country_code: str, 
                                 start_date: str, 
                                 end_date: str) -> Dict[str, Any]:
        """
        Generate Currency Transaction Report (CTR)
        Reports all transactions above the reporting threshold
        """
        if not self.supabase:
            return {"error": "No database connection"}
        
        try:
            # Get threshold for this country
            threshold = self.thresholds.get(country_code, {}).get(
                ReportType.CURRENCY_TRANSACTION, 
                self.default_thresholds[ReportType.CURRENCY_TRANSACTION]
            )
            
            # Get all transactions above threshold
            query = self.supabase.table("payment_transactions").select("*") \
                .gte("created_at", start_date) \
                .lt("created_at", end_date) \
                .gte("amount", threshold)
            
            if country_code:
                query = query.eq("country_code", country_code)
                
            response = await query.execute()
            
            if hasattr(response, "error") and response.error:
                return {"error": response.error}
                
            transactions = response.data or []
            
            # Get user details for the transactions
            user_ids = list(set(tx.get("user_id") for tx in transactions if tx.get("user_id")))
            
            user_details = {}
            if user_ids:
                user_response = await self.supabase.table("user_profiles").select(
                    "id, first_name, last_name, country_code, kyc_level"
                ).in_("id", user_ids).execute()
                
                if user_response.data:
                    user_details = {u["id"]: u for u in user_response.data}
            
            # Format CTR data
            ctr_records = []
            for tx in transactions:
                user_id = tx.get("user_id")
                user = user_details.get(user_id, {})
                
                ctr_record = {
                    "transaction_id": tx.get("id"),
                    "reference": tx.get("reference"),
                    "date": tx.get("created_at"),
                    "amount": tx.get("amount"),
                    "currency": tx.get("currency"),
                    "payment_type": tx.get("payment_type"),
                    "status": tx.get("status"),
                    "country_code": tx.get("country_code") or country_code,
                    "user": {
                        "id": user_id,
                        "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Unknown",
                        "country_code": user.get("country_code") or country_code,
                        "kyc_level": user.get("kyc_level", 0)
                    },
                    "sender_address": tx.get("sender_address"),
                    "receiver_address": tx.get("receiver_address"),
                    "reporting_threshold": threshold
                }
                
                ctr_records.append(ctr_record)
            
            # Create report data
            return {
                "report_type": ReportType.CURRENCY_TRANSACTION,
                "country_code": country_code,
                "start_date": start_date,
                "end_date": end_date,
                "threshold": threshold,
                "generated_at": datetime.utcnow().isoformat(),
                "record_count": len(ctr_records),
                "records": ctr_records
            }
            
        except Exception as e:
            logger.error(f"CTR report generation failed: {e}")
            return {"error": str(e), "report_type": ReportType.CURRENCY_TRANSACTION}
    
    async def _generate_sar_report(self, 
                                 country_code: str, 
                                 start_date: str, 
                                 end_date: str) -> Dict[str, Any]:
        """
        Generate Suspicious Activity Report (SAR)
        Reports all flagged suspicious activities
        """
        if not self.supabase:
            return {"error": "No database connection"}
        
        try:
            # Get alerts from monitoring service
            alerts_query = self.supabase.table("monitoring_alerts").select("*") \
                .gte("created_at", start_date) \
                .lt("created_at", end_date)
                
            alerts_response = await alerts_query.execute()
            
            if hasattr(alerts_response, "error") and alerts_response.error:
                return {"error": alerts_response.error}
                
            alerts = alerts_response.data or []
            
            # Get user details for the alerts
            user_ids = list(set(alert.get("user_id") for alert in alerts if alert.get("user_id")))
            
            user_details = {}
            if user_ids:
                user_response = await self.supabase.table("user_profiles").select(
                    "id, first_name, last_name, country_code, kyc_level"
                ).in_("id", user_ids).execute()
                
                if user_response.data:
                    user_details = {u["id"]: u for u in user_response.data}
            
            # Get transactions referenced in alerts
            tx_ids = []
            for alert in alerts:
                tx_ids.extend(alert.get("transaction_ids") or [])
                
            tx_details = {}
            if tx_ids:
                tx_response = await self.supabase.table("payment_transactions").select("*").in_("id", tx_ids).execute()
                
                if tx_response.data:
                    tx_details = {tx["id"]: tx for tx in tx_response.data}
            
            # Format SAR data
            sar_records = []
            for alert in alerts:
                user_id = alert.get("user_id")
                user = user_details.get(user_id, {})
                
                # Filter alerts for this country
                if country_code and user.get("country_code") and user.get("country_code") != country_code:
                    continue
                
                # Get transactions for this alert
                alert_txs = []
                for tx_id in alert.get("transaction_ids") or []:
                    if tx_id in tx_details:
                        alert_txs.append(tx_details[tx_id])
                
                # Calculate total transaction amount
                total_amount = sum(tx.get("amount", 0) for tx in alert_txs)
                
                sar_record = {
                    "alert_id": alert.get("id"),
                    "pattern_type": alert.get("pattern_type"),
                    "severity": alert.get("severity"),
                    "date": alert.get("created_at"),
                    "status": alert.get("status"),
                    "user": {
                        "id": user_id,
                        "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Unknown",
                        "country_code": user.get("country_code") or country_code,
                        "kyc_level": user.get("kyc_level", 0)
                    },
                    "transaction_count": len(alert_txs),
                    "total_amount": total_amount,
                    "details": alert.get("details")
                }
                
                sar_records.append(sar_record)
            
            # Create report data
            return {
                "report_type": ReportType.SUSPICIOUS_ACTIVITY,
                "country_code": country_code,
                "start_date": start_date,
                "end_date": end_date,
                "generated_at": datetime.utcnow().isoformat(),
                "record_count": len(sar_records),
                "records": sar_records
            }
            
        except Exception as e:
            logger.error(f"SAR report generation failed: {e}")
            return {"error": str(e), "report_type": ReportType.SUSPICIOUS_ACTIVITY}
    
    async def _generate_cbw_report(self, 
                                country_code: str, 
                                start_date: str, 
                                end_date: str) -> Dict[str, Any]:
        """
        Generate Cross-Border Wire Transfer Report
        Reports all cross-border transactions
        """
        if not self.supabase:
            return {"error": "No database connection"}
        
        try:
            # Get all cross-border transactions
            query = self.supabase.table("payment_transactions").select("*") \
                .gte("created_at", start_date) \
                .lt("created_at", end_date) \
                .eq("payment_type", "cross_border")
            
            if country_code:
                query = query.eq("country_code", country_code)
                
            response = await query.execute()
            
            if hasattr(response, "error") and response.error:
                return {"error": response.error}
                
            transactions = response.data or []
            
            # Get user details for the transactions
            user_ids = list(set(tx.get("user_id") for tx in transactions if tx.get("user_id")))
            
            user_details = {}
            if user_ids:
                user_response = await self.supabase.table("user_profiles").select(
                    "id, first_name, last_name, country_code, kyc_level"
                ).in_("id", user_ids).execute()
                
                if user_response.data:
                    user_details = {u["id"]: u for u in user_response.data}
            
            # Format CBW data
            cbw_records = []
            for tx in transactions:
                user_id = tx.get("user_id")
                user = user_details.get(user_id, {})
                
                # Determine corridor
                from_country = user.get("country_code") or country_code
                to_country = None
                
                if tx.get("metadata") and isinstance(tx.get("metadata"), dict):
                    to_country = tx.get("metadata").get("to_country")
                
                cbw_record = {
                    "transaction_id": tx.get("id"),
                    "reference": tx.get("reference"),
                    "date": tx.get("created_at"),
                    "amount": tx.get("amount"),
                    "fee": tx.get("fee"),
                    "currency": tx.get("currency"),
                    "status": tx.get("status"),
                    "from_country": from_country,
                    "to_country": to_country,
                    "corridor": f"{from_country}-{to_country}" if to_country else None,
                    "user": {
                        "id": user_id,
                        "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Unknown",
                        "kyc_level": user.get("kyc_level", 0)
                    },
                    "sender_address": tx.get("sender_address"),
                    "receiver_address": tx.get("receiver_address"),
                    "exchange_rate": tx.get("exchange_rate")
                }
                
                cbw_records.append(cbw_record)
            
            # Create report data
            return {
                "report_type": ReportType.CROSS_BORDER_WIRE,
                "country_code": country_code,
                "start_date": start_date,
                "end_date": end_date,
                "generated_at": datetime.utcnow().isoformat(),
                "record_count": len(cbw_records),
                "records": cbw_records
            }
            
        except Exception as e:
            logger.error(f"CBW report generation failed: {e}")
            return {"error": str(e), "report_type": ReportType.CROSS_BORDER_WIRE}
    
    async def _generate_monthly_summary(self, 
                                      country_code: str, 
                                      start_date: str, 
                                      end_date: str) -> Dict[str, Any]:
        """
        Generate Monthly Summary Report
        Provides summary of all activity for the month
        """
        if not self.supabase:
            return {"error": "No database connection"}
        
        try:
            # Get all transactions in the period
            query = self.supabase.table("payment_transactions").select("*") \
                .gte("created_at", start_date) \
                .lt("created_at", end_date)
            
            if country_code:
                query = query.eq("country_code", country_code)
                
            response = await query.execute()
            
            if hasattr(response, "error") and response.error:
                return {"error": response.error}
                
            transactions = response.data or []
            
            # Calculate metrics
            total_volume = sum(tx.get("amount", 0) for tx in transactions)
            total_fees = sum(tx.get("fee", 0) for tx in transactions)
            
            # Group by payment type
            payment_types = {}
            for tx in transactions:
                payment_type = tx.get("payment_type")
                if payment_type not in payment_types:
                    payment_types[payment_type] = {
                        "count": 0,
                        "volume": 0,
                        "fees": 0
                    }
                
                payment_types[payment_type]["count"] += 1
                payment_types[payment_type]["volume"] += tx.get("amount", 0)
                payment_types[payment_type]["fees"] += tx.get("fee", 0)
            
            # Group by currency
            currencies = {}
            for tx in transactions:
                currency = tx.get("currency")
                if currency not in currencies:
                    currencies[currency] = {
                        "count": 0,
                        "volume": 0
                    }
                
                currencies[currency]["count"] += 1
                currencies[currency]["volume"] += tx.get("amount", 0)
            
            # Group by day
            daily_volumes = {}
            for tx in transactions:
                created_at = tx.get("created_at")
                if not created_at:
                    continue
                    
                try:
                    tx_date = parser.parse(created_at).date().isoformat()
                    
                    if tx_date not in daily_volumes:
                        daily_volumes[tx_date] = {
                            "count": 0,
                            "volume": 0,
                            "fees": 0
                        }
                    
                    daily_volumes[tx_date]["count"] += 1
                    daily_volumes[tx_date]["volume"] += tx.get("amount", 0)
                    daily_volumes[tx_date]["fees"] += tx.get("fee", 0)
                except ValueError:
                    continue
            
            # Get user metrics
            unique_users = set(tx.get("user_id") for tx in transactions if tx.get("user_id"))
            
            # Create report data
            return {
                "report_type": ReportType.MONTHLY_SUMMARY,
                "country_code": country_code,
                "start_date": start_date,
                "end_date": end_date,
                "generated_at": datetime.utcnow().isoformat(),
                "record_count": len(transactions),
                "summary": {
                    "total_transactions": len(transactions),
                    "total_volume": total_volume,
                    "total_fees": total_fees,
                    "unique_users": len(unique_users),
                    "average_transaction_size": total_volume / len(transactions) if transactions else 0
                },
                "payment_types": payment_types,
                "currencies": currencies,
                "daily_volumes": daily_volumes
            }
            
        except Exception as e:
            logger.error(f"Monthly summary report generation failed: {e}")
            return {"error": str(e), "report_type": ReportType.MONTHLY_SUMMARY}
    
    async def _generate_daily_transactions(self, 
                                         country_code: str, 
                                         start_date: str, 
                                         end_date: str) -> Dict[str, Any]:
        """
        Generate Daily Transaction Report
        Lists all transactions for a day
        """
        if not self.supabase:
            return {"error": "No database connection"}
        
        try:
            # Get all transactions for the day
            query = self.supabase.table("payment_transactions").select("*") \
                .gte("created_at", start_date) \
                .lt("created_at", end_date)
            
            if country_code:
                query = query.eq("country_code", country_code)
                
            response = await query.execute()
            
            if hasattr(response, "error") and response.error:
                return {"error": response.error}
                
            transactions = response.data or []
            
            # Get user details for the transactions
            user_ids = list(set(tx.get("user_id") for tx in transactions if tx.get("user_id")))
            
            user_details = {}
            if user_ids:
                user_response = await self.supabase.table("user_profiles").select(
                    "id, first_name, last_name, country_code, kyc_level"
                ).in_("id", user_ids).execute()
                
                if user_response.data:
                    user_details = {u["id"]: u for u in user_response.data}
            
            # Format transaction records
            tx_records = []
            for tx in transactions:
                user_id = tx.get("user_id")
                user = user_details.get(user_id, {})
                
                tx_record = {
                    "transaction_id": tx.get("id"),
                    "reference": tx.get("reference"),
                    "date": tx.get("created_at"),
                    "amount": tx.get("amount"),
                    "fee": tx.get("fee"),
                    "currency": tx.get("currency"),
                    "payment_type": tx.get("payment_type"),
                    "status": tx.get("status"),
                    "country_code": tx.get("country_code") or country_code,
                    "user": {
                        "id": user_id,
                        "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Unknown",
                        "country_code": user.get("country_code"),
                        "kyc_level": user.get("kyc_level", 0)
                    },
                    "sender_address": tx.get("sender_address"),
                    "receiver_address": tx.get("receiver_address"),
                    "tx_hash": tx.get("tx_id"),
                    "provider": tx.get("provider")
                }
                
                tx_records.append(tx_record)
            
            # Create report data
            return {
                "report_type": ReportType.DAILY_TRANSACTIONS,
                "country_code": country_code,
                "start_date": start_date,
                "end_date": end_date,
                "generated_at": datetime.utcnow().isoformat(),
                "record_count": len(tx_records),
                "records": tx_records
            }
            
        except Exception as e:
            logger.error(f"Daily transactions report generation failed: {e}")
            return {"error": str(e), "report_type": ReportType.DAILY_TRANSACTIONS}
    
    async def _format_report(self, report_data: Dict[str, Any], format: str) -> Any:
        """Format the report in the requested format"""
        if "error" in report_data:
            return json.dumps({"error": report_data["error"]})
            
        if format == ReportFormat.JSON:
            return json.dumps(report_data, indent=2)
            
        elif format == ReportFormat.CSV:
            # Convert report data to CSV
            output = io.StringIO()
            writer = None
            
            # Different handling based on report type
            if "records" in report_data:
                # Reports with record lists (most reports)
                records = report_data["records"]
                
                if not records:
                    return "No records found"
                
                # Flatten the first record to get CSV headers
                flat_record = self._flatten_record(records[0])
                fieldnames = list(flat_record.keys())
                
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write each record
                for record in records:
                    writer.writerow(self._flatten_record(record))
            else:
                # Summary reports
                fieldnames = ["metric", "value"]
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write summary data
                if "summary" in report_data:
                    for key, value in report_data["summary"].items():
                        writer.writerow({"metric": key, "value": value})
                        
                # Write other sections
                for section in ["payment_types", "currencies", "daily_volumes"]:
                    if section in report_data:
                        writer.writerow({"metric": f"--- {section.upper()} ---", "value": ""})
                        for key, data in report_data[section].items():
                            if isinstance(data, dict):
                                for subkey, subvalue in data.items():
                                    writer.writerow({"metric": f"{key} - {subkey}", "value": subvalue})
                            else:
                                writer.writerow({"metric": key, "value": data})
            
            return output.getvalue()
            
        elif format in [ReportFormat.PDF, ReportFormat.XLSX]:
            # For now, just return JSON with a note
            # In production, we would use libraries to generate these formats
            return json.dumps({
                "note": f"{format.upper()} generation not implemented in this version",
                "report_data": report_data
            })
        else:
            return json.dumps({"error": f"Unsupported format: {format}"})
    
    def _flatten_record(self, record: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested dictionaries for CSV output"""
        result = {}
        
        for key, value in record.items():
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                nested = self._flatten_record(value, f"{prefix}{key}_")
                result.update(nested)
            elif isinstance(value, (list, tuple)):
                # For lists, join with commas
                result[f"{prefix}{key}"] = ",".join(str(item) for item in value)
            else:
                # Regular values
                result[f"{prefix}{key}"] = value
                
        return result
    
    async def get_reports(self, 
                         report_type: Optional[str] = None, 
                         country_code: Optional[str] = None, 
                         limit: int = 100, 
                         offset: int = 0) -> List[Dict[str, Any]]:
        """Get list of generated reports with filtering"""
        if not self.supabase:
            return []
            
        try:
            # Build the query
            query = self.supabase.table("regulatory_reports").select("id, report_type, country_code, start_date, end_date, format, status, created_at, completed_at, record_count, file_name")
            
            if report_type:
                query = query.eq("report_type", report_type)
                
            if country_code:
                query = query.eq("country_code", country_code)
                
            # Apply pagination and ordering
            query = query.order("created_at", {"ascending": False}).range(offset, offset + limit - 1)
            
            # Execute query
            response = await query.execute()
            
            if hasattr(response, "error") and response.error:
                logger.error(f"Failed to retrieve reports: {response.error}")
                return []
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Failed to get reports: {e}")
            return []
    
    async def get_report_content(self, report_id: str) -> Optional[str]:
        """Get the content of a generated report"""
        if not self.supabase:
            return None
            
        try:
            response = await self.supabase.table("regulatory_reports").select(
                "report_content, status, format, file_name"
            ).eq("id", report_id).execute()
            
            if not response.data:
                return None
                
            report = response.data[0]
            
            if report["status"] != ReportStatus.COMPLETED:
                return None
                
            if not report.get("report_content"):
                return json.dumps({"error": "Report content not available"})
                
            return report["report_content"]
            
        except Exception as e:
            logger.error(f"Failed to get report content: {e}")
            return None
    
    async def download_report(self, report_id: str) -> Optional[Tuple[str, str]]:
        """
        Get report content for download
        
        Returns:
            Tuple of (content, filename) if successful, None otherwise
        """
        content = await self.get_report_content(report_id)
        if not content:
            return None
            
        try:
            response = await self.supabase.table("regulatory_reports").select(
                "file_name, format"
            ).eq("id", report_id).execute()
            
            if not response.data:
                return None
                
            file_name = response.data[0]["file_name"]
            
            return (content, file_name)
            
        except Exception as e:
            logger.error(f"Failed to get report for download: {e}")
            return None

# Create singleton instance
reporting_engine = RegulatoryReportingEngine()