// File: frontend/src/pages/BookkeepingPage.tsx
// 📊 Automated Bookkeeping - Mobile-Optimized Multi-Step Wizard

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
  RefreshCw,
  X
} from 'lucide-react';

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

  // Mock API client (replace with your actual apiClient)
  const apiClient = {
    post: async (url: string, data: any, config?: any) => {
      console.log('API POST:', url, data);
      return { data: { success: true, statement_id: 'mock-123', transaction_count: 50 } };
    },
    get: async (url: string) => {
      console.log('API GET:', url);
      return { data: { success: true, transactions: generateMockTransactions() } };
    },
    put: async (url: string, data: any) => {
      console.log('API PUT:', url, data);
      return { data: { success: true } };
    }
  };

  // Mock toast
  const toast = {
    success: (msg: string) => console.log('✅', msg),
    error: (msg: string) => console.error('❌', msg)
  };

  // ============================================
  // MOCK DATA GENERATOR
  // ============================================

  const generateMockTransactions = (): Transaction[] => {
    const descriptions = [
      'Online Purchase - Amazon',
      'Salary Payment',
      'Rent Payment',
      'Grocery Store',
      'Utility Bill - Electricity',
      'Restaurant - Dinner',
      'Gas Station',
      'Bank Fees',
      'Insurance Premium',
      'Mobile Recharge'
    ];

    return Array.from({ length: 25 }, (_, i) => ({
      id: `txn-${i + 1}`,
      transaction_date: new Date(2024, 0, i + 1).toISOString().split('T')[0],
      description: descriptions[i % descriptions.length],
      reference: `REF${1000 + i}`,
      debit_amount: i % 3 === 0 ? Math.floor(Math.random() * 50000) + 5000 : 0,
      credit_amount: i % 3 !== 0 ? Math.floor(Math.random() * 100000) + 10000 : 0,
      balance: 500000 + (i * 10000),
      account_code: i > 10 ? `${1000 + (i % 5)}` : undefined,
      category: i > 10 ? ['Operating Expenses', 'Revenue', 'Administrative'][i % 3] : undefined
    }));
  };

  // ============================================
  // STEP 1: FILE UPLOAD
  // ============================================

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ['csv', 'xlsx', 'xls', 'pdf'];
    const fileExt = file.name.split('.').pop()?.toLowerCase();
    
    if (!fileExt || !allowedTypes.includes(fileExt)) {
      toast.error('Invalid file type. Use CSV, Excel, or PDF');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      toast.error('File size exceeds 10MB limit');
      return;
    }

    setUploadedFile(file);
  };

  const uploadStatement = async () => {
    if (!uploadedFile) return;

    console.log('🔵 Starting upload process...');
    console.log('🔵 File object:', uploadedFile);
    console.log('🔵 File name:', uploadedFile.name);
    console.log('🔵 File size:', uploadedFile.size);
    console.log('🔵 File type:', uploadedFile.type);

    try {
        setLoading(true);
        
        // Create FormData
        const formData = new FormData();
        formData.append('file', uploadedFile);
        
        // Debug FormData contents
        console.log('🔵 FormData entries:');
        for (let [key, value] of formData.entries()) {
        console.log(`   ${key}:`, value);
        }
        
        console.log('🔵 Making API request to:', '/api/v1/bookkeeping/upload-statement');
        
        // Make request with explicit headers
        const response = await apiClient.post(
        '/api/v1/bookkeeping/upload-statement',
        formData,
        {
            headers: {
            'Content-Type': 'multipart/form-data',
            },
            // Add timeout
            timeout: 30000, // 30 seconds
        }
        );

        console.log('🔵 Raw response:', response);
        console.log('🔵 Response status:', response.status);
        console.log('🔵 Response headers:', response.headers);
        console.log('📤 Response data:', response.data);
        console.log('📤 Statement ID:', response.data.statement_id);
        console.log('📤 Transaction count:', response.data.transaction_count);
        console.log('📤 Parsing status:', response.data.parsing_status);
        
        // Check if response is mock
        if (response.data.statement_id === 'mock-123') {
        console.error('❌❌❌ MOCK DATA DETECTED! Backend not responding! ❌❌❌');
        toast.error('Backend is returning mock data. Check server logs.');
        return;
        }

        if (response.data.success) {
        setUploadResult(response.data);
        
        // Fetch transactions for review
        console.log('🔵 Fetching transactions for statement:', response.data.statement_id);
        await fetchTransactions(response.data.statement_id);
        
        toast.success(`✅ Parsed ${response.data.transaction_count} transactions`);
        setCurrentStep('review');
        } else {
        console.error('❌ Upload failed:', response.data);
        toast.error('Upload failed');
        }
    } catch (error: any) {
        console.error('❌❌❌ UPLOAD ERROR ❌❌❌');
        console.error('Error object:', error);
        console.error('Error message:', error.message);
        console.error('Error response:', error.response);
        console.error('Error response data:', error.response?.data);
        console.error('Error response status:', error.response?.status);
        
        toast.error(error.response?.data?.detail || error.message || 'Upload failed');
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
        { transaction_id: transactionId, account_code: accountCode, category: category }
      );

      if (response.data.success) {
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
        await fetchTransactions(uploadResult.statement_id);
        setCategorizationComplete(true);
        toast.success(`✅ Transactions categorized`);
        setCurrentStep('report');
      }
    } catch (error: any) {
      console.error('Categorization error:', error);
      toast.error('Categorization failed');
    } finally {
      setLoading(false);
    }
  };

  // ============================================
  // STEP 4: GENERATE TRIAL BALANCE
  // ============================================

  const generateTrialBalance = async () => {
    try {
      setGeneratingReport(true);
      
      const mockTrialBalance: TrialBalance = {
        accounts: [
          { account_code: '1000', account_name: 'Cash', account_type: 'Asset', debits: 500000, credits: 200000, balance: 300000 },
          { account_code: '1100', account_name: 'Accounts Receivable', account_type: 'Asset', debits: 300000, credits: 50000, balance: 250000 },
          { account_code: '4000', account_name: 'Sales Revenue', account_type: 'Revenue', debits: 0, credits: 800000, balance: -800000 },
          { account_code: '5000', account_name: 'Operating Expenses', account_type: 'Expense', debits: 250000, credits: 0, balance: 250000 }
        ],
        total_debits: 1050000,
        total_credits: 1050000,
        is_balanced: true,
        period_start: '2024-01-01',
        period_end: '2024-01-31'
      };

      setTimeout(() => {
        setTrialBalance(mockTrialBalance);
        toast.success('✅ Trial balance generated');
        setGeneratingReport(false);
      }, 1500);
    } catch (error: any) {
      console.error('Trial balance error:', error);
      toast.error('Report generation failed');
      setGeneratingReport(false);
    }
  };

  const downloadTrialBalance = async () => {
    if (!trialBalance) return;
    toast.success('📥 Download started (mock)');
  };

  // ============================================
  // WIZARD NAVIGATION
  // ============================================

  const steps = [
    { id: 'upload', label: 'Upload', icon: <Upload className="h-5 w-5" /> },
    { id: 'review', label: 'Review', icon: <FileText className="h-5 w-5" /> },
    { id: 'categorize', label: 'Categorize', icon: <Sparkles className="h-5 w-5" /> },
    { id: 'report', label: 'Report', icon: <BookOpen className="h-5 w-5" /> }
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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2 flex items-center gap-2 sm:gap-3">
            <BookOpen className="h-6 w-6 sm:h-8 sm:w-8 text-green-400" />
            <span className="leading-tight">Automated Bookkeeping</span>
          </h1>
          <p className="text-sm sm:text-base text-gray-400">
            Upload → Review → Categorize → Report
          </p>
        </div>

        {/* Progress Stepper - Mobile Optimized */}
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4 sm:p-6 mb-6 sm:mb-8">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <React.Fragment key={step.id}>
                <div className="flex flex-col items-center">
                  <div
                    className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center mb-2 transition-all ${
                      index <= currentStepIndex
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-700 text-gray-400'
                    }`}
                  >
                    {step.icon}
                  </div>
                  {/* Hide labels on mobile, show on sm+ */}
                  <span
                    className={`hidden sm:block text-xs sm:text-sm font-medium text-center ${
                      index <= currentStepIndex ? 'text-white' : 'text-gray-500'
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
                
                {index < steps.length - 1 && (
                  <div
                    className={`flex-1 h-1 mx-2 sm:mx-4 transition-all ${
                      index < currentStepIndex ? 'bg-green-600' : 'bg-gray-700'
                    }`}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4 sm:p-6 min-h-[400px]">
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

        {/* Navigation Buttons - Mobile Optimized */}
        <div className="flex gap-3 sm:gap-4 mt-6">
          <button
            onClick={prevStep}
            disabled={currentStep === 'upload'}
            className="flex-1 sm:flex-none sm:px-6 py-3 sm:py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 min-h-[44px] text-sm sm:text-base"
          >
            <ChevronLeft className="h-4 w-4 sm:h-5 sm:w-5" />
            <span>Back</span>
          </button>

          {currentStep !== 'report' && (
            <button
              onClick={nextStep}
              disabled={!canProceed() || loading}
              className="flex-1 sm:flex-none sm:px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 min-h-[44px] text-sm sm:text-base font-medium"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 sm:h-5 sm:w-5 border-b-2 border-white"></div>
                  <span className="hidden sm:inline">Processing...</span>
                  <span className="sm:hidden">...</span>
                </>
              ) : (
                <>
                  <span>
                    {currentStep === 'upload' && 'Upload'}
                    {currentStep === 'review' && 'Continue'}
                    {currentStep === 'categorize' && !categorizationComplete && 'Categorize'}
                    {currentStep === 'categorize' && categorizationComplete && 'Continue'}
                  </span>
                  <ChevronRight className="h-4 w-4 sm:h-5 sm:w-5" />
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================
// STEP COMPONENTS - MOBILE OPTIMIZED
// ============================================

const UploadStep = ({ uploadedFile, onFileSelect, loading }: any) => (
  <div className="text-center py-8 sm:py-12">
    <Upload className="h-12 w-12 sm:h-16 sm:w-16 text-green-400 mx-auto mb-4 sm:mb-6" />
    <h2 className="text-xl sm:text-2xl font-bold text-white mb-3 sm:mb-4 px-4">Upload Bank Statement</h2>
    <p className="text-sm sm:text-base text-gray-400 mb-6 sm:mb-8 px-4">
      Supports CSV, Excel (XLSX/XLS), and PDF formats
    </p>

    {uploadedFile ? (
      <div className="mb-6 p-4 bg-green-900/20 border border-green-500/30 rounded-lg inline-block max-w-full mx-4">
        <FileText className="h-6 w-6 sm:h-8 sm:w-8 text-green-400 mx-auto mb-2" />
        <p className="text-white font-medium text-sm sm:text-base break-all">{uploadedFile.name}</p>
        <p className="text-xs sm:text-sm text-gray-400">{(uploadedFile.size / 1024).toFixed(2)} KB</p>
      </div>
    ) : (
      <label className="inline-block cursor-pointer px-4">
        <div className="px-6 sm:px-8 py-3 sm:py-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors min-h-[44px] flex items-center justify-center text-sm sm:text-base">
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

    <div className="mt-8 text-left max-w-md mx-auto px-4">
      <h3 className="text-white font-semibold mb-3 text-sm sm:text-base">✅ What happens next:</h3>
      <ul className="space-y-2 text-gray-400 text-xs sm:text-sm">
        <li className="flex items-start gap-2">
          <CheckCircle className="h-4 w-4 sm:h-5 sm:w-5 text-green-400 flex-shrink-0 mt-0.5" />
          <span>Extracts transactions (date, description, amounts)</span>
        </li>
        <li className="flex items-start gap-2">
          <CheckCircle className="h-4 w-4 sm:h-5 sm:w-5 text-green-400 flex-shrink-0 mt-0.5" />
          <span>Identifies account details and period</span>
        </li>
        <li className="flex items-start gap-2">
          <CheckCircle className="h-4 w-4 sm:h-5 sm:w-5 text-green-400 flex-shrink-0 mt-0.5" />
          <span>Prepares for AI categorization</span>
        </li>
      </ul>
    </div>
  </div>
);

const ReviewStep = ({ transactions, editingTransaction, onEdit, onUpdate, formatCurrency }: any) => {
  const [isMobile, setIsMobile] = useState(false);

  React.useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  return (
    <div>
      <div className="mb-4 sm:mb-6">
        <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">Review Transactions</h2>
        <p className="text-sm sm:text-base text-gray-400">
          {transactions.length} transactions parsed. Review and edit if needed.
        </p>
      </div>

      {/* Mobile: Card View */}
      {isMobile ? (
        <div className="space-y-3">
          {transactions.slice(0, 20).map((trans: Transaction) => (
            <div key={trans.id} className="bg-gray-700/30 border border-gray-600/50 rounded-lg p-4">
              <div className="flex justify-between items-start mb-2">
                <div className="flex-1">
                  <p className="text-white font-medium text-sm mb-1">{trans.description}</p>
                  <p className="text-gray-400 text-xs">{trans.transaction_date}</p>
                </div>
                <button
                  onClick={() => onEdit(trans.id)}
                  className="text-blue-400 hover:text-blue-300 p-2"
                >
                  <Edit3 className="h-4 w-4" />
                </button>
              </div>
              
              <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                <div>
                  <span className="text-gray-400">Debit:</span>
                  <p className="text-red-400 font-medium">
                    {trans.debit_amount > 0 ? formatCurrency(trans.debit_amount) : '-'}
                  </p>
                </div>
                <div>
                  <span className="text-gray-400">Credit:</span>
                  <p className="text-green-400 font-medium">
                    {trans.credit_amount > 0 ? formatCurrency(trans.credit_amount) : '-'}
                  </p>
                </div>
              </div>
              
              <div className="mt-2 pt-2 border-t border-gray-600">
                <span className="text-gray-400 text-xs">Balance: </span>
                <span className="text-white font-medium text-sm">{formatCurrency(trans.balance)}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Desktop: Table View */
        <div className="overflow-x-auto -mx-6 px-6">
          <table className="w-full min-w-[700px]">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 px-4 text-gray-400 font-medium text-sm">Date</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium text-sm">Description</th>
                <th className="text-right py-3 px-4 text-gray-400 font-medium text-sm">Debit</th>
                <th className="text-right py-3 px-4 text-gray-400 font-medium text-sm">Credit</th>
                <th className="text-right py-3 px-4 text-gray-400 font-medium text-sm">Balance</th>
                <th className="text-center py-3 px-4 text-gray-400 font-medium text-sm">Action</th>
              </tr>
            </thead>
            <tbody>
              {transactions.slice(0, 20).map((trans: Transaction) => (
                <tr key={trans.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                  <td className="py-3 px-4 text-gray-300 text-sm">{trans.transaction_date}</td>
                  <td className="py-3 px-4 text-white text-sm">{trans.description}</td>
                  <td className="py-3 px-4 text-right text-red-400 text-sm">
                    {trans.debit_amount > 0 ? formatCurrency(trans.debit_amount) : '-'}
                  </td>
                  <td className="py-3 px-4 text-right text-green-400 text-sm">
                    {trans.credit_amount > 0 ? formatCurrency(trans.credit_amount) : '-'}
                  </td>
                  <td className="py-3 px-4 text-right text-white text-sm">
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
      )}

      {transactions.length > 20 && (
        <p className="text-center text-gray-400 text-xs sm:text-sm mt-4">
          Showing first 20 transactions. All {transactions.length} will be processed.
        </p>
      )}
    </div>
  );
};

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
            ? `✅ ${categorized} of ${transactions.length} transactions categorized`
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
                <h3 className="text-white font-semibold text-lg mb-2">🤖 AI-Powered (Groq - FREE)</h3>
                <p className="text-gray-400 text-sm mb-3">
                  Uses Groq AI (free, lightning fast) to intelligently categorize transactions based on Nigerian accounting standards
                </p>
                <div className="flex items-center gap-2 text-sm text-green-400">
                  <CheckCircle className="h-4 w-4" />
                  <span>95%+ accuracy • FREE • 50x faster than GPT-4</span>
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
                  Uses keyword matching and predefined rules for categorization (no API needed)
                </p>
                <div className="flex items-center gap-2 text-sm text-yellow-400">
                  <AlertCircle className="h-4 w-4" />
                  <span>80%+ accuracy • Works offline</span>
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
            <h3 className="text-white font-semibold text-lg mb-2">✅ Categorization Complete!</h3>
            <p className="text-gray-400 text-sm mb-4">
              {categorized} of {transactions.length} transactions have been categorized
            </p>
            
            {/* 🚨 NEW: Preview of categorized transactions */}
            <div className="mt-6 space-y-2 max-h-60 overflow-y-auto">
              <h4 className="text-sm font-semibold text-gray-300 mb-3">Sample Categorizations:</h4>
              {transactions.slice(0, 5).map((trans: Transaction, idx: number) => (
                trans.account_code && (
                  <div key={idx} className="bg-gray-800/50 rounded p-3 text-left">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <p className="text-white text-sm truncate">{trans.description}</p>
                        <p className="text-xs text-gray-400 mt-1">
                          {trans.category} ({trans.account_code})
                        </p>
                      </div>
                      <span className="text-xs text-green-400 ml-2">
                        {Math.round((trans.confidence_score || 0) * 100)}%
                      </span>
                    </div>
                  </div>
                )
              ))}
            </div>
            
            <div className="mt-6 pt-4 border-t border-gray-700">
              <p className="text-sm text-gray-400">
                Click <strong className="text-white">"Continue"</strong> below to generate trial balance →
              </p>
            </div>
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
}: any) => {
  const [isMobile, setIsMobile] = useState(false);

  React.useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  return (
    <div>
      <div className="mb-4 sm:mb-6">
        <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">Trial Balance Report</h2>
        <p className="text-sm sm:text-base text-gray-400">
          Generate and download your trial balance in Excel format
        </p>
      </div>

      {!trialBalance ? (
        <div className="text-center py-8 sm:py-12">
          <BookOpen className="h-12 w-12 sm:h-16 sm:w-16 text-blue-400 mx-auto mb-4 sm:mb-6" />
          <button
            onClick={onGenerate}
            disabled={generatingReport}
            className="px-6 sm:px-8 py-3 sm:py-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2 mx-auto min-h-[44px] text-sm sm:text-base"
          >
            {generatingReport ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span className="hidden sm:inline">Generating Report...</span>
                <span className="sm:hidden">Generating...</span>
              </>
            ) : (
              <>
                <TrendingUp className="h-5 w-5" />
                <span>Generate Trial Balance</span>
              </>
            )}
          </button>
        </div>
      ) : (
        <div>
          {/* Summary Cards - Mobile Stacked */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-4 sm:mb-6">
            <div className="bg-gradient-to-br from-blue-900/20 to-indigo-900/20 border border-blue-500/30 rounded-xl p-4 sm:p-6">
              <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-blue-400 mb-2 sm:mb-3" />
              <div className="text-xs sm:text-sm text-gray-400 mb-1">Total Debits</div>
              <div className="text-lg sm:text-2xl font-bold text-white">
                {formatCurrency(trialBalance.total_debits)}
              </div>
            </div>

            <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-4 sm:p-6">
              <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-green-400 mb-2 sm:mb-3" />
              <div className="text-xs sm:text-sm text-gray-400 mb-1">Total Credits</div>
              <div className="text-lg sm:text-2xl font-bold text-white">
                {formatCurrency(trialBalance.total_credits)}
              </div>
            </div>

            <div className={`bg-gradient-to-br ${
              trialBalance.is_balanced 
                ? 'from-green-900/20 to-emerald-900/20 border-green-500/30' 
                : 'from-red-900/20 to-orange-900/20 border-red-500/30'
            } border rounded-xl p-4 sm:p-6`}>
              <CheckCircle className={`h-6 w-6 sm:h-8 sm:w-8 ${
                trialBalance.is_balanced ? 'text-green-400' : 'text-red-400'
              } mb-2 sm:mb-3`} />
              <div className="text-xs sm:text-sm text-gray-400 mb-1">Status</div>
              <div className={`text-lg sm:text-2xl font-bold ${
                trialBalance.is_balanced ? 'text-green-400' : 'text-red-400'
              }`}>
                {trialBalance.is_balanced ? '✅ Balanced' : '⚠️ Not Balanced'}
              </div>
            </div>
          </div>

          {/* Accounts Table/Cards */}
          <div className="bg-gray-900/50 rounded-xl p-3 sm:p-4 mb-4 sm:mb-6">
            <h3 className="text-white font-semibold mb-3 sm:mb-4 text-sm sm:text-base">Account Breakdown</h3>
            
            {isMobile ? (
              /* Mobile: Card View */
              <div className="space-y-3">
                {trialBalance.accounts.map((account: any) => (
                  <div key={account.account_code} className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <p className="text-white font-medium text-sm">{account.account_name}</p>
                        <p className="text-gray-400 text-xs">{account.account_code}</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <span className="text-gray-400">Debits</span>
                        <p className="text-red-400 font-medium">{formatCurrency(account.debits)}</p>
                      </div>
                      <div>
                        <span className="text-gray-400">Credits</span>
                        <p className="text-green-400 font-medium">{formatCurrency(account.credits)}</p>
                      </div>
                      <div>
                        <span className="text-gray-400">Balance</span>
                        <p className="text-white font-medium">{formatCurrency(account.balance)}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              /* Desktop: Table View */
              <div className="overflow-x-auto">
                <table className="w-full min-w-[600px]">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left py-3 px-4 text-gray-400 font-medium text-sm">Code</th>
                      <th className="text-left py-3 px-4 text-gray-400 font-medium text-sm">Account</th>
                      <th className="text-right py-3 px-4 text-gray-400 font-medium text-sm">Debits</th>
                      <th className="text-right py-3 px-4 text-gray-400 font-medium text-sm">Credits</th>
                      <th className="text-right py-3 px-4 text-gray-400 font-medium text-sm">Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trialBalance.accounts.map((account: any) => (
                      <tr key={account.account_code} className="border-b border-gray-700/50">
                        <td className="py-3 px-4 text-gray-300 text-sm">{account.account_code}</td>
                        <td className="py-3 px-4 text-white text-sm">{account.account_name}</td>
                        <td className="py-3 px-4 text-right text-red-400 text-sm">
                          {formatCurrency(account.debits)}
                        </td>
                        <td className="py-3 px-4 text-right text-green-400 text-sm">
                          {formatCurrency(account.credits)}
                        </td>
                        <td className="py-3 px-4 text-right text-white text-sm">
                          {formatCurrency(account.balance)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Download Button */}
          <div className="text-center">
            <button
              onClick={onDownload}
              className="w-full sm:w-auto px-6 sm:px-8 py-3 sm:py-4 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 min-h-[44px] text-sm sm:text-base"
            >
              <Download className="h-5 w-5" />
              <span>Download Excel Report</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default BookkeepingPage;