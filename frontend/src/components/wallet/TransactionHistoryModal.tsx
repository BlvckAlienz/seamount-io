// File: frontend/src/components/wallet/TransactionHistoryModal.tsx
import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/config/api';
import { 
  Loader2, 
  ExternalLink, 
  ArrowUpRight, 
  ArrowDownToLine,
  Clock,
  CheckCircle2,
  XCircle
} from 'lucide-react';
import toast from 'react-hot-toast';

interface Transaction {
  id: string;
  created_at: string;
  transaction_type: string;
  amount: number;
  asset: string;
  chain: string;
  txn_hash: string;
  to_address: string;
  status: string;
  network_fee: number;
  network_fee_asset: string;
  platform_fee: number;
  seamount_fee?: number;
  seamount_fee_asset?: string;
}

interface TransactionHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const CHAIN_ICONS: Record<string, string> = {
  algorand: '🔵',
  bitcoin: '🟠',
  ethereum: '💎',
  polygon: '🟣',
  tron: '🔴',
  solana: '🟢',
  xrp: '✨'
};

const CHAIN_EXPLORERS: Record<string, string> = {
  algorand: 'https://algoexplorer.io/tx/',
  bitcoin: 'https://blockstream.info/tx/',
  ethereum: 'https://etherscan.io/tx/',
  polygon: 'https://polygonscan.com/tx/',
  tron: 'https://tronscan.org/#/transaction/',
  solana: 'https://explorer.solana.com/tx/',
  xrp: 'https://livenet.xrpl.org/transactions/'
};

export const TransactionHistoryModal: React.FC<TransactionHistoryModalProps> = ({
  isOpen,
  onClose
}) => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    if (isOpen) {
      fetchTransactions();
    }
  }, [isOpen]);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/api/v1/transactions/blockchain-history');
      if (response.data.success) {
        setTransactions(response.data.transactions || []);
      }
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
      toast.error('Could not load transaction history');
    } finally {
      setLoading(false);
    }
  };

  const filteredTransactions = filter === 'all' 
    ? transactions 
    : transactions.filter(tx => tx.chain === filter);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getExplorerUrl = (chain: string, txHash: string) => {
    return `${CHAIN_EXPLORERS[chain] || 'https://etherscan.io/tx/'}${txHash}`;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[800px] max-w-[95vw] max-h-[90vh] overflow-y-auto bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 border-2 border-cyan-500/30 shadow-2xl">
        <DialogHeader className="border-b border-cyan-500/30 pb-4">
          <DialogTitle className="flex items-center gap-2 text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">
            <Clock className="h-6 w-6 text-cyan-400" />
            Transaction History
          </DialogTitle>
        </DialogHeader>

        {/* Filter Tabs */}
        <div className="flex flex-wrap gap-2 py-4 border-b border-cyan-500/20">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filter === 'all'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50'
                : 'bg-gray-800/50 text-gray-400 hover:text-cyan-300 border border-gray-700/50'
            }`}
          >
            All Chains
          </button>
          {Object.keys(CHAIN_ICONS).map(chain => (
            <button
              key={chain}
              onClick={() => setFilter(chain)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-1 ${
                filter === chain
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50'
                  : 'bg-gray-800/50 text-gray-400 hover:text-cyan-300 border border-gray-700/50'
              }`}
            >
              <span>{CHAIN_ICONS[chain]}</span>
              <span className="capitalize">{chain}</span>
            </button>
          ))}
        </div>

        {/* Transactions List */}
        <div className="space-y-3 py-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-8 w-8 text-cyan-400 animate-spin mb-4" />
              <p className="text-gray-400">Loading your transactions...</p>
            </div>
          ) : filteredTransactions.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">📭</div>
              <p className="text-gray-400">No transactions found</p>
              <p className="text-sm text-gray-600 mt-2">Your transaction history will appear here</p>
            </div>
          ) : (
            filteredTransactions.map((tx) => {
              // Determine if this is a send (outgoing) transaction
              const isSend = tx.transaction_type === 'send' || tx.transaction_type === 'transfer';
              const typeLabel = isSend ? 'Sent' : 'Received';
              const sign = isSend ? '-' : '+';

              return (
                <div
                  key={tx.id}
                  className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-cyan-500/20 rounded-xl p-4 hover:border-cyan-500/40 transition-all"
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    {/* Left: Chain & Type */}
                    <div className="flex items-center gap-3">
                      <div className="text-2xl">{CHAIN_ICONS[tx.chain]}</div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-semibold text-white">
                            {typeLabel}
                          </span>
                          {tx.status === 'completed' ? (
                            <CheckCircle2 className="h-4 w-4 text-green-400" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-400" />
                          )}
                        </div>
                        <div className="text-xs text-gray-500">{formatDate(tx.created_at)}</div>
                      </div>
                    </div>

                    {/* Middle: Amount & Asset */}
                    <div className="text-left md:text-center">
                      <div className="text-xl font-bold text-white">
                        {sign}{tx.amount.toFixed(6)} {tx.asset}
                      </div>
                      {tx.seamount_fee !== undefined && tx.seamount_fee > 0 && (
                        <div className="text-xs text-gray-500">
                          Seamount Fee: {tx.seamount_fee.toFixed(6)} {tx.seamount_fee_asset || ''}
                        </div>
                      )}
                    </div>

                    {/* Right: To Address & Explorer Link */}
                    <div className="text-left md:text-right">
                      <div className="text-sm text-gray-400">
                        To: {tx.to_address.slice(0, 8)}...{tx.to_address.slice(-6)}
                      </div>
                      <a
                        href={getExplorerUrl(tx.chain, tx.txn_hash)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors mt-1"
                      >
                        View on Explorer
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};