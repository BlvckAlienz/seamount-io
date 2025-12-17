import React, { useState, useEffect } from 'react';
import { TrendingUp, DollarSign, Users, Clock, AlertTriangle, CheckCircle, XCircle, Zap, Trophy, Target, ArrowRight, Info, Wallet, X, Loader, ExternalLink } from 'lucide-react';

import { apiClient } from '@/config/api';
import { supabase } from '@/lib/supabase';
import toast from 'react-hot-toast';

import { TransactionMonitor } from '@/components/predictions/TransactionMonitor';
import { useWalletOrchestrator } from '@/contexts/WalletOrchestratorContext';
import { UnifiedWalletModal } from '@/components/wallet/UnifiedWalletModal';

// 🦊 ENHANCED METAMASK TYPE DECLARATION
declare global {
  interface Window {
    ethereum?: {
      isMetaMask?: boolean;
      request: (args: { method: string; params?: any[] }) => Promise<any>;
      on?: (event: string, handler: (...args: any[]) => void) => void;
      removeListener?: (event: string, handler: (...args: any[]) => void) => void;
    };
  }
}

interface Market {
  id: number;
  question: string;
  description: string;
  endTime: number;
  resolved: boolean;
  outcome: boolean;
  totalVolume: string;
  participantCount: number;
  yesOdds: number;
  noOdds: number;
  timeRemaining: number;
  yesPercent: number;
  noPercent: number;
}

interface Bet {
  id: string;
  market_id: number;
  question: string;
  prediction: boolean;
  amount: number;
  created_at: string;
  resolved: boolean;
  won?: boolean;
  payout?: number;
  tx_hash?: string;
  status?: 'pending' | 'confirmed' | 'failed' | 'won' | 'lost' | 'claimable';
  claimed?: boolean;
  claimed_at?: string;
  claim_tx_hash?: string;
  updated_at?: string;
  just_resolved?: boolean;
}

interface PortfolioBet extends Bet {
  market_question: string;
  market_end_time: number;
  current_odds: {
    yes: number;
    no: number;
  };
  roi: number;
}

// ✅ CORRECT BASECAMP TESTNET CONFIG
const BASECAMP_CONFIG = {
  chainId: '0x1cbc67c35a',
  chainName: 'Basecamp',
  nativeCurrency: {
    name: 'CAMP',
    symbol: 'CAMP',
    decimals: 18
  },
  rpcUrls: [
    'https://rpc.basecamp.t.raas.gelato.cloud'
  ],
  blockExplorerUrls: ['https://basecamp.cloud.blockscout.com']
};

