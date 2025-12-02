import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { TrendingUp, DollarSign, Users, Clock, Trophy, Target, ArrowRight, Info, XCircle, Zap } from 'lucide-react';

// Mock supabase for demo
const supabase = {
  auth: {
    getSession: async () => ({
      data: { session: { access_token: 'demo-token' } }
    })
  }
};

// Mock toast for demo
const toast = {
  success: (msg: string, opts?: any) => console.log('✅', msg),
  error: (msg: string, opts?: any) => console.error('❌', msg),
  loading: (msg: string, opts?: any) => console.log('⏳', msg)
};

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
}

const CAMP_CHAIN_ID = 325000;

// Mock data
const MOCK_MARKETS: Market[] = [
  {
    id: 0,
    question: "Will Bitcoin reach $100K by end of 2025?",
    description: "BTC must close above $100,000 on any major exchange by December 31, 2025",
    endTime: Date.now() + 86400000 * 30,
    resolved: false,
    outcome: false,
    totalVolume: "50000000",
    participantCount: 42,
    yesOdds: 6500,
    noOdds: 3500,
    timeRemaining: 86400 * 30,
    yesPercent: 65,
    noPercent: 35
  },
  {
    id: 1,
    question: "Will Arsenal win Premier League 2024/25?",
    description: "Arsenal must be top of the table when the season ends",
    endTime: Date.now() + 86400000 * 60,
    resolved: false,
    outcome: false,
    totalVolume: "25000000",
    participantCount: 28,
    yesOdds: 4500,
    noOdds: 5500,
    timeRemaining: 86400 * 60,
    yesPercent: 45,
    noPercent: 55
  }
];

