// 📁 FILE: frontend/src/components/modals/SwapModal.tsx
// UPDATED: Dual-tab swap — Algorand (existing) + WDK Velora EVM (new)

import React, { useState, useEffect } from 'react';
import { X, ArrowDownUp, TrendingUp, AlertCircle, Check, Loader2, Zap } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface SwapModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ── Asset definitions ──────────────────────────────────────────────
const ALGO_ASSETS = [
  { symbol: 'USDT',  name: 'Tether USD',      decimals: 6 },
  { symbol: 'ALGO',  name: 'Algorand',         decimals: 6 },
  { symbol: 'USDCa', name: 'USD Coin',         decimals: 6 },
  { symbol: 'goBTC', name: 'Wrapped Bitcoin',  decimals: 8 },
  { symbol: 'goETH', name: 'Wrapped Ethereum', decimals: 8 },
];

const WDK_ASSETS = [
  { symbol: 'USDT', name: 'Tether USD (EVM)',  chain: 'ethereum' },
  { symbol: 'USDC', name: 'USD Coin (EVM)',    chain: 'ethereum' },
];

const WDK_CHAINS = [
  { id: 'ethereum', label: 'Ethereum' },
  { id: 'polygon',  label: 'Polygon'  },
];

// ── Main Component ─────────────────────────────────────────────────
export const SwapModal: React.FC<SwapModalProps> = ({ open, onOpenChange }) => {
  const [activeTab, setActiveTab]     = useState<'algo' | 'wdk'>('algo');

  // ── Algorand state ─────────────────────────────────────────────
  const [fromAsset,        setFromAsset]        = useState('USDT');
  const [toAsset,          setToAsset]          = useState('ALGO');
  const [amount,           setAmount]           = useState('');
  const [quote,            setQuote]            = useState<any>(null);
  const [loading,          setLoading]          = useState(false);
  const [swapping,         setSwapping]         = useState(false);
  const [error,            setError]            = useState('');
  const [balances,         setBalances]         = useState<Record<string, number>>({});
  const [fetchingBalances, setFetchingBalances] = useState(false);

  // ── WDK (Velora) state ─────────────────────────────────────────
  const [wdkFromAsset, setWdkFromAsset] = useState('USDT');
  const [wdkToAsset,   setWdkToAsset]   = useState('USDC');
  const [wdkChain,     setWdkChain]     = useState('ethereum');
  const [wdkAmount,    setWdkAmount]    = useState('');
  const [wdkQuote,     setWdkQuote]     = useState<any>(null);
  const [wdkLoading,   setWdkLoading]   = useState(false);
  const [wdkSwapping,  setWdkSwapping]  = useState(false);
  const [wdkError,     setWdkError]     = useState('');

  // ── Fetch balances ─────────────────────────────────────────────
  useEffect(() => {
    if (!open) return;
    setFetchingBalances(true);
    apiClient.get('/api/v1/wallet/balances')
      .then(res => {
        if (res?.data?.success && res.data.assets) {
          const map: Record<string, number> = {};
          res.data.assets.forEach((a: any) => {
            const key = a.asset || a.symbol || a.chain?.toUpperCase();
            if (key) map[key] = a.balance || 0;
          });
          setBalances(map);
        }
      })
      .catch(() => setBalances({}))
      .finally(() => setFetchingBalances(false));
  }, [open]);

  // ── Algorand: auto-fetch quote ─────────────────────────────────
  useEffect(() => {
    if (!amount || parseFloat(amount) <= 0 || !open || activeTab !== 'algo') {
      setQuote(null);
      return;
    }
    const t = setTimeout(fetchAlgoQuote, 500);
    return () => clearTimeout(t);
  }, [amount, fromAsset, toAsset, open, activeTab]);

  // ── WDK: auto-fetch quote ──────────────────────────────────────
  useEffect(() => {
    if (!wdkAmount || parseFloat(wdkAmount) <= 0 || !open || activeTab !== 'wdk') {
      setWdkQuote(null);
      return;
    }
    const t = setTimeout(fetchWdkQuote, 500);
    return () => clearTimeout(t);
  }, [wdkAmount, wdkFromAsset, wdkToAsset, wdkChain, open, activeTab]);

  // ── Algorand quote ─────────────────────────────────────────────
  const fetchAlgoQuote = async () => {
    setLoading(true); setError('');
    try {
      const res = await apiClient.post('/api/v1/swap/quote', {
        from_asset: fromAsset,
        to_asset:   toAsset,
        amount:     parseFloat(amount),
      });
      if (res.data.success !== false) setQuote(res.data);
      else setError(res.data.error || 'Failed to get quote');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Unable to fetch quote');
      setQuote(null);
    } finally { setLoading(false); }
  };

  const executeAlgoSwap = async () => {
    if (!quote) { toast.error('Get a quote first'); return; }
    setSwapping(true);
    try {
      const res = await apiClient.post('/api/v1/swap/execute', {
        from_asset: fromAsset, to_asset: toAsset, amount: parseFloat(amount),
      });
      if (res.data.success) {
        toast.success(`✅ Swap successful! Received ${res.data.amount_out.toFixed(4)} ${toAsset}`);
        setAmount(''); setQuote(null); onOpenChange(false);
        window.dispatchEvent(new Event('wallet-balance-updated'));
      } else throw new Error(res.data.error || 'Swap failed');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Swap failed. Try again.');
    } finally { setSwapping(false); }
  };

  // ── WDK quote ──────────────────────────────────────────────────
  const fetchWdkQuote = async () => {
    if (wdkFromAsset === wdkToAsset) {
      setWdkError('Select different tokens'); return;
    }
    setWdkLoading(true); setWdkError('');
    try {
      const res = await apiClient.post('/api/v1/wdk/swap', {
        token_in:  wdkFromAsset,
        token_out: wdkToAsset,
        amount_in: parseFloat(wdkAmount),
        chain:     wdkChain,
        // quote-only mode — backend should detect and return quote without executing
        quote_only: true,
      });
      if (res.data.success !== false) setWdkQuote(res.data);
      else setWdkError(res.data.error || 'Failed to get quote');
    } catch (err: any) {
      setWdkError(err.response?.data?.detail || 'Unable to fetch quote');
      setWdkQuote(null);
    } finally { setWdkLoading(false); }
  };

  const executeWdkSwap = async () => {
    if (!wdkQuote) { toast.error('Get a quote first'); return; }
    setWdkSwapping(true);
    try {
      const res = await apiClient.post('/api/v1/wdk/swap', {
        token_in:  wdkFromAsset,
        token_out: wdkToAsset,
        amount_in: parseFloat(wdkAmount),
        chain:     wdkChain,
      });
      if (res.data.success) {
        toast.success(`✅ EVM Swap done! Tx: ${res.data.tx_hash?.slice(0, 10)}...`);
        setWdkAmount(''); setWdkQuote(null); onOpenChange(false);
        window.dispatchEvent(new Event('wallet-balance-updated'));
      } else throw new Error(res.data.error || 'WDK swap failed');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'WDK Swap failed. Try again.');
    } finally { setWdkSwapping(false); }
  };

  const swapAlgoAssets = () => { const t = fromAsset; setFromAsset(toAsset); setToAsset(t); };
  const swapWdkAssets  = () => { const t = wdkFromAsset; setWdkFromAsset(wdkToAsset); setWdkToAsset(t); };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto p-2 sm:p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => onOpenChange(false)} />

      <div
        className="relative bg-white border-2 border-gray-200 rounded-xl sm:rounded-2xl p-4 sm:p-6 w-full max-w-[95vw] sm:max-w-[500px] shadow-2xl animate-in slide-in-from-bottom-4 duration-300 max-h-[90vh] overflow-y-auto"
        style={{ zIndex: 1000 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg sm:text-xl font-bold text-gray-900 flex items-center gap-2">
            <ArrowDownUp className="h-5 w-5 text-purple-600" />
            Swap Assets
          </h2>
          <button onClick={() => onOpenChange(false)} className="text-gray-400 hover:text-gray-900 p-1">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex rounded-lg border border-gray-200 mb-5 overflow-hidden">
          <button
            className={`flex-1 py-2 text-sm font-semibold transition-colors ${
              activeTab === 'algo'
                ? 'bg-purple-600 text-white'
                : 'bg-transparent text-gray-600 hover:bg-gray-100'
            }`}
            onClick={() => setActiveTab('algo')}
          >
            Algorand DEX
          </button>
          <button
            className={`flex-1 py-2 text-sm font-semibold flex items-center justify-center gap-1.5 transition-colors ${
              activeTab === 'wdk'
                ? 'bg-blue-600 text-white'
                : 'bg-transparent text-gray-600 hover:bg-gray-100'
            }`}
            onClick={() => setActiveTab('wdk')}
          >
            <Zap className="h-3.5 w-3.5" /> EVM (Velora)
          </button>
        </div>

        {/* ── ALGORAND TAB ── */}
        {activeTab === 'algo' && (
          <>
            {/* From */}
            <div className="mb-3">
              <label className="text-xs font-semibold text-gray-900 mb-1 block">From</label>
              {balances[fromAsset] !== undefined && (
                <div className="flex justify-between items-center px-3 py-1.5 mb-2 bg-blue-50 rounded-lg border border-blue-200">
                  <span className="text-xs text-gray-700">Available:</span>
                  <span className="font-bold text-xs text-blue-700">
                    {balances[fromAsset].toFixed(6)} {fromAsset}
                  </span>
                </div>
              )}
              <div className="flex gap-2">
                <input
                  type="number" value={amount} onChange={e => setAmount(e.target.value)}
                  placeholder="0.00"
                  className="flex-1 bg-white border-2 border-gray-300 rounded-lg px-3 py-2.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <select
                  value={fromAsset} onChange={e => setFromAsset(e.target.value)}
                  className="bg-white border-2 border-gray-300 rounded-lg px-2 py-2.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  {ALGO_ASSETS.map(a => <option key={a.symbol} value={a.symbol}>{a.symbol}</option>)}
                </select>
              </div>
            </div>

            {/* Swap button */}
            <div className="flex justify-center my-2">
              <button onClick={swapAlgoAssets} className="p-2 bg-purple-100 rounded-full hover:bg-purple-200 transition-colors">
                <ArrowDownUp className="h-4 w-4 text-purple-600" />
              </button>
            </div>

            {/* To */}
            <div className="mb-4">
              <label className="text-xs font-semibold text-gray-900 mb-1 block">To</label>
              <select
                value={toAsset} onChange={e => setToAsset(e.target.value)}
                className="w-full bg-white border-2 border-gray-300 rounded-lg px-3 py-2.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                {ALGO_ASSETS.filter(a => a.symbol !== fromAsset).map(a => (
                  <option key={a.symbol} value={a.symbol}>{a.symbol} — {a.name}</option>
                ))}
              </select>
            </div>

            {/* Error */}
            {error && (
              <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                <span className="text-xs text-red-700">{error}</span>
              </div>
            )}

            {/* Quote */}
            {loading && <div className="flex items-center justify-center py-4"><Loader2 className="h-5 w-5 animate-spin text-purple-600" /></div>}
            {quote && !loading && (
              <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded-lg space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-600">You receive</span>
                  <span className="font-bold text-purple-700">
                    {quote.amount_out?.toFixed(6)} {toAsset}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-600">Rate</span>
                  <span className="text-gray-800">
                    1 {fromAsset} = {quote.exchange_rate?.toFixed(6)} {toAsset}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-600">Fee</span>
                  <span className="text-gray-800">
                    {quote.fee_percentage?.toFixed(2)}%
                  </span>
                </div>
              </div>
            )}

            <button
              onClick={executeAlgoSwap}
              disabled={swapping || loading || !quote || !amount}
              className="w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-300 text-white rounded-xl font-semibold transition-colors flex items-center justify-center gap-2"
            >
              {swapping ? <><Loader2 className="h-4 w-4 animate-spin" /> Swapping...</> : 'Swap'}
            </button>
          </>
        )}

        {/* ── WDK VELORA TAB ── */}
        {activeTab === 'wdk' && (
          <>
            {/* Chain selector */}
            <div className="mb-3">
              <label className="text-xs font-semibold text-gray-900 mb-1 block">Chain</label>
              <div className="flex gap-2">
                {WDK_CHAINS.map(c => (
                  <button
                    key={c.id}
                    onClick={() => setWdkChain(c.id)}
                    className={`flex-1 py-1.5 text-xs rounded-lg border font-semibold transition-colors ${
                      wdkChain === c.id
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 text-gray-600 hover:border-blue-400'
                    }`}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            {/* From */}
            <div className="mb-3">
              <label className="text-xs font-semibold text-gray-900 mb-1 block">From</label>
              <div className="flex gap-2">
                <input
                  type="number" value={wdkAmount} onChange={e => setWdkAmount(e.target.value)}
                  placeholder="0.00"
                  className="flex-1 bg-white border-2 border-gray-300 rounded-lg px-3 py-2.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <select
                  value={wdkFromAsset} onChange={e => setWdkFromAsset(e.target.value)}
                  className="bg-white border-2 border-gray-300 rounded-lg px-2 py-2.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {WDK_ASSETS.map(a => <option key={a.symbol} value={a.symbol}>{a.symbol}</option>)}
                </select>
              </div>
            </div>

            {/* Swap direction */}
            <div className="flex justify-center my-2">
              <button onClick={swapWdkAssets} className="p-2 bg-blue-100 rounded-full hover:bg-blue-200 transition-colors">
                <ArrowDownUp className="h-4 w-4 text-blue-600" />
              </button>
            </div>

            {/* To */}
            <div className="mb-4">
              <label className="text-xs font-semibold text-gray-900 mb-1 block">To</label>
              <select
                value={wdkToAsset} onChange={e => setWdkToAsset(e.target.value)}
                className="w-full bg-white border-2 border-gray-300 rounded-lg px-3 py-2.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {WDK_ASSETS.filter(a => a.symbol !== wdkFromAsset).map(a => (
                  <option key={a.symbol} value={a.symbol}>{a.symbol} — {a.name}</option>
                ))}
              </select>
            </div>

            {/* Error */}
            {wdkError && (
              <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                <span className="text-xs text-red-700">{wdkError}</span>
              </div>
            )}

            {/* Quote */}
            {wdkLoading && <div className="flex items-center justify-center py-4"><Loader2 className="h-5 w-5 animate-spin text-blue-600" /></div>}
            {wdkQuote && !wdkLoading && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-600">You receive (est.)</span>
                  <span className="font-bold text-blue-700">
                    {wdkQuote.amount_out ?? '—'} {wdkToAsset}
                  </span>
                </div>
                {wdkQuote.fee && (
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">Est. fee</span>
                    <span className="text-gray-800">{wdkQuote.fee} wei</span>
                  </div>
                )}
                <div className="text-xs text-blue-600 flex items-center gap-1">
                  <Zap className="h-3 w-3" /> Powered by Velora on {wdkChain.charAt(0).toUpperCase() + wdkChain.slice(1)}
                </div>
              </div>
            )}

            <button
              onClick={executeWdkSwap}
              disabled={wdkSwapping || wdkLoading || !wdkQuote || !wdkAmount}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-xl font-semibold transition-colors flex items-center justify-center gap-2"
            >
              {wdkSwapping ? <><Loader2 className="h-4 w-4 animate-spin" /> Swapping...</> : 'Swap via Velora'}
            </button>

            <p className="text-center text-xs text-gray-500 mt-2">
              EVM swap powered by Tether WDK + Velora DEX
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default SwapModal;