// File: frontend/src/components/wallet/WithdrawModal.tsx
/**
 * WithdrawModal Component - Off-ramp crypto to bank
 * Converts USDT/ALGO to NGN and sends to bank account
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { apiClient } from '@/config/api'
import { Button } from '@/components/ui/button.tsx'
import { Input } from '@/components/ui/input.tsx'
import { Label } from '@/components/ui/label.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import { Loader2, ArrowDownToLine, AlertCircle, CheckCircle2 } from 'lucide-react'

interface WithdrawModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function WithdrawModal({ open, onOpenChange }: WithdrawModalProps) {
  const [amount, setAmount] = useState('')
  const [asset, setAsset] = useState('USDT')
  const [bankAccount, setBankAccount] = useState('')
  const [bankCode, setBankCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [quote, setQuote] = useState<any>(null)
  const [accountName, setAccountName] = useState<string | null>(null)

  // Nigerian Banks
  const NIGERIAN_BANKS = [
    { code: '044', name: 'Access Bank' },
    { code: '023', name: 'Citibank' },
    { code: '050', name: 'Ecobank' },
    { code: '084', name: 'Enterprise Bank' },
    { code: '070', name: 'Fidelity Bank' },
    { code: '011', name: 'First Bank' },
    { code: '214', name: 'First City Monument Bank' },
    { code: '058', name: 'Guaranty Trust Bank' },
    { code: '030', name: 'Heritage Bank' },
    { code: '301', name: 'Jaiz Bank' },
    { code: '082', name: 'Keystone Bank' },
    { code: '526', name: 'Parallex Bank' },
    { code: '076', name: 'Polaris Bank' },
    { code: '101', name: 'Providus Bank' },
    { code: '221', name: 'Stanbic IBTC Bank' },
    { code: '068', name: 'Standard Chartered Bank' },
    { code: '232', name: 'Sterling Bank' },
    { code: '100', name: 'Suntrust Bank' },
    { code: '032', name: 'Union Bank' },
    { code: '033', name: 'United Bank for Africa' },
    { code: '215', name: 'Unity Bank' },
    { code: '035', name: 'Wema Bank' },
    { code: '057', name: 'Zenith Bank' },
  ]

  const ASSETS = [
    { value: 'USDT', label: 'Tether (USDT)' },
    { value: 'USDCa', label: 'USD Coin (USDCa)' },
    { value: 'ALGO', label: 'Algorand (ALGO)' },
  ]

  // Verify bank account
  const verifyBankAccount = async () => {
    if (!bankAccount || !bankCode || bankAccount.length !== 10) {
      toast.error('Please enter a valid 10-digit account number')
      return
    }

    setVerifying(true)
    setError(null)
    setAccountName(null)

    try {
      const response = await apiClient.post('/api/v1/offramp/verify-account', {
        account_number: bankAccount,
        bank_code: bankCode,
      })

      setAccountName(response.data.account_name)
      toast.success(`Account verified: ${response.data.account_name}`)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to verify account'
      setError(errorMsg)
      toast.error(errorMsg)
    } finally {
      setVerifying(false)
    }
  }

  // Get withdrawal quote
  const fetchQuote = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      return
    }

    try {
      const response = await apiClient.post('/api/v1/offramp/quote', {
        amount: parseFloat(amount),
        asset,
      })

      setQuote(response.data)
      setError(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to get quote')
      setQuote(null)
    }
  }

  // Handle withdrawal
  const handleWithdraw = async () => {
    if (!accountName) {
      toast.error('Please verify your bank account first')
      return
    }

    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.post('/api/v1/offramp/withdraw', {
        amount: parseFloat(amount),
        asset,
        bank_code: bankCode,
        account_number: bankAccount,
      })

      toast.success('Withdrawal initiated! Funds will arrive in 1-2 hours')
      
      // Reset form
      setAmount('')
      setBankAccount('')
      setBankCode('')
      setAccountName(null)
      setQuote(null)
      
      onOpenChange(false)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Withdrawal failed'
      setError(errorMsg)
      toast.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px] max-w-[95vw] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <ArrowDownToLine className="h-5 w-5" />
            Withdraw to Bank
          </DialogTitle>
          <DialogDescription className="text-sm">
            Convert crypto to NGN and send to your bank account
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Asset Selection */}
          <div className="space-y-2">
            <Label htmlFor="withdraw-asset" className="text-sm font-medium">Asset to Withdraw</Label>
            <Select value={asset} onValueChange={setAsset}>
              <SelectTrigger id="withdraw-asset" className="w-full">
                <SelectValue placeholder="Select asset" />
              </SelectTrigger>
              <SelectContent>
                {ASSETS.map((a) => (
                  <SelectItem key={a.value} value={a.value}>
                    {a.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Amount */}
          <div className="space-y-2">
            <Label htmlFor="withdraw-amount" className="text-sm font-medium">Amount</Label>
            <Input
              id="withdraw-amount"
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              onBlur={fetchQuote}
              disabled={loading}
            />
          </div>

          {/* Quote Display */}
          {quote && (
            <div className="rounded-lg bg-muted p-3 space-y-1.5 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground text-xs">Exchange Rate:</span>
                <span className="font-medium text-sm">₦{quote.exchange_rate?.toFixed(2)}/USD</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground text-xs">NGN Amount:</span>
                <span className="font-medium text-sm">₦{quote.ngn_amount?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground text-xs">Fee (1.8%):</span>
                <span className="font-medium text-sm">₦{quote.fee?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center pt-1.5 border-t">
                <span className="text-muted-foreground text-xs">You Receive:</span>
                <span className="font-semibold text-green-600 text-sm">
                  ₦{quote.final_amount?.toLocaleString()}
                </span>
              </div>
            </div>
          )}

          {/* Bank Selection */}
          <div className="space-y-2">
            <Label htmlFor="bank" className="text-sm font-medium">Bank</Label>
            <Select value={bankCode} onValueChange={setBankCode}>
              <SelectTrigger id="bank" className="w-full">
                <SelectValue placeholder="Select bank" />
              </SelectTrigger>
              <SelectContent className="max-h-[200px]">
                {NIGERIAN_BANKS.map((bank) => (
                  <SelectItem key={bank.code} value={bank.code}>
                    {bank.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Account Number */}
          <div className="space-y-2">
            <Label htmlFor="account" className="text-sm font-medium">Account Number</Label>
            <div className="flex gap-2">
              <Input
                id="account"
                type="text"
                maxLength={10}
                placeholder="0123456789"
                value={bankAccount}
                onChange={(e) => {
                  setBankAccount(e.target.value)
                  setAccountName(null)
                }}
                disabled={loading || verifying}
                className="flex-1"
              />
              <Button
                type="button"
                variant="outline"
                onClick={verifyBankAccount}
                disabled={!bankAccount || !bankCode || verifying || loading}
                className="shrink-0"
              >
                {verifying ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Verify'
                )}
              </Button>
            </div>
          </div>

          {/* Account Name Display */}
          {accountName && (
            <Alert className="bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800 dark:text-green-200 text-sm">
                <strong>{accountName}</strong>
              </AlertDescription>
            </Alert>
          )}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm">{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
            className="w-full sm:w-auto"
          >
            Cancel
          </Button>
          <Button
            onClick={handleWithdraw}
            disabled={loading || !accountName || !amount || parseFloat(amount) <= 0}
            className="w-full sm:w-auto"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <ArrowDownToLine className="mr-2 h-4 w-4" />
                Withdraw ₦{quote?.final_amount?.toLocaleString() || '0'}
              </>
            )}
          </Button>
        </DialogFooter>

        <p className="text-xs text-muted-foreground text-center px-2 pb-2">
          Withdrawals typically arrive within 1-2 hours. A 1.8% fee applies.
        </p>
      </DialogContent>
    </Dialog>
  )
}