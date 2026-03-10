// File: frontend/src/components/payments/SendForm.tsx
// ✅ PRODUCTION-READY: QR code scanning added
// ✅ Fee display and balance validation remain

import { useState, useEffect, useRef } from 'react';
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
  Activity,
  AlertTriangle,
  QrCode,
  X
} from 'lucide-react';
import { apiClient } from '@/config/api';
import { Html5Qrcode } from 'html5-qrcode';

// ============================================================================
// CHAIN ASSET GROUPS (unchanged)
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
  ],
  solana: [ 
    { value: 'SOL', label: 'Solana (SOL)', icon: '◎', description: 'Ultra-fast blockchain' },
    { value: 'USDT_SOLANA', label: 'Tether (Solana)', icon: '₮', description: 'USDT on Solana' },
    { value: 'USDC_SOLANA', label: 'USD Coin (Solana)', icon: '◎', description: 'USDC on Solana' },
  ]
};

const ALL_ASSETS = [
  ...ASSET_GROUPS.algorand,
  ...ASSET_GROUPS.bitcoin,
  ...ASSET_GROUPS.ethereum,
  ...ASSET_GROUPS.polygon,
  ...ASSET_GROUPS.tron,
  ...ASSET_GROUPS.solana
];

const CHAIN_NAMES: { [key: string]: string } = {
  'algorand': '🟢 Algorand',
  'bitcoin': '🟠 Bitcoin',
  'ethereum': '🔵 Ethereum',
  'polygon': '🟣 Polygon',
  'tron': '🔴 Tron',
  'solana': '🟣 Solana'
};

// ============================================================================
// ADDRESS VALIDATION PATTERNS
// ============================================================================
const ADDRESS_PATTERNS: { [key: string]: RegExp } = {
  algorand: /^[A-Z2-7]{58}$/,
  bitcoin: /^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$/,
  ethereum: /^0x[a-fA-F0-9]{40}$/,
  polygon: /^0x[a-fA-F0-9]{40}$/,
  tron: /^T[A-Za-z1-9]{33}$/,
  solana: /^[1-9A-HJ-NP-Za-km-z]{32,44}$/
};

// ============================================================================
// GET CHAIN FROM ASSET
// ============================================================================
const getChainFromAsset = (assetValue: string): string => {
  if (assetValue.includes('_')) {
    const chainPart = assetValue.split('_')[1]?.toLowerCase();
    const chainMap: { [key: string]: string } = {
      'tron': 'tron',
      'eth': 'ethereum',
      'polygon': 'polygon',
      'solana': 'solana',
      'algo': 'algorand'
    };
    return chainMap[chainPart] || 'algorand';
  }
  
  for (const [chain, assets] of Object.entries(ASSET_GROUPS)) {
    if (assets.some(a => a.value === assetValue)) {
      return chain;
    }
  }
  return 'algorand';
};

// ============================================================================
// NATIVE ASSET MAP
// ============================================================================
const getNativeAsset = (chain: string): string => {
  const map: Record<string, string> = {
    tron: 'TRX',
    algorand: 'ALGO',
    ethereum: 'ETH',
    polygon: 'MATIC',
    bitcoin: 'BTC',
    solana: 'SOL'
  };
  return map[chain] || 'ALGO';
};

// ============================================================================
// COMPONENT
// ============================================================================
interface SendFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SendForm({ open, onOpenChange }: SendFormProps) {
  const { balances, sendTransaction, loading: walletLoading, fetchBalances } = useWallet();

  useEffect(() => {
    if (open) {
      fetchBalances();
    }
  }, [open, fetchBalances]);
  
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

  // Fee state
  const [estimatedNetworkFee, setEstimatedNetworkFee] = useState<number>(0);
  const [seamountFeeNative, setSeamountFeeNative] = useState<number>(0);
  const [feeLoading, setFeeLoading] = useState(false);
  const [insufficientNative, setInsufficientNative] = useState(false);

  // QR scanner state
  const [showScanner, setShowScanner] = useState(false);
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const scannerContainerId = 'qr-reader';

  // Get chain from selected asset
  const selectedChain = getChainFromAsset(asset);
  const nativeAsset = getNativeAsset(selectedChain);
  const selectedAssetConfig = ALL_ASSETS.find(a => a.value === asset);
  
