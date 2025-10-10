import React, { useState, useEffect } from 'react';
import { AlertCircle, Shield, Globe } from 'lucide-react';

interface CountryConfig {
  name: string;
  idTypes: Array<{ value: string; label: string; placeholder: string }>;
  requiresID: boolean;
}

const COUNTRY_CONFIGS: Record<string, CountryConfig> = {
  NG: {
    name: 'Nigeria',
    idTypes: [
      { value: 'BVN', label: 'BVN (Bank Verification Number)', placeholder: '22123456789' },
      { value: 'NIN', label: 'NIN (National ID Number)', placeholder: '12345678901' }
    ],
    requiresID: true
  },
  KE: {
    name: 'Kenya',
    idTypes: [
      { value: 'NATIONAL_ID', label: 'Kenyan National ID', placeholder: '12345678' }
    ],
    requiresID: true
  },
  GH: {
    name: 'Ghana',
    idTypes: [
      { value: 'GHANA_CARD', label: 'Ghana Card', placeholder: 'GHA-123456789-0' }
    ],
    requiresID: true
  },
  ZA: {
    name: 'South Africa',
    idTypes: [
      { value: 'ID_NUMBER', label: 'SA ID Number', placeholder: '8001015009087' }
    ],
    requiresID: true
  },
  DEFAULT: {
    name: 'Other',
    idTypes: [
      { value: 'PASSPORT', label: 'Passport Number', placeholder: 'A12345678' }
    ],
    requiresID: false // Passport is optional for non-priority markets
  }
};

interface BVNCollectionModalProps {
  onComplete: (data: any) => void;
  onCancel: () => void;
  userEmail: string;
  countryCode?: string;
}

const BVNCollectionModal: React.FC<BVNCollectionModalProps> = ({ 
  onComplete, 
  onCancel, 
  userEmail,
  countryCode = 'NG'
}) => {
  const [formData, setFormData] = useState({
    idType: '',
    idNumber: '',
    dateOfBirth: '',
    gender: '',
    phoneNumber: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const config = COUNTRY_CONFIGS[countryCode] || COUNTRY_CONFIGS.DEFAULT;

  // Auto-select ID type if only one option
  useEffect(() => {
    if (config.idTypes.length === 1) {
      setFormData(prev => ({ ...prev, idType: config.idTypes[0].value }));
    }
  }, [config]);

  const selectedIDType = config.idTypes.find(id => id.value === formData.idType);

  const validateForm = () => {
    if (config.requiresID && !formData.idNumber) {
      setError(`${selectedIDType?.label || 'ID'} is required`);
      return false;
    }
    if (!formData.dateOfBirth) {
      setError('Date of birth is required');
      return false;
    }
    if (!formData.gender) {
      setError('Gender is required');
      return false;
    }
    if (!formData.phoneNumber) {
      setError('Phone number is required');
      return false;
    }
    return true;
  };

  const handleSubmit = async () => {
    setError('');
    
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      await onComplete({
        ...formData,
        country: countryCode
      });
    } catch (err: any) {
      setError(err.message || 'Verification failed');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-2xl p-8 max-w-md w-full mx-4 border border-gray-700">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-blue-500/20 rounded-full flex items-center justify-center">
            <Globe className="h-6 w-6 text-blue-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Identity Verification</h2>
            <p className="text-gray-400 text-sm">{config.name}</p>
          </div>
        </div>
        
        <p className="text-gray-300 mb-6">
          Complete your profile to unlock full platform access
        </p>
        
        <div className="space-y-4">
          {/* ID Type Selection (if multiple options) */}
          {config.idTypes.length > 1 && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                ID Type *
              </label>
              <select
                value={formData.idType}
                onChange={(e) => setFormData({...formData, idType: e.target.value, idNumber: ''})}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                <option value="">Select ID type</option>
                {config.idTypes.map(id => (
                  <option key={id.value} value={id.value}>{id.label}</option>
                ))}
              </select>
            </div>
          )}
          
          {/* ID Number Input */}
          {(formData.idType || config.idTypes.length === 1) && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {selectedIDType?.label || config.idTypes[0].label} {config.requiresID && '*'}
              </label>
              <input
                type="text"
                value={formData.idNumber}
                onChange={(e) => setFormData({...formData, idNumber: e.target.value})}
                placeholder={selectedIDType?.placeholder || config.idTypes[0].placeholder}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>
          )}
          
          {/* Date of Birth */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Date of Birth *
            </label>
            <input
              type="date"
              value={formData.dateOfBirth}
              onChange={(e) => setFormData({...formData, dateOfBirth: e.target.value})}
              max={new Date().toISOString().split('T')[0]}
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>
          
          {/* Gender */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Gender *
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setFormData({...formData, gender: 'M'})}
                className={`px-4 py-3 rounded-lg border transition-all ${
                  formData.gender === 'M' 
                    ? 'bg-blue-600 border-blue-600 text-white' 
                    : 'bg-gray-900 border-gray-700 text-gray-300 hover:border-gray-600'
                }`}
              >
                Male
              </button>
              <button
                type="button"
                onClick={() => setFormData({...formData, gender: 'F'})}
                className={`px-4 py-3 rounded-lg border transition-all ${
                  formData.gender === 'F' 
                    ? 'bg-blue-600 border-blue-600 text-white' 
                    : 'bg-gray-900 border-gray-700 text-gray-300 hover:border-gray-600'
                }`}
              >
                Female
              </button>
            </div>
          </div>
          
          {/* Phone Number */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Phone Number *
            </label>
            <input
              type="tel"
              value={formData.phoneNumber}
              onChange={(e) => setFormData({...formData, phoneNumber: e.target.value})}
              placeholder="+234 801 234 5678"
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-900/20 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm flex items-start gap-2">
              <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <button
              onClick={onCancel}
              className="flex-1 px-4 py-3 border border-gray-700 text-gray-300 rounded-lg hover:bg-gray-900 transition-colors"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 transition-all shadow-lg"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Verifying...' : 'Continue'}
            </button>
          </div>
        </div>
        
        <div className="mt-6 flex items-start gap-2 text-xs text-gray-500">
          <Shield className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <p>Your data is encrypted and used only for regulatory compliance</p>
        </div>
      </div>
    </div>
  );
};

export default BVNCollectionModal;