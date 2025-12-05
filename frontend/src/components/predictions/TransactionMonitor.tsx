import React, { useState, useEffect } from 'react';
import { CheckCircle, Clock, AlertCircle, ExternalLink, Loader, Zap } from 'lucide-react';

// ✅ ADD THIS IMPORT
import { supabase } from '@/lib/supabase';

interface TransactionMonitorProps {
  betId: string;
  txHash: string;
  onConfirmed: () => void;
}

export const TransactionMonitor: React.FC<TransactionMonitorProps> = ({ 
  betId, 
  txHash, 
  onConfirmed 
}) => {
  const [status, setStatus] = useState<'pending' | 'confirmed' | 'failed'>('pending');
  const [confirmations, setConfirmations] = useState(0);
  const [blockNumber, setBlockNumber] = useState<number | null>(null);
  const [explorerUrl, setExplorerUrl] = useState('');
  const [elapsed, setElapsed] = useState(0);

useEffect(() => {
  let pollInterval: NodeJS.Timeout;
  let timeInterval: NodeJS.Timeout;

  const pollStatus = async () => {
    try {
      // Auto-detect if this is a bet or claim transaction
      const endpoint = txHash.startsWith('0x') && betId.includes('-')
        ? `/api/v1/predictions/bet/${betId}/status`
        : `/api/v1/predictions/claim/${betId}/status`;

      const response = await fetch(endpoint, {
        headers: {
          'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`
        }
      });

      const data = await response.json();

      if (data.success) {
        setStatus(data.status);
        setConfirmations(data.confirmations || 0);
        setBlockNumber(data.block_number || null);
        setExplorerUrl(data.explorer_url || '');

        if (data.status === 'confirmed') {
          clearInterval(pollInterval);
          clearInterval(timeInterval);
          
          // ✅ TRIGGER IMMEDIATE REFRESH
          onConfirmed();
          
          // ✅ FORCE PARENT TO RE-FETCH DATA
          setTimeout(() => {
            window.location.reload(); // Nuclear option but guarantees sync
          }, 2000);
        } else if (data.status === 'failed') {
          clearInterval(pollInterval);
          clearInterval(timeInterval);
        }
      }
    } catch (error) {
      console.error('Status poll failed:', error);
    }
  };

  // Poll every 2 seconds
  pollInterval = setInterval(pollStatus, 2000);
  pollStatus(); // Initial poll

  // Track elapsed time
  timeInterval = setInterval(() => {
    setElapsed(prev => prev + 1);
  }, 1000);

  return () => {
    clearInterval(pollInterval);
    clearInterval(timeInterval);
  };
}, [betId, onConfirmed]);

  const getStatusConfig = () => {
    switch (status) {
      case 'confirmed':
        return {
          icon: <CheckCircle className="w-6 h-6 text-green-400" />,
          title: '✅ Transaction Confirmed',
          description: 'Your bet is now live on-chain',
          gradient: 'from-green-500/20 to-emerald-500/20',
          border: 'border-green-500/50',
          pulse: false
        };
      case 'failed':
        return {
          icon: <AlertCircle className="w-6 h-6 text-red-400" />,
          title: '❌ Transaction Failed',
          description: 'Your bet was rejected by the network',
          gradient: 'from-red-500/20 to-rose-500/20',
          border: 'border-red-500/50',
          pulse: false
        };
      default:
        return {
          icon: <Loader className="w-6 h-6 text-blue-400 animate-spin" />,
          title: '⏳ Broadcasting Transaction',
          description: 'Waiting for blockchain confirmation...',
          gradient: 'from-blue-500/20 to-cyan-500/20',
          border: 'border-blue-500/50',
          pulse: true
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className={`bg-gradient-to-br ${config.gradient} border ${config.border} rounded-2xl p-6 ${config.pulse ? 'animate-pulse' : ''}`}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        {config.icon}
        <div className="flex-1">
          <h3 className="text-lg font-bold text-white">{config.title}</h3>
          <p className="text-sm text-gray-400">{config.description}</p>
        </div>
      </div>

      {/* Transaction Details */}
      <div className="space-y-3 mb-4">
        {/* TX Hash */}
        <div className="flex items-center justify-between bg-slate-800/50 rounded-lg p-3">
          <span className="text-xs text-gray-400">Transaction</span>
          <a
            href={explorerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300 font-mono"
          >
            {txHash.slice(0, 10)}...{txHash.slice(-8)}
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>

        {/* Time Elapsed */}
        {status === 'pending' && (
          <div className="flex items-center justify-between bg-slate-800/50 rounded-lg p-3">
            <span className="text-xs text-gray-400">Time Elapsed</span>
            <span className="text-xs text-white font-semibold">{elapsed}s</span>
          </div>
        )}

        {status === 'confirmed' && blockNumber && (
          <>
            <div className="flex items-center justify-between bg-slate-800/50 rounded-lg p-3">
              <span className="text-xs text-gray-400">Block Number</span>
              <span className="text-xs text-white font-mono">#{blockNumber}</span>
            </div>
            <div className="flex items-center justify-between bg-slate-800/50 rounded-lg p-3">
              <span className="text-xs text-gray-400">Confirmations</span>
              <span className="text-xs text-green-400 font-bold">{confirmations}</span>
            </div>
          </>
        )}
      </div>

      {/* Real-Time Status Bar */}
      {status === 'pending' && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400">Network Processing</span>
            <span className="text-blue-400 flex items-center gap-1">
              <Zap className="w-3 h-3" />
              Live
            </span>
          </div>
          <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 animate-pulse" style={{ width: '70%' }} />
          </div>
        </div>
      )}

      {/* Success Confetti Effect */}
      {status === 'confirmed' && (
        <div className="text-center mt-4">
          <div className="text-4xl mb-2">🎉</div>
          <p className="text-xs text-green-400 font-semibold">Bet successfully placed on-chain!</p>
        </div>
      )}
    </div>
  );
};