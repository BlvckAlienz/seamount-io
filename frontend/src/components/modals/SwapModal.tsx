// 📁 FILE: frontend/src/components/modals/SwapModal.tsx
// ✅ PRODUCTION SWAP MODAL - Mobile-First Responsive Design

import React, { useState, useEffect } from 'react';
import { X, ArrowDownUp, TrendingUp, AlertCircle, Check, Loader2 } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface SwapModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

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

  // Fetch balances when modal opens
  useEffect(() => {
    const fetchBalances = async () => {
      if (!open) return;
      
      setFetchingBalances(true);
      try {
        const response = await apiClient.get('/api/v1/wallet/balances');
        
        if (response?.data?.success && response.data.assets) {
          const balanceMap: Record<string, number> = {};
          
          response.data.assets.forEach((asset: any) => {
            const assetKey = asset.asset || asset.symbol || asset.chain?.toUpperCase();
            if (assetKey) {
              balanceMap[assetKey] = asset.balance || 0;
            }
          });
          
          setBalances(balanceMap);
        }
      } catch (err) {
        console.error('Failed to fetch balances:', err);
        setBalances({});
      } finally {
        setFetchingBalances(false);
      }
    };
    
    fetchBalances();
  }, [open]);

  // Auto-fetch quote when amount/assets change
  useEffect(() => {
    if (!amount || parseFloat(amount) <= 0 || !open) {
      setQuote(null);
      return;
    }

    const timer = setTimeout(() => {
      fetchQuote();
    }, 500);

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

        setAmount('');
        setQuote(null);
        onOpenChange(false);

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
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto p-2 sm:p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />

      {/* Modal - 📱 RESPONSIVE CONTAINER */}
      <div 
        className="relative bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600 rounded-xl sm:rounded-2xl p-4 sm:p-6 w-full max-w-[95vw] sm:max-w-[500px] shadow-2xl animate-in slide-in-from-bottom-4 duration-300 max-h-[90vh] overflow-y-auto"
        style={{ zIndex: 1000 }}
      >
        {/* Header - 📱 COMPACT ON MOBILE */}
        <div className="flex items-center justify-between mb-4 sm:mb-6">
          <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <ArrowDownUp className="h-5 w-5 sm:h-6 sm:w-6 text-purple-600" />
            <span className="hidden xs:inline">Swap Assets</span>
            <span className="xs:hidden">Swap</span>
          </h2>
          <button
            onClick={() => onOpenChange(false)}
            className="text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors p-1"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* From Asset - 📱 STACKED LAYOUT ON MOBILE */}
        <div className="mb-3 sm:mb-4">
          <label className="text-xs sm:text-sm font-semibold text-gray-900 dark:text-white mb-1.5 sm:mb-2 block">
            From
          </label>

          {/* Balance Display - 📱 COMPACT */}
          {balances[fromAsset] !== undefined && (
            <div className="flex justify-between items-center px-2 sm:px-3 py-1.5 sm:py-2 mb-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <span className="text-xs sm:text-sm text-gray-700 dark:text-gray-300">Available:</span>
              <span className="font-bold text-xs sm:text-sm text-blue-700 dark:text-blue-300">
                {balances[fromAsset].toFixed(6)} {fromAsset}
              </span>
            </div>
          )}

          {/* Input + Asset Selector - 📱 RESPONSIVE */}
          <div className="flex flex-col xs:flex-row gap-2">
            <div className="relative flex-1">
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className="w-full bg-white dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-500 rounded-lg px-3 sm:px-4 py-2.5 sm:py-3 text-gray-900 dark:text-white text-base sm:text-lg focus:outline-none focus:ring-2 focus:ring-purple-500 pr-14 sm:pr-16"
              />
              
              {/* MAX Button - 📱 RESPONSIVE */}
              {balances[fromAsset] > 0 && (
                <button
                  type="button"
                  onClick={() => setAmount(balances[fromAsset].toString())}
                  className="absolute right-2 top-1/2 -translate-y-1/2 px-2 sm:px-3 py-1 text-xs font-bold bg-purple-500 hover:bg-purple-600 text-white rounded-md sm:rounded-lg transition-colors"
                >
                  MAX
                </button>
              )}
            </div>

            {/* Asset Dropdown - 📱 FULL WIDTH ON SMALL SCREENS */}
            <select
              value={fromAsset}
              onChange={(e) => setFromAsset(e.target.value)}
              className="w-full xs:w-auto bg-white dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-500 rounded-lg px-3 sm:px-4 py-2.5 sm:py-3 text-gray-900 dark:text-white text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              {SUPPORTED_ASSETS.map((asset) => (
                <option key={asset.symbol} value={asset.symbol}>
                  {asset.symbol}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Swap Direction Button - 📱 TOUCH-FRIENDLY */}
        <div className="flex justify-center my-2 sm:my-3">
          <button
            onClick={swapAssets}
            className="bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 border-2 border-gray-300 dark:border-gray-500 rounded-full p-2 sm:p-2.5 transition-all hover:scale-110 active:scale-95"
          >
            <ArrowDownUp className="h-4 w-4 sm:h-5 sm:w-5 text-purple-600" />
          </button>
        </div>

        {/* To Asset - 📱 RESPONSIVE */}
        <div className="mb-4 sm:mb-6">
          <label className="text-xs sm:text-sm font-semibold text-gray-900 dark:text-white mb-1.5 sm:mb-2 block">
            To
          </label>
          <div className="flex flex-col xs:flex-row gap-2">
            <input
              type="text"
              value={quote ? quote.amount_out.toFixed(4) : '0.00'}
              readOnly
              placeholder="0.00"
              className="flex-1 bg-gray-100 dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-500 rounded-lg px-3 sm:px-4 py-2.5 sm:py-3 text-gray-900 dark:text-white text-base sm:text-lg focus:outline-none"
            />
            <select
              value={toAsset}
              onChange={(e) => setToAsset(e.target.value)}
              className="w-full xs:w-auto bg-white dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-500 rounded-lg px-3 sm:px-4 py-2.5 sm:py-3 text-gray-900 dark:text-white text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-purple-500"
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
            {/* NEW: Show explicit exchange rate */}
            <div className="flex justify-between items-center text-sm mb-3 pb-3 border-b-2 border-blue-200 dark:border-blue-700">
              <span className="text-gray-700 dark:text-gray-300 font-semibold">Exchange Rate</span>
              <span className="text-gray-900 dark:text-white font-bold">
                1 {fromAsset} = {quote.exchange_rate?.toFixed(6)} {toAsset}
              </span>
            </div>
            
            <div className="flex justify-between text-sm">
              <span className="text-gray-700 dark:text-gray-300">Amount Before Fees</span>
              <span className="text-gray-900 dark:text-white font-medium">
                {quote.amount_out_before_fees?.toFixed(4)} {toAsset}
              </span>
            </div>
            
            <div className="flex justify-between text-sm">
              <span className="text-gray-700 dark:text-gray-300">
                Platform Fee ({quote.fee_percentage?.toFixed(1)}%)
              </span>
              <span className="text-orange-600 dark:text-orange-400 font-medium">
                - {quote.fee_amount?.toFixed(4)} {toAsset}
              </span>
            </div>
            
            <div className="flex justify-between text-sm">
              <span className="text-gray-700 dark:text-gray-300">Price Impact</span>
              <span className={`font-medium ${
                quote.price_impact > 5 
                  ? 'text-red-600' 
                  : quote.price_impact > 2 
                  ? 'text-orange-600' 
                  : 'text-green-600'
              }`}>
                {quote.price_impact?.toFixed(2)}%
              </span>
            </div>
            
            <div className="flex justify-between text-sm">
              <span className="text-gray-700 dark:text-gray-300">Network Fee</span>
              <span className="text-gray-900 dark:text-white">~$0.001</span>
            </div>
            
            <div className="border-t-2 border-blue-300 dark:border-blue-700 pt-3 mt-3 flex justify-between items-center">
              <span className="text-gray-900 dark:text-white font-semibold">You Receive</span>
              <div className="text-right">
                <div className="text-gray-900 dark:text-white font-bold text-lg">
                  {quote.amount_out?.toFixed(4)} {toAsset}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Min: {quote.min_amount_out?.toFixed(4)} {toAsset}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* NEW: Rate Validation Warning */}
        {quote && quote.exchange_rate && (
          (() => {
            // Calculate expected rate range based on asset pair
            const expectedRates: { [key: string]: { min: number; max: number } } = {
              'USDT-ALGO': { min: 1.5, max: 5.0 },   // 1 USDT = 1.5-5 ALGO
              'ALGO-USDT': { min: 0.2, max: 0.7 },   // 1 ALGO = $0.20-$0.70
              'USDT-USDCa': { min: 0.98, max: 1.02 }, // 1:1 stables
            };
            
            const pairKey = `${fromAsset}-${toAsset}`;
            const expected = expectedRates[pairKey];
            
            if (expected) {
              const rate = quote.exchange_rate;
              const isOutOfRange = rate < expected.min || rate > expected.max;
              
              if (isOutOfRange) {
                return (
                  <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-800 rounded-lg p-3 mb-4 flex items-start gap-2">
                    <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm text-red-900 dark:text-red-100 font-semibold">
                        ⚠️ Unusual Exchange Rate Detected
                      </p>
                      <p className="text-xs text-red-800 dark:text-red-200 mt-1">
                        Rate: 1 {fromAsset} = {rate.toFixed(6)} {toAsset}<br />
                        Expected: {expected.min} - {expected.max}<br />
                        <strong>This quote may be inaccurate. Please double-check before proceeding.</strong>
                      </p>
                    </div>
                  </div>
                );
              }
            }
            
            return null;
          })()
        )}

        {/* NEW: Price Impact Warning */}
        {quote && quote.price_impact > 5 && (
          <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-800 rounded-lg p-3 mb-4 flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-red-900 dark:text-red-100 font-semibold">High Price Impact!</p>
              <p className="text-xs text-red-800 dark:text-red-200 mt-1">
                This swap will significantly affect the pool price. Consider reducing your amount.
              </p>
            </div>
          </div>
        )}

        {/* Error Display - 📱 COMPACT */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-800 rounded-lg p-2.5 sm:p-3 mb-3 sm:mb-4 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 sm:h-5 sm:w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs sm:text-sm text-red-900 dark:text-red-100 font-medium">{error}</p>
          </div>
        )}

        {/* Loading State - 📱 COMPACT */}
        {loading && !error && (
          <div className="flex items-center justify-center py-3 sm:py-4 text-gray-600 dark:text-gray-400">
            <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin mr-2" />
            <span className="font-medium text-xs sm:text-sm">Fetching best rate...</span>
          </div>
        )}

        {/* Insufficient Balance Warning - 📱 COMPACT */}
        {parseFloat(amount) > 0 && balances[fromAsset] !== undefined && parseFloat(amount) > balances[fromAsset] && (
          <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-800 rounded-lg p-2.5 sm:p-3 mb-3 sm:mb-4 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 sm:h-5 sm:w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs sm:text-sm text-red-900 dark:text-red-100 font-medium">
              Insufficient balance. You have {balances[fromAsset].toFixed(6)} {fromAsset} available.
            </p>
          </div>
        )}

        {/* Swap Button - 📱 TOUCH-FRIENDLY */}
        <button
          onClick={executeSwap}
          disabled={
            !quote || 
            swapping || 
            loading || 
            !!error ||
            (balances[fromAsset] !== undefined && parseFloat(amount) > balances[fromAsset])
          }
          className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold py-3 sm:py-4 rounded-lg transition-all flex items-center justify-center gap-2 text-sm sm:text-base active:scale-95"
        >
          {swapping ? (
            <>
              <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" />
              Swapping...
            </>
          ) : (
            <>
              <ArrowDownUp className="h-4 w-4 sm:h-5 sm:w-5" />
              Swap Now
            </>
          )}
        </button>

        {/* Disclaimer - 📱 COMPACT */}
        <p className="text-[10px] sm:text-xs text-gray-600 dark:text-gray-400 text-center mt-3 sm:mt-4 font-medium">
          Powered by Pact Finance DEX on Algorand MainNet
        </p>
      </div>
    </div>
  );
};