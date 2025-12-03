import React, { useState, useEffect } from 'react';
import { TrendingUp, DollarSign, Users, Clock, AlertTriangle, CheckCircle, XCircle, Zap, Trophy, Target, ArrowRight, Info, Wallet, X, Loader, ExternalLink } from 'lucide-react';

import { apiClient } from '@/config/api';
import { supabase } from '@/lib/supabase'; 
import toast from 'react-hot-toast';

import { TransactionMonitor } from '@/components/predictions/TransactionMonitor';

// 🔥 ENHANCED METAMASK TYPE DECLARATION
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
  status?: 'pending' | 'confirmed' | 'failed';
}

interface PortfolioBet extends Bet {
  market_question: string;
  market_end_time: number;
  current_odds: {
    yes: number;
    no: number;
  };
  roi: number;
  status: 'pending' | 'won' | 'lost' | 'claimable';
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

  // 🔥 IN-APP WALLET CONNECTION
  const [showWalletModal, setShowWalletModal] = useState(false);
  const [connecting, setConnecting] = useState(false);

  // WALLET STATE FOR ON-CHAIN TRANSACTIONS
  const [walletConnected, setWalletConnected] = useState(false);
  const [userAddress, setUserAddress] = useState<string>('');
  const [signingTransaction, setSigningTransaction] = useState(false);

