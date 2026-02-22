// 📁 FILE: frontend/src/components/modals/EarnModal.tsx
// ✅ PRODUCTION EARN MODAL - Mobile-First Responsive Design

import React, { useState, useEffect } from 'react';
import { X, TrendingUp, Shield, Zap, Check, Loader2, Info } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface EarnModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const YIELD_TIERS = [
  {
    id: 'prime',
    name: 'Prime',
    apy: '5.25%',
    apyNet: '5.25%',
    risk: 'Low Risk',
    icon: Shield,
    color: 'text-green-400',
    bgColor: 'bg-green-900/20',
    borderColor: 'border-green-500/50',
    description: 'Stable yield via Folks Finance lending. Conservative and reliable.',
    minAmount: 10,
  },
  {
    id: 'alpha',
    name: 'Alpha',
    apy: '8.2%',
    apyNet: '8.2%',
    risk: 'Medium Risk',
    icon: Zap,
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/20',
    borderColor: 'border-purple-500/50',
    description: 'Higher yield via Pact+Folks composite strategy. Balanced risk/reward.',
    minAmount: 10,
  },
];

const SUPPORTED_ASSETS = [
  { symbol: 'USDT', displayName: 'Tether USD (Algorand)' },
  { symbol: 'USDCa', displayName: 'USD Coin (Algorand)' },
  { symbol: 'ALGO', displayName: 'Algorand' }
];

