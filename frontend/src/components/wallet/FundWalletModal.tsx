// File: frontend/src/components/wallet/FundWalletModal.tsx
/**
 * FundWalletModal Component - On-ramp fiat to crypto
 * Supports Cashramp, Paystack, Flutterwave
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Wallet, AlertCircle, CheckCircle2 } from 'lucide-react'

interface FundWalletModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function FundWalletModal({ open, onOpenChange }: FundWalletModalProps) {
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState('NGN')
  const [asset, setAsset] = useState('USDT')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [quote, setQuote] = useState<any>(null)

  const CURRENCIES = [
    { code: 'NGN', name: 'Nigerian Naira', symbol: '₦' },
    { code: 'KES', name: 'Kenyan Shilling', symbol: 'KSh' },
    { code: 'GHS', name: 'Ghanaian Cedi', symbol: 'GH₵' },
    { code: 'ZAR', name: 'South African Rand', symbol: 'R' },
  ]

  const ASSETS = [
    { value: 'USDT', label: 'Tether (USDT)', icon: '₮' },
    { value: 'USDCa', label: 'USD Coin (USDCa)', icon: '◎' },
    { value: 'ALGO', label: 'Algorand (ALGO)', icon: 'Ⱥ' },
  ]

  // Get quote for on-ramp
  const fetchQuote = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      return
    }

    try {
      const response = await api.post<any>('/onramp/quote', {
        amount: parseFloat(amount),
        currency,
        asset,
      })

      setQuote(response.data)
      setError(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to get quote')
      setQuote(null)
    }
  }

  // Handle fund wallet
  const handleFund = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await api.post<any>('/onramp/initialize', {
        amount: parseFloat(amount),
        currency,
        asset,
      })

      // Redirect to payment page
      if (response.data?.payment_url) {
        window.location.href = response.data.payment_url
      } else {
        throw new Error('No payment URL received')
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to initialize payment'
      setError(errorMsg)
      toast.error(errorMsg)
      setLoading(false)
    }
  }

  const selectedCurrency = CURRENCIES.find(c => c.code === currency)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wallet className="h-5 w-5" />
            Fund Wallet
          </DialogTitle>
          <DialogDescription>
            Buy crypto using your local currency
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Currency Selection */}
          <div className="space-y-2">
            <Label htmlFor="currency">Currency</Label>
            <Select value={currency} onValueChange={setCurrency}>
              <SelectTrigger id="currency">
                <SelectValue placeholder="Select currency" />
              </SelectTrigger>
              <SelectContent>
                {CURRENCIES.map((curr) => (
                  <SelectItem key={curr.code} value={curr.code}>
                    {curr.symbol} {curr.name} ({curr.code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Amount */}
          <div className="space-y-2">
            <Label htmlFor="amount">Amount</Label>
            <div className="relative">
              <span className="absolute left-3 top-2.5 text-muted-foreground">
                {selectedCurrency?.symbol}
              </span>
              <Input
                id="amount"
                type="number"
                step="100"
                min="0"
                placeholder="0.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                onBlur={fetchQuote}
                disabled={loading}
                className="pl-10"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Minimum: {selectedCurrency?.symbol}1,000
            </p>
          </div>

          {/* Asset to Receive */}
          <div className="space-y-2">
            <Label htmlFor="asset">Asset to Receive</Label>
            <Select value={asset} onValueChange={setAsset}>
              <SelectTrigger id="asset">
                <SelectValue placeholder="Select asset" />
              </SelectTrigger>
              <SelectContent>
                {ASSETS.map((a) => (
                  <SelectItem key={a.value} value={a.value}>
                    <span className="flex items-center gap-2">
                      <span className="text-lg">{a.icon}</span>
                      {a.label}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Quote Display */}
          {quote && (
            <div className="rounded-lg bg-muted p-3 space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Exchange Rate:</span>
                <span className="font-medium">
                  {selectedCurrency?.symbol}{quote.exchange_rate?.toFixed(2)}/USD
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Fee (1.8%):</span>
                <span className="font-medium">
                  {selectedCurrency?.symbol}{quote.fee?.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between pt-1 border-t">
                <span className="text-muted-foreground">You Receive:</span>
                <span className="font-semibold text-green-600">
                  {quote.crypto_amount?.toFixed(4)} {asset}
                </span>
              </div>
            </div>
          )}

          {/* Provider Info */}
          <Alert className="bg-blue-50 border-blue-200">
            <CheckCircle2 className="h-4 w-4 text-blue-600" />
            <AlertDescription className="text-blue-800">
              <strong>Payment via:</strong> Cashramp → Paystack → Flutterwave
              <br />
              <span className="text-xs">Automatic provider selection for best rates</span>
            </AlertDescription>
          </Alert>

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleFund}
            disabled={loading || !amount || parseFloat(amount) <= 0}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Wallet className="mr-2 h-4 w-4" />
                Fund {selectedCurrency?.symbol}{amount || '0'}
              </>
            )}
          </Button>
        </DialogFooter>

        <p className="text-xs text-muted-foreground text-center px-6">
          Crypto will be credited to your wallet within 5-10 minutes after payment.
        </p>
      </DialogContent>
    </Dialog>
  )
}