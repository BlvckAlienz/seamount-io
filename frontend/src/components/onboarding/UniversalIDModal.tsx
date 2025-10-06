import React, { useState, useEffect } from 'react';
import { X, Shield, Lock, AlertCircle, Globe } from 'lucide-react';
import toast from 'react-hot-toast';
import { getCountryConfig, IDRequirement, CountryIDConfig } from '../../config/idRequirements';

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
  const [config, setConfig] = useState<CountryIDConfig | null>(null);
  const [selectedIDType, setSelectedIDType] = useState<string>('');
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

// In UniversalIDModal, enhance the useEffect to auto-select BVN for Nigeria
useEffect(() => {
  const countryConfig = getCountryConfig(countryCode);
  if (countryConfig) {
    setConfig(countryConfig);
    
    // 🎯 AUTO-SELECT BVN FOR NIGERIAN USERS
    if (countryCode === 'NG') {
      const bvnOption = countryConfig.supportedIDTypes.find(type => type.value === 'BVN');
      if (bvnOption) {
        setSelectedIDType('BVN');
      } else if (countryConfig.supportedIDTypes.length > 0) {
        setSelectedIDType(countryConfig.supportedIDTypes[0].value);
      }
    } else if (countryConfig.supportedIDTypes.length > 0) {
      setSelectedIDType(countryConfig.supportedIDTypes[0].value);
    }
  }
}, [countryCode]);

  const validateField = (requirement: IDRequirement, value: string): string | null => {
    if (!value.trim()) {
      return `${requirement.label} is required`;
    }
    if (requirement.validation && !requirement.validation(value)) {
      return requirement.errorMessage || 'Invalid input';
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!config || !selectedIDType) return;
    
    const requirements = config.requiredFields[selectedIDType] || [];
    const newErrors: Record<string, string> = {};
    
    // Validate all fields
    requirements.forEach(req => {
      const error = validateField(req, formData[req.field] || '');
      if (error) {
        newErrors[req.field] = error;
      }
    });
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    
    setLoading(true);
    setErrors({});
    
    try {
      const token = localStorage.getItem('token') || sessionStorage.getItem('supabase.auth.token');
      
      const payload = {
        ...formData,
        id_type: selectedIDType,
        country_code: countryCode
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
        throw new Error(errorData.detail || 'Failed to save ID data');
      }
      
      const result = await response.json();
      
      if (result.success) {
        toast.success('ID information saved successfully');
        onComplete(payload);
      } else {
        throw new Error(result.message || 'Failed to save ID data');
      }
      
    } catch (error: any) {
      console.error('ID submission error:', error);
      toast.error(error.message || 'Failed to save information');
      setErrors({ submit: error.message });
    } finally {
      setLoading(false);
    }
  };

  const renderField = (requirement: IDRequirement) => {
    const value = formData[requirement.field] || '';
    const error = errors[requirement.field];
    
    if (requirement.type === 'select') {
      return (
        <div key={requirement.field}>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            {requirement.label} *
          </label>
          <select
            value={value}
            onChange={(e) => {
              setFormData(prev => ({ ...prev, [requirement.field]: e.target.value }));
              setErrors(prev => ({ ...prev, [requirement.field]: '' }));
            }}
            className={`w-full bg-gray-800 border ${
              error ? 'border-red-500' : 'border-gray-700'
            } rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none`}
          >
            <option value="">Select {requirement.label}</option>
            {requirement.options?.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
        </div>
      );
    }
    
    return (
      <div key={requirement.field}>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          {requirement.label} *
        </label>
        <input
          type={requirement.type}
          value={value}
          onChange={(e) => {
            let inputValue = e.target.value;
            // Auto-format for number fields
            if (requirement.validation && /^\d+$/.test(requirement.validation.toString())) {
              inputValue = inputValue.replace(/\D/g, '');
            }
            setFormData(prev => ({ ...prev, [requirement.field]: inputValue }));
            setErrors(prev => ({ ...prev, [requirement.field]: '' }));
          }}
          placeholder={requirement.placeholder}
          max={requirement.type === 'date' ? new Date(new Date().setFullYear(new Date().getFullYear() - 18)).toISOString().split('T')[0] : undefined}
          className={`w-full bg-gray-800 border ${
            error ? 'border-red-500' : 'border-gray-700'
          } rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none`}
        />
        {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
      </div>
    );
  };

  if (!config) {
    return (
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
        <div className="bg-gray-900 rounded-2xl p-8 max-w-md w-full">
          <p className="text-white text-center">Loading country requirements...</p>
        </div>
      </div>
    );
  }

  const requirements = config.requiredFields[selectedIDType] || [];

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl max-w-md w-full p-8 border border-blue-500/30 shadow-2xl relative max-h-[90vh] overflow-y-auto">
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
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

        {errors.submit && (
          <div className="mb-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
            <p className="text-red-400 text-sm flex items-center">
              <AlertCircle className="h-4 w-4 mr-2" />
              {errors.submit}
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* ID Type Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              ID Type *
            </label>
            <select
              value={selectedIDType}
              onChange={(e) => {
                setSelectedIDType(e.target.value);
                setFormData({});
                setErrors({});
              }}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none"
            >
              {config.supportedIDTypes.map(type => (
                <option key={type.value} value={type.value}>{type.label}</option>
              ))}
            </select>
          </div>

          {/* Dynamic Fields */}
          {requirements.map(renderField)}

          {/* Confirmation */}
          <div className="flex items-start gap-2 pt-2">
            <input
              type="checkbox"
              id="confirm"
              required
              className="mt-1 w-4 h-4 bg-gray-800 border-gray-700 rounded"
            />
            <label htmlFor="confirm" className="text-xs text-gray-400">
              I confirm this information is accurate and matches my official ID
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="flex-1 border border-gray-700 text-gray-300 py-3 px-4 rounded-lg hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors disabled:opacity-50"
            >
              {loading ? 'Saving...' : 'Continue'}
            </button>
          </div>
        </form>

        <div className="mt-4 p-3 bg-blue-900/20 border border-blue-500/30 rounded-lg">
          <div className="flex items-start gap-2">
            <Lock className="h-4 w-4 text-blue-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-gray-300">
              Your data is encrypted and securely stored. We comply with international data protection regulations.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UniversalIDModal;