-- ============================================
-- NIGERIAN TAX COMPLIANCE SYSTEM - DATABASE SCHEMA
-- ============================================

-- Set search path for all functions
SET search_path = public, pg_catalog;

-- ============================================
-- 1. TAX RULES REPOSITORY
-- Store provisions from Nigerian Tax Act
-- ============================================
CREATE TABLE IF NOT EXISTS public.tax_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code VARCHAR(50) UNIQUE NOT NULL, -- e.g., "CIT_SMALL_CO_2023"
    rule_category VARCHAR(50) NOT NULL, -- CIT, PIT, VAT, CGT, WHT, STAMP_DUTY
    act_section VARCHAR(100), -- "Finance Act 2023, Section 8(1)"
    description TEXT NOT NULL,
    
    -- Rule Logic (JSONB for flexibility)
    rule_logic JSONB NOT NULL,
    /* Example structure:
    {
        "condition": {"field": "annual_turnover", "operator": "<", "value": 100000000},
        "outcome": {"tax_rate": 0.00, "description": "0% CIT for turnover < N100M"},
        "effective_date": "2023-01-01",
        "sunset_date": null
    }
    */
    
    effective_from DATE NOT NULL,
    effective_until DATE, -- NULL means still active
    priority INTEGER DEFAULT 0, -- For rule conflict resolution
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tax_rules_category ON public.tax_rules(rule_category);
CREATE INDEX idx_tax_rules_active ON public.tax_rules(effective_from, effective_until) WHERE effective_until IS NULL;

-- ============================================
-- 2. USER TAX PROFILES
-- Comprehensive tax-relevant user data
-- ============================================
CREATE TABLE IF NOT EXISTS public.user_tax_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Entity Classification
    entity_type VARCHAR(50) NOT NULL, -- 'individual', 'company', 'partnership', 'trust'
    business_type VARCHAR(100), -- 'small_company', 'startup', 'agricultural', etc.
    industry_sector VARCHAR(100),
    registration_date DATE,
    
    -- Financial Data (Annual)
    annual_turnover DECIMAL(20,2) DEFAULT 0,
    annual_profit DECIMAL(20,2) DEFAULT 0,
    digital_asset_gains DECIMAL(20,2) DEFAULT 0,
    vat_taxable_supplies DECIMAL(20,2) DEFAULT 0,
    export_revenue DECIMAL(20,2) DEFAULT 0,
    
    -- Deductions & Credits
    rnd_expenses DECIMAL(20,2) DEFAULT 0,
    pension_contributions DECIMAL(20,2) DEFAULT 0,
    capital_allowances DECIMAL(20,2) DEFAULT 0,
    
    -- Employee Info
    employee_count INTEGER DEFAULT 0,
    employees_below_min_wage INTEGER DEFAULT 0,
    
    -- Special Status Flags
    is_startup BOOLEAN DEFAULT FALSE,
    startup_incorporation_date DATE,
    has_pioneer_status BOOLEAN DEFAULT FALSE,
    in_free_trade_zone BOOLEAN DEFAULT FALSE,
    exports_digital_services BOOLEAN DEFAULT FALSE,
    
    -- Tax Compliance History
    last_filing_date DATE,
    compliance_score INTEGER DEFAULT 0, -- 0-100
    risk_level VARCHAR(20) DEFAULT 'low', -- low, medium, high
    
    -- Metadata
    data_source VARCHAR(50) DEFAULT 'user_input', -- 'user_input', 'compliance_docs', 'auto_inferred'
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES auth.users(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_user_tax_profile UNIQUE(user_id)
);

CREATE INDEX idx_user_tax_profiles_user ON public.user_tax_profiles(user_id);
CREATE INDEX idx_user_tax_profiles_entity_type ON public.user_tax_profiles(entity_type);

