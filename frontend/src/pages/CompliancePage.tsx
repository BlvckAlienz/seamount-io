// File: frontend/src/pages/CompliancePage.tsx
// 📱 Mobile-First Responsive Compliance Dashboard - SIMPLIFIED VERSION

import React, { useState, useEffect } from 'react';
import { Receipt, FileText, CheckCircle, Upload, TrendingUp, Trash2 } from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

const CompliancePage = () => {
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState<any>(null);
  const [checklist, setChecklist] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'checklist' | 'documents' | 'exemptions'>('overview');
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
        setLoading(true);
        
        // Don't use artificial delay in production
        const [subRes, checklistRes, docsRes, progressRes] = await Promise.allSettled([
        apiClient.get('/api/v1/subscriptions/my-subscription'),
        apiClient.get('/api/v1/compliance/checklist'),
        apiClient.get('/api/v1/compliance/documents'),
        apiClient.get('/api/v1/compliance/checklist/progress-details')
        ]);

        // Handle subscription response
        if (subRes.status === 'fulfilled' && subRes.value.data.success) {
        setSubscription(subRes.value.data.subscription);
        } else {
        setSubscription(null);
        }

        // Handle checklist response
        if (checklistRes.status === 'fulfilled' && checklistRes.value.data.success) {
        const uniqueChecklist = deduplicateChecklistItems(checklistRes.value.data.checklist);
        setChecklist(uniqueChecklist);
        }

        // Handle documents response
        if (docsRes.status === 'fulfilled' && docsRes.value.data.success) {
        setDocuments(docsRes.value.data.documents);
        }

        // Handle progress response
        if (progressRes.status === 'fulfilled' && progressRes.value.data.success) {
        const progressData = progressRes.value.data;
        const overallProgress = progressData.overall_progress || 0;
        
        // Calculate total items from category progress
        let totalItems = 0;
        let completedItems = 0;
        
        Object.values(progressData.category_progress || {}).forEach((cat: any) => {
            totalItems += cat.total_items || 0;
            completedItems += cat.completed_items || 0;
        });
        
        setStats({
            completed_items: completedItems,
            total_items: totalItems,
            completion_percentage: overallProgress,
            category_progress: progressData.category_progress,
            total_documents: progressData.total_documents || 0
        });
        } else {
        // Fallback calculation if progress endpoint fails
        if (checklistRes.status === 'fulfilled' && checklistRes.value.data.success) {
            const uniqueChecklist = deduplicateChecklistItems(checklistRes.value.data.checklist);
            const totalItems = uniqueChecklist.length;
            const completedItems = uniqueChecklist.filter(item => item.is_completed).length;
            const completionPercentage = totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;
            
            setStats({
            completed_items: completedItems,
            total_items: totalItems,
            completion_percentage: completionPercentage
            });
        }
        }
        
        setAuthChecked(true);
    } catch (error) {
        console.error('Failed to fetch compliance data:', error);
        toast.error('Failed to load compliance data');
        setAuthChecked(true);
    } finally {
        setLoading(false);
    }
    };

  const deduplicateChecklistItems = (items: any[]): any[] => {
    if (!items || items.length === 0) return [];
    
    const seen = new Map();
    const result: any[] = [];
    
    items.forEach(item => {
      if (!item) return;
      const key = `${item.category}_${item.item_description}_${item.item_code || ''}`.toLowerCase().trim();
      if (!seen.has(key)) {
        seen.set(key, true);
        result.push(item);
      }
    });
    
    return result;
  };

  const formatCurrencyNGN = (amount: number): string => {
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  if (loading && !authChecked) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600"></div>
        </div>
      </div>
    );
  }

  if (authChecked && !subscription) {
    return <SubscriptionPlans formatCurrency={formatCurrencyNGN} />;
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
        <div className="max-w-7xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-3 mb-2">
              <Receipt className="h-8 w-8 text-green-400" />
              <span>Compliance OS</span>
            </h1>
            <p className="text-gray-400">Your audit & taxation command center</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-6">
              <div className="text-sm text-gray-400 mb-2">Audit Progress</div>
              <div className="text-4xl font-bold text-white mb-2">
                {stats?.completion_percentage || 0}%
              </div>
              <div className="text-sm text-blue-400">
                {stats?.completed_items || 0} of {stats?.total_items || 0} items
              </div>
            </div>

            <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-6">
              <div className="text-sm text-gray-400 mb-2">Documents</div>
              <div className="text-4xl font-bold text-white mb-2">{documents.length}</div>
              <div className="text-sm text-green-400">Uploaded for audit</div>
            </div>

            <div className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/30 rounded-xl p-6">
              <div className="text-sm text-gray-400 mb-2">Subscription</div>
              <div className="text-2xl font-bold text-white mb-2">{subscription?.subscription_plans?.name}</div>
              <div className="text-sm text-purple-400">{formatCurrencyNGN(subscription?.amount)}/yr</div>
            </div>
          </div>

          <div className="flex gap-2 mb-6 overflow-x-auto">
            {['overview', 'checklist', 'documents', 'exemptions'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab as any)}
                className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {activeTab === 'overview' && <OverviewTab stats={stats} />}
          {activeTab === 'checklist' && <ChecklistTab checklist={checklist} onRefresh={fetchData} />}
          {activeTab === 'documents' && <DocumentsTab documents={documents} onRefresh={fetchData} />}
          {activeTab === 'exemptions' && <ExemptionsTab formatCurrency={formatCurrencyNGN} />}
        </div>
      </div>
    </div>
  );
};