  // ✅ TRANSACTION MONITOR STATE
  const [activeTransaction, setActiveTransaction] = useState<{
    betId: string;
    txHash: string;
  } | null>(null);

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
            setUserAddress(accounts[0]);
            setWalletConnected(true);
            console.log('✅ MetaMask reconnected:', accounts[0]);
          } else {
            console.warn('⚠️ Wrong network, please switch to BaseCAMP');
          }
        } else {
          setTimeout(() => {
            setShowWalletModal(true);
          }, 1000);
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
      // ✅ SHOW ALL BETS (including pending with tx_hash)
      const displayableBets = data.bets.filter((bet: any) => 
        bet.tx_hash && (bet.status === 'confirmed' || bet.status === 'pending')
      );
      
      setMyBets(displayableBets);
      
      console.log(`✅ Loaded ${displayableBets.length} bets`);
      
      // ✅ AUTO-REFRESH if pending bets exist
      const pendingCount = displayableBets.filter((b: any) => b.status === 'pending').length;
      if (pendingCount > 0) {
        console.log(`⏳ ${pendingCount} pending bets - will auto-refresh`);
        setTimeout(fetchMyBets, 5000); // Poll every 5 seconds
      }
    }
  } catch (error) {
    console.error('Failed to fetch my bets:', error);
  }
};

  // 🔥 IN-APP WALLET CONNECTION
  const connectWallet = async () => {
    setConnecting(true);
    
    try {
      if (!window.ethereum) {
        const shouldInstall = window.confirm(
          '⚠️ MetaMask not detected.\n\nInstall MetaMask to place bets?'
        );
        
        if (shouldInstall) {
          window.open('https://metamask.io/download/', '_blank');
        }
        setConnecting(false);
        return;
      }

      const accounts = await window.ethereum.request({ 
        method: 'eth_requestAccounts' 
      }) as string[];

      try {
        await window.ethereum.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: BASECAMP_CONFIG.chainId }]
        });
        
        console.log('✅ Switched to existing BaseCAMP network');
        
      } catch (switchError: any) {
        if (switchError.code === 4902) {
          console.log('⚠️ BaseCAMP not found in MetaMask, adding now...');
          
          try {
            await window.ethereum.request({
              method: 'wallet_addEthereumChain',
              params: [BASECAMP_CONFIG]
            });
            console.log('✅ BaseCAMP network added successfully');
          } catch (addError: any) {
            if (addError.code === -32603 && addError.message.includes('same RPC endpoint')) {
              toast.error(
                '⚠️ BaseCAMP network already exists in MetaMask.\n\n' +
                'Please manually switch to "Basecamp" network in MetaMask.',
                { duration: 6000 }
              );
              setConnecting(false);
              return;
            }
            throw addError;
          }
        } else {
          throw switchError;
        }
      }

      const chainId = await window.ethereum.request({ 
        method: 'eth_chainId' 
      });
      
      if (chainId !== BASECAMP_CONFIG.chainId) {
        toast.error('⚠️ Please switch to BaseCAMP network in MetaMask');
        setConnecting(false);
        return;
      }

      setUserAddress(accounts[0]);
      setWalletConnected(true);
      setShowWalletModal(false);
      
      toast.success(
        `✅ Wallet connected: ${accounts[0].slice(0, 6)}...${accounts[0].slice(-4)}`,
        { duration: 3000 }
      );
      
    } catch (error: any) {
      console.error('❌ Wallet connection failed:', error);
      
      if (error.code === 4001) {
        toast.error('Connection cancelled by user');
      } else if (error.message?.includes('already processing')) {
        toast.error('Please check MetaMask popup');
      } else {
        toast.error(error.message || 'Failed to connect wallet');
      }
    } finally {
      setConnecting(false);
    }
  };

  const disconnectWallet = () => {
    setWalletConnected(false);
    setUserAddress('');
    toast.success('Wallet disconnected');
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
    const num = parseFloat(volume) / 1000000;
    if (num >= 1000000) return `$${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `$${(num / 1000).toFixed(1)}K`;
    return `$${num.toFixed(0)}`;
  };

  const calculatePotentialPayout = () => {
    if (!selectedMarket || !betAmount) return 0;
    
    const amount = parseFloat(betAmount);
    const totalPool = parseFloat(selectedMarket.totalVolume) / 1000000 + amount;
    const winningPool = betPrediction 
      ? (selectedMarket.yesPercent * parseFloat(selectedMarket.totalVolume) / 100000000) + amount
      : (selectedMarket.noPercent * parseFloat(selectedMarket.totalVolume) / 100000000) + amount;
    
    if (winningPool === 0) return amount * 1.96;
    
    const grossPayout = (amount / winningPool) * totalPool;
    return grossPayout * 0.982;
  };

  const handlePlaceBet = async () => {
    if (!walletConnected) {
      setShowWalletModal(true);
      return;
    }
    
    if (!selectedMarket || !betAmount) return;
    
    setLoading(true);
    
    try {
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();
      
      if (sessionError || !session?.access_token) {
        toast.error('⚠️ Please sign in to place bets');
        return;
      }
      
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
          user_wallet: userAddress
        })
      });
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.detail || 'Bet recording failed');
      }
      
      if (!data.contract_function.encoded_data || 
          !data.contract_function.encoded_data.startsWith('0x')) {
        throw new Error('🚨 Invalid contract data from backend');
      }

      console.log('📝 Sending transaction:', {
        to: data.contract_address,
        value: `0x${data.contract_function.value_in_wei.toString(16)}`,
        data: data.contract_function.encoded_data,
        from: userAddress
      });

      const txHash = await window.ethereum!.request({
        method: 'eth_sendTransaction',
        params: [{
          from: userAddress,
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
          user_wallet: userAddress,
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
        `📡 Transaction submitted! Monitoring status...`,
        { id: 'bet-tx', duration: 3000 }
      );
      
      await fetchMarkets();
      await fetchMyBets();
      setBetAmount('10');
      
    } catch (error: any) {
      console.error('Bet placement error:', error);
      toast.error(error.message || 'Bet placement failed', { id: 'bet-tx' });
    } finally {
      setLoading(false);
      setSigningTransaction(false);
    }
  };

  const getCategoryFromQuestion = (question: string) => {
    if (question.toLowerCase().includes('bitcoin') || question.toLowerCase().includes('btc')) return 'crypto';
    if (question.toLowerCase().includes('eagles') || question.toLowerCase().includes('arsenal')) return 'sports';
    if (question.toLowerCase().includes('ngn') || question.toLowerCase().includes('exchange')) return 'forex';
    if (question.toLowerCase().includes('election') || question.toLowerCase().includes('jonathan')) return 'politics';
    return 'other';
  };

  const getCategoryEmoji = (category: string) => {
    const emojis: Record<string, string> = {
      sports: '⚽',
      crypto: '₿',
      forex: '💱',
      politics: '🏛️',
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
        setWalletConnected(false);
        setUserAddress('');
        toast.error('Wallet disconnected');
      } else {
        setUserAddress(accounts[0]);
        toast.success(`Switched to ${accounts[0].slice(0, 6)}...${accounts[0].slice(-4)}`);
      }
    };

    const handleChainChanged = (chainId: string) => {
      if (chainId !== BASECAMP_CONFIG.chainId) {
        toast.error('⚠️ Please switch back to BaseCAMP network');
        setWalletConnected(false);
      } else {
        toast.success('✅ Connected to BaseCAMP');
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* 🔥 WALLET CONNECTION HEADER */}
        <div className="flex justify-end mb-4">
          {walletConnected ? (
            <div className="flex items-center gap-3">
              <div className="bg-green-500/20 border border-green-500/30 rounded-lg px-4 py-2 flex items-center gap-2">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-green-400 font-mono text-sm">
                  {userAddress.slice(0, 6)}...{userAddress.slice(-4)}
                </span>
              </div>
              <button
                onClick={disconnectWallet}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm transition"
              >
                Disconnect
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowWalletModal(true)}
              className="px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-lg hover:shadow-lg hover:shadow-green-500/30 transition flex items-center gap-2"
            >
              <Wallet className="w-5 h-5" />
              Connect Wallet
            </button>
          )}
        </div>
        
        {/* Hero Header */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-3 mb-4 px-6 py-3 bg-gradient-to-r from-green-500/20 to-emerald-500/20 rounded-full border border-green-500/30">
            <Zap className="h-5 w-5 text-green-400 animate-pulse" />
            <span className="text-green-400 font-semibold text-sm">5 LIVE MARKETS $0 VOLUME</span>
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
          {[
            { label: 'Total Volume', value: '$0', icon: DollarSign, color: 'text-green-400' },
            { label: 'Active Markets', value: markets.length, icon: TrendingUp, color: 'text-blue-400' },
            { label: 'Total Traders', value: '0', icon: Users, color: 'text-purple-400' },
            { label: 'Your Profit', value: '$0.00', icon: Trophy, color: 'text-yellow-400' }
          ].map((stat, idx) => (
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
            className={`flex-1 md:flex-initial px-8 py-4 rounded-xl font-bold text-lg transition-all duration-300 ${
              activeTab === 'markets'
                ? 'bg-gradient-to-r from-green-600 to-emerald-600 text-white shadow-lg shadow-green-500/30 scale-105'
                : 'bg-slate-800/50 text-gray-400 hover:bg-slate-700/50 hover:text-white'
            }`}
          >
            <Target className="inline h-5 w-5 mr-2" />
            Active Markets
          </button>
          
          <button
            onClick={() => setActiveTab('mybets')}
            className={`flex-1 md:flex-initial px-8 py-4 rounded-xl font-bold text-lg transition-all duration-300 ${
              activeTab === 'mybets'
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
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-gradient-to-br from-green-900/30 to-green-800/20 border border-green-500/30 rounded-2xl p-6">
                    <div className="text-sm text-green-400 mb-1 uppercase tracking-wide">Total Staked</div>
                    <div className="text-3xl font-black text-white">
                      ${myBets.filter(b => b.status === 'confirmed').reduce((sum, bet) => sum + bet.amount, 0).toFixed(2)}
                    </div>
                  </div>
                  
                  <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/20 border border-blue-500/30 rounded-2xl p-6">
                    <div className="text-sm text-blue-400 mb-1 uppercase tracking-wide">Potential Winnings</div>
                    <div className="text-3xl font-black text-white">
                      ${myBets.filter(b => !b.resolved).reduce((sum, bet) => sum + (bet.payout || 0), 0).toFixed(2)}
                    </div>
                  </div>
                  
                  <div className="bg-gradient-to-br from-purple-900/30 to-purple-800/20 border border-purple-500/30 rounded-2xl p-6">
                    <div className="text-sm text-purple-400 mb-1 uppercase tracking-wide">Active Bets</div>
                    <div className="text-3xl font-black text-white">
                      {myBets.filter(b => !b.resolved).length}
                    </div>
                  </div>
                </div>

                {/* Bets List */}
                <div className="space-y-4">
                  {myBets.map(bet => (
                    <div
                      key={bet.id}
                      className={`bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border transition-all hover:scale-[1.01] ${
                        bet.won 
                          ? 'border-green-500/50 hover:border-green-500' 
                          : bet.resolved 
                          ? 'border-red-500/30 opacity-60' 
                          : 'border-slate-700/50 hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                              bet.prediction 
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
                            {bet.status === 'confirmed' && (
                              <span className="px-3 py-1 rounded-full text-xs font-bold bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" />
                                Confirmed
                              </span>
                            )}
                            {bet.resolved && bet.won && (
                              <span className="px-3 py-1 rounded-full text-xs font-bold bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 animate-pulse">
                                WON
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
                          <div className="text-xl font-bold text-white">${bet.amount.toFixed(2)}</div>
                          {bet.payout && !bet.resolved && (
                            <div className="text-xs text-green-400 mt-1">
                              Potential: ${bet.payout.toFixed(2)}
                            </div>
                          )}
                          {bet.won && bet.payout && (
                            <div className="text-lg font-bold text-green-400 mt-1">
                              +${bet.payout.toFixed(2)}
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* ✅ BLOCKCHAIN EXPLORER LINK */}
                      {bet.tx_hash && (
                        <a
                          href={`https://camp-network-testnet.blockscout.com/tx/${bet.tx_hash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-4 flex items-center justify-center gap-2 py-2 px-4 bg-slate-700/50 hover:bg-slate-600/50 rounded-lg text-xs text-gray-400 hover:text-white transition-all"
                        >
                          <ExternalLink className="w-3 h-3" />
                          View on Blockchain Explorer
                        </a>
                      )}
                      
                      {bet.won && !bet.resolved && (
                        <button
                          onClick={() => {/* Claim winnings logic */}}
                          className="w-full mt-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-green-500/30 transition-all flex items-center justify-center gap-2"
                        >
                          <Trophy className="h-5 w-5" />
                          Claim ${bet.payout?.toFixed(2)}
                        </button>
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
                        toast.success('🎉 Bet confirmed on-chain!', { duration: 5000 });
                        setTimeout(() => {
                          setActiveTransaction(null);
                          setShowBetModal(false);
                        }, 3000);
                      }}
                    />
                  </div>
                ) : (
                  <>
                    {/* YES/NO Toggle */}
                    <div className="grid grid-cols-2 gap-3 mb-6">
                      <button
                        onClick={() => setBetPrediction(true)}
                        className={`p-6 rounded-xl border-2 transition-all ${
                          betPrediction
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
                        className={`p-6 rounded-xl border-2 transition-all ${
                          !betPrediction
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
                      <label className="block text-sm font-semibold text-gray-400 mb-2">Bet Amount (USDC)</label>
                      <div className="relative">
                        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-2xl text-gray-500">$</span>
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
                        {[10, 50, 100, 500].map(amount => (
                          <button
                            key={amount}
                            onClick={() => setBetAmount(amount.toString())}
                            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-green-500 rounded-lg text-sm font-semibold text-gray-300 hover:text-white transition-all"
                          >
                            ${amount}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Payout Breakdown */}
                    <div className="bg-slate-800/50 rounded-xl p-5 mb-6 border border-slate-700">
                      <div className="flex justify-between mb-3">
                        <span className="text-gray-400">Your Bet</span>
                        <span className="text-white font-semibold">${betAmount || '0'}</span>
                      </div>
                      <div className="flex justify-between mb-3">
                        <span className="text-gray-400">Potential Return</span>
                        <span className="text-green-400 font-semibold">${calculatePotentialPayout().toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between mb-3">
                        <span className="text-gray-400">Platform Fee (1.8%)</span>
                        <span className="text-gray-500 font-semibold">-${(calculatePotentialPayout() * 0.018).toFixed(2)}</span>
                      </div>
                      <div className="pt-3 border-t border-slate-700 flex justify-between">
                        <span className="text-white font-bold">Net Payout</span>
                        <span className="text-2xl text-green-400 font-black">${(calculatePotentialPayout() * 0.982).toFixed(2)}</span>
                      </div>
                    </div>

                    {/* Warning */}
                    <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 mb-6 flex gap-3">
                      <Info className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-yellow-200">
                        Betting is implemented on Camp testnet. Check back soon for the real deal!
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
                          `Place ${betAmount ? `$${betAmount}` : ''} Bet`
                        )}
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 🔥 IN-APP WALLET CONNECTION MODAL */}
        {showWalletModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-slate-900 rounded-2xl border border-slate-700 max-w-md w-full p-6 relative">
              <button
                onClick={() => setShowWalletModal(false)}
                className="absolute top-4 right-4 text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="text-center mb-6">
                <div className="w-16 h-16 bg-gradient-to-br from-green-600 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Wallet className="w-8 h-8 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">🎯 Connect to Place Bets</h2>
                <p className="text-gray-400 text-sm mb-4">
                  You need a MetaMask wallet with <span className="text-green-400 font-semibold">CAMP tokens</span> to participate
                </p>
                <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 mb-4">
                  <p className="text-blue-300 text-xs">
                    ℹ️ <strong>Judges:</strong> Use your MetaMask BaseCAMP testnet wallet. 
                    Get free CAMP at <a 
                      href="https://faucet.campnetwork.xyz/" 
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline hover:text-blue-200"
                    >
                      faucet.campnetwork.xyz
                    </a>
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <button
                  onClick={connectWallet}
                  disabled={connecting}
                  className="w-full p-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-green-500/50 rounded-xl transition flex items-center justify-between group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-orange-500 rounded-lg flex items-center justify-center">
                      <span className="text-white font-bold text-sm">🦊</span>
                    </div>
                    <div className="text-left">
                      <div className="text-white font-semibold">MetaMask</div>
                      <div className="text-gray-400 text-xs">Most popular wallet</div>
                    </div>
                  </div>
                  {connecting ? (
                    <Loader className="w-5 h-5 text-green-400 animate-spin" />
                  ) : (
                    <CheckCircle className="w-5 h-5 text-gray-600 group-hover:text-green-400 transition" />
                  )}
                </button>

                <div className="text-center text-xs text-gray-500 pt-2">
                  Don't have a wallet?{' '}
                  <a 
                    href="https://metamask.io/download/" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-green-400 hover:underline"
                  >
                    Download MetaMask
                  </a>
                </div>
              </div>

              <div className="mt-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <div className="flex gap-2">
                  <span className="text-yellow-400 text-sm">💡</span>
                  <div>
                    <p className="text-yellow-200 text-sm font-semibold mb-1">New to BaseCAMP?</p>
                    <p className="text-yellow-200/80 text-xs">
                      Get free testnet CAMP tokens at{' '}
                      <a 
                        href="https://faucet.campnetwork.xyz/" 
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline hover:text-yellow-100"
                      >
                        faucet.campnetwork.xyz
                      </a>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PredictionMarketsPage;