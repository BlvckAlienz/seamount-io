import React, { useState } from 'react';
import { Check, AlertCircle, CreditCard, Globe, Smartphone, DollarSign } from 'lucide-react';

// --- CORRECTED IMPORT PATHS ---
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { apiClient } from '@/config/api';

interface FlutterwavePaymentProps {
  userId: string;
  onComplete: (result: any) => void;
  onCancel?: () => void;
}

interface PaymentData {
  amount: string;
  currency: string;
  email: string;
  phone: string;
  name: string;
  countryCode: string;
}

const FlutterwavePayment: React.FC<FlutterwavePaymentProps> = ({
  userId,
  onComplete,
  onCancel
}) => {
  const [step, setStep] = useState<'details' | 'processing' | 'success' | 'error'>('details');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [reference, setReference] = useState<string | null>(null);
  const [paymentData, setPaymentData] = useState<PaymentData>({
    amount: '',
    currency: 'NGN', // Default to Nigerian Naira
    email: '',
    phone: '',
    name: '',
    countryCode: 'NG', // Default to Nigeria
  });
  const [transactionDetails, setTransactionDetails] = useState<any>(null);

  const handleInputChange = (field: keyof PaymentData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setPaymentData(prev => ({ ...prev, [field]: e.target.value }));

    // Update currency based on country code
    if (field === 'countryCode') {
      const countryCurrencies: Record<string, string> = {
        'NG': 'NGN',
        'KE': 'KES',
        'ZA': 'ZAR',
        'GH': 'GHS',
        'UG': 'UGX',
      };
      
      const newCurrency = countryCurrencies[e.target.value] || 'USD';
      setPaymentData(prev => ({ ...prev, currency: newCurrency }));
    }
  };

  const initializePayment = async () => {
    setLoading(true);
    setError(null);
    
    try {
      if (!paymentData.amount || !paymentData.email) {
        throw new Error('Amount and email are required');
      }

      const amount = parseFloat(paymentData.amount);
      if (isNaN(amount) || amount <= 0) {
        throw new Error('Please enter a valid amount');
      }

      // Initialize Flutterwave payment via our backend
      const response = await apiClient.post('/api/v1/payments/initialize-deposit', {
        amount,
        currency: paymentData.currency,
        email: paymentData.email,
        phone: paymentData.phone,
        name: paymentData.name,
      });

      if (response.data && response.data.payment_link) {
        setReference(response.data.transaction_id);
        setStep('processing');
        
        // Open Flutterwave checkout in a new window
        window.open(response.data.payment_link, '_blank');
        
        // Polling is a fallback; webhooks are the primary method.
        // startPollingPaymentStatus(response.data.transaction_id);
      } else {
        throw new Error(response.data.message || 'Failed to initialize payment');
      }
    } catch (err) {
      console.error('Payment initialization failed:', err);
      const errorMessage = (err as any).response?.data?.detail || (err instanceof Error ? err.message : 'Payment initialization failed');
      setError(errorMessage);
      setStep('error');
    } finally {
      setLoading(false);
    }
  };

  // Note: Polling is generally not recommended for production.
  // The primary method should be a webhook from Flutterwave to your backend.
  // This is a client-side fallback.
  const startPollingPaymentStatus = (ref: string) => {
    let attempts = 0;
    const maxAttempts = 20; // Poll for max 5 minutes (15s × 20)
    
    const pollInterval = setInterval(async () => {
      attempts++;
      
      try {
        // Your backend should have a route to verify the payment
        const result = await apiClient.post('/api/v1/payments/verify-deposit', { reference: ref });
        
        if (result.data.verified) {
          clearInterval(pollInterval);
          setTransactionDetails(result.data.transaction);
          setStep('success');
          onComplete(result.data);
        } else if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setError('Payment verification timed out. Please check your dashboard or contact support.');
          setStep('error');
        }
      } catch (err) {
        console.error('Payment verification error:', err);
        if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setError('Payment verification failed. Please contact support.');
          setStep('error');
        }
      }
    }, 15000);
  };

  const resetPaymentFlow = () => {
    setStep('details');
    setError(null);
    setLoading(false);
    setReference(null);
    setTransactionDetails(null);
  };

  const renderStepContent = () => {
    switch (step) {
      case 'details':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Amount</label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                  <input type="number" value={paymentData.amount} onChange={handleInputChange('amount')} placeholder="0.00" className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-600 rounded-lg" required />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Country</label>
                <div className="relative">
                  <Globe className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                  <select value={paymentData.countryCode} onChange={handleInputChange('countryCode')} className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-600 rounded-lg">
                    <option value="NG">Nigeria (NGN)</option>
                    <option value="KE">Kenya (KES)</option>
                    <option value="ZA">South Africa (ZAR)</option>
                    <option value="GH">Ghana (GHS)</option>
                    <option value="UG">Uganda (UGX)</option>
                  </select>
                </div>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Email</label>
              <input type="email" value={paymentData.email} onChange={handleInputChange('email')} placeholder="your@email.com" className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg" required />
            </div>
            <div className="flex space-x-4">
              {onCancel && <Button variant="secondary" onClick={onCancel} className="flex-1">Cancel</Button>}
              <Button onClick={initializePayment} loading={loading} disabled={!paymentData.amount || !paymentData.email} className="flex-1 bg-gradient-to-r from-green-600 to-blue-600">Proceed to Payment</Button>
            </div>
          </div>
        );
      case 'processing':
        return (
          <div className="text-center py-8">
            <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
            <h3 className="text-xl font-bold text-white mb-2">Processing Your Payment</h3>
            <p className="text-gray-300">Please complete your payment in the Flutterwave checkout window.</p>
          </div>
        );
      case 'success':
        return (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6"><Check className="h-8 w-8 text-green-500" /></div>
            <h3 className="text-xl font-bold text-white mb-2">Payment Successful!</h3>
            <p className="text-gray-300 mb-6">Your payment has been processed and USDS has been minted to your wallet.</p>
            <Button onClick={onComplete}>Go to Dashboard</Button>
          </div>
        );
      case 'error':
        return (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6"><AlertCircle className="h-8 w-8 text-red-500" /></div>
            <h3 className="text-xl font-bold text-white mb-2">Payment Failed</h3>
            <p className="text-red-400 mb-6">{error || 'An error occurred during payment processing.'}</p>
            <Button onClick={resetPaymentFlow}>Try Again</Button>
          </div>
        );
    }
  };

  return (
    <Card>
      <h2 className="text-2xl font-bold text-white mb-6">
        {step === 'details' && 'Fiat Deposit via Flutterwave'}
        {step === 'processing' && 'Processing Payment'}
        {step === 'success' && 'Payment Complete'}
        {step === 'error' && 'Payment Failed'}
      </h2>
      {renderStepContent()}
    </Card>
  );
};

export default FlutterwavePayment;```