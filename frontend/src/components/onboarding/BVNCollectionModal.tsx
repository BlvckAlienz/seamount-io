import React, { useState, useEffect } from 'react';
import { AlertCircle, Shield, Globe, ChevronDown } from 'lucide-react';

interface IDType {
  value: string;
  label: string;
  placeholder: string;
}

interface CountryConfig {
  code: string;
  name: string;
  dialCode: string;
  idTypes: IDType[];
}

const COUNTRIES: CountryConfig[] = [
  {
    code: 'NG',
    name: 'Nigeria',
    dialCode: '+234',
    idTypes: [
      { value: 'BVN', label: 'BVN (Bank Verification Number)', placeholder: '22123456789' },
      { value: 'NIN', label: 'NIN (National ID)', placeholder: '12345678901' }
    ]
  },
  {
    code: 'KE',
    name: 'Kenya',
    dialCode: '+254',
    idTypes: [
      { value: 'NATIONAL_ID', label: 'National ID', placeholder: '12345678' }
    ]
  },
  {
    code: 'ZA',
    name: 'South Africa',
    dialCode: '+27',
    idTypes: [
      { value: 'ID_NUMBER', label: 'ID Number', placeholder: '8001015009087' }
    ]
  },
  {
    code: 'GH',
    name: 'Ghana',
    dialCode: '+233',
    idTypes: [
      { value: 'GHANA_CARD', label: 'Ghana Card', placeholder: 'GHA-123456789-0' }
    ]
  },
  {
    code: 'CM',
    name: 'Cameroon',
    dialCode: '+237',
    idTypes: [
      { value: 'NATIONAL_ID', label: 'National ID Card', placeholder: '123456789' }
    ]
  },
  {
    code: 'RW',
    name: 'Rwanda',
    dialCode: '+250',
    idTypes: [
      { value: 'NATIONAL_ID', label: 'National ID', placeholder: '1234567890123456' }
    ]
  },
  {
    code: 'TZ',
    name: 'Tanzania',
    dialCode: '+255',
    idTypes: [
      { value: 'NIDA', label: 'NIDA Number', placeholder: '12345678-12345-12345-12' }
    ]
  },
  {
    code: 'UG',
    name: 'Uganda',
    dialCode: '+256',
    idTypes: [
      { value: 'NATIONAL_ID', label: 'National ID', placeholder: 'CM12345678ABC123' }
    ]
  },
  {
    code: 'MW',
    name: 'Malawi',
    dialCode: '+265',
    idTypes: [
      { value: 'NATIONAL_ID', label: 'National ID', placeholder: 'MNE123456' }
    ]
  },
  {
    code: 'ZM',
    name: 'Zambia',
    dialCode: '+260',
    idTypes: [
      { value: 'NRC', label: 'NRC Number', placeholder: '123456/78/9' }
    ]
  },
  {
    code: 'US',
    name: 'United States',
    dialCode: '+1',
    idTypes: [
      { value: 'SSN', label: 'Social Security Number', placeholder: '123-45-6789' },
      { value: 'DRIVERS_LICENSE', label: 'Driver\'s License', placeholder: 'D1234567' }
    ]
  },
  {
    code: 'GB',
    name: 'United Kingdom',
    dialCode: '+44',
    idTypes: [
      { value: 'PASSPORT', label: 'Passport Number', placeholder: '123456789' },
      { value: 'DRIVERS_LICENSE', label: 'Driving Licence', placeholder: 'MORGA753116SM9IJ' }
    ]
  },
  {
    code: 'IN',
    name: 'India',
    dialCode: '+91',
    idTypes: [
      { value: 'AADHAAR', label: 'Aadhaar Number', placeholder: '1234 5678 9012' },
      { value: 'PAN', label: 'PAN Card', placeholder: 'ABCDE1234F' }
    ]
  }
];

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
  const [selectedCountry, setSelectedCountry] = useState<CountryConfig>(
    COUNTRIES.find(c => c.code === countryCode) || COUNTRIES[0]
  );
  const [formData, setFormData] = useState({
    idType: '',
    idNumber: '',
    dateOfBirth: '',
    gender: '',
    phoneNumber: '',
    country: countryCode
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (selectedCountry.idTypes.length === 1) {
      setFormData(prev => ({ ...prev, idType: selectedCountry.idTypes[0].value }));
    }
  }, [selectedCountry]);

  const handleCountryChange = (code: string) => {
    const country = COUNTRIES.find(c => c.code === code);
    if (country) {
      setSelectedCountry(country);
      setFormData(prev => ({ 
        ...prev, 
        country: code,
        idType: country.idTypes.length === 1 ? country.idTypes[0].value : '',
        idNumber: ''
      }));
    }
  };

  const selectedIDType = selectedCountry.idTypes.find(id => id.value === formData.idType);

  const validateForm = () => {
    if (!formData.idNumber) {
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
      // Format phone with country code
      const fullPhone = formData.phoneNumber.startsWith('+') 
        ? formData.phoneNumber 
        : `${selectedCountry.dialCode}${formData.phoneNumber.replace(/^0+/, '')}`;

      await onComplete({
        ...formData,
        phoneNumber: fullPhone
      });
    } catch (err: any) {
      setError(err.message || 'Verification failed');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-2xl p-8 max-w-md w-full mx-4 border border-gray-700 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-blue-500/20 rounded-full flex items-center justify-center">
            <Globe className="h-6 w-6 text-blue-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Identity Verification</h2>
            <p className="text-gray-400 text-sm">Complete your profile</p>
          </div>
        </div>
        
        <div className="space-y-4">
          {/* Country Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Country *
            </label>
            <div className="relative">
              <select
                value={selectedCountry.code}
                onChange={(e) => handleCountryChange(e.target.value)}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:outline-none appearance-none"
              >
                {COUNTRIES.map(country => (
                  <option key={country.code} value={country.code}>
                    {country.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* ID Type */}
          {selectedCountry.idTypes.length > 1 && (
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
                {selectedCountry.idTypes.map(id => (
                  <option key={id.value} value={id.value}>{id.label}</option>
                ))}
              </select>
            </div>
          )}
          
          {/* ID Number */}
          {(formData.idType || selectedCountry.idTypes.length === 1) && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {selectedIDType?.label || selectedCountry.idTypes[0].label} *
              </label>
              <input
                type="text"
                value={formData.idNumber}
                onChange={(e) => setFormData({...formData, idNumber: e.target.value})}
                placeholder={selectedIDType?.placeholder || selectedCountry.idTypes[0].placeholder}
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
            <div className="flex gap-2">
              <div className="w-24 px-3 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white text-center">
                {selectedCountry.dialCode}
              </div>
              <input
                type="tel"
                value={formData.phoneNumber}
                onChange={(e) => setFormData({...formData, phoneNumber: e.target.value})}
                placeholder="801 234 5678"
                className="flex-1 px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {error && (
            <div className="bg-red-900/20 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm flex items-start gap-2">
              <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

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
              {isSubmitting ? 'Submitting...' : 'Continue'}
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