// ============================================
// SUB-COMPONENTS
// ============================================

const SubscriptionPlans = ({ formatCurrency }: { formatCurrency: (amount: number) => string }) => {
  const [loading, setLoading] = useState(false);

  const SUBSCRIPTION_PLANS = [
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
      outcome: "You're fully compliant. No FIRS penalties. Investors trust your numbers.",
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
  ];

  const handleSubscribe = async (planCode: string) => {
    try {
      setLoading(true);
      const res = await apiClient.post('/api/v1/subscriptions/initialize', { plan_code: planCode });
      if (res.data.success && res.data.payment_link) {
        window.location.href = res.data.payment_link;
      } else {
        toast.error('Failed to initialize subscription');
      }
    } catch (error) {
      toast.error('Subscription failed');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      <div className="flex-1 overflow-y-auto p-6 pt-20 lg:pt-6 flex items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600"></div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      <div className="flex-1 overflow-y-auto p-6 pt-20 lg:pt-6">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold text-white mb-2">Choose Your Plan</h1>
          <p className="text-gray-400 mb-8">Get audit-ready and unlock tax exemptions</p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {SUBSCRIPTION_PLANS.map((plan) => (
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
                  onClick={() => handleSubscribe(plan.id)}
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
};

const OverviewTab = ({ stats }: any) => (
  <div className="bg-gray-800/50 border border-gray-700/50 rounded-2xl p-6">
    <h2 className="text-xl font-bold text-white mb-4">Compliance Overview</h2>
    <div className="space-y-4">
      <div>
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-400">Audit Readiness</span>
          <span className="text-white font-medium">{stats?.completion_percentage || 0}%</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all"
            style={{ width: `${stats?.completion_percentage || 0}%` }}
          />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
        <div className="bg-gray-900/50 rounded-lg p-4">
          <FileText className="h-8 w-8 text-blue-400 mb-2" />
          <h3 className="text-white font-semibold mb-1">Documents</h3>
          <p className="text-gray-400 text-sm">Upload and organize your compliance documents</p>
        </div>
        <div className="bg-gray-900/50 rounded-lg p-4">
          <TrendingUp className="h-8 w-8 text-green-400 mb-2" />
          <h3 className="text-white font-semibold mb-1">Tax Exemptions</h3>
          <p className="text-gray-400 text-sm">Discover exemptions you qualify for</p>
        </div>
      </div>
    </div>
  </div>
);

const ChecklistTab = ({ checklist, onRefresh }: any) => {
  const handleComplete = async (itemId: string) => {
    try {
      await apiClient.post(`/api/v1/compliance/checklist/${itemId}/complete`);
      toast.success('Item marked as complete');
      onRefresh();
    } catch (error) {
      toast.error('Failed to update checklist');
    }
  };

  const categories: { [key: string]: string } = {
    C: 'Understanding Business',
    D: 'Share Capital',
    E: 'Fixed Assets',
    F: 'Inventory',
    G: 'Debtors',
    H: 'Cash & Bank',
    J: 'Creditors',
    K: 'Sales & Income',
    L: 'Expenses'
  };

  const groupedChecklist = checklist.reduce((acc: any, item: any) => {
    if (!acc[item.category]) acc[item.category] = [];
    acc[item.category].push(item);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {Object.entries(categories).map(([code, name]) => {
        const items = groupedChecklist[code] || [];
        const completedCount = items.filter((i: any) => i.is_completed).length;
        
        return (
          <div key={code} className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-white">
                {code}. {name}
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">
                  {completedCount}/{items.length}
                </span>
                <div className="w-24 bg-gray-700 rounded-full h-2">
                    <div 
                        className="bg-green-500 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${items.length > 0 ? (completedCount/items.length)*100 : 0}%` }}
                    />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              {items.map((item: any) => (
                <div
                  key={item.id}
                  className="flex items-start gap-3 p-3 bg-gray-900/50 rounded-lg hover:bg-gray-900/70 transition-colors"
                >
                  <button
                    onClick={() => !item.is_completed && handleComplete(item.id)}
                    disabled={item.is_completed}
                    className={`flex-shrink-0 transition-colors ${
                      item.is_completed ? 'text-green-400 cursor-default' : 'text-gray-600 hover:text-green-400'
                    }`}
                  >
                    <CheckCircle className="h-5 w-5" />
                  </button>
                  <div className="flex-1">
                    <p className={`text-sm ${item.is_completed ? 'text-gray-400 line-through' : 'text-gray-300'}`}>
                      {item.item_description}
                    </p>
                    {item.is_completed && (
                      <p className="text-xs text-green-400 mt-1">✓ Completed</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

const DocumentsTab = ({ documents, onRefresh }: any) => {
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('C');
  const [selectedType, setSelectedType] = useState('incorporation_docs');

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

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

      await apiClient.post('/api/v1/compliance/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      toast.success('Document uploaded successfully!');
      onRefresh();
    } catch (error: any) {
      console.error('Upload error:', error);
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
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
      setDeletingId(documentId);
      // You need to implement this backend endpoint
      await apiClient.delete(`/api/v1/compliance/documents/${documentId}`);
      toast.success('Document deleted successfully!');
      onRefresh();
    } catch (error: any) {
      console.error('Delete error:', error);
      toast.error('Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
        <h3 className="text-lg font-bold text-white mb-4">Upload Document</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Category</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
            >
              <option value="C">C - Understanding Business</option>
              <option value="D">D - Share Capital</option>
              <option value="E">E - Fixed Assets</option>
              <option value="F">F - Inventory</option>
              <option value="G">G - Debtors</option>
              <option value="H">H - Cash & Bank</option>
              <option value="J">J - Creditors</option>
              <option value="K">K - Sales & Income</option>
              <option value="L">L - Expenses</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Document Type</label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
            >
              <option value="incorporation_docs">Incorporation Docs</option>
              <option value="tax_certificate">Tax Certificate</option>
              <option value="audited_accounts">Audited Accounts</option>
              <option value="bank_statement">Bank Statement</option>
              <option value="license">License</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>

        <label className="flex items-center justify-center gap-2 px-6 py-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg cursor-pointer transition-colors">
          <Upload className="h-5 w-5" />
          {uploading ? 'Uploading...' : 'Choose File (PDF, JPG, PNG, DOC)'}
          <input
            type="file"
            onChange={handleUpload}
            disabled={uploading}
            className="hidden"
            accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
          />
        </label>
        <p className="text-xs text-gray-500 mt-2 text-center">Max file size: 10MB</p>
      </div>

      {/* SIMPLIFIED Documents List - No verification status */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
        <h3 className="text-lg font-bold text-white mb-4">Uploaded Documents ({documents.length})</h3>
        
        {documents.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="h-12 w-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No documents uploaded yet</p>
            <p className="text-gray-500 text-sm mt-2">Upload a file to update your audit checklist</p>
          </div>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
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
                        {doc.document_type?.replace('_', ' ') || 'Other'}
                      </span>
                      <span>•</span>
                      <span>Category {doc.category}</span>
                      <span>•</span>
                      <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors disabled:opacity-50"
                    title="Delete document"
                  >
                    {deletingId === doc.id ? 'Deleting...' : <Trash2 className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const ExemptionsTab = ({ formatCurrency }: { formatCurrency: (amount: number) => string }) => {
  const [formData, setFormData] = useState({
    business_type: 'small_company',
    annual_turnover: '',
    industry_sector: 'technology',
    employee_count: '',
    has_pension_contributions: false
  });
  const [result, setResult] = useState<any>(null);
  const [checking, setChecking] = useState(false);

  const handleCheck = async () => {
    try {
      setChecking(true);
      const res = await apiClient.post('/api/v1/compliance/exemption-checker', formData);
      if (res.data.success) {
        setResult(res.data);
        toast.success(`Found ${res.data.eligible_exemptions.length} exemptions!`);
      }
    } catch (error) {
      toast.error('Exemption check failed');
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
        <h3 className="text-lg font-bold text-white mb-4">Check Your Eligibility</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Business Type</label>
            <select
              value={formData.business_type}
              onChange={(e) => setFormData({...formData, business_type: e.target.value})}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
            >
              <option value="small_company">Small Company</option>
              <option value="startup">Startup</option>
              <option value="agricultural">Agricultural Business</option>
              <option value="individual">Individual/Sole Proprietor</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Annual Turnover (NGN)</label>
            <input
              type="number"
              value={formData.annual_turnover}
              onChange={(e) => setFormData({...formData, annual_turnover: e.target.value})}
              placeholder="Enter annual turnover"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Industry Sector</label>
            <select
              value={formData.industry_sector}
              onChange={(e) => setFormData({...formData, industry_sector: e.target.value})}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
            >
              <option value="technology">Technology</option>
              <option value="agriculture">Agriculture</option>
              <option value="manufacturing">Manufacturing</option>
              <option value="services">Services</option>
              <option value="retail">Retail</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Number of Employees</label>
            <input
              type="number"
              value={formData.employee_count}
              onChange={(e) => setFormData({...formData, employee_count: e.target.value})}
              placeholder="Enter employee count"
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.has_pension_contributions}
              onChange={(e) => setFormData({...formData, has_pension_contributions: e.target.checked})}
              className="w-4 h-4"
            />
            <label className="text-sm text-gray-300">We make pension contributions</label>
          </div>

          <button
            onClick={handleCheck}
            disabled={checking}
            className="w-full py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors"
          >
            {checking ? 'Checking...' : 'Check Exemptions'}
          </button>
        </div>
      </div>

      {result && (
        <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-6">
          <h3 className="text-lg font-bold text-white mb-2">You Qualify For:</h3>
          <div className="text-3xl font-bold text-green-400 mb-6">
            {formatCurrency(result.estimated_tax_savings)} in savings
          </div>

          <div className="space-y-3">
            {result.eligible_exemptions.map((exemption: any, idx: number) => (
              <div key={idx} className="p-4 bg-gray-900/50 rounded-lg">
                <h4 className="text-white font-semibold mb-1">{exemption.name}</h4>
                <p className="text-sm text-gray-400 mb-2">{exemption.description}</p>
                {exemption.estimated_savings > 0 && (
                  <p className="text-sm text-green-400">
                    Estimated Savings: {formatCurrency(exemption.estimated_savings)}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default CompliancePage;