  // Get available balance
  const availableBalance = balances[asset]?.balance || 0;
  const nativeBalance = balances[nativeAsset]?.balance || 0;
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
  // FETCH FEE ESTIMATE
  // ============================================================================
  useEffect(() => {
    const fetchFeeEstimate = async () => {
      if (!amount || parseFloat(amount) <= 0) {
        setEstimatedNetworkFee(0);
        setSeamountFeeNative(0);
        return;
      }

      setFeeLoading(true);
      try {
        const response = await apiClient.post('/api/v1/fees/estimate', {
          chain: selectedChain,
          asset,
          amount: parseFloat(amount)
        });
        
        if (response.data.success) {
          setEstimatedNetworkFee(response.data.network_fee_native || 0);
          setSeamountFeeNative(response.data.seamount_fee_native || 0);
        } else {
          // Fallback to rough estimates
          const nativeFees: Record<string, number> = {
            tron: 1.1,
            algorand: 0.001,
            ethereum: 0.005,
            polygon: 0.01,
            bitcoin: 0.0005,
            solana: 0.00001
          };
          setEstimatedNetworkFee(nativeFees[selectedChain] || 0);
          const seamountPercent = 0.1; // 10% of network fee
          setSeamountFeeNative((nativeFees[selectedChain] || 0) * seamountPercent);
        }
      } catch (error) {
        console.error('Failed to fetch fee estimate:', error);
        // Fallback
        const nativeFees: Record<string, number> = {
          tron: 1.1,
          algorand: 0.001,
          ethereum: 0.005,
          polygon: 0.01,
          bitcoin: 0.0005,
          solana: 0.00001
        };
        setEstimatedNetworkFee(nativeFees[selectedChain] || 0);
        const seamountPercent = 0.1;
        setSeamountFeeNative((nativeFees[selectedChain] || 0) * seamountPercent);
      } finally {
        setFeeLoading(false);
      }
    };

    fetchFeeEstimate();
  }, [amount, asset, selectedChain]);

  // ============================================================================
  // CHECK IF USER HAS ENOUGH NATIVE BALANCE
  // ============================================================================
  useEffect(() => {
    if (!amount || parseFloat(amount) <= 0) {
      setInsufficientNative(false);
      return;
    }

    const totalNativeNeeded = estimatedNetworkFee + seamountFeeNative;
    setInsufficientNative(nativeBalance < totalNativeNeeded);
  }, [amount, estimatedNetworkFee, seamountFeeNative, nativeBalance]);

  // ============================================================================
  // QR SCANNER SETUP
  // ============================================================================
  const stopScanner = async () => {
    if (scannerRef.current) {
      try {
        const state = scannerRef.current.getState();
        // State 2 = SCANNING, State 3 = PAUSED
        if (state === 2 || state === 3) {
          await scannerRef.current.stop();
        }
      } catch (e) {
        console.debug('Scanner stop error (safe to ignore):', e);
      } finally {
        scannerRef.current = null;
      }
    }
  };

  useEffect(() => {
    if (!showScanner) {
      stopScanner();
      return;
    }

    const timer = setTimeout(async () => {
      const el = document.getElementById(scannerContainerId);
      if (!el) {
        console.error('QR container not found');
        toast.error('Could not initialize camera');
        setShowScanner(false);
        return;
      }

      try {
        const qr = new Html5Qrcode(scannerContainerId);
        scannerRef.current = qr;

        const cameras = await Html5Qrcode.getCameras();
        if (!cameras || cameras.length === 0) {
          toast.error('No camera found on this device');
          setShowScanner(false);
          return;
        }

        // Prefer back camera on mobile
        const camera = cameras.find(c =>
          c.label.toLowerCase().includes('back') ||
          c.label.toLowerCase().includes('rear') ||
          c.label.toLowerCase().includes('environment')
        ) || cameras[cameras.length - 1];

        await qr.start(
          camera.id,
          { fps: 10, qrbox: { width: 250, height: 250 }, aspectRatio: 1.0 },
          (decodedText) => {
            // Extract address — strip crypto URI prefix (e.g. "bitcoin:addr?amount=x")
            let address = decodedText.trim();
            if (address.includes(':')) {
              address = address.split(':')[1]?.split('?')[0] || address;
            }
            setRecipient(address.trim());
            toast.success('✅ Address scanned successfully');
            setShowScanner(false);
          },
          (err) => {
            // Per-frame errors are normal, suppress them
            console.debug('QR frame error:', err);
          }
        );
      } catch (err: any) {
        console.error('QR scanner failed to start:', err);
        if (err?.message?.includes('Permission')) {
          toast.error('Camera permission denied. Please allow camera access.');
        } else {
          toast.error('Failed to start scanner. Try again.');
        }
        setShowScanner(false);
      }
    }, 300);

    return () => {
      clearTimeout(timer);
      stopScanner();
    };
  }, [showScanner]);