export const EarnModal: React.FC<EarnModalProps> = ({ open, onOpenChange }) => {
  const [selectedTier, setSelectedTier] = useState('prime');
  const [asset, setAsset] = useState('USDT');
  const [amount, setAmount] = useState('');
  const [loading, setLoading] = useState(false);
  const [userStakes, setUserStakes] = useState<any[]>([]);

  const tier = YIELD_TIERS.find((t) => t.id === selectedTier)!;

  useEffect(() => {
    if (open) {
      fetchUserStakes();
    }
  }, [open]);

  const fetchUserStakes = async () => {
    try {
      const response = await apiClient.get('/api/v1/yield/stakes');
      if (response.data.success) {
        setUserStakes(response.data.stakes || []);
      }
    } catch (err) {
      console.error('Failed to fetch stakes:', err);
    }
  };

  const handleStake = async () => {
    const amountNum = parseFloat(amount);

    if (!amountNum || amountNum < tier.minAmount) {
      toast.error(`Minimum stake: $${tier.minAmount}`);
      return;
    }

    setLoading(true);

    try {
      const response = await apiClient.post('/api/v1/yield/stake', {
        asset: asset,
        amount: amountNum,
        tier: selectedTier,
      });

      if (response.data.success) {
        toast.success(
          `✅ Staked ${amountNum} ${asset} in ${tier.name} tier! Earning ${tier.apy} APY`,
          { duration: 5000 }
        );

        setAmount('');
        fetchUserStakes();
        onOpenChange(false);

        window.dispatchEvent(new Event('wallet-balance-updated'));
      } else {
        throw new Error(response.data.error || 'Stake failed');
      }
    } catch (err: any) {
      console.error('Staking failed:', err);
      toast.error(err.response?.data?.detail || 'Failed to stake. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto p-2 sm:p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />

      {/* Modal - 📱 RESPONSIVE CONTAINER */}
      <div 
        className="relative bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600 rounded-xl sm:rounded-2xl p-4 sm:p-6 w-full max-w-[95vw] sm:max-w-[600px] shadow-2xl animate-in slide-in-from-bottom-4 duration-300 my-4 sm:my-8 max-h-[90vh] overflow-y-auto"
        style={{ zIndex: 1000 }}
      >
        {/* Header - 📱 COMPACT */}
        <div className="flex items-center justify-between mb-4 sm:mb-6">
          <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <TrendingUp className="h-5 w-5 sm:h-6 sm:w-6 text-yellow-600" />
            <span className="hidden xs:inline">Earn Yield</span>
            <span className="xs:hidden">Earn</span>
          </h2>
          <button
            onClick={() => onOpenChange(false)}
            className="text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors p-1"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tier Selection - 📱 STACKED ON MOBILE */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 mb-4 sm:mb-6">
          {YIELD_TIERS.map((t) => {
            const Icon = t.icon;
            const isSelected = selectedTier === t.id;

            return (
              <button
                key={t.id}
                onClick={() => setSelectedTier(t.id)}
                className={`p-3 sm:p-4 rounded-lg sm:rounded-xl border-2 transition-all text-left active:scale-95 ${
                  isSelected
                    ? `${t.bgColor} ${t.borderColor} shadow-lg`
                    : 'bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 hover:border-gray-400 dark:hover:border-gray-400'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5 sm:mb-2">
                  <div className="flex items-center gap-1.5 sm:gap-2">
                    <Icon className={`h-5 w-5 sm:h-6 sm:w-6 ${isSelected ? t.color : 'text-gray-500 dark:text-gray-400'}`} />
                    <span className="text-base sm:text-lg font-bold text-gray-900 dark:text-white">{t.name}</span>
                  </div>
                  {isSelected && <Check className={`h-4 w-4 sm:h-5 sm:w-5 ${t.color}`} />}
                </div>
                <div className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mb-1">{t.apy}</div>
                <div className="text-[10px] sm:text-xs text-gray-600 dark:text-gray-400 mb-1.5 sm:mb-2 font-medium">{t.risk}</div>
                <p className="text-[10px] sm:text-xs text-gray-600 dark:text-gray-400 leading-relaxed">{t.description}</p>
              </button>
            );
          })}
        </div>

        {/* Stake Form - 📱 RESPONSIVE */}
        <div className="bg-gray-50 dark:bg-gray-700 border-2 border-gray-200 dark:border-gray-600 rounded-lg sm:rounded-xl p-3 sm:p-4 mb-3 sm:mb-4">
          <div className="mb-3 sm:mb-4">
            <label className="text-xs sm:text-sm font-semibold text-gray-900 dark:text-white mb-1.5 sm:mb-2 block">
              Select Asset
            </label>
            <select
              value={asset}
              onChange={(e) => setAsset(e.target.value)}
              className="..."
            >
              {SUPPORTED_ASSETS.map((a) => (
                <option key={a.symbol} value={a.symbol}>
                  {a.displayName}
                </option>
              ))}
            </select>
          </div>

          <div className="mb-3 sm:mb-4">
            <label className="text-xs sm:text-sm font-semibold text-gray-900 dark:text-white mb-1.5 sm:mb-2 block">
              Amount (Minimum ${tier.minAmount})
            </label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder={`${tier.minAmount}.00`}
              className="w-full bg-white dark:bg-gray-800 border-2 border-gray-300 dark:border-gray-500 rounded-lg px-3 sm:px-4 py-2.5 sm:py-3 text-gray-900 dark:text-white text-base sm:text-lg focus:outline-none focus:ring-2 focus:ring-yellow-500"
            />
          </div>

          {/* Expected Returns - 📱 COMPACT */}
          {amount && parseFloat(amount) >= tier.minAmount && (
            <div className="bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600 rounded-lg p-2.5 sm:p-3 space-y-1.5 sm:space-y-2">
              <div className="flex justify-between text-xs sm:text-sm">
                <span className="text-gray-700 dark:text-gray-300">Expected Daily Yield</span>
                <span className="text-green-600 font-medium">
                  ${((parseFloat(amount) * parseFloat(tier.apy.replace('%', '')) / 100) / 365).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between text-xs sm:text-sm">
                <span className="text-gray-700 dark:text-gray-300">Expected Annual Yield</span>
                <span className="text-green-600 font-medium">
                  ${((parseFloat(amount) * parseFloat(tier.apy.replace('%', '')) / 100)).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between text-xs sm:text-sm border-t-2 border-gray-200 dark:border-gray-600 pt-1.5 sm:pt-2">
                <span className="text-gray-900 dark:text-white font-semibold">APY (Net of Fees)</span>
                <span className="text-gray-900 dark:text-white font-bold">{tier.apyNet}</span>
              </div>
            </div>
          )}
        </div>

        {/* Stake Button - 📱 TOUCH-FRIENDLY */}
        <button
          onClick={handleStake}
          disabled={loading || !amount || parseFloat(amount) < tier.minAmount}
          className="w-full bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold py-3 sm:py-4 rounded-lg transition-all flex items-center justify-center gap-2 text-sm sm:text-base active:scale-95"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" />
              Staking...
            </>
          ) : (
            <>
              <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5" />
              Stake & Earn
            </>
          )}
        </button>

        {/* Active Stakes - 📱 COMPACT SCROLLABLE */}
        {userStakes.length > 0 && (
          <div className="mt-4 sm:mt-6 pt-4 sm:pt-6 border-t-2 border-gray-200 dark:border-gray-600">
            <h3 className="text-sm sm:text-base font-bold text-gray-900 dark:text-white mb-3 sm:mb-4 flex items-center gap-2">
              <Info className="h-4 w-4 sm:h-5 sm:w-5 text-blue-600" />
              <span className="hidden xs:inline">Your Active Stakes</span>
              <span className="xs:hidden">Active Stakes</span>
            </h3>
            <div className="space-y-2 max-h-32 sm:max-h-40 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600">
              {userStakes
                .filter((s) => s.status === 'active')
                .map((stake) => (
                  <div
                    key={stake.stake_id}
                    className="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg p-2.5 sm:p-3 flex justify-between items-center"
                  >
                    <div>
                      <div className="text-sm sm:text-base text-gray-900 dark:text-white font-medium">
                        {stake.principal} {stake.asset}
                      </div>
                      <div className="text-[10px] sm:text-xs text-gray-600 dark:text-gray-400 capitalize">{stake.tier} Tier</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm sm:text-base text-green-600 font-medium">{stake.current_apy}</div>
                      <div className="text-[10px] sm:text-xs text-gray-600 dark:text-gray-400">
                        +${stake.net_yield.toFixed(2)} earned
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Disclaimer - 📱 COMPACT */}
        <p className="text-[10px] sm:text-xs text-gray-600 dark:text-gray-400 text-center mt-3 sm:mt-4 font-medium">
          Powered by Folks Finance & Pact Finance on Algorand MainNet
        </p>
      </div>
    </div>
  );
};