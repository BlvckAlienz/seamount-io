-- backend/database/migrations/003_tax_legislation_tables.sql
-- 🚀 Nigerian Tax Act 2025 Legislative Database Schema
-- Run this migration to enable legislative tax calculations

BEGIN;

-- ============================================
-- CORE LEGISLATIVE TABLES
-- ============================================

CREATE TABLE IF NOT EXISTS tax_legislation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code VARCHAR(50) UNIQUE NOT NULL,
    rule_name VARCHAR(200) NOT NULL,
    rule_description TEXT,
    
    -- Rule categorization
    tax_type VARCHAR(20) NOT NULL CHECK (tax_type IN ('CIT', 'PIT', 'VAT', 'CGT', 'TET', 'WHT', 'DEV_LEVY', 'STAMP_DUTY')),
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('company', 'individual', 'partnership', 'all')),
    applies_to_sector VARCHAR(100),
    
    -- Rule logic
    condition_logic JSONB,
    calculation_formula VARCHAR(500),
    rate DECIMAL(5,3),
    min_amount DECIMAL(15,2),
    max_amount DECIMAL(15,2),
    min_threshold DECIMAL(15,2),
    max_threshold DECIMAL(15,2),
    
    -- Legal references
    act_name VARCHAR(200) NOT NULL,
    section_reference VARCHAR(50),
    subsection VARCHAR(100),
    citation_text TEXT,
    
    -- Temporal validity
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expiration_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes separately (this is the FIX)
CREATE INDEX IF NOT EXISTS idx_tax_legislation_tax_type ON tax_legislation_rules(tax_type);
CREATE INDEX IF NOT EXISTS idx_tax_legislation_entity ON tax_legislation_rules(entity_type);
CREATE INDEX IF NOT EXISTS idx_tax_legislation_active ON tax_legislation_rules(is_active, effective_date);

CREATE TABLE IF NOT EXISTS tax_exemption_criteria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exemption_code VARCHAR(50) UNIQUE NOT NULL,
    exemption_name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    
    -- Qualification logic
    qualification_logic JSONB NOT NULL, -- {"conditions": [{"field": "annual_turnover", "operator": "<", "value": 100000000}]}
    required_documents TEXT[],
    
    -- Tax impact
    applies_to_tax_types VARCHAR(20)[] NOT NULL, -- e.g., {'CIT', 'TET'}
    savings_calculation_formula VARCHAR(500), -- e.g., "taxable_profit * 0.30"
    max_savings_amount DECIMAL(15,2),
    savings_validity_months INTEGER, -- e.g., 60 for 5-year exemption
    
    -- Legal references
    act_name VARCHAR(200) NOT NULL,
    section_reference VARCHAR(50) NOT NULL,
    citation_text TEXT NOT NULL,
    
    -- Temporal
    effective_date DATE NOT NULL,
    expiration_date DATE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS penalty_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    penalty_code VARCHAR(50) UNIQUE NOT NULL,
    violation_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    
    -- Penalty calculation
    calculation_type VARCHAR(20) NOT NULL CHECK (calculation_type IN ('percentage', 'fixed', 'tiered')),
    penalty_rate DECIMAL(5,3), -- e.g., 0.10 for 10%
    fixed_amount DECIMAL(15,2),
    tiered_rates JSONB, -- {"tiers": [{"min": 0, "max": 1000000, "rate": 0.05}]}
    
    -- Additional consequences
    includes_interest BOOLEAN DEFAULT FALSE,
    interest_rate DECIMAL(5,3), -- e.g., 0.21 for 21%
    criminal_liability BOOLEAN DEFAULT FALSE,
    suspension_possible BOOLEAN DEFAULT FALSE,
    
    -- Legal references
    act_name VARCHAR(200) NOT NULL,
    section_reference VARCHAR(50) NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tax_calculation_formulas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    formula_code VARCHAR(50) UNIQUE NOT NULL,
    formula_name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Mathematical representation
    formula_expression VARCHAR(500) NOT NULL, -- e.g., "(annual_profit - allowable_deductions) * cit_rate"
    variables JSONB NOT NULL, -- [{"name": "annual_profit", "type": "decimal"}, ...]
    
    -- Applicability
    applies_to_tax_types VARCHAR(20)[],
    applies_to_entity_types VARCHAR(20)[],
    
    -- Example with Nigerian numbers
    example_calculation JSONB, -- {"inputs": {"annual_profit": 50000000, "allowable_deductions": 10000000}, "output": 12000000}
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- TAX PROFILE ENHANCEMENTS
-- ============================================

