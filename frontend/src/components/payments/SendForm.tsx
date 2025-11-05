// File: frontend/src/components/payments/SendForm.tsx
/**
 * SendForm Component - Multi-chain crypto payments
 * Supports USDT, ALGO, BTC sends with KYC checks
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, Send, AlertCircle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface SendFormProps {
  onSuccess?: () => void
  onKYCRequired?: () => void
}

export function SendForm({ onSuccess, onKYCRequired }: SendFormProps) {
  const [recipient, setRecipient] = useState('')
  const [amount, setAmount] = useState('')
  const [asset, setAsset] = useState('USDT')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [quote, setQuote] = useState<any>(null)

  // Supported assets
  const ASSETS = [
    { value: 'USDT', label: 'Tether (USDT)', icon: '₮' },
    { value: 'USDCa', label: 'USD Coin (USDCa)', icon: '◎' },
    { value: 'ALGO', label: 'Algorand (ALGO)', icon: 'Ⱥ' },
    { value: 'BTC', label: 'Bitcoin (BTC)', icon: '₿' },
  ]

  // Get quote before sending
  const fetchQuote = async () => {
    if (!recipient || !amount || parseFloat(amount) <= 0) {
      return
    }

    try {
      const response = await api.post('/payments/quote', {
        recipient,
        asset,
        amount: parseFloat(amount),
      })

      setQuote(response.data)
      setError(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to get quote')
      setQuote(null)
    }
  }

  // Handle send transaction
  const handleSend = async () => {
    if (!recipient || !amount || parseFloat(amount) <= 0) {
      toast.error('Please fill in all fields')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await api.post('/payments/send', {
        recipient,
        asset,
        amount: parseFloat(amount),
      })

      if (response.data.kyc_required) {
        toast.warning('KYC verification required')
        onKYCRequired?.()
      } else {
        toast.success(`Successfully sent ${amount} ${asset} to ${recipient}`)
        
        // Reset form
        setRecipient('')
        setAmount('')
        setQuote(null)
        
        onSuccess?.()
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to send payment'
      setError(errorMsg)
      toast.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Send className="h-5 w-5" />
          Send Crypto
        </CardTitle>
        <CardDescription>
          Send cryptocurrency to any wallet address
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

        {/* Recipient Address */}
        <div className="space-y-2">
          <Label htmlFor="recipient">Recipient Address</Label>
          <Input
            id="recipient"
            placeholder="Enter wallet address or @username"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            disabled={loading}
          />
        </div>

        {/* Amount */}
        <div className="space-y-2">
          <Label htmlFor="amount">Amount</Label>
          <Input
            id="amount"
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
          <div className="rounded-lg bg-muted p-3 space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Network Fee:</span>
              <span className="font-medium">${quote.fee?.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Recipient Gets:</span>
              <span className="font-medium">
                {(parseFloat(amount) - (quote.fee || 0)).toFixed(4)} {asset}
              </span>
            </div>
            <div className="flex justify-between pt-1 border-t">
              <span className="text-muted-foreground">Total Cost:</span>
              <span className="font-semibold">{amount} {asset}</span>
            </div>
          </div>
        )}

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
          disabled={loading || !recipient || !amount || parseFloat(amount) <= 0}
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
          Network fees apply. KYC may be required for large amounts.
        </p>
      </CardContent>
    </Card>
  )
}