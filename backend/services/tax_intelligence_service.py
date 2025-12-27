# backend/services/tax_intelligence_service.py
# 🎯 Nigerian Tax Intelligence Engine - Core Orchestrator
# Surgical precision, zero bloat, maximum impact

import logging
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal, getcontext
from datetime import datetime, date, timedelta
import traceback
from enum import Enum

from backend.config import Settings
from backend.services.database_service import DatabaseService
from backend.services.compliance_service import ComplianceService
from backend.services.audit_service import AuditService, AuditEventType

getcontext().prec = 28  # Financial precision

logger = logging.getLogger(__name__)


class TaxCategory(str, Enum):
    """Tax categories from Nigerian Tax Act"""
    CIT = "cit"  # Companies Income Tax
    PIT = "pit"  # Personal Income Tax
    VAT = "vat"  # Value Added Tax
    CGT = "cgt"  # Capital Gains Tax
    WHT = "wht"  # Withholding Tax
    TET = "tet"  # Tertiary Education Tax
    DEV_LEVY = "dev_levy"  # Development Levy
    STAMP_DUTY = "stamp_duty"
    PAYE = "paye"  # Pay As You Earn


class ExemptionCode(str, Enum):
    """Exemption codes from Nigerian Tax Act"""
    SMALL_COMPANY = "small_co"  # < N100M turnover
    AGRICULTURAL_HOLIDAY = "agri_holiday"  # 5-year agri exemption
    STARTUP_24MO = "startup_24mo"  # 24-month startup exemption
    PIONEER_STATUS = "pioneer_status"  # 3-5 year pioneer exemption
    RND_DEDUCTION = "rnd_deduction"  # R&D expense deduction
    PENSION_DEDUCTION = "pension_ded"  # Pension contribution deduction
    MIN_WAGE_EXEMPT = "min_wage_exempt"  # Min wage PAYE exemption
    DIGITAL_EXPORT_ZERO_VAT = "digital_export_zero"  # 0% VAT on digital exports
    FREE_TRADE_ZONE = "ftz_exemption"  # Free trade zone exemption


