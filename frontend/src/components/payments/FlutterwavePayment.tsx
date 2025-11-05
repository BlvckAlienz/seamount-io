import React, { useState } from 'react';
import { Check, AlertCircle, Globe, DollarSign } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
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
  const [paymentData, setPaymentData] = useState<PaymentData>({
    amount: '',
    currency: 'NGN',
    email: '',
    countryCode: 'NG',
  });

  const handleInputChange = (field: keyof PaymentData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setPaymentData(prev => ({ ...prev, [field]: e.target.value }));

    if (field === 'countryCode') {
      const countryCurrencies: Record<string, string> = {
        'NG': 'NGN', 'KE': 'KES', 'ZA': 'ZAR', 'GH': 'GHS', 'UG': 'UGX',
      };
      const newCurrency = countryCurrencies[e.target.value] || 'USD';
      setPaymentData(prev => ({ ...prev, currency: newCurrency }));
    }
  };

  const initializePayment = async () => {
    setLoading(true);
    setError(null);
    try {
      const amount = parseFloat(paymentData.amount);
      if (isNaN(amount) || amount <= 0) throw new Error('Please enter a valid amount');
      if (!paymentData.email) throw new Error('Email is required');
      
      const response = await apiClient.post(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/payments/initialize-deposit`, {
        amount,
        currency: paymentData.currency,
        email: paymentData.email,
      });

      if (response.data && response.data.payment_link) {
        setStep('processing');
        window.open(response.data.payment_link, '_blank');
      } else {
        throw new Error(response.data.message || 'Failed to initialize payment');
      }
    } catch (err) {
      const errorMessage = (err as any).response?.data?.detail || (err instanceof Error ? err.message : 'Payment initialization failed');
      setError(errorMessage);
      setStep('error');
    } finally {
      setLoading(false);
    }
  };

  const resetPaymentFlow = () => {
    setStep('details');
    setError(null);
  };

  const renderStepContent = () => {
    switch (step) {
      case 'details':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Amount</label>
                <div className="relative"><DollarSign className="absolute left-3 top-3 h-5 w-5 text-gray-400" /><input type="number" value={paymentData.amount} onChange={handleInputChange('amount')} placeholder="0.00" className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-600 rounded-lg" required /></div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Country</label>
                <div className="relative"><Globe className="absolute left-3 top-3 h-5 w-5 text-gray-400" /><select value={paymentData.countryCode} onChange={handleInputChange('countryCode')} className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-600 rounded-lg"><option value="NG">Nigeria (NGN)</option><option value="KE">Kenya (KES)</option><option value="ZA">South Africa (ZAR)</option><option value="GH">Ghana (GHS)</option><option value="UG">Uganda (UGX)</option></select></div>
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
            <h3 className="text-xl font-bold text-white mb-2">Processing Payment</h3>
            <p className="text-gray-300">Please complete your payment in the new window. This window will update automatically upon completion.</p>
          </div>
        );
      case 'success':
        return (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6"><Check className="h-8 w-8 text-green-500" /></div>
            <h3 className="text-xl font-bold text-white mb-2">Payment Successful!</h3>
            <p className="text-gray-300 mb-6">Your deposit is confirmed and USDS has been minted to your wallet.</p>
            <Button onClick={() => onComplete(true)}>Go to Dashboard</Button>
          </div>
        );
      case 'error':
        return (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6"><AlertCircle className="h-8 w-8 text-red-500" /></div>
            <h3 className="text-xl font-bold text-white mb-2">Payment Failed</h3>
            <p className="text-red-400 mb-6">{error || 'An unexpected error occurred.'}</p>
            <Button onClick={resetPaymentFlow}>Try Again</Button>
          </div>
        );
    }
  };

  return (
    <Card>
      <h2 className="text-2xl font-bold text-white mb-6">
        {step === 'details' && 'Fiat Deposit via Flutterwave'}
        {step === 'processing' && 'Awaiting Payment Confirmation'}
        {step === 'success' && 'Deposit Complete'}
        {step === 'error' && 'Payment Error'}
      </h2>
      {renderStepContent()}
    </Card>
  );
};

export default FlutterwavePayment;