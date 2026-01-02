# backend/services/legislative_db_service.py
# 🎯 Enhanced Database Service for Legislative Tax Calculations

import logging
from typing import Dict, Any, List, Optional
from datetime import date
from decimal import Decimal
from enum import Enum

from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class TaxType(str, Enum):
    CIT = "CIT"
    PIT = "PIT"
    VAT = "VAT"
    CGT = "CGT"
    TET = "TET"
    WHT = "WHT"
    DEV_LEVY = "DEV_LEVY"

class LegislativeDBService:
    """Service for accessing legislative tax data from database"""
    
    def __init__(self, db: DatabaseService):
        self.db = db
    
    async def get_applicable_tax_rules(
        self, 
        tax_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        effective_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tax rules applicable to specific entity type and tax type
        """
        try:
            query = self.db.supabase.from_("tax_legislation_rules")\
                .select("*")\
                .eq("is_active", True)
            
            if tax_type:
                query = query.eq("tax_type", tax_type)
            
            if entity_type and entity_type != "all":
                query = query.in_("entity_type", [entity_type, "all"])
            
            if effective_date:
                query = query.lte("effective_date", effective_date.isoformat())
                query = query.or_(f"expiration_date.is.null,expiration_date.gte.{effective_date}")
            else:
                today = date.today().isoformat()
                query = query.lte("effective_date", today)
                query = query.or_("expiration_date.is.null,expiration_date.gte.{today}")
            
            result = await query.execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get tax rules: {e}")
            return []
    
    async def get_exemptions_for_profile(
        self, 
        profile_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get exemptions user qualifies for based on profile data
        Uses rule-based qualification logic from database
        """
        try:
            # Get all active exemptions
            exemptions = await self.db.supabase.from_("tax_exemption_criteria")\
                .select("*")\
                .eq("effective_date", "<=", date.today().isoformat())\
                .or_(f"expiration_date.is.null,expiration_date.gte.{date.today().isoformat()}")\
                .execute()
            
            qualified_exemptions = []
            
            for exemption in exemptions.data or []:
                if await self._evaluate_qualification_logic(
                    exemption.get('qualification_logic', {}), 
                    profile_data
                ):
                    # Calculate estimated savings
                    estimated_savings = await self._calculate_exemption_savings(
                        exemption, 
                        profile_data
                    )
                    
                    qualified_exemptions.append({
                        **exemption,
                        "estimated_savings": float(estimated_savings),
                        "user_qualifies": True,
                        "status": "qualified"
                    })
            
            return qualified_exemptions
            
        except Exception as e:
            logger.error(f"Failed to get exemptions: {e}")
            return []
    
    async def get_penalty_for_violation(
        self, 
        violation_type: str,
        tax_liability: Optional[Decimal] = None,
        undeclared_amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Get penalty for specific violation type
        """
        try:
            result = await self.db.supabase.from_("penalty_schedules")\
                .select("*")\
                .eq("violation_type", violation_type)\
                .single()\
                .execute()
            
            if not result.data:
                return {}
            
            penalty_rule = result.data
            penalty_amount = Decimal('0')
            
            if penalty_rule['calculation_type'] == 'percentage':
                if penalty_rule['penalty_rate']:
                    base_amount = undeclared_amount if undeclared_amount else tax_liability
                    if base_amount:
                        penalty_amount = Decimal(str(base_amount)) * Decimal(str(penalty_rule['penalty_rate']))
                        
                        # Apply minimum if specified
                        if penalty_rule['fixed_amount']:
                            min_amount = Decimal(str(penalty_rule['fixed_amount']))
                            if penalty_amount < min_amount:
                                penalty_amount = min_amount
            elif penalty_rule['calculation_type'] == 'fixed':
                penalty_amount = Decimal(str(penalty_rule['fixed_amount']))
            
            # Add interest if applicable
            interest_amount = Decimal('0')
            if penalty_rule['includes_interest'] and penalty_rule['interest_rate']:
                # Simplified: 1 year interest for demonstration
                interest_amount = penalty_amount * Decimal(str(penalty_rule['interest_rate']))
            
            return {
                "violation_type": violation_type,
                "penalty_amount": float(penalty_amount),
                "interest_amount": float(interest_amount),
                "total_amount": float(penalty_amount + interest_amount),
                "description": penalty_rule['description'],
                "act_section": penalty_rule['section_reference'],
                "criminal_liability": penalty_rule.get('criminal_liability', False)
            }
            
        except Exception as e:
            logger.error(f"Failed to get penalty: {e}")
            return {}
    
    async def _evaluate_qualification_logic(
        self, 
        logic: Dict[str, Any], 
        profile: Dict[str, Any]
    ) -> bool:
        """
        Evaluate qualification logic against profile data
        """
        try:
            if not logic or 'conditions' not in logic:
                return False
            
            conditions = logic.get('conditions', [])
            
            for condition in conditions:
                field = condition.get('field')
                operator = condition.get('operator')
                value = condition.get('value')
                
                if field not in profile:
                    return False
                
                profile_value = profile[field]
                
                # Evaluate based on operator
                if operator == '=':
                    if profile_value != value:
                        return False
                elif operator == '>':
                    if not (Decimal(str(profile_value)) > Decimal(str(value))):
                        return False
                elif operator == '<':
                    if not (Decimal(str(profile_value)) < Decimal(str(value))):
                        return False
                elif operator == '>=':
                    if not (Decimal(str(profile_value)) >= Decimal(str(value))):
                        return False
                elif operator == '<=':
                    if not (Decimal(str(profile_value)) <= Decimal(str(value))):
                        return False
                elif operator == 'contains':
                    if value not in str(profile_value).lower():
                        return False
                elif operator == 'between':
                    min_val = condition.get('min')
                    max_val = condition.get('max')
                    if min_val and max_val:
                        profile_decimal = Decimal(str(profile_value))
                        if not (Decimal(str(min_val)) <= profile_decimal <= Decimal(str(max_val))):
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to evaluate qualification logic: {e}")
            return False
    
    async def _calculate_exemption_savings(
        self, 
        exemption: Dict[str, Any], 
        profile: Dict[str, Any]
    ) -> Decimal:
        """
        Calculate estimated savings for an exemption
        """
        try:
            formula = exemption.get('savings_calculation_formula')
            if not formula:
                return Decimal('0')
            
            # Simple formula evaluation (in production, use a proper expression evaluator)
            if "annual_profit * 0.30" in formula:
                annual_profit = Decimal(str(profile.get('annual_profit', 0)))
                return annual_profit * Decimal('0.30')
            elif "export_revenue * 0.075" in formula:
                export_revenue = Decimal(str(profile.get('export_revenue', 0)))
                return export_revenue * Decimal('0.075')
            elif "annual_profit * 0.30 * 5" in formula:
                annual_profit = Decimal(str(profile.get('annual_profit', 0)))
                return annual_profit * Decimal('0.30') * Decimal('5')
            elif "annual_profit * 0.30 * 2" in formula:
                annual_profit = Decimal(str(profile.get('annual_profit', 0)))
                return annual_profit * Decimal('0.30') * Decimal('2')
            else:
                return Decimal('0')
                
        except Exception as e:
            logger.error(f"Failed to calculate exemption savings: {e}")
            return Decimal('0')
    
    async def get_tax_calculation_formula(
        self, 
        formula_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get specific tax calculation formula
        """
        try:
            result = await self.db.supabase.from_("tax_calculation_formulas")\
                .select("*")\
                .eq("formula_code", formula_code)\
                .single()\
                .execute()
            
            return result.data if result.data else None
            
        except Exception as e:
            logger.error(f"Failed to get calculation formula: {e}")
            return None