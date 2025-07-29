import React from 'react';
import { DollarSign, AlertCircle, Info } from 'lucide-react';
import { useTransactionFees } from '../contexts/TransactionFeeContext';

interface UsdsFeeReminderProps {
  amount?: number;
  variant?: 'inline' | 'card' | 'alert';
  className?: string;
}

const UsdsFeeReminder: React.FC<UsdsFeeReminderProps> = ({
  amount = 0,
  variant = 'inline',
  className = ''
}) => {
  const { calculateFee, recommendedUsdsBalance, minRequiredUsds } = useTransactionFees();
  
  const fee = amount > 0 ? calculateFee(amount) : minRequiredUsds;
  const recommendedBalance = amount > 0 ? recommendedUsdsBalance(amount) : minRequiredUsds * 3;

  if (variant === 'inline') {
    return (
      <div className={`flex items-center text-xs text-blue-400 ${className}`}>
        <DollarSign className="h-3 w-3 mr-1" />
        <span>USDS fee: ${fee.toFixed(2)} • Keep min. ${recommendedBalance.toFixed(2)} USDS</span>
      </div>
    );
  }

  if (variant === 'alert') {
    return (
      <div className={`flex items-start p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg ${className}`}>
        <AlertCircle className="h-5 w-5 text-yellow-500 mr-2 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-white font-medium">USDS Required for Transaction Fees</p>
          <p className="text-xs text-gray-300 mt-1">
            All transaction fees are paid in USDS. For this transaction, you'll need approximately ${fee.toFixed(2)} USDS.
            We recommend maintaining at least ${recommendedBalance.toFixed(2)} USDS in your wallet.
          </p>
        </div>
      </div>
    );
  }

  // Card variant
  return (
    <div className={`p-4 bg-gradient-to-r from-blue-900/30 to-blue-800/10 rounded-lg border border-blue-700/30 ${className}`}>
      <div className="flex items-center mb-2">
        <Info className="h-5 w-5 text-blue-400 mr-2" />
        <h3 className="text-sm font-medium text-white">USDS Transaction Fees</h3>
      </div>
      <p className="text-xs text-gray-300 mb-3">
        All transactions on Seamount require USDS for fees. This ensures fast, reliable transfers across all supported countries.
      </p>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="p-2 bg-gray-800/50 rounded">
          <div className="text-gray-400">Current Fee:</div>
          <div className="text-blue-400 font-medium">${fee.toFixed(2)} USDS</div>
        </div>
        <div className="p-2 bg-gray-800/50 rounded">
          <div className="text-gray-400">Recommended Balance:</div>
          <div className="text-blue-400 font-medium">${recommendedBalance.toFixed(2)} USDS</div>
        </div>
      </div>
    </div>
  );
};

export default UsdsFeeReminder;