// 📂 FILE: frontend/src/components/WalletConnectionModal.tsx
import React, { useState, useEffect } from 'react';
import { X, Check, AlertTriangle, Loader2 } from 'lucide-react';
import { supabase } from '@/lib/supabase';
import toast from 'react-hot-toast';
import Web3 from 'web3';

interface WalletConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (wallet: ConnectedWallet) => void;
}

interface ConnectedWallet {
  address: string;
  chain: string;
  chainName: string;
  walletSource: string;
  verified: boolean;
}

interface DetectedWallet {
  name: string;
  icon: string;
  detected: boolean;
  provider: any;
  chainId: number;
}

interface WindowWithEthereum extends Window {
  ethereum?: {
    isMetaMask?: boolean;
    isCoinbaseWallet?: boolean;
    isTrust?: boolean;
    isBinance?: boolean;
    request: (args: { method: string; params?: any[] }) => Promise<any>;
  };
}

const CAMP_NETWORK_CONFIG = {
  chainId: '0x4f650', // 325000 in hex
  chainName: 'Camp Network Testnet V2',
  rpcUrls: ['https://rpc.camp-network-testnet.gelato.digital'],
  nativeCurrency: {
    name: 'ETH',
    symbol: 'ETH',
    decimals: 18
  },
  blockExplorerUrls: ['https://camp.cloud.blockscout.com']
};

