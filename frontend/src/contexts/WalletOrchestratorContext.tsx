import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useAppKit } from '@reown/appkit/react';
import { useAccount, useDisconnect, useSignMessage, useChainId } from 'wagmi';
import { apiClient } from '@/config/api';
import { useAuth } from './AuthContext';
import toast from 'react-hot-toast';

// ============================================================================
// TYPES
// ============================================================================

type ChainId = 'algorand' | 'bitcoin' | 'ethereum' | 'polygon' | 'tron' | 'base' | 'celo' | 'basecamp';

interface AutoCreatedWallet {
  address: string;
  balance: number;
  usd_value: number;
  status: 'created' | 'not_created';
  type: 'auto_created';
}

interface ExternalWallet {
  address: string;
  chainId: number;
  walletProvider: string;
  isConnected: boolean;
  type: 'external';
}

interface NetworkConfig {
  id: ChainId;
  name: string;
  chainId: number;
  chainIdHex: string;
  nativeCurrency: string;
  connectionMethod: 'auto_created' | 'walletconnect' | 'metamask_direct';
  rpcUrl?: string;
  explorer: string;
}

interface WalletOrchestratorContextType {
  // External wallets ONLY (BaseCAMP, Base, Celo)
  externalWallets: Record<ChainId, ExternalWallet | null>;
  
  // BaseCAMP specific (for predictions)
  baseCampAddress: string | null;
  isBaseCampConnected: boolean;
  
  // Actions
  connectExternalWallet: (network: 'base' | 'celo') => Promise<void>;
  connectBaseCAMP: () => Promise<void>;
  disconnectExternalWallet: (network: ChainId) => Promise<void>;
  
  // State
  loading: boolean;
  isConnecting: boolean;
}

const WalletOrchestratorContext = createContext<WalletOrchestratorContextType | undefined>(undefined);

// ============================================================================
// NETWORK CONFIGURATIONS
// ============================================================================

const NETWORK_CONFIGS: Record<ChainId, NetworkConfig> = {
  // Auto-created wallets (backend manages)
  algorand: {
    id: 'algorand',
    name: 'Algorand',
    chainId: 0, // Not EVM
    chainIdHex: '0x0',
    nativeCurrency: 'ALGO',
    connectionMethod: 'auto_created',
    explorer: 'https://algoexplorer.io'
  },
  bitcoin: {
    id: 'bitcoin',
    name: 'Bitcoin',
    chainId: 0,
    chainIdHex: '0x0',
    nativeCurrency: 'BTC',
    connectionMethod: 'auto_created',
    explorer: 'https://blockchair.com/bitcoin'
  },
  ethereum: {
    id: 'ethereum',
    name: 'Ethereum',
    chainId: 1,
    chainIdHex: '0x1',
    nativeCurrency: 'ETH',
    connectionMethod: 'auto_created',
    explorer: 'https://etherscan.io'
  },
  polygon: {
    id: 'polygon',
    name: 'Polygon',
    chainId: 137,
    chainIdHex: '0x89',
    nativeCurrency: 'MATIC',
    connectionMethod: 'auto_created',
    explorer: 'https://polygonscan.com'
  },
  tron: {
    id: 'tron',
    name: 'TRON',
    chainId: 0,
    chainIdHex: '0x0',
    nativeCurrency: 'TRX',
    connectionMethod: 'auto_created',
    explorer: 'https://tronscan.org'
  },
  
  // External wallets (user connects)
  basecamp: {
    id: 'basecamp',
    name: 'BaseCAMP Testnet',
    chainId: 123456789, // Actual BaseCAMP chain ID
    chainIdHex: '0x1cbc67c35a',
    nativeCurrency: 'CAMP',
    connectionMethod: 'metamask_direct',
    rpcUrl: 'https://rpc.basecamp.t.raas.gelato.cloud',
    explorer: 'https://basecamp.cloud.blockscout.com'
  },
  base: {
    id: 'base',
    name: 'Base',
    chainId: 8453,
    chainIdHex: '0x2105',
    nativeCurrency: 'ETH',
    connectionMethod: 'walletconnect',
    explorer: 'https://basescan.org'
  },
  celo: {
    id: 'celo',
    name: 'Celo',
    chainId: 42220,
    chainIdHex: '0xA4EC',
    nativeCurrency: 'CELO',
    connectionMethod: 'walletconnect',
    explorer: 'https://celoscan.io'
  }
};

// ============================================================================
// PROVIDER
// ============================================================================