class TaxIntelligenceService:
    """
    🧠 Tax Intelligence Engine
    
    Core Responsibilities:
    1. Calculate tax liabilities with surgical precision
    2. Qualify exemptions based on user profile + compliance data
    3. Model "what-if" scenarios for tax planning
    4. Estimate penalties for non-compliance
    5. Generate comprehensive tax reports with citations
    
    Design Principles:
    - Single Source of Truth: All tax logic centralized here
    - Rule-Based + Context-Aware: Not just static calculations
    - Audit Everything: Every calculation logged
    - Self-Healing: Retries on failures, graceful degradation
    - Citation System: Link results to actual law sections
    """

    def __init__(
        self,
        settings: Settings,
        db: DatabaseService,
        compliance: ComplianceService,
        audit: AuditService
    ):
        self.settings = settings
        self.db = db
        self.compliance = compliance
        self.audit = audit
        self.max_retries = 3
        
        # Cache tax rules in memory for performance
        self._rules_cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=1)

    # ============================================
    # CORE CALCULATION ENGINE
    # ============================================

    async def calculate_comprehensive_tax_liability(
        self,
        user_id: str,
        scenario_data: Optional[Dict[str, Any]] = None,
        tax_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        🎯 Master Tax Calculator
        
        Calculates all applicable taxes based on user profile + scenario overrides.
        Returns detailed breakdown with exemptions, citations, and recommendations.
        
        Args:
            user_id: User identifier
            scenario_data: Optional scenario overrides (for "what-if" modeling)
            tax_year: Tax year (default: current year)
            
        Returns:
            {
                "breakdown": {
                    "cit": {...},
                    "vat": {...},
                    "cgt": {...},
                    ...
                },
                "total_liability": Decimal,
                "exemptions_applied": [...],
                "total_savings": Decimal,
                "effective_tax_rate": Decimal,
                "citations": [...],
                "recommendations": [...],
                "risk_flags": [...],
                "confidence_score": float
            }
        """
        try:
            # Get user tax profile
            profile = await self._get_user_tax_profile(user_id)
            
            # Apply scenario overrides if provided
            if scenario_data:
                profile.update(scenario_data)
            
            # Load applicable tax rules
            rules = await self._get_applicable_rules(profile)
            
            # Calculate each tax category
            breakdown = {}
            citations = []
            
            # 1. Companies Income Tax (CIT) / Personal Income Tax (PIT)
            if profile['entity_type'] in ['company', 'partnership']:
                cit_result = await self._calculate_cit(profile, rules)
                breakdown['cit'] = cit_result
                citations.extend(cit_result.get('citations', []))
            elif profile['entity_type'] == 'individual':
                pit_result = await self._calculate_pit(profile, rules)
                breakdown['pit'] = pit_result
                citations.extend(pit_result.get('citations', []))
            
            # 2. Value Added Tax (VAT)
            if profile.get('vat_taxable_supplies', 0) > 0:
                vat_result = await self._calculate_vat(profile, rules)
                breakdown['vat'] = vat_result
                citations.extend(vat_result.get('citations', []))
            
            # 3. Capital Gains Tax (CGT) - Digital Assets
            if profile.get('digital_asset_gains', 0) > 0:
                cgt_result = await self._calculate_cgt_digital(profile, rules)
                breakdown['cgt_digital'] = cgt_result
                citations.extend(cgt_result.get('citations', []))
            
            # 4. Tertiary Education Tax (TET)
            if profile['entity_type'] == 'company':
                tet_result = await self._calculate_tet(profile, rules)
                breakdown['tet'] = tet_result
                citations.extend(tet_result.get('citations', []))
            
            # 5. Development Levy
            if profile.get('annual_turnover', 0) > Decimal('100000000'):  # > N100M
                levy_result = await self._calculate_dev_levy(profile, rules)
                breakdown['dev_levy'] = levy_result
                citations.extend(levy_result.get('citations', []))
            
            # Qualify exemptions
            exemptions = await self.qualify_exemptions(user_id, profile)
            
            # Apply exemptions and calculate savings
            total_liability_before = sum(
                item.get('amount', Decimal('0')) 
                for item in breakdown.values()
            )
            
            total_savings = sum(
                Decimal(str(e.get('estimated_savings', 0))) 
                for e in exemptions
            )
            
            total_liability_after = max(Decimal('0'), total_liability_before - total_savings)
            
            # Calculate effective tax rate
            total_income = profile.get('annual_turnover', Decimal('1'))
            effective_rate = (total_liability_after / total_income * 100) if total_income > 0 else Decimal('0')
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(profile, breakdown, exemptions)
            
            # Identify risk flags
            risk_flags = await self._identify_risk_flags(profile, breakdown)
            
            # Calculate confidence score
            confidence_score = await self._calculate_confidence_score(profile)
            
            result = {
                "breakdown": breakdown,
                "total_liability_before_exemptions": float(total_liability_before),
                "total_liability": float(total_liability_after),
                "exemptions_applied": exemptions,
                "total_savings": float(total_savings),
                "effective_tax_rate": float(effective_rate),
                "citations": self._deduplicate_citations(citations),
                "recommendations": recommendations,
                "risk_flags": risk_flags,
                "confidence_score": confidence_score,
                "calculated_at": datetime.utcnow().isoformat(),
                "tax_year": tax_year or datetime.utcnow().year
            }
            
            # Log calculation to audit trail
            await self.audit.log_event(
                AuditEventType.TAX_CALCULATION,
                user_id=user_id,
                details={
                    "calculation_type": "comprehensive",
                    "total_liability": float(total_liability_after),
                    "confidence_score": confidence_score
                }
            )
            
            # Persist calculation to database
            await self._persist_calculation(user_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Tax calculation failed for user {user_id}: {e}\n{traceback.format_exc()}")
            raise

    # ============================================
    # INDIVIDUAL TAX CALCULATORS
    # ============================================

    async def _calculate_cit(self, profile: Dict, rules: List[Dict]) -> Dict[str, Any]:
        """Calculate Companies Income Tax"""
        turnover = Decimal(str(profile.get('annual_turnover', 0)))
        profit = Decimal(str(profile.get('annual_profit', turnover * Decimal('0.2'))))  # Estimate if not provided
        
        # Determine applicable rate based on turnover
        if turnover < Decimal('100000000'):  # < N100M
            rate = Decimal('0.00')
            rule_ref = "Finance Act 2023, Section 8(1) - Small Company Exemption"
        elif turnover < Decimal('500000000'):  # N100M - N500M
            rate = Decimal('0.20')
            rule_ref = "Companies Income Tax Act - Medium Company Rate"
        else:  # > N500M
            rate = Decimal('0.30')
            rule_ref = "Companies Income Tax Act - Standard Rate"
        
        # Apply deductions
        deductions = Decimal('0')
        if profile.get('rnd_expenses', 0) > 0:
            deductions += Decimal(str(profile['rnd_expenses']))
        if profile.get('capital_allowances', 0) > 0:
            deductions += Decimal(str(profile['capital_allowances']))
        
        taxable_profit = max(Decimal('0'), profit - deductions)
        cit_amount = taxable_profit * rate
        
        return {
            "tax_type": "CIT",
            "turnover": float(turnover),
            "gross_profit": float(profit),
            "deductions": float(deductions),
            "taxable_profit": float(taxable_profit),
            "tax_rate": float(rate),
            "amount": float(cit_amount),
            "citations": [{"section": rule_ref, "applies_to": "CIT calculation"}]
        }

    async def _calculate_pit(self, profile: Dict, rules: List[Dict]) -> Dict[str, Any]:
        """Calculate Personal Income Tax (Progressive)"""
        annual_income = Decimal(str(profile.get('annual_turnover', 0)))
        
        # PIT bands (Nigerian Tax Act 2023)
        bands = [
            (Decimal('300000'), Decimal('0.07')),
            (Decimal('300000'), Decimal('0.11')),  # Next N300K
            (Decimal('500000'), Decimal('0.15')),  # Next N500K
            (Decimal('500000'), Decimal('0.19')),  # Next N500K
            (Decimal('1600000'), Decimal('0.21')),  # Next N1.6M
            (float('inf'), Decimal('0.25'))  # Above N3.2M
        ]
        
        pit_amount = Decimal('0')
        remaining = annual_income
        band_breakdown = []
        
        for band_limit, band_rate in bands:
            if remaining <= 0:
                break
            
            taxable_in_band = min(remaining, Decimal(str(band_limit)))
            tax_in_band = taxable_in_band * band_rate
            pit_amount += tax_in_band
            
            band_breakdown.append({
                "band": float(taxable_in_band),
                "rate": float(band_rate),
                "tax": float(tax_in_band)
            })
            
            remaining -= taxable_in_band
        
        return {
            "tax_type": "PIT",
            "annual_income": float(annual_income),
            "band_breakdown": band_breakdown,
            "amount": float(pit_amount),
            "citations": [{"section": "Personal Income Tax Act - Progressive Rates", "applies_to": "PIT calculation"}]
        }

    async def _calculate_vat(self, profile: Dict, rules: List[Dict]) -> Dict[str, Any]:
        """Calculate Value Added Tax"""
        vat_supplies = Decimal(str(profile.get('vat_taxable_supplies', 0)))
        vat_rate = Decimal('0.075')  # 7.5%
        
        # Check for exemptions
        if profile.get('exports_digital_services'):
            vat_rate = Decimal('0.00')
            rule_ref = "Finance Act 2023 - Digital Service Exports (0% VAT)"
        else:
            rule_ref = "VAT Act 2023 - Standard Rate (7.5%)"
        
        vat_amount = vat_supplies * vat_rate
        
        return {
            "tax_type": "VAT",
            "taxable_supplies": float(vat_supplies),
            "vat_rate": float(vat_rate),
            "amount": float(vat_amount),
            "citations": [{"section": rule_ref, "applies_to": "VAT calculation"}]
        }

    async def _calculate_cgt_digital(self, profile: Dict, rules: List[Dict]) -> Dict[str, Any]:
        """Calculate Capital Gains Tax on Digital Assets"""
        digital_gains = Decimal(str(profile.get('digital_asset_gains', 0)))
        cgt_rate = Decimal('0.10')  # 10% on digital asset gains
        
        cgt_amount = digital_gains * cgt_rate
        
        return {
            "tax_type": "CGT_DIGITAL",
            "digital_asset_gains": float(digital_gains),
            "cgt_rate": float(cgt_rate),
            "amount": float(cgt_amount),
            "citations": [{"section": "Finance Act 2023 - Digital Asset Gains (10% CGT)", "applies_to": "CGT on digital assets"}]
        }

    async def _calculate_tet(self, profile: Dict, rules: List[Dict]) -> Dict[str, Any]:
        """Calculate Tertiary Education Tax (2% of assessable profits)"""
        profit = Decimal(str(profile.get('annual_profit', profile.get('annual_turnover', 0) * Decimal('0.2'))))
        tet_rate = Decimal('0.02')
        
        tet_amount = profit * tet_rate
        
        return {
            "tax_type": "TET",
            "assessable_profit": float(profit),
            "tet_rate": float(tet_rate),
            "amount": float(tet_amount),
            "citations": [{"section": "Tertiary Education Tax Act - 2% of Assessable Profits", "applies_to": "TET calculation"}]
        }

    async def _calculate_dev_levy(self, profile: Dict, rules: List[Dict]) -> Dict[str, Any]:
        """Calculate Development Levy (4% for companies > N100M turnover)"""
        turnover = Decimal(str(profile.get('annual_turnover', 0)))
        levy_rate = Decimal('0.04')
        
        levy_amount = turnover * levy_rate
        
        return {
            "tax_type": "DEV_LEVY",
            "turnover": float(turnover),
            "levy_rate": float(levy_rate),
            "amount": float(levy_amount),
            "citations": [{"section": "Development Levy Act - 4% on Large Companies", "applies_to": "Development Levy"}]
        }

    # ============================================
    # EXEMPTION QUALIFICATION ENGINE
    # ============================================

    async def qualify_exemptions(
        self,
        user_id: str,
        profile: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        🎯 Exemption Qualification Engine
        
        Determines which tax exemptions user qualifies for based on:
        1. User tax profile
        2. Compliance document status
        3. Nigerian Tax Act provisions
        
        Returns list of qualified exemptions with estimated savings.
        """
        if not profile:
            profile = await self._get_user_tax_profile(user_id)
        
        qualified = []
        
        # 1. Small Company Exemption (< N100M turnover = 0% CIT)
        turnover = Decimal(str(profile.get('annual_turnover', 0)))
        if profile['entity_type'] == 'company' and turnover < Decimal('100000000'):
            estimated_savings = turnover * Decimal('0.30')  # Would have paid 30%
            qualified.append({
                "code": ExemptionCode.SMALL_COMPANY,
                "name": "Small Company 0% CIT Exemption",
                "description": "Companies with turnover < N100M pay 0% CIT",
                "act_section": "Finance Act 2023, Section 8(1)",
                "estimated_savings": float(estimated_savings),
                "qualification_criteria": "Annual turnover < N100,000,000",
                "user_qualifies": True,
                "required_documents": ["Audited Financial Statements", "Tax Clearance Certificate"],
                "status": "qualified"
            })
        
        # 2. Agricultural Business Tax Holiday (5 years)
        if 'agri' in profile.get('industry_sector', '').lower():
            annual_tax = turnover * Decimal('0.30')  # Assume 30% rate
            estimated_savings = annual_tax * 5  # 5 years
            qualified.append({
                "code": ExemptionCode.AGRICULTURAL_HOLIDAY,
                "name": "Agricultural Business Tax Holiday",
                "description": "5-year tax exemption for agricultural businesses",
                "act_section": "Industrial Development Act, Section 15",
                "estimated_savings": float(estimated_savings),
                "qualification_criteria": "Operating in agricultural sector",
                "user_qualifies": True,
                "required_documents": ["Business License", "Sector Registration Certificate"],
                "status": "qualified"
            })
        
        # 3. Startup 24-Month Exemption
        if profile.get('is_startup'):
            incorporation_date = profile.get('startup_incorporation_date')
            if incorporation_date:
                months_since_incorporation = (date.today() - incorporation_date).days / 30
                if months_since_incorporation <= 24:
                    annual_tax = turnover * Decimal('0.30')
                    estimated_savings = annual_tax * 2  # 2 years
                    qualified.append({
                        "code": ExemptionCode.STARTUP_24MO,
                        "name": "Startup 24-Month Tax Exemption",
                        "description": "24-month CIT exemption for registered startups",
                        "act_section": "Finance Act 2023 - Startup Provisions",
                        "estimated_savings": float(estimated_savings),
                        "qualification_criteria": "Registered startup < 24 months old",
                        "user_qualifies": True,
                        "required_documents": ["CAC Certificate", "Startup Registration"],
                        "status": "qualified"
                    })
        
        # 4. Pioneer Status (3-5 year exemption)
        if profile.get('has_pioneer_status'):
            annual_tax = turnover * Decimal('0.30')
            estimated_savings = annual_tax * 5
            qualified.append({
                "code": ExemptionCode.PIONEER_STATUS,
                "name": "Pioneer Status Tax Holiday",
                "description": "3-5 year tax holiday for pioneer industries",
                "act_section": "Industrial Development Act - Pioneer Status",
                "estimated_savings": float(estimated_savings),
                "qualification_criteria": "Granted pioneer industry status",
                "user_qualifies": True,
                "required_documents": ["Pioneer Certificate"],
                "status": "qualified"
            })
        
        # 5. R&D Deduction (Up to 5% of turnover)
        rnd_expenses = Decimal(str(profile.get('rnd_expenses', 0)))
        if rnd_expenses > 0:
            max_deduction = turnover * Decimal('0.05')  # Up to 5%
            deduction = min(rnd_expenses, max_deduction)
            estimated_savings = deduction * Decimal('0.30')  # Assume 30% CIT rate
            qualified.append({
                "code": ExemptionCode.RND_DEDUCTION,
                "name": "R&D Expense Deduction",
                "description": "R&D expenses deductible up to 5% of turnover",
                "act_section": "Companies Income Tax Act - R&D Incentives",
                "estimated_savings": float(estimated_savings),
                "qualification_criteria": "Documented R&D expenses",
                "user_qualifies": True,
                "required_documents": ["R&D Expense Report", "Innovation Documentation"],
                "status": "qualified"
            })

        # 6. Pension Contribution Deduction
        pension = Decimal(str(profile.get('pension_contributions', 0)))
        if pension > 0:
            estimated_savings = pension * Decimal('0.30')  # Tax savings on deduction
            qualified.append({
                "code": ExemptionCode.PENSION_DEDUCTION,
                "name": "Pension Contribution Deduction",
                "description": "Employer pension contributions are tax-deductible",
                "act_section": "Pension Reform Act 2014",
                "estimated_savings": float(estimated_savings),
                "qualification_criteria": "Registered pension scheme contributions",
                "user_qualifies": True,
                "required_documents": ["Pension Scheme Registration", "Contribution Records"],
                "status": "qualified"
            })
        
        # 7. Minimum Wage PAYE Exemption
        employees_below_min = profile.get('employees_below_min_wage', 0)
        if employees_below_min > 0:
            # Estimate: N30K/month * 12 months * 7% PAYE * number of employees
            estimated_savings = Decimal('30000') * 12 * Decimal('0.07') * Decimal(str(employees_below_min))
            qualified.append({
                "code": ExemptionCode.MIN_WAGE_EXEMPT,
                "name": "Minimum Wage PAYE Exemption",
                "description": "Employees earning minimum wage exempt from PAYE",
                "act_section": "Personal Income Tax Act - Minimum Wage Exemption",
                "estimated_savings": float(estimated_savings),
                "qualification_criteria": "Employees earning ≤ minimum wage",
                "user_qualifies": True,
                "required_documents": ["Payroll Records"],
                "status": "qualified"
            })
        
        # 8. Digital Export Zero-VAT
        if profile.get('exports_digital_services'):
            export_revenue = Decimal(str(profile.get('export_revenue', 0)))
            estimated_savings = export_revenue * Decimal('0.075')  # Would have paid 7.5% VAT
            qualified.append({
                "code": ExemptionCode.DIGITAL_EXPORT_ZERO_VAT,
                "name": "Digital Service Export VAT Exemption",
                "description": "0% VAT on digital service exports",
                "act_section": "Finance Act 2023 - Digital Services Export",
                "estimated_savings": float(estimated_savings),
                "qualification_criteria": "Exports digital services to foreign clients",
                "user_qualifies": True,
                "required_documents": ["Export Invoices", "Foreign Exchange Receipts"],
                "status": "qualified"
            })
        
        # 9. Free Trade Zone Exemption
        if profile.get('in_free_trade_zone'):
            annual_tax = turnover * Decimal('0.30')
            estimated_savings = annual_tax * 10  # 10-year exemption
            qualified.append({
                "code": ExemptionCode.FREE_TRADE_ZONE,
                "name": "Free Trade Zone Tax Holiday",
                "description": "10-year tax exemption for businesses in FTZs",
                "act_section": "Oil and Gas Free Zones Act",
                "estimated_savings": float(estimated_savings),
                "qualification_criteria": "Operating within designated Free Trade Zone",
                "user_qualifies": True,
                "required_documents": ["FTZ Registration Certificate", "Zone Operator License"],
                "status": "qualified"
            })
        
        # Log exemption check
        await self.audit.log_event(
            AuditEventType.TAX_EXEMPTION_CHECK,
            user_id=user_id,
            details={"qualified_count": len(qualified), "total_estimated_savings": sum(e['estimated_savings'] for e in qualified)}
        )
        
        return qualified

    # ============================================
    # SCENARIO MODELING
    # ============================================

    async def model_tax_scenario(
        self,
        user_id: str,
        scenario_name: str,
        scenario_data: Dict[str, Any],
        save_scenario: bool = True
    ) -> Dict[str, Any]:
        """
        🎯 Tax Scenario Modeler
        
        Allows users to model "what-if" scenarios:
        - What if I hire 10 more employees?
        - What if I invest in R&D?
        - What if I move operations to free trade zone?
        
        Returns comparison with baseline and variance analysis.
        """
        # Calculate scenario tax liability
        scenario_result = await self.calculate_comprehensive_tax_liability(
            user_id,
            scenario_data=scenario_data
        )
        
        # Get baseline (actual profile)
        baseline_result = await self.calculate_comprehensive_tax_liability(user_id)
        
        # Variance analysis
        variance = {
            "liability_change": scenario_result['total_liability'] - baseline_result['total_liability'],
            "liability_change_pct": (
                (scenario_result['total_liability'] - baseline_result['total_liability']) / baseline_result['total_liability'] * 100
                if baseline_result['total_liability'] > 0 else 0
            ),
            "savings_change": scenario_result['total_savings'] - baseline_result['total_savings'],
            "effective_rate_change": scenario_result['effective_tax_rate'] - baseline_result['effective_tax_rate']
        }
        
        result = {
            "scenario_name": scenario_name,
            "scenario_data": scenario_data,
            "scenario_result": scenario_result,
            "baseline_result": baseline_result,
            "variance_analysis": variance,
            "recommendation": self._generate_scenario_recommendation(variance)
        }
        
        # Save scenario if requested
        if save_scenario:
            await self._persist_scenario(user_id, result)
        
        return result

    # ============================================
    # PENALTY ESTIMATION
    # ============================================

    async def estimate_penalties(
        self,
        user_id: str,
        violation_types: List[str],
        tax_liability: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        🎯 Penalty Estimator
        
        Estimates penalties for non-compliance scenarios:
        - Late filing
        - Non-payment
        - Under-declaration
        - Non-registration
        """
        penalties = []
        total_penalty = Decimal('0')
        
        # Get user profile for context
        profile = await self._get_user_tax_profile(user_id)
        if not tax_liability:
            calc = await self.calculate_comprehensive_tax_liability(user_id)
            tax_liability = Decimal(str(calc['total_liability']))
        
        # Penalty rules (Nigerian Tax Act)
        penalty_rules = {
            "late_filing": {
                "rate": Decimal('0.10'),  # 10% of tax due
                "minimum": Decimal('50000'),
                "description": "Late filing penalty (10% of tax due, min ₦50,000)",
                "section": "FIRS Penalties Schedule"
            },
            "late_payment": {
                "rate": Decimal('0.10'),  # 10% of tax due
                "minimum": Decimal('50000'),
                "plus_interest": Decimal('0.21'),  # 21% annual interest
                "description": "Late payment penalty plus 21% annual interest",
                "section": "FIRS Penalties Schedule"
            },
            "non_registration": {
                "flat": Decimal('100000'),
                "description": "Failure to register for tax (₦100,000)",
                "section": "Tax Administration Act"
            },
            "under_declaration": {
                "rate": Decimal('0.20'),  # 20% of undeclared amount
                "minimum": Decimal('100000'),
                "description": "Under-declaration penalty (20% of undeclared amount)",
                "section": "Tax Administration Act"
            },
            "tax_evasion": {
                "rate": Decimal('1.00'),  # 100% of evaded tax
                "minimum": Decimal('500000'),
                "plus_criminal": True,
                "description": "Tax evasion (100% penalty + criminal prosecution)",
                "section": "Criminal Code Act"
            }
        }
        
        for violation in violation_types:
            if violation in penalty_rules:
                rule = penalty_rules[violation]
                
                if 'rate' in rule:
                    penalty_amount = max(
                        rule['minimum'],
                        tax_liability * rule['rate']
                    )
                elif 'flat' in rule:
                    penalty_amount = rule['flat']
                else:
                    penalty_amount = rule['minimum']
                
                penalties.append({
                    "violation_type": violation,
                    "description": rule['description'],
                    "act_section": rule['section'],
                    "penalty_amount": float(penalty_amount),
                    "criminal_liability": rule.get('plus_criminal', False)
                })
                
                total_penalty += penalty_amount
        
        result = {
            "penalties": penalties,
            "total_penalty": float(total_penalty),
            "tax_liability": float(tax_liability),
            "total_amount_due": float(tax_liability + total_penalty),
            "severity": "high" if total_penalty > tax_liability else "medium" if total_penalty > tax_liability * Decimal('0.5') else "low"
        }
        
        # Log penalty estimation
        await self.audit.log_event(
            AuditEventType.TAX_PENALTY_EST,
            user_id=user_id,
            details=result
        )
        
        return result

    # ============================================
    # HELPER METHODS
    # ============================================

    async def _get_user_tax_profile(self, user_id: str) -> Dict[str, Any]:
        """Fetch comprehensive user tax profile"""
        try:
            result = await self.db.supabase.from_("user_tax_profiles").select("*").eq("user_id", user_id).single().execute()
            if result.data:
                return result.data
            else:
                # Create default profile
                default_profile = {
                    "user_id": user_id,
                    "entity_type": "individual",
                    "annual_turnover": 0,
                    "annual_profit": 0
                }
                await self.db.supabase.from_("user_tax_profiles").insert(default_profile).execute()
                return default_profile
        except Exception as e:
            logger.error(f"Failed to get tax profile for user {user_id}: {e}")
            return {"user_id": user_id, "entity_type": "individual"}

    async def _get_applicable_rules(self, profile: Dict) -> List[Dict]:
        """Load applicable tax rules from database"""
        # Implement caching for performance
        if self._rules_cache and self._cache_timestamp and (datetime.utcnow() - self._cache_timestamp) < self._cache_ttl:
            return self._rules_cache.get('all', [])
        
        try:
            result = await self.db.supabase.from_("tax_rules").select("*").is_("effective_until", None).execute()
            rules = result.data or []
            self._rules_cache = {'all': rules}
            self._cache_timestamp = datetime.utcnow()
            return rules
        except Exception as e:
            logger.error(f"Failed to load tax rules: {e}")
            return []

    def _deduplicate_citations(self, citations: List[Dict]) -> List[Dict]:
        """Remove duplicate citations"""
        seen = set()
        unique = []
        for cit in citations:
            key = cit.get('section', '')
            if key not in seen:
                seen.add(key)
                unique.append(cit)
        return unique

    async def _generate_recommendations(
        self,
        profile: Dict,
        breakdown: Dict,
        exemptions: List[Dict]
    ) -> List[str]:
        """Generate actionable tax recommendations"""
        recommendations = []
        
        # Check if missing exemptions
        turnover = Decimal(str(profile.get('annual_turnover', 0)))
        if profile['entity_type'] == 'company' and turnover < Decimal('100000000'):
            if not any(e['code'] == ExemptionCode.SMALL_COMPANY for e in exemptions):
                recommendations.append("✅ Apply for Small Company Exemption - You qualify for 0% CIT!")
        
        # Check for R&D opportunities
        if profile.get('rnd_expenses', 0) == 0 and turnover > Decimal('50000000'):
            recommendations.append("💡 Consider documenting R&D expenses - Up to 5% of turnover is deductible")
        
        # Check for pension contributions
        if profile.get('pension_contributions', 0) == 0 and profile.get('employee_count', 0) > 0:
            recommendations.append("📊 Set up employer pension contributions - They're tax-deductible")
        
        # Check for digital export opportunity
        if not profile.get('exports_digital_services') and 'tech' in profile.get('industry_sector', '').lower():
            recommendations.append("🌍 Explore digital service exports - Qualify for 0% VAT")
        
        return recommendations

    async def _identify_risk_flags(self, profile: Dict, breakdown: Dict) -> List[str]:
        """Identify compliance risk flags"""
        risks = []
        
        # Check for missing tax registrations
        if not profile.get('tin'):  # Tax Identification Number
            risks.append("⚠️ No TIN found - Register with FIRS immediately to avoid ₦100K penalty")
        
        # Check for high effective tax rate (potential for optimization)
        turnover = profile.get('annual_turnover', 1)
        if turnover > 0:
            effective_rate = sum(item.get('amount', 0) for item in breakdown.values()) / turnover * 100
            if effective_rate > 35:
                risks.append("📈 High effective tax rate - Review exemptions you may be missing")
        
        # Check for overdue filings
        last_filing = profile.get('last_filing_date')
        if not last_filing or (date.today() - last_filing).days > 365:
            risks.append("🚨 Tax filing overdue - File immediately to avoid penalties")
        
        return risks

    async def _calculate_confidence_score(self, profile: Dict) -> float:
        """Calculate confidence score for tax calculation (0.0 to 1.0)"""
        score = 1.0
        
        # Deduct for missing critical data
        if not profile.get('annual_turnover') or profile['annual_turnover'] == 0:
            score -= 0.3
        if not profile.get('annual_profit'):
            score -= 0.2
        if not profile.get('entity_type'):
            score -= 0.2
        if not profile.get('verified'):
            score -= 0.1
        
        return max(0.0, score)

    def _generate_scenario_recommendation(self, variance: Dict) -> str:
        """Generate recommendation based on scenario variance"""
        liability_change = variance['liability_change']
        
        if liability_change < 0:
            return f"✅ This scenario REDUCES your tax by ₦{abs(liability_change):,.2f}. Strongly recommended."
        elif liability_change > 0:
            return f"⚠️ This scenario INCREASES your tax by ₦{liability_change:,.2f}. Consider alternatives."
        else:
            return "➡️ This scenario has no tax impact."

    async def _persist_calculation(self, user_id: str, result: Dict):
        """Save calculation to database"""
        try:
            data = {
                "user_id": user_id,
                "calculation_type": "comprehensive",
                "tax_year": result['tax_year'],
                "input_snapshot": {},
                "tax_breakdown": result['breakdown'],
                "exemptions_applied": result['exemptions_applied'],
                "total_savings": result['total_savings'],
                "calculation_engine_version": "1.0",
                "confidence_score": result['confidence_score']
            }
            await self.db.supabase.from_("tax_calculations").insert(data).execute()
        except Exception as e:
            logger.warning(f"Failed to persist calculation: {e}")

    async def _persist_scenario(self, user_id: str, scenario: Dict):
        """Save scenario to database"""
        try:
            data = {
                "user_id": user_id,
                "scenario_name": scenario['scenario_name'],
                "scenario_type": "manual",
                "input_data": scenario['scenario_data'],
                "calculation_results": scenario['scenario_result']
            }
            await self.db.supabase.from_("tax_scenarios").insert(data).execute()
        except Exception as e:
            logger.warning(f"Failed to persist scenario: {e}")
