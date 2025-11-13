// File: frontend/src/components/payments/SendForm.tsx
// Multi-chain payment form with WalletContext integration

import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { useWallet } from '@/contexts/WalletContext';
import { Button } from '@/components/ui/button.tsx';
import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.tsx';
import { Loader2, Send, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert.tsx';

// ============================================================================
// SUPPORTED ASSETS
// ============================================================================
const SUPPORTED_ASSETS = [
  { value: 'ALGO', label: 'Algorand (ALGO)', icon: 'Ⱥ', chain: 'algorand' },
  { value: 'USDCa', label: 'USD Coin (USDCa)', icon: '◎', chain: 'algorand' },
  { value: 'USDT', label: 'Tether (USDT)', icon: '₮', chain: 'tron' },
  { value: 'BTC', label: 'Bitcoin (BTC)', icon: '₿', chain: 'bitcoin' },
  { value: 'ETH', label: 'Ethereum (ETH)', icon: 'Ξ', chain: 'ethereum' },
  { value: 'MATIC', label: 'Polygon (MATIC)', icon: '⬣', chain: 'polygon' },
];

// ============================================================================
// ADDRESS VALIDATION
// ============================================================================
const validateAddress = (address: string, chain: string): boolean => {
  const patterns: { [key: string]: RegExp } = {
    algorand: /^[A-Z2-7]{58}$/,
    bitcoin: /^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$/,
    ethereum: /^0x[a-fA-F0-9]{40}$/,
    polygon: /^0x[a-fA-F0-9]{40}$/,
    tron: /^T[A-Za-z1-9]{33}$/
  };
  
  return patterns[chain]?.test(address) || false;
};

// ============================================================================
// COMPONENT
// ============================================================================
interface SendFormProps {
  onSuccess?: () => void;
}

export function SendForm({ onSuccess }: SendFormProps) {
  const { balances, sendTransaction, loading: walletLoading } = useWallet();
  
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');
  const [asset, setAsset] = useState('ALGO');
  const [memo, setMemo] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Get selected asset config
  const selectedAssetConfig = SUPPORTED_ASSETS.find(a => a.value === asset);
  const selectedChain = selectedAssetConfig?.chain || 'algorand';
  
  // Get available balance for selected asset
  const availableBalance = balances[asset]?.balance || 0;
  const balanceUSD = balances[asset]?.usd_value || 0;

  // ============================================================================
  // VALIDATION
  // ============================================================================
  useEffect(() => {
    if (recipient.length === 0) {
      setValidationError(null);
      return;
    }

    if (!validateAddress(recipient, selectedChain)) {
      setValidationError(`Invalid ${selectedChain} address format`);
    } else {
      setValidationError(null);
    }
  }, [recipient, selectedChain]);

  // ============================================================================
  // HANDLE SEND
  // ============================================================================
  const handleSend = async () => {
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
      toast.error(`Insufficient balance. Available: ${availableBalance} ${asset}`);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await sendTransaction({
        recipient,
        asset,
        amount: amountNum,
        memo: memo || undefined
      });

      if (result.success) {
        // Reset form
        setRecipient('');
        setAmount('');
        setMemo('');
        
        onSuccess?.();
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
  // RENDER
  // ============================================================================
  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Send className="h-5 w-5" />
          Send Crypto
        </CardTitle>
        <CardDescription>
          Send cryptocurrency across multiple chains
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Asset Selection */}
        <div className="space-y-2">
          <Label htmlFor="asset">Asset</Label>
          <Select value={asset} onValueChange={setAsset}>
            <SelectTrigger id="asset">
              <SelectValue placeholder="Select asset" />
            </SelectTrigger>
            <SelectContent>
              {SUPPORTED_ASSETS.map((a) => (
                <SelectItem key={a.value} value={a.value}>
                  <span className="flex items-center gap-2">
                    <span className="text-lg">{a.icon}</span>
                    {a.label}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {/* Balance Display */}
          <div className="text-sm text-muted-foreground">
            Available: {availableBalance.toFixed(4)} {asset}
            {balanceUSD > 0 && ` ($${balanceUSD.toFixed(2)})`}
          </div>
        </div>

        {/* Recipient Address */}
        <div className="space-y-2">
          <Label htmlFor="recipient">Recipient Address</Label>
          <Input
            id="recipient"
            placeholder={`Enter ${selectedChain} address`}
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            disabled={loading}
            className={validationError ? 'border-red-500' : ''}
          />
          {validationError && (
            <div className="flex items-center gap-1 text-xs text-red-500">
              <AlertCircle className="h-3 w-3" />
              {validationError}
            </div>
          )}
          {!validationError && recipient.length > 0 && (
            <div className="flex items-center gap-1 text-xs text-green-500">
              <CheckCircle2 className="h-3 w-3" />
              Valid {selectedChain} address
            </div>
          )}
        </div>

        {/* Amount */}
        <div className="space-y-2">
          <Label htmlFor="amount">Amount</Label>
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
            />
            <button
              type="button"
              onClick={() => setAmount(availableBalance.toString())}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-blue-500 hover:text-blue-600 font-medium"
              disabled={loading || availableBalance === 0}
            >
              MAX
            </button>
          </div>
        </div>

        {/* Memo (Optional) */}
        <div className="space-y-2">
          <Label htmlFor="memo">Memo (Optional)</Label>
          <Input
            id="memo"
            placeholder="Add a note..."
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
            disabled={loading}
            maxLength={100}
          />
        </div>

        {/* Error Display */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Send Button */}
        <Button
          onClick={handleSend}
          disabled={loading || walletLoading || !recipient || !amount || parseFloat(amount) <= 0 || !!validationError}
          className="w-full"
        >
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Sending...
            </>
          ) : (
            <>
              <Send className="mr-2 h-4 w-4" />
              Send {amount || '0'} {asset}
            </>
          )}
        </Button>

        {/* Fee Info */}
        <p className="text-xs text-muted-foreground text-center">
          Network fees apply. Transaction will be routed through {selectedChain}.
        </p>
      </CardContent>
    </Card>
  );
}