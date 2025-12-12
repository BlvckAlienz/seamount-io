import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useAppKit } from '@reown/appkit/react';
import { useAccount, useDisconnect, useSignMessage, useChainId } from 'wagmi';
import { apiClient } from '@/config/api';
import { useAuth } from './AuthContext';
import toast from 'react-hot-toast';

// Network types
type NetworkType = 'mainnet' | 'testnet' | 'camp_mainnet_future';
type ChainId = 'base' | 'celo' | 'basecamp' | 'camp_mainnet';

interface NetworkConfig {
  id: ChainId;
  name: string;
  type: NetworkType;
  chainId: number;
  chainIdHex: string;
  nativeCurrency: string;
  connectionMethod: 'walletconnect' | 'metamask_direct';
  icon: string;
  description: string;
  explorer: string;
  rpcUrl?: string;
}

interface WalletState {
  address: string;
  chainId: number;
  network: ChainId;
  isConnected: boolean;
  walletProvider: string;
  connectionType: string;
  balance?: string;
}

interface WalletOrchestratorContextType {
  // State
  wallets: Record<ChainId, WalletState | null>;
  activeNetwork: ChainId | null;
  isConnecting: boolean;
  
  // Methods
  connectWallet: (network: ChainId) => Promise<void>;
  disconnectWallet: (network: ChainId) => Promise<void>;
  switchNetwork: (from: ChainId, to: ChainId) => Promise<void>;
  getWallet: (network: ChainId) => WalletState | null;
  getBestNetworkForAction: (action: 'send' | 'bet' | 'earn' | 'swap') => ChainId;
  
  // Queries
  isWalletConnected: (network: ChainId) => boolean;
  getAllConnectedNetworks: () => ChainId[];
  getTotalBalanceUSD: () => number;
}

// Network configurations
const NETWORK_CONFIGS: Record<ChainId, NetworkConfig> = {
  base: {
    id: 'base',
    name: 'Base',
    type: 'mainnet',
    chainId: 8453,
    chainIdHex: '0x2105',
    nativeCurrency: 'ETH',
    connectionMethod: 'walletconnect',
    icon: 'https://icons.llamao.fi/icons/chains/rsz_base.jpg',
    description: 'Ethereum L2 by Coinbase',
    explorer: 'https://basescan.org'
  },
  celo: {
    id: 'celo',
    name: 'Celo',
    type: 'mainnet',
    chainId: 42220,
    chainIdHex: '0xA4EC',
    nativeCurrency: 'CELO',
    connectionMethod: 'walletconnect',
    icon: 'https://cryptologos.cc/logos/celo-celo-logo.svg',
    description: 'Mobile-first blockchain',
    explorer: 'https://celoscan.io'
  },
  basecamp: {
    id: 'basecamp',
    name: 'BaseCAMP',
    type: 'testnet',
    chainId: 8453, // Note: Same as Base but testnet
    chainIdHex: '0x1cbc67c35a',
    nativeCurrency: 'CAMP',
    connectionMethod: 'metamask_direct',
    icon: 'https://campnetwork.xyz/logo.png',
    description: 'Prediction markets testnet',
    explorer: 'https://basecamp.cloud.blockscout.com',
    rpcUrl: 'https://rpc.basecamp.t.raas.gelato.cloud'
  },
  camp_mainnet: {
    id: 'camp_mainnet',
    name: 'CAMP Mainnet',
    type: 'camp_mainnet_future',
    chainId: 84532, // Placeholder
    chainIdHex: '0x14A34',
    nativeCurrency: 'CAMP',
    connectionMethod: 'walletconnect',
    icon: 'https://campnetwork.xyz/logo.png',
    description: 'Future prediction markets mainnet',
    explorer: 'https://campnetwork.xyz',
    rpcUrl: 'https://rpc.campnetwork.xyz'
  }
};

// Action to network mapping
const ACTION_NETWORK_MAP: Record<string, ChainId[]> = {
  send: ['base', 'celo'], // Real money transfers
  bet: ['basecamp'], // Testnet for now, will be camp_mainnet
  earn: ['base', 'celo'], // Real yield
  swap: ['base', 'celo'] // Real swaps
};