export function WalletOrchestratorProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { open } = useAppKit();
  const { address: wagmiAddress, isConnected: wagmiConnected, chain } = useAccount();
  const chainId = useChainId();
  const { disconnect } = useDisconnect();
  const { signMessageAsync } = useSignMessage();
  
  // State - ONLY external wallets
  const [externalWallets, setExternalWallets] = useState<Record<ChainId, ExternalWallet | null>>({
    base: null,
    celo: null,
    basecamp: null,
    algorand: null,
    bitcoin: null,
    ethereum: null,
    polygon: null,
    tron: null
  });
  const [totalBalanceUSD, setTotalBalanceUSD] = useState(0);
  const [loading, setLoading] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [baseCampAddress, setBaseCampAddress] = useState<string | null>(null);

  // ============================================================================
  // FETCH EXTERNAL WALLETS (Only when authenticated)
  // ============================================================================
  
  const fetchExternalWallets = async () => {
    if (!user) {
      console.log('ℹ️ User not authenticated, skipping external wallets fetch');
      return;
    }

    try {
      const response = await apiClient.get('/api/v1/wallet/connected-wallets');
      
      if (response.data.success) {
        const walletList = response.data.wallets || [];
        const newExternalWallets = { ...externalWallets };

        walletList.forEach((wallet: any) => {
          const networkId = wallet.blockchain as ChainId;
          if (networkId === 'base' || networkId === 'celo') {
            newExternalWallets[networkId] = {
              address: wallet.address,
              chainId: NETWORK_CONFIGS[networkId].chainId,
              walletProvider: wallet.wallet_provider || 'unknown',
              isConnected: true,
              type: 'external'
            };
          }
        });

        setExternalWallets(newExternalWallets);
        console.log(`✅ Fetched external wallets:`, newExternalWallets);
      }
    } catch (error: any) {
      if (error?.response?.status === 403) {
        console.log('ℹ️ External wallets fetch returned 403 (not authenticated)');
      } else {
        console.error('Failed to fetch external wallets:', error);
      }
    }
  };

  // ============================================================================
  // CHECK BASECAMP PERSISTENCE (Local storage)
  // ============================================================================
  
  const checkBaseCampConnection = () => {
    if (typeof window === 'undefined' || !window.ethereum) return;

    const savedAddress = localStorage.getItem('basecamp_address');
    if (savedAddress) {
      window.ethereum.request({ method: 'eth_accounts' }).then((accounts: string[]) => {
        if (accounts.includes(savedAddress)) {
          setBaseCampAddress(savedAddress);
          console.log('✅ BaseCAMP persisted:', savedAddress.slice(0, 8) + '...');
        } else {
          localStorage.removeItem('basecamp_address');
        }
      });
    }
  };

  // ============================================================================
  // CONNECT BASECAMP (MetaMask Direct - No backend)
  // ============================================================================
  
  const connectBaseCAMP = async () => {
    if (!window.ethereum) {
      toast.error('MetaMask not installed');
      return;
    }

    setIsConnecting(true);

    try {
      const config = NETWORK_CONFIGS.basecamp;

      // Request accounts
      const accounts = await window.ethereum.request({ 
        method: 'eth_requestAccounts' 
      }) as string[];

      if (!accounts || accounts.length === 0) {
        throw new Error('No accounts found');
      }

      // Switch or add network
      try {
        await window.ethereum.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: config.chainIdHex }]
        });
      } catch (switchError: any) {
        if (switchError.code === 4902) {
          // Add network
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [{
              chainId: config.chainIdHex,
              chainName: config.name,
              nativeCurrency: {
                name: config.nativeCurrency,
                symbol: config.nativeCurrency,
                decimals: 18
              },
              rpcUrls: [config.rpcUrl],
              blockExplorerUrls: [config.explorer]
            }]
          });
        } else {
          throw switchError;
        }
      }

      // Save to localStorage
      localStorage.setItem('basecamp_address', accounts[0]);
      setBaseCampAddress(accounts[0]);

      toast.success('BaseCAMP connected!');
      console.log('✅ BaseCAMP connected:', accounts[0].slice(0, 8) + '...');

    } catch (error: any) {
      console.error('BaseCAMP connection failed:', error);
      
      if (error.code === 4001) {
        toast.error('Connection rejected');
      } else {
        toast.error('Failed to connect BaseCAMP');
      }
    } finally {
      setIsConnecting(false);
    }
  };

  // ============================================================================
  // CONNECT EXTERNAL WALLET (Base/Celo via WalletConnect)
  // ============================================================================
  
  const connectExternalWallet = async (network: 'base' | 'celo') => {
    if (!user) {
      toast.error('Please sign in to connect wallets');
      return;
    }

    setIsConnecting(true);
    const config = NETWORK_CONFIGS[network];

    try {
      // Step 1: Open WalletConnect modal if not connected
      if (!wagmiConnected || !wagmiAddress) {
        await open();
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        if (!wagmiConnected || !wagmiAddress) {
          throw new Error('Wallet connection cancelled');
        }
      }

      // Step 2: Verify correct network
      if (chainId !== config.chainId) {
        toast.error(`Please switch to ${config.name} network in your wallet`);
        setIsConnecting(false);
        return;
      }

      // Step 3: Get nonce
      const nonceResponse = await apiClient.post('/api/v1/wallet/nonce', {
        address: wagmiAddress,
        blockchain: network
      });

      if (!nonceResponse.data.success) {
        throw new Error(nonceResponse.data.error || 'Failed to generate nonce');
      }

      const { nonce, message } = nonceResponse.data;

      // Step 4: Sign message
      const signature = await signMessageAsync({ message });

      // Step 5: Detect wallet provider
      let walletProvider = 'walletconnect';
      const ethereum = (window as any).ethereum;
      if (ethereum?.isMetaMask) walletProvider = 'metamask';
      else if (ethereum?.isCoinbaseWallet) walletProvider = 'coinbase_wallet';
      else if (ethereum?.isMiniPay) walletProvider = 'minipay';
      else if (ethereum?.isValora) walletProvider = 'valora';

      // Step 6: Register connection
      const connectResponse = await apiClient.post('/api/v1/wallet/connect', {
        blockchain: network,
        address: wagmiAddress,
        wallet_provider: walletProvider,
        signature,
        nonce
      });

      if (!connectResponse.data.success) {
        throw new Error(connectResponse.data.error || 'Registration failed');
      }

      // Update state
      setExternalWallets(prev => ({
        ...prev,
        [network]: {
          address: wagmiAddress,
          chainId: config.chainId,
          walletProvider,
          isConnected: true,
          type: 'external'
        }
      }));

      toast.success(`${config.name} wallet connected!`);
      console.log(`✅ ${network} connected:`, wagmiAddress.slice(0, 8) + '...');

    } catch (error: any) {
      console.error(`${network} connection failed:`, error);
      
      if (error.message?.includes('rejected')) {
        toast.error('Connection rejected');
      } else {
        toast.error(`Failed to connect ${config.name}`);
      }
    } finally {
      setIsConnecting(false);
    }
  };

  // ============================================================================
  // DISCONNECT WALLET
  // ============================================================================
  
  const disconnectExternalWallet = async (network: ChainId) => {
    const config = NETWORK_CONFIGS[network];

    try {
      if (network === 'basecamp') {
        // Local storage only
        localStorage.removeItem('basecamp_address');
        setBaseCampAddress(null);
        toast.success('BaseCAMP disconnected');
      } else if (network === 'base' || network === 'celo') {
        // Backend disconnect
        await apiClient.post('/api/v1/wallet/disconnect', { blockchain: network });
        
        setExternalWallets(prev => ({
          ...prev,
          [network]: null
        }));

        // If this is the active wagmi chain, disconnect
        if (chainId === config.chainId) {
          disconnect();
        }

        toast.success(`${config.name} disconnected`);
      }
    } catch (error) {
      console.error(`${network} disconnection failed:`, error);
      toast.error(`Failed to disconnect ${config.name}`);
    }
  };

  // ============================================================================
  // INITIALIZATION
  // ============================================================================
  
  useEffect(() => {
    if (user) {
      console.log('✅ User authenticated, checking external wallets...');
      // ONLY fetch external wallets (Base, Celo)
      // Auto-created wallets handled by WalletProvider
      fetchExternalWallets();
      checkBaseCampConnection();
    } else {
      // Clear external wallet state only
      setExternalWallets({
        base: null,
        celo: null,
        basecamp: null,
        algorand: null,
        bitcoin: null,
        ethereum: null,
        polygon: null,
        tron: null
      });
      setBaseCampAddress(null);
  }
}, [user]);

  // Check BaseCAMP on mount
  useEffect(() => {
    checkBaseCampConnection();
  }, []);

  // ============================================================================
  // CONTEXT VALUE
  // ============================================================================
  const value: WalletOrchestratorContextType = {
    externalWallets,
    baseCampAddress,
    isBaseCampConnected: !!baseCampAddress,
    connectExternalWallet,
    connectBaseCAMP,
    disconnectExternalWallet,
    loading,
    isConnecting
  };

  return (
    <WalletOrchestratorContext.Provider value={value}>
      {children}
    </WalletOrchestratorContext.Provider>
  );
}

// ============================================================================
// HOOK
// ============================================================================

export function useWalletOrchestrator() {
  const context = useContext(WalletOrchestratorContext);
  if (!context) {
    throw new Error('useWalletOrchestrator must be used within WalletOrchestratorProvider');
  }
  return context;
}

// Export configs for use in other components
export { NETWORK_CONFIGS };
export type { ChainId, AutoCreatedWallet, ExternalWallet };