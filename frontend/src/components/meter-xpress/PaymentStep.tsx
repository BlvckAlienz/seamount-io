// File: frontend/src/components/meter-xpress/PaymentStep.tsx
import React, { useState, useEffect } from 'react';
import { CreditCard, CheckCircle, ArrowRight, AlertCircle, Receipt } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface PaymentStepProps {
  applicationId: string;
}

export const PaymentStep: React.FC<PaymentStepProps> = ({ applicationId }) => {
  const [application, setApplication] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchApplication();
  }, []);

  const fetchApplication = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/api/v1/meter-xpress/applications/${applicationId}`);
      
      if (response.data.success) {
        setApplication(response.data.application);
      }
    } catch (error) {
      toast.error('Failed to load application details');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitForPayment = async () => {
    try {
      setSubmitting(true);
      
      const response = await apiClient.post(
        `/api/v1/meter-xpress/applications/${applicationId}/submit`
      );

      if (response.data.success && response.data.payment_link) {
        toast.success('Redirecting to payment...');
        
        // Redirect to Paystack
        window.location.href = response.data.payment_link;
      } else {
        toast.error('Failed to initialize payment');
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Payment initialization failed');
    } finally {
      setSubmitting(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-500"></div>
      </div>
    );
  }

  if (!application) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-16 w-16 text-red-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-white mb-2">Application Not Found</h3>
        <p className="text-gray-400">Unable to load application details</p>
      </div>
    );
  }

  const formData = application.form_data || {};

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Receipt className="h-16 w-16 text-green-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-white mb-2">Review & Pay</h2>
        <p className="text-gray-400">Review your application details and proceed to payment</p>
      </div>

      {/* Application Summary */}
      <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-xl p-6 space-y-4">
        <h3 className="text-lg font-bold text-white border-b border-gray-700 pb-2">Application Summary</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-sm text-gray-400">Applicant Name</div>
            <div className="text-white font-medium">
              {formData.first_name} {formData.middle_name} {formData.surname}
            </div>
          </div>

          <div>
            <div className="text-sm text-gray-400">Supply Type</div>
            <div className="text-white font-medium">{formData.supply_type}</div>
          </div>

          <div>
            <div className="text-sm text-gray-400">Email</div>
            <div className="text-white font-medium">{formData.primary_email}</div>
          </div>

          <div>
            <div className="text-sm text-gray-400">Phone Number</div>
            <div className="text-white font-medium">{formData.mobile_number}</div>
          </div>

          <div>
            <div className="text-sm text-gray-400">District</div>
            <div className="text-white font-medium">{formData.district}</div>
          </div>

          <div>
            <div className="text-sm text-gray-400">Premise Type</div>
            <div className="text-white font-medium">{formData.premise_type}</div>
          </div>

          <div>
            <div className="text-sm text-gray-400">Phase Type</div>
            <div className="text-white font-medium">
              {application.phase_type === '1phase' ? 'Single Phase (230V)' : 'Three Phase (400V)'}
            </div>
          </div>

          <div>
            <div className="text-sm text-gray-400">MAP Vendor</div>
            <div className="text-white font-medium">{application.map_vendor}</div>
          </div>
        </div>

        <div className="mt-4">
          <div className="text-sm text-gray-400">Service Address</div>
          <div className="text-white font-medium">{formData.landmark}</div>
        </div>
      </div>

      {/* Pricing Breakdown */}
      <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-6">
        <h3 className="text-lg font-bold text-white mb-4">Payment Breakdown</h3>
        
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-gray-300">MAP Base Price</span>
            <span className="text-white font-medium">
              {formatCurrency(application.map_base_price)}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-gray-300">
              Seamount Service Fee
              <span className="text-xs text-gray-500 ml-2">
                ({application.phase_type === '1phase' ? '60%' : '50%'} markup)
              </span>
            </span>
            <span className="text-white font-medium">
              {formatCurrency(application.service_fee)}
            </span>
          </div>

          <div className="border-t border-gray-600 pt-3 flex justify-between items-center">
            <span className="text-lg font-semibold text-white">Total Amount</span>
            <span className="text-2xl font-bold text-green-400">
              {formatCurrency(application.total_amount)}
            </span>
          </div>
        </div>

        <div className="mt-4 p-3 bg-blue-900/20 rounded-lg">
          <p className="text-xs text-blue-200">
            💡 <strong>What's included:</strong> Meter procurement from {application.map_vendor}, 
            licensed contractor coordination, document verification, installation scheduling, 
            and 6-month post-installation support.
          </p>
        </div>
      </div>

      {/* Service Guarantee */}
      <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-6">
        <h3 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
          <CheckCircle className="h-6 w-6 text-green-400" />
          Seamount Guarantee
        </h3>
        <ul className="space-y-2 text-sm text-gray-300">
          <li className="flex items-start gap-2">
            <span className="text-green-400 mt-1">✓</span>
            <span>Application processed within 48 hours</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-400 mt-1">✓</span>
            <span>Licensed LECAN contractor assigned to your location</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-400 mt-1">✓</span>
            <span>Installation scheduled within 7 business days</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-400 mt-1">✓</span>
            <span>Meter activation support and troubleshooting</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-400 mt-1">✓</span>
            <span>Full refund if installation doesn't complete within 30 days</span>
          </li>
        </ul>
      </div>

      {/* Payment Button */}
      <button
        onClick={handleSubmitForPayment}
        disabled={submitting}
        className="w-full py-4 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 text-lg"
      >
        {submitting ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
            Processing...
          </>
        ) : (
          <>
            <CreditCard className="h-6 w-6" />
            Pay {formatCurrency(application.total_amount)}
            <ArrowRight className="h-6 w-6" />
          </>
        )}
      </button>

      <p className="text-xs text-center text-gray-500">
        Secure payment powered by Paystack. You'll be redirected to complete your payment.
      </p>
    </div>
  );
};