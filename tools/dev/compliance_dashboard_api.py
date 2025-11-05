"""
Seamount.io Compliance Dashboard API
Real-time AML/KYC monitoring, reporting, and regulatory compliance
File: /backend/api/compliance_dashboard.py
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# Import custom modules
from backend.audit_logging import AuditEventType, audit_logger
from backend.continuous_monitoring import MonitoringSeverity, monitoring_service
from backend.regulatory_reports import ReportFormat, ReportType, reporting_engine
from backend.user_verification import user_verification_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class UpdateAlertRequest(BaseModel):
    status: str = Field(..., description="New alert status")
    notes: Optional[str] = Field(None, description="Optional notes")
    priority: Optional[str] = Field("normal", description="Priority level")

class GenerateReportRequest(BaseModel):
    report_type: str = Field(..., description="Type of report to generate")
    country_code: str = Field(..., description="Country code for report")
    start_date: str = Field(..., description="Start date (ISO format)")
    end_date: str = Field(..., description="End date (ISO format)")
    format: str = Field("json", description="Output format")

class UserActionRequest(BaseModel):
    action: str = Field(..., description="Action to take")
    reason: str = Field(..., description="Reason for action")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")

class ComplianceMetrics(BaseModel):
    total_alerts: int
    pending_reviews: int
    false_positives: int
    blocked_transactions: int
    compliance_score: float
    risk_distribution: Dict[str, int]

# Enhanced Compliance Service
class ComplianceService:
    def __init__(self):
        self.alert_thresholds = {
            "high_value_tx": 10000,
            "velocity_limit": 50000,
            "suspicious_pattern": 0.8,
            "cross_border_limit": 5000,
            "daily_tx_limit": 100000
        }
        self.risk_weights = {
            "transaction_amount": 0.3,
            "frequency": 0.25,
            "geographic": 0.2,
            "behavioral": 0.25
        }
        self.initialized = False

    async def initialize(self):
        """Initialize compliance service with retry logic"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Initialize monitoring connections
                await monitoring_service.initialize()
                await audit_logger.initialize()
                await reporting_engine.initialize()
                
                self.initialized = True
                logger.info("Compliance service initialized successfully")
                return
                
            except Exception as e:
                logger.warning(f"Initialization attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error("Failed to initialize compliance service after all retries")
                    raise

    async def get_enhanced_alerts(self, 
                                 status: Optional[str] = None,
                                 severity: Optional[str] = None,
                                 limit: int = 50,
                                 offset: int = 0) -> List[Dict]:
        """Get alerts with enhanced filtering and risk scoring"""
        try:
            base_alerts = await monitoring_service.get_alerts(
                status=status,
                severity=severity,
                limit=limit,
                offset=offset
            )
            
            # Enhance alerts with additional context
            enhanced_alerts = []
            for alert in base_alerts:
                # Add risk score calculation
                risk_score = await self._calculate_alert_risk(alert)
                alert["risk_score"] = risk_score
                alert["risk_level"] = self._get_risk_level(risk_score)
                
                # Add user context if available
                if alert.get("user_id"):
                    user_context = await self._get_user_context(alert["user_id"])
                    alert["user_context"] = user_context
                
                enhanced_alerts.append(alert)
            
            return enhanced_alerts
            
        except Exception as e:
            logger.error(f"Enhanced alerts retrieval failed: {e}")
            raise

    async def _calculate_alert_risk(self, alert: Dict) -> float:
        """Calculate comprehensive risk score for alert"""
        risk_score = 0.0
        
        # Amount-based risk
        amount = alert.get("amount", 0)
        if amount > self.alert_thresholds["high_value_tx"]:
            risk_score += 0.3
        
        # Frequency-based risk
        frequency_score = alert.get("frequency_score", 0)
        risk_score += frequency_score * self.risk_weights["frequency"]
        
        # Geographic risk
        country_risk = alert.get("country_risk", 0)
        risk_score += country_risk * self.risk_weights["geographic"]
        
        # Behavioral patterns
        behavior_score = alert.get("behavior_score", 0)
        risk_score += behavior_score * self.risk_weights["behavioral"]
        
        return min(risk_score, 1.0)

    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level"""
        if risk_score >= 0.8:
            return "critical"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        else:
            return "low"

    async def _get_user_context(self, user_id: str) -> Dict:
        """Get user context for alert enhancement"""
        try:
            # Get user profile
            user_response = await user_verification_manager.supabase.table("user_profiles").select(
                "id, first_name, last_name, country_code, kyc_level, kyc_verified, risk_score"
            ).eq("id", user_id).execute()
            
            if user_response.data:
                return user_response.data[0]
            
            return {}
            
        except Exception as e:
            logger.warning(f"Failed to get user context for {user_id}: {e}")
            return {}

    async def get_compliance_metrics(self, country_code: Optional[str] = None) -> Dict:
        """Get comprehensive compliance metrics"""
        try:
            # Get alert statistics
            alerts = await self.get_enhanced_alerts(limit=1000)
            
            # Filter by country if specified
            if country_code:
                alerts = [a for a in alerts if a.get("country_code") == country_code]
            
            # Calculate metrics
            total_alerts = len(alerts)
            pending_reviews = len([a for a in alerts if a.get("status") == "pending"])
            false_positives = len([a for a in alerts if a.get("status") == "false_positive"])
            blocked_transactions = len([a for a in alerts if a.get("status") == "blocked"])
            
            # Risk distribution
            risk_distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
            for alert in alerts:
                risk_level = alert.get("risk_level", "low")
                if risk_level in risk_distribution:
                    risk_distribution[risk_level] += 1
            
            # Compliance score calculation
            if total_alerts > 0:
                compliance_score = max(0, 1 - (false_positives / total_alerts) * 0.5)
            else:
                compliance_score = 1.0
            
            return {
                "total_alerts": total_alerts,
                "pending_reviews": pending_reviews,
                "false_positives": false_positives,
                "blocked_transactions": blocked_transactions,
                "compliance_score": compliance_score,
                "risk_distribution": risk_distribution,
                "country_code": country_code,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Compliance metrics calculation failed: {e}")
            raise

# Initialize service
compliance_service = ComplianceService()

# Initialize router
router = APIRouter(
    prefix="/api/v1/compliance",
    tags=["Compliance"],
    responses={404: {"description": "Not found"}},
)

# Authentication dependencies
async def get_compliance_officer(request: Request) -> Dict:
    """Get compliance officer from request context"""
    # TODO: Implement actual authentication
    # For now, return mock officer
    return {
        "id": "compliance_officer_1",
        "name": "Compliance Officer",
        "role": "compliance",
        "permissions": ["view_alerts", "update_alerts", "generate_reports", "manage_users"]
    }

async def ensure_compliance_officer(user: Dict) -> Dict:
    """Ensure user has compliance officer role"""
    if user.get("role") != "compliance":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compliance officer role required"
        )
    return user

# Dashboard endpoints
@router.get("/dashboard")
async def get_dashboard(
    country_code: Optional[str] = Query(None, description="Filter by country"),
    officer: Dict = Depends(get_compliance_officer)
):
    """Get comprehensive compliance dashboard overview"""
    await ensure_compliance_officer(officer)
    
    try:
        # Get comprehensive metrics
        metrics = await compliance_service.get_compliance_metrics(country_code)
        
        # Get recent alerts
        recent_alerts = await compliance_service.get_enhanced_alerts(limit=10)
        
        # Get KYC statistics
        kyc_query = user_verification_manager.supabase.table("user_profiles").select(
            "kyc_level, kyc_verified, country_code"
        )
        if country_code:
            kyc_query = kyc_query.eq("country_code", country_code)
        
        kyc_response = await kyc_query.execute()
        kyc_data = kyc_response.data or []
        
        # Calculate KYC stats
        kyc_stats = {
            "total_users": len(kyc_data),
            "verified": len([u for u in kyc_data if u.get("kyc_verified")]),
            "pending": len([u for u in kyc_data if not u.get("kyc_verified")]),
            "by_level": {"0": 0, "1": 0, "2": 0, "3": 0}
        }
        
        for user in kyc_data:
            level = str(user.get("kyc_level", 0))
            if level in kyc_stats["by_level"]:
                kyc_stats["by_level"][level] += 1
        
        # Get recent reports
        recent_reports = await reporting_engine.get_reports(limit=5)
        
        # Log dashboard access
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "compliance_dashboard_access",
                "country_filter": country_code
            },
            severity="info"
        )
        
        return {
            "status": "success",
            "dashboard": {
                "metrics": metrics,
                "recent_alerts": recent_alerts,
                "kyc_stats": kyc_stats,
                "recent_reports": recent_reports,
                "country_code": country_code,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Dashboard retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

# Alert management endpoints
@router.get("/alerts")
async def get_alerts(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    country_code: Optional[str] = Query(None, description="Filter by country"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    officer: Dict = Depends(get_compliance_officer)
):
    """Get alerts with enhanced filtering"""
    await ensure_compliance_officer(officer)
    
    try:
        alerts = await compliance_service.get_enhanced_alerts(
            status=status,
            severity=severity,
            limit=limit,
            offset=offset
        )
        
        # Apply additional filters
        if risk_level:
            alerts = [a for a in alerts if a.get("risk_level") == risk_level]
        
        if country_code:
            alerts = [a for a in alerts if a.get("country_code") == country_code]
        
        # Log access
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "view_alerts",
                "filters": {
                    "status": status,
                    "severity": severity,
                    "risk_level": risk_level,
                    "country_code": country_code
                },
                "count": len(alerts)
            },
            severity="info"
        )
        
        return {
            "success": True,
            "alerts": alerts,
            "count": len(alerts),
            "filters_applied": {
                "status": status,
                "severity": severity,
                "risk_level": risk_level,
                "country_code": country_code
            }
        }
        
    except Exception as e:
        logger.error(f"Alerts retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}")
async def update_alert_status(
    alert_id: str,
    update: UpdateAlertRequest,
    officer: Dict = Depends(get_compliance_officer)
):
    """Update alert status with enhanced tracking"""
    await ensure_compliance_officer(officer)
    
    try:
        # Validate alert exists
        existing_alert = await monitoring_service.get_alert(alert_id)
        if not existing_alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Update alert
        success = await monitoring_service.update_alert_status(
            alert_id=alert_id,
            status=update.status,
            notes=update.notes,
            updated_by=officer["id"]
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Alert update failed")
        
        # Log audit event
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "update_alert",
                "alert_id": alert_id,
                "previous_status": existing_alert.get("status"),
                "new_status": update.status,
                "notes": update.notes,
                "priority": update.priority
            },
            resource_id=alert_id,
            severity="info",
            critical=update.status in ["resolved", "blocked"]
        )
        
        return {
            "success": True,
            "alert_id": alert_id,
            "status": update.status,
            "updated_by": officer["id"],
            "updated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Alert update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts/{alert_id}")
async def get_alert_details(
    alert_id: str,
    officer: Dict = Depends(get_compliance_officer)
):
    """Get detailed alert information"""
    await ensure_compliance_officer(officer)
    
    try:
        alert = await monitoring_service.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Enhance with risk analysis
        risk_score = await compliance_service._calculate_alert_risk(alert)
        alert["risk_score"] = risk_score
        alert["risk_level"] = compliance_service._get_risk_level(risk_score)
        
        # Get related transactions
        if alert.get("user_id"):
            tx_response = await user_verification_manager.supabase.table("payment_transactions").select(
                "*"
            ).eq("user_id", alert["user_id"]).order("created_at", {"ascending": False}).limit(10).execute()
            
            related_transactions = tx_response.data or []
            alert["related_transactions"] = related_transactions
        
        # Log access
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "view_alert_details",
                "alert_id": alert_id,
                "risk_level": alert.get("risk_level")
            },
            resource_id=alert_id,
            severity="info"
        )
        
        return {
            "success": True,
            "alert": alert
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Alert details retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# User management endpoints
@router.get("/users")
async def get_users_for_review(
    status: Optional[str] = Query(None, description="Filter by verification status"),
    country_code: Optional[str] = Query(None, description="Filter by country"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    officer: Dict = Depends(get_compliance_officer)
):
    """Get users for compliance review"""
    await ensure_compliance_officer(officer)
    
    try:
        # Build query
        query = user_verification_manager.supabase.table("user_profiles").select(
            "id, first_name, last_name, country_code, kyc_level, kyc_verified, risk_score, created_at"
        )
        
        if status == "verified":
            query = query.eq("kyc_verified", True)
        elif status == "unverified":
            query = query.eq("kyc_verified", False)
        
        if country_code:
            query = query.eq("country_code", country_code)
        
        if risk_level:
            # This would need to be implemented based on your risk scoring system
            pass
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        # Execute query
        response = await query.execute()
        users = response.data or []
        
        # Enhance with additional data
        for user in users:
            # Get recent alerts
            user_alerts = await monitoring_service.get_alerts(user_id=user["id"])
            user["alert_count"] = len(user_alerts)
            
            # Get transaction volume
            tx_response = await user_verification_manager.supabase.table("payment_transactions").select(
                "amount"
            ).eq("user_id", user["id"]).execute()
            
            transactions = tx_response.data or []
            user["total_volume"] = sum(tx.get("amount", 0) for tx in transactions)
            user["transaction_count"] = len(transactions)
        
        # Log access
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "view_users",
                "filters": {
                    "status": status,
                    "country_code": country_code,
                    "risk_level": risk_level
                },
                "count": len(users)
            },
            severity="info"
        )
        
        return {
            "success": True,
            "users": users,
            "count": len(users),
            "filters_applied": {
                "status": status,
                "country_code": country_code,
                "risk_level": risk_level
            }
        }
        
    except Exception as e:
        logger.error(f"Users retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    officer: Dict = Depends(get_compliance_officer)
):
    """Get comprehensive user details for compliance review"""
    await ensure_compliance_officer(officer)
    
    try:
        # Get user profile
        user_response = await user_verification_manager.supabase.table("user_profiles").select(
            "*"
        ).eq("id", user_id).execute()
        
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_response.data[0]
        
        # Get user transactions
        tx_response = await user_verification_manager.supabase.table("payment_transactions").select(
            "*"
        ).eq("user_id", user_id).order("created_at", {"ascending": False}).limit(100).execute()
        
        transactions = tx_response.data or []
        
        # Get user alerts
        user_alerts = await monitoring_service.get_alerts(user_id=user_id)
        
        # Get verification history
        verify_response = await user_verification_manager.supabase.table("kyc_verification_history").select(
            "*"
        ).eq("user_id", user_id).order("created_at", {"ascending": False}).execute()
        
        verification_history = verify_response.data or []
        
        # Calculate comprehensive risk score
        risk_data = await monitoring_service.get_user_risk_score(user_id)
        
        # Calculate transaction analytics
        tx_analytics = {
            "total_volume": sum(tx.get("amount", 0) for tx in transactions),
            "transaction_count": len(transactions),
            "avg_transaction": sum(tx.get("amount", 0) for tx in transactions) / len(transactions) if transactions else 0,
            "countries": list(set(tx.get("destination_country") for tx in transactions if tx.get("destination_country"))),
            "frequency": len(transactions) / max(1, (datetime.utcnow() - datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))).days)
        }
        
        # Log access
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "view_user_details",
                "subject_user_id": user_id,
                "risk_level": risk_data.get("risk_level")
            },
            resource_id=user_id,
            severity="info"
        )
        
        return {
            "success": True,
            "user": user,
            "risk": risk_data,
            "transactions": {
                "analytics": tx_analytics,
                "recent": transactions[:10]
            },
            "alerts": {
                "count": len(user_alerts),
                "recent": user_alerts[:10]
            },
            "verification": {
                "history": verification_history,
                "current_level": user.get("kyc_level", 0),
                "verified": user.get("kyc_verified", False),
                "last_verified": user.get("kyc_last_verified")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User details retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/action")
async def take_user_action(
    user_id: str,
    action: UserActionRequest,
    officer: Dict = Depends(get_compliance_officer)
):
    """Take compliance action on user account"""
    await ensure_compliance_officer(officer)
    
    try:
        # Get current user state
        user_response = await user_verification_manager.supabase.table("user_profiles").select(
            "*"
        ).eq("id", user_id).execute()
        
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_response.data[0]
        result = {"success": False}
        
        if action.action == "upgrade_kyc":
            new_level = action.details.get("new_level", user.get("kyc_level", 0) + 1)
            
            upgrade_result = await user_verification_manager.upgrade_kyc_level(
                user_id=user_id,
                new_level=new_level,
                admin_id=officer["id"],
                reason=action.reason
            )
            
            if upgrade_result.get("success"):
                result = {
                    "success": True,
                    "action": "upgrade_kyc",
                    "previous_level": user.get("kyc_level", 0),
                    "new_level": new_level
                }
        
        elif action.action == "suspend":
            await user_verification_manager.supabase.table("user_profiles").update({
                "is_active": False,
                "suspended_reason": action.reason,
                "suspended_at": datetime.utcnow().isoformat(),
                "suspended_by": officer["id"]
            }).eq("id", user_id).execute()
            
            result = {
                "success": True,
                "action": "suspend",
                "reason": action.reason
            }
        
        elif action.action == "reactivate":
            await user_verification_manager.supabase.table("user_profiles").update({
                "is_active": True,
                "suspended_reason": None,
                "suspended_at": None,
                "suspended_by": None,
                "reactivated_at": datetime.utcnow().isoformat(),
                "reactivated_by": officer["id"],
                "reactivated_reason": action.reason
            }).eq("id", user_id).execute()
            
            result = {
                "success": True,
                "action": "reactivate",
                "reason": action.reason
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported action: {action.action}")
        
        # Log audit event
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": f"user_{action.action}",
                "subject_user_id": user_id,
                "reason": action.reason,
                "details": action.details,
                "result": result
            },
            resource_id=user_id,
            severity="warning",
            critical=True
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User action failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Reporting endpoints
@router.post("/reports")
async def generate_report(
    report_request: GenerateReportRequest,
    officer: Dict = Depends(get_compliance_officer)
):
    """Generate regulatory compliance report"""
    await ensure_compliance_officer(officer)
    
    try:
        result = await reporting_engine.generate_report(
            report_type=report_request.report_type,
            country_code=report_request.country_code,
            start_date=report_request.start_date,
            end_date=report_request.end_date,
            format=report_request.format,
            generated_by=officer["id"]
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Log audit event
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "generate_report",
                "report_type": report_request.report_type,
                "country_code": report_request.country_code,
                "date_range": f"{report_request.start_date} to {report_request.end_date}",
                "format": report_request.format
            },
            resource_id=result.get("id"),
            severity="info"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports")
async def list_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    country_code: Optional[str] = Query(None, description="Filter by country"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    officer: Dict = Depends(get_compliance_officer)
):
    """List available compliance reports"""
    await ensure_compliance_officer(officer)
    
    try:
        reports = await reporting_engine.get_reports(
            report_type=report_type,
            country_code=country_code,
            limit=limit,
            offset=offset
        )
        
        # Log access
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "list_reports",
                "filters": {
                    "report_type": report_type,
                    "country_code": country_code
                },
                "count": len(reports)
            },
            severity="info"
        )
        
        return {
            "success": True,
            "reports": reports,
            "count": len(reports)
        }
        
    except Exception as e:
        logger.error(f"Reports listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    officer: Dict = Depends(get_compliance_officer)
):
    """Get compliance report content"""
    await ensure_compliance_officer(officer)
    
    try:
        report_content = await reporting_engine.get_report_content(report_id)
        
        if not report_content:
            raise HTTPException(status_code=404, detail="Report not found")
        
# Log access
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "view_report",
                "report_id": report_id,
                "report_type": report_content.get("report_type"),
                "country_code": report_content.get("country_code")
            },
            resource_id=report_id,
            severity="info"
        )
        
        return {
            "success": True,
            "report": report_content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    officer: Dict = Depends(get_compliance_officer)
):
    """Download compliance report file"""
    await ensure_compliance_officer(officer)
    
    try:
        # Get report metadata
        report_info = await reporting_engine.get_report_info(report_id)
        
        if not report_info:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get file path
        file_path = report_info.get("file_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Report file not found")
        
        # Log download
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "download_report",
                "report_id": report_id,
                "file_path": file_path
            },
            resource_id=report_id,
            severity="info"
        )
        
        # Return file response
        return FileResponse(
            path=file_path,
            filename=f"compliance_report_{report_id}_{datetime.now().strftime('%Y%m%d')}.{report_info.get('format', 'json')}",
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Advanced analytics endpoints
@router.get("/analytics/trends")
async def get_compliance_trends(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    country_code: Optional[str] = Query(None, description="Filter by country"),
    officer: Dict = Depends(get_compliance_officer)
):
    """Get compliance trends and analytics"""
    await ensure_compliance_officer(officer)
    
    try:
        # Calculate date range
        period_days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        days = period_days.get(period, 30)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get trend data
        trends = await monitoring_service.get_compliance_trends(
            start_date=start_date,
            end_date=end_date,
            country_code=country_code
        )
        
        # Calculate key metrics
        metrics = {
            "alert_volume_trend": trends.get("alert_volume", []),
            "false_positive_rate": trends.get("false_positive_rate", 0),
            "resolution_time": trends.get("avg_resolution_time", 0),
            "compliance_score_trend": trends.get("compliance_score", []),
            "risk_distribution": trends.get("risk_distribution", {}),
            "geographic_distribution": trends.get("geographic_distribution", {}),
            "period": period,
            "country_code": country_code
        }
        
        # Log access
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "view_compliance_trends",
                "period": period,
                "country_code": country_code
            },
            severity="info"
        )
        
        return {
            "success": True,
            "trends": metrics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Compliance trends retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/risk-assessment")
async def get_risk_assessment(
    user_id: Optional[str] = Query(None, description="Assess specific user"),
    country_code: Optional[str] = Query(None, description="Country-specific assessment"),
    officer: Dict = Depends(get_compliance_officer)
):
    """Get comprehensive risk assessment"""
    await ensure_compliance_officer(officer)
    
    try:
        if user_id:
            # Individual user risk assessment
            risk_data = await monitoring_service.get_comprehensive_user_risk(user_id)
            
            # Get user context
            user_context = await compliance_service._get_user_context(user_id)
            
            assessment = {
                "user_id": user_id,
                "risk_score": risk_data.get("risk_score", 0),
                "risk_level": risk_data.get("risk_level", "low"),
                "risk_factors": risk_data.get("risk_factors", []),
                "recommendations": risk_data.get("recommendations", []),
                "user_context": user_context,
                "last_updated": datetime.utcnow().isoformat()
            }
        else:
            # marketData-wide risk assessment
            assessment = await monitoring_service.get_marketData_risk_assessment(
                country_code=country_code
            )
        
        # Log access
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "view_risk_assessment",
                "subject_user_id": user_id,
                "country_code": country_code
            },
            resource_id=user_id,
            severity="info"
        )
        
        return {
            "success": True,
            "risk_assessment": assessment
        }
        
    except Exception as e:
        logger.error(f"Risk assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Real-time monitoring endpoints
@router.get("/monitoring/live-feed")
async def get_live_compliance_feed(
    officer: Dict = Depends(get_compliance_officer)
):
    """Get real-time compliance event stream"""
    await ensure_compliance_officer(officer)
    
    async def event_generator():
        """Generator for Server-Sent Events"""
        last_event_id = 0
        
        while True:
            try:
                # Get new events since last check
                events = await monitoring_service.get_events_since(last_event_id)
                
                for event in events:
                    # Format as SSE
                    yield f"data: {json.dumps(event)}\n\n"
                    last_event_id = event.get("id", last_event_id)
                
                # Wait before next check
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Live feed error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
    
    # Log access
    await audit_logger.log_event(
        event_type=AuditEventType.ADMIN_ACTION,
        user_id=officer["id"],
        details={"action": "access_live_feed"},
        severity="info"
    )
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@router.get("/monitoring/system-health")
async def get_system_health(
    officer: Dict = Depends(get_compliance_officer)
):
    """Get compliance system health status"""
    await ensure_compliance_officer(officer)
    
    try:
        # Check service health
        health_status = {
            "monitoring_service": await monitoring_service.health_check(),
            "audit_logger": await audit_logger.health_check(),
            "reporting_engine": await reporting_engine.health_check(),
            "database": await user_verification_manager.health_check(),
            "compliance_service": compliance_service.initialized
        }
        
        # Calculate overall health
        healthy_services = sum(1 for status in health_status.values() if status)
        total_services = len(health_status)
        overall_health = healthy_services / total_services
        
        # Get system metrics
        system_metrics = await monitoring_service.get_system_metrics()
        
        health_report = {
            "overall_health": overall_health,
            "status": "healthy" if overall_health > 0.8 else "degraded" if overall_health > 0.5 else "unhealthy",
            "services": health_status,
            "metrics": system_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log health check
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "system_health_check",
                "overall_health": overall_health,
                "status": health_report["status"]
            },
            severity="info"
        )
        
        return {
            "success": True,
            "health": health_report
        }
        
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bulk operations endpoints
@router.post("/bulk/alerts")
async def bulk_update_alerts(
    alert_ids: List[str] = Body(..., description="List of alert IDs"),
    action: str = Body(..., description="Action to perform"),
    notes: Optional[str] = Body(None, description="Optional notes"),
    officer: Dict = Depends(get_compliance_officer)
):
    """Bulk update multiple alerts"""
    await ensure_compliance_officer(officer)
    
    try:
        results = []
        errors = []
        
        for alert_id in alert_ids:
            try:
                # Update individual alert
                success = await monitoring_service.update_alert_status(
                    alert_id=alert_id,
                    status=action,
                    notes=notes,
                    updated_by=officer["id"]
                )
                
                if success:
                    results.append({"alert_id": alert_id, "status": "success"})
                else:
                    errors.append({"alert_id": alert_id, "error": "Update failed"})
                    
            except Exception as e:
                errors.append({"alert_id": alert_id, "error": str(e)})
        
        # Log bulk operation
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "bulk_update_alerts",
                "alert_count": len(alert_ids),
                "bulk_action": action,
                "success_count": len(results),
                "error_count": len(errors),
                "notes": notes
            },
            severity="warning",
            critical=True
        )
        
        return {
            "success": True,
            "results": results,
            "errors": errors,
            "summary": {
                "total": len(alert_ids),
                "successful": len(results),
                "failed": len(errors)
            }
        }
        
    except Exception as e:
        logger.error(f"Bulk alert update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Configuration endpoints
@router.get("/config")
async def get_compliance_config(
    officer: Dict = Depends(get_compliance_officer)
):
    """Get compliance configuration"""
    await ensure_compliance_officer(officer)
    
    try:
        config = {
            "alert_thresholds": compliance_service.alert_thresholds,
            "risk_weights": compliance_service.risk_weights,
            "supported_countries": await reporting_engine.get_supported_countries(),
            "report_types": await reporting_engine.get_report_types(),
            "kyc_levels": user_verification_manager.kyc_levels,
            "monitoring_intervals": await monitoring_service.get_monitoring_config()
        }
        
        # Log access
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={"action": "view_compliance_config"},
            severity="info"
        )
        
        return {
            "success": True,
            "config": config
        }
        
    except Exception as e:
        logger.error(f"Config retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config")
async def update_compliance_config(
    config_updates: Dict[str, Any] = Body(..., description="Configuration updates"),
    officer: Dict = Depends(get_compliance_officer)
):
    """Update compliance configuration"""
    await ensure_compliance_officer(officer)
    
    try:
        # Validate and apply configuration updates
        updated_fields = []
        
        if "alert_thresholds" in config_updates:
            compliance_service.alert_thresholds.update(config_updates["alert_thresholds"])
            updated_fields.append("alert_thresholds")
        
        if "risk_weights" in config_updates:
            compliance_service.risk_weights.update(config_updates["risk_weights"])
            updated_fields.append("risk_weights")
        
        if "monitoring_intervals" in config_updates:
            await monitoring_service.update_monitoring_config(config_updates["monitoring_intervals"])
            updated_fields.append("monitoring_intervals")
        
        # Log configuration change
        await audit_logger.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=officer["id"],
            details={
                "action": "update_compliance_config",
                "updated_fields": updated_fields,
                "changes": config_updates
            },
            severity="warning",
            critical=True
        )
        
        return {
            "success": True,
            "updated_fields": updated_fields,
            "message": "Configuration updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Startup event handler
@router.on_event("startup")
async def startup_event():
    """Initialize compliance service on startup"""
    try:
        await compliance_service.initialize()
        logger.info("Compliance dashboard API initialized successfully")
    except Exception as e:
        logger.error(f"Compliance dashboard startup failed: {e}")
        raise

# Error handlers
@router.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for compliance API"""
    logger.error(f"Unhandled exception in compliance API: {exc}")
    
    # Log error for audit
    try:
        await audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_ERROR,
            user_id="system",
            details={
                "error": str(exc),
                "endpoint": str(request.url),
                "method": request.method
            },
            severity="error",
            critical=True
        )
    except Exception as audit_error:
        logger.error(f"Failed to log audit event: {audit_error}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again or contact support."
        }
    )

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for compliance dashboard"""
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "compliance_dashboard",
            "version": "1.0.0"
        }
        
        # Check if service is initialized
        if not compliance_service.initialized:
            health_status["status"] = "initializing"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# Export router
__all__ = ["router", "compliance_service"]
