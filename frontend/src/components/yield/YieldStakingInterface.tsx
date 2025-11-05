// File: frontend/src/components/yield/YieldStakingInterface.tsx
import React, { useState, useEffect } from 'react';
import { TrendingUp, Shield, Zap } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/config/api';

const YieldStakingInterface: React.FC = () => {
  const [tiers, setTiers] = useState([]);
  const [selectedTier, setSelectedTier] = useState('stable');
  const [amount, setAmount] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTiers();
  }, []);

  const fetchTiers = async () => {
    try {
      const response = await apiClient.get('/api/v1/yield/tiers');
      setTiers(response.data.tiers);
    } catch (error) {
      console.error('Failed to fetch tiers:', error);
    }
  };

  const handleStake = async () => {
    setLoading(true);
    
    try {
      const response = await apiClient.post('/api/v1/yield/stake', {
        asset: 'USDT',
        amount: parseFloat(amount),
        tier: selectedTier
      });
      
      alert(`✅ Staked successfully! Earning ${response.data.target_apy} APY`);
      setAmount('');
      
    } catch (error) {
      console.error('Staking failed:', error);
      alert('Staking failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const tierIcons = {
    stable: Shield,
    growth: TrendingUp,
    alpha: Zap
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-3xl font-bold text-white">Earn Yield on Your Crypto</h2>
      
      {/* Tier Selection */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {tiers.map((tier: any) => {
          const Icon = tierIcons[tier.tier];
          return (
            <Card
              key={tier.tier}
              className={`cursor-pointer transition ${
                selectedTier === tier.tier
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-gray-600 hover:border-gray-500'
              }`}
              onClick={() => setSelectedTier(tier.tier)}
            >
              <div className="flex items-center space-x-3 mb-4">
                <Icon className="h-8 w-8 text-blue-400" />
                <div>
                  <h3 className="text-xl font-bold text-white capitalize">
                    {tier.tier}
                  </h3>
                  <p className="text-sm text-gray-400">{tier.risk_level} risk</p>
                </div>
              </div>
              
              <div className="text-3xl font-bold text-green-400 mb-2">
                {tier.target_apy}
              </div>
              
              <div className="text-sm text-gray-400">
                {tier.recommended_for}
              </div>
            </Card>
          );
        })}
      </div>
      
      {/* Stake Amount */}
      <Card>
        <h3 className="text-xl font-bold text-white mb-4">Stake Your Crypto</h3>
        
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Amount (USDT)
          </label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Minimum 10 USDT"
            className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white"
          />
        </div>
        
        <Button
          onClick={handleStake}
          loading={loading}
          disabled={!amount || parseFloat(amount) < 10}
          className="w-full bg-green-600 hover:bg-green-700"
        >
          Start Earning
        </Button>
      </Card>
    </div>
  );
};

export default YieldStakingInterface;