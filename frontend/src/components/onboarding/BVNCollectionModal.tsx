// File Location: frontend/src/components/onboarding/BVNCollectionModal.tsx
// HYBRID APPROACH: Smart progressive BVN collection modal

import React, { useState } from 'react';
import { X, Shield, Lock, AlertCircle, Phone } from 'lucide-react';
import toast from 'react-hot-toast';

interface BVNCollectionModalProps {
  onComplete: (bvnData: BVNData) => void;
  onCancel: () => void;
  userEmail: string;
}

interface BVNData {
  bvn: string;
  date_of_birth: string;
  gender: string;
}

const BVNCollectionModal: React.FC<BVNCollectionModalProps> = ({ 
  onComplete, 
  onCancel,
  userEmail 
}) => {
  const [formData, setFormData] = useState<BVNData>({
    bvn: '',
    date_of_birth: '',
    gender: ''
  });
  const [loading, setLoading] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateBVN = (bvn: string): boolean => {
    // Must be exactly 11 digits
    const bvnRegex = /^\d{11}$/;
    return bvnRegex.test(bvn);
  };

  const validateAge = (dob: string): boolean => {
    // Must be 18+ years old
    const birthDate = new Date(dob);
    const today = new Date();
    const age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      return age - 1 >= 18;
    }
    return age >= 18;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    const newErrors: Record<string, string> = {};
    
    if (!formData.bvn.trim()) {
      newErrors.bvn = 'BVN is required';
    } else if (!validateBVN(formData.bvn)) {
      newErrors.bvn = 'BVN must be exactly 11 digits';
    }
    
    if (!formData.date_of_birth) {
      newErrors.date_of_birth = 'Date of birth is required';
    } else if (!validateAge(formData.date_of_birth)) {
      newErrors.date_of_birth = 'You must be at least 18 years old';
    }
    
    if (!formData.gender) {
      newErrors.gender = 'Gender is required';
    }
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    
    setLoading(true);
    setErrors({});
    
    try {
      // Submit to backend
      const token = localStorage.getItem('token') || sessionStorage.getItem('supabase.auth.token');
      
      const response = await fetch('/api/kyc/submit-kyc-data', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to save KYC data');
      }
      
      const result = await response.json();
      
      if (result.success) {
        toast.success('Information saved successfully');
        onComplete(formData);
      } else {
        throw new Error(result.message || 'Failed to save KYC data');
      }
      
    } catch (error: any) {
      console.error('BVN submission error:', error);
      toast.error(error.message || 'Failed to save information');
      setErrors({ submit: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl max-w-md w-full p-8 border border-blue-500/30 shadow-2xl relative">
        {/* Close Button */}
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
        >
          <X className="h-6 w-6" />
        </button>

        {/* Header */}
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Shield className="h-8 w-8 text-blue-400" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Quick Identity Check</h2>
          <p className="text-gray-400 text-sm">
            To comply with Nigerian banking regulations, we need to verify your BVN
          </p>
        </div>

        {/* Compliance Notice */}
        <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4 mb-6">
          <h3 className="text-blue-400 font-semibold mb-2 flex items-center text-sm">
            <Lock className="h-4 w-4 mr-2" />
            Why we need this
          </h3>
          <ul className="text-xs text-gray-300 space-y-1">
            <li>• Nigerian regulations require BVN verification for financial services</li>
            <li>• Your data is encrypted and never shared</li>
            <li>• This enables instant NGN deposits and withdrawals</li>
          </ul>
        </div>

        {/* Error Alert */}
        {errors.submit && (
          <div className="mb-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
            <p className="text-red-400 text-sm flex items-center">
              <AlertCircle className="h-4 w-4 mr-2" />
              {errors.submit}
            </p>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* BVN Input */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Bank Verification Number (BVN) *
            </label>
            <input
              type="text"
              value={formData.bvn}
              onChange={(e) => {
                const value = e.target.value.replace(/\D/g, '').slice(0, 11);
                setFormData(prev => ({ ...prev, bvn: value }));
                setErrors(prev => ({ ...prev, bvn: '' }));
              }}
              placeholder="Enter 11-digit BVN"
              maxLength={11}
              className={`w-full bg-gray-800 border ${
                errors.bvn ? 'border-red-500' : 'border-gray-700'
              } rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none transition-colors`}
            />
            {errors.bvn && (
              <p className="text-red-400 text-xs mt-1">{errors.bvn}</p>
            )}
            <button
              type="button"
              onClick={() => setShowHelp(!showHelp)}
              className="text-blue-400 hover:text-blue-300 text-xs mt-1 flex items-center gap-1"
            >
              <Phone className="h-3 w-3" />
              How to find my BVN?
            </button>
            {showHelp && (
              <div className="mt-2 p-3 bg-gray-800/50 rounded-lg text-xs text-gray-300">
                <p className="font-semibold mb-1">Find your BVN:</p>
                <ul className="space-y-1">
                  <li>• Dial *565*0# from your registered phone</li>
                  <li>• Check your bank statement</li>
                  <li>• Visit any bank branch with valid ID</li>
                </ul>
              </div>
            )}
          </div>

          {/* Date of Birth */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Date of Birth *
            </label>
            <input
              type="date"
              value={formData.date_of_birth}
              onChange={(e) => {
                setFormData(prev => ({ ...prev, date_of_birth: e.target.value }));
                setErrors(prev => ({ ...prev, date_of_birth: '' }));
              }}
              max={new Date(new Date().setFullYear(new Date().getFullYear() - 18)).toISOString().split('T')[0]}
              className={`w-full bg-gray-800 border ${
                errors.date_of_birth ? 'border-red-500' : 'border-gray-700'
              } rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none transition-colors`}
            />
            {errors.date_of_birth && (
              <p className="text-red-400 text-xs mt-1">{errors.date_of_birth}</p>
            )}
          </div>

          {/* Gender */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Gender *
            </label>
            <select
              value={formData.gender}
              onChange={(e) => {
                setFormData(prev => ({ ...prev, gender: e.target.value }));
                setErrors(prev => ({ ...prev, gender: '' }));
              }}
              className={`w-full bg-gray-800 border ${
                errors.gender ? 'border-red-500' : 'border-gray-700'
              } rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none transition-colors`}
            >
              <option value="">Select gender</option>
              <option value="M">Male</option>
              <option value="F">Female</option>
              <option value="Other">Other</option>
            </select>
            {errors.gender && (
              <p className="text-red-400 text-xs mt-1">{errors.gender}</p>
            )}
          </div>

          {/* Confirmation Checkbox */}
          <div className="flex items-start gap-2">
            <input
              type="checkbox"
              id="confirm"
              required
              className="mt-1 w-4 h-4 bg-gray-800 border-gray-700 rounded"
            />
            <label htmlFor="confirm" className="text-xs text-gray-400">
              I confirm this information is accurate and matches my BVN records
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="flex-1 border border-gray-700 text-gray-300 py-3 px-4 rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
            >
              I'll do this later
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Saving...' : 'Continue to Verification'}
            </button>
          </div>
        </form>

        {/* Security Note */}
        <p className="text-center text-xs text-gray-500 mt-4">
          🔒 Your data is encrypted and stored securely
        </p>
      </div>
    </div>
  );
};

export default BVNCollectionModal;