import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Activity, Send, RefreshCw, Shield, AlertTriangle, Bitcoin, Coins } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import AdvancedChart from '../components/charts/AdvancedChart';
import { CardSkeleton } from '../components/ui/LoadingSkeleton';
import { generateMockChartData } from '../data/mockData';
import { useAuth } from '../contexts/AuthContext';
import VerificationModal from '../components/VerificationModal';
import toast from 'react-hot-toast';
import { portfolioAPI, tradingAPI, userAPI } from '../config/api';

// Asset Icons Component
const AssetIcon = ({ asset }: { asset: string }) => {
  const iconClass = "h-6 w-6";
  switch (asset) {
    case 'goBTC':
      return <Bitcoin className={`${iconClass} text-orange-500`} />;
    case 'goETH':
	  return <Coins className={`${iconClass} text-blue-400`} />;
    case 'USDT':
    case 'USDCa':
      return <DollarSign className={`${iconClass} text-green-500`} />;
    case 'ALGO':
      return <Shield className={`${iconClass} text-purple-500`} />;
    default:
      return <DollarSign className={`${iconClass} text-gray-500`} />;
  }
};

// Multi-Asset Portfolio Component
const AssetPortfolio = ({ assets }: { assets: any[] }) => {
  return (
    <Card>
      <h3 className="text-lg font-semibold text-white mb-4">Your Portfolio</h3>
      <div className="space-y-3">
        {assets.length > 0 ? (
          assets.map((asset) => (
            <div key={asset.symbol} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
              <div className="flex items-center space-x-3">
                <AssetIcon asset={asset.symbol} />
                <div>
                  <div className="text-white font-medium">{asset.name}</div>
                  <div className="text-gray-400 text-sm">{asset.balance.toFixed(6)} {asset.symbol}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-white font-medium">${asset.value_usd.toFixed(2)}</div>
                <div className="text-gray-400 text-sm">${asset.price_usd.toFixed(2)}/unit</div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-8">
            <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-400">No assets yet. Start by buying your first digital asset.</p>
          </div>
        )}
      </div>
    </Card>
  );
};

// Asset Purchase Component
const BuyAssetForm = ({ onBuy, loading }: { 
  onBuy: (asset: string, amountUSD: number, paymentMethod: string) => void, 
  loading: boolean 
}) => {
  const [selectedAsset, setSelectedAsset] = useState('USDT');
  const [amountUSD, setAmountUSD] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('paystack');

  const supportedAssets = [
    { symbol: 'USDT', name: 'Tether USD', icon: 'ðŸ’µ' },
    { symbol: 'USDCa', name: 'USD Coin', icon: 'ðŸ’µ' },
    { symbol: 'goBTC', name: 'Wrapped Bitcoin', icon: 'â‚¿' },
    { symbol: 'goETH', name: 'Wrapped Ethereum', icon: 'Îž' },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onBuy(selectedAsset, parseFloat(amountUSD), paymentMethod);
  };

  return (
    <Card>
      <h3 className="text-lg font-semibold text-white mb-4">Buy Digital Assets</h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Select Asset</label>
          <select
            value={selectedAsset}
            onChange={(e) => setSelectedAsset(e.target.value)}
            className="w-full p-3 bg-gray-800 border border-gray-700 rounded-lg text-white"
          >
            {supportedAssets.map((asset) => (
              <option key={asset.symbol} value={asset.symbol}>
                {asset.icon} {asset.name} ({asset.symbol})
              </option>
            ))}
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Amount (USD)</label>
          <input
            type="number"
            value={amountUSD}
            onChange={(e) => setAmountUSD(e.target.value)}
            className="w-full p-3 bg-gray-800 border border-gray-700 rounded-lg text-white"
            placeholder="100.00"
            required
            min="10"
            step="0.01"
          />
          <div className="text-xs text-gray-400 mt-1">Minimum: $10 USD</div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Payment Method</label>
          <select
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            className="w-full p-3 bg-gray-800 border border-gray-700 rounded-lg text-white"
          >
            <option value="paystack">Paystack (Bank Transfer/Card)</option>
            <option value="quidax">Quidax (Nigerian Banks)</option>
          </select>
        </div>

        <div className="bg-blue-900/50 p-3 rounded-lg text-sm text-blue-200">
          <div className="flex justify-between">
            <span>Amount:</span>
            <span>${amountUSD || '0.00'}</span>
          </div>
          <div className="flex justify-between">
            <span>Network Fee (3%):</span>
            <span>${((parseFloat(amountUSD) || 0) * 0.03).toFixed(2)}</span>
          </div>
          <div className="flex justify-between font-medium border-t border-blue-800 mt-2 pt-2">
            <span>Total Cost:</span>
            <span>${((parseFloat(amountUSD) || 0) * 1.03).toFixed(2)}</span>
          </div>
        </div>
        
        <Button 
          type="submit" 
          loading={loading} 
          icon={DollarSign} 
          className="w-full bg-green-600 hover:bg-green-700"
        >
          Buy {selectedAsset}
        </Button>
      </form>
    </Card>
  );
};

const DashboardPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [chartData, setChartData] = useState(generateMockChartData(30));
  const [showVerificationModal, setShowVerificationModal] = useState(false);
  const [buyingAsset, setBuyingAsset] = useState(false);
  const [portfolio, setPortfolio] = useState<any>(null);
  const [walletAddress, setWalletAddress] = useState<string>('');
  
  const { user, role, refreshKycStatus } = useAuth();

  useEffect(() => {
    loadPortfolioData();
  }, []);

  const loadPortfolioData = async () => {
    try {
      setLoading(true);
      
      // Load portfolio data
      const portfolioResponse = await portfolioAPI.getSummary();
      setPortfolio(portfolioResponse.data);
      
      // Get wallet address if available
      try {
        const walletsResponse = await userAPI.provisionWallets();
        if (walletsResponse.data.wallet_address) {
          setWalletAddress(walletsResponse.data.wallet_address);
        }
      } catch (error) {
        console.warn('Wallet not provisioned yet');
      }
      
    } catch (error) {
      console.error('Failed to load portfolio:', error);
      toast.error('Failed to load portfolio data');
    } finally {
      setLoading(false);
    }
  };

  const completeVerification = async () => {
    try {
      window.location.href = '/onboarding';
    } catch (error) {
      console.error('Failed to redirect to verification:', error);
      toast.error('Failed to start verification process');
    }
  };

  const handleTransactionRequest = (action: () => void) => {
    if (user?.kyc_status !== 'approved') {
      setShowVerificationModal(true);
      return false;
    }
    return true;
  };

  const buyAsset = async (asset: string, amountUSD: number, paymentMethod: string) => {
    const canProceed = handleTransactionRequest(() => buyAsset(asset, amountUSD, paymentMethod));
    if (!canProceed) return;
    
    try {
      setBuyingAsset(true);
      const response = await tradingAPI.buy({
        asset,
        amount_usd: amountUSD,
        payment_method: paymentMethod
      });
      
      if (response.data.success) {
        // Redirect to payment provider
        window.open(response.data.checkout_url, '_blank');
        toast.success(`Redirecting to ${paymentMethod} for payment`);
      }
      
    } catch (error) {
      console.error('Asset purchase failed:', error);
      toast.error('Asset purchase failed. Please try again.');
    } finally {
      setBuyingAsset(false);
    }
  };

  const provisionWallet = async () => {
    try {
      const response = await userAPI.provisionWallets();
      if (response.data.success) {
        setWalletAddress(response.data.wallet_address);
        toast.success('Wallet created successfully!');
        if (response.data.mnemonic) {
          toast('Save your recovery phrase!', { icon: 'âš ï¸', duration: 5000 });
        }
      }
    } catch (error) {
      console.error('Wallet creation failed:', error);
      toast.error('Failed to create wallet');
    }
  };

  const formatCurrency = (amount: number) => 
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  const hasRestrictedAccess = user?.kyc_status === 'skipped' || user?.kyc_status === 'pending' || !user?.kyc_status;
  const canTrade = user?.kyc_status === 'approved';

  if (loading) {
    return <CardSkeleton count={4} />;
  }
  
  // Wallet creation prompt
  if (!walletAddress) {
    return (
      <Card className="text-center mt-10 max-w-lg mx-auto">
        <Shield className="mx-auto h-12 w-12 text-blue-500 mb-4" />
        <h2 className="text-2xl font-bold text-white mb-2">Create Your Algorand Wallet</h2>
        <p className="text-gray-400 mb-6">A secure wallet is required to hold and trade digital assets on Seamount.</p>
        <Button onClick={provisionWallet} loading={buyingAsset}>
          Create Secure Wallet
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Verification Notice */}
      {hasRestrictedAccess && (
        <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-6 rounded-md">
          <div className="flex items-start">
            <AlertTriangle className="h-6 w-6 mr-3 mt-0.5" />
            <div>
              <p className="font-bold">Verification Required</p>
              <p className="mt-1">Complete identity verification to unlock trading and full platform features.</p>
              <button 
                onClick={completeVerification}
                className="mt-2 bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600 transition-colors"
              >
                Complete Verification
              </button>
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-sm">Total Balance</span>
            <DollarSign className="h-5 w-5 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {formatCurrency(portfolio?.total_balance_usd || 0)}
          </div>
        </Card>
        
        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-sm">Assets</span>
            <Activity className="h-5 w-5 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {portfolio?.assets?.length || 0}
          </div>
        </Card>
        
        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-sm">24h Change</span>
            <TrendingUp className="h-5 w-5 text-green-400" />
          </div>
          <div className="text-2xl font-bold text-green-400">
            {portfolio?.change_24h >= 0 ? '+' : ''}{(portfolio?.change_24h || 0).toFixed(2)}%
          </div>
        </Card>
        
        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-sm">Status</span>
            <Shield className="h-5 w-5 text-blue-400" />
          </div>
          <div className="text-sm font-medium">
            {canTrade ? (
              <span className="text-green-400">Trading Active</span>
            ) : (
              <span className="text-yellow-400">KYC Required</span>
            )}
          </div>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Portfolio Overview */}
        <div className="lg:col-span-1">
          <AssetPortfolio assets={portfolio?.assets || []} />
        </div>
        
        {/* Buy Assets */}
        <div className="lg:col-span-1">
          {canTrade ? (
            <BuyAssetForm onBuy={buyAsset} loading={buyingAsset} />
          ) : (
            <Card className="text-center">
              <AlertTriangle className="mx-auto h-12 w-12 text-yellow-400 mb-4" />
              <h3 className="text-lg font-semibold text-white mb-2">Complete Verification</h3>
              <p className="text-gray-400 mb-4">Identity verification is required to trade digital assets.</p>
              <Button onClick={completeVerification} className="bg-blue-600 hover:bg-blue-700">
                Complete KYC
              </Button>
            </Card>
          )}
        </div>
      </div>

      {/* Chart Section */}
      <div className="mt-6">
        <Card>
          <h3 className="text-lg font-semibold text-white mb-4">Portfolio Performance</h3>
          <AdvancedChart 
            data={chartData} 
            height={300}
            showVolume={false}
            title="Portfolio Value (USD)"
          />
        </Card>
      </div>

      {/* Quick Actions */}
      {canTrade && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <Button 
            variant="outline" 
            icon={Send}
            onClick={() => toast('Send feature coming soon')}
          >
            Send Assets
          </Button>
          <Button 
            variant="outline" 
            icon={RefreshCw}
            onClick={loadPortfolioData}
          >
            Refresh Portfolio
          </Button>
          <Button 
            variant="outline" 
            icon={Activity}
            onClick={() => toast('Trading view coming soon')}
          >
            Advanced Trading
          </Button>
        </div>
      )}

      {/* Verification Modal */}
      {showVerificationModal && (
        <VerificationModal
          isOpen={showVerificationModal}
          onClose={() => setShowVerificationModal(false)}
          onComplete={completeVerification}
          userRole={role}
          message="Complete identity verification to unlock trading features"
        />
      )}
    </div>
  );
};

export default DashboardPage;
          