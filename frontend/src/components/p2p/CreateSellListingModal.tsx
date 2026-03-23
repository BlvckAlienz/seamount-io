// NEW FILE: frontend/src/components/p2p/CreateSellListingModal.tsx
// Mirror of CreateListingModal but for merchant BUY listings
// ─────────────────────────────────────────────────────────────

import { useState } from 'react'
import { apiClient } from '@/config/api'
import { useWallet } from '@/contexts/WalletContext'
import toast from 'react-hot-toast'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog.tsx'
import { Button } from '@/components/ui/button.tsx'
import { Input } from '@/components/ui/input.tsx'
import { Label } from '@/components/ui/label.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx'
import { Loader2, ArrowDownUp } from 'lucide-react'

// Reuse same constants as MerchantOnboardingModal
const TOKEN_OPTIONS = [
  { value: 'USDT_TRON',    label: 'USDT (Tron)',        recommended: true  },
  { value: 'USDT_ALGO',    label: 'USDT (Algorand)',    recommended: false },
  { value: 'USDCa',        label: 'USD Coin (Algorand)', recommended: false },
  { value: 'USDT_ETH',     label: 'USDT (Ethereum)',    recommended: false },
  { value: 'USDC_ETH',     label: 'USDC (Ethereum)',    recommended: false },
  { value: 'USDT_POLYGON', label: 'USDT (Polygon)',     recommended: false },
  { value: 'USDC_POLYGON', label: 'USDC (Polygon)',     recommended: false },
  { value: 'USDT_SOLANA',  label: 'USDT (Solana)',      recommended: false },
  { value: 'USDC_SOLANA',  label: 'USDC (Solana)',      recommended: false },
  { value: 'BTC',          label: 'Bitcoin (BTC)',      recommended: false },
  { value: 'ETH',          label: 'Ethereum (ETH)',     recommended: false },
  { value: 'SOL',          label: 'Solana (SOL)',       recommended: false },
  { value: 'MATIC',        label: 'Polygon (MATIC)',    recommended: false },
  { value: 'TRX',          label: 'TRON (TRX)',         recommended: false },
  { value: 'ALGO',         label: 'Algorand (ALGO)',    recommended: false },
]

const FIAT_OPTIONS = ['KES','NGN','GHS','USD','GBP','EUR']
const PAYMENT_METHOD_OPTIONS = [
  'M-Pesa (Safaricom)', 'Airtel Money Kenya', 'Opay', 'Palmpay', 'Kuda Bank',
  'GTBank (Guaranty Trust)', 'Access Bank', 'Zenith Bank', 'First Bank of Nigeria',
  'UBA (United Bank for Africa)', 'Equity Bank Kenya', 'KCB Bank Kenya',
  'Co-operative Bank', 'Bank Transfer (Other)',
]

