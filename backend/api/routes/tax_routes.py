# backend/api/routes/tax_routes.py
# 🎯 Nigerian Tax Intelligence API - User-Facing Endpoints

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from backend.dependencies import get_current_user, get_supabase_client
from backend.services.tax_intelligence_service import TaxIntelligenceService
from backend.services.database_service import DatabaseService
from backend.services.compliance_service import ComplianceService
from backend.services.audit_service import AuditService
from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tax", tags=["Tax Intelligence"])


# ============================================
# PYDANTIC MODELS
# ============================================

class TaxCalculationRequest(BaseModel):
    scenario_data: Optional[Dict[str, Any]] = None
    tax_year: Optional[int] = None


class TaxScenarioRequest(BaseModel):
    scenario_name: str
    scenario_data: Dict[str, Any]
    save_scenario: bool = True


class PenaltyEstimationRequest(BaseModel):
    violation_types: List[str]
    tax_liability: Optional[float] = None


# ============================================
# DEPENDENCY INJECTION
# ============================================

def get_tax_intelligence_service(
    supabase=Depends(get_supabase_client)
) -> TaxIntelligenceService:
    """Initialize Tax Intelligence Service with dependencies"""
    settings = get_settings()
    db = DatabaseService(supabase)
    compliance = ComplianceService(settings, db, None, None)
    audit = AuditService(supabase)
    
    return TaxIntelligenceService(settings, db, compliance, audit)


# ============================================
# ENDPOINTS
# ============================================

@router.post("/calculate")
async def calculate_tax_liability(
    request: TaxCalculationRequest = Body(...),
    current_user: Dict = Depends(get_current_user),
    tax_service: TaxIntelligenceService = Depends(get_tax_intelligence_service)
):
    """
    🎯 Calculate comprehensive tax liability
    
    Returns detailed breakdown of all applicable taxes, exemptions, and recommendations.
    """
    try:
        user_id = current_user['id']
        
        result = await tax_service.calculate_comprehensive_tax_liability(
            user_id=user_id,
            scenario_data=request.scenario_data,
            tax_year=request.tax_year
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Tax calculation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Tax calculation failed: {str(e)}")


@router.get("/exemptions")
async def get_qualified_exemptions(
    current_user: Dict = Depends(get_current_user),
    tax_service: TaxIntelligenceService = Depends(get_tax_intelligence_service)
):
    """
    🎯 Get tax exemptions user qualifies for
    
    Returns list of exemptions with estimated savings and required documents.
    """
    try:
        user_id = current_user['id']
        
        exemptions = await tax_service.qualify_exemptions(user_id)
        
        total_savings = sum(e['estimated_savings'] for e in exemptions)
        
        return {
            "success": True,
            "exemptions": exemptions,
            "total_count": len(exemptions),
            "total_estimated_savings": total_savings
        }
        
    except Exception as e:
        logger.error(f"Exemption qualification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Exemption check failed: {str(e)}")


@router.post("/scenario/model")
async def model_tax_scenario(
    request: TaxScenarioRequest = Body(...),
    current_user: Dict = Depends(get_current_user),
    tax_service: TaxIntelligenceService = Depends(get_tax_intelligence_service)
):
    """
    🎯 Model "what-if" tax scenario
    
    Allows users to explore different scenarios and compare with baseline.
    """
    try:
        user_id = current_user['id']
        
        result = await tax_service.model_tax_scenario(
            user_id=user_id,
            scenario_name=request.scenario_name,
            scenario_data=request.scenario_data,
            save_scenario=request.save_scenario
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Scenario modeling failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scenario modeling failed: {str(e)}")


@router.post("/penalties/estimate")
async def estimate_penalties(
    request: PenaltyEstimationRequest = Body(...),
    current_user: Dict = Depends(get_current_user),
    tax_service: TaxIntelligenceService = Depends(get_tax_intelligence_service)
):
    """
    🎯 Estimate penalties for non-compliance
    
    Calculates potential penalties based on violation types.
    """
    try:
        user_id = current_user['id']
        
        result = await tax_service.estimate_penalties(
            user_id=user_id,
            violation_types=request.violation_types,
            tax_liability=request.tax_liability
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Penalty estimation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Penalty estimation failed: {str(e)}")


@router.get("/scenarios/history")
async def get_scenario_history(
    limit: int = 10,
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """Get user's saved tax scenarios"""
    try:
        user_id = current_user['id']
        
        result = await supabase.from_("tax_scenarios")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return {
            "success": True,
            "scenarios": result.data or []
        }
        
    except Exception as e:
        logger.error(f"Scenario history fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calculations/history")
async def get_calculation_history(
    tax_year: Optional[int] = None,
    limit: int = 10,
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """Get user's tax calculation history"""
    try:
        user_id = current_user['id']
        
        query = supabase.from_("tax_calculations").select("*").eq("user_id", user_id)
        
        if tax_year:
            query = query.eq("tax_year", tax_year)
        
        result = await query.order("created_at", desc=True).limit(limit).execute()
        
        return {
            "success": True,
            "calculations": result.data or []
        }
        
    except Exception as e:
        logger.error(f"Calculation history fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deadlines")
async def get_tax_deadlines(
    upcoming: bool = True,
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """Get tax deadlines applicable to user"""
    try:
        user_id = current_user['id']
        
        query = supabase.from_("user_tax_deadlines")\
            .select("*, tax_deadlines(*)")\
            .eq("user_id", user_id)
        
        if upcoming:
            from datetime import date
            query = query.gte("personalized_due_date", date.today().isoformat())
        
        result = await query.order("personalized_due_date").execute()
        
        return {
            "success": True,
            "deadlines": result.data or []
        }
        
    except Exception as e:
        logger.error(f"Deadlines fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))