// Create context
const WalletOrchestratorContext = createContext<WalletOrchestratorContextType | undefined>(undefined);

// Main provider component
export function WalletOrchestratorProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { open } = useAppKit();
  const { address, isConnected, chain } = useAccount();
  const chainId = useChainId();
  const { disconnect } = useDisconnect();
  const { signMessageAsync } = useSignMessage();
  
  const [wallets, setWallets] = useState<Record<ChainId, WalletState | null>>({
    base: null,
    celo: null,
    basecamp: null,
    camp_mainnet: null
  });
  const [activeNetwork, setActiveNetwork] = useState<ChainId | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);

  // Initialize: Load saved wallet states
  useEffect(() => {
    if (user) {
      loadSavedWallets();
      detectCurrentNetwork();
    }
  }, [user, chainId, address]);

  const loadSavedWallets = async () => {
    try {
      // Load WalletConnect wallets (Base, Celo)
      const response = await apiClient.get('/api/v1/wallet/connected-wallets');
      if (response.data.success) {
        const newWallets = { ...wallets };
        response.data.wallets.forEach((wallet: any) => {
          if (wallet.blockchain === 'base' || wallet.blockchain === 'celo') {
            newWallets[wallet.blockchain] = {
              address: wallet.address,
              chainId: NETWORK_CONFIGS[wallet.blockchain].chainId,
              network: wallet.blockchain,
              isConnected: true,
              walletProvider: wallet.wallet_provider,
              connectionType: 'walletconnect'
            };
          }
        });
        setWallets(newWallets);
      }
    } catch (error) {
      console.warn('Could not load saved wallets:', error);
    }
  };

  const detectCurrentNetwork = () => {
    if (!chainId || !address) return;
    
    // Check which network we're currently on
    Object.entries(NETWORK_CONFIGS).forEach(([networkId, config]) => {
      if (config.chainId === chainId || config.chainIdHex === `0x${chainId.toString(16)}`) {
        setActiveNetwork(networkId as ChainId);
        
        // Update wallet state if connected
        if (isConnected && address) {
          setWallets(prev => ({
            ...prev,
            [networkId]: {
              address,
              chainId,
              network: networkId as ChainId,
              isConnected: true,
              walletProvider: detectWalletProvider(),
              connectionType: config.connectionMethod
            }
          }));
        }
      }
    });
  };

  const detectWalletProvider = (): string => {
    const ethereum = (window as any).ethereum;
    if (ethereum?.isMetaMask) return 'metamask';
    if (ethereum?.isCoinbaseWallet) return 'coinbase_wallet';
    if (ethereum?.isMiniPay) return 'minipay';
    if (ethereum?.isValora) return 'valora';
    return 'walletconnect';
  };

  const connectWallet = async (network: ChainId): Promise<void> => {
    setIsConnecting(true);
    const config = NETWORK_CONFIGS[network];
    
    try {
      switch (config.connectionMethod) {
        case 'walletconnect':
          await connectViaWalletConnect(network, config);
          break;
        case 'metamask_direct':
          await connectViaMetaMask(network, config);
          break;
      }
      
      setActiveNetwork(network);
      toast.success(`${config.name} wallet connected!`);
    } catch (error: any) {
      console.error(`❌ Failed to connect ${network}:`, error);
      toast.error(`Failed to connect ${config.name}: ${error.message}`);
    } finally {
      setIsConnecting(false);
    }
  };

  const connectViaWalletConnect = async (network: ChainId, config: NetworkConfig) => {
    // Step 1: Open WalletConnect modal if not connected
    if (!isConnected || !address) {
      await open();
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      if (!isConnected || !address) {
        throw new Error('Wallet connection cancelled');
      }
    }

    // Step 2: Verify correct network
    if (chainId !== config.chainId) {
      throw new Error(`Please switch to ${config.name} network in your wallet`);
    }

    // Step 3: Get nonce and authenticate
    const nonceResponse = await apiClient.post('/api/v1/wallet/nonce', {
      address,
      blockchain: network
    });

    if (!nonceResponse.data.success) {
      throw new Error(nonceResponse.data.error || 'Authentication failed');
    }

    const { nonce, message } = nonceResponse.data;
    const signature = await signMessageAsync({ message });

    // Step 4: Register connection with backend
    const connectResponse = await apiClient.post('/api/v1/wallet/connect', {
      blockchain: network,
      address,
      wallet_provider: detectWalletProvider(),
      signature,
      nonce
    });

    if (!connectResponse.data.success) {
      throw new Error(connectResponse.data.error || 'Registration failed');
    }

    // Step 5: Update local state
    setWallets(prev => ({
      ...prev,
      [network]: {
        address,
        chainId: config.chainId,
        network,
        isConnected: true,
        walletProvider: detectWalletProvider(),
        connectionType: 'walletconnect'
      }
    }));
  };

  const connectViaMetaMask = async (network: ChainId, config: NetworkConfig) => {
    if (!(window as any).ethereum) {
      throw new Error('MetaMask not installed');
    }

    const ethereum = (window as any).ethereum;
    
    // Request accounts
    const accounts = await ethereum.request({ method: 'eth_requestAccounts' }) as string[];
    
    // Switch or add network
    try {
      await ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: config.chainIdHex }]
      });
    } catch (switchError: any) {
      if (switchError.code === 4902) {
        // Network not added, add it
        await ethereum.request({
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

    // Update local state (no backend registration for testnet)
    setWallets(prev => ({
      ...prev,
      [network]: {
        address: accounts[0],
        chainId: config.chainId,
        network,
        isConnected: true,
        walletProvider: 'metamask',
        connectionType: 'metamask_direct'
      }
    }));
  };

  const disconnectWallet = async (network: ChainId) => {
    const config = NETWORK_CONFIGS[network];
    const wallet = wallets[network];
    
    if (!wallet) return;
    
    try {
      if (wallet.connectionType === 'walletconnect') {
        // Disconnect from backend
        await apiClient.post('/api/v1/wallet/disconnect', { blockchain: network });
        
        // If this is the active network, disconnect from wallet provider too
        if (activeNetwork === network) {
          disconnect();
        }
      }
      
      // Update local state
      setWallets(prev => ({
        ...prev,
        [network]: null
      }));
      
      toast.success(`${config.name} wallet disconnected`);
    } catch (error) {
      console.error(`❌ Failed to disconnect ${network}:`, error);
      toast.error(`Failed to disconnect ${config.name}`);
    }
  };

  const switchNetwork = async (from: ChainId, to: ChainId) => {
    const toConfig = NETWORK_CONFIGS[to];
    
    // If target is testnet and not connected, connect first
    if (to === 'basecamp' && !wallets[to]) {
      await connectWallet(to);
      return;
    }
    
    // For WalletConnect networks, just update active network
    setActiveNetwork(to);
    toast.info(`Switched to ${toConfig.name}`);
  };

  const getBestNetworkForAction = (action: string): ChainId => {
    const availableNetworks = ACTION_NETWORK_MAP[action] || ['base'];
    
    // Return first connected network, or first available
    for (const network of availableNetworks) {
      if (wallets[network]?.isConnected) {
        return network;
      }
    }
    
    return availableNetworks[0]; // Default to first option
  };

  // Context value
  const contextValue: WalletOrchestratorContextType = {
    wallets,
    activeNetwork,
    isConnecting,
    connectWallet,
    disconnectWallet,
    switchNetwork,
    getWallet: (network) => wallets[network],
    getBestNetworkForAction,
    isWalletConnected: (network) => !!wallets[network]?.isConnected,
    getAllConnectedNetworks: () => 
      Object.entries(wallets)
        .filter(([_, wallet]) => wallet?.isConnected)
        .map(([network]) => network as ChainId),
    getTotalBalanceUSD: () => 0 // TODO: Implement balance aggregation
  };

  return (
    <WalletOrchestratorContext.Provider value={contextValue}>
      {children}
    </WalletOrchestratorContext.Provider>
  );
}

// Hook
export function useWalletOrchestrator() {
  const context = useContext(WalletOrchestratorContext);
  if (!context) {
    throw new Error('useWalletOrchestrator must be used within WalletOrchestratorProvider');
  }
  return context;
}

// Export configs for use in other components
export { NETWORK_CONFIGS };