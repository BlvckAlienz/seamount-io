import React, { useState } from 'react';
import { Wallet, X, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card.tsx';
import { Button } from '@/components/ui/button.tsx';

interface AutomatedWalletConnectProps {
  isOpen: boolean;
  onClose: () => void;
  onWalletConnected: (address: string, provider: string) => void;
}

const AutomatedWalletConnect: React.FC<AutomatedWalletConnectProps> = ({
  isOpen,
  onClose,
  onWalletConnected
}) => {
  const [connecting, setConnecting] = useState(false);

  if (!isOpen) return null;

  const handleConnect = async () => {
    setConnecting(true);
    // TODO: Implement actual wallet connection logic
    setTimeout(() => {
      setConnecting(false);
      onClose();
    }, 1000);
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <Wallet className="h-6 w-6" />
            Connect Wallet
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <p className="text-gray-400 mb-6">
          Automated wallet connection coming soon.
        </p>

        <Button onClick={handleConnect} disabled={connecting} className="w-full">
          {connecting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Connecting...
            </>
          ) : (
            'Connect'
          )}
        </Button>
      </Card>
    </div>
  );
};

export default AutomatedWalletConnect;