import React, { useState, useEffect, useCallback } from 'react';
import { X, TrendingUp, ShoppingCart, Clock, Filter, Search, RefreshCw, Shield, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '@/components/layout/Sidebar';
import { apiClient } from '@/config/api';
import { useAuth } from '@/contexts/AuthContext';
import toast from 'react-hot-toast';
import { formatCurrencyUSD, formatCurrencyWithDecimals } from '@/utils/formatters';
import { FundWalletModal } from '@/components/wallet/FundWalletModal';

interface AssetOffer {
  id: string;
  seller_id: string;
  asset_id: string;
  quantity: number;
  price_per_unit: number;
  total_value: number;
  payment_network: string;
  status: string;
  expires_at: string;
  published_at: string;
  tokenized_assets?: {
    symbol: string;
    name: string;
    isin?: string;
    asset_type?: string;
    asset_id?: string;
    image_url?: string;
  };
}

interface MarketStats {
  totalOffers: number;
  totalValue: number;
  averagePrice: number;
  recentTrades: number;
}

const TradingPage = () => {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  
  const [offers, setOffers] = useState<AssetOffer[]>([]);
  const [filteredOffers, setFilteredOffers] = useState<AssetOffer[]>([]);
  const [selectedOffer, setSelectedOffer] = useState<AssetOffer | null>(null);
  const [userAlgoBalance, setUserAlgoBalance] = useState<number>(0);
  const [balanceLoading, setBalanceLoading] = useState(true);
  const [purchaseQuantity, setPurchaseQuantity] = useState<number>(1); // New state for quantity selection

  const [algoUsdPrice, setAlgoUsdPrice] = useState<number>(0.12);
  const [priceLoading, setPriceLoading] = useState(true);
  const [priceSource, setPriceSource] = useState<string>('');
  const [showBuyModal, setShowBuyModal] = useState(false);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [buyLoading, setBuyLoading] = useState(false);
  const [showFundModal, setShowFundModal] = useState(false);
  
  const [searchTerm, setSearchTerm] = useState('');
  const [filterNetwork, setFilterNetwork] = useState<string>('all');
  const [filterAssetType, setFilterAssetType] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'price_asc' | 'price_desc' | 'newest' | 'expiring'>('newest');
  
  const [marketStats, setMarketStats] = useState<MarketStats>({
    totalOffers: 0,
    totalValue: 0,
    averagePrice: 0,
    recentTrades: 0
  });

  // Helper function to get image URL
  const getImageUrl = (imageUrl: string | undefined) => {
    if (!imageUrl) return '';
    
    // If it's already a full URL, return it
    if (imageUrl.startsWith('http')) return imageUrl;
    
    // If it's just a filename, construct the full URL
    const supabaseUrl = 'https://opqnoficlhbylxfpaehp.supabase.co';
    return `${supabaseUrl}/storage/v1/object/public/asset-images/${imageUrl}`;
  };

  useEffect(() => {
    if (!authLoading && !user) {
      toast.error('Please sign in to access the trading platform');
      navigate('/login');
    }
  }, [authLoading, user, navigate]);

  const fetchOffers = useCallback(async (isSilentRefresh = false) => {
    if (!isSilentRefresh) {
      setIsLoading(true);
    } else {
      setIsRefreshing(true);
    }

    try {
      const response = await apiClient.get('/api/v1/tokenization/offers', {
        params: { 
          status: 'published',
          cacheBust: Date.now()
        }
      });
      
      if (response.data.success) {
        const offersData = response.data.offers || [];
        setOffers(offersData);
        
        const stats = calculateMarketStats(offersData);
        setMarketStats(stats);
        
        if (!isSilentRefresh) {
          toast.success(`Loaded ${offersData.length} market offers`);
        }
      } else {
        throw new Error(response.data.message || 'Failed to load offers');
      }
    } catch (error: any) {
      console.error('Failed to fetch offers:', error);
      
      if (!isSilentRefresh) {
        toast.error(
          error.response?.data?.detail || 
          error.message || 
          'Failed to load market offers. Please try again.'
        );
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const fetchAlgoPrice = async () => {
      try {
        setPriceLoading(true);
        const response = await apiClient.get('/api/v1/market/algo-price');
        
        if (response.data.success) {
          setAlgoUsdPrice(response.data.price);
          setPriceSource(response.data.source);
        }
      } catch (error) {
        console.error('Failed to fetch ALGO price:', error);
        setAlgoUsdPrice(0.12);
        setPriceSource('fallback');
      } finally {
        setPriceLoading(false);
      }
    };
    
    fetchAlgoPrice();
    
    const interval = setInterval(fetchAlgoPrice, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const ALGO_PER_USD = 1 / algoUsdPrice;
  const MIN_BALANCE = 0.1;
  const TX_FEE = 0.002;
  
  // Calculate required ALGO based on selected quantity
  const requiredAlgo = selectedOffer && purchaseQuantity > 0 
    ? (selectedOffer.price_per_unit * purchaseQuantity * ALGO_PER_USD) + MIN_BALANCE + TX_FEE 
    : 0;
  const hasEnoughBalance = userAlgoBalance >= requiredAlgo;
  const shortageAlgo = Math.max(0, requiredAlgo - userAlgoBalance);
  const shortageUSD = shortageAlgo * algoUsdPrice;

  useEffect(() => {
    if (user && !authLoading) {
      fetchOffers();
      
      const refreshInterval = setInterval(() => {
        fetchOffers(true);
      }, 30000);
      
      return () => clearInterval(refreshInterval);
    }
  }, [user, authLoading, fetchOffers]);
  
  useEffect(() => {
    if (showBuyModal && selectedOffer) {
      fetchAlgoBalance();
      // Reset purchase quantity to 1 when modal opens
      setPurchaseQuantity(1);
    }
  }, [showBuyModal, selectedOffer]);

  const fetchAlgoBalance = async () => {
    try {
      setBalanceLoading(true);
      const response = await apiClient.get('/api/v1/wallet/balance/algorand');
      if (response.data.success) {
        setUserAlgoBalance(response.data.balance);
      }
    } catch (error) {
      console.error('Failed to fetch ALGO balance:', error);
      setUserAlgoBalance(0);
    } finally {
      setBalanceLoading(false);
    }
  };

  useEffect(() => {
    if (offers.length === 0) {
      setFilteredOffers([]);
      return;
    }

    let filtered = [...offers];

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(offer =>
        offer.tokenized_assets?.symbol?.toLowerCase().includes(term) ||
        offer.tokenized_assets?.name?.toLowerCase().includes(term) ||
        offer.tokenized_assets?.isin?.toLowerCase().includes(term)
      );
    }

    if (filterNetwork !== 'all') {
      filtered = filtered.filter(offer => offer.payment_network === filterNetwork);
    }

    if (filterAssetType !== 'all') {
      filtered = filtered.filter(offer => 
        offer.tokenized_assets?.asset_type === filterAssetType
      );
    }

    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'price_asc':
          return a.price_per_unit - b.price_per_unit;
        case 'price_desc':
          return b.price_per_unit - a.price_per_unit;
        case 'newest':
          return new Date(b.published_at).getTime() - new Date(a.published_at).getTime();
        case 'expiring':
          return new Date(a.expires_at).getTime() - new Date(b.expires_at).getTime();
        default:
          return 0;
      }
    });

    setFilteredOffers(filtered);
  }, [offers, searchTerm, filterNetwork, filterAssetType, sortBy]);

  const calculateMarketStats = (offersList: AssetOffer[]): MarketStats => {
    if (offersList.length === 0) {
      return { totalOffers: 0, totalValue: 0, averagePrice: 0, recentTrades: 0 };
    }

    const totalValue = offersList.reduce((sum, o) => sum + o.total_value, 0);
    const averagePrice = offersList.reduce((sum, o) => sum + o.price_per_unit, 0) / offersList.length;
    
    const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const recentTrades = offersList.filter(o => 
      new Date(o.published_at) > twentyFourHoursAgo
    ).length;

    return {
      totalOffers: offersList.length,
      totalValue,
      averagePrice,
      recentTrades
    };
  };

  const handleBuyClick = (offer: AssetOffer) => {
    if (!user) {
      toast.error('Please sign in to make a purchase');
      navigate('/login');
      return;
    }

    if (offer.seller_id === user.id) {
      toast.error(
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4" />
          <span>This is your own listing. Manage it from "My Assets".</span>
        </div>,
        { duration: 5000 }
      );
      return;
    }

    setSelectedOffer(offer);
    setPurchaseQuantity(1); // Reset to minimum
    setShowBuyModal(true);
  };

  const handleBuyConfirm = async () => {
    if (!selectedOffer || !user || purchaseQuantity <= 0) return;

    try {
      setBuyLoading(true);
      
      const response = await apiClient.post('/api/v1/tokenization/execute-trade', {
        offer_id: selectedOffer.id,
        payment_network: selectedOffer.payment_network,
        quantity: purchaseQuantity  // Send the selected quantity
      });

      if (response.data.success) {
        toast.success(
          <div className="flex flex-col gap-1">
            <div className="font-semibold">Trade Executed Successfully!</div>
            <div className="text-sm opacity-90">DVP settlement in progress...</div>
          </div>,
          { duration: 5000 }
        );
        
        // Update offers list
        if (purchaseQuantity === selectedOffer.quantity) {
          // Full purchase - remove the offer
          setOffers(prev => prev.filter(o => o.id !== selectedOffer.id));
        } else {
          // Partial purchase - update the offer quantity
          setOffers(prev => prev.map(o => {
            if (o.id === selectedOffer.id) {
              return {
                ...o,
                quantity: o.quantity - purchaseQuantity,
                total_value: o.price_per_unit * (o.quantity - purchaseQuantity)
              };
            }
            return o;
          }));
        }
        
        setShowBuyModal(false);
        setSelectedOffer(null);
        
        setTimeout(() => fetchOffers(true), 2000);
      } else {
        throw new Error(response.data.message || 'Trade failed');
      }
    } catch (error: any) {
      console.error('Trade execution failed:', error);
      
      let errorMessage = 'Failed to execute trade';
      let isSelfTrade = false;
      
      if (error.response?.data) {
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
          isSelfTrade = errorMessage.toLowerCase().includes('your own') || 
                       errorMessage.toLowerCase().includes('self-trade');
        } else if (error.response.data.detail?.message) {
          errorMessage = error.response.data.detail.message;
          isSelfTrade = errorMessage.toLowerCase().includes('your own') || 
                       error.response.data.detail?.code === 'SELF_TRADE_BLOCKED';
        } else if (error.response.data.message) {
          errorMessage = error.response.data.message;
        }
      }
      
      if (isSelfTrade) {
        toast.error(
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            <span>This is your own listing. You cannot purchase your own assets.</span>
          </div>,
          { duration: 5000 }
        );
        
        setOffers(prev => prev.filter(o => o.id !== selectedOffer.id));
      } else {
        toast.error(errorMessage, { duration: 5000 });
      }
    } finally {
      setBuyLoading(false);
    }
  };

  const getPaymentNetworkLabel = (network: string) => {
    const labels: Record<string, string> = {
      'usdc_circle': 'USDC (Circle)',
      'usdc_polygon': 'USDC (Polygon)',
      'usdt_erc20': 'USDT (ERC-20)',
      'native_algo': 'Algorand (Native)'
    };
    return labels[network] || network;
  };

  const getAssetTypeLabel = (assetType?: string) => {
    if (!assetType) return 'Other';
    
    const labels: Record<string, string> = {
      'equity': 'Equity',
      'bond': 'Bond',
      'etf': 'ETF',
      'commodity': 'Commodity',
      'real_estate': 'Real Estate'
    };
    return labels[assetType] || assetType;
  };

  const uniqueAssetTypes = Array.from(
    new Set(offers.map(o => o.tokenized_assets?.asset_type).filter(Boolean))
  );

  if (authLoading) {
    return (
      <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />

      <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-2 md:gap-3 mb-1">
                <TrendingUp className="h-6 w-6 md:h-8 md:w-8 text-blue-400" />
                <span>Secondary Market</span>
              </h1>
              <p className="text-sm md:text-base text-gray-400">
                Buy tokenized assets with atomic DVP settlement
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              <button
                onClick={() => fetchOffers(false)}
                disabled={isRefreshing}
                className="flex items-center gap-2 px-4 py-2 bg-gray-700/50 hover:bg-gray-700 rounded-lg text-white transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                <span className="hidden sm:inline">Refresh</span>
              </button>
              
              <button
                onClick={() => navigate('/my-assets')}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium transition-colors"
              >
                My Assets
              </button>
            </div>
          </div>

          {/* Market Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-gray-400 mb-1">Active Offers</div>
                  <div className="text-2xl md:text-3xl font-bold text-white">
                    {marketStats.totalOffers}
                  </div>
                </div>
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <TrendingUp className="h-6 w-6 text-blue-400" />
                </div>
              </div>
              <div className="text-xs text-blue-400 mt-2">
                {marketStats.recentTrades} new in 24h
              </div>
            </div>

            <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-gray-400 mb-1">Market Value</div>
                  <div className="text-2xl md:text-3xl font-bold text-white">
                    {formatCurrencyUSD(marketStats.totalValue)}
                  </div>
                </div>
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <ShoppingCart className="h-6 w-6 text-green-400" />
                </div>
              </div>
              <div className="text-xs text-green-400 mt-2">
                Average: {formatCurrencyWithDecimals(marketStats.averagePrice)}
              </div>
            </div>

            <div className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/30 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-gray-400 mb-1">Unique Assets</div>
                  <div className="text-2xl md:text-3xl font-bold text-white">
                    {new Set(offers.map(o => o.tokenized_assets?.symbol)).size}
                  </div>
                </div>
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <Shield className="h-6 w-6 text-purple-400" />
                </div>
              </div>
              <div className="text-xs text-purple-400 mt-2">
                Tokenized securities
              </div>
            </div>

            <div className="bg-gradient-to-br from-orange-900/20 to-amber-900/20 border border-orange-500/30 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-gray-400 mb-1">Avg. Settlement</div>
                  <div className="text-2xl md:text-3xl font-bold text-white">2-4m</div>
                </div>
                <div className="p-2 bg-orange-500/20 rounded-lg">
                  <Clock className="h-6 w-6 text-orange-400" />
                </div>
              </div>
              <div className="text-xs text-orange-400 mt-2">
                Instant DVP execution
              </div>
            </div>
          </div>

          {/* Search & Filter Bar */}
          <div className="bg-gray-800/30 border border-gray-700/50 rounded-xl p-4 mb-6">
            <div className="flex flex-col gap-4">
              {/* Top Row: Search and Basic Filters */}
              <div className="flex flex-col sm:flex-row gap-3">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search by symbol, name, or ISIN..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-gray-900/50 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <Filter className="h-5 w-5 text-gray-400" />
                  <select
                    value={filterNetwork}
                    onChange={(e) => setFilterNetwork(e.target.value)}
                    className="px-4 py-2.5 bg-gray-900/50 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors min-w-[180px]"
                  >
                    <option value="all">All Payment Networks</option>
                    {Array.from(new Set(offers.map(o => o.payment_network))).map(network => (
                      <option key={network} value={network}>
                        {getPaymentNetworkLabel(network)}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                  className="px-4 py-2.5 bg-gray-700/50 hover:bg-gray-700 rounded-lg text-white transition-colors whitespace-nowrap"
                >
                  {showAdvancedFilters ? 'Hide Filters' : 'More Filters'}
                </button>
              </div>

              {/* Advanced Filters (Collapsible) */}
              {showAdvancedFilters && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-4 border-t border-gray-700/50">
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">Asset Type</label>
                    <select
                      value={filterAssetType}
                      onChange={(e) => setFilterAssetType(e.target.value)}
                      className="w-full px-4 py-2.5 bg-gray-900/50 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
                    >
                      <option value="all">All Asset Types</option>
                      {uniqueAssetTypes.map(type => (
                        <option key={type} value={type}>
                          {getAssetTypeLabel(type)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm text-gray-400 mb-2">Sort By</label>
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as any)}
                      className="w-full px-4 py-2.5 bg-gray-900/50 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
                    >
                      <option value="newest">Newest First</option>
                      <option value="price_asc">Price: Low to High</option>
                      <option value="price_desc">Price: High to Low</option>
                      <option value="expiring">Expiring Soon</option>
                    </select>
                  </div>

                  <div className="flex items-end">
                    <button
                      onClick={() => {
                        setSearchTerm('');
                        setFilterNetwork('all');
                        setFilterAssetType('all');
                        setSortBy('newest');
                      }}
                      className="w-full px-4 py-2.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-white transition-colors"
                    >
                      Clear All Filters
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Results Info */}
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-gray-400">
              Showing <span className="text-white font-semibold">{filteredOffers.length}</span> of{' '}
              <span className="text-white font-semibold">{offers.length}</span> offers
              {searchTerm && ` for "${searchTerm}"`}
            </div>
            
            {isRefreshing && (
              <div className="flex items-center gap-2 text-sm text-blue-400">
                <RefreshCw className="h-3 w-3 animate-spin" />
                Updating market data...
              </div>
            )}
          </div>

          {/* Market Offers */}
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mb-4"></div>
              <div className="text-gray-400">Loading market offers...</div>
            </div>
          ) : filteredOffers.length === 0 ? (
            <div className="text-center py-12 bg-gray-800/20 rounded-xl border border-gray-700/50">
              <TrendingUp className="h-16 w-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-400 mb-2">
                {searchTerm || filterNetwork !== 'all' || filterAssetType !== 'all' 
                  ? 'No Matching Offers Found' 
                  : 'No Active Offers Available'}
              </h3>
              <p className="text-gray-500 max-w-md mx-auto mb-6">
                {searchTerm || filterNetwork !== 'all' || filterAssetType !== 'all'
                  ? 'Try adjusting your search or filter criteria'
                  : 'Check back later for new trading opportunities'}
              </p>
              {(searchTerm || filterNetwork !== 'all' || filterAssetType !== 'all') && (
                <button
                  onClick={() => {
                    setSearchTerm('');
                    setFilterNetwork('all');
                    setFilterAssetType('all');
                  }}
                  className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors"
                >
                  Clear Filters
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredOffers.map((offer) => {
                const isOwnListing = offer.seller_id === user.id;
                const expiresSoon = new Date(offer.expires_at).getTime() - Date.now() < 24 * 60 * 60 * 1000;
                
                return (
                  <div
                    key={offer.id}
                    className={`bg-gradient-to-br from-gray-800/50 to-gray-900/50 border rounded-xl p-4 transition-all relative overflow-hidden group hover:scale-[1.02] ${
                      isOwnListing 
                        ? 'border-purple-500/50 hover:border-purple-400/70' 
                        : 'border-gray-700/50 hover:border-blue-500/50'
                    }`}
                  >
                    {/* Asset Image Display */}
                    {offer.tokenized_assets?.image_url && (
                      <div className="mb-4 -mx-4 -mt-4">
                        <img 
                          src={getImageUrl(offer.tokenized_assets.image_url)} 
                          alt={offer.tokenized_assets.symbol || 'Asset'}
                          className="w-full h-48 object-cover rounded-t-xl"
                          onError={(e) => {
                            console.error('❌ Image failed to load:', {
                              original: offer.tokenized_assets?.image_url,
                              constructed: e.currentTarget.src,
                              offerId: offer.id,
                              asset: offer.tokenized_assets?.symbol
                            });
                          }}
                          onLoad={(e) => {
                            console.log('✅ Image loaded successfully:', e.currentTarget.src);
                          }}
                        />
                      </div>
                    )}

                    {/* Ribbon for own listings */}
                    {isOwnListing && (
                      <div className="absolute -top-2 -right-8 rotate-45 z-10">
                        <div className="bg-gradient-to-r from-purple-600 to-pink-600 text-white text-xs font-bold px-10 py-1 shadow-lg">
                          YOUR LISTING
                        </div>
                      </div>
                    )}

                    {/* Expiring Soon Badge */}
                    {expiresSoon && !isOwnListing && (
                      <div className="absolute top-2 right-2 z-10">
                        <div className="bg-gradient-to-r from-orange-500/90 to-red-500/90 text-white text-xs font-bold px-2 py-1 rounded-full">
                          Expiring Soon
                        </div>
                      </div>
                    )}

                    {/* Asset Info */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-lg font-bold text-white">
                            {offer.tokenized_assets?.symbol || 'Unknown'}
                          </h3>
                          {offer.tokenized_assets?.isin && (
                            <span className="text-xs text-gray-500 bg-gray-800/50 px-2 py-0.5 rounded">
                              {offer.tokenized_assets.isin}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-400 truncate mb-2">
                          {offer.tokenized_assets?.name || 'Tokenized Asset'}
                        </p>
                        
                        {/* Pera Explorer Link */}
                        {offer.tokenized_assets?.asset_id && (
                          <a
                            href={`https://explorer.perawallet.app/asset/${offer.tokenized_assets.asset_id}/`}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                          >
                            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                            View on Explorer (ASA {offer.tokenized_assets.asset_id})
                          </a>
                        )}
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        isOwnListing 
                          ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' 
                          : 'bg-green-500/20 text-green-400'
                      }`}>
                        {isOwnListing ? 'Your Offer' : 'Live'}
                      </span>
                    </div>

                    {/* Asset Type */}
                    {offer.tokenized_assets?.asset_type && (
                      <div className="mb-3">
                        <span className="text-xs text-gray-500 bg-gray-800/30 px-2 py-1 rounded">
                          {getAssetTypeLabel(offer.tokenized_assets.asset_type)}
                        </span>
                      </div>
                    )}

                    {/* Quantity & Price */}
                    <div className="space-y-3 mb-4">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-gray-800/30 rounded-lg p-3">
                          <div className="text-xs text-gray-400 mb-1">Available</div>
                          <div className="text-base font-bold text-white">{offer.quantity.toLocaleString()}</div>
                        </div>
                        <div className="bg-gray-800/30 rounded-lg p-3">
                          <div className="text-xs text-gray-400 mb-1">Price/Unit</div>
                          <div className="text-base font-bold text-white">{formatCurrencyWithDecimals(offer.price_per_unit)}</div>
                        </div>
                      </div>
                      
                      <div className="bg-blue-900/10 border border-blue-500/20 rounded-lg p-3">
                        <div className="text-xs text-gray-400 mb-1">Total Value</div>
                        <div className="text-xl font-bold text-blue-400">{formatCurrencyUSD(offer.total_value)}</div>
                      </div>
                    </div>

                    {/* Payment Network & Expiry */}
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <div className="text-xs text-gray-400 mb-1">Payment</div>
                        <div className="text-xs font-medium text-blue-400">
                          {getPaymentNetworkLabel(offer.payment_network)}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-gray-400 mb-1">Expires</div>
                        <div className={`text-xs font-medium ${expiresSoon ? 'text-orange-400' : 'text-gray-400'}`}>
                          {new Date(offer.expires_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>

                    {/* Buy Button */}
                    <button
                      onClick={() => handleBuyClick(offer)}
                      disabled={isOwnListing}
                      className={`w-full py-3 font-semibold rounded-lg transition-all flex items-center justify-center gap-2 ${
                        isOwnListing
                          ? 'bg-gradient-to-r from-purple-600/30 to-pink-600/30 text-purple-300 border border-purple-500/30 cursor-not-allowed'
                          : 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white shadow-lg hover:shadow-xl'
                      }`}
                    >
                      {isOwnListing ? (
                        <>
                          <Shield className="h-4 w-4" />
                          Your Listing
                        </>
                      ) : (
                        <>
                          <ShoppingCart className="h-4 w-4" />
                          Buy Now
                        </>
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Buy Confirmation Modal */}
      {showBuyModal && selectedOffer && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-white">Confirm Purchase</h3>
                <button
                  onClick={() => {
                    setShowBuyModal(false);
                    setSelectedOffer(null);
                  }}
                  className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                  disabled={buyLoading}
                >
                  <X className="h-5 w-5 text-gray-400" />
                </button>
              </div>
              
              {/* Asset Details */}
              <div className="space-y-4 mb-6">
                {/* Asset Image in Modal */}
                {selectedOffer.tokenized_assets?.image_url && (
                  <div className="bg-gray-800/50 rounded-xl overflow-hidden">
                    <img 
                      src={getImageUrl(selectedOffer.tokenized_assets.image_url)} 
                      alt={selectedOffer.tokenized_assets.symbol || 'Asset'}
                      className="w-full h-48 object-cover"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                      }}
                    />
                  </div>
                )}

                <div className="bg-gray-800/50 rounded-xl p-4">
                  <div className="text-sm text-gray-400 mb-1">Asset</div>
                  <div className="text-lg font-bold text-white">
                    {selectedOffer.tokenized_assets?.symbol} - {selectedOffer.tokenized_assets?.name}
                  </div>
                  {selectedOffer.tokenized_assets?.isin && (
                    <div className="text-xs text-gray-500 mt-1">
                      ISIN: {selectedOffer.tokenized_assets.isin}
                    </div>
                  )}
                  
                  {/* Blockchain Verification Link */}
                  {selectedOffer.tokenized_assets?.asset_id && (
                    <a
                      href={`https://explorer.perawallet.app/asset/${selectedOffer.tokenized_assets.asset_id}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 mt-2 transition-colors"
                    >
                      <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Verify on Blockchain (ASA {selectedOffer.tokenized_assets.asset_id})
                    </a>
                  )}
                </div>

                {/* Quantity Selection */}
                <div className="bg-gray-800/50 rounded-xl p-4">
                  <div className="text-sm text-gray-400 mb-2">Purchase Quantity</div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setPurchaseQuantity(Math.max(1, purchaseQuantity - 1))}
                      disabled={purchaseQuantity <= 1}
                      className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-white"
                    >
                      -
                    </button>
                    <input
                      type="number"
                      min="1"
                      max={selectedOffer.quantity}
                      value={purchaseQuantity}
                      onChange={(e) => {
                        const value = parseInt(e.target.value);
                        if (!isNaN(value) && value >= 1 && value <= selectedOffer.quantity) {
                          setPurchaseQuantity(value);
                        }
                      }}
                      className="flex-1 px-3 py-1 bg-gray-900 border border-gray-700 rounded text-white text-center"
                    />
                    <button
                      onClick={() => setPurchaseQuantity(Math.min(selectedOffer.quantity, purchaseQuantity + 1))}
                      disabled={purchaseQuantity >= selectedOffer.quantity}
                      className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-white"
                    >
                      +
                    </button>
                  </div>
                  <div className="text-xs text-gray-400 mt-2 text-center">
                    Available: {selectedOffer.quantity.toLocaleString()} units
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-800/50 rounded-xl p-4">
                    <div className="text-sm text-gray-400 mb-1">Price/Unit</div>
                    <div className="text-lg font-bold text-white">
                      {formatCurrencyWithDecimals(selectedOffer.price_per_unit)}
                    </div>
                  </div>
                  <div className="bg-gray-800/50 rounded-xl p-4">
                    <div className="text-sm text-gray-400 mb-1">Subtotal</div>
                    <div className="text-lg font-bold text-white">
                      {formatCurrencyUSD(selectedOffer.price_per_unit * purchaseQuantity)}
                    </div>
                  </div>
                </div>

                <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-4">
                  <div className="text-sm text-gray-400 mb-1">Total Cost</div>
                  <div className="text-2xl font-bold text-white">
                    {formatCurrencyUSD(selectedOffer.price_per_unit * purchaseQuantity)}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    Payment via {getPaymentNetworkLabel(selectedOffer.payment_network)}
                  </div>
                </div>

                {/* DVP Settlement Info */}
                <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Shield className="h-4 w-4 text-green-400" />
                    <div className="text-sm font-semibold text-green-400">DVP Settlement</div>
                  </div>
                  <div className="text-xs text-gray-400">
                    Delivery vs Payment ensures atomic settlement. Assets and payment are exchanged simultaneously.
                    Estimated completion: 2-4 minutes.
                  </div>
                </div>

                {/* Exchange Rate & Balance Check */}
                <div className="bg-gray-800/30 rounded-xl p-4">
                  {/* Exchange Rate Display */}
                  <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-700">
                    <span className="text-xs text-gray-400">Exchange Rate</span>
                    {priceLoading ? (
                      <span className="text-xs text-gray-400 animate-pulse">Fetching...</span>
                    ) : (
                      <div className="text-right">
                        <div className="text-sm font-medium text-white">
                          1 ALGO = ${algoUsdPrice.toFixed(4)} USD
                        </div>
                        <div className="text-xs text-gray-500">
                          Source: {priceSource} {priceSource !== 'fallback' && <span className="text-green-400">● Live</span>}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Balance Display */}
                  <div className="space-y-2 mb-3">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-400">Your ALGO Balance:</span>
                      <span className={`text-sm font-medium ${hasEnoughBalance ? 'text-green-400' : 'text-red-400'}`}>
                        {balanceLoading ? (
                          <span className="animate-pulse">Loading...</span>
                        ) : (
                          <>
                            {userAlgoBalance.toFixed(3)} ALGO
                            <span className="text-xs text-gray-500 ml-2">
                              (${(userAlgoBalance * algoUsdPrice).toFixed(2)})
                            </span>
                          </>
                        )}
                      </span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-400">Required ALGO:</span>
                      <span className="text-sm font-medium text-white">
                        {requiredAlgo.toFixed(3)} ALGO
                        <span className="text-xs text-gray-500 ml-2">
                          (${(requiredAlgo * algoUsdPrice).toFixed(2)})
                        </span>
                      </span>
                    </div>
                  </div>

                  {/* Shortage Warning */}
                  {!hasEnoughBalance && (
                    <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="h-4 w-4 text-red-400" />
                        <span className="text-sm font-semibold text-red-400">Insufficient Balance</span>
                      </div>
                      <div className="text-xs text-gray-400 mb-2">
                        You need {shortageAlgo.toFixed(3)} more ALGO (≈ ${shortageUSD.toFixed(2)} USD)
                      </div>
                      <button
                        onClick={() => {
                          setShowBuyModal(false);
                          setShowFundModal(true);
                        }}
                        className="w-full py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white text-xs font-medium rounded-lg transition-colors shadow-lg"
                      >
                        💳 Fund Wallet (Buy ALGO)
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowBuyModal(false);
                    setSelectedOffer(null);
                  }}
                  disabled={buyLoading}
                  className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBuyConfirm}
                  disabled={buyLoading || !hasEnoughBalance}
                  className="flex-1 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-semibold rounded-lg transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {buyLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Executing DVP...
                    </>
                  ) : !hasEnoughBalance ? (
                    <>
                      <AlertTriangle className="h-4 w-4" />
                      Insufficient ALGO
                    </>
                  ) : (
                    `Buy ${purchaseQuantity} Units`
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Fund Wallet Modal */}
      <FundWalletModal 
        open={showFundModal} 
        onOpenChange={setShowFundModal}
      />
    </div>
  );
};

export default TradingPage;