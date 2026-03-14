// FILE: frontend/src/components/p2p/PlaceOrderModal.tsx
// Order form shown when user clicks "Buy" on a merchant card.
// Mirrors Binance's order placement UX.

import { useState } from 'react'
import { v4 as uuidv4 } from 'uuid'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/lib/api'
import {
  Dialog, DialogContent, DialogHeader,
  DialogTitle, DialogDescription, DialogFooter
} from '@/components/ui/dialog.tsx'
import { Button } from '@/components/ui/button.tsx'
import { Input } from '@/components/ui/input.tsx'
import { Label } from '@/components/ui/label.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import { ShieldCheck, Clock, Star, AlertCircle, ArrowRight, Loader2 } from 'lucide-react'

interface Listing {
  id: string
  token: string
  fiat_currency: string
  price_per_token: number
  min_order_fiat: number
  max_order_fiat: number
  available_amount: number
  payment_methods: string[]
  terms: string | null
  p2p_merchants: {
    display_name: string
    verified: boolean
    total_orders: number
    completion_rate: number
    avg_release_time_mins: number
    is_online: boolean
  }
}

interface PlaceOrderModalProps {
  listing: Listing
  fiatCurrency: string
  tokenMeta: { icon: string; label: string } | undefined
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function PlaceOrderModal({
  listing, fiatCurrency, tokenMeta, open, onOpenChange
}: PlaceOrderModalProps) {
  const { user } = useAuth()
  const [fiatAmount,     setFiatAmount]     = useState('')
  const [paymentMethod,  setPaymentMethod]  = useState('')
  const [loading,        setLoading]        = useState(false)
  const [error,          setError]          = useState<string | null>(null)

  const tokenDisplay = listing.token.split('_')[0]
  const m = listing.p2p_merchants

  // Derived token amount from fiat input
  const tokenAmount = fiatAmount && parseFloat(fiatAmount) > 0
    ? (parseFloat(fiatAmount) / listing.price_per_token).toFixed(6)
    : '0.000000'

  const isAmountValid =
    fiatAmount &&
    parseFloat(fiatAmount) >= listing.min_order_fiat &&
    parseFloat(fiatAmount) <= listing.max_order_fiat

  // ── Submit Order ─────────────────────────────────────────
  const handlePlaceOrder = async () => {
    if (!isAmountValid || !paymentMethod) return
    if (!user?.id) { toast.error('Please log in first'); return }

    setLoading(true)
    setError(null)

    try {
      const { data } = await api.post('/api/p2p/orders', {
        idempotencyKey: uuidv4(),         // unique per attempt — prevents duplicates
        listingId: listing.id,
        buyerId: user.id,
        fiatAmount: parseFloat(fiatAmount),
        paymentMethod
      })

      toast.success('Order placed! Payment details are now visible.')
      onOpenChange(false)

      // Navigate to order detail page
      window.location.href = `/p2p/orders/${data.order.id}`
    } catch (err: any) {
      const msg = err.response?.data?.detail ?? err.message ?? 'Failed to place order'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px] max-w-[95vw] bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600">
        <DialogHeader className="border-b pb-4">
          <DialogTitle className="text-xl font-bold text-gray-900 dark:text-white">
            Buy {tokenDisplay}
          </DialogTitle>
          <DialogDescription className="text-gray-500 dark:text-gray-400">
            Review the merchant's terms and place your order.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">

          {/* Merchant Summary */}
          <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
            <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold">
              {m.display_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-1.5 font-semibold text-gray-900 dark:text-white text-sm">
                {m.display_name}
                {m.verified && <ShieldCheck className="h-3.5 w-3.5 text-blue-500" />}
              </div>
              <div className="flex gap-3 text-xs text-gray-500 mt-0.5">
                <span>{m.total_orders} orders</span>
                <span><Star className="h-3 w-3 inline text-yellow-400 mr-0.5" />{m.completion_rate.toFixed(1)}%</span>
                <span><Clock className="h-3 w-3 inline mr-0.5" />{m.avg_release_time_mins} min release</span>
              </div>
            </div>
            <div className="ml-auto text-right">
              <div className="text-lg font-bold text-gray-900 dark:text-white">
                {listing.price_per_token.toLocaleString()} {fiatCurrency}
              </div>
              <div className="text-xs text-gray-500">per {tokenDisplay}</div>
            </div>
          </div>

          {/* Merchant Terms */}
          {listing.terms && (
            <div className="text-xs text-gray-600 dark:text-gray-400 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
              <span className="font-bold text-yellow-700 dark:text-yellow-400">Merchant Terms: </span>
              {listing.terms}
            </div>
          )}

          {/* Fiat Amount Input */}
          <div className="space-y-1.5">
            <Label className="text-sm font-semibold text-gray-900 dark:text-white">
              I will pay
            </Label>
            <div className="relative">
              <Input
                type="number"
                placeholder={`${listing.min_order_fiat} – ${listing.max_order_fiat}`}
                value={fiatAmount}
                onChange={e => setFiatAmount(e.target.value)}
                className="pr-16 h-12 text-lg font-medium"
                disabled={loading}
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 font-bold text-gray-600 dark:text-gray-400">
                {fiatCurrency}
              </span>
            </div>
            <p className="text-xs text-gray-500">
              Limit: {listing.min_order_fiat.toLocaleString()} – {listing.max_order_fiat.toLocaleString()} {fiatCurrency}
            </p>
          </div>

          {/* Token Amount (read-only, derived) */}
          <div className="space-y-1.5">
            <Label className="text-sm font-semibold text-gray-900 dark:text-white">
              I will receive
            </Label>
            <div className="relative">
              <Input
                readOnly
                value={tokenAmount}
                className="pr-20 h-12 text-lg font-bold bg-gray-50 dark:bg-gray-900 cursor-not-allowed"
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 font-bold text-blue-600 dark:text-blue-400">
                {tokenMeta?.icon} {tokenDisplay}
              </span>
            </div>
          </div>

          {/* Payment Method */}
          <div className="space-y-1.5">
            <Label className="text-sm font-semibold text-gray-900 dark:text-white">
              Payment Method
            </Label>
            <Select value={paymentMethod} onValueChange={setPaymentMethod} disabled={loading}>
              <SelectTrigger className="h-12">
                <SelectValue placeholder="Select payment method" />
              </SelectTrigger>
              <SelectContent>
                {listing.payment_methods.map(pm => (
                  <SelectItem key={pm} value={pm}>{pm}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Warning */}
          <Alert className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <AlertCircle className="h-4 w-4 text-blue-600" />
            <AlertDescription className="text-sm text-gray-700 dark:text-gray-300">
              After placing the order, you will have <strong>15 minutes</strong> to complete the payment.
              Payment details will be revealed only after order placement.
            </AlertDescription>
          </Alert>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="border-t pt-4 gap-3">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
            className="flex-1 h-12 font-semibold"
          >
            Cancel
          </Button>
          <Button
            onClick={handlePlaceOrder}
            disabled={loading || !isAmountValid || !paymentMethod}
            className="flex-1 h-12 font-bold bg-green-600 hover:bg-green-700 text-white disabled:opacity-50"
          >
            {loading ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Placing Order...</>
            ) : (
              <>Place Order <ArrowRight className="ml-2 h-4 w-4" /></>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}