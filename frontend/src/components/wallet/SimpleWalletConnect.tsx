// File: frontend/src/components/wallet/SimpleWalletConnect.tsx
import React from 'react';
import { useWallet, Wallet, WalletId } from '@txnlab/use-wallet-react';
import { BsWallet2, BsCheckCircleFill, BsX } from 'react-icons/bs';

interface SimpleWalletConnectProps {
  isOpen: boolean;
  onClose: () => void;
  onWalletConnected: (address: string, provider: string) => void;
}

const SimpleWalletConnect: React.FC<SimpleWalletConnectProps> = ({
  isOpen,
  onClose,
  onWalletConnected
}) => {
  const { wallets, activeAddress } = useWallet();

  const handleWalletConnect = async (wallet: Wallet) => {
    try {
      const accounts = await wallet.connect();
      if (accounts && accounts.length > 0) {
        onWalletConnected(accounts[0], wallet.id);
        onClose();
      }
    } catch (error) {
      console.error('Wallet connection failed:', error);
    }
  };

  const isKmd = (wallet: Wallet) => wallet.id === WalletId.KMD;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-2xl max-w-md w-full p-6 border border-gray-700 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              <BsWallet2 className="text-cyan-400" />
              Connect Wallet
            </h3>
            <p className="text-gray-400 text-sm">Choose your wallet provider</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <BsX className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        {/* Wallet List */}
        <div className="space-y-3">
          {wallets?.map((wallet) => (
            <button
              key={wallet.id}
              onClick={() => handleWalletConnect(wallet)}
              className="w-full flex items-center gap-4 p-4 border border-gray-600 rounded-xl hover:border-cyan-500 hover:bg-gray-700/50 transition-all group"
              disabled={wallet.isActive}
            >
              {!isKmd(wallet) && (
                <img
                  src={wallet.metadata.icon}
                  alt={wallet.metadata.name}
                  className="w-8 h-8 object-contain rounded-md"
                />
              )}
              
              <div className="flex-1 text-left">
                <div className="font-semibold text-white">
                  {isKmd(wallet) ? 'LocalNet Wallet' : wallet.metadata.name}
                </div>
                <div className="text-sm text-gray-400">
                  {wallet.isActive ? 'Connected' : 'Click to connect'}
                </div>
              </div>

              {wallet.isActive ? (
                <BsCheckCircleFill className="text-cyan-400 text-xl" />
              ) : (
                <div className="text-gray-400 group-hover:text-cyan-400 transition-colors">
                  →
                </div>
              )}
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-gray-700">
          <p className="text-center text-gray-400 text-sm">
            Your wallet connection is secure and encrypted
          </p>
        </div>
      </div>
    </div>
  );
};

export default SimpleWalletConnect;