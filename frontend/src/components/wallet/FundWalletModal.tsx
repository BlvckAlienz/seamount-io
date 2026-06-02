// File: frontend/src/components/wallet/FundWalletModal.tsx
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button.tsx'
import { Input } from '@/components/ui/input.tsx'
import { Label } from '@/components/ui/label.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import {
  Dialog, DialogClose, DialogContent, DialogDescription,
  DialogHeader, DialogTitle,
} from '@/components/ui/dialog.tsx'
import { Loader2, Wallet, Info, AlertCircle, Copy, CheckCircle2, Smartphone, X } from 'lucide-react'

type Step = 'configure' | 'confirming' | 'pay_bank' | 'pay_stk' | 'redirecting'

interface FundWalletModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// ── Currency catalogue — full list restored ───────────────────────────────────
// provider:  busha | kotani | flutterwave
// pay_in:    bank_account | stk_push | redirect
// backup:    shown as secondary label in UI
const CURRENCIES = [
  { code: 'NGN', name: 'Nigerian Naira',      symbol: '₦',    flag: '🇳🇬', provider: 'busha',       pay_in: 'bank_account', backup: 'Paystack (collection)' },
  { code: 'KES', name: 'Kenyan Shilling',     symbol: 'KSh',  flag: '🇰🇪', provider: 'busha',       pay_in: 'bank_account', backup: 'Kotani (fallback)'     },
  { code: 'GHS', name: 'Ghanaian Cedi',       symbol: 'GH₵',  flag: '🇬🇭', provider: 'kotani',      pay_in: 'stk_push',     backup: 'Flutterwave (fallback)'},
  { code: 'UGX', name: 'Ugandan Shilling',    symbol: 'USh',  flag: '🇺🇬', provider: 'kotani',      pay_in: 'stk_push',     backup: null                    },
  { code: 'TZS', name: 'Tanzanian Shilling',  symbol: 'TSh',  flag: '🇹🇿', provider: 'kotani',      pay_in: 'stk_push',     backup: null                    },
  { code: 'RWF', name: 'Rwandan Franc',       symbol: 'FRw',  flag: '🇷🇼', provider: 'kotani',      pay_in: 'stk_push',     backup: null                    },
  { code: 'ZMW', name: 'Zambian Kwacha',      symbol: 'ZK',   flag: '🇿🇲', provider: 'kotani',      pay_in: 'stk_push',     backup: null                    },
  { code: 'XOF', name: 'West African CFA',    symbol: 'CFA',  flag: '🌍',  provider: 'kotani',      pay_in: 'stk_push',     backup: null                    },
  { code: 'XAF', name: 'Central African CFA', symbol: 'FCFA', flag: '🌍',  provider: 'kotani',      pay_in: 'stk_push',     backup: null                    },
  { code: 'ZAR', name: 'South African Rand',  symbol: 'R',    flag: '🇿🇦', provider: 'flutterwave', pay_in: 'redirect',     backup: null                    },
  { code: 'USD', name: 'US Dollar',           symbol: '$',    flag: '🇺🇸', provider: 'flutterwave', pay_in: 'redirect',     backup: null                    },
  { code: 'GBP', name: 'British Pound',       symbol: '£',    flag: '🇬🇧', provider: 'flutterwave', pay_in: 'redirect',     backup: null                    },
  { code: 'EUR', name: 'Euro',                symbol: '€',    flag: '🇪🇺', provider: 'flutterwave', pay_in: 'redirect',     backup: null                    },
]

const PROVIDER_LABEL: Record<string, string> = {
  busha:       'Busha',
  kotani:      'Kotani Pay',
  flutterwave: 'Flutterwave',
}

