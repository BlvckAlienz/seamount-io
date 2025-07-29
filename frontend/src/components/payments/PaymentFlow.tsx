import React, { useState, useCallback } from 'react';
import { CreditCard, Ban as Bank, Smartphone, Globe, ArrowRight, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { useBackendIntegration } from '../hooks/useBackendIntegration';
import Card from './Card';
import Button from './Button';

interface PaymentFlowProps {
  userId: string;
  onComplete: (result: any) => void;
}

const PaymentFlow: React.FC<PaymentFlowProps> = ({ userId, onComplete }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [paymentData, setPaymentData] = useState({
    amount: '',
    currency: 'USD',
    country: 'US',
    method: 'card' as const,
    recipient: '',
    token: 'ETH'
  });

  const { 
    connected, 
    loading, 
    error, 
    initiateFunding, 
    executeTransfer, 
    getSwapQuote, 
    executeSwap 
  } = useBackendIntegration(userId);

  // Step 1: Fund wallet with fiat
  const handleFunding = useCallback(async () => {
    if (!paymentData.amount) return;
    
    try {
      const fundingSession = await initiateFunding({
        amount: parseFloat(paymentData.amount),
        currency: paymentData.currency,
        country: paymentData.country,
        paymentMethod: paymentData.method
      });

      console.log('💰 Funding session created:', fundingSession);
      
      // Simulate payment processing
      setTimeout(() => {
        setCurrentStep(3); // Move to swap step
      }, 2000);
      
    } catch (error) {
      console.error('Funding failed:', error);
    }
  }, [paymentData, initiateFunding]);

  // Step 2: Swap USDS to target token
  const handleSwapAndTransfer = useCallback(async () => {
    if (!paymentData.amount || !paymentData.recipient) return;

    try {
      const amount = parseFloat(paymentData.amount);
      
      // Get swap quote if not sending USDS
      if (paymentData.token !== 'USDS') {
        const quote = await getSwapQuote('USDS', paymentData.token, amount);
        console.log('💱 Swap quote:', quote);
        
        // Execute swap
        const swapResult = await executeSwap({
          fromToken: 'USDS',
          toToken: paymentData.token,
          amount,
          slippage: 0.5,
          userAddress: 'user_wallet' // Would be actual user wallet
        });
        
        console.log('✅ Swap completed:', swapResult);
      }

      // Execute transfer
      const transferResult = await executeTransfer({
        toAddress: paymentData.recipient,
        amount,
        token: paymentData.token
      });

      console.log('🚀 Transfer completed:', transferResult);
      onComplete(transferResult);
      setCurrentStep(4); // Success step
      
    } catch (error) {
      console.error('Swap/Transfer failed:', error);
    }
  }, [paymentData, getSwapQuote, executeSwap, executeTransfer, onComplete]);

  const supportedCountries = [
    { code: 'US', name: 'United States', currency: 'USD' },
    { code: 'KE', name: 'Kenya', currency: 'KES' },
    { code: 'NG', name: 'Nigeria', currency: 'NGN' },
    { code: 'ZA', name: 'South Africa', currency: 'ZAR' },
    { code: 'AE', name: 'UAE', currency: 'AED' },
    { code: 'SG', name: 'Singapore', currency: 'SGD' }
  ];

  const paymentMethods = [
    { key: 'card', icon: CreditCard, label: 'Credit/Debit Card', desc: 'Instant funding' },
    { key: 'bank_transfer', icon: Bank, label: 'Bank Transfer', desc: '1-2 business days' },
    { key: 'mobile_money', icon: Smartphone, label: 'Mobile Money', desc: 'M-Pesa, etc.' },
    { key: 'wire_transfer', icon: Globe, label: 'Wire Transfer', desc: '2-3 business days' }
  ];

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <Card className="max-w-2xl mx-auto">
            <h2 className="text-2xl font-bold text-white mb-6">Fund Your Wallet</h2>
            
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Amount</label>
                  <input
                    type="number"
                    value={paymentData.amount}
                    onChange={(e) => setPaymentData(prev => ({ ...prev, amount: e.target.value }))}
                    placeholder="0.00"
                    className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Country</label>
                  <select
                    value={paymentData.country}
                    onChange={(e) => {
                      const country = supportedCountries.find(c => c.code === e.target.value);
                      setPaymentData(prev => ({ 
                        ...prev, 
                        country: e.target.value,
                        currency: country?.currency || 'USD'
                      }));
                    }}
                    className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white"
                  >
                    {supportedCountries.map(country => (
                      <option key={country.code} value={country.code}>
                        {country.name} ({country.currency})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">Payment Method</label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {paymentMethods.map(({ key, icon: Icon, label, desc }) => (
                    <button
                      key={key}
                      onClick={() => setPaymentData(prev => ({ ...prev, method: key as any }))}
                      className={`p-4 rounded-lg border transition-all text-left ${
                        paymentData.method === key
                          ? 'border-blue-500 bg-blue-500/10'
                          : 'border-gray-600 hover:border-gray-500'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <Icon className="h-6 w-6 text-gray-300" />
                        <div>
                          <div className="font-medium text-white">{label}</div>
                          <div className="text-xs text-gray-400">{desc}</div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <div className="flex items-center text-red-400">
                    <AlertCircle className="h-5 w-5 mr-2" />
                    {error}
                  </div>
                </div>
              )}

              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                <div className="text-sm text-blue-400">
                  💡 Your {paymentData.currency} will be converted to USDS at current market rates
                </div>
              </div>

              <Button
                onClick={() => setCurrentStep(2)}
                disabled={!paymentData.amount || loading}
                className="w-full"
                icon={ArrowRight}
              >
                Continue to Payment
              </Button>
            </div>
          </Card>
        );

      case 2:
        return (
          <Card className="max-w-2xl mx-auto">
            <h2 className="text-2xl font-bold text-white mb-6">Confirm Funding</h2>
            
            <div className="space-y-6">
              <div className="bg-gray-800/50 rounded-lg p-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-400">Amount</span>
                  <span className="text-white font-mono">{paymentData.amount} {paymentData.currency}</span>
                </div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-400">Conversion Rate</span>
                  <span className="text-white font-mono">1 {paymentData.currency} ≈ 1.00 USDS</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">You'll Receive</span>
                  <span className="text-green-400 font-mono">~{paymentData.amount} USDS</span>
                </div>
              </div>

              <div className="text-center">
                {loading && (
                  <div className="flex items-center justify-center space-x-2 text-blue-400">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Processing funding...</span>
                  </div>
                )}
              </div>

              <Button
                onClick={handleFunding}
                loading={loading}
                className="w-full bg-green-600 hover:bg-green-700"
                icon={CheckCircle}
              >
                {loading ? 'Processing...' : 'Confirm Funding'}
              </Button>
            </div>
          </Card>
        );

      case 3:
        return (
          <Card className="max-w-2xl mx-auto">
            <h2 className="text-2xl font-bold text-white mb-6">Send Payment</h2>
            
            <div className="space-y-6">
              <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
                <div className="flex items-center text-green-400">
                  <CheckCircle className="h-5 w-5 mr-2" />
                  Wallet funded with {paymentData.amount} USDS
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Recipient Address</label>
                  <input
                    type="text"
                    value={paymentData.recipient}
                    onChange={(e) => setPaymentData(prev => ({ ...prev, recipient: e.target.value }))}
                    placeholder="0x... or wallet address"
                    className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Token</label>
                  <select
                    value={paymentData.token}
                    onChange={(e) => setPaymentData(prev => ({ ...prev, token: e.target.value }))}
                    className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white"
                  >
                    <option value="USDS">USDS (Direct)</option>
                    <option value="ETH">ETH (Swap + Send)</option>
                    <option value="USDT">USDT (Swap + Send)</option>
                    <option value="USDC">USDC (Swap + Send)</option>
                  </select>
                </div>
              </div>

              {paymentData.token !== 'USDS' && (
                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                  <div className="text-sm text-blue-400">
                    💱 Will swap {paymentData.amount} USDS → {paymentData.token} before sending
                  </div>
                </div>
              )}

              <Button
                onClick={handleSwapAndTransfer}
                loading={loading}
                disabled={!paymentData.recipient}
                className="w-full"
                icon={ArrowRight}
              >
                {loading ? 'Processing...' : `Send ${paymentData.token}`}
              </Button>
            </div>
          </Card>
        );

      case 4:
        return (
          <Card className="max-w-2xl mx-auto text-center">
            <CheckCircle className="h-16 w-16 text-green-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-white mb-4">Payment Sent Successfully!</h2>
            <p className="text-gray-400 mb-6">
              Your cross-border payment has been processed via Seamount's fraud-resistant network.
            </p>
            <div className="bg-gray-800/50 rounded-lg p-4 mb-6">
              <div className="text-sm text-gray-400 mb-2">Transaction Summary</div>
              <div className="flex justify-between text-sm mb-1">
                <span>Amount:</span>
                <span className="text-white">{paymentData.amount} {paymentData.token}</span>
              </div>
              <div className="flex justify-between text-sm mb-1">
                <span>Network Fee:</span>
                <span className="text-white">~$0.001</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Confirmation Time:</span>
                <span className="text-green-400">~0.3 seconds</span>
              </div>
            </div>
            <Button onClick={() => setCurrentStep(1)} variant="secondary">
              Send Another Payment
            </Button>
          </Card>
        );

      default:
        return null;
    }
  };

  // Connection status indicator
  if (!connected) {
    return (
      <Card className="max-w-2xl mx-auto text-center">
        <div className="text-yellow-400 mb-4">⚠️ Backend Connection</div>
        <p className="text-gray-400 mb-4">
          {loading ? 'Connecting to Seamount backend...' : 'Backend unavailable - using demo mode'}
        </p>
        {!loading && (
          <div className="text-sm text-gray-500">
            All operations will be simulated for demonstration
          </div>
        )}
      </Card>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 py-12">
      {/* Progress indicator */}
      <div className="max-w-4xl mx-auto px-4 mb-8">
        <div className="flex items-center justify-between">
          {[1, 2, 3, 4].map((step) => (
            <div
              key={step}
              className={`flex items-center ${
                step < 4 ? 'flex-1' : ''
              }`}
            >
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  currentStep >= step
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                {currentStep > step ? <CheckCircle className="h-5 w-5" /> : step}
              </div>
              {step < 4 && (
                <div
                  className={`flex-1 h-1 mx-4 ${
                    currentStep > step ? 'bg-blue-500' : 'bg-gray-700'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between mt-2 text-sm text-gray-400">
          <span>Fund</span>
          <span>Confirm</span>
          <span>Send</span>
          <span>Complete</span>
        </div>
      </div>

      {renderStep()}
    </div>
  );
};

export default PaymentFlow;