const PredictionMarketsPage: React.FC = () => {
  // ✅ SIMPLE STATE - PRIMITIVES ONLY
  const [markets, setMarkets] = useState<Market[]>(MOCK_MARKETS);
  const [myBets, setMyBets] = useState<Bet[]>([]);
  const [selectedMarket, setSelectedMarket] = useState<Market | null>(null);
  const [betAmount, setBetAmount] = useState<string>('10');
  const [betPrediction, setBetPrediction] = useState<boolean>(true);
  const [loading, setLoading] = useState(false);
  const [showBetModal, setShowBetModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'markets' | 'mybets'>('markets');
  
  // ✅ WALLET STATE - SIMPLE STRINGS
  const [walletConnected, setWalletConnected] = useState(false);
  const [walletAddress, setWalletAddress] = useState('');

  // ✅ LOAD WALLET FROM LOCALSTORAGE ONCE (RUNS ONCE)
  useEffect(() => {
    const savedWallet = localStorage.getItem('seamount_wallet_address');
    if (savedWallet) {
      setWalletAddress(savedWallet);
      setWalletConnected(true);
    }
  }, []); // ✅ EMPTY DEPS - RUNS ONCE

  // ✅ CONNECT WALLET - MEMOIZED (NEVER RECREATED)
  const connectWallet = useCallback(async () => {
    if (typeof window.ethereum === 'undefined') {
      toast.error('Please install MetaMask');
      return;
    }

    try {
      setLoading(true);
      
      const accounts = await window.ethereum.request({ 
        method: 'eth_requestAccounts' 
      });
      const address = accounts[0];

      // Switch to Camp Network
      try {
        await window.ethereum.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: `0x${CAMP_CHAIN_ID.toString(16)}` }]
        });
      } catch (switchError: any) {
        if (switchError.code === 4902) {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [{
              chainId: `0x${CAMP_CHAIN_ID.toString(16)}`,
              chainName: 'Camp Network Testnet V2',
              rpcUrls: ['https://rpc.camp-network-testnet.gelato.digital'],
              nativeCurrency: { name: 'ETH', symbol: 'ETH', decimals: 18 },
              blockExplorerUrls: ['https://camp.cloud.blockscout.com']
            }]
          });
        }
      }

      // Update state
      setWalletAddress(address);
      setWalletConnected(true);
      localStorage.setItem('seamount_wallet_address', address);
      toast.success('✅ Wallet connected!');
      
    } catch (error: any) {
      console.error('Wallet connection failed:', error);
      if (error.code === 4001) {
        toast.error('Connection rejected');
      } else {
        toast.error('Connection failed');
      }
    } finally {
      setLoading(false);
    }
  }, []); // ✅ NO DEPS - FUNCTION NEVER RECREATED

  // ✅ MEMOIZED HELPER FUNCTIONS
  const formatTimeRemaining = useCallback((seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  }, []);

  const formatVolume = useCallback((volume: string) => {
    const num = parseFloat(volume) / 1000000;
    if (num >= 1000000) return `$${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `$${(num / 1000).toFixed(1)}K`;
    return `$${num.toFixed(0)}`;
  }, []);

  // ✅ CALCULATE PAYOUT - MEMOIZED (ONLY RECALCS WHEN DEPS CHANGE)
  const potentialPayout = useMemo(() => {
    if (!selectedMarket || !betAmount) return 0;
    
    const amount = parseFloat(betAmount);
    const totalPool = parseFloat(selectedMarket.totalVolume) / 1000000 + amount;
    const winningPool = betPrediction 
      ? (selectedMarket.yesPercent * parseFloat(selectedMarket.totalVolume) / 100000000) + amount
      : (selectedMarket.noPercent * parseFloat(selectedMarket.totalVolume) / 100000000) + amount;
    
    if (winningPool === 0) return amount * 1.96;
    
    const grossPayout = (amount / winningPool) * totalPool;
    return grossPayout * 0.982;
  }, [selectedMarket, betAmount, betPrediction]); // ✅ ONLY RECALC WHEN THESE CHANGE

  const handlePlaceBet = async () => {
    if (!selectedMarket || !betAmount) return;

    if (!walletConnected || !walletAddress) {
      toast.error('Please connect your wallet first');
      connectWallet();
      return;
    }
    
    setLoading(true);
    
    try {
      toast.loading('Demo: Simulating bet placement...', { id: 'bet-process' });
      
      // Simulate async operation
      await new Promise(resolve => setTimeout(resolve, 2000));

      toast.success(`🎉 Demo bet placed: $${betAmount} on ${betPrediction ? 'YES' : 'NO'}!`, { 
        id: 'bet-process', 
        duration: 5000 
      });
      
      setShowBetModal(false);
      setBetAmount('10');
      
    } catch (error: any) {
      console.error('Bet placement failed:', error);
      toast.error('Demo: Bet placement failed', { id: 'bet-process' });
    } finally {
      setLoading(false);
    }
  };

  const getCategoryFromQuestion = (question: string) => {
    if (question.toLowerCase().includes('bitcoin') || question.toLowerCase().includes('btc')) return 'crypto';
    if (question.toLowerCase().includes('arsenal') || question.toLowerCase().includes('premier')) return 'sports';
    return 'other';
  };

  const getCategoryEmoji = (category: string) => {
    const emojis: Record<string, string> = {
      sports: '⚽',
      crypto: '₿',
      other: '📊'
    };
    return emojis[category] || '📊';
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      sports: 'from-blue-500 to-cyan-500',
      crypto: 'from-purple-500 to-pink-500',
      other: 'from-gray-500 to-slate-500'
    };
    return colors[category] || 'from-gray-500 to-slate-500';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-3 mb-4 px-6 py-3 bg-gradient-to-r from-green-500/20 to-emerald-500/20 rounded-full border border-green-500/30">
            <Zap className="h-5 w-5 text-green-400 animate-pulse" />
            <span className="text-green-400 font-semibold text-sm">DEMO MODE • {markets.length} MARKETS</span>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white via-green-100 to-emerald-300 mb-3">
            Seamount Predictions
          </h1>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Bet on sports, crypto, FX, and politics with USDC on Camp Network
          </p>
        </div>

        {/* Wallet Banner - SIMPLE VERSION */}
        {!walletConnected ? (
          <div className="bg-gradient-to-r from-purple-900/50 to-pink-900/50 border border-purple-500/30 rounded-2xl p-4 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white mb-1">🔌 Connect MetaMask</h3>
                <p className="text-gray-300 text-sm">Connect to start betting</p>
              </div>
              <button
                onClick={connectWallet}
                disabled={loading}
                className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-purple-500/30 transition-all disabled:opacity-50"
              >
                {loading ? 'Connecting...' : 'Connect MetaMask'}
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-gradient-to-r from-green-900/30 to-emerald-900/30 border border-green-500/30 rounded-2xl p-3 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-white font-semibold text-sm">
                  {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
                </span>
              </div>
              <span className="text-green-400 text-xs">Camp Network ✓</span>
            </div>
          </div>
        )}
        
        {/* Tabs */}
        <div className="flex gap-3 mb-6">
          <button
            onClick={() => setActiveTab('markets')}
            className={`flex-1 md:flex-initial px-8 py-4 rounded-xl font-bold text-lg transition-all duration-300 ${
              activeTab === 'markets'
                ? 'bg-gradient-to-r from-green-600 to-emerald-600 text-white shadow-lg'
                : 'bg-slate-800/50 text-gray-400 hover:bg-slate-700/50'
            }`}
          >
            <Target className="inline h-5 w-5 mr-2" />
            Active Markets
          </button>
          
          <button
            onClick={() => setActiveTab('mybets')}
            className={`flex-1 md:flex-initial px-8 py-4 rounded-xl font-bold text-lg transition-all duration-300 ${
              activeTab === 'mybets'
                ? 'bg-gradient-to-r from-green-600 to-emerald-600 text-white shadow-lg'
                : 'bg-slate-800/50 text-gray-400 hover:bg-slate-700/50'
            }`}
          >
            <Trophy className="inline h-5 w-5 mr-2" />
            My Bets ({myBets.length})
          </button>
        </div>

        {/* Markets Grid */}
        {activeTab === 'markets' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {markets.map(market => {
              const category = getCategoryFromQuestion(market.question);
              return (
                <div
                  key={market.id}
                  onClick={() => {
                    setSelectedMarket(market);
                    setShowBetModal(true);
                  }}
                  className="group bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50 hover:border-green-500/50 transition-all cursor-pointer hover:scale-[1.02]"
                >
                  <div className="flex items-center justify-between mb-4">
                    <span className={`px-4 py-1.5 rounded-full text-xs font-bold text-white bg-gradient-to-r ${getCategoryColor(category)}`}>
                      {getCategoryEmoji(category)} {category.toUpperCase()}
                    </span>
                    <div className="flex items-center gap-2 text-gray-400">
                      <Clock className="h-4 w-4" />
                      <span className="text-sm font-semibold">{formatTimeRemaining(market.timeRemaining)}</span>
                    </div>
                  </div>

                  <h3 className="text-xl font-bold text-white mb-3 group-hover:text-green-400 transition-colors">
                    {market.question}
                  </h3>
                  
                  <p className="text-gray-400 text-sm mb-5 line-clamp-2">
                    {market.description}
                  </p>

                  <div className="grid grid-cols-2 gap-3 mb-5">
                    <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-green-900/30 to-green-800/20 border border-green-500/30 p-4">
                      <div className="text-xs text-green-400 font-bold mb-1">YES</div>
                      <div className="text-3xl font-black text-white">{market.yesPercent}%</div>
                    </div>
                    
                    <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-red-900/30 to-red-800/20 border border-red-500/30 p-4">
                      <div className="text-xs text-red-400 font-bold mb-1">NO</div>
                      <div className="text-3xl font-black text-white">{market.noPercent}%</div>
                    </div>
                  </div>

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
                    
                    <button className="flex items-center gap-2 text-green-400 font-semibold text-sm">
                      Place Bet
                      <ArrowRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* My Bets Tab */}
        {activeTab === 'mybets' && (
          <div className="bg-slate-800/50 rounded-2xl p-12 text-center">
            <Trophy className="h-20 w-20 text-gray-600 mx-auto mb-4" />
            <h3 className="text-2xl font-bold text-white mb-2">No Bets Yet</h3>
            <button
              onClick={() => setActiveTab('markets')}
              className="px-8 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-bold rounded-xl"
            >
              Browse Markets
            </button>
          </div>
        )}

        {/* Bet Modal */}
        {showBetModal && selectedMarket && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
            <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-slate-700">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-2">{selectedMarket.question}</h2>
                    <p className="text-gray-400 text-sm">{selectedMarket.description}</p>
                  </div>
                  <button onClick={() => setShowBetModal(false)} className="text-gray-400 hover:text-white">
                    <XCircle className="h-6 w-6" />
                  </button>
                </div>
              </div>

              <div className="p-6">
                <div className="grid grid-cols-2 gap-3 mb-6">
                  <button
                    onClick={() => setBetPrediction(true)}
                    className={`p-6 rounded-xl border-2 transition-all ${
                      betPrediction
                        ? 'bg-gradient-to-br from-green-600 to-emerald-600 border-green-400'
                        : 'bg-slate-800/50 border-slate-700'
                    }`}
                  >
                    <div className="text-lg font-bold text-white mb-1">YES</div>
                    <div className="text-3xl font-black text-white">{selectedMarket.yesPercent}%</div>
                  </button>
                  
                  <button
                    onClick={() => setBetPrediction(false)}
                    className={`p-6 rounded-xl border-2 transition-all ${
                      !betPrediction
                        ? 'bg-gradient-to-br from-red-600 to-rose-600 border-red-400'
                        : 'bg-slate-800/50 border-slate-700'
                    }`}
                  >
                    <div className="text-lg font-bold text-white mb-1">NO</div>
                    <div className="text-3xl font-black text-white">{selectedMarket.noPercent}%</div>
                  </button>
                </div>

                <div className="mb-6">
                  <label className="block text-sm font-semibold text-gray-400 mb-2">Bet Amount (USDC)</label>
                  <input
                    type="number"
                    value={betAmount}
                    onChange={(e) => setBetAmount(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-4 text-2xl font-bold text-white"
                    placeholder="10"
                    min="1"
                  />
                </div>

                <div className="bg-slate-800/50 rounded-xl p-5 mb-6 border border-slate-700">
                  <div className="flex justify-between mb-3">
                    <span className="text-gray-400">Your Bet</span>
                    <span className="text-white font-semibold">${betAmount || '0'}</span>
                  </div>
                  <div className="flex justify-between mb-3">
                    <span className="text-gray-400">Potential Return</span>
                    <span className="text-green-400 font-semibold">${potentialPayout.toFixed(2)}</span>
                  </div>
                  <div className="pt-3 border-t border-slate-700 flex justify-between">
                    <span className="text-white font-bold">Net Payout</span>
                    <span className="text-2xl text-green-400 font-black">${(potentialPayout * 0.982).toFixed(2)}</span>
                  </div>
                </div>

                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 mb-6 flex gap-3">
                  <Info className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-yellow-200">
                    This is a demo. In production, this would interact with Camp Network smart contracts.
                  </p>
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={() => setShowBetModal(false)}
                    className="flex-1 px-6 py-4 bg-slate-800 border border-slate-700 text-white font-bold rounded-xl"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handlePlaceBet}
                    disabled={loading || !betAmount || parseFloat(betAmount) < 1 || !walletConnected}
                    className="flex-1 px-6 py-4 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-green-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Processing...' : `Place $${betAmount} Bet`}
                  </button>
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