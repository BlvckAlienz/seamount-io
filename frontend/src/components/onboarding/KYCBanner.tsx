// File: frontend/src/components/onboarding/KYCBanner.tsx

import React from 'react';
import { AlertTriangle, Shield } from 'lucide-react';

interface Props {
  cumulativeVolume: number;
  limit: number;
  kycStatus: string;
  onVerify: () => void;
}

export const KYCBanner: React.FC<Props> = ({ cumulativeVolume, limit, kycStatus, onVerify }) => {
  if (kycStatus === 'verified') return null;
  
  const remaining = Math.max(0, limit - cumulativeVolume);
  const percentUsed = (cumulativeVolume / limit) * 100;
  
  // Urgency levels
  const urgency = 
    remaining <= 500 ? 'critical' :
    remaining <= 1000 ? 'warning' : 'info';
  
  const styles = {
    critical: {
      bg: 'bg-red-900/20 border-red-500',
      text: 'text-red-300',
      icon: 'text-red-400',
      button: 'bg-red-600 hover:bg-red-700'
    },
    warning: {
      bg: 'bg-orange-900/20 border-orange-500',
      text: 'text-orange-300',
      icon: 'text-orange-400',
      button: 'bg-orange-600 hover:bg-orange-700'
    },
    info: {
      bg: 'bg-blue-900/20 border-blue-500',
      text: 'text-blue-300',
      icon: 'text-blue-400',
      button: 'bg-blue-600 hover:bg-blue-700'
    }
  }[urgency];
  
  return (
    <div className={`rounded-xl border-l-4 p-4 mb-6 ${styles.bg} backdrop-blur-sm animate-in slide-in-from-top`}>
      <div className="flex items-start gap-3">
        <AlertTriangle className={`h-5 w-5 ${styles.icon} mt-0.5`} />
        
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <h4 className={`font-semibold ${styles.text}`}>
              {urgency === 'critical' ? '🚨 Transaction Limit Reached' :
               urgency === 'warning' ? '⚠️ Approaching Limit' :
               '💡 Unlock Unlimited Transactions'}
            </h4>
            <span className={`text-sm ${styles.text}`}>
              ${cumulativeVolume.toFixed(2)} / ${limit}
            </span>
          </div>
          
          <p className={`text-sm ${styles.text} mb-3`}>
            {urgency === 'critical' 
              ? 'Complete KYC verification to continue transacting'
              : `${remaining.toFixed(2)} remaining. Verify your identity for unlimited access.`}
          </p>
          
          {/* Progress Bar */}
          <div className="w-full bg-gray-700 rounded-full h-2 mb-3">
            <div
              className={`h-2 rounded-full transition-all ${
                urgency === 'critical' ? 'bg-red-500' :
                urgency === 'warning' ? 'bg-orange-500' : 'bg-blue-500'
              }`}
              style={{ width: `${Math.min(100, percentUsed)}%` }}
            />
          </div>
          
          <button
            onClick={onVerify}
            className={`px-4 py-2 rounded-lg text-white font-medium transition-all ${styles.button}`}
          >
            {urgency === 'critical' ? 'Verify Now (Required)' : 'Complete Verification'}
          </button>
        </div>
      </div>
    </div>
  );
};