// File: frontend/src/components/payments/SendForm.tsx
// ✨ PRODUCTION-READY: Multi-chain Send with Confirmation Modal

import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { useWallet } from '@/contexts/WalletContext';
import { Button } from '@/components/ui/button.tsx';
import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog.tsx';
import { Alert, AlertDescription } from '@/components/ui/alert.tsx';
import { 
  Loader2, 
  Send, 
  AlertCircle, 
  CheckCircle2, 
  ArrowRight,
  Info,
  Activity
} from 'lucide-react';

// ============================================================================
// CHAIN ASSET GROUPS (Matching your WalletDetailModal pattern)
// ============================================================================
const ASSET_GROUPS = {
  algorand: [
    { value: 'ALGO', label: 'Algorand (ALGO)', icon: 'Ⱥ', description: 'Fast & low-cost blockchain' },
    { value: 'USDT', label: 'Tether (Algorand)', icon: '₮', description: 'Stablecoin on Algorand' },
    { value: 'USDCa', label: 'USD Coin (USDCa)', icon: '◎', description: 'Algorand native stablecoin' },
    { value: 'goBTC', label: 'Wrapped Bitcoin', icon: '₿', description: 'Bitcoin on Algorand' },
    { value: 'goETH', label: 'Wrapped Ethereum', icon: 'Ξ', description: 'Ethereum on Algorand' },
  ],
  bitcoin: [
    { value: 'BTC', label: 'Bitcoin (BTC)', icon: '₿', description: 'Original cryptocurrency' },
  ],
  ethereum: [
    { value: 'ETH', label: 'Ethereum (ETH)', icon: 'Ξ', description: 'Smart contract platform' },
    { value: 'USDT_ETH', label: 'Tether (Ethereum)', icon: '₮', description: 'USDT on Ethereum' },
    { value: 'USDC_ETH', label: 'USD Coin (Ethereum)', icon: '◎', description: 'USDC on Ethereum' },
  ],
  polygon: [
    { value: 'MATIC', label: 'Polygon (MATIC)', icon: '⬣', description: 'Ethereum scaling solution' },
    { value: 'USDT_POLYGON', label: 'Tether (Polygon)', icon: '₮', description: 'USDT on Polygon' },
    { value: 'USDC_POLYGON', label: 'USD Coin (Polygon)', icon: '◎', description: 'USDC on Polygon' },
  ],
  tron: [
    { value: 'TRX', label: 'TRON (TRX)', icon: '⚡', description: 'High-throughput blockchain' },
    { value: 'USDT_TRON', label: 'Tether (Tron)', icon: '₮', description: 'USDT on Tron' },
  ]
};

// Get available balance for selected asset - use the exact symbol from API
const availableBalance = balances[asset]?.balance || 0;
const balanceUSD = balances[asset]?.usd_value || 0;

// ADD DEBUG LOGGING:
console.log('🔍 SendForm Debug:', {
  selectedAsset: asset,
  availableBalance,
  balanceUSD,
  allBalances: balances
});

const ALL_ASSETS = [
  ...ASSET_GROUPS.algorand,
  ...ASSET_GROUPS.bitcoin,
  ...ASSET_GROUPS.ethereum,
  ...ASSET_GROUPS.polygon,
  ...ASSET_GROUPS.tron
];

const CHAIN_NAMES: { [key: string]: string } = {
  'algorand': '🟢 Algorand',
  'bitcoin': '🟠 Bitcoin',
  'ethereum': '🔵 Ethereum',
  'polygon': '🟣 Polygon',
  'tron': '🔴 Tron'
};

// ============================================================================
// ADDRESS VALIDATION PATTERNS
// ============================================================================
const ADDRESS_PATTERNS: { [key: string]: RegExp } = {
  algorand: /^[A-Z2-7]{58}$/,
  bitcoin: /^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$/,
  ethereum: /^0x[a-fA-F0-9]{40}$/,
  polygon: /^0x[a-fA-F0-9]{40}$/,
  tron: /^T[A-Za-z1-9]{33}$/
};

// ============================================================================
// GET CHAIN FROM ASSET
// ============================================================================
const getChainFromAsset = (assetValue: string): string => {
  for (const [chain, assets] of Object.entries(ASSET_GROUPS)) {
    if (assets.some(a => a.value === assetValue)) {
      return chain;
    }
  }
  return 'algorand';
};

// ============================================================================
// COMPONENT
// ============================================================================
interface SendFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SendForm({ open, onOpenChange }: SendFormProps) {
  const { balances, sendTransaction, loading: walletLoading } = useWallet();
  
  // Form state
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');
  const [asset, setAsset] = useState('ALGO');
  const [memo, setMemo] = useState('');
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [showConfirmation, setShowConfirmation] = useState(false);

  // Get chain from selected asset
  const selectedChain = getChainFromAsset(asset);
  const selectedAssetConfig = ALL_ASSETS.find(a => a.value === asset);
  
  // Get available balance
  const availableBalance = balances[asset]?.balance || 0;
  const balanceUSD = balances[asset]?.usd_value || 0;

