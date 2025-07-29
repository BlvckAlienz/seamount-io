import React, { useState } from 'react';
import { Crown, X, Check, Zap, Shield, TrendingUp } from 'lucide-react';
import { revenueCat } from '../services/revenueCatIntegration';
import Button from './Button';
import Card from './Card';

interface PaywallModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpgrade?: () => void;
  feature?: string;
}

const PaywallModal: React.FC<PaywallModalProps> = ({ 
  isOpen, 
  onClose, 
  onUpgrade,
  feature = 'Premium Feature'
}) => {
  const [loading, setLoading] = useState(false);
  const [selectedTier, setSelectedTier] = useState('seamount_pro_monthly');

  if (!isOpen) return null;

  const subscriptionTiers = [
    {
      id: 'seamount_pro_monthly',
      name: 'Pro Monthly',
      price: '$29.99',
      period: 'per month',
      features: [
        'Advanced AI Trading Signals',
        'Real-time Fraud Detection', 
        'Priority Customer Support',
        'Advanced Portfolio Analytics',
        'API Access (10,000 calls/month)',
        'Cross-border Payment Optimization'
      ],
      highlight: true,
      savings: null
    },
    {
      id: 'seamount_pro_yearly', 
      name: 'Pro Yearly',
      price: '$299.99',
      period: 'per year',
      features: [
        'All Pro Monthly features',
        '2 months free (16% savings)',
        'White-glove onboarding',
        'Advanced risk analytics',
        'Custom integrations',
        'Dedicated account manager'
      ],
      highlight: false,
      savings: '16% OFF'
    }
  ];

  const handleUpgrade = async (tierId: string) => {
    setLoading(true);
    try {
      const success = await revenueCat.presentPaywall('current_user');
      
      if (success) {
        onUpgrade?.();
        onClose();
      }
    } catch (error) {
      console.error('Upgrade failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-4xl relative" glassy>
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors z-10"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-full mb-4">
            <Crown className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-white mb-2">
            Unlock {feature}
          </h2>
          <p className="text-gray-400 text-lg">
            Upgrade to Pro and access advanced trading features, AI insights, and priority support
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {subscriptionTiers.map((tier) => (
            <div
              key={tier.id}
              className={`relative p-6 rounded-xl border transition-all cursor-pointer ${
                selectedTier === tier.id
                  ? 'border-blue-500 bg-blue-500/10'
                  : tier.highlight
                  ? 'border-yellow-500 bg-yellow-500/10'
                  : 'border-gray-700 bg-gray-800/40'
              }`}
              onClick={() => setSelectedTier(tier.id)}
            >
              {tier.savings && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="bg-green-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                    {tier.savings}
                  </span>
                </div>
              )}

              {tier.highlight && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="bg-yellow-500 text-black text-xs font-bold px-3 py-1 rounded-full">
                    MOST POPULAR
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <h3 className="text-xl font-bold text-white mb-2">{tier.name}</h3>
                <div className="text-3xl font-bold text-white">{tier.price}</div>
                <div className="text-gray-400 text-sm">{tier.period}</div>
              </div>

              <div className="space-y-3">
                {tier.features.map((feature, index) => (
                  <div key={index} className="flex items-center space-x-3">
                    <Check className="h-4 w-4 text-green-400 flex-shrink-0" />
                    <span className="text-gray-300 text-sm">{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-xl p-6 mb-6">
          <h3 className="text-white font-semibold mb-4 flex items-center">
            <Zap className="h-5 w-5 text-yellow-400 mr-2" />
            What You'll Get Instantly
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center space-x-3">
              <TrendingUp className="h-5 w-5 text-green-400" />
              <span className="text-gray-300 text-sm">AI-powered trading signals</span>
            </div>
            <div className="flex items-center space-x-3">
              <Shield className="h-5 w-5 text-blue-400" />
              <span className="text-gray-300 text-sm">Advanced fraud protection</span>
            </div>
            <div className="flex items-center space-x-3">
              <Crown className="h-5 w-5 text-yellow-400" />
              <span className="text-gray-300 text-sm">Priority support access</span>
            </div>
          </div>
        </div>

        <div className="flex space-x-4">
          <Button
            variant="secondary"
            className="flex-1"
            onClick={onClose}
          >
            Maybe Later
          </Button>
          <Button
            className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
            loading={loading}
            onClick={() => handleUpgrade(selectedTier)}
            icon={Crown}
          >
            {loading ? 'Processing...' : 'Upgrade Now'}
          </Button>
        </div>

        <div className="text-center mt-4">
          <p className="text-xs text-gray-400">
            Cancel anytime • 14-day money-back guarantee • Secure payment processing
          </p>
        </div>
      </Card>
    </div>
  );
};

export default PaywallModal;