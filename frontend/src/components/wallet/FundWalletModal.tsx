// File: frontend/src/components/wallet/FundWalletModal.tsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { loadMoonPay } from '@moonpay/moonpay-js'
import { api } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button.tsx'
import { Input } from '@/components/ui/input.tsx'
import { Label } from '@/components/ui/label.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import {
  Dialog, DialogContent, DialogDescription,
  DialogHeader, DialogTitle,
} from '@/components/ui/dialog.tsx'
import { Loader2, Wallet, Info, AlertCircle, ShieldCheck, Globe, Banknote } from 'lucide-react'

interface FundWalletModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Provider = 'local' | 'moonpay'

// ── MoonPay-supported onramp assets ──────────────────────────────
const MOONPAY_ASSET_GROUPS = {
  '🟢 Algorand': [
    { value: 'ALGO', label: 'Algorand (ALGO)', icon: 'Ⱥ' },
  ],
  '🟠 Bitcoin': [
    { value: 'BTC', label: 'Bitcoin (BTC)', icon: '₿' },
  ],
  '🔵 Ethereum': [
    { value: 'ETH',      label: 'Ethereum (ETH)',      icon: 'Ξ' },
    { value: 'USDT_ETH', label: 'Tether (Ethereum)',   icon: '₮' },
    { value: 'USDC_ETH', label: 'USD Coin (Ethereum)', icon: '◎' },
  ],
  '🟣 Polygon': [
    { value: 'MATIC',        label: 'Polygon (MATIC)',    icon: '▶' },
    { value: 'USDT_POLYGON', label: 'Tether (Polygon)',   icon: '₮' },
    { value: 'USDC_POLYGON', label: 'USD Coin (Polygon)', icon: '◎' },
  ],
  '🔴 Tron': [
    { value: 'TRX',       label: 'TRON (TRX)',    icon: '⚡' },
    { value: 'USDT_TRON', label: 'Tether (Tron)', icon: '₮' },
  ],
  '🟣 Solana': [
    { value: 'SOL',         label: 'Solana (SOL)',      icon: '◎' },
    { value: 'USDT_SOLANA', label: 'Tether (Solana)',   icon: '₮' },
    { value: 'USDC_SOLANA', label: 'USD Coin (Solana)', icon: '◎' },
  ],
}

// ── Local provider: all assets including Algorand-native ──────────
const LOCAL_ASSET_GROUPS = {
  '🟢 Algorand': [
    { value: 'ALGO',      label: 'Algorand (ALGO)',         icon: 'Ⱥ' },
    { value: 'USDT_ALGO', label: 'Tether (Algorand)',       icon: '₮' },
    { value: 'USDCa',     label: 'USD Coin (USDCa)',        icon: '◎' },
    { value: 'goBTC',     label: 'Wrapped Bitcoin (goBTC)', icon: '₿' },
    { value: 'goETH',     label: 'Wrapped Ethereum (goETH)',icon: 'Ξ' },
  ],
  '🟠 Bitcoin': [{ value: 'BTC', label: 'Bitcoin (BTC)', icon: '₿' }],
  '🔵 Ethereum': [
    { value: 'ETH',      label: 'Ethereum (ETH)',      icon: 'Ξ' },
    { value: 'USDT_ETH', label: 'Tether (Ethereum)',   icon: '₮' },
    { value: 'USDC_ETH', label: 'USD Coin (Ethereum)', icon: '◎' },
  ],
  '🟣 Polygon': [
    { value: 'MATIC',        label: 'Polygon (MATIC)',    icon: '▶' },
    { value: 'USDT_POLYGON', label: 'Tether (Polygon)',   icon: '₮' },
    { value: 'USDC_POLYGON', label: 'USD Coin (Polygon)', icon: '◎' },
  ],
  '🔴 Tron': [
    { value: 'TRX',       label: 'TRON (TRX)',    icon: '⚡' },
    { value: 'USDT_TRON', label: 'Tether (Tron)', icon: '₮' },
  ],
  '🟣 Solana': [
    { value: 'SOL',         label: 'Solana (SOL)',      icon: '◎' },
    { value: 'USDT_SOLANA', label: 'Tether (Solana)',   icon: '₮' },
    { value: 'USDC_SOLANA', label: 'USD Coin (Solana)', icon: '◎' },
  ],
}

