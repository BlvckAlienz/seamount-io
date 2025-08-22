// File Location: frontend/src/pages/DashboardPage.tsx
// Description: The definitive user command center, merging portfolio, analytics, and wallet actions.

import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Activity, Send, RefreshCw, Shield } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import AdvancedChart from '../components/charts/AdvancedChart';
import { CardSkeleton, ChartSkeleton } from '../components/ui/LoadingSkeleton';
import { generateMockChartData } from '../data/mockData';
import { useWallet } from '../hooks/useWallet';
import { useMarketData } from '../hooks/useMarketData';
import { useAuth } from '../contexts/AuthContext';
import VerificationModal from '../components/VerificationModal';
import toast from 'react-hot-toast';

// A new component for the Send Money form, extracted for clarity
const SendMoneyForm = ({ onSend, loading }: { onSend: (to: string, amount: number, memo: string) => void, loading: boolean }) => {
    const [to, setTo] = useState('');
    const [amount, setAmount] = useState('');
    const [memo, setMemo] = useState('');
  
    const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault();
      onSend(to, parseFloat(amount), memo);
    };
  
    return (
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Recipient Address</label>
          <input
            type="text"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="w-full pl-3 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
            placeholder="Algorand Address"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Amount (USDS)</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full pl-3 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
            placeholder="0.00"
            required
            step="0.01"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Memo (Optional)</label>
          <input
            type="text"
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
            className="w-full pl-3 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
            placeholder="Dinner, rent, etc."
          />
        </div>
        <Button type="submit" loading={loading} icon={Send} className="w-full">
          Send Payment
        </Button>
      </form>
    );
};

const DashboardPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [chartData, setChartData] = useState(generateMockChartData(30));
  const [showVerificationModal, setShowVerificationModal] = useState(false);
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);
  
  // Use our new, unified hooks
  const { address, balance, isConnected, provisionWallet, loading: walletLoading } = useWallet();
  const { portfolio, assets, loading: marketLoading, error: marketError } = useMarketData();
  const { user, role } = useAuth();

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 1500); // Simulate initial page load
    return () => clearTimeout(timer);
  }, []);

  // Add this function to handle transaction requests
  const handleTransactionRequest = (action: () => void) => {
    if (role === 'alien') {
      setPendingAction(() => action);
      setShowVerificationModal(true);
      return false;
    }
    return true;
  };

  // Add the sendPayment function
  const sendPayment = async (to: string, amount: number, memo: string) => {
    const canProceed = handleTransactionRequest(() => sendPayment(to, amount, memo));
    if (!canProceed) return;
    
    try {
      // Your existing send payment logic here
      console.log(`Sending ${amount} USDS to ${to} with memo: ${memo}`);
      // await apiClient.post('/api/payments/send', { to, amount, memo });
      toast.success('Payment sent successfully!');
    } catch (error) {
      console.error('Payment failed:', error);
      toast.error('Payment failed. Please try again.');
    }
  };

  const formatCurrency = (amount: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  const formatPercentage = (percentage: number) => `${percentage >= 0 ? '+' : ''}${percentage.toFixed(2)}%`;

  if (loading || marketLoading) {
    return <CardSkeleton count={4} />; // Show loading skeleton
  }
  
  // If the user has no wallet, prompt them to create one.
  if (!isConnected && !walletLoading) {
      return (
          <Card className="text-center mt-10 max-w-lg mx-auto">
              <Shield className="mx-auto h-12 w-12 text-blue-500 mb-4" />
              <h2 className="text-2xl font-bold text-white mb-2">Create Your Secure Wallet</h2>
              <p className="text-gray-400 mb-6">A wallet is required to send, receive, and trade USDS. Let's set one up for you now.</p>
              <Button onClick={provisionWallet} loading={walletLoading}>
                  Provision Secure Wallet
              </Button>
          </Card>
      );
  }

  return (
    <div className="space-y-6">
      {/* Add a notification for unverified users */}
      {role === 'alien' && (
        <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-6">
          <p className="font-bold">Verification Required</p>
          <p>Complete identity verification to unlock all features including sending and receiving USDS.</p>
          <button 
            onClick={() => window.location.href = '/onboarding'}
            className="mt-2 bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600"
          >
            Complete Verification
          </button>
        </div>
      )}

      {/* KPI Cards from Analytics.tsx */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-sm">Total Balance</span>
            <DollarSign className="h-5 w-5 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white">{formatCurrency(portfolio?.totalBalance || 0)}</div>
        </Card>
        <Card>
            <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">USDS Balance</span>
                <Shield className="h-5 w-5 text-teal-400" />
            </div>
            <div className="text-2xl font-bold text-white">{formatCurrency(balance)}</div>
        </Card>
        <Card>
            <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">24h Change</span>
                <Activity className="h-5 w-5 text-green-400" />
            </div>
            <div className={`text-2xl font-bold ${portfolio?.dayChange >= 0 ? 'text-green-400' : 'text-red-400'}`}>{formatCurrency(portfolio?.dayChange || 0)}</div>
        </Card>
        <Card>
            <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">All-Time P&L</span>
                <TrendingUp className="h-5 w-5 text-purple-400" />
            </div>
            <div className={`text-2xl font-bold ${portfolio?.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>{formatCurrency(portfolio?.totalPnL || 0)}</div>
        </Card>
      </div>

      {/* Main Content Area: Chart and Wallet Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {/* Chart from Analytics.tsx */}
          <Card>
            <h3 className="text-lg font-semibold text-white mb-6">Portfolio Performance</h3>
            <AdvancedChart data={chartData} height={350} />
          </Card>
        </div>
        
        {/* Wallet Actions from Wallet.tsx */}
        <div className="space-y-6">
            <Card>
                <h3 className="text-lg font-semibold text-white mb-6">Send USDS</h3>
                <SendMoneyForm onSend={sendPayment} loading={walletLoading} />
            </Card>
             <Card>
                <h3 className="text-lg font-semibold text-white mb-4">Receive USDS</h3>
                <p className="text-sm text-gray-400 mb-2">Your Algorand Address:</p>
                <div className="p-2 bg-gray-900 rounded-md text-center">
                    <code className="text-xs text-teal-300 break-all">{address}</code>
                </div>
                {/* QR Code generation would go here */}
            </Card>
        </div>
      </div>

      {/* Add the VerificationModal component */}
      <VerificationModal
        isOpen={showVerificationModal}
        onClose={() => setShowVerificationModal(false)}
        actionDescription="send payments"
        onVerify={() => {
          setShowVerificationModal(false);
          if (pendingAction) {
            pendingAction();
          }
        }}
      />
    </div>
  );
};

export default DashboardPage;