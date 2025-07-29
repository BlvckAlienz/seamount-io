import React, { useState } from 'react';
import { Send, DollarSign, Loader2, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import Card from './Card';
import Button from './Button';
import { paymentService } from '../services/paymentService';

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
  const [status, setStatus] = useState<'idle' | 'creating' | 'executing' | 'complete' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [paymentId, setPaymentId] = useState<string | null>(null);
  const [transactionResult, setTransactionResult] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!amount || !receiverAddress) {
      setError('Amount and receiver address are required');
      return;
    }
    
    try {
      setStatus('creating');
      setError(null);
      
      // Create P2P payment
      const createResult = await paymentService.createP2PPayment({
        senderUserId: userId,
        receiverAddress,
        amount: parseFloat(amount),
        memo
      });
      
      if (!createResult.success) {
        throw new Error(createResult.error || 'Failed to create payment');
      }
      
      setPaymentId(createResult.paymentId);
      
      // Execute P2P payment
      setStatus('executing');
      const executeResult = await paymentService.executeP2PPayment(createResult.paymentId!);
      
      if (!executeResult.success) {
        throw new Error(executeResult.error || 'Failed to execute payment');
      }
      
      setTransactionResult(executeResult);
      setStatus('complete');
      
      if (onComplete) {
        onComplete(executeResult);
      }
      
    } catch (error) {
      console.error('P2P payment failed:', error);
      setError(error instanceof Error ? error.message : 'Payment failed');
      setStatus('error');
    }
  };

  const resetForm = () => {
    setAmount('');
    setReceiverAddress('');
    setMemo('');
    setStatus('idle');
    setError(null);
    setPaymentId(null);
    setTransactionResult(null);
  };

  const renderContent = () => {
    switch (status) {
      case 'idle':
        return (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Recipient Address
              </label>
              <input
                type="text"
                value={receiverAddress}
                onChange={(e) => setReceiverAddress(e.target.value)}
                placeholder="0x... or Algorand address"
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Amount (USDS)
              </label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  className="w-full pl-10 pr-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div className="flex space-x-2 mt-2">
                <button
                  type="button"
                  onClick={() => setAmount('10')}
                  className="flex-1 py-1 px-2 text-xs bg-gray-600 hover:bg-gray-500 rounded text-gray-300"
                >
                  $10
                </button>
                <button
                  type="button"
                  onClick={() => setAmount('50')}
                  className="flex-1 py-1 px-2 text-xs bg-gray-600 hover:bg-gray-500 rounded text-gray-300"
                >
                  $50
                </button>
                <button
                  type="button"
                  onClick={() => setAmount('100')}
                  className="flex-1 py-1 px-2 text-xs bg-gray-600 hover:bg-gray-500 rounded text-gray-300"
                >
                  $100
                </button>
                <button
                  type="button"
                  onClick={() => setAmount('500')}
                  className="flex-1 py-1 px-2 text-xs bg-gray-600 hover:bg-gray-500 rounded text-gray-300"
                >
                  $500
                </button>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Memo (Optional)
              </label>
              <textarea
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                placeholder="Add a note to the recipient"
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                rows={2}
              />
            </div>
            
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <div className="flex items-center space-x-2 text-red-400">
                  <AlertCircle className="h-5 w-5" />
                  <span>{error}</span>
                </div>
              </div>
            )}
            
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
              <div className="flex items-center mb-2">
                <Clock className="h-4 w-4 text-blue-400 mr-2" />
                <span className="text-sm text-blue-400 font-medium">USDS-Powered Transfer</span>
              </div>
              <p className="text-xs text-gray-300">
                Transactions are settled instantly using USDS. Always keep some USDS in your wallet for transaction fees.
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
                type="submit"
                className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600"
                icon={Send}
              >
                Send USDS
              </Button>
            </div>
          </form>
        );
        
      case 'creating':
      case 'executing':
        return (
          <div className="text-center py-8">
            <Loader2 className="h-12 w-12 text-blue-500 animate-spin mx-auto mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">
              {status === 'creating' ? 'Preparing Transaction' : 'Processing Transaction'}
            </h3>
            <p className="text-gray-400 mb-6">
              {status === 'creating' 
                ? 'Your payment is being prepared...' 
                : 'Your payment is being processed on the blockchain...'}
            </p>
            {paymentId && (
              <div className="text-sm text-gray-400">
                Payment ID: {paymentId}
              </div>
            )}
          </div>
        );
        
      case 'complete':
        return (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-8 w-8 text-green-500" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Payment Complete</h3>
            <p className="text-green-400 mb-6">
              Your payment has been successfully processed.
            </p>
            
            <div className="bg-gray-700/50 rounded-lg p-4 mb-6 text-left">
              <div className="grid grid-cols-2 gap-2">
                <div className="text-gray-400">Amount:</div>
                <div className="text-white text-right">{parseFloat(amount)} USDS</div>
                <div className="text-gray-400">To:</div>
                <div className="text-white text-right">{receiverAddress.substring(0, 10)}...{receiverAddress.substring(receiverAddress.length - 6)}</div>
                <div className="text-gray-400">Transaction:</div>
                <div className="text-white text-right">{transactionResult?.txId ? `${transactionResult.txId.substring(0, 10)}...` : 'Pending'}</div>
                <div className="text-gray-400">Settlement Time:</div>
                <div className="text-green-400 text-right">&lt; 1 second</div>
              </div>
            </div>
            
            <Button onClick={resetForm}>
              Send Another Payment
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
              {error || 'An error occurred during the payment process.'}
            </p>
            <Button onClick={resetForm}>
              Try Again
            </Button>
          </div>
        );
    }
  };

  return (
    <Card>
      <div className="flex items-center space-x-3 mb-6">
        <Send className="h-5 w-5 text-blue-500" />
        <h2 className="text-xl font-bold text-white">Send USDS</h2>
      </div>
      
      {renderContent()}
    </Card>
  );
};

export default P2PPayment;