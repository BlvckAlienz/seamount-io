// File: frontend/src/pages/CompliancePage.tsx - UPDATED v4
// ✅ Removed Compliance Score card
// ✅ Fixed Development Levy display (0% for small companies)
// ✅ Simplified Audit Profile section
// ✅ Removed Audit Profile Progress section
// ✅ Fixed document counts in dropdown and list
// ✅ Removed 1:1 Document Sync tag
// ✅ Mobile-friendly design

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Receipt,
  FileText,
  CheckCircle,
  Upload,
  TrendingUp,
  Trash2,
  RefreshCw,
  AlertCircle,
  Calculator,
  BarChart2,
  Lightbulb,
  Shield,
  Clock,
  DollarSign,
  AlertTriangle,
  BookOpen,
  Scale,
  Download,
  ExternalLink,
  Lock,
  Users,
  Building,
  Package,
  CreditCard,
  Banknote,
  ShoppingCart,
  Wallet
} from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

// ============================================
// TYPE DEFINITIONS
// ============================================

interface ComplianceState {
  loading: boolean;
  refreshing: boolean;
  subscription: any;
  checklist: ChecklistItem[];
  documents: Document[];
  metrics: {
    documents_count: number;
    total_items: number;
    completed_items: number;
    progress_percentage: number;
    last_sync: string;
  };
  systemStatus: {
    consistent: boolean;
    verified: boolean;
    last_verified: string;
  };
  taxData: {
    currentLiability: number;
    exemptions: any[];
    scenarios: any[];
    deadlines: any[];
    recommendations: string[];
    riskFlags: string[];
    confidenceScore: number;
    legislationVersion: string;
    lastCalculated: string;
  };
}

interface ChecklistItem {
  id: string;
  category: 'C' | 'D' | 'E' | 'F' | 'G' | 'H' | 'J' | 'K' | 'L';
  item_description: string;
  is_completed: boolean;
  document_uploaded?: boolean;
  required_document_type?: string;
}

interface Document {
  id: string;
  file_name: string;
  category: 'C' | 'D' | 'E' | 'F' | 'G' | 'H' | 'J' | 'K' | 'L';
  document_type: string;
  created_at: string;
  file_size?: number;
}

type TabType = 'overview' | 'audit-profile' | 'exemptions' | 'calculator' | 'deadlines';

// ============================================
// DOCUMENT-CHECKLIST MAPPING (1:1 Synchronization)
// ============================================

const DOCUMENT_CHECKLIST_MAP: Record<string, {
  category: string;
  category_name: string;
  icon: React.ReactNode;
  items: Array<{
    checklist_description: string;
    document_type: string;
    document_name: string;
  }>;
}> = {
  C: {
    category: 'C',
    category_name: 'Understanding Business',
    icon: <Building className="h-5 w-5" />,
    items: [
      {
        checklist_description: "Incorporation documents (CAC certificate, Form CAC 1.1, etc.)",
        document_type: 'incorporation_docs',
        document_name: 'Incorporation Documents'
      },
      {
        checklist_description: "Memorandum and Articles of Association",
        document_type: 'memorandum_articles',
        document_name: 'Memorandum & Articles of Association'
      },
      {
        checklist_description: "Company's Common Seal (if any)",
        document_type: 'common_seal',
        document_name: 'Company Common Seal'
      },
      {
        checklist_description: "Board Resolution authorizing operations",
        document_type: 'board_resolution',
        document_name: 'Board Resolution'
      },
      {
        checklist_description: "Taxpayer's business address verification",
        document_type: 'business_address',
        document_name: 'Business Address Verification'
      }
    ]
  },
  D: {
    category: 'D',
    category_name: 'Share Capital',
    icon: <Users className="h-5 w-5" />,
    items: [
      {
        checklist_description: "Share capital structure",
        document_type: 'share_capital_structure',
        document_name: 'Share Capital Structure'
      },
      {
        checklist_description: "Register of members",
        document_type: 'register_of_members',
        document_name: 'Register of Members'
      },
      {
        checklist_description: "Share certificates (if any)",
        document_type: 'share_certificates',
        document_name: 'Share Certificates'
      },
      {
        checklist_description: "Directors' shareholding pattern",
        document_type: 'directors_shareholding',
        document_name: 'Directors Shareholding Pattern'
      }
    ]
  },
  E: {
    category: 'E',
    category_name: 'Fixed Assets',
    icon: <Building className="h-5 w-5" />,
    items: [
      {
        checklist_description: "Fixed Asset Register",
        document_type: 'fixed_asset_register',
        document_name: 'Fixed Asset Register'
      },
      {
        checklist_description: "Purchase invoices for fixed assets",
        document_type: 'asset_purchase_invoices',
        document_name: 'Asset Purchase Invoices'
      },
      {
        checklist_description: "Depreciation schedule",
        document_type: 'depreciation_schedule',
        document_name: 'Depreciation Schedule'
      },
      {
        checklist_description: "Asset disposal records (if any)",
        document_type: 'asset_disposal_records',
        document_name: 'Asset Disposal Records'
      }
    ]
  },
  F: {
    category: 'F',
    category_name: 'Inventory',
    icon: <Package className="h-5 w-5" />,
    items: [
      {
        checklist_description: "Inventory ledger",
        document_type: 'inventory_ledger',
        document_name: 'Inventory Ledger'
      },
      {
        checklist_description: "Stock count sheets",
        document_type: 'stock_count_sheets',
        document_name: 'Stock Count Sheets'
      },
      {
        checklist_description: "Inventory valuation records",
        document_type: 'inventory_valuation',
        document_name: 'Inventory Valuation Records'
      }
    ]
  },
  G: {
    category: 'G',
    category_name: 'Debtors',
    icon: <CreditCard className="h-5 w-5" />,
    items: [
      {
        checklist_description: "Aged debtors analysis",
        document_type: 'aged_debtors',
        document_name: 'Aged Debtors Analysis'
      },
      {
        checklist_description: "Debtors ledger",
        document_type: 'debtors_ledger',
        document_name: 'Debtors Ledger'
      },
      {
        checklist_description: "Credit sales invoices",
        document_type: 'credit_sales_invoices',
        document_name: 'Credit Sales Invoices'
      }
    ]
  },
  H: {
    category: 'H',
    category_name: 'Cash & Bank',
    icon: <Banknote className="h-5 w-5" />,
    items: [
      {
        checklist_description: "Bank statements (all accounts)",
        document_type: 'bank_statements',
        document_name: 'Bank Statements'
      },
      {
        checklist_description: "Cash book",
        document_type: 'cash_book',
        document_name: 'Cash Book'
      },
      {
        checklist_description: "Bank reconciliation statements",
        document_type: 'bank_reconciliation',
        document_name: 'Bank Reconciliation Statements'
      },
      {
        checklist_description: "Petty cash records",
        document_type: 'petty_cash_records',
        document_name: 'Petty Cash Records'
      }
    ]
  },
  J: {
    category: 'J',
    category_name: 'Creditors',
    icon: <ShoppingCart className="h-5 w-5" />,
    items: [
      {
        checklist_description: "Aged creditors analysis",
        document_type: 'aged_creditors',
        document_name: 'Aged Creditors Analysis'
      },
      {
        checklist_description: "Creditors ledger",
        document_type: 'creditors_ledger',
        document_name: 'Creditors Ledger'
      },
      {
        checklist_description: "Purchase invoices",
        document_type: 'purchase_invoices',
        document_name: 'Purchase Invoices'
      }
    ]
  },
  K: {
    category: 'K',
    category_name: 'Sales & Income',
    icon: <Receipt className="h-5 w-5" />,
    items: [
      {
        checklist_description: "Sales ledger",
        document_type: 'sales_ledger',
        document_name: 'Sales Ledger'
      },
      {
        checklist_description: "Sales invoices/ receipts",
        document_type: 'sales_invoices',
        document_name: 'Sales Invoices/Receipts'
      },
      {
        checklist_description: "Income recognition policy",
        document_type: 'income_policy',
        document_name: 'Income Recognition Policy'
      }
    ]
  },
  L: {
    category: 'L',
    category_name: 'Expenses',
    icon: <Wallet className="h-5 w-5" />,
    items: [
      {
        checklist_description: "Expenses ledger",
        document_type: 'expenses_ledger',
        document_name: 'Expenses Ledger'
      },
      {
        checklist_description: "Payment vouchers",
        document_type: 'payment_vouchers',
        document_name: 'Payment Vouchers'
      },
      {
        checklist_description: "Payroll records",
        document_type: 'payroll_records',
        document_name: 'Payroll Records'
      },
      {
        checklist_description: "Tax payment receipts (WHT, VAT, etc.)",
        document_type: 'tax_payment_receipts',
        document_name: 'Tax Payment Receipts'
      }
    ]
  }
};

// ============================================
// AIR-TIGHT TAX CALCULATION ENGINE (NTA 2025 Compliant)
// ============================================

