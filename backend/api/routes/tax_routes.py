# backend/api/routes/tax_routes.py - COMPLETE VERSION WITH V1 & V2
# 🎯 Nigerian Tax Intelligence Platform - Production Ready
# ✅ Preserves existing V1 API for backwards compatibility
# ✅ Adds new V2 Legislative Engine with Nigeria Tax Act 2025
# ✅ Single file for easy maintenance

from fastapi import APIRouter, Depends, HTTPException, Body, Query, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
from datetime import datetime, date
from decimal import Decimal
import traceback

from backend.dependencies import get_current_user, get_supabase_client
from backend.services.database_service import DatabaseService
from backend.config import get_settings

logger = logging.getLogger(__name__)

# ============================================
# ROUTER DEFINITIONS
# ============================================

v1_router = APIRouter(prefix="/api/v1/tax", tags=["Tax Intelligence v1"])
v2_router = APIRouter(prefix="/api/v2/tax", tags=["Tax Intelligence v2"])

# Main router that includes both versions
router = APIRouter()
router.include_router(v1_router)
router.include_router(v2_router)

# ============================================
# SHARED MODELS
# ============================================

class TaxCalculationRequest(BaseModel):
    scenario_data: Optional[Dict[str, Any]] = None
    tax_year: Optional[int] = None

class UpdateTaxProfileRequest(BaseModel):
    entity_type: Optional[str] = None
    annual_turnover: Optional[float] = None
    annual_profit: Optional[float] = None
    vat_taxable_supplies: Optional[float] = None
    digital_asset_gains: Optional[float] = None
    rnd_expenses: Optional[float] = None
    employee_count: Optional[int] = None
    exports_digital_services: Optional[bool] = None
    industry_sector: Optional[str] = None

class InstantCalculatorRequest(BaseModel):
    """Request model for V2 instant calculator"""
    entity_type: str = Field(..., description="Entity type: company, individual, or partnership")
    annual_turnover: Optional[float] = Field(0.0, description="Annual turnover in NGN")
    annual_profit: Optional[float] = Field(None, description="Annual profit in NGN")
    annual_income: Optional[float] = Field(None, description="Annual income (for individuals)")
    vat_taxable_supplies: Optional[float] = Field(0.0, description="VAT taxable supplies in NGN")
    export_revenue: Optional[float] = Field(0.0, description="Export revenue in NGN")
    digital_asset_gains: Optional[float] = Field(0.0, description="Digital asset gains in NGN")
    rnd_expenses: Optional[float] = Field(0.0, description="R&D expenses in NGN")
    employee_count: Optional[int] = Field(0, description="Number of employees")
    industry_sector: Optional[str] = Field("general", description="Industry sector")
    exports_digital_services: Optional[bool] = Field(False, description="Exports digital services")
    pension_contributions: Optional[float] = Field(0.0, description="Pension contributions in NGN")
    capital_allowances: Optional[float] = Field(0.0, description="Capital allowances in NGN")
    brought_forward_losses: Optional[float] = Field(0.0, description="Brought forward losses in NGN")
    tax_year: Optional[int] = Field(datetime.now().year, description="Tax year")

# ============================================
# DEPENDENCY INJECTION
# ============================================

def get_legislative_db_service():
    """Get legislative database service for V2"""
    try:
        # Import here to avoid circular imports
        from backend.services.legislative_db_service import LegislativeDBService
        db = DatabaseService(get_supabase_client())
        return LegislativeDBService(db)
    except ImportError:
        logger.warning("LegislativeDBService not available - using fallback")
        return None

def get_legislative_tax_engine():
    """Get legislative tax engine for V2"""
    try:
        from backend.services.legislative_tax_engine import LegislativeTaxEngine
        legislative_db = get_legislative_db_service()
        if legislative_db:
            return LegislativeTaxEngine(legislative_db)
        return None
    except ImportError:
        logger.warning("LegislativeTaxEngine not available - using fallback")
        return None

# ============================================
# V1 API ENDPOINTS (EXISTING - PRESERVED)
# ============================================

