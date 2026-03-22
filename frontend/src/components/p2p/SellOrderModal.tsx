// ═══════════════════════════════════════════════════════════════
// FILE 1: frontend/src/components/p2p/SellOrderModal.tsx
// User places a sell order — mirrors PlaceOrderModal structure
// ═══════════════════════════════════════════════════════════════

import { useState } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import { apiClient } from '@/config/api'
import {
  Dialog, DialogContent, DialogHeader,
  DialogTitle, DialogDescription, DialogFooter
} from '@/components/ui/dialog.tsx'
import { Button }   from '@/components/ui/button.tsx'
import { Input }    from '@/components/ui/input.tsx'
import { Label }    from '@/components/ui/label.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import { ShieldCheck, Clock, Star, AlertCircle, ArrowRight, Loader2 } from 'lucide-react'

const PAYOUT_METHOD_OPTIONS = [
  // Nigeria — Mobile Money
  'Opay', 'Palmpay', 'Kuda Bank', 'Moniepoint', 'Carbon (Paylater)',
  // Nigeria — Banks
  'GTBank (Guaranty Trust)', 'Access Bank', 'Zenith Bank',
  'First Bank of Nigeria', 'UBA (United Bank for Africa)',
  'Fidelity Bank', 'FCMB', 'Sterling Bank', 'Union Bank',
  'Wema Bank (ALAT)', 'Stanbic IBTC', 'Polaris Bank', 'Providus Bank',
  // Kenya — Mobile Money
  'M-Pesa (Safaricom)', 'M-Pesa Paybill', 'Airtel Money Kenya',
  // Kenya — Banks
  'Equity Bank Kenya', 'KCB Bank Kenya', 'Co-operative Bank',
  'NCBA Bank', 'Absa Bank Kenya', 'Standard Chartered Kenya',
  'I&M Bank', 'Diamond Trust Bank', 'Family Bank',
  // International
  'Bank Transfer (Other)', 'SEPA Transfer', 'UK Bank Transfer',
]

function getDefaultPayoutFields(method: string): Record<string, string> {
  if (method.includes('M-Pesa') || method.includes('Airtel'))
    return { phone_number: '', account_name: '' }
  if (method.includes('Bank') || method.includes('SEPA') || method.includes('Transfer'))
    return { bank_name: method, account_number: '', account_name: '' }
  return { account_number: '', account_name: '' }
}

