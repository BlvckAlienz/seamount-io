# backend/services/legislative_tax_engine.py
# 🧠 CORE LEGISLATIVE TAX ENGINE - Powered by Nigeria Tax Act 2025

import logging
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal, getcontext
from datetime import datetime, date, timedelta
import json
import math

from backend.services.legislative_db_service import LegislativeDBService, TaxType

logger = logging.getLogger(__name__)
getcontext().prec = 28  # Financial precision

class LegislativeTaxEngine:
    """
    🎯 Legislative Tax Calculation Engine
    Powered by Nigeria Tax Act 2025
    
    Key Features:
    1. Rule-based calculations from actual legislation
    2. Dynamic exemption qualification
    3. Temporal scenario modeling
    4. Compliance penalty estimation
    5. Legal citation generation
    """
    
    def __init__(self, legislative_db: LegislativeDBService):
        self.legislative_db = legislative_db
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)
        
    async def calculate_comprehensive_tax(
        self,
        entity_type: str,
        calculation_data: Dict[str, Any],
        tax_year: int = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive tax liability using legislative rules
        """
        try:
            if not tax_year:
                tax_year = datetime.now().year
            
            # Identify applicable taxes based on entity type
            applicable_taxes = self._identify_applicable_taxes(entity_type, calculation_data)
            
            # Calculate each tax type
            breakdown = {}
            citations = []
            total_liability = Decimal('0')
            
            for tax_type in applicable_taxes:
                tax_result = await self._calculate_tax_by_type(
                    tax_type, entity_type, calculation_data, tax_year
                )
                
                if tax_result:
                    breakdown[tax_type.lower()] = tax_result
                    citations.extend(tax_result.get('legal_citations', []))
                    total_liability += Decimal(str(tax_result.get('amount', 0)))
            
            # Qualify for exemptions
            exemptions = await self.legislative_db.get_exemptions_for_profile({
                'entity_type': entity_type,
                **calculation_data
            })
            
            # Apply exemption savings
            total_savings = sum(
                Decimal(str(e.get('estimated_savings', 0))) 
                for e in exemptions
            )
            
            net_liability = max(Decimal('0'), total_liability - total_savings)
            
            # Calculate effective tax rate
            turnover = Decimal(str(calculation_data.get('annual_turnover', 1)))
            effective_rate = (net_liability / turnover * 100) if turnover > 0 else Decimal('0')
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(
                entity_type, calculation_data, breakdown, exemptions
            )
            
            # Generate compliance risks
            risk_flags = await self._identify_compliance_risks(
                entity_type, calculation_data, breakdown
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(calculation_data)
            
            result = {
                "breakdown": breakdown,
                "total_liability_before_exemptions": float(total_liability),
                "total_liability": float(net_liability),
                "exemptions_applied": exemptions,
                "total_savings": float(total_savings),
                "effective_tax_rate": float(effective_rate),
                "citations": self._deduplicate_citations(citations),
                "recommendations": recommendations,
                "risk_flags": risk_flags,
                "confidence_score": confidence_score,
                "calculated_at": datetime.utcnow().isoformat(),
                "tax_year": tax_year,
                "legislation_version": "Nigeria Tax Act 2025"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Comprehensive tax calculation failed: {e}", exc_info=True)
            raise
    
    async def _calculate_tax_by_type(
        self,
        tax_type: str,
        entity_type: str,
        data: Dict[str, Any],
        tax_year: int
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate specific tax type using legislative rules
        """
        # Get applicable rules for this tax type
        rules = await self.legislative_db.get_applicable_tax_rules(
            tax_type=tax_type,
            entity_type=entity_type,
            effective_date=date(tax_year, 1, 1)
        )
        
        if not rules:
            return None
        
        # Calculate based on tax type
        if tax_type == TaxType.CIT:
            return await self._calculate_cit_legislative(data, rules)
        elif tax_type == TaxType.PIT:
            return await self._calculate_pit_legislative(data, rules)
        elif tax_type == TaxType.VAT:
            return await self._calculate_vat_legislative(data, rules)
        elif tax_type == TaxType.CGT:
            return await self._calculate_cgt_legislative(data, rules)
        elif tax_type == TaxType.TET:
            return await self._calculate_tet_legislative(data, rules)
        elif tax_type == TaxType.DEV_LEVY:
            return await self._calculate_dev_levy_legislative(data, rules)
        
        return None
    
    async def _calculate_cit_legislative(
        self, 
        data: Dict[str, Any], 
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate Companies Income Tax per Nigeria Tax Act 2025
        """
        turnover = Decimal(str(data.get('annual_turnover', 0)))
        gross_profit = Decimal(str(data.get('annual_profit', turnover * Decimal('0.2'))))
        
        # Apply allowable deductions
        allowable_deductions = self._calculate_allowable_deductions(data)
        
        # Apply loss relief if applicable
        brought_forward_losses = Decimal(str(data.get('brought_forward_losses', 0)))
        
        taxable_profit = max(Decimal('0'), gross_profit - allowable_deductions - brought_forward_losses)
        
        # Determine applicable CIT rate based on turnover
        cit_rate = Decimal('0.30')  # Default large company rate
        
        # Find matching rule
        applicable_rule = None
        for rule in rules:
            if rule['rule_code'].startswith('CIT_'):
                if self._evaluate_rule_condition(rule, {'annual_turnover': float(turnover)}):
                    applicable_rule = rule
                    cit_rate = Decimal(str(rule['rate'] or '0.30'))
                    break
        
        cit_amount = taxable_profit * cit_rate
        
        # Prepare legal citations
        legal_citations = []
        if applicable_rule:
            legal_citations.append({
                "section": applicable_rule.get('section_reference', ''),
                "description": applicable_rule.get('citation_text', ''),
                "applies_to": "CIT rate determination"
            })
        
        # Add deduction citations
        if allowable_deductions > 0:
            legal_citations.append({
                "section": "Nigeria Tax Act 2025, Section 45",
                "description": "Allowable business expense deductions",
                "applies_to": "Deductions calculation"
            })
        
        if brought_forward_losses > 0:
            legal_citations.append({
                "section": "Nigeria Tax Act 2025, Section 47",
                "description": "Loss relief provisions",
                "applies_to": "Loss set-off"
            })
        
        return {
            "tax_type": "CIT",
            "company_size": self._determine_company_size(turnover),
            "turnover": float(turnover),
            "gross_profit": float(gross_profit),
            "allowable_deductions": float(allowable_deductions),
            "brought_forward_losses": float(brought_forward_losses),
            "taxable_profit": float(taxable_profit),
            "cit_rate": float(cit_rate),
            "amount": float(cit_amount),
            "legal_citations": legal_citations
        }
    
    async def _calculate_pit_legislative(
        self, 
        data: Dict[str, Any], 
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate Personal Income Tax per Nigeria Tax Act 2025
        Progressive tax bands with Consolidated Relief Allowance
        """
        annual_income = Decimal(str(data.get('annual_turnover', data.get('annual_income', 0))))
        
        # Apply Consolidated Relief Allowance (CRA)
        # Greater of ₦200,000 or 1% of gross income + 20% of gross income
        cra = max(
            Decimal('200000'),
            (annual_income * Decimal('0.01')) + (annual_income * Decimal('0.20'))
        )
        
        # Apply pension deductions if applicable
        pension_contributions = Decimal(str(data.get('pension_contributions', 0)))
        
        taxable_income = max(Decimal('0'), annual_income - cra - pension_contributions)
        
        # Progressive tax bands (from legislation)
        bands = [
            (Decimal('300000'), Decimal('0.07'), "First ₦300,000"),
            (Decimal('300000'), Decimal('0.11'), "Next ₦300,000"),
            (Decimal('500000'), Decimal('0.15'), "Next ₦500,000"),
            (Decimal('500000'), Decimal('0.19'), "Next ₦500,000"),
            (Decimal('1600000'), Decimal('0.21'), "Next ₦1,600,000"),
            (None, Decimal('0.24'), "Above ₦3,200,000")
        ]
        
        # Calculate tax per band
        remaining_income = taxable_income
        band_calculations = []
        total_pit = Decimal('0')
        
        for band_limit, rate, description in bands:
            if remaining_income <= 0:
                break
            
            if band_limit:
                taxable_in_band = min(remaining_income, band_limit)
            else:
                taxable_in_band = remaining_income
            
            tax_in_band = taxable_in_band * rate
            total_pit += tax_in_band
            
            band_calculations.append({
                "band": description,
                "taxable_amount": float(taxable_in_band),
                "rate": float(rate),
                "tax_amount": float(tax_in_band)
            })
            
            remaining_income -= taxable_in_band
        
        return {
            "tax_type": "PIT",
            "annual_income": float(annual_income),
            "consolidated_relief_allowance": float(cra),
            "pension_deductions": float(pension_contributions),
            "taxable_income": float(taxable_income),
            "band_breakdown": band_calculations,
            "amount": float(total_pit),
            "legal_citations": [
                {
                    "section": "Nigeria Tax Act 2025, Section 34",
                    "description": "Progressive Personal Income Tax rates",
                    "applies_to": "PIT rate bands"
                },
                {
                    "section": "Nigeria Tax Act 2025, Section 35",
                    "description": "Consolidated Relief Allowance",
                    "applies_to": "CRA calculation"
                },
                {
                    "section": "Pension Reform Act 2024",
                    "description": "Pension contribution deductions",
                    "applies_to": "Pension deductions"
                }
            ]
        }
    
    async def _calculate_vat_legislative(
        self, 
        data: Dict[str, Any], 
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate Value Added Tax per Nigeria Tax Act 2025
        """
        vat_supplies = Decimal(str(data.get('vat_taxable_supplies', 0)))
        
        # Check for digital export exemption
        exports_digital = data.get('exports_digital_services', False)
        export_revenue = Decimal(str(data.get('export_revenue', 0)))
        
        if exports_digital:
            # 0% VAT on digital exports
            vat_rate = Decimal('0.00')
            vat_amount = Decimal('0')
            applicable_rule_desc = "0% VAT on digital service exports"
            section_ref = "Nigeria Tax Act 2025, Section 33(c)"
        else:
            # Standard 7.5% VAT
            vat_rate = Decimal('0.075')
            vat_amount = vat_supplies * vat_rate
            applicable_rule_desc = "Standard VAT rate 7.5%"
            section_ref = "Nigeria Tax Act 2025, Section 33"
        
        # Check registration threshold (₦25M)
        registration_threshold = Decimal('25000000')
        requires_registration = vat_supplies >= registration_threshold
        
        return {
            "tax_type": "VAT",
            "taxable_supplies": float(vat_supplies),
            "export_revenue": float(export_revenue),
            "vat_rate": float(vat_rate),
            "amount": float(vat_amount),
            "requires_registration": requires_registration,
            "registration_threshold": float(registration_threshold),
            "legal_citations": [
                {
                    "section": section_ref,
                    "description": applicable_rule_desc,
                    "applies_to": "VAT rate determination"
                },
                {
                    "section": "Nigeria Tax Act 2025, Section 32",
                    "description": "VAT registration threshold of ₦25M",
                    "applies_to": "Registration requirement"
                }
            ]
        }
    
    async def _calculate_cgt_legislative(
        self, 
        data: Dict[str, Any], 
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate Capital Gains Tax per Nigeria Tax Act 2025
        Special focus on digital assets
        """
        digital_gains = Decimal(str(data.get('digital_asset_gains', 0)))
        cgt_rate = Decimal('0.10')  # 10% for digital assets
        
        cgt_amount = digital_gains * cgt_rate
        
        return {
            "tax_type": "CGT_DIGITAL",
            "digital_asset_gains": float(digital_gains),
            "cgt_rate": float(cgt_rate),
            "amount": float(cgt_amount),
            "legal_citations": [
                {
                    "section": "Nigeria Tax Act 2025, Section 56",
                    "description": "Capital Gains Tax on digital assets at 10%",
                    "applies_to": "CGT calculation"
                }
            ]
        }
    
    async def _calculate_tet_legislative(
        self, 
        data: Dict[str, Any], 
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate Tertiary Education Tax per Nigeria Tax Act 2025
        2% of assessable profits
        """
        assessable_profit = Decimal(str(data.get('annual_profit', 0)))
        tet_rate = Decimal('0.02')
        
        tet_amount = assessable_profit * tet_rate
        
        return {
            "tax_type": "TET",
            "assessable_profit": float(assessable_profit),
            "tet_rate": float(tet_rate),
            "amount": float(tet_amount),
            "legal_citations": [
                {
                    "section": "Nigeria Tax Act 2025, Section 78",
                    "description": "Tertiary Education Tax at 2% of assessable profits",
                    "applies_to": "TET calculation"
                }
            ]
        }
    
    async def _calculate_dev_levy_legislative(
        self, 
        data: Dict[str, Any], 
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate Development Levy for large companies
        """
        turnover = Decimal(str(data.get('annual_turnover', 0)))
        
        # Only applies to companies with turnover > ₦100M
        if turnover < Decimal('100000000'):
            return {
                "tax_type": "DEV_LEVY",
                "applicable": False,
                "reason": "Turnover below ₦100M threshold",
                "amount": 0.0,
                "legal_citations": []
            }
        
        levy_rate = Decimal('0.04')  # 4% development levy
        levy_amount = turnover * levy_rate
        
        return {
            "tax_type": "DEV_LEVY",
            "applicable": True,
            "turnover": float(turnover),
            "levy_rate": float(levy_rate),
            "amount": float(levy_amount),
            "legal_citations": [
                {
                    "section": "Development Levy Act",
                    "description": "4% development levy on companies with turnover > ₦100M",
                    "applies_to": "Development levy calculation"
                }
            ]
        }
    
    def _calculate_allowable_deductions(self, data: Dict[str, Any]) -> Decimal:
        """
        Calculate total allowable deductions per Tax Act
        """
        deductions = Decimal('0')
        
        # R&D expenses (up to 5% of turnover)
        rnd_expenses = Decimal(str(data.get('rnd_expenses', 0)))
        turnover = Decimal(str(data.get('annual_turnover', 0)))
        max_rnd_deduction = turnover * Decimal('0.05')
        rnd_deduction = min(rnd_expenses, max_rnd_deduction)
        deductions += rnd_deduction
        
        # Capital allowances
        capital_allowances = Decimal(str(data.get('capital_allowances', 0)))
        deductions += capital_allowances
        
        # Pension contributions
        pension_contributions = Decimal(str(data.get('pension_contributions', 0)))
        deductions += pension_contributions
        
        return deductions
    
    def _determine_company_size(self, turnover: Decimal) -> str:
        """Determine company size per Nigerian classification"""
        if turnover < Decimal('100000000'):
            return "small"
        elif turnover < Decimal('500000000'):
            return "medium"
        else:
            return "large"
    
    def _evaluate_rule_condition(
        self, 
        rule: Dict[str, Any], 
        data: Dict[str, Any]
    ) -> bool:
        """
        Evaluate if rule condition matches data
        """
        condition = rule.get('condition_logic')
        if not condition:
            return True
        
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        if field not in data:
            return False
        
        data_value = Decimal(str(data[field]))
        
        if operator == '<':
            return data_value < Decimal(str(value))
        elif operator == '<=':
            return data_value <= Decimal(str(value))
        elif operator == '>':
            return data_value > Decimal(str(value))
        elif operator == '>=':
            return data_value >= Decimal(str(value))
        elif operator == '=':
            return data_value == Decimal(str(value))
        elif operator == 'between':
            min_val = Decimal(str(condition.get('min', 0)))
            max_val = Decimal(str(condition.get('max', float('inf'))))
            return min_val <= data_value <= max_val
        
        return False
    
    def _identify_applicable_taxes(
        self, 
        entity_type: str, 
        data: Dict[str, Any]
    ) -> List[str]:
        """
        Identify which taxes apply to this entity
        """
        taxes = []
        
        if entity_type in ['company', 'partnership']:
            taxes.append(TaxType.CIT)
            taxes.append(TaxType.TET)
            
            # Development levy for large companies
            turnover = Decimal(str(data.get('annual_turnover', 0)))
            if turnover >= Decimal('100000000'):
                taxes.append(TaxType.DEV_LEVY)
        
        elif entity_type == 'individual':
            taxes.append(TaxType.PIT)
        
        # VAT if applicable
        vat_supplies = Decimal(str(data.get('vat_taxable_supplies', 0)))
        if vat_supplies > 0:
            taxes.append(TaxType.VAT)
        
        # CGT on digital assets
        digital_gains = Decimal(str(data.get('digital_asset_gains', 0)))
        if digital_gains > 0:
            taxes.append(TaxType.CGT)
        
        return taxes
    
    async def _generate_recommendations(
        self,
        entity_type: str,
        data: Dict[str, Any],
        breakdown: Dict[str, Any],
        exemptions: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable tax recommendations"""
        recommendations = []
        
        turnover = Decimal(str(data.get('annual_turnover', 0)))
        
        # Small company exemption recommendation
        if entity_type == 'company' and turnover < Decimal('100000000'):
            has_small_co_exemption = any(
                e.get('exemption_code') == 'SMALL_CO_EXEMPTION' 
                for e in exemptions
            )
            if not has_small_co_exemption:
                recommendations.append(
                    "✅ You qualify for Small Company 0% CIT Exemption! "
                    "Register with CAC and file audited accounts to claim."
                )
        
        # R&D deduction opportunity
        if data.get('rnd_expenses', 0) == 0 and turnover > Decimal('50000000'):
            recommendations.append(
                "💡 Consider documenting R&D expenses - "
                "You can deduct up to 5% of turnover (₦{:,})".format(
                    float(turnover * Decimal('0.05'))
                )
            )
        
        # Digital export VAT exemption
        if not data.get('exports_digital_services') and turnover > Decimal('10000000'):
            recommendations.append(
                "🌍 Explore digital service exports - "
                "Qualify for 0% VAT on export revenue."
            )
        
        # Pension contributions
        if data.get('employee_count', 0) > 0 and data.get('pension_contributions', 0) == 0:
            recommendations.append(
                "📊 Set up employer pension scheme - "
                "Contributions are tax-deductible."
            )
        
        # VAT registration
        vat_supplies = Decimal(str(data.get('vat_taxable_supplies', 0)))
        if vat_supplies >= Decimal('25000000'):
            recommendations.append(
                "⚠️ VAT registration required - "
                "Your taxable supplies exceed ₦25M threshold."
            )
        
        return recommendations
    
    async def _identify_compliance_risks(
        self,
        entity_type: str,
        data: Dict[str, Any],
        breakdown: Dict[str, Any]
    ) -> List[str]:
        """Identify compliance risk flags"""
        risks = []
        
        # Missing TIN
        if not data.get('tin_number') and entity_type != 'individual':
            risks.append(
                "🚨 No Tax Identification Number (TIN) found. "
                "Register with FIRS to avoid ₦100,000 penalty."
            )
        
        # High effective tax rate
        turnover = Decimal(str(data.get('annual_turnover', 1)))
        if turnover > 0:
            total_tax = sum(item.get('amount', 0) for item in breakdown.values())
            effective_rate = (total_tax / turnover) * 100
            if effective_rate > 35:
                risks.append(
                    f"📈 High effective tax rate ({effective_rate:.1f}%). "
                    "Review available exemptions and deductions."
                )
        
        # Overdue filings
        last_filing = data.get('last_filing_date')
        if last_filing:
            try:
                last_date = datetime.fromisoformat(last_filing.replace('Z', '+00:00')).date()
                days_since = (date.today() - last_date).days
                if days_since > 365:
                    risks.append(
                        f"⏰ Tax filing overdue by {days_since - 365} days. "
                        "Late filing penalty: 10% of tax due + interest."
                    )
            except:
                pass
        
        return risks
    
    def _calculate_confidence_score(self, data: Dict[str, Any]) -> float:
        """Calculate confidence score (0.0 to 1.0)"""
        score = 1.0
        
        # Deduct for missing critical data
        required_fields = ['annual_turnover', 'entity_type']
        
        for field in required_fields:
            if field not in data or not data[field]:
                score -= 0.3
        
        if not data.get('annual_profit'):
            score -= 0.2
        
        # Additional completeness checks
        if data.get('entity_type') == 'company' and not data.get('industry_sector'):
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _deduplicate_citations(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate citations"""
        seen = set()
        unique = []
        
        for citation in citations:
            key = f"{citation.get('section', '')}-{citation.get('description', '')}"
            if key not in seen:
                seen.add(key)
                unique.append(citation)
        
        return unique
    
    # ============================================
    # ADVANCED SCENARIO MODELING
    # ============================================
    
    async def model_tax_scenario(
        self,
        baseline_data: Dict[str, Any],
        scenario_data: Dict[str, Any],
        scenario_name: str,
        timeframe_years: int = 5
    ) -> Dict[str, Any]:
        """
        Model tax scenario with temporal projection
        """
        baseline_result = await self.calculate_comprehensive_tax(
            baseline_data.get('entity_type', 'company'),
            baseline_data
        )
        
        scenario_result = await self.calculate_comprehensive_tax(
            scenario_data.get('entity_type', baseline_data.get('entity_type', 'company')),
            scenario_data
        )
        
        # Calculate variance
        liability_change = scenario_result['total_liability'] - baseline_result['total_liability']
        liability_change_pct = (
            (liability_change / baseline_result['total_liability']) * 100 
            if baseline_result['total_liability'] > 0 else 0
        )
        
        # Generate temporal projection
        temporal_projection = await self._generate_temporal_projection(
            baseline_data, scenario_data, timeframe_years
        )
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            baseline_result, scenario_result, liability_change
        )
        
        return {
            "scenario_name": scenario_name,
            "baseline_analysis": baseline_result,
            "scenario_analysis": scenario_result,
            "variance_analysis": {
                "liability_change": liability_change,
                "liability_change_pct": liability_change_pct,
                "savings_change": scenario_result['total_savings'] - baseline_result['total_savings'],
                "effective_rate_change": scenario_result['effective_tax_rate'] - baseline_result['effective_tax_rate']
            },
            "temporal_projection": temporal_projection,
            "executive_summary": executive_summary,
            "key_decision_points": self._identify_decision_points(
                baseline_result, scenario_result
            ),
            "recommended_actions": self._generate_scenario_recommendations(
                baseline_result, scenario_result
            )
        }
    
    async def _generate_temporal_projection(
        self,
        baseline: Dict[str, Any],
        scenario: Dict[str, Any],
        years: int
    ) -> List[Dict[str, Any]]:
        """
        Generate multi-year tax projection
        """
        projection = []
        
        for year in range(1, years + 1):
            # Project growth (simplified - in production, use business logic)
            year_multiplier = Decimal('1.0') + (Decimal(str(scenario.get('growth_rate', 0.1))) * Decimal(str(year)))
            
            # Project data for this year
            year_data = {}
            for key, value in scenario.items():
                if isinstance(value, (int, float)) and key not in ['growth_rate', 'employee_count']:
                    year_data[key] = float(Decimal(str(value)) * year_multiplier)
                else:
                    year_data[key] = value
            
            # Calculate tax for projected year
            year_result = await self.calculate_comprehensive_tax(
                year_data.get('entity_type', baseline.get('entity_type', 'company')),
                year_data
            )
            
            projection.append({
                "year": datetime.now().year + year,
                "projected_data": year_data,
                "tax_projection": year_result,
                "cumulative_tax": sum(p['tax_projection']['total_liability'] for p in projection) + year_result['total_liability']
            })
        
        return projection
    
    def _generate_executive_summary(
        self,
        baseline: Dict[str, Any],
        scenario: Dict[str, Any],
        liability_change: float
    ) -> str:
        """
        Generate executive summary for scenario
        """
        if liability_change < 0:
            return (
                f"✅ **TAX SAVINGS OPPORTUNITY**\n\n"
                f"This scenario **reduces your annual tax liability by ₦{abs(liability_change):,.2f}** "
                f"({abs(liability_change / baseline['total_liability'] * 100):.1f}%). "
                f"Your effective tax rate drops from {baseline['effective_tax_rate']:.1f}% to "
                f"{scenario['effective_tax_rate']:.1f}%.\n\n"
                f"**Key Benefits:**\n"
                f"• Annual tax savings: ₦{abs(liability_change):,.2f}\n"
                f"• Improved cash flow\n"
                f"• Better compliance position"
            )
        elif liability_change > 0:
            return (
                f"⚠️ **TAX INCREASE WARNING**\n\n"
                f"This scenario **increases your annual tax liability by ₦{liability_change:,.2f}** "
                f"({liability_change / baseline['total_liability'] * 100:.1f}%). "
                f"Your effective tax rate rises from {baseline['effective_tax_rate']:.1f}% to "
                f"{scenario['effective_tax_rate']:.1f}%.\n\n"
                f"**Considerations:**\n"
                f"• Additional annual tax cost: ₦{liability_change:,.2f}\n"
                f"• Impact on profitability\n"
                f"• Alternative strategies available"
            )
        else:
            return (
                f"➡️ **NEUTRAL TAX IMPACT**\n\n"
                f"This scenario has minimal impact on your tax liability. "
                f"Your effective tax rate remains at {baseline['effective_tax_rate']:.1f}%.\n\n"
                f"**Recommendation:** Evaluate non-tax benefits before proceeding."
            )
    
    def _identify_decision_points(
        self,
        baseline: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Identify key decision points from scenario analysis
        """
        decision_points = []
        
        # CIT rate change
        if 'cit' in baseline.get('breakdown', {}) and 'cit' in scenario.get('breakdown', {}):
            baseline_cit = baseline['breakdown']['cit'].get('cit_rate', 0)
            scenario_cit = scenario['breakdown']['cit'].get('cit_rate', 0)
            
            if baseline_cit != scenario_cit:
                decision_points.append({
                    "decision": "Company Size Classification",
                    "impact": f"CIT rate changes from {baseline_cit*100:.1f}% to {scenario_cit*100:.1f}%",
                    "action": "Review turnover management strategies",
                    "priority": "high" if scenario_cit > baseline_cit else "medium"
                })
        
        # Exemption qualification
        baseline_exemptions = len(baseline.get('exemptions_applied', []))
        scenario_exemptions = len(scenario.get('exemptions_applied', []))
        
        if scenario_exemptions > baseline_exemptions:
            decision_points.append({
                "decision": "Exemption Qualification",
                "impact": f"Qualify for {scenario_exemptions - baseline_exemptions} additional exemptions",
                "action": "Gather required documentation and apply",
                "priority": "high"
            })
        
        # VAT registration requirement
        if 'vat' in scenario.get('breakdown', {}):
            requires_registration = scenario['breakdown']['vat'].get('requires_registration', False)
            if requires_registration:
                decision_points.append({
                    "decision": "VAT Registration",
                    "impact": "Required to register for VAT (₦25M threshold exceeded)",
                    "action": "Register with FIRS within 30 days",
                    "priority": "critical"
                })
        
        return decision_points
    
    def _generate_scenario_recommendations(
        self,
        baseline: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> List[str]:
        """
        Generate scenario-specific recommendations
        """
        recommendations = []
        
        # Check for new exemptions in scenario
        scenario_exemption_codes = {
            e.get('exemption_code') 
            for e in scenario.get('exemptions_applied', [])
        }
        
        baseline_exemption_codes = {
            e.get('exemption_code') 
            for e in baseline.get('exemptions_applied', [])
        }
        
        new_exemptions = scenario_exemption_codes - baseline_exemption_codes
        
        for exemption_code in new_exemptions:
            if exemption_code == 'SMALL_CO_EXEMPTION':
                recommendations.append(
                    "🎯 **Claim Small Company Exemption**: "
                    "File audited accounts and apply for 0% CIT status with FIRS."
                )
            elif exemption_code == 'DIGITAL_EXPORT_VAT':
                recommendations.append(
                    "🌍 **Register for 0% VAT on Exports**: "
                    "Document export revenue and apply for VAT exemption."
                )
            elif exemption_code == 'RND_DEDUCTION_5PCT':
                recommendations.append(
                    "🔬 **Document R&D Expenses**: "
                    "Formalize R&D documentation to claim up to 5% turnover deduction."
                )
        
        # VAT registration recommendation
        if 'vat' in scenario.get('breakdown', {}):
            vat_breakdown = scenario['breakdown']['vat']
            if vat_breakdown.get('requires_registration', False):
                recommendations.append(
                    "📋 **Immediate VAT Registration**: "
                    "Register with FIRS to avoid ₦100,000 penalty for non-registration."
                )
        
        return recommendations