-- Add new columns to existing user_tax_profiles table
ALTER TABLE user_tax_profiles 
ADD COLUMN IF NOT EXISTS tin_number VARCHAR(20),
ADD COLUMN IF NOT EXISTS registration_date DATE,
ADD COLUMN IF NOT EXISTS last_filing_date DATE,
ADD COLUMN IF NOT EXISTS next_filing_date DATE,
ADD COLUMN IF NOT EXISTS has_pioneer_status BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS pioneer_status_expiry DATE,
ADD COLUMN IF NOT EXISTS is_startup BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS startup_incorporation_date DATE,
ADD COLUMN IF NOT EXISTS in_free_trade_zone BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS capital_allowances DECIMAL(15,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS brought_forward_losses DECIMAL(15,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS export_revenue DECIMAL(15,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS pension_contributions DECIMAL(15,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS employees_below_min_wage INTEGER DEFAULT 0;

-- ============================================
-- INSERT SAMPLE DATA FROM NIGERIAN TAX ACT 2025
-- ============================================

-- Companies Income Tax (CIT) Rules
INSERT INTO tax_legislation_rules (rule_code, rule_name, tax_type, entity_type, condition_logic, calculation_formula, rate, min_threshold, act_name, section_reference, citation_text) VALUES
-- Small Company Exemption
('CIT_SMALL_0PCT', 'Small Company 0% CIT', 'CIT', 'company', 
 '{"field": "annual_turnover", "operator": "<", "value": 100000000}', 
 'taxable_profit * 0.00', 0.000, 0, 'Nigeria Tax Act 2025', 'Section 23(a)', 
 'Companies with annual turnover below ₦100,000,000 qualify for 0% Companies Income Tax.'),
 
-- Medium Company Rate
('CIT_MEDIUM_20PCT', 'Medium Company 20% CIT', 'CIT', 'company', 
 '{"field": "annual_turnover", "operator": "between", "min": 100000000, "max": 500000000}', 
 'taxable_profit * 0.20', 0.200, 100000000, 'Nigeria Tax Act 2025', 'Section 23(b)', 
 'Companies with turnover between ₦100M and ₦500M pay 20% CIT.'),
 
-- Large Company Rate
('CIT_LARGE_30PCT', 'Large Company 30% CIT', 'CIT', 'company', 
 '{"field": "annual_turnover", "operator": ">=", "value": 500000000}', 
 'taxable_profit * 0.30', 0.300, 500000000, 'Nigeria Tax Act 2025', 'Section 23(c)', 
 'Companies with turnover of ₦500M or more pay 30% CIT.'),

-- R&D Deduction
('CIT_RND_DEDUCTION', 'R&D Expense Deduction', 'CIT', 'company', 
 '{"field": "rnd_expenses", "operator": ">", "value": 0}', 
 'MIN(rnd_expenses, annual_turnover * 0.05)', NULL, 0, 'Nigeria Tax Act 2025', 'Section 45(c)', 
 'R&D expenses are deductible up to 5% of annual turnover.'),

-- Value Added Tax (VAT) Rules
('VAT_STANDARD_7.5PCT', 'Standard VAT Rate', 'VAT', 'all', 
 '{"field": "vat_taxable_supplies", "operator": ">", "value": 0}', 
 'vat_taxable_supplies * 0.075', 0.075, 25000000, 'Nigeria Tax Act 2025', 'Section 33', 
 'Standard VAT rate is 7.5% on taxable supplies above ₦25M threshold.'),

('VAT_DIGITAL_EXPORT_0PCT', 'Digital Export 0% VAT', 'VAT', 'all', 
 '{"field": "exports_digital_services", "operator": "=", "value": true}', 
 'export_revenue * 0.00', 0.000, 0, 'Nigeria Tax Act 2025', 'Section 33(c)', 
 'Digital service exports to foreign clients qualify for 0% VAT.'),

-- Personal Income Tax (PIT) Bands
('PIT_BAND_7PCT', 'First ₦300,000 PIT', 'PIT', 'individual', 
 '{"field": "taxable_income", "operator": ">", "value": 0}', 
 'MIN(taxable_income, 300000) * 0.07', 0.070, 0, 'Nigeria Tax Act 2025', 'Section 34(a)', 
 'First ₦300,000 of taxable income at 7% rate.'),

('PIT_BAND_11PCT', 'Next ₦300,000 PIT', 'PIT', 'individual', 
 '{"field": "taxable_income", "operator": ">", "value": 300000}', 
 'MIN(MAX(taxable_income - 300000, 0), 300000) * 0.11', 0.110, 300000, 'Nigeria Tax Act 2025', 'Section 34(b)', 
 'Next ₦300,000 of taxable income at 11% rate.'),

('PIT_BAND_15PCT', 'Next ₦500,000 PIT', 'PIT', 'individual', 
 '{"field": "taxable_income", "operator": ">", "value": 600000}', 
 'MIN(MAX(taxable_income - 600000, 0), 500000) * 0.15', 0.150, 600000, 'Nigeria Tax Act 2025', 'Section 34(c)', 
 'Next ₦500,000 of taxable income at 15% rate.'),

-- Capital Gains Tax on Digital Assets
('CGT_DIGITAL_10PCT', 'Digital Asset CGT', 'CGT', 'all', 
 '{"field": "digital_asset_gains", "operator": ">", "value": 0}', 
 'digital_asset_gains * 0.10', 0.100, 0, 'Nigeria Tax Act 2025', 'Section 56', 
 'Capital gains on digital assets taxed at 10%.'),

-- Tertiary Education Tax
('TET_STANDARD_2PCT', 'TET 2% on Profits', 'TET', 'company', 
 '{"field": "annual_profit", "operator": ">", "value": 0}', 
 'assessable_profit * 0.02', 0.020, 0, 'Nigeria Tax Act 2025', 'Section 78', 
 'Tertiary Education Tax at 2% of assessable profits.');

-- Insert exemption criteria
INSERT INTO tax_exemption_criteria (exemption_code, exemption_name, description, qualification_logic, required_documents, applies_to_tax_types, savings_calculation_formula, act_name, section_reference, citation_text, effective_date) VALUES
('SMALL_CO_EXEMPTION', 'Small Company 0% CIT', '0% CIT for companies with turnover < ₦100M', 
 '{"conditions": [{"field": "entity_type", "operator": "=", "value": "company"}, {"field": "annual_turnover", "operator": "<", "value": 100000000}]}', 
 '{"Audited Financial Statements", "Tax Clearance Certificate"}', 
 '{"CIT"}', 
 'annual_profit * 0.30', 
 'Nigeria Tax Act 2025', 'Section 23(a)', 
 'Small companies (turnover < ₦100M) exempt from CIT for first 5 years.', '2025-01-01'),

('AGRIC_TAX_HOLIDAY', 'Agricultural Tax Holiday', '5-year tax exemption for agricultural businesses', 
 '{"conditions": [{"field": "industry_sector", "operator": "contains", "value": "agriculture"}, {"field": "entity_type", "operator": "=", "value": "company"}]}', 
 '{"Business License", "Agricultural Sector Registration"}', 
 '{"CIT", "TET"}', 
 'annual_profit * 0.30 * 5', 
 'Nigeria Tax Act 2025', 'Section 89', 
 'Agricultural businesses qualify for 5-year tax holiday.', '2025-01-01'),

('STARTUP_24MO_EXEMPT', 'Startup 24-Month Exemption', '24-month CIT exemption for registered startups', 
 '{"conditions": [{"field": "is_startup", "operator": "=", "value": true}, {"field": "months_since_incorporation", "operator": "<=", "value": 24}]}', 
 '{"CAC Certificate", "Startup Registration Certificate"}', 
 '{"CIT"}', 
 'annual_profit * 0.30 * 2', 
 'Nigeria Tax Act 2025', 'Section 92', 
 'Registered startups exempt from CIT for first 24 months.', '2025-01-01'),

('DIGITAL_EXPORT_VAT', 'Digital Export 0% VAT', '0% VAT on digital service exports', 
 '{"conditions": [{"field": "exports_digital_services", "operator": "=", "value": true}, {"field": "export_revenue", "operator": ">", "value": 0}]}', 
 '{"Export Invoices", "Foreign Exchange Receipts"}', 
 '{"VAT"}', 
 'export_revenue * 0.075', 
 'Nigeria Tax Act 2025', 'Section 33(c)', 
 'Digital service exports to foreign clients qualify for 0% VAT.', '2025-01-01'),

('RND_DEDUCTION_5PCT', 'R&D Expense Deduction', 'R&D expenses deductible up to 5% of turnover', 
 '{"conditions": [{"field": "rnd_expenses", "operator": ">", "value": 0}]}', 
 '{"R&D Expense Report", "Innovation Documentation"}', 
 '{"CIT"}', 
 'MIN(rnd_expenses, annual_turnover * 0.05) * 0.30', 
 'Nigeria Tax Act 2025', 'Section 45(c)', 
 'R&D expenses are deductible up to 5% of annual turnover.', '2025-01-01');

-- Insert penalty schedules from Tax Administration Act
INSERT INTO penalty_schedules (penalty_code, violation_type, description, calculation_type, penalty_rate, fixed_amount, includes_interest, interest_rate, act_name, section_reference) VALUES
('LATE_FILING_10PCT', 'Late Filing', 'Late filing penalty - 10% of tax due, min ₦50,000', 'percentage', 0.10, 50000, TRUE, 0.21, 'Nigeria Tax Administration Act 2025', 'Section 55'),
('LATE_PAYMENT_10PCT', 'Late Payment', 'Late payment penalty - 10% of tax due, min ₦50,000', 'percentage', 0.10, 50000, TRUE, 0.21, 'Nigeria Tax Administration Act 2025', 'Section 56'),
('NON_REGISTRATION_100K', 'Non-Registration', 'Failure to register for tax - ₦100,000 flat penalty', 'fixed', NULL, 100000, FALSE, NULL, 'Nigeria Tax Administration Act 2025', 'Section 34'),
('UNDER_DECLARATION_20PCT', 'Under-Declaration', 'Under-declaration penalty - 20% of undeclared amount', 'percentage', 0.20, 100000, TRUE, 0.21, 'Nigeria Tax Administration Act 2025', 'Section 78'),
('TAX_EVASION_100PCT', 'Tax Evasion', 'Tax evasion - 100% penalty + criminal prosecution', 'percentage', 1.00, 500000, TRUE, 0.21, 'Nigeria Tax Administration Act 2025', 'Section 102');

-- Insert calculation formulas
INSERT INTO tax_calculation_formulas (formula_code, formula_name, description, formula_expression, variables, applies_to_tax_types, example_calculation) VALUES
('CIT_BASE_FORMULA', 'Companies Income Tax Base', 'CIT calculation for companies', 
 '(annual_profit - allowable_deductions - brought_forward_losses) * cit_rate', 
 '[{"name": "annual_profit", "type": "decimal", "description": "Annual accounting profit"}, {"name": "allowable_deductions", "type": "decimal", "description": "Allowable expenses per Tax Act"}, {"name": "brought_forward_losses", "type": "decimal", "description": "Losses from previous years"}, {"name": "cit_rate", "type": "decimal", "description": "Applicable CIT rate"}]', 
 '{"CIT"}', 
 '{"inputs": {"annual_profit": 50000000, "allowable_deductions": 10000000, "brought_forward_losses": 5000000, "cit_rate": 0.30}, "output": 10500000}'),

('PIT_PROGRESSIVE_FORMULA', 'Progressive PIT Calculation', 'Progressive PIT calculation for individuals', 
 'SUM(band_taxable_amount * band_rate)', 
 '[{"name": "taxable_income", "type": "decimal", "description": "Income after allowances"}, {"name": "bands", "type": "array", "description": "Progressive tax bands"}]', 
 '{"PIT"}', 
 '{"inputs": {"taxable_income": 4000000, "bands": [{"limit": 300000, "rate": 0.07}, {"limit": 300000, "rate": 0.11}, {"limit": 500000, "rate": 0.15}]}, "output": 515000}'),

('VAT_SIMPLE_FORMULA', 'VAT Net Calculation', 'VAT payable calculation', 
 'output_vat - input_vat', 
 '[{"name": "output_vat", "type": "decimal", "description": "VAT on sales/supplies"}, {"name": "input_vat", "type": "decimal", "description": "VAT on purchases"}]', 
 '{"VAT"}', 
 '{"inputs": {"output_vat": 750000, "input_vat": 300000}, "output": 450000}'),

('TET_SIMPLE_FORMULA', 'Tertiary Education Tax', 'TET calculation for companies', 
 'assessable_profit * 0.02', 
 '[{"name": "assessable_profit", "type": "decimal", "description": "Profit after adjustments"}]', 
 '{"TET"}', 
 '{"inputs": {"assessable_profit": 50000000}, "output": 1000000}');

COMMIT;