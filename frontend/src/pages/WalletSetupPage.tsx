import React, { useState } from 'react';
import { Shield, Copy, ExternalLink, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import Card from './Card';
import Button from './Button';
import { apiService } from '../services/apiService';
import { useAuth } from '../contexts/AuthContext';

interface WalletSetupProps {
  userId: string;
  onComplete: (wallet: { address: string }) => void;
}

const WalletSetup: React.FC<WalletSetupProps> = ({ userId, onComplete }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { kycStatus } = useAuth();
  const [wallet, setWallet] = useState<{ address: string } | null>(null);

  const createWallet = async () => {
    // Check if user has completed KYC
    if (kycStatus !== 'approved') {
      setError('Identity verification is required before creating a wallet');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Create wallet through API service
      const response = await apiService.request<{ success: boolean; address: string }>(
        '/payment-engine/create-wallet',
        'POST',
        { userId }
      );
      
      if (!response.success || !response.address) {
        throw new Error('Failed to create wallet');
      }
      
      setWallet({ address: response.address });
      onComplete({ address: response.address });
    } catch (err) {
      console.error('Wallet creation failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to create wallet');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card className="text-center py-8">
        <Loader2 className="h-12 w-12 text-blue-500 animate-spin mx-auto mb-4" />
        <h3 className="text-xl font-bold text-white mb-2">Creating Your Wallet</h3>
        <p className="text-gray-400">
          We're setting up your secure USDS wallet. This may take a moment...
        </p>
      </Card>
    );
  }

  if (wallet) {
    return (
      <Card className="text-center py-8">
        <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
          <CheckCircle className="h-8 w-8 text-green-500" />
        </div>
        <h3 className="text-xl font-bold text-white mb-2">Wallet Created Successfully</h3>
        
        <div className="bg-gray-800/50 rounded-lg p-4 mb-6 max-w-md mx-auto">
          <p className="text-sm text-gray-300 mb-4">Your new wallet address:</p>
          <div className="flex items-center bg-gray-700 rounded p-3 mb-2">
            <code className="text-green-400 text-xs break-all flex-1">{wallet.address}</code>
            <Button size="sm" variant="ghost" icon={Copy}>Copy</Button>
          </div>
          <p className="text-xs text-gray-400">
            This is your secure USDS wallet address. You can use it to send and receive USDS stablecoins.
          </p>
        </div>
        
        <div className="text-xs text-blue-400 bg-blue-500/10 p-3 rounded border border-blue-500/20 mt-2">
          💰 Remember to keep some USDS in your wallet for transaction fees
        </div>
        
        <div className="space-x-4">
          <Button variant="secondary" icon={ExternalLink}>
            View on Explorer
          </Button>
          <Button>
            Continue
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="text-center py-8">
        <Shield className="h-16 w-16 text-blue-500 mx-auto mb-4" />
        <h3 className="text-2xl font-bold text-white mb-4">Create Your Seamount Wallet</h3>
        <p className="text-gray-400 mb-8 max-w-lg mx-auto">
          You need a blockchain wallet to send and receive USDS stablecoins. Your wallet will be created on the Algorand blockchain for fast, secure transactions.
        </p>
        
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-6 max-w-md mx-auto">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-5 w-5 text-red-400" />
              <span className="text-red-400">{error}</span>
            </div>
          </div>
        )}
        
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 mb-6 max-w-md mx-auto">
          <div className="text-sm text-blue-400">
            <p className="mb-2"><strong>Your wallet features:</strong></p>
            <ul className="text-left space-y-1">
              <li>✅ Sub-second transaction confirmation</li>
              <li>✅ Low transaction fees (~$0.001)</li>
              <li>✅ Compatible with all African payment rails</li>
              <li>✅ Secured by Algorand blockchain</li>
            </ul>
          </div>
        </div>
        
        <Button
          onClick={createWallet}
          className="bg-gradient-to-r from-blue-600 to-purple-600 px-8"
        >
          Create My Wallet
        </Button>
      </div>
    </Card>
  );
};

export default WalletSetup;