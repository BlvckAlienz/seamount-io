// File: frontend/src/components/wallet/WalletConnectCard.tsx
import React from 'react';
import { Link2, Check, ExternalLink, AlertCircle } from 'lucide-react';
import { useWeb3Modal } from '@web3modal/wagmi/react';
import { useWalletConnect } from '@/contexts/WalletConnectContext';
import toast from 'react-hot-toast';

interface WalletConnectCardProps {
  blockchain: 'base' | 'celo';
}

const WalletConnectCard: React.FC<WalletConnectCardProps> = ({ blockchain }) => {
  const { open } = useWeb3Modal();
  const {
    isConnected,
    address,
    chainId,
    chainName,
    connectWallet,
    disconnectWallet,
    connectedChains,
    isConnecting
  } = useWalletConnect();

  // Chain configuration
  const chainConfig = {
    base: {
      name: 'Base',
      id: 8453,
      icon: 'https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/eth.png',
      color: 'from-blue-500 to-blue-700',
      explorer: 'https://basescan.org',
      description: 'Ethereum L2 by Coinbase'
    },
    celo: {
      name: 'Celo',
      id: 42220,
      icon: 'https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/celo.png',
      color: 'from-green-500 to-emerald-700',
      explorer: 'https://celoscan.io',
      description: 'Mobile-first blockchain'
    }
  };

  const config = chainConfig[blockchain];
  const isChainConnected = connectedChains.includes(blockchain);
  const isCorrectChain = chainId === config.id;

  const handleConnect = async () => {
    try {
      if (!isConnected) {
        // Open WalletConnect modal to select wallet
        await open();
        toast.success('Select your wallet and switch to ' + config.name);
      } else if (!isCorrectChain) {
        // Wrong network
        toast.error(`Please switch to ${config.name} network in your wallet`);
      } else {
        // Correct network, save connection
        await connectWallet(blockchain);
      }
    } catch (error: any) {
      console.error('Connection error:', error);
      toast.error(error.message || 'Connection failed');
    }
  };

  const handleDisconnect = async () => {
    try {
      await disconnectWallet(blockchain);
    } catch (error: any) {
      console.error('Disconnection error:', error);
      toast.error('Disconnection failed');
    }
  };

  // ========== CONNECTED STATE ==========
  if (isChainConnected) {
    return (
      <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-green-500/50 hover:border-green-500 transition-all hover:shadow-xl hover:shadow-green-500/10">
        <div className="flex items-start justify-between mb-4">
          <div className={`p-3 rounded-xl bg-gradient-to-br ${config.color} text-white shadow-lg`}>
            <img src={config.icon} alt={config.name} className="w-6 h-6" />
          </div>
          <div className="text-right">
            <div className="flex items-center gap-1 text-green-400 text-sm font-medium mb-1">
              <Check className="w-4 h-4" />
              Connected
            </div>
            <div className="text-sm text-gray-400">External Wallet</div>
          </div>
        </div>

        <div className="mb-4">
          <div className="text-white font-semibold">{config.name}</div>
          <div className="text-gray-400 text-sm">{config.description}</div>
          {address && (
            <div className="text-gray-400 text-xs mt-2 flex items-center gap-2">
              <span className="truncate">{address.slice(0, 8)}...{address.slice(-6)}</span>
              
                href={`${config.explorer}/address/${address}`}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-blue-400 transition-colors"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}
        </div>

        <button
          onClick={handleDisconnect}
          className="w-full bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-lg font-medium text-sm transition-colors"
        >
          Disconnect
        </button>
      </div>
    );
  }

  // ========== NOT CONNECTED STATE ==========
  return (
    <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50 hover:border-blue-500/50 transition-all hover:shadow-lg cursor-pointer group">
      <div className="flex items-start justify-between mb-4">
        <div className={`p-3 rounded-xl bg-gradient-to-br ${config.color} text-white shadow-lg`}>
          <img src={config.icon} alt={config.name} className="w-6 h-6" />
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-400">Ready to Connect</div>
        </div>
      </div>

      <div className="mb-4">
        <div className="text-white font-semibold">{config.name}</div>
        <div className="text-gray-400 text-sm">{config.description}</div>
        <div className="text-gray-500 text-xs mt-2 flex items-center gap-2">
          <Link2 className="w-3 h-3" />
          Use existing wallet
        </div>
      </div>

      {/* Show warning if wrong network */}
      {isConnected && !isCorrectChain && (
        <div className="mb-3 p-2 bg-yellow-900/20 border border-yellow-600/30 rounded-lg flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-yellow-300">
            Switch to {config.name} network in your wallet
          </div>
        </div>
      )}

      <button
        onClick={handleConnect}
        disabled={isConnecting}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded-lg font-medium transition-colors group-hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isConnecting ? (
          <span className="flex items-center justify-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            Connecting...
          </span>
        ) : (
          <span className="flex items-center justify-center gap-2">
            <Link2 className="w-5 h-5" />
            Connect Wallet
          </span>
        )}
      </button>

      <div className="mt-3 text-center text-xs text-gray-500">
        MetaMask • Coinbase Wallet • MiniPay • Valora
      </div>
    </div>
  );
};

export default WalletConnectCard;