// ── Asset catalogue — full list restored ──────────────────────────────────────
const ASSET_GROUPS = {
  '🟢 Algorand': [
    { value: 'ALGO',      label: 'Algorand (ALGO)',         icon: 'Ⱥ' },
    { value: 'USDT_ALGO', label: 'Tether (Algorand)',       icon: '₮' },
    { value: 'USDCa',     label: 'USD Coin (USDCa)',        icon: '◎' },
    { value: 'goBTC',     label: 'Wrapped Bitcoin (goBTC)', icon: '₿' },
    { value: 'goETH',     label: 'Wrapped Ethereum (goETH)',icon: 'Ξ' },
  ],
  '🟠 Bitcoin':  [{ value: 'BTC',          label: 'Bitcoin (BTC)',          icon: '₿' }],
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

// Assets that Kotani doesn't support — fall back to Flutterwave flow for these
const KOTANI_UNSUPPORTED = new Set(['ALGO', 'USDT_ALGO', 'USDCa', 'goBTC', 'goETH'])

// Kotani mobile networks per currency
const KOTANI_TELCOS: Record<string, { id: string; name: string }[]> = {
  KES: [{ id: 'MPESA',     name: 'M-Pesa'       }, { id: 'AIRTEL',     name: 'Airtel Money' }],
  GHS: [{ id: 'MTN',       name: 'MTN MoMo'     }, { id: 'VODAFONE',   name: 'Vodafone Cash' }, { id: 'AIRTELTIGO', name: 'AirtelTigo'  }],
  UGX: [{ id: 'MTN',       name: 'MTN MoMo'     }, { id: 'AIRTEL',     name: 'Airtel Money' }],
  TZS: [{ id: 'MPESA',     name: 'M-Pesa'       }, { id: 'AIRTEL',     name: 'Airtel'       }, { id: 'TIGO',       name: 'Tigo Cash'   }],
  RWF: [{ id: 'MTN',       name: 'MTN MoMo'     }, { id: 'AIRTEL',     name: 'Airtel Money' }],
  ZMW: [{ id: 'MTN',       name: 'MTN MoMo'     }, { id: 'AIRTEL',     name: 'Airtel Money' }, { id: 'ZAMTEL',     name: 'Zamtel'      }],
  XOF: [{ id: 'ORANGE',    name: 'Orange Money' }, { id: 'MTN',        name: 'MTN MoMo'     }],
  XAF: [{ id: 'ORANGE',    name: 'Orange Money' }, { id: 'MTN',        name: 'MTN MoMo'     }],
}

export function FundWalletModal({ open, onOpenChange }: FundWalletModalProps) {
  const [step, setStep]           = useState<Step>('configure')
  const [asset, setAsset]         = useState('USDT_TRON')
  const [currency, setCurrency]   = useState('NGN')
  const [amount, setAmount]       = useState('')
  const [phone, setPhone]         = useState('')
  const [telco, setTelco]         = useState('')
  const [quote, setQuote]         = useState<any>(null)
  const [txResult, setTxResult]   = useState<any>(null)
  const [loading, setLoading]     = useState(false)
  const [fetchingQ, setFetchingQ] = useState(false)
  const [error, setError]         = useState<string | null>(null)
  const [copied, setCopied]       = useState(false)

  const { session } = useAuth()
  const navigate    = useNavigate()

  const selectedCurrency = CURRENCIES.find(c => c.code === currency)!
  const isBusha          = selectedCurrency.provider === 'busha'
  const isKotani         = selectedCurrency.provider === 'kotani'
  const isFlutter        = selectedCurrency.provider === 'flutterwave'
  const telcos           = KOTANI_TELCOS[currency] ?? []

  // For Kotani currencies, also fall back to Flutterwave if asset is unsupported
  const effectiveProvider = isKotani && KOTANI_UNSUPPORTED.has(asset) ? 'flutterwave' : selectedCurrency.provider
  const useFlutterFallback = effectiveProvider === 'flutterwave'

  useEffect(() => {
    if (!open) { setStep('configure'); setQuote(null); setError(null); return }
    const pre = sessionStorage.getItem('preselected_asset')
    if (pre) { setAsset(pre); sessionStorage.removeItem('preselected_asset') }
  }, [open])

  useEffect(() => {
    setQuote(null); setError(null); setTelco('')
  }, [currency])

  useEffect(() => { setQuote(null) }, [asset, amount])

  // Debounced quote — skip for Flutterwave (redirect flow, no server quote needed)
  useEffect(() => {
    if (useFlutterFallback || isFlutter) return
    if (!amount || parseFloat(amount) <= 0) { setQuote(null); return }
    const t = setTimeout(fetchQuote, 600)
    return () => clearTimeout(t)
  }, [amount, currency, asset, effectiveProvider])

  const fetchQuote = async () => {
    if (!amount || parseFloat(amount) <= 0) return
    setFetchingQ(true); setError(null)
    try {
      const endpoint = isBusha && !useFlutterFallback
        ? '/api/v1/busha/onramp/quote'
        : '/api/v1/kotani/onramp/quote'
      const res = await api.post(endpoint, {
        amount_fiat: parseFloat(amount), currency, crypto_asset: asset,
      })
      if (res?.success) setQuote(res)
      else setError(res?.message || 'Failed to fetch quote')
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Quote failed')
    } finally {
      setFetchingQ(false)
    }
  }

  const handleConfirm = async () => {
    if (!session) { toast.error('Sign in to continue'); return }
    if (!amount || parseFloat(amount) <= 0) { toast.error('Enter a valid amount'); return }
    if ((isKotani && !useFlutterFallback) && !phone) { toast.error('Enter your phone number'); return }
    if ((isKotani && !useFlutterFallback) && !telco) { toast.error('Select your mobile network'); return }

    setLoading(true); setError(null); setStep('confirming')
    try {
      // ── Flutterwave (ZAR, USD, GBP, EUR + Kotani asset fallback) ──
      if (isFlutter || useFlutterFallback) {
        const res = await api.post('/api/v1/onramp/initialize', {
          amount_fiat: parseFloat(amount), currency, crypto_asset: asset, payment_method: 'auto',
        })
        const data = res.data || res
        if (data?.success && data?.checkout_url) {
          setStep('redirecting')
          toast.success('Redirecting to payment...')
          setTimeout(() => { window.location.href = data.checkout_url }, 500)
        } else {
          throw new Error(data?.detail || 'Payment link not generated')
        }
        return
      }

      // ── Busha (NGN, KES) ──────────────────────────────────────────
      if (isBusha) {
        const res = await api.post('/api/v1/busha/onramp/initialize', {
          amount_fiat: parseFloat(amount), currency, crypto_asset: asset,
        })
        if (!res?.success) throw new Error(res?.message || 'Initialization failed')
        setTxResult(res); setStep('pay_bank')
        return
      }

      // ── Kotani Pay (GHS, UGX, TZS, RWF, ZMW, XOF, XAF) ──────────
      if (isKotani) {
        const res = await api.post('/api/v1/kotani/onramp/initialize', {
          amount_fiat: parseFloat(amount), currency, crypto_asset: asset,
          phone_number: phone, telco_id: telco,
        })
        if (!res?.success) throw new Error(res?.message || 'Initialization failed')
        setTxResult(res); setStep('pay_stk')
        return
      }

    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || 'Failed'
      setError(msg); toast.error(msg); setStep('configure')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true); toast.success('Copied!')
    setTimeout(() => setCopied(false), 2000)
  }, [])

  // Provider badge text
  const providerBadge = (() => {
    if (useFlutterFallback) return '⚡ Flutterwave (asset fallback)'
    const primary = PROVIDER_LABEL[selectedCurrency.provider]
    return selectedCurrency.backup ? `${primary} · ${selectedCurrency.backup}` : primary
  })()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] max-w-md max-h-[92dvh] overflow-y-auto rounded-2xl p-0 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 shadow-2xl">

        {/* ── Sticky Header ── */}
        <div className="sticky top-0 z-10 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 px-5 pt-5 pb-4 rounded-t-2xl">
          <DialogClose className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </DialogClose>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg font-bold text-gray-900 dark:text-white">
              <div className="p-2 rounded-xl bg-blue-50 dark:bg-blue-900/30">
                <Wallet className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              Buy Crypto
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Pay with local currency · crypto lands in your Seamount wallet.
            </DialogDescription>
          </DialogHeader>
        </div>

        {/* ── Body ── */}
        <div className="px-5 py-4 space-y-4">

          {/* CONFIGURE / CONFIRMING */}
          {(step === 'configure' || step === 'confirming') && (
            <>
              {/* Currency */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Your Currency</Label>
                <Select value={currency} onValueChange={setCurrency}>
                  <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="max-h-72 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                    {CURRENCIES.map(c => (
                      <SelectItem key={c.code} value={c.code} className="py-2.5 text-gray-900 dark:text-white">
                        <span className="mr-2">{c.flag}</span>
                        <span className="font-medium">{c.code}</span>
                        <span className="ml-2 text-xs text-gray-400">{c.name}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {/* Provider badge — always visible */}
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  ⚡ <span className="font-medium text-gray-600 dark:text-gray-300">{providerBadge}</span>
                </p>
              </div>

              {/* Asset */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Asset to Receive</Label>
                <Select value={asset} onValueChange={setAsset}>
                  <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="max-h-72 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                    {Object.entries(ASSET_GROUPS).map(([chain, assets]) => (
                      <div key={chain}>
                        <div className="px-3 py-1.5 text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest bg-gray-50 dark:bg-gray-900">
                          {chain}
                        </div>
                        {(assets as any[]).map((a: any) => (
                          <SelectItem key={a.value} value={a.value} className="py-2.5 pl-6 text-sm text-gray-900 dark:text-white cursor-pointer">
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
                {isKotani && KOTANI_UNSUPPORTED.has(asset) && (
                  <p className="text-xs text-amber-600 dark:text-amber-400">
                    ⚠️ Algorand-native assets not supported by Kotani Pay — routing via Flutterwave instead.
                  </p>
                )}
              </div>

              {/* Amount */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Amount</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 dark:text-gray-400 font-semibold">
                    {selectedCurrency.symbol}
                  </span>
                  <Input
                    type="number" placeholder="0.00" value={amount}
                    onChange={e => setAmount(e.target.value)} disabled={loading}
                    className="pl-10 h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-base"
                  />
                </div>
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  Minimum: {selectedCurrency.symbol}{currency === 'NGN' ? '1,000' : '10'}
                </p>
              </div>

              {/* Kotani: phone + network — only for non-Flutterwave fallback */}
              {isKotani && !useFlutterFallback && (
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Mobile Network</Label>
                    <Select value={telco} onValueChange={setTelco}>
                      <SelectTrigger className="h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
                        <SelectValue placeholder="Select network" />
                      </SelectTrigger>
                      <SelectContent className="bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                        {telcos.map(t => (
                          <SelectItem key={t.id} value={t.id} className="text-gray-900 dark:text-white">{t.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Phone Number</Label>
                    <Input
                      type="tel" placeholder="e.g. 0712345678" value={phone}
                      onChange={e => setPhone(e.target.value)}
                      className="h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    />
                  </div>
                </div>
              )}

              {/* Live quote — Busha + Kotani only */}
              {fetchingQ && (
                <div className="flex items-center gap-2 py-1">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                  <span className="text-xs text-gray-400">Fetching quote...</span>
                </div>
              )}
              {quote && !fetchingQ && !useFlutterFallback && !isFlutter && (
                <div className="rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 p-3.5 space-y-2">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Live Quote</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">Seamount fee (2.5%)</span>
                    <span className="text-gray-600 dark:text-gray-300">
                      {isBusha
                        ? `${selectedCurrency.symbol}${parseFloat(quote.markup_amount || 0).toFixed(2)}`
                        : `${parseFloat(quote.markup_crypto || 0).toFixed(6)} ${asset.split('_')[0]}`
                      }
                    </span>
                  </div>
                  <div className="flex justify-between font-bold pt-1.5 border-t border-blue-200 dark:border-blue-700">
                    <span className="text-gray-800 dark:text-white text-sm">You Receive</span>
                    <span className="text-green-600 dark:text-green-400 text-sm">
                      {isBusha
                        ? `${parseFloat(quote.crypto_amount || 0).toFixed(6)} ${asset.split('_')[0]}`
                        : `${parseFloat(quote.net_crypto || 0).toFixed(6)} ${asset.split('_')[0]}`
                      }
                    </span>
                  </div>
                  {isBusha && (
                    <p className="text-xs text-gray-400 pt-1">
                      Total to pay: <strong>{selectedCurrency.symbol}{parseFloat(quote.gross_amount || 0).toFixed(2)}</strong>
                    </p>
                  )}
                </div>
              )}

              {/* Info banner */}
              <Alert className="border border-green-100 dark:border-green-900 bg-green-50 dark:bg-green-900/20 rounded-xl py-3">
                <Info className="h-4 w-4 text-green-600 shrink-0 mt-0.5" />
                <AlertDescription className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                  <strong className="text-green-700 dark:text-green-400">Smart routing</strong>
                  {' — best provider auto-selected for your currency. Crypto credited after payment.'}
                  {isBusha   && !useFlutterFallback && <span className="block mt-1 text-blue-600 dark:text-blue-400">🔵 {currency === 'NGN' ? 'Powered by Busha · Paystack (collection)' : 'Powered by Busha · M-Pesa'}</span>}
                  {isKotani  && !useFlutterFallback && <span className="block mt-1 text-purple-600 dark:text-purple-400">🟣 Powered by Kotani Pay</span>}
                  {(isFlutter || useFlutterFallback) && <span className="block mt-1 text-orange-600 dark:text-orange-400">🟠 Powered by Flutterwave</span>}
                </AlertDescription>
              </Alert>
            </>
          )}

          {/* PAY_BANK — Busha bank account details */}
          {step === 'pay_bank' && txResult && (
            <div className="space-y-4">
              <div className="text-center py-2">
                <CheckCircle2 className="h-10 w-10 text-green-500 mx-auto mb-2" />
                <p className="font-bold text-gray-900 dark:text-white">Transfer to this account</p>
                <p className="text-sm text-gray-500 mt-1">Crypto credited automatically after payment clears.</p>
              </div>
              <div className="rounded-xl border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20 divide-y divide-blue-100 dark:divide-blue-800 overflow-hidden">
                {[
                  { label: 'Bank Name',      value: txResult.pay_in_details?.bank_name,                         copyable: false },
                  { label: 'Account Number', value: txResult.pay_in_details?.account_number,                    copyable: true  },
                  { label: 'Account Name',   value: txResult.pay_in_details?.account_name,                      copyable: false },
                  { label: 'Amount to Pay',  value: `${selectedCurrency.symbol}${txResult.pay_in_details?.amount?.toFixed(2)}`, copyable: false },
                ].map(row => (
                  <div key={row.label} className="flex justify-between items-center px-4 py-3">
                    <span className="text-xs text-gray-500">{row.label}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-900 dark:text-white">{row.value}</span>
                      {row.copyable && (
                        <button onClick={() => copyToClipboard(row.value!)} className="text-blue-500 hover:text-blue-700">
                          {copied ? <CheckCircle2 className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <Alert className="border border-amber-200 bg-amber-50 rounded-xl py-3">
                <Info className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                <AlertDescription className="text-xs text-amber-800 leading-relaxed">
                  Transfer <strong>exactly</strong> the amount shown before{' '}
                  <strong>{txResult.pay_in_details?.expires_at ? new Date(txResult.pay_in_details.expires_at).toLocaleTimeString() : 'expiry'}</strong>.
                </AlertDescription>
              </Alert>
            </div>
          )}

          {/* PAY_STK — Kotani STK push */}
          {step === 'pay_stk' && txResult && (
            <div className="space-y-4 text-center py-4">
              <div className="p-4 rounded-full bg-green-50 dark:bg-green-900/20 w-20 h-20 mx-auto flex items-center justify-center">
                <Smartphone className="h-10 w-10 text-green-600 animate-pulse" />
              </div>
              <p className="font-bold text-lg text-gray-900 dark:text-white">Check Your Phone</p>
              <p className="text-sm text-gray-500 leading-relaxed px-4">
                A payment request has been sent to <strong>{txResult.pay_in_details?.phone_number}</strong> via{' '}
                <strong>{txResult.pay_in_details?.telco}</strong>. Approve it to complete your purchase.
              </p>
              <div className="rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-3">
                <p className="text-xs text-gray-500">Amount</p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">
                  {selectedCurrency.symbol}{txResult.pay_in_details?.amount?.toFixed(2)} {currency}
                </p>
              </div>
              <p className="text-xs text-gray-400">Crypto will appear in your wallet within 2–5 minutes after approval.</p>
            </div>
          )}

          {/* REDIRECTING */}
          {step === 'redirecting' && (
            <div className="text-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-4" />
              <p className="text-sm text-gray-500">Redirecting to secure payment...</p>
            </div>
          )}

          {error && (
            <Alert variant="destructive" className="rounded-xl border py-3">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <AlertDescription className="text-xs">{error}</AlertDescription>
            </Alert>
          )}
        </div>

        {/* ── Sticky Footer ── */}
        <div className="sticky bottom-0 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 px-5 py-4 rounded-b-2xl space-y-3">
          <div className="flex gap-3">
            {(step === 'pay_bank' || step === 'pay_stk') ? (
              <Button onClick={() => onOpenChange(false)} className="w-full h-12 rounded-xl font-bold bg-green-600 hover:bg-green-700 text-white">
                Done
              </Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}
                  className="flex-1 h-12 rounded-xl border-gray-200 dark:border-gray-700 font-semibold">
                  Cancel
                </Button>
                <Button
                  onClick={handleConfirm}
                  disabled={
                    loading || step === 'redirecting' ||
                    !amount || parseFloat(amount) <= 0 ||
                    (isKotani && !useFlutterFallback && (!phone || !telco)) ||
                    fetchingQ
                  }
                  className="flex-[2] h-12 rounded-xl font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading
                    ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Processing...</>
                    : <><Wallet className="mr-2 h-4 w-4" />Pay {selectedCurrency.symbol}{amount || '0'}</>
                  }
                </Button>
              </>
            )}
          </div>
          {(step === 'configure' || step === 'confirming') && (
            <div className="text-center">
              <button
                onClick={() => { onOpenChange(false); navigate('/payments?tab=p2p') }}
                className="text-xs text-gray-400 hover:text-green-500 transition-colors underline underline-offset-2"
              >
                💰 Or buy via P2P — as low as 0.3% fee
              </button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}