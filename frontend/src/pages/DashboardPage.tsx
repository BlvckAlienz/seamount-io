import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, TrendingDown, DollarSign, Activity, Send, 
  RefreshCw, Shield, AlertTriangle, Bitcoin, Coins, Copy, 
  Check, Eye, EyeOff, Download, Lock, ExternalLink, ArrowUpRight, ArrowDownLeft
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { portfolioAPI, userAPI } from '../config/api';

// Asset Card Component with 0-balance visibility
const AssetCard = ({ asset, onBuy, onSend }: { asset: any; onBuy: () => void; onSend: () => void }) => {
  const getGradient = (symbol: string) => {
    const gradients: { [key: string]: string } = {
      'ALGO': 'from-purple-500 to-indigo-600',
      'USDT': 'from-green-500 to-emerald-600',
      'USDCa': 'from-blue-500 to-cyan-600',
      'goBTC': 'from-orange-500 to-yellow-600',
      'goETH': 'from-gray-400 to-slate-600'
    };
    return gradients[symbol] || 'from-gray-500 to-gray-600';
  };

  const getIcon = (symbol: string) => {
    switch (symbol) {
      case 'goBTC': return <Bitcoin className="h-8 w-8" />;
      case 'goETH': return <Coins className="h-8 w-8" />;
      case 'ALGO': return <Shield className="h-8 w-8" />;
      default: return <DollarSign className="h-8 w-8" />;
    }
  };

  const balance = asset.balance || 0;
  const valueUsd = asset.value_usd || 0;
  const hasBalance = balance > 0;

  return (
    <div className="group relative bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50 hover:border-blue-500/50 transition-all hover:shadow-xl hover:shadow-blue-500/10">
      <div className={`absolute inset-0 bg-gradient-to-br ${getGradient(asset.symbol)} opacity-0 group-hover:opacity-10 rounded-2xl transition-opacity`} />
      
      <div className="relative">
        <div className="flex items-start justify-between mb-4">
          <div className={`p-3 rounded-xl bg-gradient-to-br ${getGradient(asset.symbol)} text-white`}>
            {getIcon(asset.symbol)}
          </div>
          <div className="text-right">
            <div className={`text-2xl font-bold ${hasBalance ? 'text-white' : 'text-gray-500'}`}>
              ${valueUsd.toFixed(2)}
            </div>
            <div className="text-sm text-gray-400">â‰ˆ {balance.toFixed(6)}</div>
          </div>
        </div>

        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-white font-semibold">{asset.name}</div>
            <div className="text-gray-400 text-sm">{asset.symbol}</div>
          </div>
          <div className="text-right">
            <div className="text-gray-400 text-sm">${asset.price_usd?.toFixed(2) || '0.00'}</div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={onBuy}
            className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-3 rounded-lg text-sm font-medium transition-colors"
          >
            <ArrowDownLeft className="h-4 w-4" />
            Buy
          </button>
          <button
            onClick={onSend}
            disabled={!hasBalance}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
              hasBalance 
                ? 'bg-gray-700 hover:bg-gray-600 text-white' 
                : 'bg-gray-800 text-gray-500 cursor-not-allowed'
            }`}
          >
            <ArrowUpRight className="h-4 w-4" />
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

// Mnemonic Backup Modal
const MnemonicBackupModal = ({ 
  mnemonic, 
  walletAddress, 
  onComplete 
}: { 
  mnemonic: string; 
  walletAddress: string; 
  onComplete: () => void;
}) => {
  const [step, setStep] = useState(1);
  const [showMnemonic, setShowMnemonic] = useState(false);
  const [verificationWords, setVerificationWords] = useState<number[]>([]);
  const [userInputs, setUserInputs] = useState<{ [key: number]: string }>({});
  const [copied, setCopied] = useState(false);

  const words = mnemonic.split(' ');

  useEffect(() => {
    const positions: number[] = [];
    while (positions.length < 3) {
      const pos = Math.floor(Math.random() * 25);
      if (!positions.includes(pos)) positions.push(pos);
    }
    setVerificationWords(positions.sort((a, b) => a - b));
  }, []);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(mnemonic);
    setCopied(true);
    toast.success('Recovery phrase copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadMnemonic = () => {
    const blob = new Blob([`Seamount Wallet Recovery Phrase\n\nWallet Address: ${walletAddress}\n\nRecovery Phrase:\n${mnemonic}\n\nâš ï¸ KEEP THIS SAFE! Never share with anyone.`], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'seamount-recovery-phrase.txt';
    a.click();
    toast.success('Recovery phrase downloaded!');
  };

  const verifyWords = () => {
    const allCorrect = verificationWords.every(pos => 
      userInputs[pos]?.toLowerCase().trim() === words[pos].toLowerCase()
    );
    
    if (allCorrect) {
      toast.success('Verification successful!');
      onComplete();
    } else {
      toast.error('Incorrect words. Please check and try again.');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl max-w-2xl w-full p-8 border border-blue-500/30 shadow-2xl">
        {step === 1 && (
          <>
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertTriangle className="h-8 w-8 text-red-400" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">Secure Your Wallet</h2>
              <p className="text-gray-400">Your recovery phrase is the ONLY way to restore your wallet</p>
            </div>

            <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 mb-6">
              <h3 className="text-red-400 font-semibold mb-2 flex items-center">
                <Lock className="h-4 w-4 mr-2" />
                Critical Security Warning
              </h3>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>â€¢ Never share your recovery phrase with anyone</li>
                <li>â€¢ Seamount will NEVER ask for your phrase</li>
                <li>â€¢ Store it offline in multiple secure locations</li>
                <li>â€¢ Anyone with this phrase can access your funds</li>
              </ul>
            </div>

            <button 
              onClick={() => setStep(2)} 
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 px-6 rounded-xl transition-all"
            >
              I Understand - Show Recovery Phrase
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <div className="text-center mb-6">
              <Shield className="h-12 w-12 text-blue-400 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-white mb-2">Your Recovery Phrase</h2>
              <p className="text-gray-400">Write these 25 words down in order</p>
            </div>

            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-gray-400">Recovery Phrase</span>
                <button
                  onClick={() => setShowMnemonic(!showMnemonic)}
                  className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1"
                >
                  {showMnemonic ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  {showMnemonic ? 'Hide' : 'Show'}
                </button>
              </div>

              <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                {showMnemonic ? (
                  <div className="grid grid-cols-3 gap-2">
                    {words.map((word, index) => (
                      <div key={index} className="bg-gray-700/50 rounded px-3 py-2 text-sm">
                        <span className="text-gray-400 mr-2">{index + 1}.</span>
                        <span className="text-white font-mono">{word}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    Click "Show" to reveal your recovery phrase
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-3 mb-4">
              <button 
                onClick={copyToClipboard}
                className="flex-1 flex items-center justify-center gap-2 border border-gray-700 text-gray-300 py-3 px-4 rounded-lg hover:bg-gray-800 transition-colors"
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? 'Copied!' : 'Copy Phrase'}
              </button>
              <button 
                onClick={downloadMnemonic}
                className="flex-1 flex items-center justify-center gap-2 border border-gray-700 text-gray-300 py-3 px-4 rounded-lg hover:bg-gray-800 transition-colors"
              >
                <Download className="h-4 w-4" />
                Download
              </button>
            </div>

            <button 
              onClick={() => setStep(3)}
              disabled={!showMnemonic}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 px-6 rounded-xl transition-all disabled:opacity-50"
            >
              I've Saved My Recovery Phrase
            </button>
          </>
        )}

        {step === 3 && (
          <>
            <div className="text-center mb-6">
              <Check className="h-12 w-12 text-green-400 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-white mb-2">Verify Your Phrase</h2>
              <p className="text-gray-400">Enter the requested words to confirm</p>
            </div>

            <div className="space-y-4 mb-6">
              {verificationWords.map(pos => (
                <div key={pos}>
                  <label className="block text-sm text-gray-400 mb-2">
                    Word #{pos + 1}
                  </label>
                  <input
                    type="text"
                    value={userInputs[pos] || ''}
                    onChange={(e) => setUserInputs({ ...userInputs, [pos]: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none"
                    placeholder="Enter word"
                  />
                </div>
              ))}
            </div>

            <div className="flex gap-3">
              <button 
                onClick={() => setStep(2)}
                className="flex-1 border border-gray-700 text-gray-300 py-3 px-4 rounded-lg hover:bg-gray-800 transition-colors"
              >
                Back
              </button>
              <button 
                onClick={verifyWords}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors"
              >
                Verify & Complete
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// Wallet Address Display
const WalletAddressCard = ({ address }: { address: string }) => {
  const [copied, setCopied] = useState(false);

  const copyAddress = () => {
    navigator.clipboard.writeText(address);
    setCopied(true);
    toast.success('Address copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-2xl p-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="text-sm text-gray-400 mb-1">Your Algorand Address</div>
          <div className="text-white font-mono text-sm break-all">{address}</div>
        </div>
        <div className="flex gap-2 ml-4">
          <button
            onClick={copyAddress}
            className={`p-2 rounded-lg transition-colors ${
              copied 
                ? 'bg-green-600 text-white' 
                : 'bg-gray-800 hover:bg-gray-700 text-gray-400'
            }`}
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </button>
          
            href={`https://algoexplorer.io/address/${address}`}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 transition-colors"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      </div>
    </div>
  );
};

