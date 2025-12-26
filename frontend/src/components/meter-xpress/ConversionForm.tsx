// File: frontend/src/components/meter-xpress/ConversionForm.tsx
import React, { useState } from 'react';
import { ArrowRight, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';
import { MAPPricingCard } from './MAPPricingCard';

interface ConversionFormProps {
  onComplete: (applicationId: string, formData: any) => void;
}

type ConversionType = 
  | 'postpaid_metered_to_prepaid_metered'
  | 'postpaid_metered_to_unmetered'
  | 'postpaid_unmetered_to_prepaid_metered'
  | 'prepaid_metered_to_unmetered'
  | 'unmetered_to_postpaid_metered';

export const ConversionForm: React.FC<ConversionFormProps> = ({ onComplete }) => {
  const [currentSection, setCurrentSection] = useState<'account' | 'conversion' | 'pricing'>('account');
  const [loading, setLoading] = useState(false);
  const [accountVerified, setAccountVerified] = useState(false);
  
  const [formData, setFormData] = useState({
    // Account Info
    account_number: '',
    meter_number: '',
    
    // Conversion Details
    conversion_from: '',
    conversion_to: '',
    
    // Metering (only if converting TO metered)
    phase: '1 Phase',
    voltage_level: '230V',
    map_vendor: '',
    selectedPricing: null as any
  });

  const conversionMatrix = [
    { from: 'Postpaid Metered', to: 'Prepaid Metered', needsMeter: true, key: 'postpaid_metered_to_prepaid_metered' },
    { from: 'Postpaid Metered', to: 'Unmetered', needsMeter: false, key: 'postpaid_metered_to_unmetered' },
    { from: 'Postpaid Unmetered', to: 'Prepaid Metered', needsMeter: true, key: 'postpaid_unmetered_to_prepaid_metered' },
    { from: 'Prepaid Metered', to: 'Unmetered', needsMeter: false, key: 'prepaid_metered_to_unmetered' },
    { from: 'Unmetered', to: 'Postpaid Metered', needsMeter: true, key: 'unmetered_to_postpaid_metered' }
  ];

  const needsMetering = () => {
    const selected = conversionMatrix.find(c => 
      c.from === formData.conversion_from && c.to === formData.conversion_to
    );
    return selected?.needsMeter || false;
  };

  const validateAccountSection = () => {
    if (!formData.account_number.trim() && !formData.meter_number.trim()) {
        toast.error('Account number OR meter number is required');
        return false;
    }
    
    // ✅ VALIDATE ACCOUNT NUMBER FORMAT IF PROVIDED
    if (formData.account_number.trim()) {
        const accountRegex = /^\d{10}-\d{2}$/;
        if (!accountRegex.test(formData.account_number.trim())) {
        toast.error('Invalid account number format. Expected: 9496632093-01 (10 digits-2 digits)');
        return false;
        }
    }
    
    return true;
    };

  const validateConversionSection = () => {
    if (!formData.conversion_from) {
      toast.error('Please select what you are converting FROM');
      return false;
    }
    if (!formData.conversion_to) {
      toast.error('Please select what you are converting TO');
      return false;
    }
    return true;
  };

  const handleVerifyAccount = async () => {
    if (!validateAccountSection()) return;

    try {
      setLoading(true);
      
      // TODO: Implement actual EKEDC account verification API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setAccountVerified(true);
      toast.success('Account verified successfully!');
      setCurrentSection('conversion');
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
    if (!validateAccountSection() || !validateConversionSection()) {
        toast.error('Please complete all required fields');
        return;
    }

    if (needsMetering() && !formData.map_vendor) {
        toast.error('Please select a MAP vendor');
        return;
    }

    try {
        setLoading(true);

        // Prepare payload matching backend expectations
        const payload = {
        account_number: formData.account_number,
        meter_number: formData.meter_number,
        conversion_from: formData.conversion_from.toLowerCase().replace(' ', '_'),
        conversion_to: formData.conversion_to.toLowerCase().replace(' ', '_'),
        ...(needsMetering() && {
            phase: formData.phase,
            voltage_level: formData.voltage_level,
            map_vendor: formData.map_vendor
        })
        };

        const response = await apiClient.post('/api/v1/meter-xpress/applications/conversion', payload);

        if (response.data.success) {
        toast.success('Conversion application created!');
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
          onClick={() => accountVerified && setCurrentSection('conversion')}
          disabled={!accountVerified}
          className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
            currentSection === 'conversion'
              ? 'bg-blue-600 text-white'
              : accountVerified
              ? 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              : 'bg-gray-800 text-gray-600 cursor-not-allowed'
          }`}
        >
          2. Conversion Type
        </button>
        {needsMetering() && (
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
        )}
      </div>

      {/* Account Verification Section */}
      {currentSection === 'account' && (
        <div className="space-y-6">
          <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <RefreshCw className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-blue-400 font-semibold mb-1">Meter Conversion</h3>
                <p className="text-sm text-gray-300">
                  You're converting your meter type (e.g., from Postpaid to Prepaid). 
                  Provide either your account number OR meter number.
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-xl font-bold text-white">Account Information</h3>

            <div>
              <label className="block text-sm text-gray-400 mb-2">
                EKEDC Account Number
              </label>
              <input
                type="text"
                value={formData.account_number}
                onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="9496632093-01"
                pattern="^\d{10}-\d{2}$"
                disabled={accountVerified}
              />
            </div>

            <div className="text-center text-gray-500 text-sm font-medium">— OR —</div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">
                Current Meter Number
              </label>
              <input
                type="text"
                value={formData.meter_number}
                onChange={(e) => setFormData({ ...formData, meter_number: e.target.value })}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter your meter number"
                disabled={accountVerified}
              />
            </div>

            <p className="text-xs text-gray-500">
              * You must provide at least one: account number OR meter number
            </p>

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
                    <p className="text-sm text-gray-300">You can now select conversion type</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Conversion Type Section */}
      {currentSection === 'conversion' && (
        <div className="space-y-6">
          <h3 className="text-xl font-bold text-white">Select Conversion Type</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Converting FROM *</label>
              <select
                value={formData.conversion_from}
                onChange={(e) => setFormData({ ...formData, conversion_from: e.target.value, conversion_to: '' })}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select current meter type</option>
                <option value="Postpaid Metered">Postpaid Metered</option>
                <option value="Postpaid Unmetered">Postpaid Unmetered</option>
                <option value="Prepaid Metered">Prepaid Metered</option>
                <option value="Unmetered">Unmetered</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Converting TO *</label>
              <select
                value={formData.conversion_to}
                onChange={(e) => setFormData({ ...formData, conversion_to: e.target.value })}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={!formData.conversion_from}
              >
                <option value="">Select target meter type</option>
                {conversionMatrix
                  .filter(c => c.from === formData.conversion_from)
                  .map(c => (
                    <option key={c.key} value={c.to}>{c.to}</option>
                  ))
                }
              </select>
            </div>
          </div>

          {formData.conversion_from && formData.conversion_to && (
            <div className={`rounded-xl p-4 border ${
              needsMetering() 
                ? 'bg-yellow-900/20 border-yellow-500/30' 
                : 'bg-green-900/20 border-green-500/30'
            }`}>
              <div className="flex items-start gap-3">
                {needsMetering() ? (
                  <AlertCircle className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <h4 className={`font-semibold mb-1 ${needsMetering() ? 'text-yellow-400' : 'text-green-400'}`}>
                    {needsMetering() ? 'New Meter Required' : 'No Meter Purchase Needed'}
                  </h4>
                  <p className="text-sm text-gray-300">
                    {needsMetering() 
                      ? 'This conversion requires a new meter. You\'ll need to select a MAP vendor and make payment.'
                      : 'This conversion doesn\'t require a new meter. You can submit for free.'
                    }
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => setCurrentSection('account')}
              className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
            >
              ← Back
            </button>
            {needsMetering() ? (
              <button
                onClick={() => {
                  if (validateConversionSection()) {
                    setCurrentSection('pricing');
                  }
                }}
                className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                Continue to Pricing
                <ArrowRight className="h-5 w-5" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="flex-1 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 text-white font-semibold rounded-lg transition-colors"
              >
                {loading ? 'Submitting...' : 'Submit Conversion Request'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Pricing Section (only if needs metering) */}
      {currentSection === 'pricing' && needsMetering() && (
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
              onClick={() => setCurrentSection('conversion')}
              className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
            >
              ← Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading || !formData.map_vendor}
              className="flex-1 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
            >
              {loading ? 'Creating Application...' : 'Create Conversion Application'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};