interface Listing {
  id: string
  token: string
  fiat_currency: string
  price_per_token: number
  min_order_fiat: number
  max_order_fiat: number
  available_amount: number
  payment_methods: string[]
  merchant_receive_address: string
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

interface Props {
  listing: Listing
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SellOrderModal({ listing, open, onOpenChange }: Props) {
  const { user }    = useAuth()
  const navigate    = useNavigate()
  const m           = listing.p2p_merchants
  const tokenDisplay = listing.token.split('_')[0]

  const [fiatAmount,    setFiatAmount]    = useState('')
  const [payoutMethod,  setPayoutMethod]  = useState('')
  const [payoutFields,  setPayoutFields]  = useState<Record<string, string>>({})
  const [loading,       setLoading]       = useState(false)
  const [error,         setError]         = useState<string | null>(null)

  // Token amount user needs to send
  const tokenAmount = fiatAmount && parseFloat(fiatAmount) > 0
    ? (parseFloat(fiatAmount) / listing.price_per_token).toFixed(6)
    : '0.000000'

  const isAmountValid =
    !!fiatAmount &&
    parseFloat(fiatAmount) >= listing.min_order_fiat &&
    parseFloat(fiatAmount) <= listing.max_order_fiat

  const isFormValid = isAmountValid && !!payoutMethod &&
    Object.values(payoutFields).every(v => v.trim().length > 0)

  const handlePayoutMethodChange = (method: string) => {
    setPayoutMethod(method)
    setPayoutFields(getDefaultPayoutFields(method))
  }

  const handlePlaceOrder = async () => {
    if (!isFormValid || !user?.id) { toast.error('Please fill all fields'); return }
    setLoading(true); setError(null)
    try {
      const res = await apiClient.post('/api/p2p/sell/orders', {
        idempotency_key: uuidv4(),
        listing_id:      listing.id,
        fiat_amount:     parseFloat(fiatAmount),
        payment_method:  payoutMethod,
        payout_details:  payoutFields,
      })
      if (res.data?.success) {
        onOpenChange(false)
        toast.success('Sell order placed! Send your tokens to the address shown.')
        navigate(`/p2p/orders/${res.data.order.id}`)
      } else {
        throw new Error(res.data?.detail ?? 'Failed to place order')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail ?? err.message ?? 'Failed'
      setError(msg); toast.error(msg)
    } finally { setLoading(false) }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px] max-w-[95vw] bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600 max-h-[90vh] overflow-y-auto">
        <DialogHeader className="border-b pb-3">
          <DialogTitle className="text-lg font-bold text-gray-900 dark:text-white">
            Sell {tokenDisplay}
          </DialogTitle>
          <DialogDescription className="text-gray-500 dark:text-gray-400 text-sm">
            You send tokens → merchant sends you fiat
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-3">
          {/* Merchant Summary */}
          <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
            <div className="w-9 h-9 rounded-full bg-orange-600 flex items-center justify-center text-white font-bold text-sm">
              {m.display_name.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1 font-semibold text-gray-900 dark:text-white text-sm">
                <span className="truncate">{m.display_name}</span>
                {m.verified && <ShieldCheck className="h-3.5 w-3.5 text-blue-500 flex-shrink-0" />}
              </div>
              <div className="flex gap-2 text-xs text-gray-500 mt-0.5 flex-wrap">
                <span>{m.total_orders} orders</span>
                <span><Star className="h-3 w-3 inline text-yellow-400 mr-0.5" />{m.completion_rate.toFixed(1)}%</span>
                <span><Clock className="h-3 w-3 inline mr-0.5" />{m.avg_release_time_mins}min</span>
              </div>
            </div>
            <div className="text-right flex-shrink-0">
              <div className="text-base font-bold text-gray-900 dark:text-white">
                {listing.price_per_token.toLocaleString()} {listing.fiat_currency}
              </div>
              <div className="text-xs text-gray-500">per {tokenDisplay}</div>
            </div>
          </div>

          {listing.terms && (
            <div className="text-xs text-gray-600 dark:text-gray-400 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-2.5">
              <span className="font-bold text-yellow-700 dark:text-yellow-400">Terms: </span>{listing.terms}
            </div>
          )}

          {/* Amount inputs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs font-semibold text-gray-700 dark:text-white">I will receive</Label>
              <div className="relative">
                <Input
                  type="number"
                  placeholder={`${listing.min_order_fiat} – ${listing.max_order_fiat}`}
                  value={fiatAmount}
                  onChange={e => setFiatAmount(e.target.value)}
                  className="pr-14 h-11 text-base font-medium"
                  disabled={loading}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 font-bold text-gray-500 text-sm">
                  {listing.fiat_currency}
                </span>
              </div>
              <p className="text-xs text-gray-400">
                {listing.min_order_fiat.toLocaleString()} – {listing.max_order_fiat.toLocaleString()} {listing.fiat_currency}
              </p>
            </div>
            <div className="space-y-1">
              <Label className="text-xs font-semibold text-gray-700 dark:text-white">I will send</Label>
              <div className="relative">
                <Input readOnly value={tokenAmount}
                  className="pr-20 h-11 text-base font-bold bg-gray-50 dark:bg-gray-900 cursor-not-allowed" />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 font-bold text-orange-600 dark:text-orange-400 text-sm">
                  {tokenDisplay}
                </span>
              </div>
            </div>
          </div>

          {/* Payout method */}
          <div className="space-y-1">
            <Label className="text-xs font-semibold text-gray-700 dark:text-white">
              How should merchant pay you?
            </Label>
            <Select value={payoutMethod} onValueChange={handlePayoutMethodChange} disabled={loading}>
              <SelectTrigger className="h-11">
                <SelectValue placeholder="Select your payout method" />
              </SelectTrigger>
              <SelectContent className="max-h-60 z-[300] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600">
                {PAYOUT_METHOD_OPTIONS.map(opt => (
                  <SelectItem key={opt} value={opt} className="text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700 py-2.5">
                    {opt}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Payout details */}
          {payoutMethod && Object.entries(payoutFields).map(([key, val]) => (
            <div key={key} className="space-y-1">
              <Label className="text-xs text-gray-500 capitalize">{key.replace(/_/g, ' ')}</Label>
              <Input
                value={val}
                onChange={e => setPayoutFields(p => ({ ...p, [key]: e.target.value }))}
                placeholder={`Your ${key.replace(/_/g, ' ')}`}
                className="h-10 text-sm"
                disabled={loading}
              />
            </div>
          ))}

          <Alert className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 py-2.5">
            <AlertCircle className="h-3.5 w-3.5 text-orange-600 flex-shrink-0" />
            <AlertDescription className="text-xs text-gray-700 dark:text-gray-300">
              After placing the order, you have <strong>15 minutes</strong> to send your tokens
              to the merchant's wallet. Merchant's address will be shown on the order page.
            </AlertDescription>
          </Alert>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="border-t pt-3 gap-2 flex-row">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading} className="flex-1 h-10 font-semibold">
            Cancel
          </Button>
          <Button
            onClick={handlePlaceOrder}
            disabled={loading || !isFormValid}
            className="flex-1 h-10 font-bold bg-orange-600 hover:bg-orange-700 text-white disabled:opacity-50"
          >
            {loading
              ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Placing...</>
              : <>Place Sell Order <ArrowRight className="ml-2 h-4 w-4" /></>
            }
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}