// Main Dashboard Component
const DashboardPage = () => {
  const { userProfile, refreshProfile } = useAuth();
  const [loading, setLoading] = useState(true);
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [showMnemonicModal, setShowMnemonicModal] = useState(false);
  const [pendingMnemonic, setPendingMnemonic] = useState<string | null>(null);
  const [walletAddress, setWalletAddress] = useState<string>('');

  // Define supported assets
  const SUPPORTED_ASSETS = [
    { symbol: 'ALGO', name: 'Algorand', decimals: 6 },
    { symbol: 'USDT', name: 'Tether', decimals: 6 },
    { symbol: 'USDCa', name: 'USD Coin', decimals: 6 },
    { symbol: 'goBTC', name: 'goBTC', decimals: 8 },
    { symbol: 'goETH', name: 'goETH', decimals: 8 }
  ];

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      const response = await portfolioAPI.getPortfolio();
      
      if (response.data.success) {
        setPortfolioData(response.data);
        setWalletAddress(response.data.wallet_address || '');
        
        // Check for new wallet with mnemonic
        if (response.data.mnemonic && !localStorage.getItem('mnemonic_backed_up')) {
          setPendingMnemonic(response.data.mnemonic);
          setShowMnemonicModal(true);
        }
      }
    } catch (error: any) {
      console.error('Portfolio fetch error:', error);
      
      // If no wallet exists, create one
      if (error.response?.status === 404) {
        await createWallet();
      } else {
        toast.error('Failed to load portfolio');
      }
    } finally {
      setLoading(false);
    }
  };

  const createWallet = async () => {
    try {
      const response = await userAPI.provisionWallets();
      
      if (response.data.success && response.data.mnemonic) {
        setPendingMnemonic(response.data.mnemonic);
        setWalletAddress(response.data.wallet_address);
        setShowMnemonicModal(true);
        await fetchPortfolioData();
      }
    } catch (error) {
      console.error('Wallet creation error:', error);
      toast.error('Failed to create wallet');
    }
  };

  const handleMnemonicBackupComplete = () => {
    localStorage.setItem('mnemonic_backed_up', 'true');
    setShowMnemonicModal(false);
    setPendingMnemonic(null);
    toast.success('Wallet secured successfully!');
  };

  const handleBuyAsset = (asset: any) => {
    toast('Buy feature coming soon!', { icon: '🔜' });
    // TODO: Navigate to buy flow
  };

  const handleSendAsset = (asset: any) => {
    if (asset.balance <= 0) {
      toast.error('Insufficient balance');
      return;
    }
    toast('Send feature coming soon!', { icon: '🔜' });
    // TODO: Navigate to send flow
  };

  const handleStartKYC = () => {
    window.location.href = '/onboarding';
  };

  // Calculate portfolio metrics
  const totalBalance = portfolioData?.total_usd || 0;
  const assets = portfolioData?.balances || {};
  
  // Create asset array with pricing
  const assetCards = SUPPORTED_ASSETS.map(asset => {
    const balance = assets[asset.symbol] || 0;
    const price = portfolioData?.prices?.[asset.symbol] || 0;
    const value_usd = balance * price;
    
    return {
      ...asset,
      balance,
      price_usd: price,
      value_usd
    };
  });

  const kycStatus = userProfile?.kyc_status || 'not_started';
  const kycLevel = userProfile?.kyc_level || 0;

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading your portfolio...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Portfolio</h1>
          <p className="text-gray-400">Manage your multi-asset Algorand wallet</p>
        </div>

        {/* KYC Alert */}
        {kycStatus !== 'verified' && (
          <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-2xl p-6 mb-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <AlertTriangle className="h-6 w-6 text-yellow-400 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="text-yellow-400 font-semibold mb-1">Identity Verification Required</h3>
                  <p className="text-gray-300 text-sm mb-3">
                    Complete KYC to unlock full platform features and higher transaction limits
                  </p>
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <Shield className="h-3 w-3" />
                      Current Tier: {kycLevel}/3
                    </span>
                    <span>•</span>
                    <span>Status: {kycStatus.replace('_', ' ')}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={handleStartKYC}
                className="bg-yellow-600 hover:bg-yellow-700 text-white px-6 py-2 rounded-lg font-medium transition-colors whitespace-nowrap"
              >
                Start Verification
              </button>
            </div>
          </div>
        )}

        {/* Wallet Address */}
        {walletAddress && (
          <div className="mb-6">
            <WalletAddressCard address={walletAddress} />
          </div>
        )}

        {/* Portfolio Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2 bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-sm text-gray-400 mb-1">Total Balance</div>
                <div className="text-4xl font-bold text-white">${totalBalance.toFixed(2)}</div>
              </div>
              <button
                onClick={fetchPortfolioData}
                className="p-3 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-400 transition-colors"
              >
                <RefreshCw className="h-5 w-5" />
              </button>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Activity className="h-4 w-4 text-green-400" />
              <span className="text-green-400">Live on Algorand Network</span>
            </div>
          </div>

          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6">
            <div className="text-sm text-gray-400 mb-2">Network</div>
            <div className="text-2xl font-bold text-white mb-4">Algorand</div>
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              Sub-5s Settlement
            </div>
          </div>
        </div>

        {/* Asset Cards Grid */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-white">Your Assets</h2>
            <span className="text-sm text-gray-400">{SUPPORTED_ASSETS.length} supported</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {assetCards.map(asset => (
              <AssetCard
                key={asset.symbol}
                asset={asset}
                onBuy={() => handleBuyAsset(asset)}
                onSend={() => handleSendAsset(asset)}
              />
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6">
          <h3 className="text-lg font-bold text-white mb-4">Quick Actions</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button className="flex flex-col items-center gap-2 p-4 rounded-xl bg-gray-800 hover:bg-gray-700 transition-colors">
              <ArrowDownLeft className="h-6 w-6 text-blue-400" />
              <span className="text-sm text-gray-300">Buy</span>
            </button>
            <button className="flex flex-col items-center gap-2 p-4 rounded-xl bg-gray-800 hover:bg-gray-700 transition-colors">
              <ArrowUpRight className="h-6 w-6 text-purple-400" />
              <span className="text-sm text-gray-300">Send</span>
            </button>
            <button className="flex flex-col items-center gap-2 p-4 rounded-xl bg-gray-800 hover:bg-gray-700 transition-colors">
              <RefreshCw className="h-6 w-6 text-green-400" />
              <span className="text-sm text-gray-300">Swap</span>
            </button>
            <button className="flex flex-col items-center gap-2 p-4 rounded-xl bg-gray-800 hover:bg-gray-700 transition-colors">
              <TrendingUp className="h-6 w-6 text-yellow-400" />
              <span className="text-sm text-gray-300">Earn</span>
            </button>
          </div>
        </div>

        {/* Platform Features Banner */}
        <div className="mt-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold mb-2">Cross-Border Payments</h3>
              <p className="text-blue-100 text-sm mb-3">
                Send money globally at 2.9% fee vs 7% traditional (2.4% savings!)
              </p>
              <div className="flex items-center gap-4 text-xs">
                <span className="flex items-center gap-1">
                  <Activity className="h-3 w-3" />
                  Sub-5s settlement
                </span>
                <span className="flex items-center gap-1">
                  <Shield className="h-3 w-3" />
                  Bank-grade security
                </span>
              </div>
            </div>
            <button className="bg-white text-blue-600 px-6 py-3 rounded-xl font-semibold hover:bg-blue-50 transition-colors whitespace-nowrap">
              Send Money
            </button>
          </div>
        </div>
      </div>

      {/* Mnemonic Backup Modal */}
      {showMnemonicModal && pendingMnemonic && (
        <MnemonicBackupModal
          mnemonic={pendingMnemonic}
          walletAddress={walletAddress}
          onComplete={handleMnemonicBackupComplete}
        />
      )}
    </div>
  );
};

export default DashboardPage;