const generateMockTaxCalculation = (inputs: any = {}) => {
  const entity_type = inputs.entity_type || 'company';
  const annual_turnover = parseFloat(inputs.annual_turnover) || 0;
  const annual_profit = parseFloat(inputs.annual_profit) || 0;
  const vat_taxable_supplies = parseFloat(inputs.vat_taxable_supplies) || 0;
  const digital_asset_gains = parseFloat(inputs.digital_asset_gains) || 0;
  const rnd_expenses = parseFloat(inputs.rnd_expenses) || 0;
  const fixed_assets = parseFloat(inputs.fixed_assets) || 0;
  const exports_digital_services = inputs.exports_digital_services || false;

  // ✅ UPDATED: R&D deduction - actual expenses capped at 5% of turnover
  const rnd_deduction = Math.min(rnd_expenses, annual_turnover * 0.05);
  
  // Taxable profit after R&D deduction
  let taxable_profit = annual_profit - rnd_deduction;
  if (taxable_profit < 0) taxable_profit = 0;

  // ✅ UPDATED: Small company qualification - ₦100M turnover AND ₦250M fixed assets
  const is_small_company = annual_turnover <= 100000000 && fixed_assets <= 250000000;

  // ✅ UPDATED: CIT - Binary rate: 0% for small companies, 30% otherwise
  let citRate = is_small_company ? 0.00 : 0.30;
  let citAmount = taxable_profit * citRate;

  // ✅ UPDATED: VAT - 7.5% standard, 0% for exports
  const vatRate = exports_digital_services ? 0.00 : 0.075;
  const vatAmount = vat_taxable_supplies * vatRate;

  // ✅ FIXED: CGT integrated into CIT rates (0% for small companies, 30% otherwise)
  const cgtRate = is_small_company ? 0.00 : 0.30;
  const cgtAmount = digital_asset_gains * cgtRate;

  // ✅ FIXED: Development Levy 4% on assessable profits - exempt for small companies
  // Note: Assessable profit is annual profit before R&D deduction for Development Levy
  const devLevyAssessableProfit = annual_profit;
  const devLevyRate = is_small_company ? 0.00 : 0.04; // ✅ FIXED: Now shows 0% for small companies
  const devLevyAmount = devLevyAssessableProfit * devLevyRate;

  const totalLiability = citAmount + vatAmount + cgtAmount + devLevyAmount;

  // ✅ UPDATED: Exemptions with correct Act sections
  const exemptions_applied = [];

  if (rnd_expenses > 0 && annual_turnover > 0) {
    exemptions_applied.push({
      exemption_code: "RND_DEDUCTION",
      exemption_name: "R&D Expense Deduction",
      description: "R&D expenses deductible up to 5% of turnover",
      estimated_savings: rnd_deduction * (is_small_company ? 0 : 0.30),
      act_section: "Nigeria Tax Act 2025, Section 20(1)(i)",
      qualification_criteria: "Documented R&D expenses for trade/business, capped at 5% turnover",
      required_documents: ["R&D Expense Reports", "Project Documentation"],
      status: "qualified"
    });
  }

  if (is_small_company && annual_turnover > 0) {
    exemptions_applied.push({
      exemption_code: "SMALL_COMPANY",
      exemption_name: "Small Company 0% CIT & Development Levy Exemption",
      description: "Companies with turnover ≤ ₦100M and fixed assets ≤ ₦250M pay 0% CIT and exempt from Development Levy",
      estimated_savings: (taxable_profit * 0.30) + (devLevyAssessableProfit * 0.04),
      act_section: "Nigeria Tax Act 2025, Section 56(a)",
      qualification_criteria: "Annual turnover ≤ ₦100,000,000 and fixed assets ≤ ₦250,000,000",
      required_documents: ["Audited Financial Statements", "Tax Clearance Certificate"],
      status: "qualified"
    });
    
    // ✅ FIXED: CGT exemption for small companies
    if (digital_asset_gains > 0) {
      exemptions_applied.push({
        exemption_code: "SMALL_COMPANY_CGT",
        exemption_name: "Small Company 0% CGT Exemption",
        description: "Small companies pay 0% Capital Gains Tax on digital asset gains",
        estimated_savings: digital_asset_gains * 0.30,
        act_section: "Nigeria Tax Act 2025, Section 56(a) & 33-39",
        qualification_criteria: "Annual turnover ≤ ₦100,000,000 and fixed assets ≤ ₦250,000,000",
        required_documents: ["Digital Asset Transaction Records", "Capital Gains Calculation"],
        status: "qualified"
      });
    }
  }

  if (exports_digital_services && vat_taxable_supplies > 0) {
    exemptions_applied.push({
      exemption_code: "DIGITAL_EXPORT_VAT",
      exemption_name: "Digital Export 0% VAT",
      description: "0% VAT on digital service exports to foreign clients",
      estimated_savings: vat_taxable_supplies * 0.075,
      act_section: "Nigeria Tax Act 2025, Section 187",
      qualification_criteria: "Export of digital services/incorporeal property, foreign exchange receipts",
      required_documents: ["Export Invoices", "Foreign Exchange Receipts"],
      status: "qualified"
    });
  }

  // ✅ FIXED: VAT registration requirement (not an exemption, but a compliance flag)
  const vatRegistrationRequired = !is_small_company && vat_taxable_supplies >= 50000000;

  const total_savings = exemptions_applied.reduce((sum: number, e: any) => sum + e.estimated_savings, 0);

  return {
    breakdown: {
      cit: {
        tax_type: "CIT",
        turnover: annual_turnover,
        gross_profit: annual_profit,
        taxable_profit: taxable_profit,
        tax_rate: citRate,
        amount: citAmount,
        company_size: is_small_company ? "small" : "standard"
      },
      vat: {
        tax_type: "VAT",
        taxable_supplies: vat_taxable_supplies,
        vat_rate: vatRate,
        amount: vatAmount,
        requires_registration: vatRegistrationRequired,
        registration_threshold: 50000000
      },
      cgt_digital: {
        tax_type: "CGT_DIGITAL",
        digital_asset_gains: digital_asset_gains,
        cgt_rate: cgtRate,
        amount: cgtAmount,
        small_company_exempt: is_small_company
      },
      dev_levy: {
        tax_type: "DEVELOPMENT_LEVY",
        assessable_profit: devLevyAssessableProfit,
        rate: devLevyRate, // ✅ FIXED: Now shows 0.00 for small companies
        amount: devLevyAmount,
        exempt_for_small: is_small_company
      }
    },
    total_liability_before_exemptions: citAmount + vatAmount + cgtAmount + devLevyAmount + total_savings,
    total_liability: totalLiability,
    exemptions_applied,
    total_savings,
    effective_tax_rate: annual_turnover > 0 ? totalLiability / annual_turnover : 0,
    citations: [
      {
        section: "Nigeria Tax Act 2025, Section 56(a)",
        description: "Small company CIT exemption for turnover ≤ ₦100M and fixed assets ≤ ₦250M",
        applies_to: "CIT calculation"
      },
      {
        section: "Nigeria Tax Act 2025, Section 187",
        description: "Zero-rating for exports including digital services",
        applies_to: "VAT calculation"
      },
      {
        section: "Nigeria Tax Act 2025, Section 20(1)(i)",
        description: "R&D expense deduction up to 5% of turnover",
        applies_to: "CIT calculation"
      },
      {
        section: "Nigeria Tax Act 2025, Section 59",
        description: "4% Development Levy on assessable profits",
        applies_to: "Development Levy calculation"
      },
      {
        section: "Nigeria Tax Act 2025, Section 33-39",
        description: "Chargeable gains including digital assets at CIT rates",
        applies_to: "CGT calculation"
      }
    ],
    recommendations: [
      is_small_company && annual_turnover > 0
        ? "✅ You qualify for Small Company 0% CIT & CGT Exemption and Development Levy exemption."
        : null,
      rnd_expenses > 0
        ? "💡 Document R&D expenses to qualify for deductions up to 5% of turnover."
        : null,
      exports_digital_services && vat_taxable_supplies > 0
        ? "✅ You qualify for 0% VAT on digital exports."
        : null,
      vatRegistrationRequired
        ? "⚠️ VAT registration required: Taxable supplies exceed ₦50M threshold"
        : null,
      !is_small_company && annual_turnover >= 20000000000
        ? "⚠️ Minimum Effective Tax Rate (15%) may apply: Turnover exceeds ₦20B threshold"
        : null
    ].filter(Boolean),
    risk_flags: [
      vatRegistrationRequired
        ? "VAT registration overdue: Taxable supplies exceed ₦50M threshold"
        : null,
      !is_small_company && annual_turnover >= 20000000000
        ? "Minimum Effective Tax Rate (15%) may apply: Turnover exceeds ₦20B threshold"
        : null
    ].filter(Boolean),
    confidence_score: annual_turnover > 0 ? 0.95 : 0.0,
    calculated_at: new Date().toISOString(),
    tax_year: new Date().getFullYear(),
    legislation_version: "Nigeria Tax Act 2025",
    mock_data: true,
    is_small_company: is_small_company
  };
};

const generateMockDeadlines = () => [
  {
    id: "deadline_1",
    deadline_name: "Annual Tax Return (CIT)",
    description: "Companies Income Tax filing for 2025 tax year",
    deadline_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    tax_authority: "Nigeria Revenue Service",
    country: "nigeria",
    penalty_amount: 100000,
    status: "upcoming"
  },
  {
    id: "deadline_2",
    deadline_name: "VAT Monthly Remittance",
    description: "Value Added Tax monthly filing and payment",
    deadline_date: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    tax_authority: "Nigeria Revenue Service",
    country: "nigeria",
    penalty_amount: 50000,
    status: "upcoming"
  }
];

// ============================================
// SYNC ENGINE: Edge-level computing for perfect sync
// ============================================

class SyncEngine {
  static calculateProgress(checklist: ChecklistItem[], documents: Document[]): { 
    total_items: number; 
    completed_items: number; 
    progress_percentage: number;
    documents_count: number;
  } {
    const total_items = checklist.length;
    
    // Create a map of document types uploaded per category
    const uploadedDocumentsByCategory = documents.reduce((acc: Record<string, Set<string>>, doc: Document) => {
      if (!acc[doc.category]) {
        acc[doc.category] = new Set();
      }
      acc[doc.category].add(doc.document_type);
      return acc;
    }, {});
    
    // Check each checklist item for exact document match
    let completed_items = 0;
    
    checklist.forEach(item => {
      const hasMatchingDocument = uploadedDocumentsByCategory[item.category]?.has(item.required_document_type || '');
      if (hasMatchingDocument) {
        completed_items++;
      }
    });
    
    const progress_percentage = total_items > 0 
      ? Math.min(100, Math.round((completed_items / total_items) * 100))
      : 0;
    
    return {
      total_items,
      completed_items,
      progress_percentage,
      documents_count: documents.length
    };
  }
  
  static syncChecklistWithDocuments(checklist: ChecklistItem[], documents: Document[]): ChecklistItem[] {
    const uploadedDocumentsByCategory = documents.reduce((acc: Record<string, Set<string>>, doc: Document) => {
      if (!acc[doc.category]) {
        acc[doc.category] = new Set();
      }
      acc[doc.category].add(doc.document_type);
      return acc;
    }, {});
    
    return checklist.map(item => {
      const hasMatchingDocument = uploadedDocumentsByCategory[item.category]?.has(item.required_document_type || '');
      return {
        ...item,
        is_completed: hasMatchingDocument || false,
        document_uploaded: hasMatchingDocument || false
      };
    });
  }
  
  static verifySyncConsistency(checklist: ChecklistItem[], documents: Document[], metrics: any): boolean {
    const calculated = this.calculateProgress(checklist, documents);
    
    return (
      calculated.documents_count === metrics.documents_count &&
      calculated.completed_items === metrics.completed_items &&
      calculated.total_items === metrics.total_items &&
      calculated.progress_percentage === metrics.progress_percentage
    );
  }
  
  static getAvailableDocumentTypesForCategory(
    category: string, 
    currentDocuments: Document[]
  ): Array<{ value: string, label: string }> {
    const categoryData = DOCUMENT_CHECKLIST_MAP[category];
    if (!categoryData) return [];
    
    const uploadedDocumentTypes = new Set(
      currentDocuments
        .filter(doc => doc.category === category)
        .map(doc => doc.document_type)
    );
    
    return categoryData.items
      .filter(item => !uploadedDocumentTypes.has(item.document_type))
      .map(item => ({
        value: item.document_type,
        label: item.document_name
      }));
  }
  
