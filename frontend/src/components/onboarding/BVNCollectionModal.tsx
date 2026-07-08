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
  // Africa
  { code: 'NG', name: 'Nigeria', dialCode: '+234', idTypes: [
    { value: 'BVN', label: 'BVN', placeholder: '22123456789' },
    { value: 'NIN', label: 'NIN', placeholder: '12345678901' }
  ]},
  { code: 'KE', name: 'Kenya', dialCode: '+254', idTypes: [
    { value: 'NATIONAL_ID', label: 'National ID', placeholder: '12345678' }
  ]},
  { code: 'ZA', name: 'South Africa', dialCode: '+27', idTypes: [
    { value: 'ID_NUMBER', label: 'ID Number', placeholder: '8001015009087' }
  ]},
  { code: 'GH', name: 'Ghana', dialCode: '+233', idTypes: [
    { value: 'GHANA_CARD', label: 'Ghana Card', placeholder: 'GHA-123456789-0' }
  ]},
  { code: 'CM', name: 'Cameroon', dialCode: '+237', idTypes: [
    { value: 'NATIONAL_ID', label: 'National ID', placeholder: '123456789' }
  ]},
  { code: 'RW', name: 'Rwanda', dialCode: '+250', idTypes: [
    { value: 'NATIONAL_ID', label: 'National ID', placeholder: '1234567890123456' }
  ]},
  { code: 'TZ', name: 'Tanzania', dialCode: '+255', idTypes: [
    { value: 'NIDA', label: 'NIDA', placeholder: '12345678-12345-12345-12' }
  ]},
  { code: 'UG', name: 'Uganda', dialCode: '+256', idTypes: [
    { value: 'NATIONAL_ID', label: 'National ID', placeholder: 'CM12345678ABC123' }
  ]},
  { code: 'MW', name: 'Malawi', dialCode: '+265', idTypes: [
    { value: 'NATIONAL_ID', label: 'National ID', placeholder: 'MNE123456' }
  ]},
  { code: 'ZM', name: 'Zambia', dialCode: '+260', idTypes: [
    { value: 'NRC', label: 'NRC', placeholder: '123456/78/9' }
  ]},
  
  // Americas
  { code: 'US', name: 'United States', dialCode: '+1', idTypes: [
    { value: 'SSN', label: 'SSN', placeholder: '123-45-6789' },
    { value: 'DRIVERS_LICENSE', label: 'Driver\'s License', placeholder: 'D1234567' }
  ]},
  { code: 'CA', name: 'Canada', dialCode: '+1', idTypes: [
    { value: 'SIN', label: 'SIN', placeholder: '123-456-789' }
  ]},
  { code: 'BR', name: 'Brazil', dialCode: '+55', idTypes: [
    { value: 'CPF', label: 'CPF', placeholder: '123.456.789-00' }
  ]},
  { code: 'MX', name: 'Mexico', dialCode: '+52', idTypes: [
    { value: 'CURP', label: 'CURP', placeholder: 'ABCD123456HDFABC00' }
  ]},
  
  // Europe
  { code: 'GB', name: 'United Kingdom', dialCode: '+44', idTypes: [
    { value: 'PASSPORT', label: 'Passport', placeholder: '123456789' },
    { value: 'NINO', label: 'National Insurance', placeholder: 'AB123456C' }
  ]},
  { code: 'DE', name: 'Germany', dialCode: '+49', idTypes: [
    { value: 'PERSONALAUSWEIS', label: 'Personalausweis', placeholder: 'L01X00T47' }
  ]},
  { code: 'FR', name: 'France', dialCode: '+33', idTypes: [
    { value: 'CNI', label: 'CNI', placeholder: '123456789012' }
  ]},
  { code: 'ES', name: 'Spain', dialCode: '+34', idTypes: [
    { value: 'DNI', label: 'DNI', placeholder: '12345678A' }
  ]},
  { code: 'IT', name: 'Italy', dialCode: '+39', idTypes: [
    { value: 'CODICE_FISCALE', label: 'Codice Fiscale', placeholder: 'RSSMRA80A01H501U' }
  ]},
  
  // Asia
  { code: 'IN', name: 'India', dialCode: '+91', idTypes: [
    { value: 'AADHAAR', label: 'Aadhaar', placeholder: '1234 5678 9012' },
    { value: 'PAN', label: 'PAN', placeholder: 'ABCDE1234F' }
  ]},
  { code: 'CN', name: 'China', dialCode: '+86', idTypes: [
    { value: 'NATIONAL_ID', label: 'National ID', placeholder: '110101199001011234' }
  ]},
  { code: 'JP', name: 'Japan', dialCode: '+81', idTypes: [
    { value: 'MY_NUMBER', label: 'My Number', placeholder: '123456789012' }
  ]},
  { code: 'SG', name: 'Singapore', dialCode: '+65', idTypes: [
    { value: 'NRIC', label: 'NRIC', placeholder: 'S1234567D' }
  ]},
  { code: 'MY', name: 'Malaysia', dialCode: '+60', idTypes: [
    { value: 'MYKAD', label: 'MyKad', placeholder: '123456-12-1234' }
  ]},
  { code: 'PH', name: 'Philippines', dialCode: '+63', idTypes: [
    { value: 'UMID', label: 'UMID', placeholder: '1234-1234567-1' }
  ]},
  
  // Middle East
  { code: 'AE', name: 'UAE', dialCode: '+971', idTypes: [
    { value: 'EMIRATES_ID', label: 'Emirates ID', placeholder: '784-1234-1234567-1' }
  ]},
  { code: 'SA', name: 'Saudi Arabia', dialCode: '+966', idTypes: [
    { value: 'NATIONAL_ID', label: 'National ID', placeholder: '1234567890' }
  ]},
  
  // Oceania
  { code: 'AU', name: 'Australia', dialCode: '+61', idTypes: [
    { value: 'MEDICARE', label: 'Medicare', placeholder: '1234 56789 0' }
  ]},
  { code: 'NZ', name: 'New Zealand', dialCode: '+64', idTypes: [
    { value: 'DRIVERS_LICENSE', label: 'Driver Licence', placeholder: 'AB123456' }
  ]}
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
    address: '',
    sourceOfFunds: '',
    country: countryCode
  });

  const SOURCE_OF_FUNDS_OPTIONS = [
    { value: 'Employment',        label: 'Employment / Salary' },
    { value: 'Business Income',   label: 'Business Income' },
    { value: 'Savings',           label: 'Personal Savings' },
    { value: 'Investment Returns', label: 'Investment Returns' },
    { value: 'Crypto Trading',    label: 'Crypto Trading Gains' },
    { value: 'Inheritance',       label: 'Inheritance / Gift' },
    { value: 'Other',             label: 'Other' },
  ];
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
    if (!formData.address || formData.address.trim().length < 5) {
      setError('Address is required');
      return false;
    }
    if (!formData.sourceOfFunds) {
      setError('Source of funds is required');
      return false;
    }
    return true;
  };

  const handleSubmit = async () => {
    setError('');
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
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
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Country *</label>
            <div className="relative">
              <select
                value={selectedCountry.code}
                onChange={(e) => handleCountryChange(e.target.value)}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:outline-none appearance-none"
              >
                {COUNTRIES.map(country => (
                  <option key={country.code} value={country.code}>{country.name}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {selectedCountry.idTypes.length > 1 && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">ID Type *</label>
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
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Date of Birth *</label>
            <input
              type="date"
              value={formData.dateOfBirth}
              onChange={(e) => setFormData({...formData, dateOfBirth: e.target.value})}
              max={new Date().toISOString().split('T')[0]}
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Gender *</label>
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
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Phone Number *</label>
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

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Residential Address *</label>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => setFormData({...formData, address: e.target.value})}
              placeholder="Street, City"
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Source of Funds *</label>
            <select
              value={formData.sourceOfFunds}
              onChange={(e) => setFormData({...formData, sourceOfFunds: e.target.value})}
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:outline-none appearance-none"
            >
              <option value="">Select source of funds</option>
              {SOURCE_OF_FUNDS_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
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
          <p>Encrypted & used only for compliance</p>
        </div>
      </div>
    </div>
  );
};

export default BVNCollectionModal;