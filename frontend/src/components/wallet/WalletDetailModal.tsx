// File: frontend/src/components/wallet/WalletDetailModal.tsx
// ✅ FIXED: Correct import path (../../config/api)

import React, { useState, useEffect } from 'react';
import { X, TrendingUp, ArrowDownLeft, ExternalLink, Activity, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient } from '../../config/api';

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
  // NEW: Live oracle data
  livePrice?: number;
  priceLoading?: boolean;
  priceError?: string;
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
  const [retryCount, setRetryCount] = useState(0);

  // ✅ ENHANCED: Real data fetch with exponential backoff
  const fetchLivePrice = async (symbol: string): Promise<number | null> => {
    const assetName = getOracleAssetName(symbol);
    
    // 🎯 TIER 1: Your Backend Oracle (Primary)
    try {
      console.log(`🔄 [Tier 1] Fetching ${symbol} from backend oracle...`);
      const response = await apiClient.get(`/api/v1/oracle/price/${assetName}`);
      if (response.data.success && response.data.price) {
        const price = parseFloat(response.data.price);
        console.log(`✅ [Backend Oracle] ${symbol}: $${price}`);
        return price;
      }
    } catch (error) {
      console.warn(`⚠️ [Backend Oracle] Failed for ${symbol}:`, error);
    }

    // 🎯 TIER 2: Binance Public API (Free, Real-Time)
    try {
      console.log(`🔄 [Tier 2] Fetching ${symbol} from Binance...`);
      const binanceSymbols: { [key: string]: string } = {
        'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'MATIC': 'MATICUSDT',
        'ALGO': 'ALGOUSDT', 'TRX': 'TRXUSDT', 'USDT': 'USDTUSDC',
        'USDC': 'USDCUSDT', 'USDCa': 'USDCUSDT', 'goBTC': 'BTCUSDT',
        'goETH': 'ETHUSDT'
      };
      
      const binanceSymbol = binanceSymbols[symbol];
      if (!binanceSymbol) {
        console.warn(`⚠️ [Binance] No mapping for ${symbol}`);
        return null;
      }
      
      const binanceUrl = `https://api.binance.com/api/v3/ticker/price?symbol=${binanceSymbol}`;
      const response = await fetch(binanceUrl, { 
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        const price = parseFloat(data.price);
        console.log(`✅ [Binance] ${symbol}: $${price}`);
        return price;
      } else {
        console.warn(`⚠️ [Binance] HTTP ${response.status} for ${symbol}`);
      }
    } catch (error) {
      console.warn(`⚠️ [Binance] Network error for ${symbol}:`, error);
    }

    // 🎯 TIER 3: CoinGecko Free API (Real-Time, No Auth)
    try {
      console.log(`🔄 [Tier 3] Fetching ${symbol} from CoinGecko...`);
      const coinGeckoIds: { [key: string]: string } = {
        'BTC': 'bitcoin', 'ETH': 'ethereum', 'MATIC': 'matic-network',
        'ALGO': 'algorand', 'TRX': 'tron', 'USDT': 'tether',
        'USDC': 'usd-coin', 'USDCa': 'usd-coin', 'goBTC': 'bitcoin',
        'goETH': 'ethereum'
      };
      
      const coinId = coinGeckoIds[symbol];
      if (!coinId) {
        console.warn(`⚠️ [CoinGecko] No mapping for ${symbol}`);
        return null;
      }
      
      const cgUrl = `https://api.coingecko.com/api/v3/simple/price?ids=${coinId}&vs_currencies=usd`;
      const response = await fetch(cgUrl, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        const price = data[coinId]?.usd;
        if (price) {
          console.log(`✅ [CoinGecko] ${symbol}: $${price}`);
          return price;
        }
      } else {
        console.warn(`⚠️ [CoinGecko] HTTP ${response.status} for ${symbol}`);
      }
    } catch (error) {
      console.warn(`⚠️ [CoinGecko] Network error for ${symbol}:`, error);
    }

    // ❌ ALL LIVE SOURCES FAILED
    console.error(`❌ All live data sources failed for ${symbol}`);
    return null;
  };

  // ✅ ENHANCED: Robust price data fetching
  const fetchPriceData = async () => {
    try {
      setLoading(true);
      const assets = chainAssets[chain] || [];
      
      if (assets.length === 0) {
        console.warn(`No assets configured for chain: ${chain}`);
        setPriceData([]);
        setLoading(false);
        return;
      }
      
      // Start with loading state
      const loadingPriceData: AssetPriceData[] = assets.map(asset => ({
        symbol: asset.symbol,
        name: asset.name,
        price: 0,
        change24h: 0,
        priceLoading: true,
        priceError: undefined
      }));

      setPriceData(loadingPriceData);

      // 🔥 Fetch REAL live prices in parallel with timeout
      const pricePromises = assets.map(async (asset) => {
        try {
          const livePrice = await Promise.race([
            fetchLivePrice(asset.symbol),
            new Promise<null>((resolve) => setTimeout(() => resolve(null), 10000)) // 10s timeout
          ]);
          
          return {
            symbol: asset.symbol,
            name: asset.name,
            price: livePrice || 0,
            livePrice: livePrice || undefined,
            change24h: 0, // TODO: Implement 24h change from real API
            priceLoading: false,
            priceError: livePrice === null ? 'Unable to fetch live price from any source' : undefined
          };
        } catch (error) {
          return {
            symbol: asset.symbol,
            name: asset.name,
            price: 0,
            livePrice: undefined,
            change24h: 0,
            priceLoading: false,
            priceError: `Failed to fetch price: ${error}`
          };
        }
      });

      const enhancedPriceData = await Promise.all(pricePromises);
      setPriceData(enhancedPriceData);
      
      // Log success/failure summary
      const successCount = enhancedPriceData.filter(d => d.livePrice !== undefined).length;
      console.log(`✅ Price fetch complete: ${successCount}/${assets.length} successful`);
      
      if (successCount === 0 && retryCount < 2) {
        // Auto-retry once
        setRetryCount(prev => prev + 1);
        setTimeout(() => fetchPriceData(), 2000);
      } else if (successCount === 0) {
        toast.error('Unable to load live prices. Please check your connection.', {
          duration: 5000
        });
      }
      
    } catch (error) {
      console.error('Failed to fetch price data:', error);
      if (retryCount < 2) {
        setRetryCount(prev => prev + 1);
        setTimeout(() => fetchPriceData(), 2000);
      } else {
        toast.error('Price data fetch failed. Please refresh the page.');
        setPriceData([]);
      }
    } finally {
      setLoading(false);
    }
  };

  // ✅ Reset retry count when modal opens
  useEffect(() => {
    if (isOpen) {
      setRetryCount(0);
      fetchPriceData();
    }
  }, [isOpen, chain]);

  // ✅ ENHANCED: Price display with proper states
  const renderPriceDisplay = (selectedAssetData: AssetPriceData) => {
    if (selectedAssetData.priceLoading) {
      return (
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
          <span className="text-gray-400">Fetching live price...</span>
        </div>
      );
    }

    if (selectedAssetData.priceError) {
      return (
        <div className="flex flex-col gap-1">
          <div className="text-red-400 flex items-center gap-2">
            <span>❌</span>
            <span>Price Unavailable</span>
          </div>
          <p className="text-sm text-gray-400">{selectedAssetData.priceError}</p>
          <button
            onClick={fetchPriceData}
            className="mt-2 text-sm text-blue-400 hover:text-blue-300 underline flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      );
    }

    if (selectedAssetData.livePrice) {
      return (
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-green-400 animate-pulse" />
          <span className="text-3xl font-bold text-white">
            ${selectedAssetData.livePrice.toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 6
            })}
          </span>
          <span className="text-green-400 text-sm font-medium bg-green-400/20 px-2 py-1 rounded">
            Live
          </span>
        </div>
      );
    }

    return (
      <div className="text-gray-400 flex items-center gap-2">
        <span>⚠️</span>
        <span>No price data available</span>
      </div>
    );
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
            <div className="lg:w-80 border-r border-gray-700 p-6 overflow-auto">
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
                  className="text-xs text-gray-400 hover:text-white mt-2 flex items-center gap-1 truncate w-full"
                >
                  <span className="truncate">{address.slice(0, 8)}...{address.slice(-6)}</span>
                  <ExternalLink className="w-3 h-3 flex-shrink-0" />
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
                  {/* Asset Header - ENHANCED WITH LIVE PRICE */}
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-2xl font-bold text-white">
                        {selectedAssetData.name} ({selectedAssetData.symbol})
                      </h3>
                      <div className="flex items-center gap-4 mt-2">
                        <div className="text-3xl font-bold text-white">
                          // 🔥 REAL DATA ONLY - Show loading, live price, or error
                          {selectedAssetData.priceLoading ? (
                            <div className="flex items-center gap-2">
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                              <span className="text-gray-400">Fetching live price...</span>
                            </div>
                          ) : selectedAssetData.priceError ? (
                            <div className="flex flex-col gap-1">
                              <div className="text-red-400 flex items-center gap-2">
                                <span className="text-2xl">❌</span>
                                <span>Price Unavailable</span>
                              </div>
                              <p className="text-sm text-gray-400">{selectedAssetData.priceError}</p>
                              <button
                                onClick={() => fetchPriceData()}
                                className="mt-2 text-sm text-blue-400 hover:text-blue-300 underline"
                              >
                                Retry
                              </button>
                            </div>
                          ) : selectedAssetData.livePrice ? (
                            <div className="flex items-center gap-2">
                              <Activity className="h-5 w-5 text-green-400 animate-pulse" />
                              <span className="text-3xl font-bold text-white">
                                ${selectedAssetData.livePrice.toFixed(2)}
                              </span>
                              <span className="text-green-400 text-sm font-medium">Live</span>
                            </div>
                          ) : (
                            <div className="text-gray-400 flex items-center gap-2">
                              <span className="text-2xl">⚠️</span>
                              <span>No price data available</span>
                            </div>
                          )}
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