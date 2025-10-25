// File: frontend/src/components/wallet/WalletDetailModal.tsx
import React, { useState, useEffect } from 'react';
import { X, TrendingUp, ArrowDownLeft, ExternalLink } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient } from '../../../config/api';

interface WalletDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  chain: string;
  chainName: string;
  address: string;
  balance: number;
}

interface AssetPriceData {
  symbol: string;
  name: string;
  price: number;
  change24h: number;
  chartData?: number[];
}

const WalletDetailModal: React.FC<WalletDetailModalProps> = ({
  isOpen,
  onClose,
  chain,
  chainName,
  address,
  balance
}) => {
  const [selectedAsset, setSelectedAsset] = useState<string>('');
  const [priceData, setPriceData] = useState<AssetPriceData[]>([]);
  const [loading, setLoading] = useState(true);

  // Define assets for each chain
  const chainAssets: { [key: string]: Array<{ symbol: string; name: string }> } = {
    bitcoin: [
      { symbol: 'BTC', name: 'Bitcoin' }
    ],
    ethereum: [
      { symbol: 'ETH', name: 'Ethereum' },
      { symbol: 'USDT', name: 'Tether' },
      { symbol: 'USDC', name: 'USD Coin' }
    ],
    polygon: [
      { symbol: 'MATIC', name: 'Polygon' },
      { symbol: 'USDT', name: 'Tether' },
      { symbol: 'USDC', name: 'USD Coin' }
    ],
    algorand: [
      { symbol: 'ALGO', name: 'Algorand' },
      { symbol: 'USDCa', name: 'USD Coin' },
      { symbol: 'USDT', name: 'Tether' },
      { symbol: 'goBTC', name: 'Wrapped Bitcoin' },
      { symbol: 'goETH', name: 'Wrapped Ethereum' }
    ]
  };

  useEffect(() => {
    if (isOpen) {
      fetchPriceData();
    }
  }, [isOpen, chain]);

  useEffect(() => {
    if (priceData.length > 0 && !selectedAsset) {
      setSelectedAsset(priceData[0].symbol);
    }
  }, [priceData, selectedAsset]);

  const fetchPriceData = async () => {
    try {
      setLoading(true);
      const assets = chainAssets[chain] || [];
      
      // Mock data for demonstration
      const mockPriceData: AssetPriceData[] = assets.map(asset => ({
        symbol: asset.symbol,
        name: asset.name,
        price: Math.random() * 1000 + 10,
        change24h: (Math.random() - 0.5) * 10,
        chartData: Array.from({ length: 24 }, () => Math.random() * 100 + 50)
      }));

      setPriceData(mockPriceData);
    } catch (error) {
      console.error('Failed to fetch price data:', error);
      toast.error('Failed to load price data');
    } finally {
      setLoading(false);
    }
  };

  const handleBuyAsset = async () => {
    try {
      const response = await apiClient.post('/api/v1/payments/on-ramp/ngn', {
        user_id: 'current-user-id',
        user_email: 'user@example.com',
        amount_fiat: 10000,
        currency: "NGN",
        asset: selectedAsset
      });
      
      if (response.data.payment_url) {
        window.location.href = response.data.payment_url;
      } else {
        toast.error('Payment initialization failed');
      }
    } catch (error) {
      console.error('Buy asset error:', error);
      toast.error('Failed to initiate purchase');
    }
  };

  const getExplorerUrl = (chain: string, address: string) => {
    const explorers: { [key: string]: string } = {
      bitcoin: `https://blockstream.info/address/${address}`,
      ethereum: `https://etherscan.io/address/${address}`,
      polygon: `https://polygonscan.com/address/${address}`,
      algorand: `https://lora.algokit.io/explorer/address/${address}`
    };
    return explorers[chain] || '#';
  };

  const selectedAssetData = priceData.find(asset => asset.symbol === selectedAsset);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden border border-blue-500/30 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-white">{chainName} Wallet</h2>
            <p className="text-gray-400 text-sm">Live asset performance and trading</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="flex flex-col lg:flex-row h-[calc(90vh-120px)]">
          {/* Sidebar - Asset Selection */}
          <div className="lg:w-80 border-r border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Assets</h3>
            <div className="space-y-2">
              {chainAssets[chain]?.map(asset => (
                <button
                  key={asset.symbol}
                  onClick={() => setSelectedAsset(asset.symbol)}
                  className={`w-full text-left p-3 rounded-lg transition-all ${
                    selectedAsset === asset.symbol
                      ? 'bg-blue-600 text-white shadow-lg'
                      : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
                  }`}
                >
                  <div className="font-medium">{asset.symbol}</div>
                  <div className="text-sm opacity-75">{asset.name}</div>
                </button>
              ))}
            </div>

            {/* Wallet Info */}
            <div className="mt-6 p-4 bg-gray-800 rounded-lg">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Wallet Balance</h4>
              <div className="text-2xl font-bold text-white">${balance.toFixed(2)}</div>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(address);
                  toast.success('Address copied!');
                }}
                className="text-xs text-gray-400 hover:text-white mt-2 flex items-center gap-1"
              >
                {address.slice(0, 8)}...{address.slice(-6)}
                <ExternalLink className="w-3 h-3" />
              </button>
            </div>
          </div>

          {/* Main Content - Chart and Buy Section */}
          <div className="flex-1 p-6 overflow-auto">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : selectedAssetData ? (
              <>
                {/* Asset Header */}
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-2xl font-bold text-white">
                      {selectedAssetData.name} ({selectedAssetData.symbol})
                    </h3>
                    <div className="flex items-center gap-4 mt-2">
                      <div className="text-3xl font-bold text-white">
                        ${selectedAssetData.price.toFixed(2)}
                      </div>
                      <div className={`text-sm font-medium ${
                        selectedAssetData.change24h >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {selectedAssetData.change24h >= 0 ? '+' : ''}{selectedAssetData.change24h.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={handleBuyAsset}
                    className="flex items-center gap-2 bg-green-600 hover:bg-green-700 px-6 py-3 rounded-xl font-semibold text-white transition-all hover:shadow-lg hover:shadow-green-500/50"
                  >
                    <ArrowDownLeft className="w-5 h-5" />
                    Buy {selectedAssetData.symbol}
                  </button>
                </div>

                {/* Chart Placeholder */}
                <div className="bg-gray-800 rounded-xl p-6 mb-6 h-64 flex items-center justify-center">
                  <div className="text-center">
                    <TrendingUp className="w-12 h-12 text-blue-400 mx-auto mb-4" />
                    <h4 className="text-white font-semibold mb-2">Live Price Chart</h4>
                    <p className="text-gray-400 text-sm">
                      Real-time chart for {selectedAssetData.symbol} coming soon
                    </p>
                  </div>
                </div>

                {/* Additional Info */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-gray-800 rounded-xl p-4">
                    <div className="text-gray-400 text-sm mb-1">24h Volume</div>
                    <div className="text-white font-semibold">$1.2B</div>
                  </div>
                  <div className="bg-gray-800 rounded-xl p-4">
                    <div className="text-gray-400 text-sm mb-1">Market Cap</div>
                    <div className="text-white font-semibold">$45.8B</div>
                  </div>
                  <div className="bg-gray-800 rounded-xl p-4">
                    <div className="text-gray-400 text-sm mb-1">All-Time High</div>
                    <div className="text-white font-semibold">$3,250.00</div>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center text-gray-400 py-12">
                Select an asset to view details
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default WalletDetailModal;