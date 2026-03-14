// FILE: frontend/src/components/p2p/MerchantOnboardingModal.tsx
// 3-step merchant application modal.
// Step 1 — Apply (display name + terms)
// Step 2 — Payment methods (what buyers will use to pay you)
// Step 3 — First listing (your first token offer)
// Mirrors Binance's flow but adapted for Seamount's bootstrap context.

import { useState } from 'react'
import { apiClient } from '@/config/api'
import { useAuth } from '@/contexts/AuthContext'
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
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import {
  ShieldCheck, Wallet, Plus, Trash2,
  ArrowRight, ArrowLeft, Loader2,
  CheckCircle, AlertCircle, BadgeCheck
} from 'lucide-react'

// ── Token options — mirrors ASSET_GROUPS in SendForm.tsx ─────
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

interface PaymentMethod {
  method: string
  details: Record<string, string>  // e.g. { phone: "0712345678", name: "John Doe" }
}

interface ListingForm {
  token: string
  fiatCurrency: string
  pricePerToken: string
  minOrderFiat: string
  maxOrderFiat: string
  availableAmount: string
  terms: string
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

const STEPS = ['Apply', 'Payment Methods', 'First Listing']

export function MerchantOnboardingModal({ open, onOpenChange, onSuccess }: Props) {
  const { user } = useAuth()
  const [step,           setStep]           = useState(0)
  const [loading,        setLoading]        = useState(false)
  const [merchantId,     setMerchantId]     = useState<string | null>(null)

  // Step 1
  const [displayName,    setDisplayName]    = useState('')
  const [agreedToTerms,  setAgreedToTerms]  = useState(false)

  // Step 2
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([
    { method: '', details: {} }
  ])

  // Step 3
  const [listing, setListing] = useState<ListingForm>({
    token: 'USDT_TRON',
    fiatCurrency: 'KES',
    pricePerToken: '',
    minOrderFiat: '',
    maxOrderFiat: '',
    availableAmount: '',
    terms: ''
  })

  const tokenDisplay = listing.token.split('_')[0]

  // ── Step 1: Register as merchant ───────────────────────────
  const handleRegister = async () => {
    if (!displayName.trim()) {
      toast.error('Enter a display name')
      return
    }
    if (!agreedToTerms) {
      toast.error('Please agree to the merchant terms')
      return
    }
    setLoading(true)
    try {
      const res = await apiClient.post('/api/p2p/merchants/register', {
        display_name: displayName.trim()
      })
      if (res.data?.success) {
        setMerchantId(res.data.merchant_id)
        toast.success('Application submitted!')
        setStep(1)
      } else {
        throw new Error(res.data?.detail ?? 'Registration failed')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? err.message ?? 'Failed to register')
    } finally {
      setLoading(false)
    }
  }

  // ── Step 2: Save payment methods ───────────────────────────
  const addPaymentMethod = () => {
    setPaymentMethods(prev => [...prev, { method: '', details: {} }])
  }

  const removePaymentMethod = (idx: number) => {
    setPaymentMethods(prev => prev.filter((_, i) => i !== idx))
  }

  const updateMethod = (idx: number, method: string) => {
    setPaymentMethods(prev => {
      const updated = [...prev]
      updated[idx] = { method, details: getDefaultDetails(method) }
      return updated
    })
  }

  const updateDetail = (idx: number, key: string, value: string) => {
    setPaymentMethods(prev => {
      const updated = [...prev]
      updated[idx] = { ...updated[idx], details: { ...updated[idx].details, [key]: value } }
      return updated
    })
  }

  const getDefaultDetails = (method: string): Record<string, string> => {
    if (method.includes('M-Pesa') || method.includes('Airtel')) {
      return { phone_number: '', account_name: '' }
    }
    if (method.includes('Bank') || method.includes('SEPA') || method.includes('Transfer')) {
      return { bank_name: '', account_number: '', account_name: '' }
    }
    return { details: '' }
  }

  const handleSavePaymentMethods = async () => {
    const valid = paymentMethods.filter(pm => pm.method)
    if (valid.length === 0) {
      toast.error('Add at least one payment method')
      return
    }
    setLoading(true)
    try {
      const res = await apiClient.post('/api/p2p/merchants/payment-methods', {
        merchant_id: merchantId,
        payment_methods: valid
      })
      if (res.data?.success) {
        toast.success('Payment methods saved!')
        setStep(2)
      } else {
        throw new Error(res.data?.detail ?? 'Failed to save')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? err.message ?? 'Failed to save payment methods')
    } finally {
      setLoading(false)
    }
  }

  // ── Step 3: Create first listing ───────────────────────────
  const handleCreateListing = async () => {
    const { token, fiatCurrency, pricePerToken, minOrderFiat, maxOrderFiat, availableAmount } = listing
    if (!pricePerToken || !minOrderFiat || !maxOrderFiat || !availableAmount) {
      toast.error('Fill in all required fields')
      return
    }
    if (parseFloat(minOrderFiat) >= parseFloat(maxOrderFiat)) {
      toast.error('Min order must be less than max order')
      return
    }
    setLoading(true)
    try {
      const paymentMethodNames = paymentMethods.filter(pm => pm.method).map(pm => pm.method)
      const paymentDetails = Object.fromEntries(
        paymentMethods.filter(pm => pm.method).map(pm => [pm.method, pm.details])
      )
      const res = await apiClient.post('/api/p2p/listings', {
        merchant_id: merchantId,
        token,
        fiat_currency: fiatCurrency,
        price_per_token: parseFloat(pricePerToken),
        min_order_fiat: parseFloat(minOrderFiat),
        max_order_fiat: parseFloat(maxOrderFiat),
        available_amount: parseFloat(availableAmount),
        payment_methods: paymentMethodNames,
        payment_details: paymentDetails,
        terms: listing.terms || null
      })
      if (res.data?.success) {
        toast.success('🎉 You are now a Seamount merchant!')
        onSuccess()
        onOpenChange(false)
        // Reset
        setStep(0); setDisplayName(''); setAgreedToTerms(false)
        setPaymentMethods([{ method: '', details: {} }])
        setListing({ token: 'USDT_TRON', fiatCurrency: 'KES', pricePerToken: '', minOrderFiat: '', maxOrderFiat: '', availableAmount: '', terms: '' })
      } else {
        throw new Error(res.data?.detail ?? 'Failed to create listing')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? err.message ?? 'Failed to create listing')
    } finally {
      setLoading(false)
    }
  }

  // ─────────────────────────────────────────────────────────
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[560px] max-w-[95vw] bg-gray-900 border border-gray-700 text-white max-h-[90vh] overflow-y-auto">

        {/* Header */}
        <DialogHeader className="border-b border-gray-700 pb-4">
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            <BadgeCheck className="h-6 w-6 text-yellow-400" />
            Become a Merchant
          </DialogTitle>
          <DialogDescription className="text-gray-400">
            Provide liquidity, earn fees on every trade
          </DialogDescription>
        </DialogHeader>

        {/* Progress Steps */}
        <div className="flex items-center gap-2 py-3">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center gap-2 flex-1">
              <div className={`flex items-center gap-1.5 text-xs font-semibold px-2 py-1 rounded-full whitespace-nowrap
                ${i < step  ? 'bg-green-500/20 text-green-400 border border-green-500/30' : ''}
                ${i === step ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : ''}
                ${i > step  ? 'bg-gray-800 text-gray-500 border border-gray-700' : ''}
              `}>
                {i < step
                  ? <CheckCircle className="h-3 w-3" />
                  : <span className="w-3 h-3 rounded-full border flex items-center justify-center text-[10px]">{i + 1}</span>
                }
                {s}
              </div>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-px ${i < step ? 'bg-green-500/40' : 'bg-gray-700'}`} />
              )}
            </div>
          ))}
        </div>

        {/* ── STEP 1: Apply ── */}
        {step === 0 && (
          <div className="space-y-5 py-2">
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 flex gap-3">
              <BadgeCheck className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-yellow-200">
                <p className="font-bold mb-1">Merchant Benefits</p>
                <ul className="text-yellow-300/80 space-y-1 text-xs">
                  <li>✓ Verified badge on all your listings</li>
                  <li>✓ Earn 0.3% fee on every completed trade</li>
                  <li>✓ Priority in listing sort order</li>
                  <li>✓ Access to merchant dashboard & analytics</li>
                </ul>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-sm font-semibold text-gray-300">Display Name</Label>
              <Input
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                placeholder="e.g. FastTrader_KE or Nairobi Crypto"
                className="bg-gray-800 border-gray-600 text-white placeholder:text-gray-500"
                maxLength={30}
              />
              <p className="text-xs text-gray-500">This is what buyers see on the marketplace</p>
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-semibold text-gray-300">Merchant Requirements</Label>
              <div className="bg-gray-800/60 rounded-xl divide-y divide-gray-700">
                {[
                  { icon: ShieldCheck, label: 'KYC verified on Seamount', met: true },
                  { icon: Wallet, label: 'Active wallet on at least one chain', met: true },
                ].map((req, i) => (
                  <div key={i} className="flex items-center gap-3 px-4 py-3">
                    <req.icon className={`h-4 w-4 ${req.met ? 'text-green-400' : 'text-red-400'}`} />
                    <span className="text-sm text-gray-300">{req.label}</span>
                    <span className={`ml-auto text-xs font-bold ${req.met ? 'text-green-400' : 'text-red-400'}`}>
                      {req.met ? 'MET ✓' : 'REQUIRED'}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <label className="flex items-start gap-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={agreedToTerms}
                onChange={e => setAgreedToTerms(e.target.checked)}
                className="mt-1 h-4 w-4 accent-blue-500"
              />
              <span className="text-sm text-gray-400 group-hover:text-gray-300">
                I understand that as a merchant I am responsible for releasing tokens promptly after
                confirming payment, maintaining a completion rate above 80%, and resolving disputes
                in good faith. Accounts with fraudulent activity will be permanently banned.
              </span>
            </label>

            <Button
              onClick={handleRegister}
              disabled={loading || !displayName.trim() || !agreedToTerms}
              className="w-full h-12 bg-blue-600 hover:bg-blue-700 font-bold gap-2"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Submit Application <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* ── STEP 2: Payment Methods ── */}
        {step === 1 && (
          <div className="space-y-5 py-2">
            <Alert className="bg-blue-500/10 border-blue-500/30">
              <AlertCircle className="h-4 w-4 text-blue-400" />
              <AlertDescription className="text-blue-300 text-xs">
                These are how buyers will pay YOU. Make sure the account names match your KYC identity
                to avoid disputes.
              </AlertDescription>
            </Alert>

            {paymentMethods.map((pm, idx) => (
              <div key={idx} className="bg-gray-800/60 rounded-xl p-4 space-y-3 border border-gray-700">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-300">Method {idx + 1}</span>
                  {paymentMethods.length > 1 && (
                    <button onClick={() => removePaymentMethod(idx)} className="text-red-400 hover:text-red-300">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
                <Select value={pm.method} onValueChange={val => updateMethod(idx, val)}>
                  <SelectTrigger className="bg-gray-700 border-gray-600 text-white">
                    <SelectValue placeholder="Select payment method" />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-800 border-gray-600">
                    {PAYMENT_METHOD_OPTIONS.map(opt => (
                      <SelectItem key={opt} value={opt} className="text-white hover:bg-gray-700">{opt}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {pm.method && Object.entries(pm.details).map(([key, val]) => (
                  <div key={key} className="space-y-1">
                    <Label className="text-xs text-gray-400 capitalize">{key.replace(/_/g, ' ')}</Label>
                    <Input
                      value={val}
                      onChange={e => updateDetail(idx, key, e.target.value)}
                      placeholder={`Enter ${key.replace(/_/g, ' ')}`}
                      className="bg-gray-700 border-gray-600 text-white placeholder:text-gray-500 h-9 text-sm"
                    />
                  </div>
                ))}
              </div>
            ))}

            <Button
              variant="outline"
              onClick={addPaymentMethod}
              className="w-full border-dashed border-gray-600 text-gray-400 hover:text-white hover:border-gray-400 gap-2"
            >
              <Plus className="h-4 w-4" /> Add Another Method
            </Button>

            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setStep(0)}
                className="flex-1 border-gray-600 text-gray-400 gap-2">
                <ArrowLeft className="h-4 w-4" /> Back
              </Button>
              <Button onClick={handleSavePaymentMethods} disabled={loading}
                className="flex-1 h-12 bg-blue-600 hover:bg-blue-700 font-bold gap-2">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Continue <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* ── STEP 3: First Listing ── */}
        {step === 2 && (
          <div className="space-y-4 py-2">
            <p className="text-sm text-gray-400">
              Set up your first offer. Buyers will see this on the marketplace.
            </p>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400 uppercase tracking-wide">Token to Sell</Label>
                <Select value={listing.token} onValueChange={val => setListing(p => ({ ...p, token: val }))}>
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
                <Label className="text-xs text-gray-400 uppercase tracking-wide">Buyer Pays In</Label>
                <Select value={listing.fiatCurrency} onValueChange={val => setListing(p => ({ ...p, fiatCurrency: val }))}>
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
              <Label className="text-xs text-gray-400 uppercase tracking-wide">
                Your Price (per {tokenDisplay} in {listing.fiatCurrency})
              </Label>
              <Input
                type="number"
                value={listing.pricePerToken}
                onChange={e => setListing(p => ({ ...p, pricePerToken: e.target.value }))}
                placeholder="e.g. 131.50"
                className="bg-gray-800 border-gray-600 text-white placeholder:text-gray-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400 uppercase tracking-wide">Min Order ({listing.fiatCurrency})</Label>
                <Input type="number" value={listing.minOrderFiat}
                  onChange={e => setListing(p => ({ ...p, minOrderFiat: e.target.value }))}
                  placeholder="e.g. 500"
                  className="bg-gray-800 border-gray-600 text-white placeholder:text-gray-500" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400 uppercase tracking-wide">Max Order ({listing.fiatCurrency})</Label>
                <Input type="number" value={listing.maxOrderFiat}
                  onChange={e => setListing(p => ({ ...p, maxOrderFiat: e.target.value }))}
                  placeholder="e.g. 50000"
                  className="bg-gray-800 border-gray-600 text-white placeholder:text-gray-500" />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-gray-400 uppercase tracking-wide">
                Available Amount ({tokenDisplay})
              </Label>
              <Input type="number" value={listing.availableAmount}
                onChange={e => setListing(p => ({ ...p, availableAmount: e.target.value }))}
                placeholder="Tokens available in your wallet for this listing"
                className="bg-gray-800 border-gray-600 text-white placeholder:text-gray-500" />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-gray-400 uppercase tracking-wide">Trade Terms (optional)</Label>
              <textarea
                value={listing.terms}
                onChange={e => setListing(p => ({ ...p, terms: e.target.value }))}
                placeholder="e.g. Payment must include order number as reference. M-Pesa only."
                className="w-full bg-gray-800 border border-gray-600 text-white placeholder:text-gray-500 rounded-md px-3 py-2 text-sm resize-none h-20 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setStep(1)}
                className="flex-1 border-gray-600 text-gray-400 gap-2">
                <ArrowLeft className="h-4 w-4" /> Back
              </Button>
              <Button onClick={handleCreateListing} disabled={loading}
                className="flex-1 h-12 bg-green-600 hover:bg-green-700 font-bold gap-2">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Go Live 🚀
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}