export const WalletConnectionModal: React.FC<WalletConnectionModalProps> = ({
  isOpen,
  onClose,
  onSuccess
}) => {
  const [connecting, setConnecting] = useState(false);
  const [step, setStep] = useState<'select' | 'connecting' | 'signing' | 'success'>('select');
  const [detectedWallets, setDetectedWallets] = useState<DetectedWallet[]>([]);
  const [selectedWallet, setSelectedWallet] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // 🔍 DETECT AVAILABLE WALLETS
  useEffect(() => {
    if (!isOpen) return;

    const detectWallets = async () => {
      const wallets: DetectedWallet[] = [];
      const win = window as WindowWithEthereum;

      // MetaMask and other EIP-1193 providers
      if (win.ethereum) {
        const ethereum = win.ethereum;
        let chainId = 0;

        try {
          const chainIdHex = await ethereum.request({ method: 'eth_chainId' });
          chainId = parseInt(chainIdHex, 16);
        } catch {
          // Default to mainnet if chainId fails
          chainId = 1;
        }

        // Check for specific wallet providers
        if (ethereum.isMetaMask) {
          wallets.push({
            name: 'MetaMask',
            icon: '🦊',
            detected: true,
            provider: ethereum,
            chainId
          });
        }

        if (ethereum.isCoinbaseWallet) {
          wallets.push({
            name: 'Coinbase Wallet',
            icon: '🔵',
            detected: true,
            provider: ethereum,
            chainId
          });
        }

        if (ethereum.isTrust) {
          wallets.push({
            name: 'Trust Wallet',
            icon: '🛡️',
            detected: true,
            provider: ethereum,
            chainId
          });
        }

        if (ethereum.isBinance) {
          wallets.push({
            name: 'Binance Wallet',
            icon: '💎',
            detected: true,
            provider: ethereum,
            chainId
          });
        }

        // Generic EIP-1193 provider fallback
        if (wallets.length === 0) {
          wallets.push({
            name: 'Browser Wallet',
            icon: '🌐',
            detected: true,
            provider: ethereum,
            chainId
          });
        }
      }

      // WalletConnect (always available)
      wallets.push({
        name: 'WalletConnect',
        icon: '📱',
        detected: true,
        provider: null, // Will be initialized on click
        chainId: 0
      });

      setDetectedWallets(wallets);
    };

    detectWallets();
  }, [isOpen]);

  // 🔌 CONNECT WALLET
  const handleConnectWallet = async (wallet: DetectedWallet) => {
    if (connecting || !wallet.detected) return;

    // Handle WalletConnect separately (needs implementation)
    if (wallet.name === 'WalletConnect') {
      toast.error('WalletConnect integration coming soon');
      return;
    }

    setConnecting(true);
    setSelectedWallet(wallet.name);
    setStep('connecting');
    setErrorMessage(null);

    try {
      // 1️⃣ REQUEST ACCOUNT ACCESS
      const accounts = await wallet.provider.request({ method: 'eth_requestAccounts' });
      const address = accounts[0];
      const chainIdHex = await wallet.provider.request({ method: 'eth_chainId' });
      const chainId = parseInt(chainIdHex, 16);

      console.log('✅ Wallet connected:', address);
      console.log('Current Chain ID:', chainId);

      // 2️⃣ CHECK IF ON CAMP NETWORK
      const campChainId = 325000;
      if (chainId !== campChainId) {
        toast.error('Please switch to Camp Network', { duration: 5000 });
        
        // Attempt to switch network
        try {
          await wallet.provider.request({
            method: 'wallet_switchEthereumChain',
            params: [{ chainId: CAMP_NETWORK_CONFIG.chainId }]
          });
        } catch (switchError: any) {
          // Chain not added - add it
          if (switchError.code === 4902) {
            await wallet.provider.request({
              method: 'wallet_addEthereumChain',
              params: [CAMP_NETWORK_CONFIG]
            });
          } else {
            throw switchError;
          }
        }
      }

      // 3️⃣ GENERATE NONCE FROM BACKEND
      setStep('signing');
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      if (sessionError || !session?.access_token) {
        console.error('❌ Session error:', sessionError);
        throw new Error('Please sign in to Seamount first');
      }

      console.log('🔑 Generating nonce for:', address);

      const nonceResponse = await fetch('/api/v1/wallet/generate-nonce', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({ address }),
        credentials: 'include' // ✅ ADD THIS for CORS
      });

      console.log('📡 Nonce response status:', nonceResponse.status);

      if (!nonceResponse.ok) {
        const errorText = await nonceResponse.text();
        console.error('❌ Nonce generation failed:', errorText);
        throw new Error(`Failed to generate nonce: ${nonceResponse.status} ${errorText}`);
      }

      const { nonce, message } = await nonceResponse.json();

      // 4️⃣ REQUEST SIGNATURE
      const web3 = new Web3(wallet.provider);
      const signature = await web3.eth.personal.sign(message, address, '');

      console.log('✅ Signature obtained');

      // 5️⃣ SAVE WALLET TO BACKEND
      const walletSource = wallet.name.toLowerCase().replace(/\s+/g, '_');
      
      const saveResponse = await fetch('/api/v1/wallet/connect-external', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          address,
          chain: 'ethereum',
          wallet_source: walletSource,
          signature,
          message
        })
      });

      if (!saveResponse.ok) {
        const errorData = await saveResponse.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to save wallet');
      }

      const saveData = await saveResponse.json();

      // 6️⃣ SUCCESS
      setStep('success');
      toast.success(`✅ ${wallet.name} connected successfully!`);

      setTimeout(() => {
        onSuccess({
          address,
          chain: 'ethereum',
          chainName: 'Camp Network',
          walletSource,
          verified: true
        });
        onClose();
      }, 1500);

    } catch (error: any) {
      console.error('Wallet connection failed:', error);
      
      let errorMsg = 'Failed to connect wallet';
      if (error.message?.includes('User rejected')) {
        errorMsg = 'Connection rejected by user';
      } else if (error.message?.includes('sign in')) {
        errorMsg = 'Please sign in to Seamount first';
      } else if (error.message) {
        errorMsg = error.message;
      }
      
      setErrorMessage(errorMsg);
      toast.error(errorMsg);
      setStep('select');
    } finally {
      setConnecting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
      <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-md w-full shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-slate-700 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white">Connect Wallet</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors disabled:opacity-50"
            disabled={connecting}
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          {/* Step Indicator */}
          <div className="flex items-center justify-center gap-2 mb-6">
            {['select', 'connecting', 'signing', 'success'].map((s, idx) => (
              <div
                key={s}
                className={`h-2 w-12 rounded-full transition-all ${
                  s === step
                    ? 'bg-green-500'
                    : ['select', 'connecting', 'signing', 'success'].indexOf(step) > idx
                    ? 'bg-green-600'
                    : 'bg-slate-700'
                }`}
              />
            ))}
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-red-400 text-sm">{errorMessage}</p>
            </div>
          )}

          {/* Wallet Selection */}
          {step === 'select' && (
            <div className="space-y-3">
              {detectedWallets.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-400 mb-4">No Web3 wallet detected</p>
                  <a
                    href="https://metamask.io/download/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-green-400 hover:text-green-300 underline"
                  >
                    Install MetaMask
                  </a>
                </div>
              ) : (
                detectedWallets.map((wallet) => (
                  <button
                    key={wallet.name}
                    onClick={() => handleConnectWallet(wallet)}
                    disabled={connecting || !wallet.detected}
                    className="w-full p-4 bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-green-500 rounded-xl transition-all text-left flex items-center gap-4 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span className="text-3xl">{wallet.icon}</span>
                    <div className="flex-1">
                      <div className="font-semibold text-white">{wallet.name}</div>
                      <div className="text-xs text-gray-400">
                        {wallet.detected ? 'Available' : 'Not installed'}
                      </div>
                    </div>
                    {wallet.detected ? (
                      <div className="text-green-500">
                        <Check className="h-5 w-5" />
                      </div>
                    ) : (
                      <div className="text-gray-500">
                        <AlertTriangle className="h-5 w-5" />
                      </div>
                    )}
                  </button>
                ))
              )}
            </div>
          )}

          {/* Connecting State */}
          {step === 'connecting' && (
            <div className="text-center py-8">
              <Loader2 className="h-12 w-12 text-green-500 animate-spin mx-auto mb-4" />
              <p className="text-white font-semibold mb-2">Connecting to {selectedWallet}...</p>
              <p className="text-gray-400 text-sm">Please approve the connection request</p>
            </div>
          )}

          {/* Signing State */}
          {step === 'signing' && (
            <div className="text-center py-8">
              <Loader2 className="h-12 w-12 text-green-500 animate-spin mx-auto mb-4" />
              <p className="text-white font-semibold mb-2">Sign the verification message</p>
              <p className="text-gray-400 text-sm">This proves you own the wallet</p>
            </div>
          )}

          {/* Success State */}
          {step === 'success' && (
            <div className="text-center py-8">
              <div className="h-16 w-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="h-10 w-10 text-green-500" />
              </div>
              <p className="text-white font-semibold mb-2">Wallet connected successfully!</p>
              <p className="text-gray-400 text-sm">Redirecting...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};