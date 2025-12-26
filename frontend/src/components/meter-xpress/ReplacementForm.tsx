// File: frontend/src/components/meter-xpress/ReplacementForm.tsx
import React, { useState } from 'react';
import { ArrowRight, AlertCircle, CheckCircle } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';
import { MAPPricingCard } from './MAPPricingCard';

interface ReplacementFormProps {
  onComplete: (applicationId: string, formData: any) => void;
}

export const ReplacementForm: React.FC<ReplacementFormProps> = ({ onComplete }) => {
  const [currentSection, setCurrentSection] = useState<'account' | 'details' | 'pricing'>('account');
  const [loading, setLoading] = useState(false);
  const [accountVerified, setAccountVerified] = useState(false);
  
  const [formData, setFormData] = useState({
    // Account Info
    meter_number: '',
    
    // Building Details
    state_of_building: 'Old / Existing',
    applicant_capacity: 'Owner of the premises',
    
    // Metering
    phase: '1 Phase',
    voltage_level: '230V',
    map_vendor: '',
    
    // Pricing
    selectedPricing: null as any
  });

  const validateAccountSection = () => {
    if (!formData.meter_number.trim()) {
      toast.error('Meter number is required');
      return false;
    }
    return true;
  };

  const validateDetailsSection = () => {
    if (!formData.state_of_building) {
      toast.error('Please select state of building');
      return false;
    }
    if (!formData.applicant_capacity) {
      toast.error('Please select applicant capacity');
      return false;
    }
    return true;
  };

  const handleVerifyAccount = async () => {
    if (!validateAccountSection()) return;

    try {
      setLoading(true);
      
      // TODO: Implement actual EKEDC account verification API
      // For now, simulate verification
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setAccountVerified(true);
      toast.success('Account verified successfully!');
      setCurrentSection('details');
    } catch (error) {
      toast.error('Account verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePhaseChange = (phase: string) => {
    setFormData({
      ...formData,
      phase,
      voltage_level: phase === '1 Phase' ? '230V' : '400V',
      map_vendor: '',
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

  const handleSubmit = async () => {
    if (!validateAccountSection() || !validateDetailsSection()) {
        toast.error('Please complete all required fields');
        return;
    }

    if (!formData.map_vendor) {
        toast.error('Please select a MAP vendor');
        return;
    }

    try {
        setLoading(true);

        // Prepare payload matching backend expectations
        const payload = {
          account_number: formData.meter_number, // Map meter_number to account_number
          state_of_building: formData.state_of_building,
          applicant_capacity: formData.applicant_capacity,
          phase: formData.phase,
          voltage_level: formData.voltage_level,
          map_vendor: formData.map_vendor
        };

        const response = await apiClient.post('/api/v1/meter-xpress/applications/replacement', payload);

        if (response.data.success) {
        toast.success('Replacement application created!');
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
          onClick={() => setCurrentSection('account')}
          disabled={!accountVerified && currentSection !== 'account'}
          className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
            currentSection === 'account'
              ? 'bg-blue-600 text-white'
              : accountVerified
              ? 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              : 'bg-gray-800 text-gray-600 cursor-not-allowed'
          }`}
        >
          1. Account Verification {accountVerified && '✓'}
        </button>
        <button
          onClick={() => accountVerified && setCurrentSection('details')}
          disabled={!accountVerified}
          className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
            currentSection === 'details'
              ? 'bg-blue-600 text-white'
              : accountVerified
              ? 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              : 'bg-gray-800 text-gray-600 cursor-not-allowed'
          }`}
        >
          2. Building Details
        </button>
        <button
          onClick={() => accountVerified && setCurrentSection('pricing')}
          disabled={!accountVerified}
          className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
            currentSection === 'pricing'
              ? 'bg-blue-600 text-white'
              : accountVerified
              ? 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              : 'bg-gray-800 text-gray-600 cursor-not-allowed'
          }`}
        >
          3. Metering & Pricing
        </button>
      </div>

      {/* Account Verification Section */}
      {currentSection === 'account' && (
        <div className="space-y-6">
          <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-yellow-400 font-semibold mb-1">Meter Replacement</h3>
                <p className="text-sm text-gray-300">
                  You're applying for a replacement meter because your previous meter is faulty. 
                  Please provide your existing account details.
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-xl font-bold text-white">Account Information</h3>

            <div>
              <label className="block text-sm text-gray-400 mb-2">
                Faulty Meter Number *
              </label>
              <input
                type="text"
                value={formData.meter_number}
                onChange={(e) => setFormData({ ...formData, meter_number: e.target.value })}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter your meter number"
                disabled={accountVerified}
              />
              <p className="text-xs text-gray-500 mt-1">
                This is the meter number of the faulty meter you want to replace
              </p>
            </div>

            {!accountVerified ? (
              <button
                onClick={handleVerifyAccount}
                disabled={loading}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    Verifying...
                  </>
                ) : (
                  <>
                    Verify Account & Continue
                    <ArrowRight className="h-5 w-5" />
                  </>
                )}
              </button>
            ) : (
              <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <CheckCircle className="h-6 w-6 text-green-400" />
                  <div>
                    <h4 className="text-green-400 font-semibold">Account Verified</h4>
                    <p className="text-sm text-gray-300">You can now proceed to building details</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Building Details Section */}
      {currentSection === 'details' && (
        <div className="space-y-4">
          <h3 className="text-xl font-bold text-white">Building Details</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                State of Building *
              </label>
              <select
                value={formData.state_of_building}
                onChange={(e) => setFormData({ ...formData, state_of_building: e.target.value })}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Newly built">Newly built</option>
                <option value="Old / Existing">Old / Existing</option>
                <option value="Renovated">Renovated</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">
                Applicant Capacity *
              </label>
              <select
                value={formData.applicant_capacity}
                onChange={(e) => setFormData({ ...formData, applicant_capacity: e.target.value })}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Owner of the premises">Owner of the premises</option>
                <option value="An employee to the owner of the premises">Employee to the owner</option>
                <option value="Authorized agent of the owner of the premises">Authorized agent</option>
                <option value="Consultant">Consultant</option>
                <option value="Electrical Contractor">Electrical Contractor</option>
              </select>
            </div>
          </div>

          <div className="flex gap-3 mt-6">
            <button
              onClick={() => setCurrentSection('account')}
              className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
            >
              ← Back
            </button>
            <button
              onClick={() => {
                if (validateDetailsSection()) {
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
          <h3 className="text-xl font-bold text-white">Metering & Pricing</h3>

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
              onClick={() => setCurrentSection('details')}
              className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
            >
              ← Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading || !formData.map_vendor}
              className="flex-1 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
            >
              {loading ? 'Creating Application...' : 'Create Replacement Application'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};