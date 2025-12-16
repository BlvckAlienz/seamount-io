// File: frontend/src/components/modals/CreateRepoModal.tsx
import React, { useState, useEffect } from 'react';
import { X, Info, AlertTriangle, TrendingUp } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface CreateRepoModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tokenizedAssets?: any[];
}

export const CreateRepoModal: React.FC<CreateRepoModalProps> = ({
  open,
  onOpenChange,
  tokenizedAssets = [],
}) => {
  const [step, setStep] = useState<1 | 2>(1);
  const [loading, setLoading] = useState(false);
  
  // Form state
  const [selectedAsset, setSelectedAsset] = useState('');
  const [collateralQuantity, setCollateralQuantity] = useState('');
  const [loanAmount, setLoanAmount] = useState('');
  const [repoRate, setRepoRate] = useState('4.5');
  const [maturityDays, setMaturityDays] = useState('30');
  
  // Auto-calculated values
  const [collateralValue, setCollateralValue] = useState(0);
  const [ltv, setLtv] = useState(0);
  const [haircut, setHaircut] = useState(15);
  const [coverage, setCoverage] = useState(0);
  const [repurchaseAmount, setRepurchaseAmount] = useState(0);

  // Calculate metrics when inputs change
  useEffect(() => {
    if (selectedAsset && collateralQuantity && loanAmount) {
      const asset = tokenizedAssets.find(a => a.id === selectedAsset);
      if (asset) {
        const colValue = parseFloat(asset.current_price_usd) * parseFloat(collateralQuantity);
        const loanAmt = parseFloat(loanAmount);
        const ltvRatio = (loanAmt / colValue) * 100;
        const coverageRatio = ((colValue * (1 - haircut/100)) / loanAmt) * 100;
        
        // Calculate repurchase amount
        const rate = parseFloat(repoRate) / 100 / 365;
        const days = parseFloat(maturityDays);
        const interest = loanAmt * rate * days;
        const repurchase = loanAmt + interest;
        
        setCollateralValue(colValue);
        setLtv(ltvRatio);
        setCoverage(coverageRatio);
        setRepurchaseAmount(repurchase);
      }
    }
  }, [selectedAsset, collateralQuantity, loanAmount, repoRate, maturityDays, haircut, tokenizedAssets]);

  const handleSubmit = async () => {
    if (!selectedAsset || !collateralQuantity || !loanAmount) {
      toast.error('Please fill all required fields');
      return;
    }

    if (ltv > 85) {
      toast.error('LTV ratio too high (max 85%)');
      return;
    }

    try {
      setLoading(true);
      
      const response = await apiClient.post('/api/v1/tokenization/create-repo', {
        collateral_asset_id: selectedAsset,
        collateral_quantity: parseInt(collateralQuantity),
        loan_amount_usd: parseFloat(loanAmount),
        repo_rate_percentage: parseFloat(repoRate),
        maturity_days: parseInt(maturityDays),
      });

      if (response.data.success) {
        toast.success('Repo trade created successfully!');
        onOpenChange(false);
        // Reset form
        setStep(1);
        setSelectedAsset('');
        setCollateralQuantity('');
        setLoanAmount('');
      } else {
        toast.error(response.data.error || 'Failed to create repo');
      }
    } catch (error: any) {
      console.error('Repo creation failed:', error);
      toast.error(error.response?.data?.detail || 'Failed to create repo trade');
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto mx-2 sm:mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 md:p-6 border-b border-gray-700">
          <div>
            <h2 className="text-xl md:text-2xl font-bold text-white">Create Repo Trade</h2>
            <p className="text-gray-400 text-xs md:text-sm mt-1">Borrow cash against tokenized securities</p>
          </div>
          <button
            onClick={() => onOpenChange(false)}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-2 p-3 md:p-4 bg-gray-800/50">
          <div className={`flex items-center gap-1 md:gap-2 px-3 md:px-4 py-2 rounded-lg ${step === 1 ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400'}`}>
            <span className="font-semibold text-sm md:text-base">1</span>
            <span className="text-xs md:text-sm">Collateral</span>
          </div>
          <div className="w-8 md:w-12 h-0.5 bg-gray-700"></div>
          <div className={`flex items-center gap-1 md:gap-2 px-3 md:px-4 py-2 rounded-lg ${step === 2 ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400'}`}>
            <span className="font-semibold text-sm md:text-base">2</span>
            <span className="text-xs md:text-sm">Terms</span>
          </div>
        </div>

        {/* Step 1: Collateral Selection */}
        {step === 1 && (
          <div className="p-4 md:p-6 space-y-4 md:space-y-6">
            {/* Asset Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Collateral Asset <span className="text-red-400">*</span>
              </label>
              <select
                value={selectedAsset}
                onChange={(e) => setSelectedAsset(e.target.value)}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
              >
                <option value="">Select asset...</option>
                {tokenizedAssets.map(asset => (
                  <option key={asset.id} value={asset.id}>
                    {asset.symbol} - {asset.name} (Available: {asset.on_chain_balance})
                  </option>
                ))}
              </select>
            </div>

            {/* Quantity */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Collateral Quantity <span className="text-red-400">*</span>
              </label>
              <input
                type="number"
                value={collateralQuantity}
                onChange={(e) => setCollateralQuantity(e.target.value)}
                placeholder="0"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {/* Loan Amount */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Loan Amount (USD) <span className="text-red-400">*</span>
              </label>
              <input
                type="number"
                value={loanAmount}
                onChange={(e) => setLoanAmount(e.target.value)}
                placeholder="0.00"
                step="0.01"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {/* Auto-Calculated Metrics */}
            {collateralValue > 0 && (
              <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-3 md:p-4 space-y-3">
                <div className="flex items-center gap-2 text-blue-400 mb-2">
                  <TrendingUp className="h-4 w-4 md:h-5 md:w-5" />
                  <span className="text-sm md:text-base font-semibold">Auto-Calculated Metrics</span>
                </div>
                
                <div className="grid grid-cols-2 gap-3 md:gap-4">
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Collateral Value</div>
                    <div className="text-base md:text-lg font-bold text-white">${collateralValue.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">LTV Ratio</div>
                    <div className={`text-base md:text-lg font-bold ${ltv > 85 ? 'text-red-400' : ltv > 75 ? 'text-yellow-400' : 'text-green-400'}`}>
                      {ltv.toFixed(2)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Haircut</div>
                    <div className="text-base md:text-lg font-bold text-white">{haircut}%</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Coverage Ratio</div>
                    <div className="text-base md:text-lg font-bold text-green-400">{coverage.toFixed(2)}%</div>
                  </div>
                </div>

                {ltv > 85 && (
                  <div className="flex items-start gap-2 mt-3 p-2 md:p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
                    <AlertTriangle className="h-4 w-4 md:h-5 md:w-5 text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="text-xs md:text-sm text-red-300">
                      LTV ratio exceeds 85% maximum. Reduce loan amount or add more collateral.
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Next Button */}
            <button
              onClick={() => setStep(2)}
              disabled={!selectedAsset || !collateralQuantity || !loanAmount || ltv > 85}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
            >
              Continue to Terms →
            </button>
          </div>
        )}

        {/* Step 2: Terms */}
        {step === 2 && (
          <div className="p-6 space-y-6">
            {/* Repo Rate */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Repo Rate (% APR) <span className="text-red-400">*</span>
              </label>
              <input
                type="number"
                value={repoRate}
                onChange={(e) => setRepoRate(e.target.value)}
                step="0.1"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {/* Maturity Days */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Maturity (Days) <span className="text-red-400">*</span>
              </label>
              <input
                type="number"
                value={maturityDays}
                onChange={(e) => setMaturityDays(e.target.value)}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {/* Repurchase Amount */}
            <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-3 md:p-4">
              <div className="text-xs md:text-sm text-gray-400 mb-2">Repurchase Amount (Principal + Interest)</div>
              <div className="text-2xl md:text-3xl font-bold text-white">${repurchaseAmount.toFixed(2)}</div>
              <div className="text-xs text-gray-400 mt-2">
                Interest: ${(repurchaseAmount - parseFloat(loanAmount)).toFixed(2)}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => setStep(1)}
                className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
              >
                ← Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="flex-1 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 text-white font-semibold rounded-lg transition-colors"
              >
                {loading ? 'Creating...' : 'Create Repo'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CreateRepoModal;