// File: frontend/src/contexts/WalletContext.tsx
// Global wallet state management for multi-chain operations

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';
import { useAuth } from './AuthContext';

// ============================================================================
// TYPES
// ============================================================================

interface WalletBalance {
  balance: number;
  chain: string;
  usd_value: number;
}

interface MultiChainWallet {
  [chain: string]: {
    address: string;
    balance?: number;
  };
}

interface SendTransactionParams {
  recipient: string;
  asset: string;
  amount: number;
  chain?: string; // Optional: will auto-route if not provided
  memo?: string;
}

interface WalletContextValue {
  // State
  wallets: MultiChainWallet;
  balances: { [asset: string]: WalletBalance };
  totalBalanceUSD: number;
  loading: boolean;
  
  // Actions
  fetchWallets: () => Promise<void>;
  fetchBalances: () => Promise<void>;
  sendTransaction: (params: SendTransactionParams) => Promise<{ success: boolean; tx_id?: string; error?: string }>;
  refreshAll: () => Promise<void>;
}

const WalletContext = createContext<WalletContextValue | undefined>(undefined);

// ============================================================================
// PROVIDER
// ============================================================================

export const WalletProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [wallets, setWallets] = useState<MultiChainWallet>({});
  const [balances, setBalances] = useState<{ [asset: string]: WalletBalance }>({});
  const [totalBalanceUSD, setTotalBalanceUSD] = useState(0);
  const [loading, setLoading] = useState(false);

  // ============================================================================
  // FETCH WALLETS
  // ============================================================================
  const fetchWallets = useCallback(async () => {
    // âœ… CRITICAL: Only fetch if authenticated
    if (!user) {
      console.log('â„¹ï¸ WalletContext: User not authenticated, skipping wallet fetch');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await api.get<any>('/api/v1/wallet/multi-chain-status');
      
      if (response.success) {
        setWallets(response.wallets || {});
      }
    } catch (error: any) {
      // âœ… Handle 403 gracefully (expected when not authenticated)
      if (error?.response?.status === 403) {
        console.log('â„¹ï¸ Wallet fetch returned 403 (not authenticated)');
        setWallets({}); // Clear state, no error toast
      } else {
        // Real errors (500, network issues, etc.)
        console.error('Failed to fetch wallets:', error);
        toast.error('Failed to load wallets');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // ============================================================================
  // FETCH BALANCES
  // ===========================================================================

  const fetchBalances = useCallback(async () => {
    if (!user) {
      console.log('ℹ️ fetchBalances: No user, skipping');
      return;
    }

    setLoading(true);
    try {
      console.log('🔍 fetchBalances: Calling API...');
      const response = await api.get<any>('/api/v1/wallet/balances');
      
      // Log the FULL raw response for debugging
      console.log('🔥 fetchBalances: Raw API response:', response);

      // Handle different possible response structures
      let success = false;
      let assets = [];
      let total_usd = 0;

      if (response?.success === true) {
        // Standard: { success: true, assets: [...], total_usd: ... }
        success = true;
        assets = response.assets || [];
        total_usd = response.total_usd || 0;
      } else if (response?.data?.success === true) {
        // Wrapped: { data: { success: true, assets: [...] } }
        success = true;
        assets = response.data.assets || [];
        total_usd = response.data.total_usd || 0;
      } else {
        console.warn('⚠️ fetchBalances: Unexpected response format', response);
      }

      if (!success) {
        console.error('❌ fetchBalances: API reported failure', response);
        setBalances({});
        setTotalBalanceUSD(0);
        return;
      }

      // Transform assets into balances object
      const balancesObj: { [asset: string]: WalletBalance } = {};
      
      if (!Array.isArray(assets)) {
        console.error('❌ fetchBalances: assets is not an array', assets);
        setBalances({});
        setTotalBalanceUSD(0);
        return;
      }

      console.log(`📦 fetchBalances: Received ${assets.length} assets`);

      assets.forEach((asset: any, index: number) => {
        // Determine the asset key (symbol or asset field, fallback to chain)
        let assetKey = asset.symbol || asset.asset;
        if (!assetKey) {
          // Fallback: map chain to native asset symbol
          const chainToAsset: { [key: string]: string } = {
            algorand: 'ALGO',
            bitcoin: 'BTC',
            ethereum: 'ETH',
            polygon: 'MATIC',
            tron: 'TRX',
            solana: 'SOL'
          };
          assetKey = chainToAsset[asset.chain] || asset.chain.toUpperCase();
          console.warn(`⚠️ Asset ${index} missing symbol/asset, using fallback: ${assetKey}`);
        }

        console.log(`  → Mapping: ${asset.chain} → ${assetKey} (balance: ${asset.balance})`);

        balancesObj[assetKey] = {
          balance: asset.balance || 0,
          chain: asset.chain,
          usd_value: asset.usd_value || 0
        };
      });

      console.log('✅ fetchBalances: Final balancesObj:', balancesObj);

      // Update state
      setBalances(balancesObj);
      setTotalBalanceUSD(total_usd);
    } catch (error) {
      console.error('❌ fetchBalances: Exception caught', error);
      setBalances({});
      setTotalBalanceUSD(0);
    } finally {
      setLoading(false);
    }
  }, [user]);

  // ============================================================================
  // SEND TRANSACTION
  // ============================================================================
  const sendTransaction = useCallback(async (params: SendTransactionParams) => {
    try {
      const response = await api.post<any>('/api/v1/wallet/send', {
        recipient: params.recipient,
        asset: params.asset,
        amount: params.amount,
        memo: params.memo
      });

      if (response.success) {
        toast.success(response.message || 'Transaction sent successfully!');
        
        // Refresh balances after successful transaction
        await fetchBalances();
        
        return {
          success: true,
          tx_id: response.transaction_id
        };
      } else {
        toast.error(response.error || 'Transaction failed');
        return {
          success: false,
          error: response.error
        };
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Transaction failed';
      toast.error(errorMessage);
      
      return {
        success: false,
        error: errorMessage
      };
    }
  }, [fetchBalances]);

  // ============================================================================
  // REFRESH ALL
  // ============================================================================
  const refreshAll = useCallback(async () => {
    await Promise.all([
      fetchWallets(),
      fetchBalances()
    ]);
  }, [fetchWallets, fetchBalances]);

  // ============================================================================
  // INITIAL LOAD
  // ============================================================================
  useEffect(() => {
    if (user) {
      console.log('âœ… WalletContext: User authenticated, loading wallet data...');
      refreshAll();
    } else {
      console.log('â„¹ï¸ WalletContext: User not authenticated, skipping wallet fetch');
      setLoading(false);
      // Clear state when logged out
      setWallets({});
      setBalances({});
      setTotalBalanceUSD(0);
    }
  }, [user]); // â† Changed from [] to [user]

  // ============================================================================
  // CONTEXT VALUE
  // ============================================================================
  const value: WalletContextValue = {
    wallets,
    balances,
    totalBalanceUSD,
    loading,
    fetchWallets,
    fetchBalances,
    sendTransaction,
    refreshAll
  };

  return (
    <WalletContext.Provider value={value}>
      {children}
    </WalletContext.Provider>
  );
};

// ============================================================================
// HOOK
// ============================================================================
export const useWallet = () => {
  const context = useContext(WalletContext);
  if (context === undefined) {
    throw new Error('useWallet must be used within a WalletProvider');
  }
  return context;
};