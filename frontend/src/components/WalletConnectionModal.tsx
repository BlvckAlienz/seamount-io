// 📂 FILE: frontend/src/components/WalletConnectionModal.tsx
// 🚨 MINIMAL VERSION - FOR EMERGENCY DEADLINE
import React, { useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

interface WalletConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (address: string) => void;
}

export const WalletConnectionModal: React.FC<WalletConnectionModalProps> = ({
  isOpen,
  onClose,
  onSuccess
}) => {
  const [connecting, setConnecting] = useState(false);

  const handleConnectMetaMask = async () => {
    if (typeof window.ethereum === 'undefined') {
      toast.error('Please install MetaMask');
      return;
    }
    
    setConnecting(true);
    try {
      const accounts = await window.ethereum.request({ 
        method: 'eth_requestAccounts' 
      });
      const address = accounts[0];
      
      onSuccess(address);
      onClose();
      toast.success('MetaMask connected!');
    } catch (error: any) {
      console.error('MetaMask connection failed:', error);
      if (error.code === 4001) {
        toast.error('Connection rejected by user');
      } else {
        toast.error('Failed to connect MetaMask');
      }
    } finally {
      setConnecting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-md w-full shadow-2xl">
        <div className="p-6 border-b border-slate-700 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white">Connect MetaMask</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
            disabled={connecting}
          >
            <X className="h-6 w-6" />
          </button>
        </div>
        
        <div className="p-6 text-center">
          <div className="text-6xl mb-4">🦊</div>
          <p className="text-gray-300 mb-6">Connect your MetaMask wallet to start betting</p>
          
          <button
            onClick={handleConnectMetaMask}
            disabled={connecting}
            className="w-full py-4 bg-gradient-to-r from-orange-600 to-yellow-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-orange-500/30 transition-all disabled:opacity-50 flex items-center justify-center gap-3"
          >
            {connecting ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Connecting...
              </>
            ) : (
              'Connect MetaMask'
            )}
          </button>
          
          <p className="text-gray-500 text-sm mt-4">
            Only MetaMask supported for now. Other wallets coming soon.
          </p>
        </div>
      </div>
    </div>
  );
};