  // ============================================================================
  // ADDRESS VALIDATION
  // ============================================================================
  useEffect(() => {
    if (recipient.length === 0) {
      setValidationError(null);
      return;
    }

    const pattern = ADDRESS_PATTERNS[selectedChain];
    if (pattern && !pattern.test(recipient)) {
      setValidationError(`Invalid ${selectedChain} address format`);
    } else {
      setValidationError(null);
    }
  }, [recipient, selectedChain]);

  // ============================================================================
  // PROCEED TO CONFIRMATION
  // ============================================================================
  const handleProceedToConfirmation = () => {
    // Validation
    if (!recipient || !amount || parseFloat(amount) <= 0) {
      toast.error('Please fill in all required fields');
      return;
    }

    if (validationError) {
      toast.error(validationError);
      return;
    }

    const amountNum = parseFloat(amount);
    if (amountNum > availableBalance) {
      toast.error(`Insufficient balance. Available: ${availableBalance.toFixed(6)} ${asset}`);
      return;
    }

    // Show confirmation modal
    setShowConfirmation(true);
  };

  // ============================================================================
  // EXECUTE TRANSACTION
  // ============================================================================
  const handleConfirmSend = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await sendTransaction({
        recipient,
        asset,
        amount: parseFloat(amount),
        memo: memo || undefined
      });

