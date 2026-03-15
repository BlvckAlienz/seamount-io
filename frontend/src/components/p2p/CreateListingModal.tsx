// FILE: frontend/src/components/p2p/CreateListingModal.tsx
// Simple listing creation modal for already-approved merchants.
// Opened from the "New Listing" button in MerchantDashboardPage.

import { useState } from 'react'
import { apiClient } from '@/config/api'
import toast from 'react-hot-toast'
import {
  Dialog, DialogContent, DialogHeader,
  DialogTitle, DialogDescription
} from '@/components/ui/dialog.tsx'
import { Button } from '@/components/ui/button.tsx'
import { Input } from '@/components/ui/input.tsx'
import { Label } from '@/components/ui/label.tsx'
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue
} from '@/components/ui/select.tsx'
import { Loader2, Plus, Trash2 } from 'lucide-react'

const TOKEN_OPTIONS = [
  { value: 'USDT_TRON',    label: 'USDT (Tron)',     recommended: true  },
  { value: 'USDT_POLYGON', label: 'USDT (Polygon)',  recommended: false },
  { value: 'USDC_ETH',     label: 'USDC (Ethereum)', recommended: false },
  { value: 'USDC_POLYGON', label: 'USDC (Polygon)',  recommended: false },
  { value: 'USDT_SOLANA',  label: 'USDT (Solana)',   recommended: false },
  { value: 'BTC',          label: 'Bitcoin (BTC)',   recommended: false },
  { value: 'ETH',          label: 'Ethereum (ETH)',  recommended: false },
  { value: 'SOL',          label: 'Solana (SOL)',    recommended: false },
]

const FIAT_OPTIONS = [
  'USD','KES','NGN','GHS','UGX','TZS','ZAR','GBP','EUR','INR','PHP'
]

const PAYMENT_METHOD_OPTIONS = [
  'M-Pesa', 'M-Pesa Paybill', 'Airtel Money',
  'Equity Bank', 'KCB Bank', 'Bank Transfer',
  'GTBank', 'Access Bank', 'Zenith Bank',
  'Standard Bank', 'FNB', 'SEPA Transfer',
  'UK Bank Transfer', 'PayPal'
]

