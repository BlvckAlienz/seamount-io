import React, { useState } from 'react';
import { Send, DollarSign, Globe, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/config/api';

interface CrossBorderPaymentProps {
  userId: string;
  onComplete?: (result: any) => void;
  onCancel?: () => void;
}

const CrossBorderPayment: React.FC<CrossBorderPaymentProps> = ({
  userId,
  onComplete,
  onCancel
}) => {
  const [amount, setAmount] = useState('');
  const [receiverAddress, setReceiverAddress] = useState('');
  const [memo, setMemo] = useState('');
  const [status, setStatus] = useState<'idle' | 'executing' | 'complete' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || !receiverAddress) {
      setError('Amount and recipient address are required.');
      return;
    }
    setStatus('executing');
    setError(null);

    try {
      // The API call is now explicit and absolute.
      const response = await apiClient.post(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/payments/p2p`, {
        recipient_address: receiverAddress,
        amount: parseFloat(amount),
        memo: memo,
      });
      
      setStatus('complete');
      if (onComplete) onComplete(response.data);

    } catch (err) {
      const errorMessage = (err as any).response?.data?.detail || (err instanceof Error ? err.message : 'Payment failed');
      setError(errorMessage);
      setStatus('error');
    }
  };

  const resetForm = () => {
    setAmount('');
    setReceiverAddress('');
    setMemo('');
    setStatus('idle');
  };

  if (status === 'complete') {
    return (
      <Card>
        <div className="text-center py-8">
          <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">Transfer Complete</h3>
          <p className="text-green-400 mb-6">Your cross-border transfer has been successfully processed.</p>
          <Button onClick={resetForm}>Send Another Payment</Button>
        </div>
      </Card>
    );
  }

  if (status === 'error') {
     return (
      <Card>
        <div className="text-center py-8">
          <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">Transfer Failed</h3>
          <p className="text-red-400 mb-6">{error}</p>
          <Button onClick={resetForm}>Try Again</Button>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center space-x-3 mb-6">
        <Globe className="h-5 w-5 text-purple-500" />
        <h2 className="text-xl font-bold text-white">Cross-Border Payment</h2>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Recipient Address</label>
          <input type="text" value={receiverAddress} onChange={(e) => setReceiverAddress(e.target.value)} placeholder="Algorand address" className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg" required/>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Amount (USDS)</label>
          <div className="relative"><DollarSign className="absolute left-3 top-3 text-gray-400" /><input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" className="w-full pl-8 pr-4 py-3 bg-gray-700 border border-gray-600 rounded-lg" required/></div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Memo (Optional)</label>
          <textarea value={memo} onChange={(e) => setMemo(e.target.value)} placeholder="Add a note" className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg resize-none" rows={2}/>
        </div>
        <div className="flex space-x-4 pt-2">
          {onCancel && <Button variant="secondary" onClick={onCancel} className="flex-1">Cancel</Button>}
          <Button type="submit" className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600" icon={Send} loading={status === 'executing'}>Send Payment</Button>
        </div>
      </form>
    </Card>
  );
};

export default CrossBorderPayment;