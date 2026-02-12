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
  // ============================================================================
  const fetchBalances = useCallback(async () => {
    // âœ… CRITICAL: Only fetch if authenticated
    if (!user) {
      console.log('â„¹ï¸ WalletContext: User not authenticated, skipping balance fetch');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await api.get<any>('/api/v1/wallet/balances');
      
      if (response.success) {
        // Convert assets array to object keyed by asset symbol
        const balancesObj: { [asset: string]: WalletBalance } = {};
        
        response.assets?.forEach((asset: any) => {
          // ðŸš¨ FIX: Derive asset key from chain since API doesn't return symbol
          let assetKey: string;
          
          // Map chain to native asset symbol
          const chainToAsset: { [key: string]: string } = {
            'algorand': 'ALGO',
            'bitcoin': 'BTC', 
            'ethereum': 'ETH',
            'polygon': 'MATIC',
            'tron': 'TRX'
          };
          
          // If asset has explicit symbol/asset field, use it; otherwise derive from chain
          if (asset.symbol) {
            assetKey = asset.symbol;
          } else if (asset.asset) {
            assetKey = asset.asset;
          } else {
            // Fallback: Use chain mapping
            assetKey = chainToAsset[asset.chain] || asset.chain.toUpperCase();
          }
          
          console.log(`âœ… Mapped: ${asset.chain} â†’ ${assetKey} (balance: ${asset.balance})`);
          
          balancesObj[assetKey] = {
            balance: asset.balance,
            chain: asset.chain,
            usd_value: asset.usd_value
          };
        });
        
        setBalances(balancesObj);
        setTotalBalanceUSD(response.total_usd || 0);
      }
    } catch (error: any) {
      // âœ… Handle 403 gracefully (expected when not authenticated)
      if (error?.response?.status === 403) {
        console.log('â„¹ï¸ Balance fetch returned 403 (not authenticated)');
        setBalances({});
        setTotalBalanceUSD(0);
      } else {
        // Real errors (500, network issues, etc.)
        console.error('Failed to fetch balances:', error);
        toast.error('Failed to load balances');
      }
    } finally {
      setLoading(false);
    }
  }, []);

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