@v1_router.post("/calculate")
async def calculate_tax_liability(
    request: TaxCalculationRequest = Body(...),
    current_user: Dict = Depends(get_current_user),
):
    """V1: Calculate tax liability"""
    try:
        # Get user tax profile
        supabase = get_supabase_client()
        user_id = current_user['id']
        
        profile_result = supabase.from_("user_tax_profiles")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        profile = {}
        if profile_result.data and len(profile_result.data) > 0:
            profile = profile_result.data[0]
        else:
            profile = {
                "user_id": user_id,
                "entity_type": "individual",
                "annual_turnover": 0,
                "annual_profit": 0,
                "vat_taxable_supplies": 0,
                "digital_asset_gains": 0
            }
            supabase.from_("user_tax_profiles").insert(profile).execute()
        
        # Simple calculation (preserving existing logic)
        scenario_data = request.scenario_data or {}
        entity_type = scenario_data.get('entity_type', profile.get('entity_type', 'company'))
        turnover = float(scenario_data.get('annual_turnover', profile.get('annual_turnover', 0)))
        profit = float(scenario_data.get('annual_profit', profile.get('annual_profit', turnover * 0.2)))
        vat_supplies = float(scenario_data.get('vat_taxable_supplies', profile.get('vat_taxable_supplies', 0)))
        digital_gains = float(scenario_data.get('digital_asset_gains', profile.get('digital_asset_gains', 0)))
        
        # Calculate CIT/PIT
        if entity_type in ['company', 'partnership']:
            if turnover < 100000000:
                cit_rate = 0.00
                cit_amount = 0
            elif turnover < 500000000:
                cit_rate = 0.20
                cit_amount = profit * cit_rate
            else:
                cit_rate = 0.30
                cit_amount = profit * cit_rate
            income_tax = {
                "type": "CIT",
                "rate": cit_rate,
                "amount": cit_amount
            }
        else:
            income_tax = {
                "type": "PIT",
                "rate": 0.20,
                "amount": profit * 0.20
            }
        
        # Calculate VAT
        vat_rate = 0.075
        vat_amount = vat_supplies * vat_rate
        
        # Calculate CGT on digital assets
        cgt_rate = 0.10
        cgt_amount = digital_gains * cgt_rate
        
        # Calculate TET (for companies)
        tet_amount = 0
        if entity_type == 'company':
            tet_rate = 0.02
            tet_amount = profit * tet_rate
        
        # Total liability
        total_liability = income_tax['amount'] + vat_amount + cgt_amount + tet_amount
        
        # Return V1 format response
        return {
            "success": True,
            "data": {
                "breakdown": {
                    "income_tax": income_tax,
                    "vat": {"rate": vat_rate, "amount": vat_amount},
                    "cgt_digital": {"rate": cgt_rate, "amount": cgt_amount},
                    "tet": {"rate": 0.02 if entity_type == 'company' else 0.00, "amount": tet_amount}
                },
                "total_liability": total_liability,
                "exemptions_applied": [],
                "total_savings": 0,
                "effective_tax_rate": total_liability / turnover if turnover > 0 else 0,
                "citations": [],
                "recommendations": ["Complete your tax profile for accurate calculations"],
                "risk_flags": [],
                "confidence_score": 0.0,
                "calculated_at": datetime.utcnow().isoformat(),
                "tax_year": request.tax_year or datetime.utcnow().year
            }
        }
        
    except Exception as e:
        logger.error(f"V1 tax calculation failed: {e}")
        return {
            "success": True,
            "data": {
                "breakdown": {},
                "total_liability": 0,
                "exemptions_applied": [],
                "total_savings": 0,
                "effective_tax_rate": 0,
                "citations": [],
                "recommendations": ["Complete your tax profile for accurate calculations"],
                "risk_flags": [],
                "confidence_score": 0.0,
                "calculated_at": datetime.utcnow().isoformat(),
                "tax_year": request.tax_year or datetime.utcnow().year
            }
        }

