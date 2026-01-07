// File: frontend/src/pages/BookkeepingPage.tsx
// 📊 Automated Bookkeeping - Multi-Step Wizard

import React, { useState, useEffect } from 'react';
import {
  Upload,
  FileText,
  CheckCircle,
  Edit3,
  Download,
  ChevronRight,
  ChevronLeft,
  AlertCircle,
  Sparkles,
  BookOpen,
  TrendingUp,
  DollarSign,
  Trash2,
  Save,
  RefreshCw
} from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

// ============================================
// TYPE DEFINITIONS
// ============================================

interface Transaction {
  id?: string;
  transaction_date: string;
  description: string;
  reference: string;
  debit_amount: number;
  credit_amount: number;
  balance: number;
  account_code?: string;
  category?: string;
  confidence_score?: number;
  is_manually_categorized?: boolean;
}

interface BankStatement {
  id: string;
  file_name: string;
  bank_name?: string;
  account_number?: string;
  statement_period_start?: string;
  statement_period_end?: string;
  transaction_count: number;
  parsing_status: string;
  created_at: string;
}

interface TrialBalance {
  accounts: Array<{
    account_code: string;
    account_name: string;
    account_type: string;
    debits: number;
    credits: number;
    balance: number;
  }>;
  total_debits: number;
  total_credits: number;
  is_balanced: boolean;
  period_start: string;
  period_end: string;
}

type WizardStep = 'upload' | 'review' | 'categorize' | 'report';

// ============================================
// MAIN COMPONENT
// ============================================

