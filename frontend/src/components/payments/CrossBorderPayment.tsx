import React, { useState } from 'react';
import { Send, DollarSign, Globe, Loader2, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';
import Card from './Card';
import Button from './Button';
import { paymentService } from '../services/paymentService';

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
  const [fromCurrency, setFromCurrency] = useState('USDS');
  const [toCurrency, setToCurrency] = useState('USDS');
  const [status, setStatus] = useState<'idle' | 'creating' | 'executing' | 'complete' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [paymentId, setPaymentId] = useState<string | null>(null);
  const [transactionResult, setTransactionResult] = useState<any>(null);

  const supportedCurrencies = [
    { code: 'USDS', name: 'USDS', type: 'crypto' },
    { code: 'USD', name: 'US Dollar', type: 'fiat' },
    { code: 'NGN', name: 'Nigerian Naira', type: 'fiat' },
    { code: 'KES', name: 'Kenyan Shilling', type: 'fiat' },
    { code: 'ZAR', name: 'South African Rand', type: 'fiat' },
    { code: 'GHS', name: 'Ghanaian Cedi', type: 'fiat' }
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!amount || !receiverAddress || !fromCurrency || !toCurrency) {
      setError('All fields are required');
      return;
    }
    
    try {
      setStatus('creating');
      setError(null);
      
      // Create cross-border payment
      const createResult = await paymentService.createCrossBorderPayment({
        senderUserId: userId,
        receiverAddress,
        amount: parseFloat(amount),
        fromCurrency,
        toCurrency,
        memo
      });
      
      if (!createResult.success) {
        throw new Error(createResult.error || 'Failed to create cross-border payment');
      }
      
      setPaymentId(createResult.paymentId);
      
      // Execute cross-border payment
      setStatus('executing');
      const executeResult = await paymentService.executeCrossBorderPayment(createResult.paymentId!);
      
      if (!executeResult.success) {
        throw new Error(executeResult.error || 'Failed to execute cross-border payment');
      }
      
      setTransactionResult(executeResult);
      setStatus('complete');
      
      if (onComplete) {
        onComplete(executeResult);
      }
      
    } catch (error) {
      console.error('Cross-border payment failed:', error);
      setError(error instanceof Error ? error.message : 'Payment failed');
      setStatus('error');
    }
  };

  const resetForm = () => {
    setAmount('');
    setReceiverAddress('');
    setMemo('');
    setFromCurrency('USDS');
    setToCurrency('USDS');
    setStatus('idle');
    setError(null);
    setPaymentId(null);
    setTransactionResult(null);
  };

  const getCurrencySymbol = (currencyCode: string) => {
    const symbols: Record<string, string> = {
      'USD': '$',
      'USDS': '$',
      'NGN': '₦',
      'KES': 'KSh',
      'ZAR': 'R',
      'GHS': '₵'
    };
    return symbols[currencyCode] || '';
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
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  From Currency
                </label>
                <select
                  value={fromCurrency}
                  onChange={(e) => setFromCurrency(e.target.value)}
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  {supportedCurrencies.map((currency) => (
                    <option key={`from-${currency.code}`} value={currency.code}>
                      {currency.name} ({currency.code})
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  To Currency
                </label>
                <select
                  value={toCurrency}
                  onChange={(e) => setToCurrency(e.target.value)}
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  {supportedCurrencies.map((currency) => (
                    <option key={`to-${currency.code}`} value={currency.code}>
                      {currency.name} ({currency.code})
                    </option>
                  ))}
                </select>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Amount ({fromCurrency})
              </label>
              <div className="relative">
                <div className="absolute left-3 top-3 text-gray-400">
                  {getCurrencySymbol(fromCurrency)}
                </div>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  className="w-full pl-8 pr-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
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
            
            {fromCurrency !== toCurrency && (
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
                <div className="flex items-center mb-2">
                  <DollarSign className="h-4 w-4 text-amber-400 mr-2" />
                  <span className="text-sm text-amber-400 font-medium">USDS Required for Fees</span>
                </div>
                <p className="text-xs text-gray-300">
                  Your payment will be automatically converted from {fromCurrency} to {toCurrency} at the current market rate.
                  A small amount of USDS is required for transaction fees.
                </p>
              </div>
            )}
            
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
                className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600"
                icon={Globe}
              >
                Send Cross-Border
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
              {status === 'creating' ? 'Preparing Transaction' : 'Processing Cross-Border Transfer'}
            </h3>
            <p className="text-gray-400 mb-6">
              {status === 'creating' 
                ? 'Your cross-border payment is being prepared...' 
                : 'Your cross-border transfer is being processed...'}
            </p>
            {status === 'executing' && (
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 mx-auto max-w-sm">
                <p className="text-sm text-blue-400">
                  Cross-border payments are processed in less than 1 second through Seamount's payment network, compared to 3-5 days with traditional banks.
                </p>
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
            <h3 className="text-xl font-bold text-white mb-2">Transfer Complete</h3>
            <p className="text-green-400 mb-6">
              Your cross-border transfer has been successfully processed.
            </p>
            
            <div className="bg-gray-700/50 rounded-lg p-4 mb-6 text-left max-w-md mx-auto">
              <div className="grid grid-cols-2 gap-2">
                <div className="text-gray-400">Amount Sent:</div>
                <div className="text-white text-right">
                  {getCurrencySymbol(fromCurrency)}{parseFloat(amount)} {fromCurrency}
                </div>
                
                <div className="text-gray-400">Amount Received:</div>
                <div className="text-white text-right">
                  {getCurrencySymbol(toCurrency)}{transactionResult?.finalAmount || amount} {toCurrency}
                </div>
                
                {transactionResult?.exchangeRate && fromCurrency !== toCurrency && (
                  <>
                    <div className="text-gray-400">Exchange Rate:</div>
                    <div className="text-white text-right">
                      1 {fromCurrency} = {transactionResult.exchangeRate} {toCurrency}
                    </div>
                  </>
                )}
                
                <div className="text-gray-400">Fee:</div>
                <div className="text-white text-right">{transactionResult?.fees || '0.00'} {fromCurrency}</div>
                
                <div className="text-gray-400">Recipient:</div>
                <div className="text-white text-right">{receiverAddress.substring(0, 8)}...{receiverAddress.substring(receiverAddress.length - 6)}</div>
                
                <div className="text-gray-400">Settlement Time:</div>
                <div className="text-green-400 text-right">&lt; 1 second</div>
                
                {transactionResult?.txId && (
                  <>
                    <div className="text-gray-400">Transaction ID:</div>
                    <div className="text-white text-right">{transactionResult.txId.substring(0, 10)}...</div>
                  </>
                )}
              </div>
            </div>
            
            <Button onClick={resetForm}>
              Send Another Cross-Border Payment
            </Button>
          </div>
        );
        
      case 'error':
        return (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <AlertCircle className="h-8 w-8 text-red-500" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Transfer Failed</h3>
            <p className="text-red-400 mb-6">
              {error || 'An error occurred during the cross-border transfer process.'}
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
        <Globe className="h-5 w-5 text-purple-500" />
        <h2 className="text-xl font-bold text-white">Cross-Border Payment</h2>
      </div>
      
      {renderContent()}
    </Card>
  );
};

export default CrossBorderPayment;