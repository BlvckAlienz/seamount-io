// File: frontend/src/components/wallet/FundWalletModal.tsx
/**
 * FundWalletModal Component - On-ramp fiat to crypto
 * Supports Cashramp, Paystack, Flutterwave
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
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
      <DialogContent className="sm:max-w-[425px] max-w-[95vw] max-h-[85vh] overflow-y-auto bg-white dark:bg-white border-2 border-gray-300">
        <DialogHeader className="border-b pb-4">
          <DialogTitle className="flex items-center gap-2 text-xl font-bold text-gray-900">
            <Wallet className="h-6 w-6 text-blue-600" />
            Fund Wallet
          </DialogTitle>
          <DialogDescription className="text-base text-gray-600 mt-2">
            Buy crypto using your local currency
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Currency Selection */}
          <div className="space-y-2">
            <Label htmlFor="currency" className="text-sm font-semibold text-gray-900">Currency</Label>
            <Select value={currency} onValueChange={setCurrency}>
              <SelectTrigger id="currency" className="w-full bg-gray-50 border-gray-300 text-gray-900 h-11">
                <SelectValue placeholder="Select currency" />
              </SelectTrigger>
              <SelectContent className="bg-white border-gray-300">
                {CURRENCIES.map((curr) => (
                  <SelectItem key={curr.code} value={curr.code} className="text-gray-900 hover:bg-gray-100">
                    {curr.symbol} {curr.name} ({curr.code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Amount */}
          <div className="space-y-2">
            <Label htmlFor="amount" className="text-sm font-semibold text-gray-900">Amount</Label>
            <div className="relative">
              <span className="absolute left-3 top-3 text-gray-600 font-medium">
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
                className="pl-10 bg-gray-50 border-gray-300 text-gray-900 h-11 text-base"
              />
            </div>
            <p className="text-sm text-gray-600 font-medium">
              Minimum: {selectedCurrency?.symbol}1,000
            </p>
          </div>

          {/* Asset to Receive */}
          <div className="space-y-2">
            <Label htmlFor="asset" className="text-sm font-semibold text-gray-900">Asset to Receive</Label>
            <Select value={asset} onValueChange={setAsset}>
              <SelectTrigger id="asset" className="w-full bg-gray-50 border-gray-300 text-gray-900 h-11">
                <SelectValue placeholder="Select asset" />
              </SelectTrigger>
              <SelectContent className="bg-white border-gray-300">
                {ASSETS.map((a) => (
                  <SelectItem key={a.value} value={a.value} className="text-gray-900 hover:bg-gray-100">
                    <span className="flex items-center gap-2">
                      <span className="text-lg">{a.icon}</span>
                      <span className="text-base font-medium">{a.label}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Quote Display */}
          {quote && (
            <div className="rounded-lg bg-blue-50 border-2 border-blue-200 p-4 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">Exchange Rate:</span>
                <span className="font-bold text-base text-gray-900">
                  {selectedCurrency?.symbol}{quote.exchange_rate?.toFixed(2)}/USD
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">Fee (1.8%):</span>
                <span className="font-bold text-base text-gray-900">
                  {selectedCurrency?.symbol}{quote.fee?.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t-2 border-blue-300">
                <span className="text-sm font-semibold text-gray-900">You Receive:</span>
                <span className="font-bold text-lg text-green-600">
                  {quote.crypto_amount?.toFixed(4)} {asset}
                </span>
              </div>
            </div>
          )}

          {/* Provider Info */}
          <Alert className="bg-blue-50 border-2 border-blue-300">
            <CheckCircle2 className="h-5 w-5 text-blue-600" />
            <AlertDescription className="text-gray-900 text-sm font-medium">
              <strong className="text-blue-700">Payment via:</strong> Cashramp → Paystack → Flutterwave
              <br />
              <span className="text-sm text-gray-600">Automatic provider selection for best rates</span>
            </AlertDescription>
          </Alert>

          {/* Error Display */}
          {error && (
            <Alert variant="destructive" className="bg-red-50 border-2 border-red-300">
              <AlertCircle className="h-5 w-5 text-red-600" />
              <AlertDescription className="text-red-900 font-medium">{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-3 pt-4 border-t">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
            className="w-full sm:w-auto h-11 text-base font-semibold border-2 border-gray-300 text-gray-700 hover:bg-gray-100"
          >
            Cancel
          </Button>
          <Button
            onClick={handleFund}
            disabled={loading || !amount || parseFloat(amount) <= 0}
            className="w-full sm:w-auto h-11 text-base font-semibold bg-blue-600 hover:bg-blue-700 text-white"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Wallet className="mr-2 h-5 w-5" />
                Fund {selectedCurrency?.symbol}{amount || '0'}
              </>
            )}
          </Button>
        </DialogFooter>

        <p className="text-sm text-gray-600 text-center px-2 pb-2 font-medium">
          Crypto will be credited to your wallet within 5-10 minutes after payment.
        </p>
      </DialogContent>
    </Dialog>
  )
}