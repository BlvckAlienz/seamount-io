import React, { useState, useCallback } from 'react';
import { Check, AlertCircle, CreditCard, Globe, Smartphone, DollarSign } from 'lucide-react';
import Card from './Card';
import Button from './Button';
import { apiService } from '../services/apiService';

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

      // Initialize Flutterwave payment
      const response = await apiService.initializeFlutterwavePayment({
        amount,
        currency: paymentData.currency,
        email: paymentData.email,
        phone: paymentData.phone,
        name: paymentData.name,
        userId,
        countryCode: paymentData.countryCode,
        redirectUrl: window.location.origin + '/payment/callback'
      });

      if (response.success) {
        setReference(response.reference);
        setStep('processing');
        
        // Open Flutterwave checkout in a new window
        window.open(response.paymentLink, '_blank');
        
        // Start polling for payment completion
        startPollingPaymentStatus(response.reference);
      } else {
        throw new Error('Failed to initialize payment');
      }
    } catch (err) {
      console.error('Payment initialization failed:', err);
      setError(err instanceof Error ? err.message : 'Payment initialization failed');
      setStep('error');
    } finally {
      setLoading(false);
    }
  };

  const startPollingPaymentStatus = (ref: string) => {
    let attempts = 0;
    const maxAttempts = 20; // Poll for max 5 minutes (15s × 20)
    
    const pollInterval = setInterval(async () => {
      attempts++;
      
      try {
        // Check payment status
        const result = await apiService.verifyFlutterwavePayment(ref);
        
        if (result.success) {
          // Payment successful
          clearInterval(pollInterval);
          setTransactionDetails(result.transaction);
          setStep('success');
          onComplete(result);
        } else if (attempts >= maxAttempts) {
          // Max polling attempts reached
          clearInterval(pollInterval);
          setError('Payment verification timed out. Please check your Flutterwave dashboard.');
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
    }, 15000); // Check every 15 seconds
    
    // Store the interval ID for cleanup
    return () => clearInterval(pollInterval);
  };

  const resetPaymentFlow = () => {
    setStep('details');
    setError(null);
    setLoading(false);
    setReference(null);
    setTransactionDetails(null);
  };

  // Generate step content
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
                  <input
                    type="number"
                    value={paymentData.amount}
                    onChange={handleInputChange('amount')}
                    placeholder="Amount"
                    className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Country</label>
                <div className="relative">
                  <Globe className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                  <select
                    value={paymentData.countryCode}
                    onChange={handleInputChange('countryCode')}
                    className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="NG">Nigeria (NGN)</option>
                    <option value="KE">Kenya (KES)</option>
                    <option value="ZA">South Africa (ZAR)</option>
                    <option value="GH">Ghana (GHS)</option>
                    <option value="UG">Uganda (UGX)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Email</label>
                <input
                  type="email"
                  value={paymentData.email}
                  onChange={handleInputChange('email')}
                  placeholder="Your email address"
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Phone Number (Optional)</label>
                <div className="relative">
                  <Smartphone className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                  <input
                    type="tel"
                    value={paymentData.phone}
                    onChange={handleInputChange('phone')}
                    placeholder="Your phone number"
                    className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Full Name (Optional)</label>
              <input
                type="text"
                value={paymentData.name}
                onChange={handleInputChange('name')}
                placeholder="Your full name"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
              <div className="flex items-center mb-2">
                <CreditCard className="h-5 w-5 text-blue-400 mr-2" />
                <span className="text-white font-medium">Flutterwave Secure Payment</span>
              </div>
              <p className="text-sm text-gray-300">
                Your payment is secured by Flutterwave. We support multiple payment methods including cards, 
                bank transfers, and mobile money across Africa.
              </p>
            </div>

            <div className="flex space-x-4">
              {onCancel && (
                <Button 
                  variant="secondary" 
                  onClick={onCancel}
                  className="flex-1"
                >
                  Cancel
                </Button>
              )}
              <Button
                onClick={initializePayment}
                loading={loading}
                disabled={!paymentData.amount || !paymentData.email}
                className="flex-1 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700"
              >
                Proceed to Payment
              </Button>
            </div>
          </div>
        );

      case 'processing':
        return (
          <div className="text-center py-8">
            <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
            <h3 className="text-xl font-bold text-white mb-2">Processing Your Payment</h3>
            <p className="text-gray-300 mb-6">
              Please complete your payment in the Flutterwave checkout window.
            </p>
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 mb-6">
              <p className="text-sm text-blue-400">
                If you've completed payment but aren't redirected automatically,
                click the button below to verify your payment status.
              </p>
            </div>
            {reference && (
              <div className="flex space-x-4 justify-center">
                <Button
                  onClick={() => startPollingPaymentStatus(reference)}
                  variant="secondary"
                >
                  Check Payment Status
                </Button>
                <Button
                  onClick={resetPaymentFlow}
                >
                  Start Over
                </Button>
              </div>
            )}
          </div>
        );

      case 'success':
        return (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <Check className="h-8 w-8 text-green-500" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Payment Successful!</h3>
            <p className="text-gray-300 mb-6">
              Your payment has been processed successfully.
            </p>
            <div className="bg-gray-800/50 rounded-lg p-4 mb-6 text-left">
              <div className="grid grid-cols-2 gap-2">
                <div className="text-gray-400">Amount:</div>
                <div className="text-white text-right">{transactionDetails?.amount} {transactionDetails?.currency || paymentData.currency}</div>
                <div className="text-gray-400">Reference:</div>
                <div className="text-white text-right">{reference}</div>
                <div className="text-gray-400">Status:</div>
                <div className="text-green-400 text-right">Completed</div>
              </div>
            </div>
            <Button onClick={resetPaymentFlow}>
              Make Another Payment
            </Button>
          </div>
        );

      case 'error':
        return (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <AlertCircle className="h-8 w-8 text-red-500" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Payment Failed</h3>
            <p className="text-red-400 mb-6">
              {error || 'An error occurred during payment processing.'}
            </p>
            <Button onClick={resetPaymentFlow}>
              Try Again
            </Button>
          </div>
        );
    }
  };

  return (
    <Card>
      <h2 className="text-2xl font-bold text-white mb-6">
        {step === 'details' && 'Payment Details'}
        {step === 'processing' && 'Processing Payment'}
        {step === 'success' && 'Payment Complete'}
        {step === 'error' && 'Payment Failed'}
      </h2>
      {renderStepContent()}
    </Card>
  );
};

export default FlutterwavePayment;