// 📂 FILE: frontend/src/components/pages/PredictionMarketsPage.tsx
import React, { useState, useEffect } from 'react';
import { TrendingUp, DollarSign, Users, Clock, AlertTriangle, CheckCircle, XCircle, Zap, Trophy, Target, ArrowRight, Info } from 'lucide-react';

import { apiClient } from '@/config/api';
import { supabase } from '@/lib/supabase';
import toast from 'react-hot-toast';
import { WalletConnectionModal } from '@/components/WalletConnectionModal'; // 🆕 ADD THIS IMPORT

declare global {
  interface Window {
    ethereum?: any;
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

interface ConnectedWallet {
  address: string;
  chain: string;
  chainName: string;
  walletSource: string;
  verified: boolean;
}

const PredictionMarketsPage: React.FC = () => {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [myBets, setMyBets] = useState<Bet[]>([]);
  const [selectedMarket, setSelectedMarket] = useState<Market | null>(null);
  const [betAmount, setBetAmount] = useState<string>('10');
  const [betPrediction, setBetPrediction] = useState<boolean>(true);
  const [loading, setLoading] = useState(false);
  const [showBetModal, setShowBetModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'markets' | 'mybets'>('markets');

  // 🔌 WALLET CONNECTION STATE (UPDATED)
  const [externalWallet, setExternalWallet] = useState<{
    connected: boolean;
    address: string;
    chainName: string;
    walletSource: string;
    verified: boolean;
  }>({
    connected: false,
    address: '',
    chainName: '',
    walletSource: '',
    verified: false
  });
  const [showWalletModal, setShowWalletModal] = useState(false); // 🆕 NEW STATE
  const [signingTransaction, setSigningTransaction] = useState(false);
  const CAMP_CHAIN_ID = 325000; // Camp Network Testnet V2

// Check for existing wallet connection on mount (ONCE ONLY)
useEffect(() => {
  let isMounted = true; // Prevent state updates after unmount
  
  const checkExistingConnection = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token || !isMounted) return;

      const response = await fetch('/api/v1/wallet/external-wallets', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });

      if (response.ok && isMounted) {
        const data = await response.json();
        if (data.wallets && data.wallets.length > 0) {
          const wallet = data.wallets[0];
          setExternalWallet({
            connected: true,
            address: wallet.address,
            chainName: wallet.chain_name,
            walletSource: wallet.wallet_source,
            verified: wallet.verified
          });
          console.log('✅ Existing wallet connection found:', wallet.address);
        }
      }
    } catch (error) {
      if (isMounted) {
        console.error('Failed to check existing wallet:', error);
      }
    }
  };

  checkExistingConnection();
  
  return () => {
    isMounted = false; // Cleanup
  };
}, []); // ✅ EMPTY DEPS ARRAY - ONLY RUN ONCE

  // Handle successful wallet connection from modal
  const handleWalletConnected = (wallet: ConnectedWallet) => {
    setExternalWallet({
      connected: true,
      address: wallet.address,
      chainName: wallet.chainName,
      walletSource: wallet.walletSource,
      verified: wallet.verified
    });
    setShowWalletModal(false);
    console.log('✅ Wallet connected:', wallet);
  };

  // 🔄 SWITCH TO CAMP NETWORK (Updated to work with any wallet provider)
  const switchToCampNetwork = async () => {
    if (typeof window.ethereum === 'undefined') {
      toast.error('No wallet detected. Please connect a wallet first.');
      setShowWalletModal(true);
      return;
    }

    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: `0x${CAMP_CHAIN_ID.toString(16)}` }]
      });
      toast.success('✅ Switched to Camp Network');
    } catch (switchError: any) {
      // Chain not added to wallet
      if (switchError.code === 4902) {
        try {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [{
              chainId: `0x${CAMP_CHAIN_ID.toString(16)}`,
              chainName: 'Camp Network Testnet V2',
              rpcUrls: ['https://rpc.camp-network-testnet.gelato.digital'],
              nativeCurrency: {
                name: 'ETH',
                symbol: 'ETH',
                decimals: 18
              },
              blockExplorerUrls: ['https://camp.cloud.blockscout.com']
            }]
          });
          toast.success('✅ Camp Network added to wallet');
        } catch (addError) {
          toast.error('Failed to add Camp Network to wallet');
        }
      } else {
        toast.error('Failed to switch network');
      }
    }
  };

  // Check wallet chain (Updated for new wallet structure)
  const checkWalletChain = () => {
    if (externalWallet.chainName !== 'Camp Network') {
      return false;
    }
    return true;
  };

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
    console.log('🎯 handlePlaceBet called');
    console.log('📊 Selected market:', selectedMarket?.id);
    console.log('💰 Bet amount:', betAmount);
    console.log('🔌 Wallet connected:', externalWallet.connected);
    console.log('🌐 Chain check:', checkWalletChain());
    
    if (!selectedMarket || !betAmount) return;

    // ⚠️ CHECK WALLET CONNECTION (UPDATED)
    if (!externalWallet.connected) {
      toast.error('Please connect your wallet first');
      setShowWalletModal(true);
      return;
    }

    // ⚠️ CHECK CORRECT NETWORK (UPDATED)
    if (!checkWalletChain()) {
      toast.error(`Wrong network! Switch to Camp Network (Chain ID: ${CAMP_CHAIN_ID})`);
      await switchToCampNetwork();
      return;
    }
    
    setLoading(true);
    setSigningTransaction(true);
    
    try {
      // 1️⃣ RECORD BET IN DATABASE
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session?.access_token) {
        toast.error('Please sign in to place bets');
        return;
      }

      toast.loading('Recording bet...', { id: 'bet-process' });
      
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
          wallet_address: externalWallet.address
        })
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.detail || 'Failed to record bet');
      }
      
      const betId = data.bet_id;
      console.log('✅ Bet recorded:', betId);

      // 2️⃣ APPROVE USDC (Client-side signing)
      if (typeof window.ethereum === 'undefined') {
        throw new Error('Wallet not available');
      }

      toast.loading('Step 1/2: Approving USDC...', { id: 'bet-process' });
      
      const Web3 = (await import('web3')).default;
      const web3 = new Web3(window.ethereum);
      
      const USDC_ADDRESS = '0x977fdEF62CE095Ae8750Fd3496730F24F60dea7a';
      const CONTRACT_ADDRESS = '0xc54a1b1ac9890191aB56849B45bA5C0604293A75';
      
      const usdcAbi = [
        {
          "constant": false,
          "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
          ],
          "name": "approve",
          "outputs": [{"name": "", "type": "bool"}],
          "type": "function"
        }
      ];
      
      const usdcContract = new web3.eth.Contract(usdcAbi, USDC_ADDRESS);
      const amountWei = web3.utils.toWei(betAmount, 'mwei');
      
      const approveTx = await usdcContract.methods
        .approve(CONTRACT_ADDRESS, amountWei)
        .send({ from: externalWallet.address });
      
      console.log('✅ USDC approved:', approveTx.transactionHash);

      // 3️⃣ PLACE BET ON SMART CONTRACT
      toast.loading('Step 2/2: Placing bet on-chain...', { id: 'bet-process' });
      
      const marketAbi = [
        {
          "inputs": [
            {"name": "marketId", "type": "uint256"},
            {"name": "prediction", "type": "bool"},
            {"name": "amount", "type": "uint256"}
          ],
          "name": "placeBet",
          "outputs": [],
          "stateMutability": "nonpayable",
          "type": "function"
        }
      ];
      
      const marketContract = new web3.eth.Contract(marketAbi, CONTRACT_ADDRESS);
      
      const betTx = await marketContract.methods
        .placeBet(selectedMarket.id, betPrediction, amountWei)
        .send({ from: externalWallet.address });
      
      console.log('✅ Bet placed:', betTx.transactionHash);

      // 4️⃣ UPDATE DATABASE WITH TX HASH
      await fetch('/api/v1/predictions/update-bet', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          bet_id: betId,
          tx_hash: betTx.transactionHash,
          status: 'confirmed'
        })
      });

      toast.success(
        `🎉 Bet placed! View on explorer: https://camp.cloud.blockscout.com/tx/${betTx.transactionHash}`,
        { id: 'bet-process', duration: 7000 }
      );
      
      // Refresh data
      await fetchMarkets();
      await fetchMyBets();
      setShowBetModal(false);
      setBetAmount('10');
      
    } catch (error: any) {
      console.error('❌ Bet placement failed:', error);
      
      let errorMsg = 'Bet placement failed';
      if (error.message?.includes('User denied')) {
        errorMsg = 'Transaction rejected by user';
      } else if (error.message?.includes('insufficient funds')) {
        errorMsg = 'Insufficient USDC or ETH for gas';
      }
      
      toast.error(errorMsg, { id: 'bet-process' });
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Hero Header */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-3 mb-4 px-6 py-3 bg-gradient-to-r from-green-500/20 to-emerald-500/20 rounded-full border border-green-500/30">
            <Zap className="h-5 w-5 text-green-400 animate-pulse" />
            <span className="text-green-400 font-semibold text-sm">5 LIVE MARKETS • $0 VOLUME</span>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white via-green-100 to-emerald-300 mb-3">
            Seamount Predictions
          </h1>
          
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Bet on sports, crypto, FX, and politics with <span className="text-green-400 font-semibold">USDC</span> on Camp Network
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
        
        {/* 🆕 UPDATED WALLET CONNECTION BANNERS */}
        {!externalWallet.connected ? (
          <div className="bg-gradient-to-r from-purple-900/50 to-pink-900/50 border border-purple-500/30 rounded-2xl p-6 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold text-white mb-2">🔐 Connect Your Wallet</h3>
                <p className="text-gray-300">Connect your Web3 wallet to start betting on prediction markets</p>
              </div>
              <button
                onClick={() => setShowWalletModal(true)}
                disabled={loading}
                className="px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-purple-500/30 transition-all disabled:opacity-50"
              >
                {loading ? 'Connecting...' : 'Connect Wallet'}
              </button>
            </div>
          </div>
        ) : !checkWalletChain() ? (
          <div className="bg-gradient-to-r from-yellow-900/50 to-orange-900/50 border border-yellow-500/30 rounded-2xl p-6 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold text-white mb-2">⚠️ Wrong Network</h3>
                <p className="text-gray-300">Please switch to Camp Network Testnet V2 (Chain ID: {CAMP_CHAIN_ID})</p>
              </div>
              <button
                onClick={switchToCampNetwork}
                className="px-8 py-4 bg-gradient-to-r from-yellow-600 to-orange-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-yellow-500/30 transition-all"
              >
                Switch Network
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-gradient-to-r from-green-900/30 to-emerald-900/30 border border-green-500/30 rounded-2xl p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-3 w-3 bg-green-500 rounded-full animate-pulse" />
                <div>
                  <span className="text-white font-semibold">
                    {externalWallet.walletSource} Connected: {externalWallet.address.slice(0, 6)}...{externalWallet.address.slice(-4)}
                  </span>
                  <div className="text-xs text-gray-400">
                    {externalWallet.verified ? '✓ Verified' : '⚠️ Needs verification'}
                  </div>
                </div>
              </div>
              <span className="text-green-400 text-sm">{externalWallet.chainName} ✓</span>
            </div>
          </div>
        )}
        
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
                      ${myBets.reduce((sum, bet) => sum + bet.amount, 0).toFixed(2)}
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
                            {bet.resolved && bet.won && (
                              <span className="px-3 py-1 rounded-full text-xs font-bold bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 animate-pulse">
                                WON 🎉
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
                      
                      {bet.won && !bet.resolved && (
                        <button
                          onClick={() => {/* Claim winnings logic */}}
                          className="w-full py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-green-500/30 transition-all flex items-center justify-center gap-2"
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
                    onClick={() => setShowBetModal(false)}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    <XCircle className="h-6 w-6" />
                  </button>
                </div>
              </div>

              {/* Modal Body */}
              <div className="p-6">
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
                    disabled={loading || signingTransaction || !betAmount || parseFloat(betAmount) < 1 || !externalWallet.connected}
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
              </div>
            </div>
          </div>
        )}

        {/* 🆕 WALLET CONNECTION MODAL */}
        <WalletConnectionModal
          isOpen={showWalletModal}
          onClose={() => setShowWalletModal(false)}
          onSuccess={handleWalletConnected}
        />
      </div>
    </div>
  );
};

export default PredictionMarketsPage;