// File Location: frontend/src/hooks/useWallet.ts
// Description: The single, unified hook for all Algorand wallet and on-chain interactions.

import { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../config/api';

// Define the shape of our wallet state
interface WalletState {
  address: string | null;
  balance: number;
  loading: boolean;
  error: string | null;
  isConnected: boolean;
}

export function useWallet() {
  const { user } = useAuth();
  const [walletState, setWalletState] = useState<WalletState>({
    address: null,
    balance: 0,
    loading: true,
    error: null,
    isConnected: false,
  });

  const handleError = (error: unknown, context: string) => {
    const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred.';
    logger.error(`Wallet Hook Error [${context}]:`, errorMessage);
    setWalletState(prev => ({ ...prev, error: errorMessage, loading: false }));
    toast.error(errorMessage);
  };
  
  const refreshBalance = useCallback(async () => {
    if (!user || !user.algorand_address) return;

    setWalletState(prev => ({ ...prev, loading: true }));
    try {
      const response = await apiClient.get('/api/v1/wallet/balance');
      setWalletState(prev => ({
        ...prev,
        balance: response.data.balance_usds,
        address: response.data.address,
        isConnected: true,
        loading: false,
      }));
    } catch (err) {
      handleError(err, 'refreshBalance');
    }
  }, [user]);

  // Effect to automatically fetch balance when the user is available
  useEffect(() => {
    if (user && user.algorand_address) {
      refreshBalance();
    } else {
      setWalletState(prev => ({ ...prev, loading: false, isConnected: false, address: null, balance: 0 }));
    }
  }, [user, refreshBalance]);
  
  const provisionWallet = useCallback(async () => {
    if (!user) {
      toast.error("You must be logged in to create a wallet.");
      return;
    }
    setWalletState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const response = await apiClient.post('/api/v1/user/provision-wallets');
      toast.success("Wallet provisioned successfully!");
      // The AuthContext will automatically refetch the user profile,
      // which will trigger the balance refresh.
      // Manually update state for immediate feedback
      setWalletState(prev => ({
          ...prev,
          address: response.data.algorand_address,
          isConnected: true,
          loading: false
      }));
    } catch (err) {
      handleError(err, 'provisionWallet');
    }
  }, [user]);

  const sendPayment = useCallback(async (recipientAddress: string, amount: number, memo: string) => {
    if (!walletState.isConnected || !user) {
      throw new Error("Wallet is not connected.");
    }
    setWalletState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const response = await apiClient.post('/api/v1/payments/p2p', {
        recipient_address: recipientAddress,
        amount: amount,
        memo: memo,
      });
      toast.success(`Successfully sent ${amount} USDS.`);
      await refreshBalance(); // Refresh balance after sending
      return response.data;
    } catch (err) {
      handleError(err, 'sendPayment');
      throw err; // Re-throw for the component to handle
    } finally {
      setWalletState(prev => ({ ...prev, loading: false }));
    }
  }, [user, walletState.isConnected, refreshBalance]);

  return {
    ...walletState,
    provisionWallet,
    refreshBalance,
    sendPayment,
  };
}