  static isCategoryComplete(category: string, currentDocuments: Document[]): boolean {
    const categoryData = DOCUMENT_CHECKLIST_MAP[category];
    if (!categoryData) return false;
    
    const uploadedDocumentTypes = new Set(
      currentDocuments
        .filter(doc => doc.category === category)
        .map(doc => doc.document_type)
    );
    
    return categoryData.items.every(item => 
      uploadedDocumentTypes.has(item.document_type)
    );
  }
  
  static getDocumentTypeName(category: string, documentType: string): string {
    const categoryData = DOCUMENT_CHECKLIST_MAP[category];
    if (!categoryData) return documentType;
    
    const item = categoryData.items.find(i => i.document_type === documentType);
    return item ? item.document_name : documentType;
  }
  
  static getCategoryStats(category: string, documents: Document[]) {
    const categoryData = DOCUMENT_CHECKLIST_MAP[category];
    if (!categoryData) return { total: 0, completed: 0, percentage: 0 };
    
    const uploadedDocumentTypes = new Set(
      documents
        .filter(doc => doc.category === category)
        .map(doc => doc.document_type)
    );
    
    const completed = uploadedDocumentTypes.size;
    const total = categoryData.items.length;
    const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
    
    return { total, completed, percentage };
  }
}

// ============================================
// SUB-COMPONENTS
// ============================================

const StatCard = ({ title, value, subtitle, icon, gradient, border }: any) => (
  <div className={`bg-gradient-to-br ${gradient} border ${border} rounded-xl p-6`}>
    <div className="flex items-start justify-between mb-3">
      <div className="text-sm text-gray-400">{title}</div>
      {icon}
    </div>
    <div className="text-3xl font-bold text-white mb-1">{value}</div>
    <div className="text-sm text-gray-400">{subtitle}</div>
  </div>
);

const OverviewTab = ({ state, formatCurrency }: any) => (
  <div className="space-y-6">
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-white">Tax Liability Breakdown</h3>
        <div className="flex items-center gap-2 text-sm">
          <BookOpen className="h-4 w-4 text-blue-400" />
          <span className="text-blue-400">{state.taxData.legislationVersion || 'Nigeria Tax Act 2025'}</span>
        </div>
      </div>
      
      <div className="space-y-3">
        <div className="flex justify-between items-center p-3 bg-gray-900/50 rounded">
          <span className="text-gray-300">Companies Income Tax (CIT)</span>
          <span className="text-white font-semibold">
            {formatCurrency(state.taxData.currentLiability * 0.5)}
          </span>
        </div>
        <div className="flex justify-between items-center p-3 bg-gray-900/50 rounded">
          <span className="text-gray-300">Value Added Tax (VAT)</span>
          <span className="text-white font-semibold">
            {formatCurrency(state.taxData.currentLiability * 0.3)}
          </span>
        </div>
        <div className="flex justify-between items-center p-3 bg-gray-900/50 rounded">
          <span className="text-gray-300">Capital Gains Tax (CGT)</span>
          <span className="text-white font-semibold">
            {formatCurrency(state.taxData.currentLiability * 0.1)}
          </span>
        </div>
        <div className="flex justify-between items-center p-3 bg-gray-900/50 rounded">
          <span className="text-gray-300">Development Levy</span>
          <span className="text-white font-semibold">
            {formatCurrency(state.taxData.currentLiability * 0.1)}
          </span>
        </div>
      </div>
      
      {state.taxData.confidenceScore < 0.7 && (
        <div className="mt-4 p-3 bg-yellow-900/20 border border-yellow-500/30 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-yellow-400" />
            <span className="text-yellow-400 text-sm">
              Confidence: {Math.round(state.taxData.confidenceScore * 100)}% • Complete audit profile for more accuracy
            </span>
          </div>
        </div>
      )}
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
        <FileText className="h-8 w-8 text-blue-400 mb-3" />
        <h3 className="text-white font-semibold mb-2">Audit Profile</h3>
        <p className="text-gray-400 text-sm mb-4">Upload and organize your compliance documents for audit readiness</p>
        <div className="flex justify-between items-center">
          <span className="text-2xl font-bold text-white">{state.metrics.documents_count}</span>
          <button 
            className="text-blue-400 text-sm hover:text-blue-300 flex items-center gap-1"
            onClick={() => {
              const element = document.getElementById('audit-profile-section');
              if (element) element.scrollIntoView({ behavior: 'smooth' });
            }}
          >
            View Documents <ExternalLink className="h-3 w-3" />
          </button>
        </div>
      </div>

      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
        <TrendingUp className="h-8 w-8 text-green-400 mb-3" />
        <h3 className="text-white font-semibold mb-2">Tax Exemptions</h3>
        <p className="text-gray-400 text-sm mb-4">Discover {state.taxData.exemptions.length} exemptions you qualify for</p>
        <div className="flex justify-between items-center">
          <span className="text-2xl font-bold text-white">
            {formatCurrency(state.taxData.exemptions.reduce((sum: number, e: any) => sum + (e.estimated_savings || 0), 0))}
          </span>
          <button 
            className="text-green-400 text-sm hover:text-green-300 flex items-center gap-1"
            onClick={() => {
              const element = document.getElementById('exemptions-section');
              if (element) element.scrollIntoView({ behavior: 'smooth' });
            }}
          >
            Check Eligibility <ExternalLink className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  </div>
);

