import React, { useState } from 'react';
import { 
  Building2, Users, TrendingUp, FileText, 
  CheckCircle, AlertCircle, ChevronRight 
} from 'lucide-react';
import { BUSINESS_SECTORS } from '@/data/businessSectors';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface QuestionnaireData {
  accountType: 'individual' | 'business' | '';
  businessType: 'custodian' | 'asset_owner' | 'broker_dealer' | 'retail_investor' | 'auction_house' | 'ngo' | 'other' | '';
  legalBusinessName: string;
  registeredCompanyNumber: string;
  companySize: 'less_than_50' | '50_to_100' | '100_to_300' | '300_to_500' | '500_to_1000' | 'more_than_1000' | '';
  sector: string;
  intent: 'tokenize_asset' | 'raise_capital' | 'trade_crypto' | 'other' | '';
  tokenizationDetails: string;
  capitalRaisingDetails: string;
  hasCorporateDocs: boolean | null;
}

interface Props {
  onComplete: (data: QuestionnaireData) => void;
  onSkip: () => void;
}

const BusinessQuestionnaireStep: React.FC<Props> = ({ onComplete, onSkip }) => {
  const [data, setData] = useState<QuestionnaireData>({
    accountType: '',
    businessType: '',
    legalBusinessName: '',
    registeredCompanyNumber: '',
    companySize: '',
    sector: '',
    intent: '',
    tokenizationDetails: '',
    capitalRaisingDetails: '',
    hasCorporateDocs: null,
  });

  const [errors, setErrors] = useState<Partial<Record<keyof QuestionnaireData, string>>>({});
  const [currentStep, setCurrentStep] = useState(1);
  
  // Document upload state
  const [uploadedDocs, setUploadedDocs] = useState<Record<string, string>>({});
  const [uploading, setUploading] = useState(false);

  // Character limits for text fields
  const CHAR_LIMITS = {
    tokenizationDetails: 500,
    capitalRaisingDetails: 500,
  };

  const handleInputChange = (field: keyof QuestionnaireData, value: any) => {
    setData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const uploadDocument = async (file: File, documentType: string) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('category', 'C'); // Category C = Understanding Business
      formData.append('document_type', documentType);

      const response = await apiClient.post('/api/v1/compliance/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.success) {
        const docId = response.data.document_id;
        setUploadedDocs(prev => ({ ...prev, [documentType]: docId }));
        toast.success(`${file.name} uploaded successfully`);
      } else {
        throw new Error('Upload failed');
      }
    } catch (error: any) {
      console.error('Upload error:', error);
      toast.error(`Failed to upload ${file.name}: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const validateStep = (): boolean => {
    const newErrors: Partial<Record<keyof QuestionnaireData, string>> = {};

    if (currentStep === 1 && !data.accountType) {
      newErrors.accountType = 'Please select an account type';
    }

    if (data.accountType === 'business') {
      if (currentStep === 2) {
        if (!data.businessType) newErrors.businessType = 'Please select business type';
        if (!data.legalBusinessName?.trim()) newErrors.legalBusinessName = 'Business name is required';
        if (!data.registeredCompanyNumber?.trim()) newErrors.registeredCompanyNumber = 'Company number is required';
        if (!data.companySize) newErrors.companySize = 'Please select company size';
        if (!data.sector) newErrors.sector = 'Please select a sector';
      }

      if (currentStep === 3) {
        if (!data.intent) newErrors.intent = 'Please select your primary intent';
        if (data.hasCorporateDocs === null) {
          newErrors.hasCorporateDocs = 'Please indicate if you have corporate docs';
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (!validateStep()) return;

    // ✅ Check if mandatory document is uploaded when corporate docs exist
    if (data.accountType === 'business' && data.hasCorporateDocs === true && !uploadedDocs['company_registration_certificate']) {
      setErrors(prev => ({ ...prev, hasCorporateDocs: 'Please upload the Company Registration Certificate before completing.' }));
      // Scroll to error
      const errorEl = document.querySelector('[data-error="hasCorporateDocs"]');
      if (errorEl) errorEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    // ✅ FIX: ALL users (individual + business) proceed to KYC
    if (data.accountType === 'individual') {
        // Save individual account type, then proceed to KYC
        onComplete(data);
        return;
    }

    // Move to next step for business
    if (currentStep < 3) {
      setCurrentStep(prev => prev + 1);
    } else {
      // Submit questionnaire data
      onComplete(data);
    }
  };

  const renderStepIndicator = () => {
    if (data.accountType !== 'business') return null;

    return (
      <div className="flex items-center justify-center gap-2 mb-6">
        {[1, 2, 3].map(step => (
          <div
            key={step}
            className={`h-2 w-12 rounded-full transition-all ${
              step === currentStep
                ? 'bg-blue-500'
                : step < currentStep
                ? 'bg-green-500'
                : 'bg-gray-600'
            }`}
          />
        ))}
      </div>
    );
  };

  // STEP 1: Account Type
  if (currentStep === 1) {
    return (
      <div className="text-center">
        {renderStepIndicator()}
        
        <div className="mb-6">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <Building2 className="h-8 w-8 text-white" />
          </div>
          <h3 className="text-2xl font-bold text-white mb-2">Account Type</h3>
          <p className="text-gray-400">Help us personalize your experience</p>
        </div>

        <div className="space-y-3">
          {/* Individual Option */}
          <button
            onClick={() => handleInputChange('accountType', 'individual')}
            className={`w-full p-4 rounded-xl border-2 transition-all text-left ${
              data.accountType === 'individual'
                ? 'border-blue-500 bg-blue-500/10'
                : 'border-gray-600 hover:border-gray-500 bg-gray-800/50'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold text-white mb-1">Individual Account</div>
                <div className="text-sm text-gray-400">Personal trading & investing</div>
              </div>
              {data.accountType === 'individual' && (
                <CheckCircle className="h-6 w-6 text-blue-500" />
              )}
            </div>
          </button>

          {/* Business Option */}
          <button
            onClick={() => handleInputChange('accountType', 'business')}
            className={`w-full p-4 rounded-xl border-2 transition-all text-left ${
              data.accountType === 'business'
                ? 'border-purple-500 bg-purple-500/10'
                : 'border-gray-600 hover:border-gray-500 bg-gray-800/50'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold text-white mb-1">Business Account</div>
                <div className="text-sm text-gray-400">
                  Tokenization, capital raising & institutional services
                </div>
              </div>
              {data.accountType === 'business' && (
                <CheckCircle className="h-6 w-6 text-purple-500" />
              )}
            </div>
          </button>
        </div>

        {errors.accountType && (
          <div className="mt-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-400" />
            <p className="text-red-400 text-sm">{errors.accountType}</p>
          </div>
        )}

        <button
          onClick={handleNext}
          disabled={!data.accountType}
          className="w-full mt-6 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-4 px-6 rounded-xl disabled:opacity-50 transition-all flex items-center justify-center gap-2"
        >
          Continue
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
    );
  }

  // STEP 2: Business Details (only for business accounts)
  if (currentStep === 2 && data.accountType === 'business') {
    return (
      <div className="text-center">
        {renderStepIndicator()}
        
        <div className="mb-6">
          <h3 className="text-2xl font-bold text-white mb-2">Business Details</h3>
          <p className="text-gray-400">Tell us about your company</p>
        </div>

        <div className="space-y-4 text-left">
          {/* Business Type */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Business Type <span className="text-red-400">*</span>
            </label>
            <select
              value={data.businessType}
              onChange={(e) => handleInputChange('businessType', e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select business type...</option>
              <option value="asset_owner">Asset Owner</option>
              <option value="custodian">Custodian</option>
              <option value="broker_dealer">Broker-Dealer</option>
              <option value="retail_investor">Retail Investor</option>
              <option value="auction_house">Auction House</option>
              <option value="ngo">NGO</option>
              <option value="other">Other</option>
            </select>
            {errors.businessType && (
              <p className="text-red-400 text-sm mt-1">{errors.businessType}</p>
            )}
          </div>

        {/* Legal Business Name */}
        <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
                Legal Business Name <span className="text-red-400">*</span>
            </label>
            <input
                type="text"
                value={data.legalBusinessName}
                onChange={(e) => handleInputChange('legalBusinessName', e.target.value)}
                placeholder="e.g., Seamount Technologies Ltd"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.legalBusinessName && (
                <p className="text-red-400 text-sm mt-1">{errors.legalBusinessName}</p>
            )}
        </div>

        {/* Registered Company Number */}
        <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
                Registered Company Number <span className="text-red-400">*</span>
            </label>
            <input
                type="text"
                value={data.registeredCompanyNumber}
                onChange={(e) => handleInputChange('registeredCompanyNumber', e.target.value)}
                placeholder="e.g., CAC/RC 1234567"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.registeredCompanyNumber && (
                <p className="text-red-400 text-sm mt-1">{errors.registeredCompanyNumber}</p>
            )}
        </div>

          {/* Company Size */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Company Size <span className="text-red-400">*</span>
            </label>
            <select
              value={data.companySize}
              onChange={(e) => handleInputChange('companySize', e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select company size...</option>
              <option value="less_than_50">Less than 50 employees</option>
              <option value="50_to_100">50-100 employees</option>
              <option value="more_than_100">More than 100 employees</option>
            </select>
            {errors.companySize && (
              <p className="text-red-400 text-sm mt-1">{errors.companySize}</p>
            )}
          </div>

          {/* Sector */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Industry Sector <span className="text-red-400">*</span>
            </label>
            <select
              value={data.sector}
              onChange={(e) => handleInputChange('sector', e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select industry sector...</option>
              {BUSINESS_SECTORS.map(sector => (
                <option key={sector.value} value={sector.value}>
                  {sector.label}
                </option>
              ))}
            </select>
            {errors.sector && (
              <p className="text-red-400 text-sm mt-1">{errors.sector}</p>
            )}
          </div>
        </div>

        <button
          onClick={handleNext}
          className="w-full mt-6 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-4 px-6 rounded-xl transition-all flex items-center justify-center gap-2"
        >
          Continue
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
    );
  }

  // STEP 3: Intent & Details (only for business accounts)
  if (currentStep === 3 && data.accountType === 'business') {
    return (
      <div className="text-center">
        {renderStepIndicator()}
        
        <div className="mb-6">
          <h3 className="text-2xl font-bold text-white mb-2">Your Goals</h3>
          <p className="text-gray-400">What brings you to Seamount?</p>
        </div>

        <div className="space-y-4 text-left max-h-[400px] overflow-y-auto pr-2">
          {/* Primary Intent */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              What do you intend to achieve? <span className="text-red-400">*</span>
            </label>
            <div className="space-y-2">
              {[
                { value: 'tokenize_asset', label: 'Tokenize Assets', icon: FileText },
                { value: 'raise_capital', label: 'Raise Capital', icon: TrendingUp },
                { value: 'trade_crypto', label: 'Trade Crypto', icon: Users },
                { value: 'other', label: 'Other', icon: AlertCircle },
              ].map(option => (
                <button
                  key={option.value}
                  onClick={() => handleInputChange('intent', option.value)}
                  className={`w-full p-3 rounded-lg border-2 transition-all text-left flex items-center gap-3 ${
                    data.intent === option.value
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-gray-600 hover:border-gray-500 bg-gray-800/50'
                  }`}
                >
                  <option.icon className="h-5 w-5 text-gray-400" />
                  <span className="text-white">{option.label}</span>
                  {data.intent === option.value && (
                    <CheckCircle className="h-5 w-5 text-blue-500 ml-auto" />
                  )}
                </button>
              ))}
            </div>
            {errors.intent && (
              <p className="text-red-400 text-sm mt-1">{errors.intent}</p>
            )}
          </div>

          {/* Tokenization Details (Optional) */}
          {(data.intent === 'tokenize_asset' || data.intent === 'multiple') && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                What do you want to tokenize? (Optional)
              </label>
              <textarea
                value={data.tokenizationDetails}
                onChange={(e) => {
                  if (e.target.value.length <= CHAR_LIMITS.tokenizationDetails) {
                    handleInputChange('tokenizationDetails', e.target.value);
                  }
                }}
                placeholder="e.g., Real estate properties, agricultural commodities, infrastructure projects..."
                className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                rows={3}
              />
              <div className="text-xs text-gray-500 mt-1">
                {data.tokenizationDetails.length}/{CHAR_LIMITS.tokenizationDetails} characters
              </div>
            </div>
          )}

          {/* Capital Raising Details (Optional) */}
          {(data.intent === 'raise_capital' || data.intent === 'tokenize_asset' || data.intent === 'other') && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Provide more details (Optional)
              </label>
              <textarea
                value={data.capitalRaisingDetails}
                onChange={(e) => {
                  if (e.target.value.length <= CHAR_LIMITS.capitalRaisingDetails) {
                    handleInputChange('capitalRaisingDetails', e.target.value);
                  }
                }}
                placeholder="e.g., Seed round for $500K, Series A targeting $2M..."
                className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                rows={3}
              />
              <div className="text-xs text-gray-500 mt-1">
                {data.capitalRaisingDetails.length}/{CHAR_LIMITS.capitalRaisingDetails} characters
              </div>
            </div>
          )}

          {/* Corporate Docs */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Do you have corporate structure documents? <span className="text-red-400">*</span>
            </label>
            <p className="text-xs text-gray-500 mb-2">
              (CAC, TIN/Tax Certificates, Licenses, Audited Accounts, etc.)
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => handleInputChange('hasCorporateDocs', true)}
                className={`flex-1 py-3 rounded-lg border-2 transition-all ${
                  data.hasCorporateDocs === true
                    ? 'border-green-500 bg-green-500/10 text-green-400'
                    : 'border-gray-600 hover:border-gray-500 bg-gray-800/50 text-white'
                }`}
              >
                Yes
              </button>
              <button
                onClick={() => handleInputChange('hasCorporateDocs', false)}
                className={`flex-1 py-3 rounded-lg border-2 transition-all ${
                  data.hasCorporateDocs === false
                    ? 'border-red-500 bg-red-500/10 text-red-400'
                    : 'border-gray-600 hover:border-gray-500 bg-gray-800/50 text-white'
                }`}
              >
                No
              </button>
            </div>
            {errors.hasCorporateDocs && (
              <div data-error="hasCorporateDocs" className="mt-2 p-2 bg-red-900/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
                <AlertCircle className="h-4 w-4 inline-block mr-1" />
                {errors.hasCorporateDocs}
              </div>
            )}
          </div>

          {/* 🆕 Document Upload Section (only when user has corporate docs) */}
          {data.hasCorporateDocs === true && (
            <div className="mt-6 p-4 bg-gray-800/50 border border-gray-700 rounded-xl">
              <h4 className="text-white font-semibold mb-3">Required Corporate Documents</h4>
              <p className="text-xs text-gray-400 mb-4">
                Upload the following documents (PDF format, max 10MB each). 
                <span className="text-red-400 ml-1">Company Registration Certificate is mandatory to proceed.</span>
              </p>
              
              <div className="space-y-3">
                {/* Mandatory: Company Registration Certificate */}
                <div className="flex items-center justify-between p-3 bg-gray-900 rounded-lg">
                  <div>
                    <div className="text-white text-sm font-medium">Company Registration Certificate</div>
                    <div className="text-xs text-gray-400">CAC certificate, incorporation documents</div>
                  </div>
                  {uploadedDocs['company_registration_certificate'] ? (
                    <span className="text-green-400 text-sm flex items-center gap-1">
                      <CheckCircle className="h-4 w-4" /> Uploaded
                    </span>
                  ) : (
                    <label className={`cursor-pointer bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-sm transition-colors ${uploading ? 'opacity-50 pointer-events-none' : ''}`}>
                      {uploading ? 'Uploading...' : 'Upload'}
                      <input
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png"
                        className="hidden"
                        disabled={uploading}
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) uploadDocument(file, 'company_registration_certificate');
                        }}
                      />
                    </label>
                  )}
                </div>
                
                {/* Optional documents (can be uploaded later) */}
                <div className="border-t border-gray-700 pt-3 mt-2">
                  <p className="text-xs text-gray-500 mb-2">Optional documents (can be uploaded later)</p>
                  <div className="space-y-2">
                    {[
                      { label: 'Articles of Association', type: 'memorandum_articles' },
                      { label: 'Directors/Share Capital Registry', type: 'register_of_members' },
                      { label: 'ID of a Director', type: 'director_id' },
                      { label: 'Director Proof of Address', type: 'director_proof_of_address' },
                      { label: 'Business License/Permit', type: 'license' },
                      { label: 'Tax Certificate', type: 'tax_certificate' },
                      { label: 'AML Policy', type: 'aml_policy' }
                    ].map(doc => (
                      <div key={doc.type} className="flex items-center justify-between">
                        <span className="text-sm text-gray-400">{doc.label}</span>
                        {uploadedDocs[doc.type] ? (
                          <span className="text-green-400 text-xs">Uploaded</span>
                        ) : (
                          <label className={`cursor-pointer bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded-lg text-xs transition-colors ${uploading ? 'opacity-50 pointer-events-none' : ''}`}>
                            Upload
                            <input
                              type="file"
                              accept=".pdf,.jpg,.jpeg,.png"
                              className="hidden"
                              disabled={uploading}
                              onChange={(e) => {
                                const file = e.target.files?.[0];
                                if (file) uploadDocument(file, doc.type);
                              }}
                            />
                          </label>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <button
          onClick={handleNext}
          disabled={data.hasCorporateDocs === true && !uploadedDocs['company_registration_certificate']}
          className="w-full mt-6 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-4 px-6 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center gap-2"
        >
          Complete Questionnaire
          <CheckCircle className="h-5 w-5" />
        </button>
      </div>
    );
  }

  return null;
};

export default BusinessQuestionnaireStep;