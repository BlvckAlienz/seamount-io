// File: frontend/src/pages/XRPPage.tsx
// XRP Ledger Hub — Balances · Deposit · Transfer · Withdraw · Yield Farming

import React, { useState, useEffect, useCallback } from 'react';
import {
  Waves, Copy, RefreshCw, ArrowUpRight, ArrowDownToLine,
  TrendingUp, AlertCircle, CheckCircle2, Loader2,
  ChevronRight, Info, ExternalLink, Coins,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';
import Sidebar from '@/components/layout/Sidebar';

// ─── Types ────────────────────────────────────────────────────────────────────

type Tab = 'overview' | 'transfer' | 'yield';

interface XRPBalances { RLUSD: string; USDC: string; XRP: string; }
interface DepositInfo {
  deposit_address: string;
  destination_tag: number;
  supported_assets: string[];
  warning: string;
}
interface YieldPosition {
  id: string; pool: string; token_deposited: number; yield_earned: number;
  status: string; created_at: string; estimated_apy_pct: number | null; days_active: number;
}
interface YieldPool {
  pool: string; success: boolean;
  on_chain: { trading_fee_pct: number | null };
  seamount_position: { active_user_positions: number; total_token_deposited: string };
  minimum_deposit: string; asset: string;
}

// ─── Small helpers ─────────────────────────────────────────────────────────────

const SYMBOL_COLORS: Record<string, string> = {
  RLUSD: 'text-blue-400', USDC: 'text-green-400', XRP: 'text-purple-400',
};
const SYMBOL_BG: Record<string, string> = {
  RLUSD: 'bg-blue-500/10 border-blue-500/30',
  USDC:  'bg-green-500/10 border-green-500/30',
  XRP:   'bg-purple-500/10 border-purple-500/30',
};

const fmt = (n: string | number, dec = 4) =>
  parseFloat(String(n)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: dec });

const copyToClipboard = (text: string, label: string) => {
  navigator.clipboard.writeText(text).then(() => toast.success(`${label} copied!`));
};

// ─── Sub-components ───────────────────────────────────────────────────────────

const Spinner = () => (
  <Loader2 className="h-4 w-4 animate-spin" />
);