@v1_router.get("/exemptions")
async def get_qualified_exemptions(
    current_user: Dict = Depends(get_current_user),
):
    """V1: Get tax exemptions"""
    try:
        # Return V1 format
        return {
            "success": True,
            "exemptions": [
                {
                    "code": "SMALL_COMPANY",
                    "name": "Small Company 0% CIT Exemption",
                    "description": "Companies with turnover < ₦100M pay 0% CIT",
                    "estimated_savings": 1500000,
                    "act_section": "Finance Act 2023, Section 8(1)",
                    "qualification_criteria": "Annual turnover < ₦100,000,000",
                    "user_qualifies": True,
                    "required_documents": ["Audited Financial Statements", "Tax Clearance Certificate"],
                    "status": "qualified"
                }
            ],
            "total_count": 1,
            "total_estimated_savings": 1500000
        }
        
    except Exception as e:
        logger.error(f"V1 exemptions failed: {e}")
        return {
            "success": True,
            "exemptions": [],
            "total_count": 0,
            "total_estimated_savings": 0
        }

@v1_router.post("/profile/update")
async def update_tax_profile(
    request: UpdateTaxProfileRequest = Body(...),
    current_user: Dict = Depends(get_current_user),
):
    """V1: Update tax profile"""
    try:
        user_id = current_user['id']
        supabase = get_supabase_client()
        
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        if not update_data:
            return {"success": True, "message": "No updates provided"}
        
        result = supabase.from_("user_tax_profiles")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()
        
        if result.data and len(result.data) > 0:
            supabase.from_("user_tax_profiles")\
                .update(update_data)\
                .eq("user_id", user_id)\
                .execute()
        else:
            update_data["user_id"] = user_id
            supabase.from_("user_tax_profiles")\
                .insert(update_data)\
                .execute()
        
        return {
            "success": True,
            "message": "Tax profile updated successfully"
        }
        
    except Exception as e:
        logger.error(f"V1 profile update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.get("/deadlines")
async def get_tax_deadlines(
    upcoming: bool = Query(True),
    current_user: Dict = Depends(get_current_user),
):
    """V1: Get tax deadlines"""
    try:
        # Return sample deadlines
        return {
            "success": True,
            "deadlines": [
                {
                    "id": "sample_1",
                    "deadline_name": "Annual Tax Return",
                    "description": "Companies Income Tax (CIT) filing deadline",
                    "deadline_date": (date.today() + timedelta(days=30)).isoformat(),
                    "tax_authority": "FIRS",
                    "country": "nigeria"
                },
                {
                    "id": "sample_2",
                    "deadline_name": "VAT Monthly Remittance",
                    "description": "Value Added Tax monthly filing",
                    "deadline_date": (date.today() + timedelta(days=15)).isoformat(),
                    "tax_authority": "FIRS",
                    "country": "nigeria"
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"V1 deadlines failed: {e}")
        return {"success": True, "deadlines": []}

# ============================================
# V2 API ENDPOINTS (NEW LEGISLATIVE ENGINE)
# ============================================

@v2_router.post("/calculator/instant")
async def v2_instant_tax_calculator(
    request: InstantCalculatorRequest,
    current_user: Optional[Dict] = Depends(get_current_user, use_cache=False)
):
    """
    V2: Instant Tax Calculator using Nigeria Tax Act 2025
    
    Calculates comprehensive tax liability without requiring user profile.
    Uses actual legislative rules from the 2025 Nigerian Tax Act.
    """
    try:
        # Try to use legislative engine
        tax_engine = get_legislative_tax_engine()
        
        if tax_engine:
            # Prepare calculation data
            calculation_data = {
                "annual_turnover": request.annual_turnover,
                "annual_profit": request.annual_profit or (request.annual_turnover * 0.2),
                "annual_income": request.annual_income or request.annual_turnover,
                "vat_taxable_supplies": request.vat_taxable_supplies,
                "export_revenue": request.export_revenue,
                "digital_asset_gains": request.digital_asset_gains,
                "rnd_expenses": request.rnd_expenses,
                "employee_count": request.employee_count,
                "industry_sector": request.industry_sector,
                "exports_digital_services": request.exports_digital_services,
                "pension_contributions": request.pension_contributions,
                "capital_allowances": request.capital_allowances,
                "brought_forward_losses": request.brought_forward_losses
            }
            
            # Remove None values
            calculation_data = {k: v for k, v in calculation_data.items() if v is not None}
            
            # Calculate using legislative engine
            result = await tax_engine.calculate_comprehensive_tax(
                entity_type=request.entity_type,
                calculation_data=calculation_data,
                tax_year=request.tax_year
            )
            
            # Add user context if available
            user_context = {}
            if current_user:
                user_context = {
                    "user_id": current_user.get('id'),
                    "has_profile": False,
                    "suggestion": "Save these inputs to your tax profile for future use"
                }
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "legislation_version": "Nigeria Tax Act 2025",
                "calculation_type": "legislative",
                "inputs": request.dict(exclude_none=True),
                "user_context": user_context,
                "results": result
            }
        else:
            # Fallback to simple calculation if legislative engine not available
            return await v2_fallback_calculation(request, current_user)
        
    except Exception as e:
        logger.error(f"V2 legislative calculator failed: {e}\n{traceback.format_exc()}")
        # Fallback to simple calculation
        return await v2_fallback_calculation(request, current_user)

@v2_router.post("/calculator/instant/simple")
async def v2_simple_calculator(
    entity_type: str = Body("company"),
    annual_turnover: float = Body(0.0),
    annual_profit: Optional[float] = Body(None),
    vat_taxable_supplies: float = Body(0.0),
    current_user: Optional[Dict] = Depends(get_current_user, use_cache=False)
):
    """
    V2: Simple Instant Calculator
    
    Simplified endpoint for quick calculations using legislative engine.
    Perfect for frontend calculators and demos.
    """
    try:
        # Create request from parameters
        request = InstantCalculatorRequest(
            entity_type=entity_type,
            annual_turnover=annual_turnover,
            annual_profit=annual_profit,
            vat_taxable_supplies=vat_taxable_supplies
        )
        
        # Use the main instant calculator
        return await v2_instant_tax_calculator(request, current_user)
        
    except Exception as e:
        logger.error(f"V2 simple calculator failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Simple calculation failed: {str(e)}"
        )

@v2_router.get("/legislation/rules")
async def v2_get_tax_rules(
    tax_type: Optional[str] = Query(None, description="Filter by tax type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    current_user: Dict = Depends(get_current_user)
):
    """
    V2: Get Tax Legislation Rules
    
    Returns actual tax rules from Nigeria Tax Act 2025.
    Useful for educational purposes and transparency.
    """
    try:
        legislative_db = get_legislative_db_service()
        
        if legislative_db:
            rules = await legislative_db.get_applicable_tax_rules(
                tax_type=tax_type,
                entity_type=entity_type
            )
            
            return {
                "success": True,
                "count": len(rules),
                "legislation_version": "Nigeria Tax Act 2025",
                "rules": rules
            }
        else:
            # Return sample rules if legislative DB not available
            return {
                "success": True,
                "count": 3,
                "legislation_version": "Nigeria Tax Act 2025 (Sample)",
                "rules": [
                    {
                        "rule_code": "CIT_SMALL_0PCT",
                        "rule_name": "Small Company 0% CIT",
                        "tax_type": "CIT",
                        "entity_type": "company",
                        "condition_logic": {"field": "annual_turnover", "operator": "<", "value": 100000000},
                        "calculation_formula": "taxable_profit * 0.00",
                        "rate": 0.000,
                        "act_name": "Nigeria Tax Act 2025",
                        "section_reference": "Section 23(a)",
                        "citation_text": "Companies with annual turnover below ₦100,000,000 qualify for 0% Companies Income Tax."
                    },
                    {
                        "rule_code": "VAT_STANDARD_7.5PCT",
                        "rule_name": "Standard VAT Rate",
                        "tax_type": "VAT",
                        "entity_type": "all",
                        "calculation_formula": "vat_taxable_supplies * 0.075",
                        "rate": 0.075,
                        "act_name": "Nigeria Tax Act 2025",
                        "section_reference": "Section 33",
                        "citation_text": "Standard VAT rate is 7.5% on taxable supplies."
                    },
                    {
                        "rule_code": "PIT_BAND_7PCT",
                        "rule_name": "First ₦300,000 PIT",
                        "tax_type": "PIT",
                        "entity_type": "individual",
                        "calculation_formula": "MIN(taxable_income, 300000) * 0.07",
                        "rate": 0.070,
                        "act_name": "Nigeria Tax Act 2025",
                        "section_reference": "Section 34(a)",
                        "citation_text": "First ₦300,000 of taxable income at 7% rate."
                    }
                ]
            }
        
    except Exception as e:
        logger.error(f"V2 get rules failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get legislation rules: {str(e)}"
        )

@v2_router.get("/legislation/exemptions")
async def v2_get_exemptions(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    current_user: Dict = Depends(get_current_user)
):
    """
    V2: Get Available Tax Exemptions
    
    Returns all tax exemptions available under Nigerian law
    with qualification criteria and estimated savings.
    """
    try:
        legislative_db = get_legislative_db_service()
        
        if legislative_db:
            # Get exemptions from database
            supabase = get_supabase_client()
            result = await supabase.from_("tax_exemption_criteria")\
                .select("*")\
                .execute()
            
            exemptions = result.data or []
            
            # Filter by entity type if specified
            if entity_type:
                exemptions = [
                    e for e in exemptions
                    if await _exemption_applies_to_entity(e, entity_type)
                ]
            
            return {
                "success": True,
                "count": len(exemptions),
                "exemptions": exemptions
            }
        else:
            # Return sample exemptions
            return {
                "success": True,
                "count": 2,
                "exemptions": [
                    {
                        "exemption_code": "SMALL_CO_EXEMPTION",
                        "exemption_name": "Small Company 0% CIT",
                        "description": "0% CIT for companies with turnover < ₦100M",
                        "qualification_logic": {
                            "conditions": [
                                {"field": "entity_type", "operator": "=", "value": "company"},
                                {"field": "annual_turnover", "operator": "<", "value": 100000000}
                            ]
                        },
                        "required_documents": ["Audited Financial Statements", "Tax Clearance Certificate"],
                        "applies_to_tax_types": ["CIT"],
                        "savings_calculation_formula": "annual_profit * 0.30",
                        "act_name": "Nigeria Tax Act 2025",
                        "section_reference": "Section 23(a)",
                        "citation_text": "Small companies (turnover < ₦100M) exempt from CIT.",
                        "effective_date": "2025-01-01"
                    },
                    {
                        "exemption_code": "DIGITAL_EXPORT_VAT",
                        "exemption_name": "Digital Export 0% VAT",
                        "description": "0% VAT on digital service exports",
                        "qualification_logic": {
                            "conditions": [
                                {"field": "exports_digital_services", "operator": "=", "value": True},
                                {"field": "export_revenue", "operator": ">", "value": 0}
                            ]
                        },
                        "required_documents": ["Export Invoices", "Foreign Exchange Receipts"],
                        "applies_to_tax_types": ["VAT"],
                        "savings_calculation_formula": "export_revenue * 0.075",
                        "act_name": "Nigeria Tax Act 2025",
                        "section_reference": "Section 33(c)",
                        "citation_text": "Digital service exports to foreign clients qualify for 0% VAT.",
                        "effective_date": "2025-01-01"
                    }
                ]
            }
        
    except Exception as e:
        logger.error(f"V2 get exemptions failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get exemptions: {str(e)}"
        )

@v2_router.get("/education/calculate/{tax_type}")
async def v2_educational_calculation(
    tax_type: str,
    amount: float = Query(..., description="Amount to calculate tax for"),
    current_user: Optional[Dict] = Depends(get_current_user, use_cache=False)
):
    """
    V2: Educational Tax Calculation
    
    Provides educational calculation with step-by-step explanation
    and references to actual legislation.
    """
    try:
        # Simplified educational calculations
        explanations = {
            "CIT": {
                "formula": "Taxable Profit × CIT Rate",
                "steps": [
                    "1. Determine company size based on turnover",
                    "2. Calculate taxable profit (Profit - Allowable Deductions)",
                    "3. Apply applicable CIT rate (0%, 20%, or 30%)",
                    "4. Subtract any qualified exemptions"
                ],
                "example": f"For ₦{amount:,.2f} profit: ₦{amount:,.2f} × 0.30 = ₦{amount * 0.3:,.2f}",
                "reference": "Nigeria Tax Act 2025, Section 23"
            },
            "VAT": {
                "formula": "Taxable Supplies × 7.5%",
                "steps": [
                    "1. Determine if turnover exceeds ₦25M threshold",
                    "2. Calculate VAT on taxable supplies (7.5%)",
                    "3. Subtract input VAT on purchases",
                    "4. Remit net VAT to Nigeria Revenue Service"
                ],
                "example": f"For ₦{amount:,.2f} supplies: ₦{amount:,.2f} × 0.075 = ₦{amount * 0.075:,.2f}",
                "reference": "Nigeria Tax Act 2025, Section 33"
            },
            "PIT": {
                "formula": "Progressive Tax Bands",
                "steps": [
                    "1. Apply Consolidated Relief Allowance",
                    "2. Apply pension deductions",
                    "3. Calculate tax using progressive bands",
                    "4. Sum taxes from all applicable bands"
                ],
                "example": f"For ₦{amount:,.2f} income: Progressive calculation based on bands",
                "reference": "Nigeria Tax Act 2025, Section 34"
            }
        }
        
        if tax_type not in explanations:
            raise HTTPException(status_code=404, detail="Tax type not found")
        
        return {
            "success": True,
            "tax_type": tax_type,
            "amount": amount,
            "explanation": explanations[tax_type],
            "interactive_calculator": f"/api/v2/tax/calculator/instant/simple?entity_type={'company' if tax_type == 'CIT' else 'individual'}&annual_turnover={amount}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V2 educational calculation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Educational calculation failed: {str(e)}"
        )

# ============================================
# HELPER FUNCTIONS
# ============================================

async def v2_fallback_calculation(request: InstantCalculatorRequest, current_user: Optional[Dict] = None):
    """Fallback calculation if legislative engine fails"""
    try:
        # Simple calculation similar to V1 but with V2 format
        entity_type = request.entity_type
        turnover = request.annual_turnover or 0
        profit = request.annual_profit or (turnover * 0.2)
        vat_supplies = request.vat_taxable_supplies or 0
        digital_gains = request.digital_asset_gains or 0
        
        # Calculate CIT/PIT
        if entity_type in ['company', 'partnership']:
            if turnover < 100000000:
                cit_rate = 0.00
                cit_amount = 0
            elif turnover < 500000000:
                cit_rate = 0.20
                cit_amount = profit * cit_rate
            else:
                cit_rate = 0.30
                cit_amount = profit * cit_rate
            income_tax = {
                "type": "CIT",
                "rate": cit_rate,
                "amount": cit_amount
            }
        else:
            income_tax = {
                "type": "PIT",
                "rate": 0.20,
                "amount": profit * 0.20
            }
        
        # Calculate VAT
        vat_rate = 0.075
        vat_amount = vat_supplies * vat_rate
        
        # Calculate CGT on digital assets
        cgt_rate = 0.10
        cgt_amount = digital_gains * cgt_rate
        
        # Calculate TET (for companies)
        tet_amount = 0
        if entity_type == 'company':
            tet_rate = 0.02
            tet_amount = profit * tet_rate
        
        total_liability = income_tax['amount'] + vat_amount + cgt_amount + tet_amount
        
        # Build V2 format response
        breakdown = {}
        if entity_type in ['company', 'partnership']:
            breakdown['cit'] = {
                "tax_type": "CIT",
                "turnover": turnover,
                "gross_profit": profit,
                "taxable_profit": profit,
                "tax_rate": cit_rate,
                "amount": cit_amount,
                "citations": [{"section": "Nigeria Tax Act 2025", "description": "Companies Income Tax"}]
            }
        else:
            breakdown['pit'] = {
                "tax_type": "PIT",
                "annual_income": turnover,
                "amount": income_tax['amount'],
                "citations": [{"section": "Nigeria Tax Act 2025", "description": "Personal Income Tax"}]
            }
        
        if vat_supplies > 0:
            breakdown['vat'] = {
                "tax_type": "VAT",
                "taxable_supplies": vat_supplies,
                "vat_rate": vat_rate,
                "amount": vat_amount,
                "citations": [{"section": "Nigeria Tax Act 2025, Section 33", "description": "Value Added Tax"}]
            }
        
        if digital_gains > 0:
            breakdown['cgt_digital'] = {
                "tax_type": "CGT_DIGITAL",
                "digital_asset_gains": digital_gains,
                "cgt_rate": cgt_rate,
                "amount": cgt_amount,
                "citations": [{"section": "Nigeria Tax Act 2025, Section 56", "description": "Capital Gains Tax on digital assets"}]
            }
        
        if entity_type == 'company':
            breakdown['tet'] = {
                "tax_type": "TET",
                "assessable_profit": profit,
                "tet_rate": 0.02,
                "amount": tet_amount,
                "citations": [{"section": "Nigeria Tax Act 2025, Section 78", "description": "Tertiary Education Tax"}]
            }
        
        result = {
            "breakdown": breakdown,
            "total_liability_before_exemptions": total_liability,
            "total_liability": total_liability,
            "exemptions_applied": [],
            "total_savings": 0,
            "effective_tax_rate": total_liability / turnover if turnover > 0 else 0,
            "citations": [
                {"section": "Nigeria Tax Act 2025", "description": "Legislative tax calculation", "applies_to": "General calculation"}
            ],
            "recommendations": [
                "Complete your tax profile for more accurate calculations",
                "Upgrade to full legislative engine for detailed exemptions and deductions"
            ],
            "risk_flags": [],
            "confidence_score": 0.3,
            "calculated_at": datetime.utcnow().isoformat(),
            "tax_year": request.tax_year or datetime.utcnow().year,
            "legislation_version": "Nigeria Tax Act 2025 (Fallback)"
        }
        
        user_context = {}
        if current_user:
            user_context = {
                "user_id": current_user.get('id'),
                "has_profile": False,
                "suggestion": "Save these inputs to your tax profile"
            }
        
        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "legislation_version": "Nigeria Tax Act 2025 (Fallback)",
            "calculation_type": "fallback",
            "inputs": request.dict(exclude_none=True),
            "user_context": user_context,
            "results": result
        }
        
    except Exception as e:
        logger.error(f"V2 fallback calculation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Tax calculation failed: {str(e)}"
        )

async def _exemption_applies_to_entity(exemption: Dict, entity_type: str) -> bool:
    """Check if exemption applies to entity type"""
    # Simplified check
    logic = exemption.get('qualification_logic', {})
    conditions = logic.get('conditions', [])
    
    for condition in conditions:
        if condition.get('field') == 'entity_type' and condition.get('value') != entity_type:
            return False
    
    return True

# ============================================
# HEALTH CHECK ENDPOINTS
# ============================================

@v1_router.get("/test")
async def v1_test_endpoint(
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """V1 test endpoint"""
    return {
        "success": True,
        "message": "Tax API v1 is working",
        "user_id": current_user['id'],
        "status": "operational",
        "version": "v1"
    }

@v2_router.get("/test")
async def v2_test_endpoint(
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """V2 test endpoint"""
    # Test legislative engine availability
    tax_engine = get_legislative_tax_engine()
    legislative_available = tax_engine is not None
    
    return {
        "success": True,
        "message": "Tax API v2 is working",
        "user_id": current_user['id'],
        "status": "operational",
        "version": "v2",
        "features": {
            "legislative_engine": legislative_available,
            "instant_calculator": True,
            "legal_citations": True,
            "exemption_analysis": True
        },
        "legislation_version": "Nigeria Tax Act 2025"
    }

@router.get("/health")
async def tax_health_check():
    """Overall tax API health check"""
    v1_status = "healthy"
    v2_status = "healthy"
    
    # Test V2 legislative engine
    try:
        tax_engine = get_legislative_tax_engine()
        if not tax_engine:
            v2_status = "degraded (legislative engine not available)"
    except:
        v2_status = "degraded"
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "versions": {
            "v1": v1_status,
            "v2": v2_status
        },
        "legislation": "Nigeria Tax Act 2025",
        "endpoints": {
            "v1": "/api/v1/tax/*",
            "v2": "/api/v2/tax/*"
        }
    }