interface Props {
  merchantId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function CreateSellListingModal({ merchantId, open, onOpenChange, onSuccess }: Props) {
  const { balances } = useWallet()
  const [loading, setLoading] = useState(false)
  const [token, setToken] = useState('USDT_TRON')
  const [fiatCurrency, setFiatCurrency] = useState('KES')
  const [pricePerToken, setPricePerToken] = useState('')
  const [minOrderFiat, setMinOrderFiat] = useState('')
  const [maxOrderFiat, setMaxOrderFiat] = useState('')
  const [availableFiat, setAvailableFiat] = useState('')
  const [paymentMethods, setPaymentMethods] = useState<string[]>([])
  const [terms, setTerms] = useState('')

  const tokenDisplay = token.split('_')[0]

  // Try auto-fill receive address from wallet
  // User should verify/override this

  const handleCreate = async () => {
    if (!pricePerToken || !minOrderFiat || !maxOrderFiat || !availableFiat
        || paymentMethods.length === 0) {
      toast.error('Fill all required fields'); return
    }
    if (parseFloat(minOrderFiat) >= parseFloat(maxOrderFiat)) {
      toast.error('Min order must be less than max'); return
    }
    setLoading(true)
    try {
      const res = await apiClient.post('/api/p2p/sell/listings', {
        merchant_id: merchantId,
        token,
        fiat_currency: fiatCurrency,
        price_per_token: parseFloat(pricePerToken),
        min_order_fiat: parseFloat(minOrderFiat),
        max_order_fiat: parseFloat(maxOrderFiat),
        available_amount: parseFloat(availableFiat),
        payment_methods: paymentMethods,
        payment_details: {},
        terms: terms || null,
      })
      if (res.data?.success) {
        toast.success('Buy listing created!')
        onSuccess()
        onOpenChange(false)
      } else {
        throw new Error(res.data?.detail ?? 'Failed')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? err.message)
    } finally { setLoading(false) }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px] max-w-[95vw] bg-gray-900 border border-gray-700 text-white max-h-[90vh] overflow-y-auto">
        <DialogHeader className="border-b border-gray-700 pb-4">
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            <ArrowDownUp className="h-5 w-5 text-orange-400" />
            Create Buy Listing
          </DialogTitle>
          <DialogDescription className="text-gray-400">
            List yourself as a token buyer — sellers will send you tokens and you pay them fiat
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-400 uppercase">Token to Buy</Label>
              <Select value={token} onValueChange={setToken}>
                <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-gray-600 max-h-60">
                  {TOKEN_OPTIONS.map(t => (
                    <SelectItem key={t.value} value={t.value} className="text-white hover:bg-gray-700">
                      {t.label} {t.recommended ? '⭐' : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-400 uppercase">Fiat Currency</Label>
              <Select value={fiatCurrency} onValueChange={setFiatCurrency}>
                <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-gray-600">
                  {FIAT_OPTIONS.map(f => (
                    <SelectItem key={f} value={f} className="text-white hover:bg-gray-700">{f}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-gray-400 uppercase">Your Price (per {tokenDisplay} in {fiatCurrency})</Label>
            <Input type="number" value={pricePerToken} onChange={e => setPricePerToken(e.target.value)}
              placeholder="e.g. 131.50" className="bg-gray-800 border-gray-600 text-white" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-400 uppercase">Min Order ({fiatCurrency})</Label>
              <Input type="number" value={minOrderFiat} onChange={e => setMinOrderFiat(e.target.value)}
                placeholder="500" className="bg-gray-800 border-gray-600 text-white" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-gray-400 uppercase">Max Order ({fiatCurrency})</Label>
              <Input type="number" value={maxOrderFiat} onChange={e => setMaxOrderFiat(e.target.value)}
                placeholder="50000" className="bg-gray-800 border-gray-600 text-white" />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-gray-400 uppercase">Available Fiat to Deploy ({fiatCurrency})</Label>
            <Input type="number" value={availableFiat} onChange={e => setAvailableFiat(e.target.value)}
              placeholder="How much fiat can you deploy?" className="bg-gray-800 border-gray-600 text-white" />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-gray-400 uppercase">How You'll Pay Fiat</Label>
            <div className="space-y-1">
              {PAYMENT_METHOD_OPTIONS.map(opt => (
                <label key={opt} className="flex items-center gap-2 cursor-pointer p-2 rounded hover:bg-gray-800">
                  <input type="checkbox" checked={paymentMethods.includes(opt)}
                    onChange={e => setPaymentMethods(prev =>
                      e.target.checked ? [...prev, opt] : prev.filter(p => p !== opt)
                    )}
                    className="accent-orange-500" />
                  <span className="text-sm text-gray-300">{opt}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-gray-400 uppercase">Terms (optional)</Label>
            <textarea value={terms} onChange={e => setTerms(e.target.value)}
              placeholder="e.g. Instant M-Pesa transfers only. No delays."
              className="w-full bg-gray-800 border border-gray-600 text-white rounded-md px-3 py-2 text-sm resize-none h-16 focus:outline-none focus:ring-2 focus:ring-orange-500" />
          </div>
        </div>

        <div className="flex gap-3 pt-3 border-t border-gray-700">
          <Button variant="outline" onClick={() => onOpenChange(false)}
            className="flex-1 border-gray-600 text-gray-400">Cancel</Button>
          <Button onClick={handleCreate} disabled={loading}
            className="flex-1 h-11 bg-orange-600 hover:bg-orange-700 font-bold gap-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Create Buy Listing 🚀
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}