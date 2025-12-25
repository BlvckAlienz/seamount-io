// File: frontend/src/components/meter-xpress/NewServiceForm.tsx
import React, { useState } from 'react';
import { ArrowRight, MapPin } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';
import { MAPPricingCard } from './MAPPricingCard';

interface NewServiceFormProps {
  onComplete: (applicationId: string, formData: any) => void;
}

export const NewServiceForm: React.FC<NewServiceFormProps> = ({ onComplete }) => {
  const [currentSection, setCurrentSection] = useState<'customer' | 'service' | 'pricing'>('customer');
  const [loading, setLoading] = useState(false);
  
  const [formData, setFormData] = useState({
    // Customer Data
    supply_type: 'Prepaid',
    first_name: '',
    middle_name: '',
    surname: '',
    customer_type: 'Private customers',
    personal_id_type: 'National Identification card',
    date_of_birth: '',
    ownership_status: 'Landlord',
    nationality: 'Nigeria',
    gender: 'Male',
    primary_email: '',
    mobile_number: '',
    phone_2: '',
    
    // Service Point Data
    state: 'Lagos',
    district: '',
    city: '',
    premise_type: 'Flats',
    premise_category: 'Mini-Flat/Self-Contained',
    activity: 'Residential',
    sub_activity: 'Residential Default Value',
    state_of_building: 'Newly built',
    applicant_capacity: 'Owner of the premises',
    landmark: '',
    pole_number: '',
    latitude: null as number | null,
    longitude: null as number | null,
    
    // Metering
    phase: '1 Phase',
    voltage_level: '230V',
    map_vendor: '',
    
    // Pricing (calculated)
    selectedPricing: null as any
  });

  const districts = ['Agbara', 'Ajah', 'Ajele', 'Apapa', 'Festac', 'Ibeju', 'Ijora', 'Island', 'Lekki', 'Mushin', 'Ojo', 'Orile'];
  
  const premiseTypes = ['Banks', 'Bungalows', 'Common Services', 'Duplex', 'Estates', 'Factories', 'Flats', 'Hospitals', 'Hotels', 'Local Council Development Area/ Local Gov', 'Low-cost Housing Scheme', 'Plazas', 'Religious', 'Schools', 'Terrace'];

  const premiseCategories: { [key: string]: string[] } = {
    'Bungalows': ['Clustered Apartments', 'Four Bedrooms with Boys Quarters', 'Mini-Flat/Self-Contained', 'One Bedroom', 'Three Bedrooms', 'Two Bedrooms'],
    'Flats': ['Clustered Apartments', 'Five Bedrooms with Boys Quarters', 'Four Bedrooms with Boys Quarters', 'Mini-Flat/Self-Contained', 'One Bedroom', 'Three Bedrooms', 'Two Bedrooms'],
    'Duplex': ['Clustered Apartments', 'Five Bedrooms with Boys Quarters', 'Four Bedrooms with Boys Quarters', 'Mini-Flat/Self-Contained', 'One Bedroom', 'Three Bedrooms', 'Two Bedrooms'],
    'Terrace': ['Four Bedrooms', 'One Bedroom', 'Three Bedrooms', 'Three Bedrooms & Four Bedrooms with Boy\'s Quarters', 'Two Bedrooms']
  };

  const handlePhaseChange = (phase: string) => {
    setFormData({
      ...formData,
      phase,
      voltage_level: phase === '1 Phase' ? '230V' : '400V',
      map_vendor: '', // Reset vendor selection
      selectedPricing: null
    });
  };

  const handleVendorSelect = (vendor: string, pricing: any) => {
    setFormData({
      ...formData,
      map_vendor: vendor,
      selectedPricing: pricing
    });
  };

  const validateCustomerSection = () => {
    // ✅ NAME VALIDATION
    if (!formData.first_name.trim()) {
        toast.error('First name is required');
        return false;
    }
    if (!formData.surname.trim()) {
        toast.error('Surname is required');
        return false;
    }

    // ✅ EMAIL VALIDATION
    if (!formData.primary_email.trim()) {
        toast.error('Email address is required');
        return false;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.primary_email)) {
        toast.error('Please enter a valid email address');
        return false;
    }

    // ✅ PHONE VALIDATION
    if (!formData.mobile_number.trim()) {
        toast.error('Mobile number is required');
        return false;
    }
    const phoneRegex = /^0\d{10}$/; // Nigerian phone format
    if (!phoneRegex.test(formData.mobile_number.replace(/\s/g, ''))) {
        toast.error('Please enter a valid 11-digit Nigerian phone number');
        return false;
    }

    // ✅ DATE OF BIRTH VALIDATION
    if (!formData.date_of_birth) {
        toast.error('Date of birth is required');
        return false;
    }

    return true;
    };

    const validateServiceSection = () => {
    // ✅ DISTRICT VALIDATION
    if (!formData.district) {
        toast.error('Please select a district');
        return false;
    }

    // ✅ LANDMARK VALIDATION
    if (!formData.landmark.trim()) {
        toast.error('Landmark/address is required');
        return false;
    }
    if (formData.landmark.trim().length < 10) {
        toast.error('Please provide a more detailed landmark description');
        return false;
    }

    // ✅ PREMISE CATEGORY VALIDATION
    if (!formData.premise_category) {
        toast.error('Please select a premise category');
        return false;
    }

    return true;
    };

  const handleSubmit = async () => {
    try {
        setLoading(true);

        // ✅ COMPREHENSIVE VALIDATION
        if (!validateCustomerSection()) {
          setCurrentSection('customer');
          return;
        }

        if (!validateServiceSection()) {
          setCurrentSection('service');
          return;
        }

        if (!formData.map_vendor) {
          toast.error('Please select a MAP vendor');
          setCurrentSection('pricing');
          return;
        }

        const response = await apiClient.post('/api/v1/meter-xpress/applications/new-service', formData);

        if (response.data.success) {
          toast.success('Application created successfully!');
          onComplete(response.data.application_id, formData);
        }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to create application');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Section Tabs */}
      <div className="flex gap-2 border-b border-gray-700 pb-2">
        <button
          onClick={() => setCurrentSection('customer')}
          className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
            currentSection === 'customer'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
          }`}
        >
          1. Customer Details
        </button>
        <button
          onClick={() => setCurrentSection('service')}
          className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
            currentSection === 'service'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
          }`}
        >
          2. Service Point
        </button>
        <button
          onClick={() => setCurrentSection('pricing')}
          className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
            currentSection === 'pricing'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
          }`}
        >
          3. Metering & Pricing
        </button>
      </div>

      {/* Customer Details Section */}
      {currentSection === 'customer' && (
        <div className="space-y-4">
          <h3 className="text-xl font-bold text-white mb-4">Customer Information</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Supply Type *</label>
              <select
                value={formData.supply_type}
                onChange={(e) => setFormData({ ...formData, supply_type: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Prepaid">Prepaid</option>
                <option value="Postpaid KCG">Postpaid KCG</option>
                <option value="Postpaid Non-KCG">Postpaid Non-KCG</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Customer Type *</label>
              <select
                value={formData.customer_type}
                onChange={(e) => setFormData({ ...formData, customer_type: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Private customers">Private customers</option>
                <option value="State Government Agencies">State Government Agencies</option>
                <option value="Federal Government Agencies">Federal Government Agencies</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">First Name *</label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter first name"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Middle Name</label>
              <input
                type="text"
                value={formData.middle_name}
                onChange={(e) => setFormData({ ...formData, middle_name: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter middle name"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Surname *</label>
              <input
                type="text"
                value={formData.surname}
                onChange={(e) => setFormData({ ...formData, surname: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter surname"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">ID Type *</label>
              <select
                value={formData.personal_id_type}
                onChange={(e) => setFormData({ ...formData, personal_id_type: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="National Identification card">National ID</option>
                <option value="Driver's license">Driver's License</option>
                <option value="International Passport">International Passport</option>
                <option value="Voter's Registration card">Voter's Card</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Date of Birth *</label>
              <input
                type="date"
                value={formData.date_of_birth}
                onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Gender *</label>
              <select
                value={formData.gender}
                onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Male">Male</option>
                <option value="Female">Female</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Email Address *</label>
              <input
                type="email"
                value={formData.primary_email}
                onChange={(e) => setFormData({ ...formData, primary_email: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="your.email@example.com"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Mobile Number *</label>
              <input
                type="tel"
                value={formData.mobile_number}
                onChange={(e) => setFormData({ ...formData, mobile_number: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="08012345678"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Ownership Status *</label>
              <select
                value={formData.ownership_status}
                onChange={(e) => setFormData({ ...formData, ownership_status: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Landlord">Landlord</option>
                <option value="Tenant">Tenant</option>
              </select>
            </div>
          </div>

          <button
            onClick={() => {
                if (validateCustomerSection()) {
                  setCurrentSection('service');
                }
            }}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
            >
            Continue to Service Point
            <ArrowRight className="h-5 w-5" />
          </button>
        </div>
      )}

      {/* Service Point Section */}
      {currentSection === 'service' && (
        <div className="space-y-4">
          <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <MapPin className="h-6 w-6 text-blue-400" />
            Service Point Details
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">District *</label>
              <select
                value={formData.district}
                onChange={(e) => setFormData({ ...formData, district: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select district</option>
                {districts.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Premise Type *</label>
              <select
                value={formData.premise_type}
                onChange={(e) => setFormData({ ...formData, premise_type: e.target.value, premise_category: '' })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {premiseTypes.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>

            {premiseCategories[formData.premise_type] && (
              <div>
                <label className="block text-sm text-gray-400 mb-2">Premise Category *</label>
                <select
                  value={formData.premise_category}
                  onChange={(e) => setFormData({ ...formData, premise_category: e.target.value })}
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select category</option>
                  {premiseCategories[formData.premise_type].map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            )}

            <div>
              <label className="block text-sm text-gray-400 mb-2">State of Building *</label>
              <select
                value={formData.state_of_building}
                onChange={(e) => setFormData({ ...formData, state_of_building: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Newly built">Newly built</option>
                <option value="Old / Existing">Old / Existing</option>
                <option value="Renovated">Renovated</option>
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm text-gray-400 mb-2">Landmark / Address *</label>
              <textarea
                value={formData.landmark}
                onChange={(e) => setFormData({ ...formData, landmark: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="Describe your location with nearby landmarks"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Pole Number (Optional)</label>
              <input
                type="text"
                value={formData.pole_number}
                onChange={(e) => setFormData({ ...formData, pole_number: e.target.value })}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Nearest electricity pole number"
              />
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setCurrentSection('customer')}
              className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
            >
              ← Back
            </button>
            <button
              onClick={() => {
                if (validateServiceSection()) {
                  setCurrentSection('pricing');
                }
              }}
              className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              Continue to Pricing
              <ArrowRight className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}

      {/* Pricing Section */}
      {currentSection === 'pricing' && (
        <div className="space-y-6">
          <h3 className="text-xl font-bold text-white mb-4">Metering & Pricing</h3>

          {/* Phase Selection */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">Select Phase Type *</label>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => handlePhaseChange('1 Phase')}
                className={`p-4 rounded-lg border-2 transition-all ${
                  formData.phase === '1 Phase'
                    ? 'bg-blue-600 border-blue-500 text-white'
                    : 'bg-gray-800 border-gray-700 text-gray-300 hover:border-blue-500'
                }`}
              >
                <div className="text-lg font-semibold mb-1">Single Phase</div>
                <div className="text-sm opacity-80">230V - Residential</div>
              </button>
              <button
                onClick={() => handlePhaseChange('3 Phase')}
                className={`p-4 rounded-lg border-2 transition-all ${
                  formData.phase === '3 Phase'
                    ? 'bg-blue-600 border-blue-500 text-white'
                    : 'bg-gray-800 border-gray-700 text-gray-300 hover:border-blue-500'
                }`}
              >
                <div className="text-lg font-semibold mb-1">Three Phase</div>
                <div className="text-sm opacity-80">400V - Commercial</div>
              </button>
            </div>
          </div>

          {/* MAP Pricing Card */}
          <MAPPricingCard
            selectedPhase={formData.phase === '1 Phase' ? '1phase' : '3phase'}
            selectedVendor={formData.map_vendor}
            onVendorSelect={handleVendorSelect}
          />

          <div className="flex gap-3">
            <button
              onClick={() => setCurrentSection('service')}
              className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
            >
              ← Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading || !formData.map_vendor}
              className="flex-1 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
            >
              {loading ? 'Creating Application...' : 'Create Application'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};