const PredictionMarketsPage: React.FC = () => {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [myBets, setMyBets] = useState<Bet[]>([]);
  const [selectedMarket, setSelectedMarket] = useState<Market | null>(null);
  const [betAmount, setBetAmount] = useState<string>('10');
  const [betPrediction, setBetPrediction] = useState<boolean>(true);
  const [loading, setLoading] = useState(false);
  const [showBetModal, setShowBetModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'markets' | 'mybets'>('markets');

  // ✅ Use unified wallet orchestrator
  const { 
    baseCampAddress, 
    isBaseCampConnected, 
    connectBaseCAMP, 
    disconnectExternalWallet,
    isConnecting 
  } = useWalletOrchestrator();

  const address = baseCampAddress;

  const [signingTransaction, setSigningTransaction] = useState(false);

  // ✅ TRANSACTION MONITOR STATE
  const [activeTransaction, setActiveTransaction] = useState<{
    betId: string;
    txHash: string;
  } | null>(null);

  // 🎯 CLAIM WINNINGS STATE
  const [claimingBetId, setClaimingBetId] = useState<string | null>(null);
  const [claimTransaction, setClaimTransaction] = useState<{
    betId: string;
    txHash: string;
  } | null>(null);

  const [portfolioStats, setPortfolioStats] = useState({
    total_staked: 0,
    potential_winnings: 0,
    realized_winnings: 0,
    active_bets: 0,
    profit_loss: 0,
    win_rate: 0
  });

  // ✅ CHECK METAMASK PERSISTENCE
  useEffect(() => {
    const checkMetaMaskConnection = async () => {
      try {
        if (!window.ethereum) return;

        const accounts = await window.ethereum.request({
          method: 'eth_accounts'
        }) as string[];

        if (accounts.length > 0) {
          const chainId = await window.ethereum.request({
            method: 'eth_chainId'
          });

          if (chainId === BASECAMP_CONFIG.chainId) {
            console.log('✅ MetaMask detected with BaseCAMP:', accounts[0]);
          } else {
            console.warn('⚠️ Wrong network, please switch to BaseCAMP');
          }
        }
      } catch (error) {
        console.error('MetaMask check failed:', error);
      }
    };

    checkMetaMaskConnection();
  }, []);

  useEffect(() => {
    fetchMarkets();
    const interval = setInterval(fetchMarkets, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (activeTab === 'mybets') {
      fetchMyBets();
    }
  }, [activeTab]);

  const fetchMyBets = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();

      if (!session?.access_token) {
        console.warn('[MyBets] No valid session');
        return;
      }

      const response = await fetch('/api/v1/predictions/my-bets', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });

      const data = await response.json();

      if (data.success) {
        setMyBets(data.bets);

        // 💨 UPDATE PORTFOLIO STATS FROM BACKEND
        if (data.stats) {
          setPortfolioStats(data.stats);
          console.log('📊 Stats updated:', data.stats);
        }

        console.log(`✅ Loaded ${data.bets.length} confirmed bets`);

        const pendingCount = data.bets.filter((b: any) => b.status === 'pending').length;
        const justResolvedCount = data.bets.filter((b: any) => b.just_resolved === true).length;

        if (pendingCount > 0) {
          console.log(`⏳ ${pendingCount} pending bets - will auto-refresh`);
          setTimeout(fetchMyBets, 5000);
        }

        // ✅ FORCE REFRESH IF MARKETS JUST RESOLVED
        if (justResolvedCount > 0) {
          console.log(`🔄 ${justResolvedCount} bets just resolved - refreshing in 2s`);
          setTimeout(fetchMyBets, 2000);
        }
      }
    } catch (error) {
      console.error('Failed to fetch my bets:', error);
    }
  };

  const fetchMarkets = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/predictions/markets');
      const data = await response.json();
      if (data.success) {
        setMarkets(data.markets);
      }
    } catch (error) {
      console.error('Failed to fetch markets:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatTimeRemaining = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  const formatVolume = (volume: string) => {
    const num = parseFloat(volume) / 1e18; // Convert from wei to CAMP
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M CAMP`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K CAMP`;
    return `${num.toFixed(1)} CAMP`;
  };

  const calculateMarketStats = () => {
    if (markets.length === 0) return { totalVolume: 0, totalTraders: 0 };

    let totalVolume = 0;

    markets.forEach(market => {
      const marketVolume = parseFloat(market.totalVolume) / 1e18;
      totalVolume += marketVolume;
    });

    const uniqueTraders = markets.reduce((sum, m) => sum + m.participantCount, 0);

    return {
      totalVolume,
      totalTraders: uniqueTraders
    };
  };

  // 🦊 TIERED FEE CALCULATION FUNCTIONS - MATCHING SMART CONTRACT
  const calculateFeeRate = (totalVolume: number): number => {
    // Convert from wei to CAMP and use same thresholds as smart contract
    const totalCAMP = totalVolume / 1e18;

    if (totalCAMP < 1000) return 10;    // 1.0% (10/1000) - LOW_FEE
    if (totalCAMP < 10000) return 7;    // 0.7% (7/1000) - MED_FEE
    return 5;                           // 0.5% (5/1000) - HIGH_FEE
  };

  const getFeePercentage = (totalVolume: number): string => {
    const rate = calculateFeeRate(totalVolume);
    // Convert to percentage: 10 = 1.0%, 7 = 0.7%, 5 = 0.5%
    return (rate / 10).toFixed(1);
  };

  const calculatePotentialPayout = () => {
    if (!selectedMarket || !betAmount) return 0;

    const amount = parseFloat(betAmount);
    const totalVolume = parseFloat(selectedMarket.totalVolume || '0');
    const totalPool = (totalVolume / 1e18) + amount;
    const winningPool = betPrediction
      ? ((selectedMarket.yesPercent / 100) * (totalVolume / 1e18)) + amount
      : ((selectedMarket.noPercent / 100) * (totalVolume / 1e18)) + amount;

    if (winningPool === 0) return amount * 1.98; // 2x minus minimum fee approximation

    const grossPayout = (amount / winningPool) * totalPool;

    // Use the same tiered fee logic as the smart contract
    const feeRate = calculateFeeRate(totalVolume);
    const fee = (grossPayout * feeRate) / 1000;
    const netPayout = grossPayout - fee;

    return netPayout;
  };

  const handlePlaceBet = async () => {
    // 🚨 GUARD: Prevent double-clicks
    if (loading || signingTransaction) {
      return;
    }

    // 🎯 CHECK BASECAMP CONNECTION
    if (!isBaseCampConnected || !address) {
      toast.error('Please connect BaseCAMP wallet to place bets');
      return;
    }

    if (!selectedMarket || !betAmount) return;

    setLoading(true);
    setSigningTransaction(true);

    try {
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      if (sessionError || !session?.access_token) {
        toast.error('Please sign in to place bets');
        return;
      }

      // 🎯 USE UNIFIED WALLET ADDRESS
      const campAddress = address;

      const response = await fetch('/api/v1/predictions/bet', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          market_id: selectedMarket.id,
          prediction: betPrediction,
          amount: parseFloat(betAmount),
          user_wallet: campAddress  // ✅ Uses unified wallet address
        })
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.detail || 'Bet recording failed');
      }

      if (!data.contract_function.encoded_data ||
        !data.contract_function.encoded_data.startsWith('0x')) {
        throw new Error('💨 Invalid contract data from backend');
      }

      console.log('📤 Sending transaction:', {
        to: data.contract_address,
        value: `0x${data.contract_function.value_in_wei.toString(16)}`,
        data: data.contract_function.encoded_data,
        from: campAddress
      });

      const txHash = await window.ethereum!.request({
        method: 'eth_sendTransaction',
        params: [{
          from: campAddress,
          to: data.contract_address,
          value: `0x${data.contract_function.value_in_wei.toString(16)}`,
          data: data.contract_function.encoded_data,
          gas: '0x30D40'
        }]
      }) as string;

      console.log('✅ Transaction submitted:', txHash);

      const confirmResponse = await fetch('/api/v1/predictions/confirm-bet', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          market_id: selectedMarket.id,
          prediction: betPrediction,
          amount: parseFloat(betAmount),
          user_wallet: campAddress,
          tx_hash: txHash
        })
      });

      const confirmData = await confirmResponse.json();

      if (!confirmData.success) {
        throw new Error('Failed to confirm bet');
      }

      // ✅ SHOW TRANSACTION MONITOR
      setActiveTransaction({
        betId: confirmData.bet_id,
        txHash: txHash
      });

      toast.success(
        `Transaction submitted! Monitoring status...`,
        { id: 'bet-tx', duration: 10000 }
      );

      await fetchMarkets();
      await fetchMyBets();
      setBetAmount('10');

    } catch (error: any) {
      console.error('💥 Bet placement error:', error);
      toast.error(error.message || 'Bet placement failed', { id: 'bet-tx' });
    } finally {
      setLoading(false);
      setSigningTransaction(false);
    }
  };

  // 🎯 CLAIM WINNINGS HANDLER
  const handleClaimWinnings = async (betId: string, marketId: number) => {
    // 🎯 USE UNIFIED WALLET: Check if BaseCAMP wallet is connected
    if (!connectedChains.includes('basecamp') || !address) {
      toast.error('Please connect BaseCAMP wallet first');
      return;
    }

    setClaimingBetId(betId);

    try {
      const { data: { session } } = await supabase.auth.getSession();

      if (!session?.access_token) {
        toast.error('Please sign in to claim winnings');
        return;
      }

      // 🎯 USE UNIFIED WALLET ADDRESS
      const campAddress = address;

      // Step 1: Get encoded claim transaction
      const response = await fetch('/api/v1/predictions/initiate-claim', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({ bet_id: betId })
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.detail || 'Failed to initiate claim');
      }

      toast.success(`Expected payout: ${data.expected_payout} CAMP`, { duration: 3000 });

      // Step 2: Execute claim transaction via MetaMask
      const txHash = await window.ethereum!.request({
        method: 'eth_sendTransaction',
        params: [{
          from: campAddress,
          to: data.contract_address,
          data: data.contract_function.encoded_data,
          gas: '0x30D40'  // 200k gas
        }]
      }) as string;

      console.log('✅ Claim tx submitted:', txHash);

      // Step 3: Confirm claim transaction
      const confirmResponse = await fetch('/api/v1/predictions/confirm-claim', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          bet_id: betId,
          claim_tx_hash: txHash
        })
      });

      const confirmData = await confirmResponse.json();

      if (!confirmData.success) {
        throw new Error('Failed to record claim transaction');
      }

      // Show transaction monitor
      setClaimTransaction({
        betId: betId,
        txHash: txHash
      });

      toast.success('Claim transaction submitted!', { duration: 10000 });

    } catch (error: any) {
      console.error('Claim error:', error);

      if (error.code === 4001) {
        toast.error('Claim cancelled by user');
      } else {
        toast.error(error.message || 'Claim failed');
      }
    } finally {
      setClaimingBetId(null);
    }
  };

  const getCategoryFromQuestion = (question: string) => {
    const lowerQuestion = question.toLowerCase();
    if (lowerQuestion.includes('bitcoin') || lowerQuestion.includes('btc')) return 'crypto';
    if (lowerQuestion.includes('eagles') || lowerQuestion.includes('arsenal')) return 'sports';
    if (lowerQuestion.includes('ngn') || lowerQuestion.includes('exchange')) return 'forex';
    if (lowerQuestion.includes('election') || lowerQuestion.includes('jonathan')) return 'politics';
    return 'other';
  };

  const getCategoryEmoji = (category: string) => {
    const emojis: Record<string, string> = {
      sports: '⚽',
      crypto: '₿',
      forex: '💱',
      politics: '🗳️',
      other: '📊'
    };
    return emojis[category] || '📊';
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      sports: 'from-blue-500 to-cyan-500',
      crypto: 'from-purple-500 to-pink-500',
      forex: 'from-green-500 to-emerald-500',
      politics: 'from-red-500 to-orange-500',
      other: 'from-gray-500 to-slate-500'
    };
    return colors[category] || 'from-gray-500 to-slate-500';
  };

  // ✅ PERSIST METAMASK CONNECTION
  useEffect(() => {
    if (!window.ethereum) return;

    const handleAccountsChanged = (accounts: string[]) => {
      if (accounts.length === 0) {
        console.log('Wallet disconnected via accountsChanged');
      } else {
        console.log('Accounts changed:', accounts[0]);
      }
    };

    const handleChainChanged = (chainId: string) => {
      if (chainId !== BASECAMP_CONFIG.chainId) {
        toast.error('⚠️ Please switch back to BaseCAMP network');
      } else {
        toast.success('Connected to BaseCAMP');
        window.location.reload();
      }
    };

    const ethereum = window.ethereum as any;
    ethereum.on('accountsChanged', handleAccountsChanged);
    ethereum.on('chainChanged', handleChainChanged);

    return () => {
      if (ethereum.removeListener) {
        ethereum.removeListener('accountsChanged', handleAccountsChanged);
        ethereum.removeListener('chainChanged', handleChainChanged);
      }
    };
  }, []);

  // 🦊 UPDATED STATS DATA ARRAY WITH TIERED FEE DISPLAY
  const statsData = [
    {
      label: 'Total Volume',
      value: `${calculateMarketStats().totalVolume.toFixed(1)} CAMP`,
      icon: DollarSign,
      color: 'text-green-400'
    },
    {
      label: 'Active Markets',
      value: markets.length,
      icon: TrendingUp,
      color: 'text-blue-400'
    },
    {
      label: 'Total Traders',
      value: calculateMarketStats().totalTraders,
      icon: Users,
      color: 'text-purple-400'
    },
    {
      label: 'Payouts',
      value: `${myBets.filter(b => b.won).reduce((sum, bet) => sum + (bet.payout || 0), 0).toFixed(1)} CAMP`,
      icon: Trophy,
      color: 'text-yellow-400'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 md:p-8">
      <button
        onClick={() => window.history.back()}
        className="absolute top-6 left-6 p-3 rounded-full bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 text-gray-400 hover:text-white transition-colors z-10"
        title="Close"
      >
        <X className="h-6 w-6" />
      </button>
      <div className="max-w-7xl mx-auto">
        {/* 🎯 BASECAMP STATUS (READ ONLY) */}
        <div className="flex justify-end mb-4">
          {isBaseCampConnected ? (
            <div className="flex items-center gap-3">
              <div className="bg-green-500/20 border border-green-500/30 rounded-lg px-4 py-2 flex items-center gap-2">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-green-400 font-mono text-sm">
                  {address?.slice(0, 6)}...{address?.slice(-4)}
                </span>
              </div>
              <button
                onClick={() => disconnectExternalWallet('basecamp')}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm transition"
              >
                Disconnect
              </button>
            </div>
          ) : (
            <button
              onClick={connectBaseCAMP}
              disabled={isConnecting}
              className="px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-lg hover:shadow-lg hover:shadow-green-500/30 transition flex items-center gap-2 disabled:opacity-50"
            >
              <Wallet className="w-5 h-5" />
              {isConnecting ? 'Connecting...' : 'Connect for Predictions'}
            </button>
          )}
        </div>

        {/* Hero Header */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-3 mb-4 px-6 py-3 bg-gradient-to-r from-green-500/20 to-emerald-500/20 rounded-full border border-green-500/30">
            <Zap className="h-5 w-5 text-green-400 animate-pulse" />
            <span className="text-green-400 font-semibold text-sm">5 LIVE MARKETS</span>
          </div>

          <h1 className="text-5xl md:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white via-green-100 to-emerald-300 mb-3">
            Seamount Predictions
          </h1>

          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Bet on sports, crypto, FX, and politics powered by <span className="text-green-400 font-semibold">CAMP</span> Network
          </p>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {statsData.map((stat, idx) => (
            <div key={idx} className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-4 hover:border-slate-600 transition-all">
              <div className="flex items-center gap-2 mb-1">
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
                <span className="text-gray-400 text-xs uppercase tracking-wide">{stat.label}</span>
              </div>
              <div className="text-2xl font-bold text-white">{stat.value}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex gap-3 mb-6">
          <button
            onClick={() => setActiveTab('markets')}
            className={`flex-1 md:flex-initial px-8 py-4 rounded-xl font-bold text-lg transition-all duration-300 ${activeTab === 'markets'
                ? 'bg-gradient-to-r from-green-600 to-emerald-600 text-white shadow-lg shadow-green-500/30 scale-105'
                : 'bg-slate-800/50 text-gray-400 hover:bg-slate-700/50 hover:text-white'
              }`}
          >
            <Target className="inline h-5 w-5 mr-2" />
            Active Markets
          </button>

          <button
            onClick={() => setActiveTab('mybets')}
            className={`flex-1 md:flex-initial px-8 py-4 rounded-xl font-bold text-lg transition-all duration-300 ${activeTab === 'mybets'
                ? 'bg-gradient-to-r from-green-600 to-emerald-600 text-white shadow-lg shadow-green-500/30 scale-105'
                : 'bg-slate-800/50 text-gray-400 hover:bg-slate-700/50 hover:text-white'
              }`}
          >
            <Trophy className="inline h-5 w-5 mr-2" />
            My Bets ({myBets.length})
          </button>
        </div>

        {/* Markets Grid */}
        {activeTab === 'markets' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {loading && markets.length === 0 ? (
              <div className="col-span-full text-center py-20">
                <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-green-500 mx-auto mb-4" />
                <p className="text-gray-400 text-lg">Loading markets...</p>
              </div>
            ) : (
              markets.map(market => {
                const category = getCategoryFromQuestion(market.question);
                return (
                  <div
                    key={market.id}
                    onClick={() => {
                      setSelectedMarket(market);
                      setShowBetModal(true);
                      // 🔧 Reset all bet states when opening modal
                      setLoading(false);
                      setSigningTransaction(false);
                      setActiveTransaction(null);
                      setBetAmount('10');
                    }}
                    className="group bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50 hover:border-green-500/50 transition-all duration-300 cursor-pointer hover:scale-[1.02] hover:shadow-xl hover:shadow-green-500/10"
                  >
                    {/* Category Badge */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <span className={`px-4 py-1.5 rounded-full text-xs font-bold text-white bg-gradient-to-r ${getCategoryColor(category)}`}>
                          {getCategoryEmoji(category)} {category.toUpperCase()}
                        </span>
                        {market.participantCount === 0 && (
                          <span className="px-3 py-1 rounded-full text-xs font-bold bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 animate-pulse">
                            NEW
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2 text-gray-400">
                        <Clock className="h-4 w-4" />
                        <span className="text-sm font-semibold">{formatTimeRemaining(market.timeRemaining)}</span>
                      </div>
                    </div>

                    {/* Question */}
                    <h3 className="text-xl font-bold text-white mb-3 group-hover:text-green-400 transition-colors leading-tight">
                      {market.question}
                    </h3>

                    <p className="text-gray-400 text-sm mb-5 line-clamp-2 leading-relaxed">
                      {market.description}
                    </p>

                    {/* Odds Display */}
                    <div className="grid grid-cols-2 gap-3 mb-5">
                      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-green-900/30 to-green-800/20 border border-green-500/30 p-4 hover:border-green-400/50 transition-all">
                        <div className="absolute inset-0 bg-gradient-to-br from-green-500/10 to-transparent" />
                        <div className="relative">
                          <div className="text-xs text-green-400 font-bold mb-1 uppercase tracking-wide">YES</div>
                          <div className="text-3xl font-black text-white">{market.yesPercent.toFixed(1)}%</div>
                          <div className="text-xs text-green-300/70 mt-1">{(10000 / market.yesOdds).toFixed(2)}x payout</div>
                        </div>
                      </div>

                      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-red-900/30 to-red-800/20 border border-red-500/30 p-4 hover:border-red-400/50 transition-all">
                        <div className="absolute inset-0 bg-gradient-to-br from-red-500/10 to-transparent" />
                        <div className="relative">
                          <div className="text-xs text-red-400 font-bold mb-1 uppercase tracking-wide">NO</div>
                          <div className="text-3xl font-black text-white">{market.noPercent.toFixed(1)}%</div>
                          <div className="text-xs text-red-300/70 mt-1">{(10000 / market.noOdds).toFixed(2)}x payout</div>
                        </div>
                      </div>
                    </div>

                    {/* Footer Stats */}
                    <div className="flex items-center justify-between pt-4 border-t border-slate-700/50">
                      <div className="flex items-center gap-4 text-sm">
                        <div className="flex items-center gap-1.5">
                          <DollarSign className="h-4 w-4 text-gray-500" />
                          <span className="text-gray-400">{formatVolume(market.totalVolume)}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Users className="h-4 w-4 text-gray-500" />
                          <span className="text-gray-400">{market.participantCount}</span>
                        </div>
                      </div>

                      <button className="flex items-center gap-2 text-green-400 font-semibold text-sm group-hover:gap-3 transition-all">
                        Place Bet
                        <ArrowRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* My Bets Tab */}
        {activeTab === 'mybets' && (
          <>
            {myBets.length === 0 ? (
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-12 border border-slate-700/50 text-center">
                <Trophy className="h-20 w-20 text-gray-600 mx-auto mb-4" />
                <h3 className="text-2xl font-bold text-white mb-2">No Bets Yet</h3>
                <p className="text-gray-400 mb-6">Start predicting to see your portfolio here</p>
                <button
                  onClick={() => setActiveTab('markets')}
                  className="px-8 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-green-500/30 transition-all"
                >
                  Browse Markets
                </button>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Portfolio Summary Card */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  {/* Card 1: Total Staked */}
                  <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/20 border border-blue-500/30 rounded-2xl p-6">
                    <div className="text-sm text-blue-400 mb-1 uppercase tracking-wide">Total Staked</div>
                    <div className="text-3xl font-black text-white">
                      {portfolioStats.total_staked.toFixed(2)} CAMP
                    </div>
                    <div className="text-xs text-blue-300/70 mt-1">Confirmed bets</div>
                  </div>

                  {/* Card 2: Potential Winnings */}
                  <div className="bg-gradient-to-br from-purple-900/30 to-purple-800/20 border border-purple-500/30 rounded-2xl p-6">
                    <div className="text-sm text-purple-400 mb-1 uppercase tracking-wide">Potential Winnings</div>
                    <div className="text-3xl font-black text-white">
                      {portfolioStats.potential_winnings.toFixed(2)} CAMP
                    </div>
                    <div className="text-xs text-purple-300/70 mt-1">If all active win</div>
                  </div>

                  {/* Card 3: Realized Winnings */}
                  <div className="bg-gradient-to-br from-green-900/30 to-green-800/20 border border-green-500/30 rounded-2xl p-6">
                    <div className="text-sm text-green-400 mb-1 uppercase tracking-wide">Realized Winnings</div>
                    <div className="text-3xl font-black text-white">
                      {portfolioStats.realized_winnings.toFixed(2)} CAMP
                    </div>
                    <div className="text-xs text-green-300/70 mt-1">From won bets</div>
                  </div>

                  {/* Card 4: Active Bets */}
                  <div className="bg-gradient-to-br from-slate-800/30 to-slate-700/20 border border-slate-500/30 rounded-2xl p-6">
                    <div className="text-sm text-slate-400 mb-1 uppercase tracking-wide">Active Bets</div>
                    <div className="text-3xl font-black text-white">
                      {portfolioStats.active_bets}
                    </div>
                    <div className="text-xs text-slate-300/70 mt-1">Unresolved</div>
                  </div>

                  {/* Card 5: Your Profit (Dynamic Color) */}
                  <div className={`bg-gradient-to-br rounded-2xl p-6 ${portfolioStats.profit_loss >= 0
                      ? 'from-yellow-900/30 to-yellow-800/20 border border-yellow-500/30'
                      : 'from-red-900/30 to-red-800/20 border border-red-500/30'
                    }`}>
                    <div className={`text-sm mb-1 uppercase tracking-wide ${portfolioStats.profit_loss >= 0 ? 'text-yellow-400' : 'text-red-400'
                      }`}>
                      Your Profit
                    </div>
                    <div className={`text-3xl font-black ${portfolioStats.profit_loss >= 0 ? 'text-yellow-400' : 'text-red-400'
                      }`}>
                      {portfolioStats.profit_loss >= 0 ? '+' : ''}{portfolioStats.profit_loss.toFixed(2)} CAMP
                    </div>
                    <div className={`text-xs mt-1 ${portfolioStats.profit_loss >= 0 ? 'text-yellow-300/70' : 'text-red-300/70'
                      }`}>
                      Win rate: {portfolioStats.win_rate.toFixed(1)}%
                    </div>
                  </div>
                </div>

                {/* Bets List */}
                <div className="space-y-4">
                  {myBets.map(bet => (
                    <div
                      key={bet.id}
                      className={`bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border transition-all hover:scale-[1.01] ${bet.won
                          ? 'border-green-500/50 hover:border-green-500'
                          : bet.resolved
                            ? 'border-red-500/30 opacity-60'
                            : 'border-slate-700/50 hover:border-slate-600'
                        }`}
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`px-3 py-1 rounded-full text-xs font-bold ${bet.prediction
                                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                : 'bg-red-500/20 text-red-400 border border-red-500/30'
                              }`}>
                              {bet.prediction ? 'YES' : 'NO'}
                            </span>

                            {/* ✅ LIVE STATUS BADGE */}
                            {bet.status === 'pending' && (
                              <span className="px-3 py-1 rounded-full text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30 animate-pulse flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                Pending
                              </span>
                            )}
                            {bet.status === 'confirmed' && !bet.resolved && (
                              <span className="px-3 py-1 rounded-full text-xs font-bold bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" />
                                Confirmed
                              </span>
                            )}
                            {bet.resolved && bet.won && !bet.claimed && (
                              <span className="px-3 py-1 rounded-full text-xs font-bold bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 animate-pulse">
                                🏆 CLAIMABLE
                              </span>
                            )}
                            {bet.resolved && bet.won && bet.claimed && (
                              <span className="px-3 py-1 rounded-full text-xs font-bold bg-green-500/20 text-green-400 border border-green-500/30">
                                ✅ CLAIMED
                              </span>
                            )}
                            {bet.resolved && !bet.won && (
                              <span className="px-3 py-1 rounded-full text-xs font-bold bg-gray-500/20 text-gray-400 border border-gray-500/30">
                                LOST
                              </span>
                            )}
                          </div>
                          <h4 className="text-lg font-bold text-white mb-1">{bet.question}</h4>
                          <p className="text-sm text-gray-400">Placed {new Date(bet.created_at).toLocaleDateString()}</p>
                        </div>

                        <div className="text-right">
                          <div className="text-sm text-gray-400 mb-1">Staked</div>
                          <div className="text-xl font-bold text-white">{bet.amount.toFixed(2)} CAMP</div>
                          {bet.payout && !bet.resolved && (
                            <div className="text-xs text-green-400 mt-1">
                              Potential: {bet.payout.toFixed(2)} CAMP
                            </div>
                          )}
                          {bet.won && bet.payout && (
                            <div className="text-lg font-bold text-green-400 mt-1">
                              +{bet.payout.toFixed(2)} CAMP
                            </div>
                          )}
                        </div>
                      </div>

                      {/* ✅ BLOCKCHAIN EXPLORER LINK */}
                      {bet.tx_hash && (
                        <a
                          href={`https://basecamp.cloud.blockscout.com/tx/${bet.tx_hash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-4 flex items-center justify-center gap-2 py-2 px-4 bg-slate-700/50 hover:bg-slate-600/50 rounded-lg text-xs text-gray-400 hover:text-white transition-all"
                        >
                          <ExternalLink className="w-3 h-3" />
                          View Bet Transaction
                        </a>
                      )}

                      {/* 🐛 DEBUG: Show bet state */}
                      {process.env.NODE_ENV === 'development' && (
                        <div className="text-xs text-gray-500 mb-2">
                          resolved={String(bet.resolved)} | won={String(bet.won)} | claimed={String(bet.claimed)}
                        </div>
                      )}

                      {/* 🎯 Show claim button if market resolved + user won + not claimed yet */}
                      {bet.resolved && bet.won === true && bet.claimed !== true && (
                        <button
                          onClick={() => handleClaimWinnings(bet.id, bet.market_id)}
                          disabled={claimingBetId === bet.id}
                          className="w-full mt-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-green-500/30 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {claimingBetId === bet.id ? (
                            <>
                              <Loader className="h-5 w-5 animate-spin" />
                              Claiming...
                            </>
                          ) : (
                            <>
                              <Trophy className="h-5 w-5" />
                              Claim {bet.payout?.toFixed(2)} CAMP
                            </>
                          )}
                        </button>
                      )}

                      {/* ✅ CLAIMED STATUS */}
                      {bet.claimed && (
                        <div className="w-full mt-4 space-y-2">
                          <div className="py-3 bg-green-500/10 border border-green-500/30 rounded-xl flex items-center justify-center gap-2">
                            <CheckCircle className="h-5 w-5 text-green-400" />
                            <span className="text-green-400 font-semibold">
                              Claimed on {new Date(bet.claimed_at || bet.updated_at || '').toLocaleDateString()}
                            </span>
                          </div>

                          {/* Claim Transaction Link */}
                          {bet.claim_tx_hash && (
                            <a
                              href={`https://basecamp.cloud.blockscout.com/tx/${bet.claim_tx_hash}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center justify-center gap-2 py-2 px-4 bg-slate-700/50 hover:bg-slate-600/50 rounded-lg text-xs text-gray-400 hover:text-white transition-all"
                            >
                              <ExternalLink className="w-3 h-3" />
                              View Claim Transaction
                            </a>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Bet Modal */}
        {showBetModal && selectedMarket && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
            <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
              {/* Modal Header */}
              <div className="p-6 border-b border-slate-700">
                <div className="flex items-start justify-between">
                  <div>
                    <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold text-white bg-gradient-to-r ${getCategoryColor(getCategoryFromQuestion(selectedMarket.question))} mb-3`}>
                      {getCategoryEmoji(getCategoryFromQuestion(selectedMarket.question))} {getCategoryFromQuestion(selectedMarket.question).toUpperCase()}
                    </span>
                    <h2 className="text-2xl font-bold text-white mb-2">{selectedMarket.question}</h2>
                    <p className="text-gray-400 text-sm">{selectedMarket.description}</p>
                  </div>
                  <button
                    onClick={() => {
                      setShowBetModal(false);
                      setActiveTransaction(null);
                    }}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    <XCircle className="h-6 w-6" />
                  </button>
                </div>
              </div>

              {/* Modal Body */}
              <div className="p-6">
                {/* Transaction Monitor - Shows during/after bet placement */}
                {activeTransaction ? (
                  <div className="mb-6">
                    <TransactionMonitor
                      betId={activeTransaction.betId}
                      txHash={activeTransaction.txHash}
                      onConfirmed={() => {
                        fetchMarkets();
                        fetchMyBets();
                        toast.success('Bet confirmed on-chain!', { duration: 9000 });
                        setTimeout(() => {
                          setActiveTransaction(null);
                          setShowBetModal(false);
                        }, 6000);
                      }}
                    />
                  </div>
                ) : (
                  <>
                    {/* YES/NO Toggle */}
                    <div className="grid grid-cols-2 gap-3 mb-6">
                      <button
                        onClick={() => setBetPrediction(true)}
                        className={`p-6 rounded-xl border-2 transition-all ${betPrediction
                            ? 'bg-gradient-to-br from-green-600 to-emerald-600 border-green-400 shadow-lg shadow-green-500/30'
                            : 'bg-slate-800/50 border-slate-700 hover:border-green-500/50'
                          }`}
                      >
                        <div className="text-lg font-bold text-white mb-1">YES</div>
                        <div className="text-3xl font-black text-white">{selectedMarket.yesPercent.toFixed(1)}%</div>
                        <div className="text-sm text-green-300 mt-1">{(10000 / selectedMarket.yesOdds).toFixed(2)}x payout</div>
                      </button>

                      <button
                        onClick={() => setBetPrediction(false)}
                        className={`p-6 rounded-xl border-2 transition-all ${!betPrediction
                            ? 'bg-gradient-to-br from-red-600 to-rose-600 border-red-400 shadow-lg shadow-red-500/30'
                            : 'bg-slate-800/50 border-slate-700 hover:border-red-500/50'
                          }`}
                      >
                        <div className="text-lg font-bold text-white mb-1">NO</div>
                        <div className="text-3xl font-black text-white">{selectedMarket.noPercent.toFixed(1)}%</div>
                        <div className="text-sm text-red-300 mt-1">{(10000 / selectedMarket.noOdds).toFixed(2)}x payout</div>
                      </button>
                    </div>

                    {/* Amount Input */}
                    <div className="mb-6">
                      <label className="block text-sm font-semibold text-gray-400 mb-2">Bet Amount (CAMP)</label>
                      <div className="relative">
                        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-2xl text-gray-500"></span>
                        <input
                          type="number"
                          value={betAmount}
                          onChange={(e) => setBetAmount(e.target.value)}
                          className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-4 text-2xl font-bold text-white focus:border-green-500 focus:outline-none"
                          placeholder="10"
                          min="1"
                        />
                      </div>

                      {/* Quick Amounts */}
                      <div className="grid grid-cols-4 gap-2 mt-3">
                        {[1, 5, 10, 50].map(amount => (
                          <button
                            key={amount}
                            onClick={() => setBetAmount(amount.toString())}
                            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-green-500 rounded-lg text-sm font-semibold text-gray-300 hover:text-white transition-all"
                          >
                            {amount} CAMP
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Payout Breakdown - TIERED FEE CALCULATION */}
                    <div className="bg-slate-800/50 rounded-xl p-5 mb-6 border border-slate-700">
                      <div className="flex justify-between mb-3">
                        <span className="text-gray-400">Your Bet</span>
                        <span className="text-white font-semibold">{betAmount || '0'} CAMP</span>
                      </div>
                      {(() => {
                        const amount = parseFloat(betAmount || '0');
                        const totalVolume = parseFloat(selectedMarket.totalVolume || '0');
                        const totalPool = (totalVolume / 1e18) + amount;
                        const winningPool = betPrediction
                          ? ((selectedMarket.yesPercent / 100) * (totalVolume / 1e18)) + amount
                          : ((selectedMarket.noPercent / 100) * (totalVolume / 1e18)) + amount;

                        const grossPayout = winningPool === 0 ? amount * 2 : (amount / winningPool) * totalPool;
                        const feeRate = calculateFeeRate(totalVolume);
                        const feePercentage = getFeePercentage(totalVolume);
                        const fee = (grossPayout * feeRate) / 1000;
                        const netPayout = grossPayout - fee;

                        return (
                          <>
                            <div className="flex justify-between mb-3">
                              <span className="text-gray-400">Potential Return</span>
                              <span className="text-green-400 font-semibold">{grossPayout.toFixed(2)} CAMP</span>
                            </div>
                            <div className="flex justify-between mb-3">
                              <span className="text-gray-400">Platform Fee ({feePercentage}%)</span>
                              <span className="text-gray-500 font-semibold">-{fee.toFixed(2)} CAMP</span>
                            </div>
                            <div className="pt-3 border-t border-slate-700 flex justify-between">
                              <span className="text-white font-bold">Net Payout</span>
                              <span className="text-2xl text-green-400 font-black">{netPayout.toFixed(2)} CAMP</span>
                            </div>
                          </>
                        );
                      })()}
                    </div>

                    {/* Warning - UPDATED FEE INFORMATION */}
                    <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 mb-6 flex gap-3">
                      <Info className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-yellow-200">
                        Fees are tiered: 1.0% for pools under 1K CAMP, 0.7% for 1K-10K CAMP, 0.5% for 10K+ CAMP
                      </p>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3">
                      <button
                        onClick={() => setShowBetModal(false)}
                        className="flex-1 px-6 py-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white font-bold rounded-xl transition-all"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handlePlaceBet}
                        disabled={loading || signingTransaction || !betAmount || parseFloat(betAmount) < 1}
                        className="flex-1 px-6 py-4 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-green-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {signingTransaction ? (
                          <div className="flex items-center justify-center gap-2">
                            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                            <span>Signing Transaction...</span>
                          </div>
                        ) : loading ? (
                          'Recording Bet...'
                        ) : (
                          `Place ${betAmount ? `${betAmount} CAMP` : ''} Bet`
                        )}
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 🎯 CLAIM TRANSACTION MONITOR MODAL */}
        {claimTransaction && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-lg w-full p-6">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-white mb-2">💰 Claiming Winnings</h2>
                  <p className="text-gray-400 text-sm">Your claim transaction is being processed</p>
                </div>
                <button
                  onClick={() => setClaimTransaction(null)}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>

              <TransactionMonitor
                betId={claimTransaction.betId}
                txHash={claimTransaction.txHash}
                onConfirmed={() => {
                  fetchMyBets();
                  toast.success('🎉 Winnings claimed successfully!', { duration: 6000 });
                  setTimeout(() => {
                    setClaimTransaction(null);
                  }, 3000);
                }}
              />

              <div className="mt-6 p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
                <p className="text-sm text-green-300 text-center">
                  ⏳ Please wait for blockchain confirmation. This usually takes 10-30 seconds.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PredictionMarketsPage;