  // ============================================================================
  // PROCEED TO CONFIRMATION
  // ============================================================================
  const handleProceedToConfirmation = () => {
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

    if (insufficientNative) {
      toast.error(`Insufficient ${nativeAsset} to cover fees. Please deposit more ${nativeAsset}.`);
      return;
    }

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
        toast.success(
          `✅ ${parseFloat(amount).toFixed(6)} ${asset} sent successfully!\n\nTx: ${result.tx_id?.substring(0, 12)}...`,
          {
            duration: 6000,
            icon: '🚀',
            style: { zIndex: 99999 }
          }
        );
        
        setTimeout(() => {
          setShowConfirmation(false);
          onOpenChange(false);
          setRecipient('');
          setAmount('');
          setMemo('');
        }, 1500);
        
      } else {
        setError(result.error || 'Transaction failed');
        toast.error(result.error || 'Transaction failed', {
          style: { zIndex: 99999 }
        });
      }
    } catch (err: any) {
      let errorMsg = err.response?.data?.detail || err.message || 'Transaction failed';
      
      // Enhanced error parsing
      if (errorMsg.includes('minimum') && errorMsg.includes('0.1 ALGO')) {
        errorMsg = `❌ NEW ACCOUNT ACTIVATION REQUIRED\n\n` +
                  `Algorand requires 0.1 ALGO minimum to activate new accounts.\n\n` +
                  `Current amount: ${amount} ALGO\n` +
                  `Please send at least 0.1 ALGO for first transaction.`;
      } else if (errorMsg.includes('opt-in') || errorMsg.includes('opted-in')) {
        errorMsg = `❌ ASSET OPT-IN REQUIRED\n\n` +
                  `Recipient must opt-in to ${asset} before receiving.\n\n` +
                  `Ask them to:\n` +
                  `1. Open their Algorand wallet\n` +
                  `2. Add ${asset} asset\n` +
                  `3. Try transaction again`;
      } else if (errorMsg.includes('Insufficient balance')) {
        errorMsg = `❌ INSUFFICIENT BALANCE\n\n` +
                  `Available: ${availableBalance.toFixed(6)} ${asset}\n` +
                  `Required: ${parseFloat(amount).toFixed(6)} ${asset} + fees`;
      } else if (errorMsg.includes('Invalid') && errorMsg.includes('address')) {
        errorMsg = `❌ INVALID RECIPIENT ADDRESS\n\n` +
                  `The ${selectedChain} address format is incorrect.\n` +
                  `Please double-check the address.`;
      }
      
      setError(errorMsg);
      toast.error(errorMsg, {
        duration: 10000,
        style: { zIndex: 99999, maxWidth: '500px', whiteSpace: 'pre-line' }
      });
    } finally {
      setLoading(false);
    }
  };

  // ============================================================================
  // RENDER: MAIN FORM
  // ============================================================================
  return (
    <>
      <Dialog open={open && !showConfirmation && !showScanner} onOpenChange={onOpenChange}>
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
              Send cryptocurrency via multi-chain networks. Fast, secure, and low-cost.
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

            {/* Recipient Address with QR Button */}
            <div className="space-y-2">
              <Label htmlFor="recipient" className="text-sm font-semibold text-gray-900 dark:text-white">
                Recipient Address
              </Label>
              <div className="flex gap-2">
                <Input
                  id="recipient"
                  placeholder={`Enter ${selectedChain} address`}
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  disabled={loading}
                  className={`flex-1 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-white h-12 text-base ${
                    validationError ? 'border-red-500 dark:border-red-500' : ''
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowScanner(true)}
                  className="h-12 w-12 flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                  title="Scan QR Code"
                >
                  <QrCode className="h-5 w-5" />
                </button>
              </div>
              
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
                Crypto Amount
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

            {/* Fee Estimate */}
            {(estimatedNetworkFee > 0 || seamountFeeNative > 0) && (
              <div className="space-y-2 bg-gray-50 dark:bg-gray-900/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-2 mb-2">
                  <Info className="h-4 w-4 text-blue-500" />
                  <span className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wide">Fee Estimate</span>
                </div>
                
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Network Fee:</span>
                  <span className="font-mono text-gray-900 dark:text-white">
                    {estimatedNetworkFee.toFixed(6)} {nativeAsset}
                  </span>
                </div>
                
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Seamount Fee:</span>
                  <span className="font-mono text-green-600 dark:text-green-400 font-medium">
                    {seamountFeeNative.toFixed(6)} {nativeAsset}
                  </span>
                </div>
                
                <div className="flex justify-between text-sm font-semibold border-t border-gray-200 dark:border-gray-700 pt-2 mt-1">
                  <span className="text-gray-800 dark:text-gray-200">Total Cost:</span>
                  <span className="text-gray-900 dark:text-white">
                    {(parseFloat(amount) + estimatedNetworkFee + seamountFeeNative).toFixed(6)} {selectedAssetConfig?.value.split('_')[0]}
                  </span>
                </div>
                
                {/* Insufficient Balance Warning */}
                {insufficientNative && (
                  <div className="flex items-start gap-2 mt-3 p-2 bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-800 rounded">
                    <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-red-800 dark:text-red-300">
                      <span className="font-bold">Insufficient {nativeAsset} balance.</span> You need additional{' '}
                      {(estimatedNetworkFee + seamountFeeNative - nativeBalance).toFixed(6)} {nativeAsset} to cover fees.
                    </div>
                  </div>
                )}
                
                {feeLoading && (
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <div className="animate-spin rounded-full h-3 w-3 border-b border-gray-500"></div>
                    Estimating fees...
                  </div>
                )}
              </div>
            )}

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
              disabled={loading || !recipient || !amount || parseFloat(amount) <= 0 || !!validationError || availableBalance === 0 || insufficientNative}
              className="w-full sm:w-auto h-12 px-8 text-base font-bold bg-green-600 hover:bg-green-700 text-white transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:transform-none"
            >
              Review Transaction
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* QR SCANNER MODAL */}
      <Dialog open={showScanner} onOpenChange={(open) => { if (!open) setShowScanner(false); }}>
        <DialogContent
          className="sm:max-w-[500px] max-w-[95vw] bg-white dark:bg-gray-900 border-2 border-gray-300 dark:border-gray-600"
          style={{ zIndex: 2000 }}
        >
          <DialogHeader className="border-b border-gray-200 dark:border-gray-700 pb-4">
            <DialogTitle className="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-white">
              <QrCode className="h-6 w-6 text-blue-500" />
              Scan Wallet QR Code
            </DialogTitle>
            <DialogDescription className="text-gray-600 dark:text-gray-400 text-sm">
              Point your camera at a wallet QR code. Address will auto-fill.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4 flex flex-col items-center gap-3">
            {/* Scanner viewport */}
            <div
              id={scannerContainerId}
              className="w-full rounded-xl overflow-hidden border-2 border-blue-500 dark:border-blue-400"
              style={{ minHeight: '300px', background: '#000' }}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              Supports Bitcoin, Ethereum, Algorand, Tron, Polygon, Solana QR codes
            </p>
          </div>

          <DialogFooter className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <Button
              variant="outline"
              onClick={() => setShowScanner(false)}
              className="w-full h-12 px-6 text-base font-semibold border-2 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <X className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* CONFIRMATION MODAL */}
      <Dialog open={showConfirmation} onOpenChange={setShowConfirmation}>
        <DialogContent className="sm:max-w-[500px] max-w-[95vw] max-h-[90vh] overflow-y-auto bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600">
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

              {/* Fee Breakdown */}
              <div className="border-t border-green-300 dark:border-green-700 pt-3 mt-3 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Network Fee:</span>
                  <span className="font-mono text-gray-900 dark:text-white">
                    {estimatedNetworkFee.toFixed(6)} {nativeAsset}
                  </span>
                </div>
                
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Seamount Fee:</span>
                  <span className="font-mono text-green-600 dark:text-green-400 font-medium">
                    {seamountFeeNative.toFixed(6)} {nativeAsset}
                  </span>
                </div>
                
                <div className="flex justify-between text-sm font-semibold border-t border-green-300 dark:border-green-700 pt-2 mt-1">
                  <span className="text-gray-800 dark:text-gray-200">Total to Deduct:</span>
                  <span className="text-gray-900 dark:text-white">
                    {(parseFloat(amount) + estimatedNetworkFee + seamountFeeNative).toFixed(6)} {selectedAssetConfig?.value.split('_')[0]}
                  </span>
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
              disabled={loading || insufficientNative}
              className="w-full sm:w-auto h-12 px-8 text-base font-bold bg-green-600 hover:bg-green-700 text-white transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Sending...
                </>
              ) : insufficientNative ? (
                <>
                  <AlertTriangle className="mr-2 h-5 w-5" />
                  Insufficient Funds
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