-- ============================================
-- 3. TAX SCENARIOS (User's "What-If" Models)
-- ============================================
CREATE TABLE IF NOT EXISTS public.tax_scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    scenario_name VARCHAR(200) NOT NULL,
    scenario_type VARCHAR(50) DEFAULT 'manual', -- 'manual', 'auto_suggestion', 'comparative'
    
    -- Input Parameters
    input_data JSONB NOT NULL,
    /* Example:
    {
        "entity_type": "company",
        "annual_turnover": 150000000,
        "digital_gains": 5000000,
        "applied_exemptions": ["small_co", "rnd_deduction"],
        "planning_horizon": "2024-2025"
    }
    */
    
    -- Calculation Results
    calculation_results JSONB,
    /* Example:
    {
        "breakdown": {
            "cit": 30000000,
            "vat": 11250000,
            "wht": 1500000,
            "total_liability": 42750000
        },
        "exemptions_applied": [
            {"code": "rnd_deduction", "savings": 250000}
        ],
        "effective_tax_rate": 28.5,
        "recommendations": [...]
    }
    */
    
    -- Comparison Data (for side-by-side scenarios)
    compared_with UUID REFERENCES public.tax_scenarios(id),
    variance_analysis JSONB,
    
    -- Status
    is_baseline BOOLEAN DEFAULT FALSE,
    is_favorite BOOLEAN DEFAULT FALSE,
    shared_with_auditor BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tax_scenarios_user ON public.tax_scenarios(user_id);
CREATE INDEX idx_tax_scenarios_type ON public.tax_scenarios(scenario_type);
CREATE INDEX idx_tax_scenarios_favorite ON public.tax_scenarios(user_id, is_favorite) WHERE is_favorite = TRUE;

-- ============================================
-- 4. EXEMPTION QUALIFICATIONS
-- Track which exemptions user qualifies for
-- ============================================
CREATE TABLE IF NOT EXISTS public.exemption_qualifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    exemption_code VARCHAR(50) NOT NULL,
    exemption_name VARCHAR(200) NOT NULL,
    rule_reference VARCHAR(100), -- Links to tax_rules.rule_code
    
    -- Qualification Status
    status VARCHAR(20) NOT NULL, -- 'qualified', 'pending_docs', 'not_qualified', 'expired'
    qualification_date DATE,
    expiry_date DATE,
    
    -- Supporting Evidence
    required_documents TEXT[], -- ['cac_certificate', 'audited_accounts']
    uploaded_document_ids UUID[], -- References compliance_documents.id
    verification_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'verified', 'rejected'
    
    -- Financial Impact
    estimated_annual_savings DECIMAL(20,2),
    actual_savings_ytd DECIMAL(20,2) DEFAULT 0,
    
    -- Audit Trail
    qualification_reason TEXT,
    disqualification_reason TEXT,
    verified_by UUID REFERENCES auth.users(id),
    verified_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_exemption_qualifications_user ON public.exemption_qualifications(user_id);
CREATE INDEX idx_exemption_qualifications_status ON public.exemption_qualifications(status);
CREATE INDEX idx_exemption_qualifications_code ON public.exemption_qualifications(exemption_code);

-- ============================================
-- 5. TAX CALCULATIONS HISTORY
-- Audit trail of all tax calculations
-- ============================================
CREATE TABLE IF NOT EXISTS public.tax_calculations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    calculation_type VARCHAR(50) NOT NULL, -- 'annual_estimate', 'scenario', 'penalty_assessment', 'real_time'
    
    -- Tax Period
    tax_year INTEGER,
    tax_period VARCHAR(20), -- 'Q1', 'Q2', 'annual', etc.
    
    -- Input Snapshot
    input_snapshot JSONB NOT NULL,
    
    -- Calculation Breakdown
    tax_breakdown JSONB NOT NULL,
    /* Example:
    {
        "cit": {"taxable_income": 50000000, "rate": 0.30, "amount": 15000000},
        "vat": {"taxable_supplies": 100000000, "rate": 0.075, "amount": 7500000},
        "wht": {"withholdings": 2000000},
        "tertiary_education_tax": {"amount": 2000000},
        "development_levy": {"amount": 2000000},
        "total": 28500000
    }
    */
    
    -- Exemptions & Reliefs Applied
    exemptions_applied JSONB,
    total_savings DECIMAL(20,2) DEFAULT 0,
    
    -- Compliance Indicators
    compliance_issues TEXT[],
    risk_flags TEXT[],
    missing_documents TEXT[],
    
    -- Calculation Metadata
    calculation_engine_version VARCHAR(20),
    rules_version VARCHAR(20),
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tax_calculations_user ON public.tax_calculations(user_id);
CREATE INDEX idx_tax_calculations_year ON public.tax_calculations(tax_year);
CREATE INDEX idx_tax_calculations_type ON public.tax_calculations(calculation_type);

-- ============================================
-- 6. TAX DEADLINES & REMINDERS
-- ============================================
CREATE TABLE IF NOT EXISTS public.tax_deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Deadline Info
    deadline_type VARCHAR(50) NOT NULL, -- 'cit_filing', 'vat_filing', 'paye_remittance', etc.
    deadline_name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Timing
    due_date DATE NOT NULL,
    tax_period VARCHAR(20), -- 'monthly', 'quarterly', 'annual'
    applicable_to VARCHAR(50)[], -- ['companies', 'individuals', 'small_companies']
    
    -- Penalties for Missing
    late_penalty_rate DECIMAL(5,4),
    minimum_penalty DECIMAL(20,2),
    penalty_description TEXT,
    
    -- Recurrence
    is_recurring BOOLEAN DEFAULT TRUE,
    recurrence_rule VARCHAR(100), -- 'FREQ=MONTHLY;BYMONTHDAY=21' (iCal format)
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tax_deadlines_due_date ON public.tax_deadlines(due_date);
CREATE INDEX idx_tax_deadlines_type ON public.tax_deadlines(deadline_type);

-- User-specific deadline tracking
CREATE TABLE IF NOT EXISTS public.user_tax_deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    deadline_id UUID NOT NULL REFERENCES public.tax_deadlines(id) ON DELETE CASCADE,
    
    -- Personalized Due Date (may differ from default)
    personalized_due_date DATE NOT NULL,
    
    -- Status Tracking
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'completed', 'overdue', 'dismissed'
    completed_at TIMESTAMPTZ,
    
    -- Reminders
    reminder_sent BOOLEAN DEFAULT FALSE,
    reminder_sent_at TIMESTAMPTZ,
    reminder_count INTEGER DEFAULT 0,
    
    -- Notes
    user_notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_tax_deadlines_user ON public.user_tax_deadlines(user_id);
CREATE INDEX idx_user_tax_deadlines_status ON public.user_tax_deadlines(status);
CREATE INDEX idx_user_tax_deadlines_due_date ON public.user_tax_deadlines(personalized_due_date);

-- ============================================
-- 7. TAX Q&A / KNOWLEDGE BASE
-- Store user questions and AI-generated answers
-- ============================================
CREATE TABLE IF NOT EXISTS public.tax_qa_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Question
    question TEXT NOT NULL,
    question_category VARCHAR(50), -- 'exemptions', 'penalties', 'deadlines', 'general'
    
    -- Answer
    answer TEXT,
    answer_sources JSONB, -- Array of {act_section, rule_code, url}
    confidence_score DECIMAL(3,2),
    
    -- User Feedback
    was_helpful BOOLEAN,
    user_feedback TEXT,
    
    -- Follow-up
    parent_question_id UUID REFERENCES public.tax_qa_sessions(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tax_qa_user ON public.tax_qa_sessions(user_id);
CREATE INDEX idx_tax_qa_category ON public.tax_qa_sessions(question_category);
CREATE INDEX idx_tax_qa_helpful ON public.tax_qa_sessions(was_helpful) WHERE was_helpful = TRUE;

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on all user-specific tables
ALTER TABLE public.user_tax_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tax_scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exemption_qualifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tax_calculations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_tax_deadlines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tax_qa_sessions ENABLE ROW LEVEL SECURITY;

-- User Tax Profiles Policies
CREATE POLICY "Users can view own tax profile"
    ON public.user_tax_profiles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own tax profile"
    ON public.user_tax_profiles FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own tax profile"
    ON public.user_tax_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Tax Scenarios Policies
CREATE POLICY "Users can manage own scenarios"
    ON public.tax_scenarios FOR ALL
    USING (auth.uid() = user_id);

-- Exemption Qualifications Policies
CREATE POLICY "Users can view own exemptions"
    ON public.exemption_qualifications FOR SELECT
    USING (auth.uid() = user_id);

-- Tax Calculations Policies
CREATE POLICY "Users can view own calculations"
    ON public.tax_calculations FOR ALL
    USING (auth.uid() = user_id);

-- User Tax Deadlines Policies
CREATE POLICY "Users can manage own deadlines"
    ON public.user_tax_deadlines FOR ALL
    USING (auth.uid() = user_id);

-- Tax Q&A Policies
CREATE POLICY "Users can view own Q&A"
    ON public.tax_qa_sessions FOR ALL
    USING (auth.uid() = user_id);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Apply to relevant tables
CREATE TRIGGER update_user_tax_profiles_updated_at
    BEFORE UPDATE ON public.user_tax_profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_tax_scenarios_updated_at
    BEFORE UPDATE ON public.tax_scenarios
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_exemption_qualifications_updated_at
    BEFORE UPDATE ON public.exemption_qualifications
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================
-- SEED DATA: CORE TAX RULES (Nigerian Tax Act 2023/2025)
-- ============================================

INSERT INTO public.tax_rules (rule_code, rule_category, act_section, description, rule_logic, effective_from) VALUES
-- CIT Rules
('CIT_SMALL_2023', 'CIT', 'Finance Act 2023, Section 8(1)', 'Small companies with turnover < N100M pay 0% CIT', 
    '{"condition": {"field": "annual_turnover", "operator": "<", "value": 100000000}, "outcome": {"tax_rate": 0.00}}', 
    '2023-01-01'),

('CIT_MEDIUM_2023', 'CIT', 'Companies Income Tax Act', 'Companies with turnover N100M-N500M pay 20% CIT',
    '{"condition": {"field": "annual_turnover", "operator": "between", "value": [100000000, 500000000]}, "outcome": {"tax_rate": 0.20}}',
    '2023-01-01'),

('CIT_LARGE_2023', 'CIT', 'Companies Income Tax Act', 'Companies with turnover > N500M pay 30% CIT',
    '{"condition": {"field": "annual_turnover", "operator": ">", "value": 500000000}, "outcome": {"tax_rate": 0.30}}',
    '2023-01-01'),

-- CGT Rules
('CGT_DIGITAL_2023', 'CGT', 'Finance Act 2023, Digital Assets', '10% CGT on digital asset gains',
    '{"condition": {"field": "digital_asset_gains", "operator": ">", "value": 0}, "outcome": {"tax_rate": 0.10}}',
    '2023-01-01'),

-- VAT Rules
('VAT_STANDARD_2023', 'VAT', 'VAT Act 2023', 'Standard VAT rate of 7.5%',
    '{"outcome": {"tax_rate": 0.075}}',
    '2020-01-01'),

('VAT_DIGITAL_EXPORT_2023', 'VAT', 'Finance Act 2023', '0% VAT on digital service exports',
    '{"condition": {"field": "exports_digital_services", "operator": "==", "value": true}, "outcome": {"tax_rate": 0.00}}',
    '2023-01-01'),

-- Exemptions
('EXEMP_AGRI_HOLIDAY', 'EXEMPTION', 'Industrial Development Act, Section 15', '5-year tax holiday for agricultural businesses',
    '{"condition": {"field": "industry_sector", "operator": "==", "value": "agriculture"}, "outcome": {"years": 5, "tax_rate": 0.00}}',
    '2020-01-01'),

('EXEMP_STARTUP_24MO', 'EXEMPTION', 'Finance Act 2023', '24-month CIT exemption for startups',
    '{"condition": {"field": "is_startup", "operator": "==", "value": true}, "outcome": {"months": 24, "tax_rate": 0.00}}',
    '2023-01-01'),

('EXEMP_PIONEER_STATUS', 'EXEMPTION', 'Industrial Development Act', 'Pioneer status grants 3-5 year tax holiday',
    '{"condition": {"field": "has_pioneer_status", "operator": "==", "value": true}, "outcome": {"years": 5, "tax_rate": 0.00}}',
    '2020-01-01')

ON CONFLICT (rule_code) DO NOTHING;

-- ============================================
-- SEED DATA: COMMON TAX DEADLINES (2024)
-- ============================================

INSERT INTO public.tax_deadlines (deadline_type, deadline_name, description, due_date, tax_period, applicable_to, late_penalty_rate, minimum_penalty) VALUES
('CIT_FILING', 'Companies Income Tax Return Filing', 'Annual CIT return filing deadline', '2024-06-30', 'annual', ARRAY['companies'], 0.10, 50000),
('VAT_FILING', 'VAT Monthly Return', 'Monthly VAT return filing', '2024-01-21', 'monthly', ARRAY['companies', 'individuals'], 0.05, 10000),
('PAYE_REMITTANCE', 'PAYE Tax Remittance', 'Monthly PAYE remittance to FIRS', '2024-01-10', 'monthly', ARRAY['companies'], 0.10, 50000),
('WHT_REMITTANCE', 'Withholding Tax Remittance', 'Monthly WHT remittance', '2024-01-21', 'monthly', ARRAY['companies'], 0.10, 25000),
('TET_PAYMENT', 'Tertiary Education Tax Payment', 'Annual TET payment (2% of assessable profits)', '2024-09-30', 'annual', ARRAY['companies'], 0.10, 100000)

ON CONFLICT DO NOTHING;

-- ✅ VERIFICATION STEPS:
-- 1. Run this SQL in Supabase SQL Editor
-- 2. Check "Tables" section - should see 8 new tables
-- 3. Check "Policies" - should see RLS policies for each user table
-- 4. Check "Functions" - should see update_updated_at_column()
-- 5. Query: SELECT * FROM tax_rules; -- Should return 9 rules
-- 6. Query: SELECT * FROM tax_deadlines; -- Should return 5 deadlines

COMMENT ON TABLE public.tax_rules IS 'Repository of Nigerian Tax Act provisions and rules';
COMMENT ON TABLE public.user_tax_profiles IS 'Comprehensive tax-relevant user profiles';
COMMENT ON TABLE public.tax_scenarios IS 'User-created tax scenario models';
COMMENT ON TABLE public.exemption_qualifications IS 'Tracks user eligibility for tax exemptions';
COMMENT ON TABLE public.tax_calculations IS 'Historical audit trail of all tax calculations';
COMMENT ON TABLE public.tax_deadlines IS 'Master list of tax filing and payment deadlines';
COMMENT ON TABLE public.user_tax_deadlines IS 'User-specific deadline tracking and reminders';
COMMENT ON TABLE public.tax_qa_sessions IS 'Tax Q&A history for knowledge base';