// 🚨 SIMPLIFIED: AuditProfileTab
const AuditProfileTab = ({ documents, onRefresh, onDocumentsUpdate }: any) => {
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<keyof typeof DOCUMENT_CHECKLIST_MAP>('C');
  const [selectedType, setSelectedType] = useState('');
  const [localDocuments, setLocalDocuments] = useState<Document[]>(documents);

  // Sync local state with props
  useEffect(() => {
    setLocalDocuments(documents);
  }, [documents]);

  // Calculate accurate document counts for each category
  const categoryStats = useMemo(() => {
    const stats: Record<string, { total: number, completed: number, percentage: number }> = {};
    Object.keys(DOCUMENT_CHECKLIST_MAP).forEach(category => {
      stats[category] = SyncEngine.getCategoryStats(category, localDocuments);
    });
    return stats;
  }, [localDocuments]);

  // Get available document types for selected category
  const availableDocumentTypes = useMemo(() => {
    return SyncEngine.getAvailableDocumentTypesForCategory(selectedCategory, localDocuments);
  }, [selectedCategory, localDocuments]);

  // Check if category is complete
  const isCategoryComplete = useMemo(() => {
    return SyncEngine.isCategoryComplete(selectedCategory, localDocuments);
  }, [selectedCategory, localDocuments]);

  // Auto-select first available document type
  useEffect(() => {
    if (availableDocumentTypes.length > 0 && !selectedType) {
      setSelectedType(availableDocumentTypes[0].value);
    } else if (availableDocumentTypes.length === 0) {
      setSelectedType('');
    }
  }, [availableDocumentTypes, selectedType]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check if category is complete
    if (isCategoryComplete) {
      toast.error(`All documents for Category ${selectedCategory} have been uploaded.`);
      return;
    }

    // Check if document type is selected
    if (!selectedType) {
      toast.error('Please select a document type');
      return;
    }

    try {
      setUploading(true);
      if (file.size > 10 * 1024 * 1024) {
        toast.error('File size exceeds 10MB limit');
        return;
      }
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('category', selectedCategory);
      formData.append('document_type', selectedType);

      const response = await apiClient.post('/api/v1/compliance/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const newDocument = response.data?.document || {
        id: `doc_${Date.now()}`,
        file_name: file.name,
        category: selectedCategory,
        document_type: selectedType,
        created_at: new Date().toISOString(),
        file_size: file.size
      };

      // Update local state immediately for instant feedback
      setLocalDocuments(prev => [...prev, newDocument]);

      // Notify parent to recalculate sync
      if (onDocumentsUpdate) {
        onDocumentsUpdate();
      }

      toast.success('Document uploaded successfully!');
      
      // Full refresh to ensure sync with backend
      setTimeout(() => {
        if (onRefresh) onRefresh();
      }, 500);
      
    } catch (error: any) {
      console.error('❌ Upload error:', error);
      let errorMsg = 'Upload failed';
      if (error.response?.data?.detail) errorMsg = error.response.data.detail;
      else if (error.response?.data?.message) errorMsg = error.response.data.message;
      else if (error.message) errorMsg = error.message;
      toast.error(`Upload failed: ${errorMsg}`);
    } finally {
      setUploading(false);
      if (e.target) e.target.value = '';
    }
  };

  const handleDelete = async (documentId: string) => {
    if (!confirm('Delete this document?')) return;
    
    try {
      setDeletingId(documentId);
      
      // Update local state immediately for instant feedback
      setLocalDocuments(prev => prev.filter(doc => doc.id !== documentId));

      // Notify parent to recalculate sync
      if (onDocumentsUpdate) {
        onDocumentsUpdate();
      }

      await apiClient.delete(`/api/v1/compliance/documents/${documentId}`);
      
      toast.success('Document deleted successfully!');
      
      // Full refresh to ensure sync with backend
      setTimeout(() => {
        if (onRefresh) onRefresh();
      }, 500);
      
    } catch (error: any) {
      console.error('❌ Delete error:', error);
      toast.error('Failed to delete document');
      // Revert local state on error
      if (onRefresh) onRefresh();
    } finally {
      setDeletingId(null);
    }
  };

  // Group documents by category for display
  const documentsByCategory = useMemo(() => {
    const grouped: Record<string, Document[]> = {};
    localDocuments.forEach(doc => {
      if (!grouped[doc.category]) grouped[doc.category] = [];
      grouped[doc.category].push(doc);
    });
    return grouped;
  }, [localDocuments]);

  return (
    <div className="space-y-6" id="audit-profile-section">
      {/* Upload Section - SIMPLIFIED */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
        <h3 className="text-lg font-bold text-white mb-4">Upload Audit Document</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Category *</label>
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value as keyof typeof DOCUMENT_CHECKLIST_MAP);
                setSelectedType('');
              }}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {Object.entries(DOCUMENT_CHECKLIST_MAP).map(([code, category]) => {
                const stats = categoryStats[code] || { completed: 0, total: 0 };
                return (
                  <option key={code} value={code}>
                    {code} - {category.category_name} ({stats.completed}/{stats.total})
                  </option>
                );
              })}
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Document Type *</label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              disabled={availableDocumentTypes.length === 0 || isCategoryComplete}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">Select document type</option>
              {availableDocumentTypes.map(doc => (
                <option key={doc.value} value={doc.value}>
                  {doc.label}
                </option>
              ))}
            </select>
            {availableDocumentTypes.length === 0 && !isCategoryComplete ? (
              <p className="text-xs text-green-500 mt-1">
                ✅ All document types for this category have been uploaded
              </p>
            ) : null}
          </div>
        </div>

        <label className={`flex items-center justify-center gap-2 px-6 py-4 ${isCategoryComplete ? 'bg-gray-700 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 cursor-pointer'} text-white font-semibold rounded-lg transition-colors disabled:opacity-50`}>
          {isCategoryComplete ? (
            <>
              <Lock className="h-5 w-5" />
              Category Complete - Cannot Upload More
            </>
          ) : uploading ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              Uploading...
            </>
          ) : (
            <>
              <Upload className="h-5 w-5" />
              Choose File (PDF, JPG, PNG, DOC)
              <input
                type="file"
                onChange={handleUpload}
                disabled={uploading || isCategoryComplete || !selectedType}
                className="hidden"
                accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
              />
            </>
          )}
        </label>
        <p className="text-xs text-gray-500 mt-2 text-center">Max file size: 10MB</p>
      </div>

      {/* Documents by Category - SIMPLIFIED */}
      <div className="space-y-6">
        {Object.entries(DOCUMENT_CHECKLIST_MAP).map(([categoryCode, categoryData]) => {
          const categoryDocuments = documentsByCategory[categoryCode] || [];
          const stats = categoryStats[categoryCode] || { completed: 0, total: 0 };
          
          return (
            <div key={categoryCode} className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gray-900 rounded-lg">
                    {categoryData.icon}
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white">
                      {categoryCode}. {categoryData.category_name}
                    </h3>
                    <p className="text-sm text-gray-400">
                      {stats.completed} of {stats.total} documents uploaded
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {stats.completed === stats.total ? (
                    <span className="px-3 py-1 bg-green-500/20 text-green-400 text-sm rounded-full flex items-center gap-1">
                      <CheckCircle className="h-3 w-3" />
                      Complete
                    </span>
                  ) : (
                    <span className="px-3 py-1 bg-yellow-500/20 text-yellow-400 text-sm rounded-full">
                      {stats.total - stats.completed} remaining
                    </span>
                  )}
                </div>
              </div>
              
              {categoryDocuments.length === 0 ? (
                <div className="text-center py-6 border border-dashed border-gray-700/50 rounded-lg">
                  <FileText className="h-12 w-12 text-gray-600 mx-auto mb-4" />
                  <p className="text-gray-400">No documents uploaded for this category</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {categoryDocuments.map((doc) => (
                    <div 
                      key={doc.id} 
                      className="flex items-center justify-between p-4 bg-gray-900/50 rounded-lg hover:bg-gray-900 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <FileText className="h-5 w-5 text-blue-400 flex-shrink-0" />
                        <div className="min-w-0 flex-1">
                          <p className="text-white font-medium truncate" title={doc.file_name}>
                            {doc.file_name}
                          </p>
                          <div className="flex flex-wrap items-center gap-2 text-xs text-gray-400 mt-1">
                            <span className="bg-gray-800 px-2 py-0.5 rounded">
                              {SyncEngine.getDocumentTypeName(doc.category, doc.document_type)}
                            </span>
                            <span>•</span>
                            <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                            <span>•</span>
                            <span>{doc.file_size ? Math.round(doc.file_size / 1024) : 'Unknown'}KB</span>
                          </div>
                        </div>
                      </div>
                      
                      <button
                        onClick={() => handleDelete(doc.id)}
                        disabled={deletingId === doc.id}
                        className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors disabled:opacity-50 ml-4"
                        title="Delete document"
                      >
                        {deletingId === doc.id ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// 🚨 AIR-TIGHT TaxCalculatorTab with fixed Development Levy display
const TaxCalculatorTab = ({ formatCurrency, onCalculationComplete, currentTaxData }: any) => {
  const [inputs, setInputs] = useState({
    entity_type: 'company',
    annual_turnover: '',
    annual_profit: '',
    digital_gains: '',
    vat_supplies: '',
    rnd_expenses: '',
    fixed_assets: '',
    employee_count: '',
    industry_sector: 'technology',
    exports_digital_services: false
  });
  const [result, setResult] = useState<any>(null);
  const [calculating, setCalculating] = useState(false);
  const [showLegalBasis, setShowLegalBasis] = useState(false);

  const calculate = async () => {
    if (!inputs.annual_turnover) {
      toast.error('Please enter Annual Turnover');
      return;
    }

    try {
      setCalculating(true);
      
      let calculationResult = null;
      
      try {
        const response = await apiClient.post('/api/v2/tax/calculator/instant', {
          entity_type: inputs.entity_type,
          annual_turnover: parseFloat(inputs.annual_turnover) || 0,
          annual_profit: inputs.annual_profit ? parseFloat(inputs.annual_profit) : undefined,
          vat_taxable_supplies: parseFloat(inputs.vat_supplies) || 0,
          digital_asset_gains: parseFloat(inputs.digital_gains) || 0,
          rnd_expenses: parseFloat(inputs.rnd_expenses) || 0,
          fixed_assets: parseFloat(inputs.fixed_assets) || 0,
          employee_count: parseInt(inputs.employee_count) || 0,
          industry_sector: inputs.industry_sector,
          exports_digital_services: inputs.exports_digital_services,
          tax_year: new Date().getFullYear()
        });
        
        if (response.data.success) {
          calculationResult = response.data.results || response.data.data;
          toast.success('Tax calculated using Nigeria Tax Act 2025!');
        }
      } catch (apiError: any) {
        console.warn('⚠️ V2 API failed, trying V1:', apiError);
        
        try {
          const v1Response = await apiClient.post('/api/v1/tax/calculate', {
            scenario_data: {
              entity_type: inputs.entity_type,
              annual_turnover: parseFloat(inputs.annual_turnover) || 0,
              annual_profit: parseFloat(inputs.annual_profit) || 0,
              digital_asset_gains: parseFloat(inputs.digital_gains) || 0,
              vat_taxable_supplies: parseFloat(inputs.vat_supplies) || 0,
              fixed_assets: parseFloat(inputs.fixed_assets) || 0
            }
          });
          
          if (v1Response.data.success) {
            calculationResult = v1Response.data.data;
            toast.success('Tax calculated successfully!');
          }
        } catch (v1Error) {
          console.warn('⚠️ V1 API also failed, using browser calculation:', v1Error);
        }
      }
      
      if (!calculationResult) {
        calculationResult = generateMockTaxCalculation({
          entity_type: inputs.entity_type,
          annual_turnover: parseFloat(inputs.annual_turnover) || 0,
          annual_profit: parseFloat(inputs.annual_profit) || 0,
          vat_taxable_supplies: parseFloat(inputs.vat_supplies) || 0,
          digital_asset_gains: parseFloat(inputs.digital_gains) || 0,
          rnd_expenses: parseFloat(inputs.rnd_expenses) || 0,
          fixed_assets: parseFloat(inputs.fixed_assets) || 0,
          employee_count: parseInt(inputs.employee_count) || 0,
          industry_sector: inputs.industry_sector,
          exports_digital_services: inputs.exports_digital_services
        });
        
        toast.success('Tax calculated using Browser Engine (API unavailable)');
      }
      
      setResult(calculationResult);
      
      if (onCalculationComplete) {
        onCalculationComplete(calculationResult);
      }
      
    } catch (error: any) {
      console.error('❌ Calculation error:', error);
      toast.error('Calculation failed. Please check your inputs.');
    } finally {
      setCalculating(false);
    }
  };

  const downloadReport = () => {
    if (!result) return;
    
    const reportHTML = `
<!DOCTYPE html>
<html>
<head>
  <title>Tax Calculation Report - Nigeria Tax Act 2025</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    .header { border-bottom: 3px solid #4CAF50; padding-bottom: 20px; margin-bottom: 30px; }
    .summary { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
    .section { margin: 25px 0; }
    table { width: 100%; border-collapse: collapse; margin: 15px 0; }
    th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
    th { background-color: #4CAF50; color: white; }
    .highlight { background-color: #e8f5e8; padding: 10px; border-radius: 5px; }
    .footnote { font-size: 12px; color: #666; margin-top: 30px; }
    .risk { color: #d32f2f; }
    .savings { color: #388e3c; }
    .note { background-color: #fffde7; padding: 10px; border-radius: 5px; margin: 10px 0; }
  </style>
</head>
<body>
  <div class="header">
    <h1>Tax Calculation Report - Nigeria Tax Act 2025</h1>
    <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
    <p><strong>Legislation:</strong> Nigeria Tax Act 2025 & Nigeria Tax Administration Act 2025</p>
    <p><strong>Calculation Engine:</strong> ${result.mock_data ? 'Browser Engine' : 'Legislative Engine'}</p>
    <p><strong>Company Size:</strong> ${result.is_small_company ? 'Small Company (≤ ₦100M turnover & ≤ ₦250M fixed assets)' : 'Standard Company'}</p>
  </div>
  
  <div class="section">
    <h2>Business Profile</h2>
    <table>
      <tr><td><strong>Entity Type:</strong></td><td>${inputs.entity_type}</td></tr>
      <tr><td><strong>Annual Turnover:</strong></td><td>${formatCurrency(parseFloat(inputs.annual_turnover) || 0)}</td></tr>
      <tr><td><strong>Annual Profit:</strong></td><td>${formatCurrency(parseFloat(inputs.annual_profit) || 0)}</td></tr>
      <tr><td><strong>Fixed Assets:</strong></td><td>${formatCurrency(parseFloat(inputs.fixed_assets) || 0)}</td></tr>
      <tr><td><strong>Industry Sector:</strong></td><td>${inputs.industry_sector}</td></tr>
      <tr><td><strong>Employee Count:</strong></td><td>${inputs.employee_count}</td></tr>
      <tr><td><strong>Digital Exports:</strong></td><td>${inputs.exports_digital_services ? 'Yes (0% VAT)' : 'No'}</td></tr>
      <tr><td><strong>Digital Asset Gains:</strong></td><td>${formatCurrency(parseFloat(inputs.digital_gains) || 0)}</td></tr>
      <tr><td><strong>R&D Expenses:</strong></td><td>${formatCurrency(parseFloat(inputs.rnd_expenses) || 0)}</td></tr>
    </table>
  </div>
  
  <div class="section">
    <h2>Tax Liability Summary</h2>
    <div class="highlight">
      <h3>Total Tax Liability: ${formatCurrency(result.total_liability || 0)}</h3>
      <p>Effective Tax Rate: ${(result.effective_tax_rate * 100).toFixed(2)}%</p>
      <p class="savings">Total Savings from Exemptions: ${formatCurrency(result.total_savings || 0)}</p>
      <p>Confidence Score: ${Math.round((result.confidence_score || 0) * 100)}%</p>
    </div>
  </div>
  
  <div class="section">
    <h2>Tax Breakdown (Nigeria Tax Act 2025)</h2>
    <table>
      <thead>
        <tr>
          <th>Tax Type</th>
          <th>Taxable Amount</th>
          <th>Tax Rate</th>
          <th>Tax Amount</th>
          <th>Notes</th>
        </tr>
      </thead>
      <tbody>
        ${Object.entries(result.breakdown || {}).map(([taxType, details]: [string, any]) => {
          if (!details) return '';
          
          let taxableAmount = 0;
          let taxRate = 0;
          let notes = '';
          
          switch(details.tax_type) {
            case 'CIT':
              taxableAmount = details.taxable_profit || 0;
              taxRate = details.tax_rate || 0;
              notes = details.company_size === 'small' ? '0% for small companies' : '30% standard rate';
              break;
            case 'VAT':
              taxableAmount = details.taxable_supplies || 0;
              taxRate = details.vat_rate || 0;
              notes = details.requires_registration ? 'Registration required' : '';
              break;
            case 'CGT_DIGITAL':
              taxableAmount = details.digital_asset_gains || 0;
              taxRate = details.cgt_rate || 0;
              notes = details.small_company_exempt ? '0% for small companies' : '30% standard rate';
              break;
            case 'DEVELOPMENT_LEVY':
              taxableAmount = details.assessable_profit || 0;
              taxRate = details.rate || 0;
              notes = details.exempt_for_small ? '0% for small companies' : '4% on assessable profit';
              break;
          }
          
          return `
          <tr>
            <td>${details.tax_type}</td>
            <td>${formatCurrency(taxableAmount)}</td>
            <td>${(taxRate * 100).toFixed(1)}%</td>
            <td>${formatCurrency(details.amount || 0)}</td>
            <td><small>${notes}</small></td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>
    
    ${result.is_small_company ? `
    <div class="note">
      <p><strong>Note:</strong> This company qualifies as a Small Company (turnover ≤ ₦100M and fixed assets ≤ ₦250M).</p>
      <p>Benefits: 0% CIT, 0% CGT, and 0% Development Levy.</p>
    </div>
    ` : ''}
  </div>
  
  ${result.exemptions_applied && result.exemptions_applied.length > 0 ? `
  <div class="section">
    <h2>Qualified Exemptions (${result.exemptions_applied.length})</h2>
    <table>
      <thead>
        <tr>
          <th>Exemption</th>
          <th>Legal Basis</th>
          <th>Estimated Savings</th>
        </tr>
      </thead>
      <tbody>
        ${result.exemptions_applied.map((ex: any, idx: number) => `
          <tr>
            <td>
              <strong>${ex.name || ex.exemption_name}</strong><br>
              <small>${ex.description}</small>
            </td>
            <td>${ex.act_section}</td>
            <td class="savings">${formatCurrency(ex.estimated_savings || 0)}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  </div>
  ` : ''}
  
  ${result.recommendations && result.recommendations.length > 0 ? `
  <div class="section">
    <h2>Recommendations</h2>
    <ul>
      ${result.recommendations.map((rec: string) => `<li>${rec}</li>`).join('')}
    </ul>
  </div>
  ` : ''}
  
  ${result.risk_flags && result.risk_flags.length > 0 ? `
  <div class="section">
    <h2 class="risk">Compliance Risks</h2>
    <ul>
      ${result.risk_flags.map((risk: string) => `<li class="risk">${risk}</li>`).join('')}
    </ul>
  </div>
  ` : ''}
  
  ${result.citations && result.citations.length > 0 ? `
  <div class="section">
    <h2>Legal Citations (Nigeria Tax Act 2025)</h2>
    <ul>
      ${result.citations.map((citation: any) => 
        `<li><strong>${citation.section}:</strong> ${citation.description} (Applies to: ${citation.applies_to})</li>`
      ).join('')}
    </ul>
  </div>
  ` : ''}
  
  <div class="footnote">
    <p>Generated by Nigerian Tax Compliance Platform on ${new Date().toLocaleString()}</p>
    <p>This report is for informational purposes only. Consult a tax professional for specific advice.</p>
    <p><strong>Disclaimer:</strong> Based on Nigeria Tax Act 2025 & Nigeria Tax Administration Act 2025</p>
    <p><strong>Important:</strong> All calculations assume compliance with filing deadlines and proper documentation.</p>
  </div>
</body>
</html>
    `;

    const blob = new Blob([reportHTML], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tax-calculation-report-${new Date().toISOString().split('T')[0]}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success('Report downloaded as HTML! Print to PDF or save as HTML.');
    
    setTimeout(() => {
      const printWindow = window.open('', '_blank');
      if (printWindow) {
        printWindow.document.write(reportHTML);
        printWindow.document.close();
      }
    }, 500);
  };

  return (
    <div className="space-y-6" id="calculator-section">
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-white">Calculate Your Tax Liability</h3>
          <div className="flex items-center gap-2 text-sm text-blue-400">
            <Scale className="h-4 w-4" />
            <span>Nigeria Tax Act 2025</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Entity Type *</label>
            <select
              value={inputs.entity_type}
              onChange={(e) => setInputs({ ...inputs, entity_type: e.target.value })}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="company">Company</option>
              <option value="individual">Individual</option>
              <option value="partnership">Partnership</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Annual Turnover (₦) *</label>
            <input
              type="number"
              value={inputs.annual_turnover}
              onChange={(e) => setInputs({ ...inputs, annual_turnover: e.target.value })}
              placeholder="Enter your annual turnover"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500"
              required
            />
            <p className="text-xs text-gray-500 mt-1">≤ ₦100M for small company qualification</p>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Annual Profit (₦)</label>
            <input
              type="number"
              value={inputs.annual_profit}
              onChange={(e) => setInputs({ ...inputs, annual_profit: e.target.value })}
              placeholder="Enter annual profit"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Fixed Assets (₦)</label>
            <input
              type="number"
              value={inputs.fixed_assets}
              onChange={(e) => setInputs({ ...inputs, fixed_assets: e.target.value })}
              placeholder="Enter fixed assets value"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <p className="text-xs text-gray-500 mt-1">≤ ₦250M for small company qualification</p>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">VAT Taxable Supplies (₦)</label>
            <input
              type="number"
              value={inputs.vat_supplies}
              onChange={(e) => setInputs({ ...inputs, vat_supplies: e.target.value })}
              placeholder="Enter VAT taxable supplies"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <p className="text-xs text-gray-500 mt-1">Registration threshold: ₦50M</p>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Digital Asset Gains (₦)</label>
            <input
              type="number"
              value={inputs.digital_gains}
              onChange={(e) => setInputs({ ...inputs, digital_gains: e.target.value })}
              placeholder="Enter digital asset gains"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <p className="text-xs text-gray-500 mt-1">✅ 0% for small companies, 30% otherwise</p>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">R&D Expenses (₦)</label>
            <input
              type="number"
              value={inputs.rnd_expenses}
              onChange={(e) => setInputs({ ...inputs, rnd_expenses: e.target.value })}
              placeholder="Enter R&D expenses"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <p className="text-xs text-gray-500 mt-1">Deductible up to 5% of turnover</p>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Employee Count</label>
            <input
              type="number"
              value={inputs.employee_count}
              onChange={(e) => setInputs({ ...inputs, employee_count: e.target.value })}
              placeholder="Enter number of employees"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
        </div>

        <div className="flex items-center gap-3 mb-6">
          <div className="flex-1">
            <label className="block text-sm text-gray-400 mb-2">Industry Sector</label>
            <select
              value={inputs.industry_sector}
              onChange={(e) => setInputs({ ...inputs, industry_sector: e.target.value })}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="technology">Technology</option>
              <option value="agriculture">Agriculture</option>
              <option value="manufacturing">Manufacturing</option>
              <option value="services">Services</option>
              <option value="retail">Retail</option>
              <option value="general">General</option>
            </select>
          </div>
          
          <div className="pt-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={inputs.exports_digital_services}
                onChange={(e) => setInputs({ ...inputs, exports_digital_services: e.target.checked })}
                className="rounded border-gray-600 bg-gray-800 text-blue-500"
              />
              <span className="text-sm text-gray-400">Exports Digital Services</span>
            </label>
            <p className="text-xs text-gray-500 mt-1">Qualifies for 0% VAT</p>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={calculate}
            disabled={calculating || !inputs.annual_turnover}
            className="flex-1 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {calculating ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Calculating...
              </>
            ) : (
              <>
                <Calculator className="h-5 w-5" />
                Calculate Tax Liability
              </>
            )}
          </button>
          
          {result && (
            <button
              onClick={downloadReport}
              className="px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <Download className="h-5 w-5" />
              Report
            </button>
          )}
        </div>
        
        <p className="text-xs text-gray-500 text-center mt-3">
          {result?.mock_data ? '🌐 Browser calculation (API unavailable)' : '⚡ Legislative Engine'} • Nigeria Tax Act 2025
        </p>
      </div>

      {result && (
        <div className="space-y-4">
          <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-6">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h3 className="text-xl font-bold text-white mb-2">Calculation Results</h3>
                <div className="flex items-center gap-2">
                  {result.mock_data ? (
                    <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded">Browser Engine</span>
                  ) : (
                    <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded">Legislative Engine</span>
                  )}
                  <span className={`px-2 py-1 ${result.is_small_company ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'} text-xs rounded`}>
                    {result.is_small_company ? 'Small Company' : 'Standard Company'}
                  </span>
                  <span className="text-sm text-gray-400">
                    Confidence: {Math.round((result.confidence_score || 0) * 100)}%
                  </span>
                </div>
              </div>
              <button
                onClick={() => setShowLegalBasis(!showLegalBasis)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors"
              >
                {showLegalBasis ? 'Hide Legal Basis' : 'Show Legal Basis'}
              </button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="bg-gray-900/70 rounded-lg p-4">
                <div className="text-sm text-gray-400 mb-1">Total Tax Liability</div>
                <div className="text-3xl font-bold text-red-400">{formatCurrency(result.total_liability || 0)}</div>
                <div className="text-xs text-gray-500 mt-1">After exemptions and deductions</div>
              </div>
              
              <div className="bg-gray-900/70 rounded-lg p-4">
                <div className="text-sm text-gray-400 mb-1">Total Savings (Exemptions)</div>
                <div className="text-3xl font-bold text-green-400">{formatCurrency(result.total_savings || 0)}</div>
                <div className="text-xs text-gray-500 mt-1">From {result.exemptions_applied?.length || 0} exemptions</div>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
              <div className="bg-gray-900/50 rounded-lg p-3">
                <div className="text-sm text-gray-400 mb-1">Effective Tax Rate</div>
                <div className="text-xl font-bold text-white">{(result.effective_tax_rate * 100).toFixed(1)}%</div>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-3">
                <div className="text-sm text-gray-400 mb-1">Tax Year</div>
                <div className="text-xl font-bold text-white">{result.tax_year || new Date().getFullYear()}</div>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-3">
                <div className="text-sm text-gray-400 mb-1">Calculation Time</div>
                <div className="text-xl font-bold text-white">
                  {result.calculated_at ? new Date(result.calculated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'Just now'}
                </div>
              </div>
            </div>
            
            <div className="space-y-3">
              <h4 className="text-white font-semibold">Tax Breakdown (Nigeria Tax Act 2025)</h4>
              {result.breakdown && Object.entries(result.breakdown).map(([taxType, details]: [string, any]) => (
                details && (
                  <div key={taxType} className="flex justify-between items-center p-3 bg-gray-900/50 rounded">
                    <div>
                      <span className="text-gray-300">{details.tax_type || taxType.toUpperCase()}</span>
                      <div className="text-xs text-gray-500">
                        {(() => {
                          let rateText = '';
                          let amountText = '';
                          
                          switch(details.tax_type) {
                            case 'CIT':
                              rateText = `Rate: ${(details.tax_rate * 100).toFixed(1)}%`;
                              amountText = `On ${formatCurrency(details.taxable_profit)}`;
                              break;
                            case 'VAT':
                              rateText = `Rate: ${(details.vat_rate * 100).toFixed(1)}%`;
                              amountText = `On ${formatCurrency(details.taxable_supplies)}`;
                              break;
                            case 'CGT_DIGITAL':
                              rateText = `Rate: ${(details.cgt_rate * 100).toFixed(1)}%`;
                              amountText = `On ${formatCurrency(details.digital_asset_gains)}`;
                              break;
                            case 'DEVELOPMENT_LEVY':
                              rateText = `Rate: ${(details.rate * 100).toFixed(1)}%`; // ✅ Now shows 0% for small companies
                              amountText = `On ${formatCurrency(details.assessable_profit)}`;
                              break;
                          }
                          
                          return (
                            <>
                              <div>{rateText}</div>
                              {amountText && <div>{amountText}</div>}
                            </>
                          );
                        })()}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-white font-semibold">{formatCurrency(details.amount || 0)}</div>
                    </div>
                  </div>
                )
              ))}
            </div>
          </div>
          
          {showLegalBasis && result.citations && result.citations.length > 0 && (
            <div className="bg-gradient-to-br from-blue-900/20 to-indigo-900/20 border border-blue-500/30 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <BookOpen className="h-5 w-5 text-blue-400" />
                <h4 className="text-lg font-semibold text-white">Legal Basis for Calculation</h4>
              </div>
              
              <div className="space-y-3">
                {result.citations.map((citation: any, idx: number) => (
                  <div key={idx} className="p-3 bg-gray-900/30 rounded-lg">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-blue-400 font-medium">{citation.section}</div>
                        <div className="text-sm text-gray-300 mt-1">{citation.description}</div>
                      </div>
                      <div className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">
                        {citation.applies_to}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="mt-4 pt-4 border-t border-blue-500/30 text-center">
                <p className="text-sm text-gray-400">
                  All calculations comply with Nigeria Tax Act 2025 & Nigeria Tax Administration Act 2025
                </p>
              </div>
            </div>
          )}
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {result.recommendations && result.recommendations.length > 0 && (
              <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Lightbulb className="h-5 w-5 text-green-400" />
                  <h4 className="text-green-400 font-semibold">Recommendations</h4>
                </div>
                <ul className="space-y-2">
                  {result.recommendations.map((rec: string, idx: number) => (
                    <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                      <span className="text-green-400 mt-1">•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {result.risk_flags && result.risk_flags.length > 0 && (
              <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="h-5 w-5 text-red-400" />
                  <h4 className="text-red-400 font-semibold">Compliance Risks</h4>
                </div>
                <ul className="space-y-2">
                  {result.risk_flags.map((risk: string, idx: number) => (
                    <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                      <span className="text-red-400 mt-1">•</span>
                      <span>{risk}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          
          {result.exemptions_applied && result.exemptions_applied.length > 0 && (
            <div className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/30 rounded-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h4 className="text-lg font-semibold text-white">Qualified Exemptions</h4>
                <span className="px-3 py-1 bg-purple-500/20 text-purple-400 text-sm rounded-full">
                  {result.exemptions_applied.length} applied
                </span>
              </div>
              
              <div className="space-y-3">
                {result.exemptions_applied.map((exemption: any, idx: number) => (
                  <div key={idx} className="p-4 bg-gray-900/30 rounded-lg">
                    <div className="flex justify-between items-start">
                      <div>
                        <h5 className="text-white font-medium">{exemption.name || exemption.exemption_name}</h5>
                        <p className="text-sm text-gray-400 mt-1">{exemption.description}</p>
                        <div className="flex items-center gap-2 mt-2">
                          <BookOpen className="h-3 w-3 text-blue-400" />
                          <span className="text-xs text-blue-400">{exemption.act_section}</span>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xl font-bold text-green-400">
                          {formatCurrency(exemption.estimated_savings || 0)}
                        </div>
                        <div className="text-xs text-gray-500">Annual Savings</div>
                      </div>
                    </div>
                    
                    {exemption.required_documents && (
                      <div className="mt-3 pt-3 border-t border-gray-700/50">
                        <div className="text-xs text-gray-500 mb-1">Required Documents:</div>
                        <div className="flex flex-wrap gap-1">
                          {exemption.required_documents.map((doc: string, docIdx: number) => (
                            <span key={docIdx} className="px-2 py-1 bg-gray-800 text-gray-300 text-xs rounded">
                              {doc}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const ExemptionsTab = ({ exemptions, formatCurrency }: any) => (
  <div className="space-y-4" id="exemptions-section">
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xl font-bold text-white">You Qualify For {exemptions.length} Exemptions</h3>
        <div className="text-2xl font-bold text-green-400">
          {formatCurrency(exemptions.reduce((sum: number, e: any) => sum + (e.estimated_savings || 0), 0))}
        </div>
      </div>
      <p className="text-gray-400 mb-6">Total estimated annual tax savings under Nigeria Tax Act 2025</p>

      <div className="space-y-4">
        {exemptions.length === 0 ? (
          <div className="text-center py-8">
            <TrendingUp className="h-12 w-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No exemptions qualified yet</p>
            <p className="text-gray-500 text-sm mt-2">Complete tax calculation to discover savings</p>
          </div>
        ) : (
          exemptions.map((exemption: any, idx: number) => (
            <div key={idx} className="bg-gray-900/50 border border-gray-700 rounded-xl p-5">
              <div className="flex justify-between items-start mb-3">
                <div className="flex-1">
                  <h4 className="text-white font-semibold text-lg mb-1">{exemption.name || exemption.exemption_name}</h4>
                  <p className="text-gray-400 text-sm mb-2">{exemption.description}</p>
                  <p className="text-xs text-blue-400">📖 {exemption.act_section}</p>
                </div>
                <div className="text-right ml-4">
                  <div className="text-2xl font-bold text-green-400">{formatCurrency(exemption.estimated_savings)}</div>
                  <div className="text-xs text-gray-500">Annual Savings</div>
                </div>
              </div>

              <div className="flex items-center gap-2 mt-4 pt-4 border-t border-gray-700">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <span className="text-sm text-gray-400">Required: {exemption.required_documents?.join(', ') || 'No specific documents required'}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  </div>
);

// ============================================
// MAIN COMPONENT WITH PERFECT SYNC ENGINE
// ============================================

const CompliancePage = () => {
  const [state, setState] = useState<ComplianceState>({
    loading: true,
    refreshing: false,
    subscription: null,
    checklist: [],
    documents: [],
    metrics: {
      documents_count: 0,
      total_items: 0,
      completed_items: 0,
      progress_percentage: 0,
      last_sync: new Date().toISOString()
    },
    systemStatus: {
      consistent: true,
      verified: false,
      last_verified: ''
    },
    taxData: {
      currentLiability: 0,
      exemptions: [],
      scenarios: [],
      deadlines: [],
      recommendations: [],
      riskFlags: [],
      confidenceScore: 0.0,
      legislationVersion: 'Nigeria Tax Act 2025',
      lastCalculated: ''
    }
  });

  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [authChecked, setAuthChecked] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<number>(Date.now());

  // Generate initial checklist from document mapping
  const generateInitialChecklist = useCallback((): ChecklistItem[] => {
    const checklist: ChecklistItem[] = [];
    
    Object.entries(DOCUMENT_CHECKLIST_MAP).forEach(([category, categoryData]) => {
      categoryData.items.forEach((item, index) => {
        checklist.push({
          id: `item_${category}_${index + 1}`,
          category: category as keyof typeof DOCUMENT_CHECKLIST_MAP,
          item_description: item.checklist_description,
          is_completed: false,
          document_uploaded: false,
          required_document_type: item.document_type
        });
      });
    });
    
    return checklist;
  }, []);

  // Edge-level sync calculation
  const calculateSyncMetrics = useCallback((checklist: ChecklistItem[], documents: Document[]) => {
    const metrics = SyncEngine.calculateProgress(checklist, documents);
    const syncedChecklist = SyncEngine.syncChecklistWithDocuments(checklist, documents);
    const isConsistent = SyncEngine.verifySyncConsistency(syncedChecklist, documents, metrics);
    
    return { metrics, syncedChecklist, isConsistent };
  }, []);

  const updateStateWithSync = useCallback((updates: Partial<ComplianceState>) => {
    setState(prev => {
      const newState = { ...prev, ...updates };
      
      // Always recalculate sync metrics when checklist or documents change
      if (updates.checklist || updates.documents) {
        const checklist = updates.checklist || newState.checklist;
        const documents = updates.documents || newState.documents;
        const { metrics, syncedChecklist, isConsistent } = calculateSyncMetrics(checklist, documents);
        
        return {
          ...newState,
          checklist: syncedChecklist,
          metrics,
          systemStatus: {
            ...newState.systemStatus,
            consistent: isConsistent,
            last_verified: new Date().toISOString()
          }
        };
      }
      
      return newState;
    });
    
    setLastSyncTime(Date.now());
  }, [calculateSyncMetrics]);

  // Handler for document updates
  const handleDocumentsUpdate = useCallback(() => {
    // Trigger immediate sync calculation
    const { metrics, syncedChecklist } = calculateSyncMetrics(state.checklist, state.documents);
    
    setState(prev => ({
      ...prev,
      checklist: syncedChecklist,
      metrics
    }));
    
    setLastSyncTime(Date.now());
    toast.success('Audit profile updated!');
  }, [state.checklist, state.documents, calculateSyncMetrics]);

  const updateTaxDataFromCalculator = useCallback((calculationResult: any) => {
    console.log('📊 CALCULATOR RESULT:', calculationResult);
    
    let exemptions = calculationResult.exemptions_applied || [];
    
    setState(prev => ({
      ...prev,
      taxData: {
        ...prev.taxData,
        currentLiability: calculationResult.total_liability || 0,
        exemptions: exemptions,
        recommendations: calculationResult.recommendations || [],
        riskFlags: calculationResult.risk_flags || [],
        confidenceScore: calculationResult.confidence_score || 0.0,
        legislationVersion: calculationResult.legislation_version || 'Nigeria Tax Act 2025',
        lastCalculated: calculationResult.calculated_at || new Date().toISOString()
      }
    }));
    
    console.log('✅ Setting exemptions:', exemptions.length, 'items');
    toast.success(`Tax calculation complete! ${exemptions.length} exemption${exemptions.length !== 1 ? 's' : ''} applied.`);
  }, []);

  const fetchData = async (showLoading = true, forceSync = false) => {
    try {
      if (showLoading) {
        updateStateWithSync({ loading: true });
      } else {
        updateStateWithSync({ refreshing: true });
      }

      console.log('📊 [Compliance] Fetching data with sync engine...', { forceSync });

      let currentSubscription = state.subscription;
      let hasActiveSubscription = false;

      // 1. Fetch subscription data
      try {
        const subRes = await apiClient.get('/api/v1/subscriptions/my-subscription');
        console.log('📋 Subscription API response:', subRes.data);
        
        currentSubscription = subRes.data?.subscription || null;
        hasActiveSubscription = subRes.data?.has_active_subscription || false;
        
        updateStateWithSync({ subscription: currentSubscription });
        
        console.log('📊 Subscription check:', {
          hasSubscription: !!currentSubscription,
          hasActiveSubscription,
          status: currentSubscription?.status
        });
        
        if (hasActiveSubscription === false) {
          console.log('⚠️ API confirmed: No active subscription, will show plans');
        } else if (currentSubscription) {
          console.log('✅ Active subscription confirmed:', currentSubscription.plan_code, '| Status:', currentSubscription.status);
        }
      } catch (error) {
        console.error('❌ Subscription check exception:', error);
        console.warn('⚠️ Subscription check failed, proceeding with fallback');
      }

      // 2. NEW: Initialize or fetch user's checklist from templates
      let checklist = generateInitialChecklist();
      try {
        // First, try to get user's existing checklist
        const checklistRes = await apiClient.get('/api/v1/compliance/checklist');
        
        if (checklistRes.data?.success && checklistRes.data.checklist?.length > 0) {
          // User has a checklist - use it
          const apiChecklist = checklistRes.data.checklist || [];
          checklist = apiChecklist.map((item: any) => {
            // Find the matching document type from our frontend mapping
            const categoryData = DOCUMENT_CHECKLIST_MAP[item.category];
            let required_document_type = item.required_document_type;
            
            if (!required_document_type && categoryData) {
              // Try to find by item description
              const matchedItem = categoryData.items.find(
                i => i.item_description === item.item_description || 
                    i.checklist_description === item.item_description
              );
              required_document_type = matchedItem?.document_type;
            }
            
            return {
              id: item.id,
              category: item.category,
              item_description: item.item_description,
              is_completed: item.is_completed || false,
              document_uploaded: item.document_uploaded || false,
              required_document_type: required_document_type || item.item_code?.toLowerCase()
            };
          });
          console.log('✅ User checklist loaded:', checklist.length, 'items');
        } else {
          // No checklist exists for this user - initialize from templates
          console.log('📋 No checklist found for user, initializing from templates...');
          
          try {
            // Call the initialize endpoint
            const initRes = await apiClient.post('/api/v1/compliance/checklist/initialize');
            
            if (initRes.data?.success) {
              // Get the newly created checklist
              const newChecklistRes = await apiClient.get('/api/v1/compliance/checklist');
              
              if (newChecklistRes.data?.success && newChecklistRes.data.checklist?.length > 0) {
                const apiChecklist = newChecklistRes.data.checklist || [];
                checklist = apiChecklist.map((item: any) => ({
                  id: item.id,
                  category: item.category,
                  item_description: item.item_description,
                  is_completed: item.is_completed || false,
                  document_uploaded: item.document_uploaded || false,
                  required_document_type: item.required_document_type || item.item_code?.toLowerCase()
                }));
                console.log('✅ Checklist initialized from templates:', checklist.length, 'items');
              } else {
                throw new Error('Failed to fetch initialized checklist');
              }
            } else {
              throw new Error('Initialization API returned failure');
            }
          } catch (initError) {
            console.error('❌ Checklist initialization failed:', initError);
            console.log('✅ Using generated checklist with document mapping');
            // Fallback to frontend-generated checklist
            checklist = generateInitialChecklist();
          }
        }
      } catch (checklistError) {
        console.error('❌ Checklist API failed:', checklistError);
        console.log('✅ Using generated checklist with document mapping');
        checklist = generateInitialChecklist();
      }

      // 3. Fetch user documents
      let documents = [];
      try {
        const docsRes = await apiClient.get('/api/v1/compliance/documents');
        if (docsRes.data?.success) {
          documents = docsRes.data.documents || [];
          console.log('✅ Documents loaded:', documents.length, 'documents');
        }
      } catch (docsError) {
        console.error('❌ Documents API failed:', docsError);
      }

      // 4. Fetch tax calculation data
      let taxCalculation = null;
      let exemptions = [];
      let deadlines = generateMockDeadlines();
      
      try {
        const v2Res = await apiClient.post('/api/v2/tax/calculator/instant', {
          entity_type: 'company',
          annual_turnover: 0,
          annual_profit: 0,
          vat_taxable_supplies: 0,
          digital_asset_gains: 0,
          rnd_expenses: 0,
          fixed_assets: 0,
          employee_count: 0,
          industry_sector: 'technology',
          exports_digital_services: false,
          tax_year: new Date().getFullYear()
        });
        
        if (v2Res.data.success) {
          taxCalculation = v2Res.data.results || v2Res.data.data;
          exemptions = taxCalculation?.exemptions_applied || exemptions;
          console.log('✅ [LEGISLATIVE] V2 tax calculation successful');
        } else {
          throw new Error('V2 calculation unsuccessful');
        }
      } catch (v2Error) {
        console.warn('⚠️ V2 legislative engine failed:', v2Error);
        // Use zero tax calculation
        taxCalculation = generateMockTaxCalculation();
        exemptions = taxCalculation.exemptions_applied || exemptions;
      }

      // 5. Fetch deadlines
      try {
        const deadlinesRes = await apiClient.get('/api/v1/tax/deadlines');
        if (deadlinesRes.data?.success) {
          deadlines = deadlinesRes.data.deadlines || deadlines;
        }
      } catch (deadlinesError) {
        console.warn('⚠️ Deadlines API failed, using mock deadlines:', deadlinesError);
      }

      // 6. Prepare tax data
      const taxData = {
        currentLiability: taxCalculation?.total_liability || 0,
        exemptions: exemptions,
        scenarios: [],
        deadlines: deadlines,
        recommendations: taxCalculation?.recommendations || [],
        riskFlags: taxCalculation?.risk_flags || [],
        confidenceScore: taxCalculation?.confidence_score || 0.0,
        legislationVersion: taxCalculation?.legislation_version || 'Nigeria Tax Act 2025',
        lastCalculated: taxCalculation?.calculated_at || new Date().toISOString()
      };

      // 7. Calculate sync metrics
      const { metrics, syncedChecklist } = calculateSyncMetrics(checklist, documents);

      // 8. Update state with all fetched data
      updateStateWithSync({
        loading: false,
        refreshing: false,
        subscription: currentSubscription,
        checklist: syncedChecklist,
        documents,
        metrics,
        systemStatus: {
          consistent: true,
          verified: true,
          last_verified: new Date().toISOString()
        },
        taxData
      });

      setAuthChecked(true);

      console.log('✅ [SYNC ENGINE] All data synchronized perfectly');
      console.log('📊 Sync Stats:', {
        documents: documents.length,
        checklist: syncedChecklist.length,
        completed: metrics.completed_items,
        progress: metrics.progress_percentage + '%',
        '1:1 Match': '✅ Enabled'
      });

    } catch (error) {
      console.error('❌ [Compliance] Data fetch failed:', error);
      updateStateWithSync({
        loading: false,
        refreshing: false,
        subscription: state.subscription
      });
      setAuthChecked(true);
      toast.error('Failed to load compliance data');
    }
  };

  // Initial data fetch
  useEffect(() => {
    fetchData();
  }, []);

  const formatCurrency = (amount: number): string => {
    try {
      if (typeof amount !== 'number' || isNaN(amount)) {
        return '₦0';
      }
      
      return new Intl.NumberFormat('en-NG', {
        style: 'currency',
        currency: 'NGN',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(amount);
    } catch (error) {
      console.error('Currency formatting error:', error);
      return `₦${amount.toFixed(0)}`;
    }
  };

  const handleRefresh = () => {
    console.log('🔄 Manual refresh triggered');
    fetchData(false, true);
  };

  // ============================================
  // LOADING STATE
  // ============================================

  if (state.loading && !authChecked) {
    return (
      <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-green-600 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading tax intelligence...</p>
          </div>
        </div>
      </div>
    );
  }

  // ============================================
  // SUBSCRIPTION PROMPT
  // ============================================

  if (authChecked && !state.subscription) {
    console.log('🔄 Showing subscription plans');
    
    return (
      <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <Sidebar />
        <div className="flex-1 overflow-y-auto p-6 pt-20 lg:pt-6">
          <div className="max-w-6xl mx-auto">
            <h1 className="text-3xl font-bold text-white mb-2">Choose Your Plan</h1>
            <p className="text-gray-400 mb-8">Get audit-ready and unlock tax exemptions with Nigeria Tax Act 2025</p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                {
                  id: 'PLN_yp8p5obbu6azilo',
                  name: 'Compliance Essentials',
                  price: 900000,
                  jobToBeDone: 'Get my books audit-ready',
                  deliverables: [
                    'Clean bookkeeping records (trial balance)',
                    'Draft audited accounts prepared',
                    'Tax exemption analysis + savings report',
                    'Tax returns prepared & filed (CIT, VAT, WHT)'
                  ],
                  outcome: 'Your business passes due diligence. Books are clean enough for compliance.',
                  bestFor: 'Startups & micro businesses needing organized records for compliance'
                },
                {
                  id: 'PLN_e23vyyhc2xjg6b5',
                  name: 'Audit-Ready Business',
                  price: 1800000,
                  popular: true,
                  jobToBeDone: 'Pass statutory audit, file taxes correctly',
                  deliverables: [
                    'Full statutory audit (audited financial statements)',
                    'Tax returns prepared & filed (CIT, VAT, WHT)',
                    'CAC full compliance (CO2, CO7, annual returns)',
                    'Tax optimization report (maximize exemptions)',
                    'Auditor opinion letter for banks/investors'
                  ],
                  outcome: "You're fully compliant. No NRS penalties. Investors trust your numbers.",
                  bestFor: 'SMEs seeking bank loans or investor funding'
                },
                {
                  id: 'PLN_le0r9qjpjwe0dnk',
                  name: 'Tokenization-Ready',
                  price: 3600000,
                  jobToBeDone: 'Raise capital by tokenizing my business',
                  deliverables: [
                    'Full statutory audit + investor-grade statements',
                    'Tax returns filed + optimization strategy',
                    'Tokenization feasibility report',
                    'Investor data room (organized docs)',
                    'CFO advisory (quarterly strategy calls)'
                  ],
                  outcome: "You're capital-ready. Investors can verify your business is legitimate and scalable.",
                  bestFor: 'Growth businesses seeking serious capital (₦50M+)'
                }
              ].map((plan) => (
                <div
                  key={plan.id}
                  className={`bg-gradient-to-br from-gray-800/50 to-gray-900/50 border rounded-2xl p-6 relative ${
                    plan.popular ? 'border-blue-500/50' : 'border-gray-700/50'
                  }`}
                >
                  {plan.popular && (
                    <span className="absolute top-0 right-0 bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-bl-lg">
                      MOST POPULAR
                    </span>
                  )}

                  <div className="mb-6">
                    <h3 className="text-2xl font-bold text-white mb-2">{plan.name}</h3>
                    <p className="text-blue-400 text-sm italic">"{plan.jobToBeDone}"</p>
                  </div>

                  <div className="mb-6">
                    <div className="text-4xl font-bold text-white">
                      {formatCurrency(plan.price)}
                    </div>
                    <div className="text-sm text-gray-400 mt-1">
                      Annual subscription • One-time payment
                    </div>
                  </div>

                  <div className="mb-6">
                    <h4 className="text-sm font-semibold text-gray-400 uppercase mb-3">What You Get:</h4>
                    <ul className="space-y-2">
                      {plan.deliverables.map((item, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm text-gray-300">
                          <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="mb-6 p-4 bg-green-900/20 border border-green-500/30 rounded-lg">
                    <h4 className="text-xs font-semibold text-green-400 uppercase mb-1">Outcome:</h4>
                    <p className="text-sm text-gray-300">{plan.outcome}</p>
                  </div>

                  <div className="mb-6 text-xs text-gray-500">
                    <strong>Best for:</strong> {plan.bestFor}
                  </div>

                  <button
                    onClick={async () => {
                      try {
                        const res = await apiClient.post('/api/v1/subscriptions/initialize', { plan_code: plan.id });
                        if (res.data.success && res.data.payment_link) {
                          window.location.href = res.data.payment_link;
                        } else {
                          toast.error('Failed to initialize subscription');
                        }
                      } catch (error) {
                        toast.error('Subscription failed');
                      }
                    }}
                    className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
                  >
                    Get Started
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ============================================
  // MAIN UI
  // ============================================

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-3">
                  <Receipt className="h-8 w-8 text-green-400" />
                  <span>Tax Intelligence Hub</span>
                </h1>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded-full flex items-center gap-1">
                    <BookOpen className="h-3 w-3" />
                    {state.taxData.legislationVersion}
                  </span>
                  <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full flex items-center gap-1">
                    <Shield className="h-3 w-3" />
                    Audit-Ready
                  </span>
                </div>
              </div>
              <p className="text-gray-400">Compliance • Tax Calculations • Audit Profile Management</p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-blue-400 px-3 py-1.5 bg-blue-500/10 rounded-full">
                🔄 Sync: {new Date(lastSyncTime).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
              </span>
              <button
                onClick={handleRefresh}
                disabled={state.refreshing}
                className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${state.refreshing ? 'animate-spin' : ''}`} />
                <span className="hidden sm:inline">{state.refreshing ? 'Syncing...' : 'Sync Now'}</span>
              </button>
            </div>
          </div>

          {/* ✅ UPDATED: Stats Cards - 3 cards instead of 4 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <StatCard
              title="Tax Liability"
              value={formatCurrency(state.taxData?.currentLiability || 0)}
              subtitle={`${Math.round(state.taxData.confidenceScore * 100)}% confidence`}
              icon={<DollarSign className="h-6 w-6 text-red-400" />}
              gradient="from-red-900/20 to-orange-900/20"
              border="border-red-500/30"
            />

            <StatCard
              title="Tax Savings"
              value={formatCurrency((state.taxData?.exemptions || []).reduce((sum, e) => sum + (e.estimated_savings || 0), 0))}
              subtitle={`${(state.taxData?.exemptions || []).length} exemptions`}
              icon={<TrendingUp className="h-6 w-6 text-green-400" />}
              gradient="from-green-900/20 to-emerald-900/20"
              border="border-green-500/30"
            />

            <StatCard
              title="Audit Documents"
              value={state.metrics?.documents_count.toString() || '0'}
              subtitle="Uploaded & synced"
              icon={<FileText className="h-6 w-6 text-yellow-400" />}
              gradient="from-yellow-900/20 to-amber-900/20"
              border="border-yellow-500/30"
            />
          </div>

          {/* Sync Status Alert */}
          {state.systemStatus.consistent === false && (
            <div className="mb-6 p-4 bg-red-900/20 border border-red-500/30 rounded-xl">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-red-400" />
                <div>
                  <h4 className="text-red-400 font-semibold">Sync Issue Detected</h4>
                  <p className="text-sm text-gray-400">Documents and compliance score are out of sync. Click "Sync Now" to resolve.</p>
                </div>
              </div>
            </div>
          )}

          {/* Risk & Recommendations Alerts */}
          {((state.taxData?.riskFlags || []).length > 0 || (state.taxData?.recommendations || []).length > 0) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              {(state.taxData?.riskFlags || []).length > 0 && (
                <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle className="h-5 w-5 text-red-400" />
                    <h3 className="text-red-400 font-semibold">Risk Flags</h3>
                  </div>
                  <ul className="space-y-2">
                    {(state.taxData?.riskFlags || []).map((risk, idx) => (
                      <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                        <span className="text-red-400">•</span>
                        <span>{risk}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {(state.taxData?.recommendations || []).length > 0 && (
                <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Lightbulb className="h-5 w-5 text-green-400" />
                    <h3 className="text-green-400 font-semibold">Recommendations</h3>
                  </div>
                  <ul className="space-y-2">
                    {(state.taxData?.recommendations || []).map((rec, idx) => (
                      <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                        <span className="text-green-400">•</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Tabs */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            {[
              { id: 'overview', label: 'Overview', icon: <BarChart2 className="h-4 w-4" /> },
              { id: 'calculator', label: 'Tax Calculator', icon: <Calculator className="h-4 w-4" /> },
              { id: 'exemptions', label: 'Exemptions', icon: <TrendingUp className="h-4 w-4" /> },
              { id: 'deadlines', label: 'Deadlines', icon: <Clock className="h-4 w-4" /> },
              { id: 'audit-profile', label: 'Audit Profile', icon: <FileText className="h-4 w-4" /> },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-all ${
                  activeTab === tab.id
                    ? 'bg-green-600 text-white shadow-lg scale-105'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {tab.id === 'calculator' && (
                  <Scale className="h-3 w-3 text-blue-300" />
                )}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="mb-20">
            {activeTab === 'overview' && <OverviewTab state={state} formatCurrency={formatCurrency} />}
            {activeTab === 'calculator' && (
              <TaxCalculatorTab 
                formatCurrency={formatCurrency} 
                onCalculationComplete={updateTaxDataFromCalculator}
                currentTaxData={state.taxData}
              />
            )}
            {activeTab === 'exemptions' && <ExemptionsTab exemptions={state.taxData.exemptions} formatCurrency={formatCurrency} />}
            {activeTab === 'audit-profile' && (
              <AuditProfileTab 
                documents={state.documents} 
                onRefresh={handleRefresh}
                onDocumentsUpdate={handleDocumentsUpdate}
              />
            )}
            {activeTab === 'deadlines' && (
              <div className="space-y-6" id="deadlines-section">
                <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
                  <h3 className="text-lg font-bold text-white mb-4">Tax Deadlines</h3>
                  <p className="text-gray-400 mb-6">Upcoming tax filing and payment deadlines</p>
                  
                  <div className="space-y-3">
                    {state.taxData.deadlines.length === 0 ? (
                      <div className="text-center py-8">
                        <Clock className="h-12 w-12 text-gray-600 mx-auto mb-4" />
                        <p className="text-gray-400">No upcoming deadlines</p>
                      </div>
                    ) : (
                      state.taxData.deadlines.map((deadline: any) => (
                        <div key={deadline.id} className="p-4 bg-gray-900/50 rounded-lg">
                          <div className="flex justify-between items-start">
                            <div>
                              <h4 className="text-white font-medium">{deadline.deadline_name}</h4>
                              <p className="text-sm text-gray-400 mt-1">{deadline.description}</p>
                              <div className="flex items-center gap-2 mt-2">
                                <Clock className="h-3 w-3 text-yellow-400" />
                                <span className="text-xs text-yellow-400">
                                  Due: {new Date(deadline.deadline_date).toLocaleDateString()}
                                </span>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-red-400 font-semibold">
                                {formatCurrency(deadline.penalty_amount)}
                              </div>
                              <div className="text-xs text-gray-500">Late penalty</div>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CompliancePage;