const StatCard: React.FC<{ label: string; value: string; sub?: string; color?: string }> = ({ label, value, sub, color = 'text-white' }) => (
  <div className="bg-gray-800/60 border border-gray-700/50 rounded-xl p-4">
    <p className="text-xs text-gray-400 mb-1">{label}</p>
    <p className={`text-xl font-bold ${color}`}>{value}</p>
    {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
  </div>
);

// ─── Main Page ────────────────────────────────────────────────────────────────

const XRPPage: React.FC = () => {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>('overview');

  // Data state
  const [balances, setBalances] = useState<XRPBalances>({ RLUSD: '0', USDC: '0', XRP: '0' });
  const [depositInfo, setDepositInfo] = useState<DepositInfo | null>(null);
  const [positions, setPositions] = useState<YieldPosition[]>([]);
  const [pools, setPools] = useState<YieldPool[]>([]);
  const [loadingBalances, setLoadingBalances] = useState(true);
  const [loadingDeposit, setLoadingDeposit] = useState(true);
  const [loadingYield, setLoadingYield] = useState(false);

  // Transfer form
  const [transferRecipient, setTransferRecipient] = useState('');
  const [transferSymbol, setTransferSymbol] = useState('RLUSD');
  const [transferAmount, setTransferAmount] = useState('');
  const [transferMemo, setTransferMemo] = useState('');
  const [transferring, setTransferring] = useState(false);

  // Withdraw form
  const [withdrawSymbol, setWithdrawSymbol] = useState('RLUSD');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [withdrawAddress, setWithdrawAddress] = useState('');
  const [withdrawTag, setWithdrawTag] = useState('');
  const [withdrawing, setWithdrawing] = useState(false);
  const [showWithdraw, setShowWithdraw] = useState(false);

  // Yield deposit form
  const [yieldPool, setYieldPool] = useState('RLUSD/XRP');
  const [yieldAmount, setYieldAmount] = useState('');
  const [depositing, setDepositing] = useState(false);

  // ── Fetchers ──────────────────────────────────────────────────────────────

  const fetchBalances = useCallback(async () => {
    if (!user) return;
    setLoadingBalances(true);
    try {
      const r = await apiClient.get('/api/v1/xrp/balances');
      if (r.data?.success) setBalances(r.data.balances);
    } catch (e) {
      console.error('XRP balances fetch failed:', e);
    } finally {
      setLoadingBalances(false);
    }
  }, [user]);

  const fetchDepositInfo = useCallback(async () => {
    if (!user) return;
    setLoadingDeposit(true);
    try {
      const r = await apiClient.get('/api/v1/xrp/deposit-info');
      if (r.data?.success) setDepositInfo(r.data);
    } catch (e) {
      console.error('XRP deposit info fetch failed:', e);
    } finally {
      setLoadingDeposit(false);
    }
  }, [user]);

  const fetchYield = useCallback(async () => {
    if (!user) return;
    setLoadingYield(true);
    try {
      const [posRes, poolRes] = await Promise.all([
        apiClient.get('/api/v1/xrp/yield/positions'),
        apiClient.get('/api/v1/xrp/yield/pools'),
      ]);
      if (posRes.data?.success) setPositions(posRes.data.positions || []);
      if (poolRes.data?.success) setPools(poolRes.data.pools || []);
    } catch (e) {
      console.error('XRP yield fetch failed:', e);
    } finally {
      setLoadingYield(false);
    }
  }, [user]);

  useEffect(() => {
    fetchBalances();
    fetchDepositInfo();
  }, [fetchBalances, fetchDepositInfo]);

  useEffect(() => {
    if (tab === 'yield') fetchYield();
  }, [tab, fetchYield]);

  // ── Actions ───────────────────────────────────────────────────────────────

  const handleTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!transferRecipient || !transferAmount) return;
    setTransferring(true);
    try {
      const r = await apiClient.post('/api/v1/xrp/transfer', {
        recipient_id: transferRecipient,
        symbol: transferSymbol,
        amount: transferAmount,
        memo: transferMemo || undefined,
      });
      if (r.data?.success) {
        toast.success(`✅ ${transferAmount} ${transferSymbol} sent instantly — $0.00 fee`);
        setTransferAmount(''); setTransferRecipient(''); setTransferMemo('');
        fetchBalances();
      } else {
        toast.error(r.data?.detail || 'Transfer failed');
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Transfer failed');
    } finally {
      setTransferring(false);
    }
  };

  const handleWithdraw = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!withdrawAmount || !withdrawAddress) return;
    setWithdrawing(true);
    try {
      const r = await apiClient.post('/api/v1/xrp/withdraw', {
        symbol: withdrawSymbol,
        amount: withdrawAmount,
        destination_address: withdrawAddress,
        destination_tag: withdrawTag ? parseInt(withdrawTag) : undefined,
      });
      if (r.data?.success) {
        toast.success(`✅ ${withdrawAmount} ${withdrawSymbol} withdrawal submitted`);
        setWithdrawAmount(''); setWithdrawAddress(''); setWithdrawTag('');
        setShowWithdraw(false);
        fetchBalances();
      } else {
        toast.error(r.data?.detail || 'Withdrawal failed');
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Withdrawal failed');
    } finally {
      setWithdrawing(false);
    }
  };

  const handleYieldDeposit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!yieldAmount) return;
    setDepositing(true);
    try {
      const r = await apiClient.post('/api/v1/xrp/yield/deposit', {
        pool: yieldPool,
        amount: yieldAmount,
      });
      if (r.data?.success) {
        toast.success(`✅ ${yieldAmount} deposited into ${yieldPool} pool`);
        setYieldAmount('');
        fetchBalances();
        fetchYield();
      } else {
        toast.error(r.data?.detail || 'Deposit failed');
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Deposit failed');
    } finally {
      setDepositing(false);
    }
  };

  const handleYieldWithdraw = async (positionId: string) => {
    if (!confirm('Withdraw this position? Principal + yield will be returned to your balance.')) return;
    try {
      const r = await apiClient.post('/api/v1/xrp/yield/withdraw', { position_id: positionId });
      if (r.data?.success) {
        toast.success(`✅ ${r.data.total_returned} ${r.data.symbol} returned to balance`);
        fetchBalances(); fetchYield();
      } else {
        toast.error(r.data?.detail || 'Withdrawal failed');
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Withdrawal failed');
    }
  };

  // ── Total USD estimate (XRP @ $0.50 approximation for display) ────────────
  const totalUSD = (
    parseFloat(balances.RLUSD) +
    parseFloat(balances.USDC) +
    parseFloat(balances.XRP) * 0.5
  ).toFixed(2);

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />

      <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
        <div className="max-w-5xl mx-auto">

          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/10 rounded-xl border border-blue-500/30">
                <Waves className="h-6 w-6 text-blue-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">XRP Ledger</h1>
                <p className="text-sm text-gray-400">RLUSD · USDC · XRP — 3s settlement, near-zero fees</p>
              </div>
            </div>
            <button
              onClick={() => { fetchBalances(); fetchDepositInfo(); if (tab === 'yield') fetchYield(); }}
              className="p-2 text-gray-400 hover:text-white transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${loadingBalances ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Balance Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <StatCard
              label="Total Value (est.)"
              value={loadingBalances ? '...' : `$${fmt(totalUSD, 2)}`}
              sub="RLUSD + USDC + XRP"
              color="text-green-400"
            />
            {(['RLUSD', 'USDC', 'XRP'] as const).map(sym => (
              <div key={sym} className={`border rounded-xl p-4 ${SYMBOL_BG[sym]}`}>
                <p className="text-xs text-gray-400 mb-1">{sym}</p>
                <p className={`text-xl font-bold ${SYMBOL_COLORS[sym]}`}>
                  {loadingBalances ? <Spinner /> : fmt(balances[sym])}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {sym === 'XRP' ? 'native' : 'stablecoin'}
                </p>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mb-6 bg-gray-800/60 rounded-xl p-1 w-fit">
            {([
              { id: 'overview', label: 'Overview', icon: Coins },
              { id: 'transfer', label: 'Transfer', icon: ArrowUpRight },
              { id: 'yield',    label: 'Yield',    icon: TrendingUp },
            ] as { id: Tab; label: string; icon: React.ElementType }[]).map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  tab === t.id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <t.icon className="h-4 w-4" />
                {t.label}
              </button>
            ))}
          </div>

          {/* ── OVERVIEW TAB ─────────────────────────────────────────────── */}
          {tab === 'overview' && (
            <div className="space-y-5">
              {/* Deposit Info */}
              <div className="bg-gray-800/60 border border-gray-700/50 rounded-2xl p-5">
                <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                  <ArrowDownToLine className="h-5 w-5 text-blue-400" />
                  Deposit to Your XRP Account
                </h2>

                {loadingDeposit ? (
                  <div className="flex items-center gap-2 text-gray-400 py-4">
                    <Spinner /> Loading deposit info...
                  </div>
                ) : depositInfo ? (
                  <div className="space-y-4">
                    {/* Warning */}
                    <div className="flex items-start gap-3 p-3 bg-orange-900/20 border border-orange-500/30 rounded-xl">
                      <AlertCircle className="h-4 w-4 text-orange-400 mt-0.5 shrink-0" />
                      <p className="text-xs text-orange-300">{depositInfo.warning}</p>
                    </div>

                    {/* Address */}
                    <div>
                      <p className="text-xs text-gray-400 mb-1">Seamount Hot Wallet Address</p>
                      <div className="flex items-center gap-2 bg-gray-900/60 rounded-xl p-3 border border-gray-700/50">
                        <code className="text-sm text-green-400 font-mono flex-1 break-all">
                          {depositInfo.deposit_address}
                        </code>
                        <button
                          onClick={() => copyToClipboard(depositInfo.deposit_address, 'Address')}
                          className="text-gray-400 hover:text-white transition-colors shrink-0"
                        >
                          <Copy className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    {/* Destination Tag — the critical field */}
                    <div>
                      <p className="text-xs text-gray-400 mb-1">Your Destination Tag
                        <span className="ml-1 text-red-400 font-bold">*Required*</span>
                      </p>
                      <div className="flex items-center gap-2 bg-red-900/20 rounded-xl p-3 border border-red-500/40">
                        <code className="text-2xl font-bold text-red-300 flex-1 font-mono">
                          {depositInfo.destination_tag}
                        </code>
                        <button
                          onClick={() => copyToClipboard(String(depositInfo.destination_tag), 'Destination tag')}
                          className="text-gray-400 hover:text-white transition-colors"
                        >
                          <Copy className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    {/* Accepted assets */}
                    <div className="flex gap-2 flex-wrap">
                      {depositInfo.supported_assets.map(a => (
                        <span key={a} className={`px-3 py-1 rounded-full text-xs font-medium border ${SYMBOL_BG[a] || 'bg-gray-700 border-gray-600 text-gray-300'} ${SYMBOL_COLORS[a] || ''}`}>
                          {a}
                        </span>
                      ))}
                    </div>

                    <p className="text-xs text-gray-500 flex items-center gap-1">
                      <Info className="h-3 w-3" />
                      Deposits confirm in ~3–5 seconds on XRPL mainnet.
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-gray-400">XRP account not set up yet. Contact support.</p>
                )}
              </div>

              {/* Transaction History preview */}
              <XRPTxHistory />
            </div>
          )}

          {/* ── TRANSFER TAB ─────────────────────────────────────────────── */}
          {tab === 'transfer' && (
            <div className="space-y-5">
              {/* Internal Transfer */}
              <div className="bg-gray-800/60 border border-gray-700/50 rounded-2xl p-5">
                <h2 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
                  <ArrowUpRight className="h-5 w-5 text-green-400" />
                  Send to Seamount User
                </h2>
                <p className="text-xs text-gray-400 mb-5">
                  Instant · $0.00 fee · No blockchain transaction
                </p>

                <form onSubmit={handleTransfer} className="space-y-4">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Recipient User ID</label>
                    <input
                      type="text"
                      value={transferRecipient}
                      onChange={e => setTransferRecipient(e.target.value)}
                      placeholder="Paste recipient's Seamount user ID"
                      required
                      className="w-full bg-gray-900/60 border border-gray-600 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Asset</label>
                      <select
                        value={transferSymbol}
                        onChange={e => setTransferSymbol(e.target.value)}
                        className="w-full bg-gray-900/60 border border-gray-600 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
                      >
                        <option>RLUSD</option>
                        <option>USDC</option>
                        <option>XRP</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">
                        Amount
                        <span className="ml-1 text-gray-500">
                          (bal: {fmt(balances[transferSymbol as keyof XRPBalances] || '0', 2)})
                        </span>
                      </label>
                      <input
                        type="number"
                        value={transferAmount}
                        onChange={e => setTransferAmount(e.target.value)}
                        placeholder="0.00"
                        min="0.000001"
                        step="any"
                        required
                        className="w-full bg-gray-900/60 border border-gray-600 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Memo (optional)</label>
                    <input
                      type="text"
                      value={transferMemo}
                      onChange={e => setTransferMemo(e.target.value)}
                      placeholder="Payment note..."
                      maxLength={100}
                      className="w-full bg-gray-900/60 border border-gray-600 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div className="flex items-center justify-between p-3 bg-green-900/10 border border-green-500/20 rounded-xl">
                    <span className="text-sm text-gray-400">Network fee</span>
                    <span className="text-sm font-bold text-green-400">$0.00</span>
                  </div>

                  <button
                    type="submit"
                    disabled={transferring}
                    className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white py-3 rounded-xl font-semibold transition-colors"
                  >
                    {transferring ? <><Spinner /> Sending...</> : <><ArrowUpRight className="h-4 w-4" /> Send Instantly</>}
                  </button>
                </form>
              </div>

              {/* External Withdraw */}
              <div className="bg-gray-800/60 border border-gray-700/50 rounded-2xl p-5">
                <button
                  onClick={() => setShowWithdraw(v => !v)}
                  className="w-full flex items-center justify-between text-left"
                >
                  <div>
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                      <ArrowDownToLine className="h-5 w-5 text-orange-400" />
                      Withdraw to External Wallet
                    </h2>
                    <p className="text-xs text-gray-400 mt-0.5">On-chain · ~3s · Small fee applies</p>
                  </div>
                  <ChevronRight className={`h-5 w-5 text-gray-400 transition-transform ${showWithdraw ? 'rotate-90' : ''}`} />
                </button>

                {showWithdraw && (
                  <form onSubmit={handleWithdraw} className="space-y-4 mt-5">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-gray-400 mb-1">Asset</label>
                        <select
                          value={withdrawSymbol}
                          onChange={e => setWithdrawSymbol(e.target.value)}
                          className="w-full bg-gray-900/60 border border-gray-600 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
                        >
                          <option>RLUSD</option>
                          <option>USDC</option>
                          <option>XRP</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-400 mb-1">Amount</label>
                        <input
                          type="number"
                          value={withdrawAmount}
                          onChange={e => setWithdrawAmount(e.target.value)}
                          placeholder="0.00"
                          min="0"
                          step="any"
                          required
                          className="w-full bg-gray-900/60 border border-gray-600 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs text-gray-400 mb-1">XRPL Destination Address</label>
                      <input
                        type="text"
                        value={withdrawAddress}
                        onChange={e => setWithdrawAddress(e.target.value)}
                        placeholder="r..."
                        required
                        className="w-full bg-gray-900/60 border border-gray-600 rounded-xl px-4 py-3 text-white text-sm font-mono placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs text-gray-400 mb-1">
                        Destination Tag <span className="text-gray-500">(if required by exchange)</span>
                      </label>
                      <input
                        type="number"
                        value={withdrawTag}
                        onChange={e => setWithdrawTag(e.target.value)}
                        placeholder="Optional"
                        className="w-full bg-gray-900/60 border border-gray-600 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-sm p-3 bg-gray-900/40 rounded-xl">
                      <span className="text-gray-400">Min withdrawal</span>
                      <span className="text-right text-white">
                        {withdrawSymbol === 'XRP' ? '0.1 XRP' : `1.00 ${withdrawSymbol}`}
                      </span>
                      <span className="text-gray-400">Fee</span>
                      <span className="text-right text-orange-300">
                        {withdrawSymbol === 'XRP' ? '0.05 XRP' : `0.50 ${withdrawSymbol}`}
                      </span>
                    </div>

                    <button
                      type="submit"
                      disabled={withdrawing}
                      className="w-full flex items-center justify-center gap-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white py-3 rounded-xl font-semibold transition-colors"
                    >
                      {withdrawing ? <><Spinner /> Processing...</> : 'Confirm Withdrawal'}
                    </button>
                  </form>
                )}
              </div>
            </div>
          )}

          {/* ── YIELD TAB ─────────────────────────────────────────────────── */}
          {tab === 'yield' && (
            <div className="space-y-5">
              {/* Pool Stats */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {loadingYield ? (
                  <div className="col-span-2 flex items-center gap-2 text-gray-400 py-6 justify-center">
                    <Spinner /> Loading pools...
                  </div>
                ) : pools.map(pool => (
                  <div key={pool.pool} className="bg-gray-800/60 border border-gray-700/50 rounded-2xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-bold text-white">{pool.pool}</h3>
                      {pool.on_chain.trading_fee_pct && (
                        <span className="text-xs px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded-full">
                          {pool.on_chain.trading_fee_pct.toFixed(2)}% fee
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <p className="text-gray-500 text-xs">Min deposit</p>
                        <p className="text-white">{pool.minimum_deposit} {pool.asset}</p>
                      </div>
                      <div>
                        <p className="text-gray-500 text-xs">Total deposited</p>
                        <p className="text-white">{fmt(pool.seamount_position.total_token_deposited, 2)} {pool.asset}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Deposit into Yield */}
              <div className="bg-gray-800/60 border border-gray-700/50 rounded-2xl p-5">
                <h2 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-yellow-400" />
                  Deposit & Earn
                </h2>
                <p className="text-xs text-gray-400 mb-5">
                  Earn AMM trading fees proportional to your share. Yield credited daily.
                </p>

                <form onSubmit={handleYieldDeposit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Pool</label>
                      <select
                        value={yieldPool}
                        onChange={e => setYieldPool(e.target.value)}
                        className="w-full bg-gray-900/60 border border-gray-600 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-yellow-500"
                      >
                        <option value="RLUSD/XRP">RLUSD / XRP</option>
                        <option value="USDC/XRP">USDC / XRP</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">
                        Amount
                        <span className="ml-1 text-gray-500">
                          (bal: {fmt(balances[yieldPool.split('/')[0] as keyof XRPBalances] || '0', 2)})
                        </span>
                      </label>
                      <input
                        type="number"
                        value={yieldAmount}
                        onChange={e => setYieldAmount(e.target.value)}
                        placeholder="Min 10.00"
                        min="10"
                        step="any"
                        required
                        className="w-full bg-gray-900/60 border border-gray-600 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-yellow-500"
                      />
                    </div>
                  </div>

                  <div className="p-3 bg-yellow-900/10 border border-yellow-500/20 rounded-xl text-xs text-yellow-300 space-y-1">
                    <p>• Your funds enter the XRPL AMM pool alongside XRP</p>
                    <p>• You earn a share of all trading fees generated by the pool</p>
                    <p>• Yield is credited daily to your RLUSD/USDC balance</p>
                    <p>• Withdraw any time — principal + accrued yield returned</p>
                  </div>

                  <button
                    type="submit"
                    disabled={depositing}
                    className="w-full flex items-center justify-center gap-2 bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50 text-white py-3 rounded-xl font-semibold transition-colors"
                  >
                    {depositing ? <><Spinner /> Depositing...</> : <><TrendingUp className="h-4 w-4" /> Start Earning</>}
                  </button>
                </form>
              </div>

              {/* Active Positions */}
              {positions.length > 0 && (
                <div className="bg-gray-800/60 border border-gray-700/50 rounded-2xl p-5">
                  <h2 className="text-lg font-bold text-white mb-4">Your Yield Positions</h2>
                  <div className="space-y-3">
                    {positions.map(pos => (
                      <div
                        key={pos.id}
                        className={`p-4 rounded-xl border ${pos.status === 'active' ? 'border-yellow-500/30 bg-yellow-900/10' : 'border-gray-700/30 bg-gray-900/20'}`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-white">{pos.pool}</span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${pos.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-gray-600 text-gray-400'}`}>
                              {pos.status}
                            </span>
                          </div>
                          {pos.estimated_apy_pct && (
                            <span className="text-xs text-yellow-400">
                              ~{pos.estimated_apy_pct.toFixed(1)}% APY
                            </span>
                          )}
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-sm mb-3">
                          <div>
                            <p className="text-gray-500 text-xs">Deposited</p>
                            <p className="text-white">{fmt(pos.token_deposited)}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">Yield earned</p>
                            <p className="text-green-400">{fmt(pos.yield_earned, 6)}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">Days active</p>
                            <p className="text-white">{pos.days_active}</p>
                          </div>
                        </div>
                        {pos.status === 'active' && (
                          <button
                            onClick={() => handleYieldWithdraw(pos.id)}
                            className="text-xs px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                          >
                            Withdraw Position
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {positions.length === 0 && !loadingYield && (
                <div className="text-center py-10 text-gray-500">
                  <TrendingUp className="h-10 w-10 mx-auto mb-3 opacity-30" />
                  <p>No yield positions yet.</p>
                  <p className="text-sm">Deposit above to start earning.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ─── TX History sub-component ─────────────────────────────────────────────────

const XRPTxHistory: React.FC = () => {
  const [txs, setTxs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get('/api/v1/xrp/transactions?limit=8')
      .then(r => { if (r.data?.success) setTxs(r.data.transactions || []); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const typeLabel: Record<string, string> = {
    deposit: '↓ Deposit',
    withdrawal: '↑ Withdraw',
    internal_transfer: '⇄ Transfer',
    amm_deposit: '+ Yield deposit',
    amm_withdrawal: '- Yield withdraw',
    yield_credit: '✦ Yield',
  };

  const typeColor: Record<string, string> = {
    deposit: 'text-green-400',
    withdrawal: 'text-red-400',
    internal_transfer: 'text-blue-400',
    amm_deposit: 'text-yellow-400',
    amm_withdrawal: 'text-orange-400',
    yield_credit: 'text-yellow-300',
  };

  return (
    <div className="bg-gray-800/60 border border-gray-700/50 rounded-2xl p-5">
      <h2 className="text-lg font-bold text-white mb-4">Recent Transactions</h2>
      {loading ? (
        <div className="flex items-center gap-2 text-gray-400 py-4 justify-center">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading...
        </div>
      ) : txs.length === 0 ? (
        <p className="text-center text-gray-500 py-6 text-sm">No XRP transactions yet.</p>
      ) : (
        <div className="space-y-2">
          {txs.map(tx => (
            <div key={tx.id} className="flex items-center justify-between py-2 border-b border-gray-700/30 last:border-0">
              <div className="flex items-center gap-3">
                <span className={`text-sm font-medium ${typeColor[tx.tx_type] || 'text-gray-400'}`}>
                  {typeLabel[tx.tx_type] || tx.tx_type}
                </span>
                <span className="text-xs text-gray-500">
                  {new Date(tx.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="text-right">
                <span className={`text-sm font-mono font-medium ${parseFloat(tx.amount) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {parseFloat(tx.amount) >= 0 ? '+' : ''}{fmt(Math.abs(parseFloat(tx.amount)), 4)} {tx.symbol}
                </span>
                {tx.tx_hash && (
                  <a
                    href={`https://testnet.xrpl.org/transactions/${tx.tx_hash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-xs text-gray-600 hover:text-blue-400 transition-colors"
                  >
                    <ExternalLink className="h-3 w-3 inline" /> explorer
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default XRPPage;