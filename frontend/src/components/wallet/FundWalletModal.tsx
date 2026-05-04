// File: frontend/src/components/wallet/FundWalletModal.tsx
/**
 * FundWalletModal — Dual Provider: Paystack/Flutterwave + MoonPay
 * - Paystack/FW: African currencies, mobile money, live quote
 * - MoonPay: Global, 160+ countries, card/Apple Pay/Google Pay
 */

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
import {
  Dialog, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import { Loader2, Wallet, AlertCircle, Info, Globe, Banknote } from 'lucide-react'

interface FundWalletModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Provider = 'paystack' | 'moonpay'

// ── Paystack/Flutterwave supported currencies ──────────────────────
const PAYSTACK_CURRENCIES = [
  { code: 'NGN', name: 'Nigerian Naira',       symbol: '₦',   flag: '🇳🇬' },
  { code: 'KES', name: 'Kenyan Shilling',       symbol: 'KSh', flag: '🇰🇪' },
  { code: 'GHS', name: 'Ghanaian Cedi',         symbol: 'GH₵', flag: '🇬🇭' },
  { code: 'ZAR', name: 'South African Rand',    symbol: 'R',   flag: '🇿🇦' },
  { code: 'UGX', name: 'Ugandan Shilling',      symbol: 'USh', flag: '🇺🇬' },
  { code: 'TZS', name: 'Tanzanian Shilling',    symbol: 'TSh', flag: '🇹🇿' },
  { code: 'RWF', name: 'Rwandan Franc',         symbol: 'FRw', flag: '🇷🇼' },
  { code: 'XOF', name: 'West African CFA',      symbol: 'CFA', flag: '🌍' },
  { code: 'XAF', name: 'Central African CFA',   symbol: 'FCFA',flag: '🌍' },
  { code: 'ZMW', name: 'Zambian Kwacha',        symbol: 'ZK',  flag: '🇿🇲' },
  { code: 'USD', name: 'US Dollar',             symbol: '$',   flag: '🇺🇸' },
  { code: 'GBP', name: 'British Pound',         symbol: '£',   flag: '🇬🇧' },
  { code: 'EUR', name: 'Euro',                  symbol: '€',   flag: '🇪🇺' },
]

// ── MoonPay fiat hint currencies ──────────────────────────────────
const MOONPAY_CURRENCIES = ['USD', 'EUR', 'GBP', 'NGN', 'KES', 'GHS']

// ── All asset groups (full list for Paystack flow) ─────────────────
const ASSET_GROUPS = {
  algorand: [
    { value: 'ALGO',      label: 'Algorand (ALGO)',        icon: 'Ⱥ' },
    { value: 'USDT_ALGO', label: 'Tether (Algorand)',      icon: '₮' },
    { value: 'USDCa',     label: 'USD Coin (USDCa)',       icon: '◎' },
    { value: 'goBTC',     label: 'Wrapped Bitcoin (goBTC)',icon: '₿' },
    { value: 'goETH',     label: 'Wrapped Ethereum (goETH)',icon:'Ξ' },
  ],
  bitcoin:  [{ value: 'BTC',          label: 'Bitcoin (BTC)',        icon: '₿' }],
  ethereum: [
    { value: 'ETH',       label: 'Ethereum (ETH)',         icon: 'Ξ' },
    { value: 'USDT_ETH',  label: 'Tether (Ethereum)',      icon: '₮' },
    { value: 'USDC_ETH',  label: 'USD Coin (Ethereum)',    icon: '◎' },
  ],
  polygon: [
    { value: 'MATIC',         label: 'Polygon (MATIC)',    icon: '▶' },
    { value: 'USDT_POLYGON',  label: 'Tether (Polygon)',   icon: '₮' },
    { value: 'USDC_POLYGON',  label: 'USD Coin (Polygon)', icon: '◎' },
  ],
  tron: [
    { value: 'TRX',       label: 'TRON (TRX)',             icon: '⚡' },
    { value: 'USDT_TRON', label: 'Tether (Tron)',          icon: '₮' },
  ],
  solana: [
    { value: 'SOL',          label: 'Solana (SOL)',         icon: '◎' },
    { value: 'USDT_SOLANA',  label: 'Tether (Solana)',      icon: '₮' },
    { value: 'USDC_SOLANA',  label: 'USD Coin (Solana)',    icon: '◎' },
  ],
}

// ── MoonPay: only what it actually supports ───────────────────────
const MOONPAY_ASSET_GROUPS = {
  algorand: [{ value: 'ALGO', label: 'Algorand (ALGO)', icon: 'Ⱥ' }],
  bitcoin:  [{ value: 'BTC',  label: 'Bitcoin (BTC)',   icon: '₿' }],
  ethereum: [
    { value: 'ETH',      label: 'Ethereum (ETH)',      icon: 'Ξ' },
    { value: 'USDT_ETH', label: 'Tether (Ethereum)',   icon: '₮' },
    { value: 'USDC_ETH', label: 'USD Coin (Ethereum)', icon: '◎' },
  ],
  polygon: [
    { value: 'MATIC',        label: 'Polygon (MATIC)',    icon: '▶' },
    { value: 'USDT_POLYGON', label: 'Tether (Polygon)',   icon: '₮' },
    { value: 'USDC_POLYGON', label: 'USD Coin (Polygon)', icon: '◎' },
  ],
  tron: [
    { value: 'TRX',       label: 'TRON (TRX)',        icon: '⚡' },
    { value: 'USDT_TRON', label: 'Tether (Tron)',     icon: '₮' },
  ],
  solana: [
    { value: 'SOL',         label: 'Solana (SOL)',        icon: '◎' },
    { value: 'USDT_SOLANA', label: 'Tether (Solana)',     icon: '₮' },
    { value: 'USDC_SOLANA', label: 'USD Coin (Solana)',   icon: '◎' },
  ],
}

const CHAIN_LABELS: Record<string, string> = {
  algorand: '🟢 Algorand', bitcoin: '🟠 Bitcoin',
  ethereum: '🔵 Ethereum', polygon: '🟣 Polygon',
  tron:     '🔴 Tron',     solana:  '🟣 Solana',
}

const MOONPAY_SAFE_ASSET: Record<string, string> = {
  goBTC: 'BTC', goETH: 'ETH', USDCa: 'USDC_ETH', USDT_ALGO: 'USDT_TRON', USDT: 'USDT_TRON',
}

export function FundWalletModal({ open, onOpenChange }: FundWalletModalProps) {
  const [provider, setProvider]   = useState<Provider>('paystack')
  const [asset, setAsset]         = useState('USDT_TRON')
  const [amount, setAmount]       = useState('')
  const [currency, setCurrency]   = useState('NGN')
  const [mpCurrency, setMpCurrency] = useState('USD') // MoonPay fiat hint
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState<string | null>(null)
  const [quote, setQuote]         = useState<any>(null)
  const [fetchingQuote, setFetchingQuote] = useState(false)

  const { session } = useAuth()
  const navigate    = useNavigate()

  // Pre-select asset from WalletDetailModal "Buy" button
  useEffect(() => {
    if (open) {
      const pre = sessionStorage.getItem('preselected_asset')
      if (pre) {
        setAsset(pre)
        sessionStorage.removeItem('preselected_asset')
      }
    }
  }, [open])

  // When switching to MoonPay, remap unsupported assets
  useEffect(() => {
    if (provider === 'moonpay') {
      const safe = MOONPAY_SAFE_ASSET[asset]
      if (safe) setAsset(safe)
    }
  }, [provider])

  // Debounced quote for Paystack flow
  useEffect(() => {
    if (provider !== 'paystack') return
    const timer = setTimeout(() => {
      if (amount && parseFloat(amount) > 0) fetchQuote()
    }, 500)
    return () => clearTimeout(timer)
  }, [amount, currency, asset, provider])

  const fetchQuote = async () => {
    setFetchingQuote(true)
    setError(null)
    try {
      const endpoint = session ? '/api/v1/onramp/quote' : '/api/v1/onramp/quote/public'
      const response = await api.post(endpoint, {
        amount_fiat: parseFloat(amount),
        currency,
        crypto_asset: asset,
      })
      if (response?.success) setQuote(response.quote)
      else setError(response?.error || 'Failed to get quote')
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to get quote')
      setQuote(null)
    } finally {
      setFetchingQuote(false)
    }
  }

  // ── Paystack / Flutterwave handler ─────────────────────────────
  const handlePaystack = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount'); return
    }
    const minAmount = currency === 'NGN' ? 1000 : 10
    if (parseFloat(amount) < minAmount) {
      toast.error(`Minimum: ${selectedCurrency?.symbol}${minAmount}`); return
    }
    setLoading(true); setError(null)
    try {
      const response = await api.post('/api/v1/onramp/initialize', {
        amount_fiat: parseFloat(amount),
        currency,
        crypto_asset: asset,
        payment_method: 'auto',
      })
      const data = response.data || response
      if (data?.success && data?.checkout_url) {
        toast.success('Redirecting to payment...')
        setTimeout(() => { window.location.href = data.checkout_url }, 500)
      } else {
        throw new Error(data?.detail || data?.error || 'Payment link not generated')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to initialize payment'
      setError(msg); toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  // ── MoonPay handler ────────────────────────────────────────────
  const handleMoonPay = async () => {
    if (!session) { toast.error('Please sign in to buy crypto'); return }
    setLoading(true); setError(null)
    try {
      const response = await api.post('/api/v1/moonpay/url/onramp', {
        asset,
        base_currency_code:   mpCurrency || undefined,
        base_currency_amount: amount ? parseFloat(amount) : undefined,
      })
      if (!response?.success) throw new Error(response?.detail || 'Failed to initialize MoonPay')
      const moonPayFactory = await loadMoonPay()
      const moonPaySdk = moonPayFactory({
        flow: 'buy', environment: 'production', variant: 'overlay',
        params: response.params,
      })
      moonPaySdk.on('transactionCompleted', () => {
        toast.success('🎉 Purchase complete! Crypto will arrive shortly.')
        onOpenChange(false)
      })
      moonPaySdk.show()
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to launch MoonPay'
      setError(msg); toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const selectedCurrency = PAYSTACK_CURRENCIES.find(c => c.code === currency)
  const activeGroups     = provider === 'moonpay' ? MOONPAY_ASSET_GROUPS : ASSET_GROUPS

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-[480px] max-w-[95vw] max-h-[90vh] overflow-y-auto bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600"
        style={{ zIndex: 1000 }}
      >
        <DialogHeader className="border-b pb-4">
          <DialogTitle className="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-white">
            <Wallet className="h-6 w-6 text-blue-600" />
            Buy Crypto
          </DialogTitle>
          <DialogDescription className="text-gray-600 dark:text-gray-400 mt-1">
            Choose your payment provider.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* ── Provider Toggle ── */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold text-gray-900 dark:text-white">Payment Provider</Label>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => { setProvider('paystack'); setError(null) }}
                className={`h-14 flex-col gap-1 border-2 text-sm font-bold transition-all ${
                  provider === 'paystack'
                    ? 'border-green-500 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                    : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400'
                }`}
              >
                <Banknote className="h-5 w-5" />
                <span>Paystack / FW</span>
                <span className="text-xs font-normal opacity-70">Best for Africa</span>
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => { setProvider('moonpay'); setError(null) }}
                className={`h-14 flex-col gap-1 border-2 text-sm font-bold transition-all ${
                  provider === 'moonpay'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                    : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400'
                }`}
              >
                <Globe className="h-5 w-5" />
                <span>MoonPay</span>
                <span className="text-xs font-normal opacity-70">160+ countries</span>
              </Button>
            </div>
          </div>

          {/* ── Asset Selection ── */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold text-gray-900 dark:text-white">Crypto to Receive</Label>
            <Select value={asset} onValueChange={setAsset}>
              <SelectTrigger className="w-full h-12 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100">
                <SelectValue placeholder="Select asset" />
              </SelectTrigger>
              <SelectContent className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 max-h-[380px] z-50">
                {Object.entries(activeGroups).map(([chain, assets]) => (
                  <div key={chain}>
                    <div className="px-3 py-2 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide bg-gray-100 dark:bg-gray-900">
                      {CHAIN_LABELS[chain]}
                    </div>
                    {assets.map((a: any) => (
                      <SelectItem key={a.value} value={a.value}
                        className="py-3 pl-8 text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-600">
                        <span className="text-lg mr-2">{a.icon}</span>
                        <span className="font-medium">{a.label}</span>
                      </SelectItem>
                    ))}
                  </div>
                ))}
              </SelectContent>
            </Select>
            {provider === 'moonpay' && (
              <p className="text-xs text-amber-600 dark:text-amber-400">
                ⚠️ Algorand-native assets (goBTC, goETH, USDCa) not supported by MoonPay.
                Use Paystack/FW for those.
              </p>
            )}
          </div>

          {/* ── PAYSTACK FLOW ── */}
          {provider === 'paystack' && (
            <>
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900 dark:text-white">Your Currency</Label>
                <Select value={currency} onValueChange={setCurrency}>
                  <SelectTrigger className="w-full h-12 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 max-h-[300px] z-50">
                    {PAYSTACK_CURRENCIES.map(c => (
                      <SelectItem key={c.code} value={c.code}
                        className="text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-600 py-3">
                        <span className="text-xl mr-2">{c.flag}</span>
                        <span className="font-medium">{c.symbol}</span>
                        <span className="ml-1">{c.name} ({c.code})</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900 dark:text-white">Amount</Label>
                <div className="relative">
                  <span className="absolute left-3 top-3 text-gray-600 dark:text-gray-400 font-medium text-lg">
                    {selectedCurrency?.symbol}
                  </span>
                  <Input type="number" placeholder="0.00" value={amount}
                    onChange={e => setAmount(e.target.value)}
                    disabled={loading}
                    className="pl-12 h-12 text-lg font-medium bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100"
                  />
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Minimum: {selectedCurrency?.symbol}{currency === 'NGN' ? '1,000' : '10'}
                </p>
              </div>

              {/* Live Quote */}
              {fetchingQuote && (
                <div className="flex items-center justify-center py-3">
                  <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                  <span className="ml-2 text-sm text-gray-500">Getting quote...</span>
                </div>
              )}
              {quote && !fetchingQuote && (
                <div className="rounded-xl bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-700 p-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Fee ({quote.total_fee_pct?.toFixed(1)}%)</span>
                    <span className="text-gray-700 dark:text-gray-300">-{selectedCurrency?.symbol}{quote.total_fee?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-base border-t border-blue-300 dark:border-blue-700 pt-2">
                    <span className="text-gray-900 dark:text-white">You Receive</span>
                    <span className="text-green-600 dark:text-green-400">
                      {quote.crypto_to_receive?.toFixed(4)} {asset}
                    </span>
                  </div>
                </div>
              )}

              <Alert className="bg-green-50 dark:bg-green-900/20 border-2 border-green-200 dark:border-green-800">
                <Info className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-sm text-gray-800 dark:text-gray-200">
                  <strong className="text-green-700 dark:text-green-300">Paystack / Flutterwave</strong> — Best rates for NGN, KES, GHS & African mobile money.
                </AlertDescription>
              </Alert>
            </>
          )}

          {/* ── MOONPAY FLOW ── */}
          {provider === 'moonpay' && (
            <>
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900 dark:text-white">
                  Amount (Optional pre-fill)
                </Label>
                <div className="flex gap-2">
                  <Input type="number" placeholder="e.g. 100" value={amount}
                    onChange={e => setAmount(e.target.value)} disabled={loading}
                    className="flex-1 h-11 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100"
                  />
                  <Select value={mpCurrency} onValueChange={setMpCurrency}>
                    <SelectTrigger className="w-24 h-11 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-white dark:bg-gray-700 z-50">
                      {MOONPAY_CURRENCIES.map(c => (
                        <SelectItem key={c} value={c}>{c}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Alert className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800">
                <Info className="h-4 w-4 text-blue-600" />
                <AlertDescription className="text-sm text-gray-800 dark:text-gray-200">
                  <strong className="text-blue-700 dark:text-blue-300">MoonPay</strong> — Card, bank, Apple Pay & Google Pay in 160+ countries.
                  KYC handled inside MoonPay widget.
                </AlertDescription>
              </Alert>
            </>
          )}

          {error && (
            <Alert variant="destructive" className="border-2">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="border-t pt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading} className="h-11 border-2">
            Cancel
          </Button>
          <Button
            onClick={provider === 'moonpay' ? handleMoonPay : handlePaystack}
            disabled={
              loading ||
              (provider === 'paystack' && (!amount || parseFloat(amount) <= 0)) ||
              fetchingQuote
            }
            className={`h-11 px-8 font-bold text-white ${
              provider === 'moonpay'
                ? 'bg-blue-600 hover:bg-blue-700'
                : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            {loading ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Preparing...</>
            ) : provider === 'moonpay' ? (
              <><Globe className="mr-2 h-4 w-4" />Open MoonPay</>
            ) : (
              <><Wallet className="mr-2 h-4 w-4" />Pay {selectedCurrency?.symbol}{amount || '0'}</>
            )}
          </Button>
        </DialogFooter>

        <div className="text-center pb-3 pt-1">
          <button
            onClick={() => { onOpenChange(false); navigate('/payments?tab=p2p') }}
            className="text-xs text-gray-500 hover:text-green-400 transition-colors underline underline-offset-2"
          >
            💰 Or buy via P2P — as low as 0.3% fee
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}