const LOCAL_CURRENCIES = [
  { code: 'NGN', name: 'Nigerian Naira',     symbol: '₦',   flag: '🇳🇬' },
  { code: 'KES', name: 'Kenyan Shilling',    symbol: 'KSh', flag: '🇰🇪' },
  { code: 'GHS', name: 'Ghanaian Cedi',      symbol: 'GH₵', flag: '🇬🇭' },
  { code: 'ZAR', name: 'South African Rand', symbol: 'R',   flag: '🇿🇦' },
  { code: 'UGX', name: 'Ugandan Shilling',   symbol: 'USh', flag: '🇺🇬' },
  { code: 'TZS', name: 'Tanzanian Shilling', symbol: 'TSh', flag: '🇹🇿' },
  { code: 'RWF', name: 'Rwandan Franc',      symbol: 'FRw', flag: '🇷🇼' },
  { code: 'XOF', name: 'West African CFA',   symbol: 'CFA', flag: '🌍' },
  { code: 'XAF', name: 'Central African CFA',symbol: 'FCFA',flag: '🌍' },
  { code: 'ZMW', name: 'Zambian Kwacha',     symbol: 'ZK',  flag: '🇿🇲' },
  { code: 'USD', name: 'US Dollar',          symbol: '$',   flag: '🇺🇸' },
  { code: 'GBP', name: 'British Pound',      symbol: '£',   flag: '🇬🇧' },
  { code: 'EUR', name: 'Euro',               symbol: '€',   flag: '🇪🇺' },
]

const MOONPAY_FIAT = [
  { code: 'USD', flag: '🇺🇸' }, { code: 'EUR', flag: '🇪🇺' }, { code: 'GBP', flag: '🇬🇧' },
  { code: 'NGN', flag: '🇳🇬' }, { code: 'KES', flag: '🇰🇪' }, { code: 'GHS', flag: '🇬🇭' },
  { code: 'ZAR', flag: '🇿🇦' },
]

// Algorand-native assets not supported by MoonPay
const MOONPAY_ASSET_FALLBACK: Record<string, string> = {
  goBTC: 'BTC', goETH: 'ETH', USDCa: 'USDC_ETH', USDT_ALGO: 'USDT_TRON',
}