const BookkeepingPage = () => {
  const [currentStep, setCurrentStep] = useState<WizardStep>('upload');
  const [loading, setLoading] = useState(false);
  
  // Step 1: Upload
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<any>(null);
  
  // Step 2: Review Transactions
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [editingTransaction, setEditingTransaction] = useState<string | null>(null);
  
  // Step 3: Categorization
  const [categorizationComplete, setCategorizationComplete] = useState(false);
  const [categorizationMethod, setCategorizationMethod] = useState<'ai' | 'rules'>('ai');
  
  // Step 4: Trial Balance
  const [trialBalance, setTrialBalance] = useState<TrialBalance | null>(null);
  const [generatingReport, setGeneratingReport] = useState(false);

  // ============================================
  // STEP 1: FILE UPLOAD
  // ============================================

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['csv', 'xlsx', 'xls', 'pdf'];
    const fileExt = file.name.split('.').pop()?.toLowerCase();
    
    if (!fileExt || !allowedTypes.includes(fileExt)) {
      toast.error('Invalid file type. Use CSV, Excel, or PDF');
      return;
    }

    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File size exceeds 10MB limit');
      return;
    }

    setUploadedFile(file);
  };

  const uploadStatement = async () => {
    if (!uploadedFile) return;

    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('file', uploadedFile);

      const response = await apiClient.post(
        '/api/v1/bookkeeping/upload-statement',
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );

      if (response.data.success) {
        setUploadResult(response.data);
        
        // Fetch transactions for review
        await fetchTransactions(response.data.statement_id);
        
        toast.success(`✅ Parsed ${response.data.transaction_count} transactions`);
        setCurrentStep('review');
      } else {
        toast.error('Upload failed');
      }
    } catch (error: any) {
      console.error('Upload error:', error);
      toast.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  // ============================================
  // STEP 2: FETCH & REVIEW TRANSACTIONS
  // ============================================

  const fetchTransactions = async (statementId: string) => {
    try {
      const response = await apiClient.get(
        `/api/v1/bookkeeping/statements/${statementId}/transactions`
      );

      if (response.data.success) {
        setTransactions(response.data.transactions);
      }
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
      toast.error('Failed to load transactions');
    }
  };

  const updateTransaction = async (
    transactionId: string,
    accountCode: string,
    category: string
  ) => {
    try {
      const response = await apiClient.put(
        '/api/v1/bookkeeping/transactions/update',
        {
          transaction_id: transactionId,
          account_code: accountCode,
          category: category
        }
      );

      if (response.data.success) {
        // Update local state
        setTransactions(prev =>
          prev.map(t =>
            t.id === transactionId
              ? { ...t, account_code: accountCode, category: category, is_manually_categorized: true }
              : t
          )
        );
        
        toast.success('Transaction updated');
        setEditingTransaction(null);
      }
    } catch (error) {
      console.error('Update failed:', error);
      toast.error('Failed to update transaction');
    }
  };

  // ============================================
  // STEP 3: CATEGORIZATION
  // ============================================

  const categorizeTransactions = async () => {
    if (!uploadResult?.statement_id) return;

    try {
      setLoading(true);
      const response = await apiClient.post(
        '/api/v1/bookkeeping/categorize-transactions',
        {
          statement_id: uploadResult.statement_id,
          use_ai: categorizationMethod === 'ai'
        }
      );

      if (response.data.success) {
        // Refresh transactions to show categorization
        await fetchTransactions(uploadResult.statement_id);
        
        setCategorizationComplete(true);
        toast.success(`✅ ${response.data.categorized_count} transactions categorized`);
        setCurrentStep('report');
      }
    } catch (error: any) {
      console.error('Categorization error:', error);
      toast.error(error.response?.data?.detail || 'Categorization failed');
    } finally {
      setLoading(false);
    }
  };

  // ============================================
  // STEP 4: GENERATE TRIAL BALANCE
  // ============================================

  const generateTrialBalance = async () => {
    if (!uploadResult?.metadata) return;

    try {
      setGeneratingReport(true);
      
      const response = await apiClient.post(
        '/api/v1/bookkeeping/trial-balance/generate',
        {
          period_start: uploadResult.metadata.period_start,
          period_end: uploadResult.metadata.period_end,
          save_report: true
        }
      );

      if (response.data.success) {
        setTrialBalance(response.data.trial_balance);
        toast.success('✅ Trial balance generated');
      }
    } catch (error: any) {
      console.error('Trial balance error:', error);
      toast.error(error.response?.data?.detail || 'Report generation failed');
    } finally {
      setGeneratingReport(false);
    }
  };

  const downloadTrialBalance = async () => {
    if (!trialBalance) return;

    try {
      const response = await apiClient.post(
        '/api/v1/bookkeeping/trial-balance/export',
        {
          period_start: trialBalance.period_start,
          period_end: trialBalance.period_end,
          company_name: 'Your Company'
        },
        {
          responseType: 'blob'
        }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `trial_balance_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('📥 Trial balance downloaded');
    } catch (error) {
      console.error('Download error:', error);
      toast.error('Download failed');
    }
  };

  // ============================================
  // WIZARD NAVIGATION
  // ============================================

  const steps = [
    { id: 'upload', label: 'Upload Statement', icon: <Upload className="h-5 w-5" /> },
    { id: 'review', label: 'Review Transactions', icon: <FileText className="h-5 w-5" /> },
    { id: 'categorize', label: 'Categorize', icon: <Sparkles className="h-5 w-5" /> },
    { id: 'report', label: 'Generate Report', icon: <BookOpen className="h-5 w-5" /> }
  ];

  const currentStepIndex = steps.findIndex(s => s.id === currentStep);

  const canProceed = () => {
    switch (currentStep) {
      case 'upload':
        return uploadedFile !== null;
      case 'review':
        return transactions.length > 0;
      case 'categorize':
        return categorizationComplete;
      case 'report':
        return trialBalance !== null;
      default:
        return false;
    }
  };

  const nextStep = () => {
    if (currentStep === 'upload' && uploadedFile) {
      uploadStatement();
    } else if (currentStep === 'review') {
      setCurrentStep('categorize');
    } else if (currentStep === 'categorize' && !categorizationComplete) {
      categorizeTransactions();
    } else if (currentStep === 'categorize' && categorizationComplete) {
      setCurrentStep('report');
    }
  };

  const prevStep = () => {
    const stepOrder: WizardStep[] = ['upload', 'review', 'categorize', 'report'];
    const currentIndex = stepOrder.indexOf(currentStep);
    if (currentIndex > 0) {
      setCurrentStep(stepOrder[currentIndex - 1]);
    }
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 0
    }).format(amount);
  };

  // ============================================
  // RENDER
  // ============================================

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-2xl md:text-3xl font-bold text-white mb-2 flex items-center gap-3">
              <BookOpen className="h-8 w-8 text-green-400" />
              Automated Bookkeeping
            </h1>
            <p className="text-gray-400">Upload bank statements → Auto-categorize → Generate trial balance</p>
          </div>

          {/* Progress Stepper */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6 mb-6">
            <div className="flex items-center justify-between">
              {steps.map((step, index) => (
                <React.Fragment key={step.id}>
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-12 h-12 rounded-full flex items-center justify-center mb-2 transition-all ${
                        index <= currentStepIndex
                          ? 'bg-green-600 text-white'
                          : 'bg-gray-700 text-gray-400'
                      }`}
                    >
                      {step.icon}
                    </div>
                    <span
                      className={`text-sm font-medium ${
                        index <= currentStepIndex ? 'text-white' : 'text-gray-500'
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                  
                  {index < steps.length - 1 && (
                    <div
                      className={`flex-1 h-1 mx-4 transition-all ${
                        index < currentStepIndex ? 'bg-green-600' : 'bg-gray-700'
                      }`}
                    />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Step Content */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6 min-h-[400px]">
            {currentStep === 'upload' && (
              <UploadStep
                uploadedFile={uploadedFile}
                onFileSelect={handleFileUpload}
                loading={loading}
              />
            )}

            {currentStep === 'review' && (
              <ReviewStep
                transactions={transactions}
                editingTransaction={editingTransaction}
                onEdit={setEditingTransaction}
                onUpdate={updateTransaction}
                formatCurrency={formatCurrency}
              />
            )}

            {currentStep === 'categorize' && (
              <CategorizeStep
                transactions={transactions}
                categorizationMethod={categorizationMethod}
                onMethodChange={setCategorizationMethod}
                categorizationComplete={categorizationComplete}
                loading={loading}
              />
            )}

            {currentStep === 'report' && (
              <ReportStep
                trialBalance={trialBalance}
                generatingReport={generatingReport}
                onGenerate={generateTrialBalance}
                onDownload={downloadTrialBalance}
                formatCurrency={formatCurrency}
              />
            )}
          </div>

          {/* Navigation Buttons */}
          <div className="flex justify-between mt-6">
            <button
              onClick={prevStep}
              disabled={currentStep === 'upload'}
              className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <ChevronLeft className="h-5 w-5" />
              Back
            </button>

            {currentStep !== 'report' && (
              <button
                onClick={nextStep}
                disabled={!canProceed() || loading}
                className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    Processing...
                  </>
                ) : (
                  <>
                    {currentStep === 'upload' && 'Upload & Parse'}
                    {currentStep === 'review' && 'Continue'}
                    {currentStep === 'categorize' && !categorizationComplete && 'Categorize Transactions'}
                    {currentStep === 'categorize' && categorizationComplete && 'Continue'}
                    <ChevronRight className="h-5 w-5" />
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================
// STEP COMPONENTS
// ============================================

const UploadStep = ({ uploadedFile, onFileSelect, loading }: any) => (
  <div className="text-center py-12">
    <Upload className="h-16 w-16 text-green-400 mx-auto mb-6" />
    <h2 className="text-2xl font-bold text-white mb-4">Upload Bank Statement</h2>
    <p className="text-gray-400 mb-8">
      Supports CSV, Excel (XLSX/XLS), and PDF formats
    </p>

    {uploadedFile ? (
      <div className="mb-6 p-4 bg-green-900/20 border border-green-500/30 rounded-lg inline-block">
        <FileText className="h-8 w-8 text-green-400 mx-auto mb-2" />
        <p className="text-white font-medium">{uploadedFile.name}</p>
        <p className="text-sm text-gray-400">{(uploadedFile.size / 1024).toFixed(2)} KB</p>
      </div>
    ) : (
      <label className="inline-block cursor-pointer">
        <div className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors">
          Choose File
        </div>
        <input
          type="file"
          onChange={onFileSelect}
          accept=".csv,.xlsx,.xls,.pdf"
          className="hidden"
          disabled={loading}
        />
      </label>
    )}

    <div className="mt-8 text-left max-w-md mx-auto">
      <h3 className="text-white font-semibold mb-3">✅ What happens next:</h3>
      <ul className="space-y-2 text-gray-400 text-sm">
        <li className="flex items-start gap-2">
          <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
          <span>Extracts transactions (date, description, amounts)</span>
        </li>
        <li className="flex items-start gap-2">
          <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
          <span>Identifies account details and period</span>
        </li>
        <li className="flex items-start gap-2">
          <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
          <span>Prepares for AI categorization</span>
        </li>
      </ul>
    </div>
  </div>
);

const ReviewStep = ({ transactions, editingTransaction, onEdit, onUpdate, formatCurrency }: any) => (
  <div>
    <div className="mb-6">
      <h2 className="text-2xl font-bold text-white mb-2">Review Transactions</h2>
      <p className="text-gray-400">
        {transactions.length} transactions parsed. Review and edit if needed.
      </p>
    </div>

    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-700">
            <th className="text-left py-3 px-4 text-gray-400 font-medium">Date</th>
            <th className="text-left py-3 px-4 text-gray-400 font-medium">Description</th>
            <th className="text-right py-3 px-4 text-gray-400 font-medium">Debit</th>
            <th className="text-right py-3 px-4 text-gray-400 font-medium">Credit</th>
            <th className="text-right py-3 px-4 text-gray-400 font-medium">Balance</th>
            <th className="text-center py-3 px-4 text-gray-400 font-medium">Action</th>
          </tr>
        </thead>
        <tbody>
          {transactions.slice(0, 20).map((trans: Transaction) => (
            <tr key={trans.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
              <td className="py-3 px-4 text-gray-300">{trans.transaction_date}</td>
              <td className="py-3 px-4 text-white">{trans.description}</td>
              <td className="py-3 px-4 text-right text-red-400">
                {trans.debit_amount > 0 ? formatCurrency(trans.debit_amount) : '-'}
              </td>
              <td className="py-3 px-4 text-right text-green-400">
                {trans.credit_amount > 0 ? formatCurrency(trans.credit_amount) : '-'}
              </td>
              <td className="py-3 px-4 text-right text-white">
                {formatCurrency(trans.balance)}
              </td>
              <td className="py-3 px-4 text-center">
                <button
                  onClick={() => onEdit(trans.id)}
                  className="text-blue-400 hover:text-blue-300"
                >
                  <Edit3 className="h-4 w-4" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    {transactions.length > 20 && (
      <p className="text-center text-gray-400 text-sm mt-4">
        Showing first 20 transactions. All {transactions.length} will be processed.
      </p>
    )}
  </div>
);

const CategorizeStep = ({ 
  transactions, 
  categorizationMethod, 
  onMethodChange, 
  categorizationComplete,
  loading 
}: any) => {
  const uncategorized = transactions.filter((t: Transaction) => !t.account_code).length;
  const categorized = transactions.length - uncategorized;

  return (
    <div className="py-8">
      <div className="text-center mb-8">
        <Sparkles className="h-16 w-16 text-green-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-white mb-2">Categorize Transactions</h2>
        <p className="text-gray-400">
          {categorizationComplete 
            ? `✅ ${categorized} transactions categorized`
            : `Choose categorization method for ${transactions.length} transactions`
          }
        </p>
      </div>

      {!categorizationComplete && (
        <div className="max-w-2xl mx-auto space-y-4">
          <div
            onClick={() => onMethodChange('ai')}
            className={`p-6 rounded-xl cursor-pointer transition-all ${
              categorizationMethod === 'ai'
                ? 'bg-green-900/20 border-2 border-green-500'
                : 'bg-gray-700/50 border-2 border-gray-600 hover:border-gray-500'
            }`}
          >
            <div className="flex items-start gap-4">
              <input
                type="radio"
                checked={categorizationMethod === 'ai'}
                onChange={() => onMethodChange('ai')}
                className="mt-1"
              />
              <div>
                <h3 className="text-white font-semibold text-lg mb-2">🤖 AI-Powered (Recommended)</h3>
                <p className="text-gray-400 text-sm mb-3">
                  Uses Claude AI to intelligently categorize transactions based on Nigerian accounting standards
                </p>
                <div className="flex items-center gap-2 text-sm text-green-400">
                  <CheckCircle className="h-4 w-4" />
                  <span>95%+ accuracy</span>
                </div>
              </div>
            </div>
          </div>

          <div
            onClick={() => onMethodChange('rules')}
            className={`p-6 rounded-xl cursor-pointer transition-all ${
              categorizationMethod === 'rules'
                ? 'bg-green-900/20 border-2 border-green-500'
                : 'bg-gray-700/50 border-2 border-gray-600 hover:border-gray-500'
            }`}
          >
            <div className="flex items-start gap-4">
              <input
                type="radio"
                checked={categorizationMethod === 'rules'}
                onChange={() => onMethodChange('rules')}
                className="mt-1"
              />
              <div>
                <h3 className="text-white font-semibold text-lg mb-2">📋 Rule-Based</h3>
                <p className="text-gray-400 text-sm mb-3">
                  Uses keyword matching and predefined rules for categorization
                </p>
                <div className="flex items-center gap-2 text-sm text-yellow-400">
                  <AlertCircle className="h-4 w-4" />
                  <span>80%+ accuracy</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {categorizationComplete && (
        <div className="max-w-md mx-auto mt-8">
          <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-6 text-center">
            <CheckCircle className="h-12 w-12 text-green-400 mx-auto mb-4" />
            <h3 className="text-white font-semibold text-lg mb-2">Categorization Complete!</h3>
            <p className="text-gray-400 text-sm">
              {categorized} transactions have been categorized and are ready for trial balance generation
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

const ReportStep = ({ 
  trialBalance, 
  generatingReport, 
  onGenerate, 
  onDownload, 
  formatCurrency 
}: any) => (
  <div>
    <div className="mb-6">
      <h2 className="text-2xl font-bold text-white mb-2">Trial Balance Report</h2>
      <p className="text-gray-400">
        Generate and download your trial balance in Excel format
      </p>
    </div>

    {!trialBalance ? (
      <div className="text-center py-12">
        <BookOpen className="h-16 w-16 text-blue-400 mx-auto mb-6" />
        <button
          onClick={onGenerate}
          disabled={generatingReport}
          className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2 mx-auto"
        >
          {generatingReport ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              Generating Report...
            </>
          ) : (
            <>
              <TrendingUp className="h-5 w-5" />
              Generate Trial Balance
            </>
          )}
        </button>
      </div>
    ) : (
      <div>
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-gradient-to-br from-blue-900/20 to-indigo-900/20 border border-blue-500/30 rounded-xl p-6">
            <DollarSign className="h-8 w-8 text-blue-400 mb-3" />
            <div className="text-sm text-gray-400 mb-1">Total Debits</div>
            <div className="text-2xl font-bold text-white">
              {formatCurrency(trialBalance.total_debits)}
            </div>
          </div>

          <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-6">
            <DollarSign className="h-8 w-8 text-green-400 mb-3" />
            <div className="text-sm text-gray-400 mb-1">Total Credits</div>
            <div className="text-2xl font-bold text-white">
              {formatCurrency(trialBalance.total_credits)}
            </div>
          </div>

          <div className={`bg-gradient-to-br ${
            trialBalance.is_balanced 
              ? 'from-green-900/20 to-emerald-900/20 border-green-500/30' 
              : 'from-red-900/20 to-orange-900/20 border-red-500/30'
          } border rounded-xl p-6`}>
            <CheckCircle className={`h-8 w-8 ${
              trialBalance.is_balanced ? 'text-green-400' : 'text-red-400'
            } mb-3`} />
            <div className="text-sm text-gray-400 mb-1">Status</div>
            <div className={`text-2xl font-bold ${
              trialBalance.is_balanced ? 'text-green-400' : 'text-red-400'
            }`}>
              {trialBalance.is_balanced ? '✅ Balanced' : '⚠️ Not Balanced'}
            </div>
          </div>
        </div>

        {/* Accounts Table */}
        <div className="bg-gray-900/50 rounded-xl p-4 mb-6">
          <h3 className="text-white font-semibold mb-4">Account Breakdown</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Code</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Account</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Debits</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Credits</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Balance</th>
                </tr>
              </thead>
              <tbody>
                {trialBalance.accounts.map((account: any) => (
                  <tr key={account.account_code} className="border-b border-gray-700/50">
                    <td className="py-3 px-4 text-gray-300">{account.account_code}</td>
                    <td className="py-3 px-4 text-white">{account.account_name}</td>
                    <td className="py-3 px-4 text-right text-red-400">
                      {formatCurrency(account.debits)}
                    </td>
                    <td className="py-3 px-4 text-right text-green-400">
                      {formatCurrency(account.credits)}
                    </td>
                    <td className="py-3 px-4 text-right text-white">
                      {formatCurrency(account.balance)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Download Button */}
        <div className="text-center">
          <button
            onClick={onDownload}
            className="px-8 py-4 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors flex items-center gap-2 mx-auto"
          >
            <Download className="h-5 w-5" />
            Download Excel Report
          </button>
        </div>
      </div>
    )}
  </div>
);

export default BookkeepingPage;