interface Props {
  merchantId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function CreateListingModal({ merchantId, open, onOpenChange, onSuccess }: Props) {
  const [loading, setLoading] = useState(false)
  const [token,         setToken]         = useState('USDT_TRON')
  const [fiatCurrency,  setFiatCurrency]  = useState('KES')
  const [pricePerToken, setPricePerToken] = useState('')
  const [minOrderFiat,  setMinOrderFiat]  = useState('')
  const [maxOrderFiat,  setMaxOrderFiat]  = useState('')
  const [availableAmt,  setAvailableAmt]  = useState('')
  const [terms,         setTerms]         = useState('')
  const [paymentMethods, setPaymentMethods] = useState<string[]>([''])

  const tokenDisplay = token.split('_')[0]

  const addMethod = () => setPaymentMethods(p => [...p, ''])
  const removeMethod = (i: number) =>
    setPaymentMethods(p => p.filter((_, idx) => idx !== i))
  const updateMethod = (i: number, val: string) =>
    setPaymentMethods(p => p.map((m, idx) => idx === i ? val : m))

  const handleSubmit = async () => {
    const validMethods = paymentMethods.filter(m => m.trim())
    if (!pricePerToken || !minOrderFiat || !maxOrderFiat || !availableAmt) {
      toast.error('Fill in all required fields')
      return
    }
    if (parseFloat(minOrderFiat) >= parseFloat(maxOrderFiat)) {
      toast.error('Min order must be less than max order')
      return
    }
    if (validMethods.length === 0) {
      toast.error('Add at least one payment method')
      return
    }

    setLoading(true)
    try {
      const res = await apiClient.post('/api/p2p/listings', {
        merchant_id: merchantId,
        token,
        fiat_currency: fiatCurrency,
        price_per_token: parseFloat(pricePerToken),
        min_order_fiat: parseFloat(minOrderFiat),
        max_order_fiat: parseFloat(maxOrderFiat),
        available_amount: parseFloat(availableAmt),
        payment_methods: validMethods,
        payment_details: {},
        terms: terms || null
      })

      if (res.data?.success) {
        toast.success('Listing created!')
        onSuccess()
        onOpenChange(false)
        // Reset form
        setPricePerToken(''); setMinOrderFiat(''); setMaxOrderFiat('')
        setAvailableAmt(''); setTerms(''); setPaymentMethods([''])
      } else {
        throw new Error(res.data?.detail ?? 'Failed to create listing')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? err.message ?? 'Failed to create listing')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-w-[95vw] bg-gray-900 border border-gray-700 text-white max-h-[90vh] overflow-y-auto">
        <DialogHeader className="border-b border-gray-700 pb-4">
          <DialogTitle className="text-lg font-bold flex items-center gap-2">
            <Plus className="h-5 w-5 text-blue-400" /> New Listing
          </DialogTitle>
          <DialogDescription className="text-gray-400 text-sm">
            Create a new token offer on the P2P marketplace
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-3">

          {/* Token + Fiat row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-400 uppercase tracking-wide">
                Token to Sell
              </Label>
              <Select value={token} onValueChange={setToken}>
                <SelectTrigger className="bg-gray-800 border-gray-600 text-white h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent
                  className="bg-gray-800 border-gray-600 z-[200]"
                  position="popper"
                  sideOffset={4}
                >
                  {TOKEN_OPTIONS.map(t => (
                    <SelectItem key={t.value} value={t.value}
                      className="text-white hover:bg-gray-700">
                      {t.label} {t.recommended ? '⭐' : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-gray-400 uppercase tracking-wide">
                Buyer Pays In
              </Label>
              <Select value={fiatCurrency} onValueChange={setFiatCurrency}>
                <SelectTrigger className="bg-gray-800 border-gray-600 text-white h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent
                  className="bg-gray-800 border-gray-600 z-[200]"
                  position="popper"
                  sideOffset={4}
                >
                  {FIAT_OPTIONS.map(f => (
                    <SelectItem key={f} value={f}
                      className="text-white hover:bg-gray-700">{f}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Price */}
          <div className="space-y-1.5">
            <Label className="text-xs text-gray-400 uppercase tracking-wide">
              Price per {tokenDisplay} ({fiatCurrency})
            </Label>
            <Input
              type="number"
              value={pricePerToken}
              onChange={e => setPricePerToken(e.target.value)}
              placeholder="e.g. 131.50"
              className="bg-gray-800 border-gray-600 text-white h-10"
            />
          </div>

          {/* Min / Max order */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-400 uppercase tracking-wide">
                Min Order ({fiatCurrency})
              </Label>
              <Input type="number" value={minOrderFiat}
                onChange={e => setMinOrderFiat(e.target.value)}
                placeholder="e.g. 500"
                className="bg-gray-800 border-gray-600 text-white h-10" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-400 uppercase tracking-wide">
                Max Order ({fiatCurrency})
              </Label>
              <Input type="number" value={maxOrderFiat}
                onChange={e => setMaxOrderFiat(e.target.value)}
                placeholder="e.g. 50,000"
                className="bg-gray-800 border-gray-600 text-white h-10" />
            </div>
          </div>

          {/* Available amount */}
          <div className="space-y-1.5">
            <Label className="text-xs text-gray-400 uppercase tracking-wide">
              Available Amount ({tokenDisplay})
            </Label>
            <Input type="number" value={availableAmt}
              onChange={e => setAvailableAmt(e.target.value)}
              placeholder="Tokens you have available"
              className="bg-gray-800 border-gray-600 text-white h-10" />
          </div>

          {/* Payment methods */}
          <div className="space-y-2">
            <Label className="text-xs text-gray-400 uppercase tracking-wide">
              Payment Methods
            </Label>
            {paymentMethods.map((pm, i) => (
              <div key={i} className="flex gap-2">
                <Select value={pm} onValueChange={val => updateMethod(i, val)}>
                  <SelectTrigger className="flex-1 bg-gray-800 border-gray-600 text-white h-10">
                    <SelectValue placeholder="Select method" />
                  </SelectTrigger>
                  <SelectContent
                    className="bg-gray-800 border-gray-600 z-[200]"
                    position="popper"
                    sideOffset={4}
                  >
                    {PAYMENT_METHOD_OPTIONS.map(opt => (
                      <SelectItem key={opt} value={opt}
                        className="text-white hover:bg-gray-700">{opt}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {paymentMethods.length > 1 && (
                  <button onClick={() => removeMethod(i)}
                    className="text-red-400 hover:text-red-300 px-2">
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
            <Button variant="outline" onClick={addMethod} size="sm"
              className="w-full border-dashed border-gray-600 text-gray-400 hover:text-white gap-2">
              <Plus className="h-3.5 w-3.5" /> Add Method
            </Button>
          </div>

          {/* Terms */}
          <div className="space-y-1.5">
            <Label className="text-xs text-gray-400 uppercase tracking-wide">
              Terms (optional)
            </Label>
            <textarea
              value={terms}
              onChange={e => setTerms(e.target.value)}
              placeholder="e.g. Payment must include order number as reference."
              className="w-full bg-gray-800 border border-gray-600 text-white placeholder:text-gray-500 rounded-md px-3 py-2 text-sm resize-none h-16 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex gap-3 border-t border-gray-700 pt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}
            className="flex-1 border-gray-600 text-gray-400">
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}
            className="flex-1 bg-green-600 hover:bg-green-700 font-bold gap-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Create Listing
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}