export function FundWalletModal({ open, onOpenChange }: FundWalletModalProps) {
  const [provider, setProvider]     = useState<Provider>('local')
  const [asset, setAsset]           = useState('USDT_TRON')
  const [amount, setAmount]         = useState('')
  const [currency, setCurrency]     = useState('NGN')
  const [mpCurrency, setMpCurrency] = useState('USD')
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState<string | null>(null)
  const [quote, setQuote]           = useState<any>(null)
  const [fetchingQuote, setFetchingQuote] = useState(false)

  const { session } = useAuth()
  const navigate    = useNavigate()

  // Pre-select asset from WalletDetailModal "Buy" button
  useEffect(() => {
    if (!open) return
    const pre = sessionStorage.getItem('preselected_asset')
    if (pre) {
      setAsset(pre)
      sessionStorage.removeItem('preselected_asset')
    }
  }, [open])

  // When switching to MoonPay, remap unsupported assets
  useEffect(() => {
    if (provider === 'moonpay') {
      const safe = MOONPAY_ASSET_FALLBACK[asset]
      if (safe) setAsset(safe)
    }
  }, [provider])

  // Reset quote when inputs change
  useEffect(() => { setQuote(null) }, [asset, currency, amount])

  // Debounced quote for local provider
  useEffect(() => {
    if (provider !== 'local') return
    if (!amount || parseFloat(amount) <= 0) { setQuote(null); return }
    const timer = setTimeout(fetchQuote, 500)
    return () => clearTimeout(timer)
  }, [amount, currency, asset, provider])

  const fetchQuote = async () => {
    setFetchingQuote(true)
    setError(null)
    try {
      const endpoint = session ? '/api/v1/onramp/quote' : '/api/v1/onramp/quote/public'
      const res = await api.post(endpoint, {
        amount_fiat: parseFloat(amount),
        currency,
        crypto_asset: asset,
      })
      if (res?.success) setQuote(res.quote)
      else setError(res?.error || 'Failed to get quote')
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Quote failed')
      setQuote(null)
    } finally {
      setFetchingQuote(false)
    }
  }

  // ── Local provider (Paystack / Flutterwave) ───────────────────
  const handleLocalPay = async () => {
    if (!amount || parseFloat(amount) <= 0) { toast.error('Enter a valid amount'); return }
    const minAmount = currency === 'NGN' ? 1000 : 10
    if (parseFloat(amount) < minAmount) {
      toast.error(`Minimum: ${selectedCurrency?.symbol}${minAmount}`); return
    }
    setLoading(true); setError(null)
    try {
      const res = await api.post('/api/v1/onramp/initialize', {
        amount_fiat: parseFloat(amount),
        currency,
        crypto_asset: asset,
        payment_method: 'auto',
      })
      const data = res.data || res
      if (data?.success && data?.checkout_url) {
        toast.success('Redirecting to payment...')
        setTimeout(() => { window.location.href = data.checkout_url }, 400)
      } else {
        throw new Error(data?.detail || data?.error || 'Payment link not generated')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Payment failed'
      setError(msg); toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  // ── MoonPay (correct SDK API — handlers in constructor) ───────
  const handleMoonPay = async () => {
    if (!session) { toast.error('Sign in to buy crypto'); return }
    setLoading(true); setError(null)
    try {
      const res = await api.post('/api/v1/moonpay/url/onramp', {
        asset,
        base_currency_code:   mpCurrency,
        base_currency_amount: amount ? parseFloat(amount) : undefined,
      })
      if (!res?.success) throw new Error(res?.detail || 'Failed to initialize MoonPay')

      const moonPayInit = await loadMoonPay()
      if (!moonPayInit) throw new Error('MoonPay SDK failed to load')

      const widget = moonPayInit({
        flow:        'buy',
        environment: 'production',
        variant:     'overlay',
        params:      res.params,
        handlers: {
          async onTransactionCompleted() {
            toast.success('🎉 Purchase complete! Crypto arriving shortly.')
            onOpenChange(false)
          },
          onCloseOverlay() {
            // user closed — no action needed
          },
        },
      })
      widget?.show()
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'MoonPay failed to launch'
      setError(msg); toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const selectedCurrency = LOCAL_CURRENCIES.find(c => c.code === currency)
  const activeGroups     = provider === 'moonpay' ? MOONPAY_ASSET_GROUPS : LOCAL_ASSET_GROUPS
  const selectedLabel    = Object.values(activeGroups).flat().find((a: any) => a.value === asset)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="
        w-[95vw] max-w-md
        max-h-[92dvh] overflow-y-auto
        rounded-2xl p-0
        bg-white dark:bg-gray-900
        border border-gray-200 dark:border-gray-700
        shadow-2xl
      ">
        {/* Sticky Header */}
        <div className="sticky top-0 z-10 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 px-5 pt-5 pb-4 rounded-t-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg font-bold text-gray-900 dark:text-white">
              <div className="p-2 rounded-xl bg-blue-50 dark:bg-blue-900/30">
                <Wallet className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              Buy Crypto
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Choose how you want to pay.
            </DialogDescription>
          </DialogHeader>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">

          {/* Provider Toggle */}
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => { setProvider('local'); setError(null) }}
              className={`flex flex-col items-center gap-1 py-3 px-2 rounded-xl border-2 text-sm font-semibold transition-all ${
                provider === 'local'
                  ? 'border-green-500 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                  : 'border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:border-gray-300'
              }`}
            >
              <Banknote className="h-5 w-5" />
              <span>Local Payment</span>
              <span className="text-[10px] font-normal opacity-70">NGN · KES · GHS & more</span>
            </button>
            <button
              onClick={() => { setProvider('moonpay'); setError(null) }}
              className={`flex flex-col items-center gap-1 py-3 px-2 rounded-xl border-2 text-sm font-semibold transition-all ${
                provider === 'moonpay'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:border-gray-300'
              }`}
            >
              <Globe className="h-5 w-5" />
              <span>MoonPay</span>
              <span className="text-[10px] font-normal opacity-70">Card · Apple Pay · 160+ countries</span>
            </button>
          </div>

          {/* Asset Selection */}
          <div className="space-y-1.5">
            <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Select Asset to Receive
            </Label>
            <Select value={asset} onValueChange={setAsset}>
              <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="max-h-72 rounded-xl bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                {Object.entries(activeGroups).map(([chain, assets]) => (
                  <div key={chain}>
                    <div className="px-3 py-1.5 text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest bg-gray-50 dark:bg-gray-900">
                      {chain}
                    </div>
                    {(assets as any[]).map((a: any) => (
                      <SelectItem key={a.value} value={a.value}
                        className="py-2.5 pl-6 text-sm text-gray-900 dark:text-white cursor-pointer">
                        <span className="mr-2">{a.icon}</span>{a.label}
                      </SelectItem>
                    ))}
                  </div>
                ))}
              </SelectContent>
            </Select>
            {asset === 'MATIC' && (
              <p className="text-xs text-purple-600 dark:text-purple-400">
                ℹ️ MATIC runs on the POL network — delivered to your Polygon address.
              </p>
            )}
            {provider === 'moonpay' && (
              <p className="text-xs text-amber-600 dark:text-amber-400">
                ⚠️ Algorand-native assets (goBTC, goETH, USDCa) not supported by MoonPay. Switch to Local Payment for those.
              </p>
            )}
          </div>

          {/* ── LOCAL PAYMENT FLOW ── */}
          {provider === 'local' && (
            <>
              {/* Currency */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Your Currency</Label>
                <Select value={currency} onValueChange={v => { setCurrency(v); setQuote(null) }}>
                  <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 max-h-[260px] z-[9999]">
                    {LOCAL_CURRENCIES.map(c => (
                      <SelectItem key={c.code} value={c.code}
                        className="text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-600 py-2.5">
                        <span className="text-base mr-2">{c.flag}</span>
                        <span className="font-medium">{c.symbol}</span>
                        <span className="ml-1 text-gray-500 dark:text-gray-400">{c.name}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Amount */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Amount</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 dark:text-gray-400 font-semibold">
                    {selectedCurrency?.symbol}
                  </span>
                  <Input type="number" placeholder="0.00" value={amount}
                    onChange={e => setAmount(e.target.value)} disabled={loading}
                    className="pl-10 h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-base"
                  />
                </div>
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  Minimum: {selectedCurrency?.symbol}{currency === 'NGN' ? '1,000' : '10'}
                </p>
              </div>

              {/* Live Quote */}
              {fetchingQuote && (
                <div className="flex items-center gap-2 py-1">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                  <span className="text-xs text-gray-400">Fetching quote...</span>
                </div>
              )}
              {quote && !fetchingQuote && (
                <div className="rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 p-3.5 space-y-2">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Live Quote</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">Fee ({quote.total_fee_pct?.toFixed(1)}%)</span>
                    <span className="text-gray-600 dark:text-gray-300">-{selectedCurrency?.symbol}{quote.total_fee?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-bold pt-1.5 border-t border-blue-200 dark:border-blue-700">
                    <span className="text-gray-800 dark:text-white text-sm">You Receive</span>
                    <span className="text-green-600 dark:text-green-400 text-sm">
                      {quote.crypto_to_receive?.toFixed(4)} {asset.split('_')[0]}
                    </span>
                  </div>
                </div>
              )}

              <Alert className="border border-green-100 dark:border-green-900 bg-green-50 dark:bg-green-900/20 rounded-xl py-3">
                <Info className="h-4 w-4 text-green-600 shrink-0 mt-0.5" />
                <AlertDescription className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                  <strong className="text-green-700 dark:text-green-400">Smart routing</strong> — best provider auto-selected for your currency. Crypto credited instantly after payment.
                  {currency === 'NGN' && <span className="block mt-1 text-blue-600 dark:text-blue-400">🔵 Powered by Paystack for NGN</span>}
                </AlertDescription>
              </Alert>
            </>
          )}

          {/* ── MOONPAY FLOW ── */}
          {provider === 'moonpay' && (
            <>
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Amount <span className="font-normal text-gray-400">(optional pre-fill)</span>
                </Label>
                <div className="flex gap-2">
                  <Input type="number" placeholder="0.00" value={amount}
                    onChange={e => setAmount(e.target.value)} disabled={loading}
                    className="flex-1 h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  />
                  <Select value={mpCurrency} onValueChange={setMpCurrency}>
                    <SelectTrigger className="w-24 h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                      {MOONPAY_FIAT.map(c => (
                        <SelectItem key={c.code} value={c.code} className="text-gray-900 dark:text-white">
                          {c.flag} {c.code}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Trust badges */}
              <div className="grid grid-cols-3 gap-2">
                {[
                  { icon: '🔒', text: 'KYC secured' },
                  { icon: '⚡', text: 'Instant delivery' },
                  { icon: '🌍', text: '160+ countries' },
                ].map(b => (
                  <div key={b.text} className="flex flex-col items-center gap-1 p-2.5 rounded-xl bg-gray-50 dark:bg-gray-800 text-center">
                    <span className="text-lg">{b.icon}</span>
                    <span className="text-[10px] font-medium text-gray-500 dark:text-gray-400">{b.text}</span>
                  </div>
                ))}
              </div>

              <Alert className="border border-blue-100 dark:border-blue-900 bg-blue-50 dark:bg-blue-900/20 rounded-xl py-3">
                <Info className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
                <AlertDescription className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                  Powered by <strong className="text-blue-600 dark:text-blue-400">MoonPay</strong> —
                  crypto delivered directly to your Seamount wallet. Apple Pay & Google Pay open in a new tab.
                </AlertDescription>
              </Alert>
            </>
          )}

          {error && (
            <Alert variant="destructive" className="rounded-xl border py-3">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <AlertDescription className="text-xs">{error}</AlertDescription>
            </Alert>
          )}
        </div>

        {/* Sticky Footer */}
        <div className="sticky bottom-0 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 px-5 py-4 rounded-b-2xl space-y-3">
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}
              className="flex-1 h-12 rounded-xl border-gray-200 dark:border-gray-700 font-semibold">
              Cancel
            </Button>
            <Button
              onClick={provider === 'moonpay' ? handleMoonPay : handleLocalPay}
              disabled={
                loading ||
                (provider === 'local' && (!amount || parseFloat(amount) <= 0)) ||
                fetchingQuote
              }
              className={`flex-[2] h-12 rounded-xl font-bold text-white ${
                provider === 'moonpay'
                  ? 'bg-blue-600 hover:bg-blue-700'
                  : 'bg-green-600 hover:bg-green-700'
              }`}
            >
              {loading
                ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Launching...</>
                : provider === 'moonpay'
                  ? <><ShieldCheck className="mr-2 h-4 w-4" />Buy with MoonPay</>
                  : <><Wallet className="mr-2 h-4 w-4" />Pay {selectedCurrency?.symbol}{amount || '0'}</>
              }
            </Button>
          </div>
          {provider === 'local' && (
            <div className="text-center">
              <button onClick={() => { onOpenChange(false); navigate('/payments?tab=p2p') }}
                className="text-xs text-gray-400 hover:text-green-500 transition-colors underline underline-offset-2">
                💰 Or buy via P2P — as low as 0.3% fee
              </button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}