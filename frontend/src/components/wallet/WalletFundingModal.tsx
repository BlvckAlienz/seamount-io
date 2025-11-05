// File: frontend/src/components/wallet/WalletFundingModal.tsx
import React, { useState } from 'react';
import { CreditCard, Smartphone, Globe, DollarSign } from 'lucide-react';
import { Card } from '@/components/ui/card.tsx';
import { Button } from '@/components/ui/button.tsx';
import { apiClient } from '@/config/api';

interface WalletFundingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (result: any) => void;
}

type FundingMethod = 'card' | 'bank_transfer' | 'crypto' | 'exchange';

const WalletFundingModal: React.FC<WalletFundingModalProps> = ({
  isOpen,
  onClose,
  onSuccess
}) => {
  const [amount, setAmount] = useState('');
  const [currency, setCurrency] = useState('NGN');
  const [method, setMethod] = useState<FundingMethod>('card');
  const [loading, setLoading] = useState(false);

  const fundingMethods = [
    {
      key: 'card' as FundingMethod,
      icon: CreditCard,
      label: 'Card Payment',
      description: 'Instant via Paystack/Flutterwave',
      available: true
    },
    {
      key: 'bank_transfer' as FundingMethod,
      icon: Globe,
      label: 'Bank Transfer',
      description: '1-2 business days',
      available: true
    },
    {
      key: 'crypto' as FundingMethod,
      icon: DollarSign,
      label: 'Send Crypto',
      description: 'From external wallet',
      available: true
    },
    {
      key: 'exchange' as FundingMethod,
      icon: Smartphone,
      label: 'Exchange Withdrawal',
      description: 'Binance, Coinbase, etc.',
      available: true
    }
  ];

  const handleFund = async () => {
    setLoading(true);
    
    try {
      if (method === 'card' || method === 'bank_transfer') {
        // Use on-ramp aggregator
        const response = await apiClient.post('/api/v1/onramp/initialize', {
          amount_fiat: parseFloat(amount),
          currency,
          crypto_asset: 'USDT',
          user_country: 'NG'
        });
        
        // Open payment link
        if (response.data.checkout_url) {
          window.open(response.data.checkout_url, '_blank');
        }
        
        onSuccess(response.data);
        
      } else if (method === 'crypto') {
        // Generate deposit address
        const response = await apiClient.post('/api/v1/wallet/deposit/address', {
          asset: 'USDT'
        });
        
        onSuccess(response.data);
        
      } else if (method === 'exchange') {
        // Show exchange withdrawal instructions
        const response = await apiClient.get('/api/v1/wallet/exchanges');
        onSuccess(response.data);
      }
      
      onClose();
      
    } catch (error) {
      console.error('Funding failed:', error);
      alert('Funding failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <Card className="max-w-2xl w-full mx-4">
        <h2 className="text-2xl font-bold text-white mb-6">Fund Your Wallet</h2>
        
        {/* Amount Input */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Amount
          </label>
          <div className="relative">
            <DollarSign className="absolute left-3 top-3 text-gray-400" />
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              className="w-full pl-10 pr-20 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white"
            />
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="absolute right-2 top-2 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white"
            >
              <option value="NGN">NGN</option>
              <option value="USD">USD</option>
              <option value="KES">KES</option>
              <option value="GHS">GHS</option>
            </select>
          </div>
        </div>
        
        {/* Funding Methods */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-3">
            Payment Method
          </label>
          <div className="grid grid-cols-2 gap-3">
            {fundingMethods.map(({ key, icon: Icon, label, description, available }) => (
              <button
                key={key}
                onClick={() => setMethod(key)}
                disabled={!available}
                className={`p-4 rounded-lg border text-left transition ${
                  method === key
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-gray-600 hover:border-gray-500'
                } ${!available && 'opacity-50 cursor-not-allowed'}`}
              >
                <Icon className="h-6 w-6 text-gray-300 mb-2" />
                <div className="font-medium text-white text-sm">{label}</div>
                <div className="text-xs text-gray-400">{description}</div>
              </button>
            ))}
          </div>
        </div>
        
        {/* Action Buttons */}
        <div className="flex space-x-4">
          <Button
            onClick={onClose}
            variant="secondary"
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            onClick={handleFund}
           
            disabled={!amount || parseFloat(amount) <= 0}
            className="flex-1 bg-green-600 hover:bg-green-700"
          >
            Continue
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default WalletFundingModal;