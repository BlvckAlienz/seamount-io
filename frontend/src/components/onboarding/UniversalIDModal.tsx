import React, { useState, useEffect } from 'react';
import { X, Shield, Lock, AlertCircle, Globe } from 'lucide-react';
import toast from 'react-hot-toast';

interface UniversalIDModalProps {
  countryCode: string;
  countryName: string;
  onComplete: (data: any) => void;
  onCancel: () => void;
  userEmail: string;
}

const UniversalIDModal: React.FC<UniversalIDModalProps> = ({
  countryCode,
  countryName,
  onComplete,
  onCancel,
  userEmail
}) => {
  const [formData, setFormData] = useState({
    bvn: '',
    id_number: '',
    date_of_birth: '',
    gender: '',
    country_code: countryCode
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Country-specific configurations
  const countryConfigs = {
    'NG': {
      label: 'BVN (Bank Verification Number)',
      field: 'bvn',
      length: 11,
      help: 'Dial *565*0# to get your BVN',
      placeholder: 'Enter 11-digit BVN',
      id_type: 'BVN'
    },
    'KE': {
      label: 'National ID Number', 
      field: 'id_number',
      length: 8,
      help: 'Your Kenyan National ID number',
      placeholder: 'Enter 8-digit National ID',
      id_type: 'NATIONAL_ID'
    },
    'GH': {
      label: 'Ghana Card Number',
      field: 'id_number', 
      length: 15,
      help: 'Your Ghana Card number',
      placeholder: 'Enter Ghana Card number',
      id_type: 'GHANA_CARD'
    },
    'ZA': {
      label: 'South African ID Number',
      field: 'id_number',
      length: 13,
      help: 'Your South African ID number',
      placeholder: 'Enter 13-digit ID number',
      id_type: 'NATIONAL_ID'
    },
    'US': {
      label: 'Government ID Number',
      field: 'id_number',
      length: 9,
      help: 'Your government-issued ID number',
      placeholder: 'Enter ID number',
      id_type: 'PASSPORT'
    },
    'GB': {
      label: 'Government ID Number',
      field: 'id_number',
      length: 9,
      help: 'Your government-issued ID number',
      placeholder: 'Enter ID number',
      id_type: 'PASSPORT'
    },
    'CA': {
      label: 'Government ID Number',
      field: 'id_number',
      length: 9,
      help: 'Your government-issued ID number',
      placeholder: 'Enter ID number',
      id_type: 'PASSPORT'
    }
  };

  const config = countryConfigs[countryCode as keyof typeof countryConfigs] || countryConfigs['US'];
  const isNigeria = countryCode === 'NG';

  useEffect(() => {
    // Reset form when country changes
    setFormData(prev => ({
      ...prev,
      bvn: '',
      id_number: '',
      country_code: countryCode
    }));
    setErrors({});
  }, [countryCode]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    // Validate ID number based on country
    const idValue = isNigeria ? formData.bvn : formData.id_number;
    if (!idValue) {
      newErrors[config.field] = `${config.label} is required`;
    } else if (config.length && idValue.length !== config.length) {
      newErrors[config.field] = `Must be exactly ${config.length} characters`;
    } else if (config.field !== 'id_number' && !/^\d+$/.test(idValue)) {
      newErrors[config.field] = 'Must contain only numbers';
    }
    
    // Validate date of birth
    if (!formData.date_of_birth) {
      newErrors.date_of_birth = 'Date of birth is required';
    } else {
      const birthDate = new Date(formData.date_of_birth);
      const age = (new Date().getTime() - birthDate.getTime()) / (1000 * 60 * 60 * 24 * 365);
      if (age < 18) {
        newErrors.date_of_birth = 'You must be at least 18 years old';
      }
      if (age > 100) {
        newErrors.date_of_birth = 'Please enter a valid date of birth';
      }
    }
    
    // Validate gender
    if (!formData.gender) {
      newErrors.gender = 'Gender is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setLoading(true);
    
    try {
      const token = localStorage.getItem('token') || sessionStorage.getItem('supabase.auth.token');
      
      // Prepare payload with proper ID type
      const payload = {
        ...formData,
        country_code: countryCode,
        id_type: config.id_type,
        // Include both bvn and id_number for API compatibility
        ...(isNigeria ? { bvn: formData.bvn } : { id_number: formData.id_number })
      };
      
      const response = await fetch('/api/kyc/submit-kyc-data', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to save ID information');
      }
      
      const result = await response.json();
      
      if (result.success) {
        toast.success('Information saved successfully');
        onComplete(payload);
      } else {
        throw new Error(result.message || 'Failed to save information');
      }
      
    } catch (error: any) {
      console.error('ID submission error:', error);
      toast.error(error.message || 'Failed to save information');
      setErrors({ submit: error.message });
    } finally {
      setLoading(false);
    }
  };

  const handleIDChange = (value: string) => {
    const cleanedValue = value.replace(/\D/g, '').slice(0, config.length);
    
    if (isNigeria) {
      setFormData(prev => ({ ...prev, bvn: cleanedValue }));
    } else {
      setFormData(prev => ({ ...prev, id_number: cleanedValue }));
    }
    
    // Clear field-specific error
    setErrors(prev => ({ ...prev, [config.field]: '' }));
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl max-w-md w-full p-8 border border-blue-500/30 shadow-2xl relative">
        <button 
          onClick={onCancel}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
          disabled={loading}
        >
          <X className="h-6 w-6" />
        </button>

        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Globe className="h-8 w-8 text-blue-400" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Verify Your Identity</h2>
          <p className="text-gray-400 text-sm">
            {countryName} - Quick verification to unlock full platform access
          </p>
        </div>

        <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4 mb-6">
          <h3 className="text-blue-400 font-semibold mb-2 flex items-center text-sm">
            <Lock className="h-4 w-4 mr-2" />
            Why we need this
          </h3>
          <p className="text-xs text-gray-300">
            {countryCode === 'NG' 
              ? 'Nigerian regulations require BVN verification for financial services. Your data is encrypted and never shared.'
              : 'Identity verification is required for financial services compliance. Your data is encrypted and securely stored.'
            }
          </p>
        </div>

        {errors.submit && (
          <div className="mb-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
            <p className="text-red-400 text-sm flex items-center">
              <AlertCircle className="h-4 w-4 mr-2" />
              {errors.submit}
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* ID Number Input - Dynamic based on country */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {config.label} *
            </label>
            <input
              type="text"
              value={isNigeria ? formData.bvn : formData.id_number}
              onChange={(e) => handleIDChange(e.target.value)}
              placeholder={config.placeholder}
              maxLength={config.length}
              className={`w-full bg-gray-800 border ${
                errors[config.field] ? 'border-red-500' : 'border-gray-700'
              } rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none transition-colors`}
              disabled={loading}
            />
            {errors[config.field] && (
              <p className="text-red-400 text-xs mt-1">{errors[config.field]}</p>
            )}
            <p className="text-gray-500 text-xs mt-1">{config.help}</p>
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
              min={new Date(new Date().setFullYear(new Date().getFullYear() - 100)).toISOString().split('T')[0]}
              className={`w-full bg-gray-800 border ${
                errors.date_of_birth ? 'border-red-500' : 'border-gray-700'
              } rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none transition-colors`}
              disabled={loading}
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
              disabled={loading}
            >
              <option value="">Select gender</option>
              <option value="M">Male</option>
              <option value="F">Female</option>
              <option value="Other">Other</option>
              <option value="Prefer not to say">Prefer not to say</option>
            </select>
            {errors.gender && (
              <p className="text-red-400 text-xs mt-1">{errors.gender}</p>
            )}
          </div>

          {/* Confirmation Checkbox */}
          <div className="flex items-start gap-2 pt-2">
            <input
              type="checkbox"
              id="confirm"
              required
              className="mt-1 w-4 h-4 bg-gray-800 border-gray-700 rounded focus:ring-blue-500 focus:ring-offset-gray-900"
              disabled={loading}
            />
            <label htmlFor="confirm" className="text-xs text-gray-400">
              I confirm this information is accurate and matches my official records. I understand this data will be used for identity verification purposes.
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="flex-1 border border-gray-700 text-gray-300 py-3 px-4 rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Saving...
                </>
              ) : (
                'Continue to Verification'
              )}
            </button>
          </div>
        </form>

        {/* Security Footer */}
        <div className="mt-6 pt-4 border-t border-gray-700/50">
          <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
            <Shield className="h-3 w-3" />
            Your data is encrypted and stored securely
          </div>
        </div>
      </div>
    </div>
  );
};

export default UniversalIDModal;