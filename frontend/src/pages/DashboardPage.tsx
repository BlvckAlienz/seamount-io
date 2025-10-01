// File: frontend/src/pages/DashboardPage.tsx
import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, TrendingDown, DollarSign, Activity, Send, 
  RefreshCw, Shield, AlertTriangle, Bitcoin, Coins, Copy, 
  Check, Eye, EyeOff, Download, Lock, ExternalLink 
} from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { CardSkeleton } from '../components/ui/LoadingSkeleton';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { portfolioAPI, userAPI } from '../config/api';

// Mnemonic Backup Modal Component
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
    // Generate 3 random word positions for verification
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
    const blob = new Blob([`Seamount Wallet Recovery Phrase\n\nWallet Address: ${walletAddress}\n\nRecovery Phrase:\n${mnemonic}\n\n⚠️ KEEP THIS SAFE! Never share with anyone.`], { type: 'text/plain' });
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
                <li>• Never share your recovery phrase with anyone</li>
                <li>• Seamount will NEVER ask for your phrase</li>
                <li>• Store it offline in multiple secure locations</li>
                <li>• Anyone with this phrase can access your funds</li>
              </ul>
            </div>

            <div className="flex gap-3">
              <Button 
                onClick={() => setStep(2)} 
                className="flex-1 bg-blue-600 hover:bg-blue-700"
              >
                I Understand - Show Recovery Phrase
              </Button>
            </div>
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
              <Button 
                onClick={copyToClipboard}
                variant="outline"
                icon={copied ? Check : Copy}
                className="flex-1"
              >
                {copied ? 'Copied!' : 'Copy Phrase'}
              </Button>
              <Button 
                onClick={downloadMnemonic}
                variant="outline"
                icon={Download}
                className="flex-1"
              >
                Download Backup
              </Button>
            </div>

            <Button 
              onClick={() => setStep(3)}
              className="w-full bg-blue-600 hover:bg-blue-700"
              disabled={!showMnemonic}
            >
              I've Saved My Recovery Phrase
            </Button>
          </>
        )}

        {step === 3 && (
          <>
            <div className="text-center mb-6">
              <Check className="h-12 w-12 text-green-400 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-white mb-2">Verify Your Phrase</h2>
              <p className="text-gray-400">Enter the requested words to confirm you saved it</p>
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
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white"
                    placeholder="Enter word"
                  />
                </div>
              ))}
            </div>

            <div className="flex gap-3">
              <Button 
                onClick={() => setStep(2)}
                variant="outline"
                className="flex-1"
              >
                Back
              </Button>
              <Button 
                onClick={verifyWords}
                className="flex-1 bg-green-600 hover:bg-green-700"
              >
                Verify & Complete
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// Asset Card Component
const AssetCard = ({ asset }: { asset: any }) => {
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

  return (
    <div className="group relative bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50 hover:border-blue-500/50 transition-all hover:shadow-xl hover:shadow-blue-500/10">
      <div className={`absolute inset-0 bg-gradient-to-br ${getGradient(asset.symbol)} opacity-0 group-hover:opacity-10 rounded-2xl transition-opacity`} />
      
      <div className="relative">
        <div className="flex items-start justify-between mb-4">
          <div className={`p-3 rounded-xl bg-gradient-to-br ${getGradient(asset.symbol)} text-white`}>
            {getIcon(asset.symbol)}
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-white">${asset.value_usd.toFixed(2)}</div>
            <div className="text-sm text-gray-400">≈ {asset.balance.toFixed(6)}</div>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-white font-semibold">{asset.name}</div>
            <div className="text-gray-400 text-sm">{asset.symbol}</div>
          </div>
          <div className="text-right">
            <div className="text-gray-400 text-sm">${asset.price_usd.toFixed(2)}</div>
          </div>
        </div>
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
    <Card className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border-blue-500/30">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="text-sm text-gray-400 mb-1">Your Algorand Address</div>
          <div className="text-white font-mono text-sm break-all">{address}</div>
        </div>
        <div className="flex gap-2 ml-4">
          <button
            onClick={copyAddress}
            className="p-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            {copied ? <Check className="h-4 w-4 text-white" /> : <Copy className="h-4 w-4 text-white" />}
          </button>
          <a
            href={`https://algoexplorer.io/address/${address}`}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            <ExternalLink className="h-4 w-4 text-white" />
          </a>
        </div>
      </div>
    </Card>
  );
};

const DashboardPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [portfolio, setPortfolio] = useState<any>(null);
  const [walletAddress, setWalletAddress] = useState<string>('');
  const [mnemonic, setMnemonic] = useState<string>('');
  const [showMnemonicModal, setShowMnemonicModal] = useState(false);
  
  const { user } = useAuth();

  useEffect(() => {
    loadPortfolioData();
  }, []);

  const loadPortfolioData = async () => {
    try {
      setLoading(true);
      const [portfolioResponse, walletResponse] = await Promise.allSettled([
        portfolioAPI.getSummary(),
        userAPI.provisionWallets()
      ]);

      if (portfolioResponse.status === 'fulfilled') {
        setPortfolio(portfolioResponse.value.data);
      }

      if (walletResponse.status === 'fulfilled' && walletResponse.value.data.wallet_address) {
        setWalletAddress(walletResponse.value.data.wallet_address);
        if (walletResponse.value.data.mnemonic) {
          setMnemonic(walletResponse.value.data.mnemonic);
          setShowMnemonicModal(true);
        }
      }
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const createWallet = async () => {
    try {
      const response = await userAPI.provisionWallets();
      if (response.data.success) {
        setWalletAddress(response.data.wallet_address);
        setMnemonic(response.data.mnemonic);
        setShowMnemonicModal(true);
      }
    } catch (error) {
      toast.error('Failed to create wallet');
    }
  };

  if (loading) return <CardSkeleton count={4} />;

  if (!walletAddress) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md text-center">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <Shield className="h-10 w-10 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-3">Create Your Wallet</h2>
          <p className="text-gray-400 mb-6">Get started with a secure Algorand wallet to hold and trade digital assets</p>
          <Button onClick={createWallet} className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700">
            Create Wallet
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Wallet Address */}
      <WalletAddressCard address={walletAddress} />

      {/* Portfolio Value Header */}
      <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 rounded-2xl p-8 border border-blue-500/30">
        <div className="text-sm text-gray-400 mb-2">Total Portfolio Value</div>
        <div className="text-5xl font-bold text-white mb-4">
          ${(portfolio?.total_balance_usd || 0).toFixed(2)}
        </div>
        <div className="flex items-center gap-2 text-green-400">
          <TrendingUp className="h-5 w-5" />
          <span>+{(portfolio?.change_24h || 0).toFixed(2)}% (24h)</span>
        </div>
      </div>

      {/* Assets Grid */}
      {portfolio?.assets?.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {portfolio.assets.map((asset: any) => (
            <AssetCard key={asset.symbol} asset={asset} />
          ))}
        </div>
      ) : (
        <Card className="text-center py-12">
          <Coins className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No Assets Yet</h3>
          <p className="text-gray-400 mb-6">Start building your portfolio by purchasing your first digital asset</p>
          <Button className="bg-blue-600 hover:bg-blue-700">
            Buy Crypto
          </Button>
        </Card>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Button variant="outline" icon={Send} className="py-4">
          Send
        </Button>
        <Button variant="outline" icon={RefreshCw} onClick={loadPortfolioData} className="py-4">
          Refresh
        </Button>
        <Button variant="outline" icon={Activity} className="py-4">
          Trade
        </Button>
      </div>

      {/* Mnemonic Backup Modal */}
      {showMnemonicModal && mnemonic && (
        <MnemonicBackupModal
          mnemonic={mnemonic}
          walletAddress={walletAddress}
          onComplete={() => setShowMnemonicModal(false)}
        />
      )}
    </div>
  );
};

export default DashboardPage;