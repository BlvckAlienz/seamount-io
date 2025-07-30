// File Location: frontend/src/components/payments/P2PPayment.tsx
// Description: The definitive, corrected, and production-ready P2P payment component.

import React, { useState } from 'react';
import { Send, DollarSign, Loader2, CheckCircle, AlertCircle } from 'lucide-react';

// --- CORRECTED IMPORT PATHS ---
// Using robust, absolute paths with the '@' alias from vite.config.ts
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { apiClient } from '@/config/api';

interface P2PPaymentProps {
  userId: string;
  onComplete?: (result: any) => void;
  onCancel?: () => void;
}

const P2PPayment: React.FC<P2PPaymentProps> = ({
  userId,
  onComplete,
  onCancel
}) => {
  const [amount, setAmount] = useState('');
  const [receiverAddress, setReceiverAddress] = useState('');
  const [memo, setMemo] = useState('');
  const [status, setStatus] = useState<'idle' | 'executing' | 'complete' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [transactionResult, setTransactionResult] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || !receiverAddress) {
      setError('Amount and recipient address are required.');
      return;
    }
    setStatus('executing');
    setError(null);
    try {
      const response = await apiClient.post('/api/v1/payments/p2p', {
        recipient_address: receiverAddress,
        amount: parseFloat(amount),
        memo: memo,
      });
      setTransactionResult(response.data);
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
          <h3 className="text-xl font-bold text-white mb-2">Payment Complete</h3>
          <p className="text-green-400 mb-6">Your payment has been successfully processed.</p>
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
          <h3 className="text-xl font-bold text-white mb-2">Payment Failed</h3>
          <p className="text-red-400 mb-6">{error}</p>
          <Button onClick={resetForm}>Try Again</Button>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center space-x-3 mb-6">
        <Send className="h-5 w-5 text-blue-500" />
        <h2 className="text-xl font-bold text-white">Send USDS</h2>
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
          <Button type="submit" className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600" icon={Send} loading={status === 'executing'}>Send USDS</Button>
        </div>
      </form>
    </Card>
  );
};

export default P2PPayment;