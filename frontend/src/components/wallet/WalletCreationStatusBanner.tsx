// File: frontend/src/components/wallet/WalletCreationStatusBanner.tsx
// 🚨 SHOWS ONLY FOR USERS WITH FAILED WALLET CREATION

import React, { useState } from 'react';
import { AlertTriangle, RefreshCw, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient } from '../../config/api';

interface WalletCreationStatusBannerProps {
  status: {
    overall_complete: boolean;
    summary: {
      total: number;
      successful: number;
      failed: number;
      pending: number;
    };
    retry_count: number;
    can_retry: boolean;
    chains: {
      [key: string]: {
        status: string;
        error?: string;
      };
    };
  };
  onRetrySuccess: () => void;
}

const WalletCreationStatusBanner: React.FC<WalletCreationStatusBannerProps> = ({
  status,
  onRetrySuccess
}) => {
  const [retrying, setRetrying] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Don't show if complete or dismissed
  if (status.overall_complete || dismissed) {
    return null;
  }

  const { successful, failed, pending } = status.summary;
  const failedChains = Object.entries(status.chains)
    .filter(([_, info]) => info.status === 'failed')
    .map(([chain]) => chain);

  const handleRetry = async () => {
    try {
      setRetrying(true);
      toast.loading('Retrying wallet creation...', { id: 'wallet-retry' });

      const response = await apiClient.post('/api/v1/wallet-creation/retry');

      if (response.data.success) {
        const successCount = Object.values(response.data.results).filter(
          (r: any) => r.success
        ).length;

        if (successCount === failedChains.length) {
          toast.success('All wallets created successfully!', { id: 'wallet-retry' });
          setTimeout(() => onRetrySuccess(), 1500);
        } else {
          toast.success(
            `${successCount} wallet(s) created. ${failedChains.length - successCount} still pending.`,
            { id: 'wallet-retry' }
          );
          onRetrySuccess();
        }
      } else {
        toast.error('Retry failed. Please try again later.', { id: 'wallet-retry' });
      }
    } catch (error: any) {
      console.error('Wallet retry error:', error);
      
      if (error?.response?.status === 429) {
        toast.error('Maximum retry attempts reached. Please contact support.', {
          id: 'wallet-retry'
        });
      } else {
        toast.error('Failed to retry wallet creation', { id: 'wallet-retry' });
      }
    } finally {
      setRetrying(false);
    }
  };

  const urgency = failed > 2 ? 'critical' : failed > 0 ? 'warning' : 'info';

  const styles = {
    critical: {
      bg: 'bg-red-900/20 border-red-500/50',
      text: 'text-red-300',
      icon: 'text-red-400',
      button: 'bg-red-600 hover:bg-red-700'
    },
    warning: {
      bg: 'bg-orange-900/20 border-orange-500/50',
      text: 'text-orange-300',
      icon: 'text-orange-400',
      button: 'bg-orange-600 hover:bg-orange-700'
    },
    info: {
      bg: 'bg-blue-900/20 border-blue-500/50',
      text: 'text-blue-300',
      icon: 'text-blue-400',
      button: 'bg-blue-600 hover:bg-blue-700'
    }
  }[urgency];

  return (
    <div
      className={`rounded-2xl border-2 p-6 mb-6 ${styles.bg} backdrop-blur-sm animate-in slide-in-from-top`}
    >
      <div className="flex items-start gap-4">
        <div className={`${styles.icon} mt-1`}>
          <AlertTriangle className="h-6 w-6" />
        </div>

        <div className="flex-1">
          <h3 className={`text-lg font-bold mb-2 ${styles.text}`}>
            {failed > 0
              ? '⚠️ Wallet Creation Incomplete'
              : 'ℹ️ Setting up your wallets...'}
          </h3>

          <p className={`text-sm mb-3 ${styles.text}`}>
            {successful} of {status.summary.total} blockchain wallets created successfully.{' '}
            {failed > 0 && (
              <>
                <strong>{failedChains.join(', ')}</strong> wallet
                {failedChains.length > 1 ? 's' : ''} failed due to network issues.
              </>
            )}
          </p>

          {/* Progress Bar */}
          <div className="w-full bg-gray-700 rounded-full h-2 mb-4">
            <div
              className={`h-2 rounded-full transition-all ${
                urgency === 'critical'
                  ? 'bg-red-500'
                  : urgency === 'warning'
                  ? 'bg-orange-500'
                  : 'bg-blue-500'
              }`}
              style={{ width: `${(successful / status.summary.total) * 100}%` }}
            />
          </div>

          {/* Failed Chains Detail */}
          {failed > 0 && (
            <div className="bg-gray-800/50 rounded-lg p-3 mb-4">
              <h4 className="text-sm font-semibold text-gray-300 mb-2">
                Failed Wallets:
              </h4>
              <div className="space-y-2">
                {Object.entries(status.chains)
                  .filter(([_, info]) => info.status === 'failed')
                  .map(([chain, info]) => (
                    <div key={chain} className="flex items-start gap-2 text-xs">
                      <span className="text-red-400">❌</span>
                      <div>
                        <span className="font-medium text-gray-300 capitalize">
                          {chain}
                        </span>
                        {info.error && (
                          <p className="text-gray-500 mt-1">{info.error}</p>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-3">
            {status.can_retry && (
              <button
                onClick={handleRetry}
                disabled={retrying}
                className={`flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed ${styles.button}`}
              >
                <RefreshCw
                  className={`h-4 w-4 ${retrying ? 'animate-spin' : ''}`}
                />
                {retrying ? 'Retrying...' : 'Retry Now'}
              </button>
            )}

            <button
              onClick={() => setDismissed(true)}
              className="text-sm text-gray-400 hover:text-gray-300 underline"
            >
              Dismiss for now
            </button>

            {status.retry_count > 3 && (
              <span className="text-xs text-gray-500 ml-auto">
                Retried {status.retry_count} times
              </span>
            )}
          </div>

          {/* Help Text */}
          <p className="text-xs text-gray-500 mt-4">
            💡 Wallet creation may fail due to temporary network issues. You can retry
            anytime or contact support if issues persist.
          </p>
        </div>

        {/* Close Button */}
        <button
          onClick={() => setDismissed(true)}
          className="text-gray-400 hover:text-gray-300 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
};

export default WalletCreationStatusBanner;