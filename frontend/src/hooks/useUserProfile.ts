import { useState, useEffect, useCallback } from 'react';
import { seamountBackend } from '../services/seamountBackend';

interface BackendState {
  connected: boolean;
  loading: boolean;
  error: string | null;
  balance: number;
  transactions: any[];
  portfolio: any;
}

export function useBackendIntegration(userId: string) {
  const [state, setState] = useState<BackendState>({
    connected: false,
    loading: true,
    error: null,
    balance: 0,
    transactions: [],
    portfolio: null
  });

  // Initialize connection
  useEffect(() => {
    let mounted = true;

    const initializeConnection = async () => {
      try {
        setState(prev => ({ ...prev, loading: true, error: null }));

        // Check backend health
        const isHealthy = await seamountBackend.checkHealth();
        
        if (mounted) {
          setState(prev => ({ 
            ...prev, 
            connected: isHealthy,
            loading: false
          }));

          // Connect WebSocket for real-time updates
          if (isHealthy) {
            seamountBackend.connectWebSocket(userId);
          }

          // Load initial data
          await loadInitialData();
        }
      } catch (error) {
        if (mounted) {
          setState(prev => ({ 
            ...prev, 
            error: 'Connection failed',
            loading: false,
            connected: false
          }));
        }
      }
    };

    const loadInitialData = async () => {
      try {
        const [balance, transactions, portfolio] = await Promise.all([
          seamountBackend.getBalance(userId),
          seamountBackend.getTransactionHistory(userId),
          seamountBackend.getPortfolioData()
        ]);

        if (mounted) {
          setState(prev => ({
            ...prev,
            balance,
            transactions,
            portfolio
          }));
        }
      } catch (error) {
        console.error('Failed to load initial data:', error);
      }
    };

    initializeConnection();

    // Listen for real-time updates
    const handleBalanceUpdate = (event: CustomEvent) => {
      setState(prev => ({ ...prev, balance: event.detail.balance }));
    };

    const handleTransactionConfirmed = (event: CustomEvent) => {
      setState(prev => ({
        ...prev,
        transactions: [event.detail, ...prev.transactions.slice(0, 19)]
      }));
    };

    window.addEventListener('balanceUpdate', handleBalanceUpdate as EventListener);
    window.addEventListener('transactionConfirmed', handleTransactionConfirmed as EventListener);

    return () => {
      mounted = false;
      seamountBackend.disconnect();
      window.removeEventListener('balanceUpdate', handleBalanceUpdate as EventListener);
      window.removeEventListener('transactionConfirmed', handleTransactionConfirmed as EventListener);
    };
  }, [userId]);

  // Payment flow methods
  const initiateFunding = useCallback(async (fundingData: {
    amount: number;
    currency: string;
    country: string;
    paymentMethod: string;
  }) => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      const session = await seamountBackend.initiateFundingFlow({
        ...fundingData,
        userId
      });

      setState(prev => ({ ...prev, loading: false }));
      return session;
    } catch (error) {
      setState(prev => ({ 
        ...prev, 
        loading: false, 
        error: error instanceof Error ? error.message : 'Funding failed' 
      }));
      throw error;
    }
  }, [userId]);

  const executeTransfer = useCallback(async (transferData: {
    toAddress: string;
    amount: number;
    token: string;
  }) => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      const result = await seamountBackend.executeTransfer({
        ...transferData,
        fromUserId: userId
      });

      // Update balance optimistically
      setState(prev => ({ 
        ...prev, 
        loading: false,
        balance: prev.balance - transferData.amount
      }));

      return result;
    } catch (error) {
      setState(prev => ({ 
        ...prev, 
        loading: false, 
        error: error instanceof Error ? error.message : 'Transfer failed' 
      }));
      throw error;
    }
  }, [userId]);

  const createWallet = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      const wallet = await seamountBackend.createWallet(userId);
      
      setState(prev => ({ ...prev, loading: false }));
      return wallet;
    } catch (error) {
      setState(prev => ({ 
        ...prev, 
        loading: false, 
        error: error instanceof Error ? error.message : 'Wallet creation failed' 
      }));
      throw error;
    }
  }, [userId]);

  const getSwapQuote = useCallback(async (fromToken: string, toToken: string, amount: number) => {
    return seamountBackend.getSwapQuote(fromToken, toToken, amount);
  }, []);

  const executeSwap = useCallback(async (swapData: {
    fromToken: string;
    toToken: string;
    amount: number;
    slippage: number;
    userAddress: string;
  }) => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      const result = await seamountBackend.executeSwap(swapData);
      
      setState(prev => ({ ...prev, loading: false }));
      return result;
    } catch (error) {
      setState(prev => ({ 
        ...prev, 
        loading: false, 
        error: error instanceof Error ? error.message : 'Swap failed' 
      }));
      throw error;
    }
  }, []);

  const refreshData = useCallback(async () => {
    try {
      const [balance, transactions, portfolio] = await Promise.all([
        seamountBackend.getBalance(userId),
        seamountBackend.getTransactionHistory(userId),
        seamountBackend.getPortfolioData()
      ]);

      setState(prev => ({
        ...prev,
        balance,
        transactions,
        portfolio
      }));
    } catch (error) {
      console.error('Failed to refresh data:', error);
    }
  }, [userId]);

  return {
    ...state,
    initiateFunding,
    executeTransfer,
    createWallet,
    getSwapQuote,
    executeSwap,
    refreshData
  };
}