      if (result.success) {
        // Reset form
        setRecipient('');
        setAmount('');
        setMemo('');
        setShowConfirmation(false);
        
        // Close modal
        onOpenChange(false);
        
        toast.success('Transaction sent successfully! 🚀');
      } else {
        setError(result.error || 'Transaction failed');
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Transaction failed';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // ============================================================================
  // RENDER: MAIN FORM
  // ============================================================================
  return (
    <>
      <Dialog open={open && !showConfirmation} onOpenChange={onOpenChange}>
        <DialogContent 
          className="sm:max-w-[550px] max-w-[95vw] max-h-[90vh] overflow-y-auto bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600"
          style={{ zIndex: 1000 }}
        >
          <DialogHeader className="border-b pb-4">
            <DialogTitle className="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-white">
              <Send className="h-6 w-6 text-green-600" />
              Send Crypto
            </DialogTitle>
            <DialogDescription className="text-base text-gray-600 dark:text-gray-400 mt-2">
              Send cryptocurrency to any wallet address. Fast, secure, and low-cost.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-5 py-4">
            {/* Asset Selection */}
            <div className="space-y-2">
              <Label htmlFor="send-asset" className="text-sm font-semibold text-gray-900 dark:text-white">
                Asset to Send
              </Label>
              <Select value={asset} onValueChange={setAsset}>
                <SelectTrigger id="send-asset" className="w-full bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-white h-12">
                  <SelectValue placeholder="Select asset to send" />
                </SelectTrigger>
                <SelectContent className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 max-h-[400px] z-50">
                  {Object.entries(ASSET_GROUPS).map(([chain, assets]) => (
                    <div key={chain} className="py-2">
                      <div className="px-3 py-2 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide bg-gray-100 dark:bg-gray-900">
                        {CHAIN_NAMES[chain] || chain}
                      </div>
                      {assets.map((a) => (
                        <SelectItem 
                          key={a.value} 
                          value={a.value}
                          className="text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700 py-3 pl-8"
                        >
                          <div className="flex flex-col gap-1">
                            <div className="flex items-center gap-2">
                              <span className="text-xl">{a.icon}</span>
                              <span className="font-medium">{a.label}</span>
                            </div>
                            <span className="text-xs text-gray-600 dark:text-gray-400">{a.description}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </div>
                  ))}
                </SelectContent>
              </Select>
              
              {/* Balance Display */}
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Available Balance:</span>
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-green-400 animate-pulse" />
                  <span className="font-bold text-gray-900 dark:text-white">
                    {availableBalance.toFixed(6)} {selectedAssetConfig?.value.split('_')[0]}
                  </span>
                  {balanceUSD > 0 && (
                    <span className="text-gray-500 dark:text-gray-400">
                      (${balanceUSD.toFixed(2)})
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Recipient Address */}
            <div className="space-y-2">
              <Label htmlFor="recipient" className="text-sm font-semibold text-gray-900 dark:text-white">
                Recipient Address
              </Label>
              <Input
                id="recipient"
                placeholder={`Enter ${selectedChain} address`}
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                disabled={loading}
                className={`w-full bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-white h-12 text-base ${
                  validationError ? 'border-red-500 dark:border-red-500' : ''
                }`}
              />
              
              {validationError && (
                <div className="flex items-center gap-2 text-xs text-red-600 dark:text-red-400 font-medium">
                  <AlertCircle className="h-4 w-4" />
                  {validationError}
                </div>
              )}
              {!validationError && recipient.length > 0 && (
                <div className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400 font-medium">
                  <CheckCircle2 className="h-4 w-4" />
                  Valid {selectedChain} address ✓
                </div>
              )}
            </div>

            {/* Amount */}
            <div className="space-y-2">
              <Label htmlFor="amount" className="text-sm font-semibold text-gray-900 dark:text-white">
                Amount
              </Label>
              <div className="relative">
                <Input
                  id="amount"
                  type="number"
                  step="0.000001"
                  min="0"
                  placeholder="0.00"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  disabled={loading}
                  className="pr-20 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-white h-12 text-lg font-medium"
                />
                <button
                  type="button"
                  onClick={() => setAmount(availableBalance.toString())}
                  className="absolute right-3 top-1/2 -translate-y-1/2 px-3 py-1 text-xs font-bold bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                  disabled={loading || availableBalance === 0}
                >
                  MAX
                </button>
              </div>
            </div>

            {/* Memo (Optional) */}
            <div className="space-y-2">
              <Label htmlFor="memo" className="text-sm font-semibold text-gray-900 dark:text-white">
                Memo (Optional)
              </Label>
              <Input
                id="memo"
                placeholder="Add a note..."
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                disabled={loading}
                maxLength={100}
                className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-white h-12 text-base"
              />
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Optional message attached to this transaction
              </p>
            </div>

            {/* Info Alert */}
            <Alert className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-300 dark:border-blue-800">
              <Info className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <AlertDescription className="text-gray-900 dark:text-gray-100 text-sm font-medium">
                <strong className="text-blue-700 dark:text-blue-300">Smart Routing:</strong> Automatically routed through {CHAIN_NAMES[selectedChain]} network.
              </AlertDescription>
            </Alert>

            {/* Error Display */}
            {error && (
              <Alert variant="destructive" className="border-2">
                <AlertCircle className="h-5 w-5" />
                <AlertDescription className="font-medium">{error}</AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter className="border-t pt-4 flex-col sm:flex-row gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
              className="w-full sm:w-auto h-12 px-6 text-base font-semibold border-2 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              Cancel
            </Button>
            <Button
              onClick={handleProceedToConfirmation}
              disabled={loading || !recipient || !amount || parseFloat(amount) <= 0 || !!validationError || availableBalance === 0}
              className="w-full sm:w-auto h-12 px-8 text-base font-bold bg-green-600 hover:bg-green-700 text-white transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:transform-none"
            >
              Review Transaction
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* CONFIRMATION MODAL */}
      <Dialog open={showConfirmation} onOpenChange={setShowConfirmation}>
        <DialogContent className="sm:max-w-[500px] bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600">
          <DialogHeader className="border-b pb-4">
            <DialogTitle className="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-white">
              <CheckCircle2 className="h-6 w-6 text-green-600" />
              Confirm Transaction
            </DialogTitle>
            <DialogDescription className="text-gray-600 dark:text-gray-400">
              Please review the transaction details before confirming
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Transaction Summary Card */}
            <div className="rounded-xl bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-2 border-green-200 dark:border-green-700 p-4 space-y-3">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wide">Transaction Details</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">You're Sending:</span>
                <div className="text-right">
                  <div className="font-bold text-xl text-gray-900 dark:text-white">
                    {parseFloat(amount).toFixed(6)} {selectedAssetConfig?.value.split('_')[0]}
                  </div>
                  {balanceUSD > 0 && (
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      ≈ ${(parseFloat(amount) * (balanceUSD / availableBalance)).toFixed(2)} USD
                    </div>
                  )}
                </div>
              </div>

              <div className="border-t border-green-300 dark:border-green-700 pt-3">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Recipient Address:</div>
                <div className="font-mono text-sm text-gray-900 dark:text-white break-all bg-white/50 dark:bg-gray-900/50 p-2 rounded">
                  {recipient}
                </div>
              </div>

              {memo && (
                <div className="border-t border-green-300 dark:border-green-700 pt-3">
                  <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Memo:</div>
                  <div className="text-sm text-gray-900 dark:text-white bg-white/50 dark:bg-gray-900/50 p-2 rounded">
                    {memo}
                  </div>
                </div>
              )}

              <div className="border-t border-green-300 dark:border-green-700 pt-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Network:</span>
                  <span className="font-semibold text-gray-900 dark:text-white">{CHAIN_NAMES[selectedChain]}</span>
                </div>
              </div>
            </div>

            {/* Warning Alert */}
            <Alert className="bg-yellow-50 dark:bg-yellow-900/20 border-2 border-yellow-300 dark:border-yellow-800">
              <AlertCircle className="h-5 w-5 text-yellow-600" />
              <AlertDescription className="text-gray-900 dark:text-gray-100 text-sm font-medium">
                <strong>⚠️ Warning:</strong> Double-check the recipient address. Crypto transactions cannot be reversed.
              </AlertDescription>
            </Alert>
          </div>

          <DialogFooter className="border-t pt-4 flex-col-reverse sm:flex-row gap-3">
            <Button
              variant="outline"
              onClick={() => setShowConfirmation(false)}
              disabled={loading}
              className="w-full sm:w-auto h-12 px-6 text-base font-semibold"
            >
              Go Back
            </Button>
            <Button
              onClick={handleConfirmSend}
              disabled={loading}
              className="w-full sm:w-auto h-12 px-8 text-base font-bold bg-green-600 hover:bg-green-700 text-white transition-all duration-300 transform hover:scale-105 animate-pulse disabled:animate-none"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-5 w-5" />
                  Confirm & Send
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}