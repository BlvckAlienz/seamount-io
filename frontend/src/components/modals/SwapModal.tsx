// 📍 FILE: frontend/src/components/modals/SwapModal.tsx
// âœ… PRODUCTION SWAP MODAL - Real DeFi Integration

import React, { useState, useEffect } from 'react';
import { X, ArrowDownUp, TrendingUp, AlertCircle, Check, Loader2 } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface SwapModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Supported assets on Algorand (from your config)
const SUPPORTED_ASSETS = [
  { symbol: 'USDT', name: 'Tether USD', decimals: 6 },
  { symbol: 'ALGO', name: 'Algorand', decimals: 6 },
  { symbol: 'USDCa', name: 'USD Coin', decimals: 6 },
  { symbol: 'goBTC', name: 'Wrapped Bitcoin', decimals: 8 },
  { symbol: 'goETH', name: 'Wrapped Ethereum', decimals: 8 },
];

export const SwapModal: React.FC<SwapModalProps> = ({ open, onOpenChange }) => {
  const [fromAsset, setFromAsset] = useState('USDT');
  const [toAsset, setToAsset] = useState('ALGO');
  const [amount, setAmount] = useState('');
  const [quote, setQuote] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [swapping, setSwapping] = useState(false);
  const [error, setError] = useState('');
  const [balances, setBalances] = useState<Record<string, number>>({});
  const [fetchingBalances, setFetchingBalances] = useState(false);

  // ➕ Fetch balances when modal opens
  useEffect(() => {
    const fetchBalances = async () => {
      if (!open) return;
      
      setFetchingBalances(true);
      try {
        const response = await apiClient.get('/api/v1/wallet/balances');
        
        if (response?.data?.success && response.data.assets) {
          const balanceMap: Record<string, number> = {};
          
          response.data.assets.forEach((asset: any) => {
            // Map asset keys to display format
            const assetKey = asset.asset || asset.symbol || asset.chain?.toUpperCase();
            if (assetKey) {
              balanceMap[assetKey] = asset.balance || 0;
            }
          });
          
          setBalances(balanceMap);
          console.log('✅ Swap balances loaded:', balanceMap);
        }
      } catch (err) {
        console.error('Failed to fetch balances:', err);
        // Don't block UI if balance fetch fails
        setBalances({});
      } finally {
        setFetchingBalances(false);
      }
    };
    
    fetchBalances();
  }, [open]);

  // âœ… Auto-fetch quote when amount/assets change
  useEffect(() => {
    if (!amount || parseFloat(amount) <= 0 || !open) {
      setQuote(null);
      return;
    }

    const timer = setTimeout(() => {
      fetchQuote();
    }, 500); // Debounce 500ms

    return () => clearTimeout(timer);
  }, [amount, fromAsset, toAsset, open]);

  const fetchQuote = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await apiClient.post('/api/v1/swap/quote', {
        from_asset: fromAsset,
        to_asset: toAsset,
        amount: parseFloat(amount),
      });

      if (response.data.success !== false) {
        setQuote(response.data);
      } else {
        setError(response.data.error || 'Failed to get quote');
      }
    } catch (err: any) {
      console.error('Quote fetch failed:', err);
      setError(err.response?.data?.detail || 'Unable to fetch quote');
      setQuote(null);
    } finally {
      setLoading(false);
    }
  };

  const executeSwap = async () => {
    if (!quote) {
      toast.error('Please get a quote first');
      return;
    }

    setSwapping(true);

    try {
      const response = await apiClient.post('/api/v1/swap/execute', {
        from_asset: fromAsset,
        to_asset: toAsset,
        amount: parseFloat(amount),
      });

      if (response.data.success) {
        toast.success(
          `✅ Swap successful! Received ${response.data.amount_out.toFixed(4)} ${toAsset}`
        );

        // Reset form
        setAmount('');
        setQuote(null);
        onOpenChange(false);

        // Trigger balance refresh (you can emit event here)
        window.dispatchEvent(new Event('wallet-balance-updated'));
      } else {
        throw new Error(response.data.error || 'Swap failed');
      }
    } catch (err: any) {
      console.error('Swap execution failed:', err);
      toast.error(err.response?.data?.detail || 'Swap failed. Please try again.');
    } finally {
      setSwapping(false);
    }
  };

  const swapAssets = () => {
    const temp = fromAsset;
    setFromAsset(toAsset);
    setToAsset(temp);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />

      {/* Modal - âœ… UPDATED TO MATCH YOUR FUND/WITHDRAW STYLE */}
      <div 
        className="relative bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600 rounded-2xl p-6 w-full max-w-[500px] shadow-2xl animate-in slide-in-from-bottom-4 duration-300 mx-4"
        style={{ zIndex: 1000 }}  // âœ… INLINE STYLE LIKE YOURS
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <ArrowDownUp className="h-6 w-6 text-purple-600" />
            Swap Assets
          </h2>
          <button
            onClick={() => onOpenChange(false)}
            className="text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* From Asset */}
        <div className="mb-4">
          <label className="text-sm font-semibold text-gray-900 dark:text-white mb-2 block">
            From
          </label>

          {/* ➕ Balance Display */}
          {balances[fromAsset] !== undefined && (
            <div className="flex justify-between items-center px-3 py-2 mb-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <span className="text-sm text-gray-700 dark:text-gray-300">Available:</span>
              <span className="font-bold text-blue-700 dark:text-blue-300">
                {balances[fromAsset].toFixed(6)} {fromAsset}
              </span>
            </div>
          )}

          <div className="flex gap-2">
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              className="flex-1 bg-white dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-500 rounded-lg px-4 py-3 text-gray-900 dark:text-white text-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            {/* ➕ MAX Button */}
            {balances[fromAsset] > 0 && (
              <button
                type="button"
                onClick={() => setAmount(balances[fromAsset].toString())}
                className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1 text-xs font-bold bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors"
              >
                MAX
              </button>
            )}

            <select
              value={fromAsset}
              onChange={(e) => setFromAsset(e.target.value)}
              className="bg-white dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-500 rounded-lg px-4 py-3 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              {SUPPORTED_ASSETS.map((asset) => (
                <option key={asset.symbol} value={asset.symbol}>
                  {asset.symbol}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Swap Direction Button */}
        <div className="flex justify-center my-2">
          <button
            onClick={swapAssets}
            className="bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 border-2 border-gray-300 dark:border-gray-500 rounded-full p-2 transition-all hover:scale-110"
          >
            <ArrowDownUp className="h-5 w-5 text-purple-600" />
          </button>
        </div>

        {/* To Asset */}
        <div className="mb-6">
          <label className="text-sm font-semibold text-gray-900 dark:text-white mb-2 block">
            To
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={quote ? quote.amount_out.toFixed(4) : '0.00'}
              readOnly
              placeholder="0.00"
              className="flex-1 bg-gray-100 dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-500 rounded-lg px-4 py-3 text-gray-900 dark:text-white text-lg focus:outline-none"
            />
            <select
              value={toAsset}
              onChange={(e) => setToAsset(e.target.value)}
              className="bg-white dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-500 rounded-lg px-4 py-3 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              {SUPPORTED_ASSETS.filter((a) => a.symbol !== fromAsset).map((asset) => (
                <option key={asset.symbol} value={asset.symbol}>
                  {asset.symbol}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Quote Details */}
        {quote && !error && (
          <div className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-700 rounded-lg p-4 mb-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-700 dark:text-gray-300">Rate</span>
              <span className="text-gray-900 dark:text-white font-medium">
                1 {fromAsset} = {(quote.amount_out / parseFloat(amount)).toFixed(6)} {toAsset}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-700 dark:text-gray-300">Price Impact</span>
              <span className={`font-medium ${quote.price_impact > 2 ? 'text-red-600' : 'text-green-600'}`}>
                {(quote.price_impact * 100).toFixed(2)}%
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-700 dark:text-gray-300">Platform Fee</span>
              <span className="text-gray-900 dark:text-white">${quote.fee_amount.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-700 dark:text-gray-300">Network Fee</span>
              <span className="text-gray-900 dark:text-white">~$0.001</span>
            </div>
            <div className="border-t-2 border-blue-300 dark:border-blue-700 pt-2 mt-2 flex justify-between">
              <span className="text-gray-900 dark:text-white font-semibold">You receive</span>
              <span className="text-gray-900 dark:text-white font-bold">
                {quote.amount_out.toFixed(4)} {toAsset}
              </span>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-800 rounded-lg p-3 mb-4 flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-900 dark:text-red-100 font-medium">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && !error && (
          <div className="flex items-center justify-center py-4 text-gray-600 dark:text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            <span className="font-medium">Fetching best rate...</span>
          </div>
        )}

        {/* ➕ Insufficient Balance Warning */}
        {parseFloat(amount) > 0 && balances[fromAsset] !== undefined && parseFloat(amount) > balances[fromAsset] && (
          <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-800 rounded-lg p-3 mb-4 flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-900 dark:text-red-100 font-medium">
              Insufficient balance. You have {balances[fromAsset].toFixed(6)} {fromAsset} available.
            </p>
          </div>
        )}

        {/* Swap Button - âœ… SOLID COLOR LIKE YOURS */}
        <button
          onClick={executeSwap}
          disabled={
            !quote || 
            swapping || 
            loading || 
            !!error ||
            (balances[fromAsset] !== undefined && parseFloat(amount) > balances[fromAsset])  // ➕ Balance check
          }
          className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold py-4 rounded-lg transition-all h-12 flex items-center justify-center gap-2"
        >
          {swapping ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Swapping...
            </>
          ) : (
            <>
              <ArrowDownUp className="h-5 w-5" />
              Swap Now
            </>
          )}
        </button>

        {/* Disclaimer */}
        <p className="text-xs text-gray-600 dark:text-gray-400 text-center mt-4 font-medium">
          Powered by Pact Finance DEX on Algorand MainNet
        </p>
      </div>
    </div>
  );
};