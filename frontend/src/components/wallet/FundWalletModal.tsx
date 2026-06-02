// File: frontend/src/components/wallet/FundWalletModal.tsx
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button.tsx'
import { Input } from '@/components/ui/input.tsx'
import { Label } from '@/components/ui/label.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog.tsx'
import { Loader2, Wallet, Info, AlertCircle, Copy, CheckCircle2, Smartphone } from 'lucide-react'

// ── Types ──────────────────────────────────────────────────────────────────────
type Step = 'configure' | 'confirming' | 'pay_bank' | 'pay_stk' | 'redirecting'

interface PayInBankDetails {
  account_number: string
  account_name:   string
  bank_name:      string
  amount:         number
  currency:       string
  expires_at:     string
  reference:      string
}

interface FundWalletModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// ── Currency catalogue ────────────────────────────────────────────────────────
const CURRENCIES = [
  { code: 'NGN', name: 'Nigerian Naira',      symbol: '₦',    flag: '🇳🇬', provider: 'busha',       pay_in: 'bank_account' },
  { code: 'KES', name: 'Kenyan Shilling',     symbol: 'KSh',  flag: '🇰🇪', provider: 'busha',       pay_in: 'bank_account' },
  { code: 'GHS', name: 'Ghanaian Cedi',       symbol: 'GH₵',  flag: '🇬🇭', provider: 'kotani',      pay_in: 'stk_push'     },
  { code: 'UGX', name: 'Ugandan Shilling',    symbol: 'USh',  flag: '🇺🇬', provider: 'kotani',      pay_in: 'stk_push'     },
  { code: 'TZS', name: 'Tanzanian Shilling',  symbol: 'TSh',  flag: '🇹🇿', provider: 'kotani',      pay_in: 'stk_push'     },
  { code: 'RWF', name: 'Rwandan Franc',       symbol: 'FRw',  flag: '🇷🇼', provider: 'kotani',      pay_in: 'stk_push'     },
  { code: 'ZMW', name: 'Zambian Kwacha',      symbol: 'ZK',   flag: '🇿🇲', provider: 'kotani',      pay_in: 'stk_push'     },
  { code: 'ZAR', name: 'South African Rand',  symbol: 'R',    flag: '🇿🇦', provider: 'flutterwave', pay_in: 'redirect'     },
]

const PROVIDER_LABEL: Record<string, string> = {
  busha:       'Busha',
  kotani:      'Kotani Pay',
  flutterwave: 'Flutterwave',
}

// ── Asset catalogue ───────────────────────────────────────────────────────────
const ASSET_GROUPS = {
  '🟢 Algorand': [
    { value: 'ALGO',  label: 'Algorand (ALGO)',  icon: 'Ⱥ' },
  ],
  '🟠 Bitcoin': [
    { value: 'BTC',   label: 'Bitcoin (BTC)',    icon: '₿' },
  ],
  '🔵 Ethereum': [
    { value: 'ETH',      label: 'Ethereum (ETH)',      icon: 'Ξ'  },
    { value: 'USDT_ETH', label: 'Tether (Ethereum)',   icon: '₮'  },
    { value: 'USDC_ETH', label: 'USD Coin (Ethereum)', icon: '◎'  },
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

// Kotani supports subset of assets
const KOTANI_SUPPORTED = new Set([
  'USDT_TRON', 'USDT_ETH', 'USDT_POLYGON', 'USDC_ETH', 'USDC_POLYGON',
  'ETH', 'BTC', 'SOL', 'USDT_SOLANA',
])

const KOTANI_TELCOS: Record<string, { id: string; name: string }[]> = {
  KES: [{ id: 'MPESA', name: 'M-Pesa' }, { id: 'AIRTEL', name: 'Airtel Money' }],
  GHS: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'VODAFONE', name: 'Vodafone Cash' }, { id: 'AIRTELTIGO', name: 'AirtelTigo' }],
  UGX: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'AIRTEL', name: 'Airtel Money' }],
  TZS: [{ id: 'MPESA', name: 'M-Pesa' }, { id: 'AIRTEL', name: 'Airtel' }, { id: 'TIGO', name: 'Tigo Cash' }],
  RWF: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'AIRTEL', name: 'Airtel Money' }],
  ZMW: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'AIRTEL', name: 'Airtel Money' }, { id: 'ZAMTEL', name: 'Zamtel' }],
}

// ── Component ─────────────────────────────────────────────────────────────────
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

  const selectedCurrency = CURRENCIES.find(c => c.code === currency)!
  const isKotani         = selectedCurrency.provider === 'kotani'
  const isBusha          = selectedCurrency.provider === 'busha'
  const isFlutter        = selectedCurrency.provider === 'flutterwave'
  const telcos           = KOTANI_TELCOS[currency] ?? []

  // Reset on open / currency change
  useEffect(() => {
    if (!open) { setStep('configure'); setQuote(null); setError(null); return }
    const pre = sessionStorage.getItem('preselected_asset')
    if (pre) { setAsset(pre); sessionStorage.removeItem('preselected_asset') }
  }, [open])

  useEffect(() => {
    setQuote(null); setError(null); setTelco('')
    // Reset asset to supported one if switching to Kotani
    if (isKotani && !KOTANI_SUPPORTED.has(asset)) setAsset('USDT_TRON')
  }, [currency])

  useEffect(() => { setQuote(null) }, [asset, amount])

  // Debounced quote fetch
  useEffect(() => {
    if (!amount || parseFloat(amount) <= 0) { setQuote(null); return }
    const t = setTimeout(fetchQuote, 600)
    return () => clearTimeout(t)
  }, [amount, currency, asset])

  const fetchQuote = async () => {
    if (!amount || parseFloat(amount) <= 0) return
    setFetchingQ(true); setError(null)
    try {
      const endpoint = isBusha
        ? '/api/v1/busha/onramp/quote'
        : '/api/v1/kotani/onramp/quote'
      const res = await api.post(endpoint, {
        amount_fiat:  parseFloat(amount),
        currency,
        crypto_asset: asset,
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
    if (isKotani && !phone) { toast.error('Enter your phone number'); return }
    if (isKotani && !telco) { toast.error('Select your mobile network'); return }

    setLoading(true); setError(null); setStep('confirming')
    try {
      if (isFlutter) {
        // Flutterwave: existing redirect flow
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

      const endpoint = isBusha
        ? '/api/v1/busha/onramp/initialize'
        : '/api/v1/kotani/onramp/initialize'

      const body: any = { amount_fiat: parseFloat(amount), currency, crypto_asset: asset }
      if (isKotani) { body.phone_number = phone; body.telco_id = telco }

      const res = await api.post(endpoint, body)
      if (!res?.success) throw new Error(res?.message || 'Initialization failed')

      setTxResult(res)
      setStep(res.pay_in_type === 'bank_account' ? 'pay_bank' : 'pay_stk')

    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || 'Failed'
      setError(msg); toast.error(msg); setStep('configure')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    toast.success('Copied!')
    setTimeout(() => setCopied(false), 2000)
  }, [])

  const activeAssets = isKotani
    ? Object.fromEntries(
        Object.entries(ASSET_GROUPS).map(([k, v]) => [k, v.filter(a => KOTANI_SUPPORTED.has(a.value))])
      )
    : ASSET_GROUPS

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] max-w-md max-h-[92dvh] overflow-y-auto rounded-2xl p-0 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 shadow-2xl">

        {/* Header */}
        <div className="sticky top-0 z-10 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 px-5 pt-5 pb-4 rounded-t-2xl">
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

        {/* Body */}
        <div className="px-5 py-4 space-y-4">

          {/* ── CONFIGURE step ────────────────────────────────────────── */}
          {(step === 'configure' || step === 'confirming') && (
            <>
              {/* Currency */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Your Currency</Label>
                <Select value={currency} onValueChange={setCurrency}>
                  <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
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
                <p className="text-xs text-gray-400">
                  Powered by <span className="font-medium text-gray-500">{PROVIDER_LABEL[selectedCurrency.provider]}</span>
                </p>
              </div>

              {/* Asset */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Asset to Receive</Label>
                <Select value={asset} onValueChange={setAsset}>
                  <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="max-h-72 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                    {Object.entries(activeAssets).map(([chain, assets]) => (
                      <div key={chain}>
                        <div className="px-3 py-1.5 text-[10px] font-bold text-gray-400 uppercase tracking-widest bg-gray-50 dark:bg-gray-900">{chain}</div>
                        {(assets as any[]).map((a: any) => (
                          <SelectItem key={a.value} value={a.value} className="py-2.5 pl-6 text-sm text-gray-900 dark:text-white">
                            <span className="mr-2">{a.icon}</span>{a.label}
                          </SelectItem>
                        ))}
                      </div>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Amount */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Amount</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-semibold">
                    {selectedCurrency.symbol}
                  </span>
                  <Input
                    type="number" placeholder="0.00" value={amount}
                    onChange={e => setAmount(e.target.value)} disabled={loading}
                    className="pl-10 h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800"
                  />
                </div>
              </div>

              {/* Kotani: phone + telco */}
              {isKotani && (
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Mobile Network</Label>
                    <Select value={telco} onValueChange={setTelco}>
                      <SelectTrigger className="h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                        <SelectValue placeholder="Select network" />
                      </SelectTrigger>
                      <SelectContent className="bg-white dark:bg-gray-800 z-[9999]">
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
                      className="h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800"
                    />
                  </div>
                </div>
              )}

              {/* Live quote */}
              {fetchingQ && (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                  <span className="text-xs text-gray-400">Fetching quote...</span>
                </div>
              )}
              {quote && !fetchingQ && (
                <div className="rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 p-3.5 space-y-2">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Live Quote</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Seamount fee (2.5%)</span>
                    <span className="text-gray-600">
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
                      You will pay <strong>{selectedCurrency.symbol}{parseFloat(quote.gross_amount || 0).toFixed(2)}</strong> total to the bank account shown next.
                    </p>
                  )}
                </div>
              )}

              <Alert className="border border-green-100 dark:border-green-900 bg-green-50 dark:bg-green-900/20 rounded-xl py-3">
                <Info className="h-4 w-4 text-green-600 shrink-0 mt-0.5" />
                <AlertDescription className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                  {isBusha && 'A temporary bank account will be generated. Transfer the exact amount shown to complete your purchase.'}
                  {isKotani && 'A payment request will be sent to your phone. Approve it to complete the purchase.'}
                  {isFlutter && 'You will be redirected to a secure payment page to complete your purchase.'}
                </AlertDescription>
              </Alert>
            </>
          )}

          {/* ── BANK ACCOUNT pay-in (Busha) ───────────────────────────── */}
          {step === 'pay_bank' && txResult && (
            <div className="space-y-4">
              <div className="text-center py-2">
                <CheckCircle2 className="h-10 w-10 text-green-500 mx-auto mb-2" />
                <p className="font-bold text-gray-900 dark:text-white">Transfer to this account</p>
                <p className="text-sm text-gray-500 mt-1">Crypto will be credited automatically after payment clears.</p>
              </div>
              <div className="rounded-xl border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20 divide-y divide-blue-100 dark:divide-blue-800 overflow-hidden">
                {[
                  { label: 'Bank Name',       value: txResult.pay_in_details?.bank_name },
                  { label: 'Account Number',  value: txResult.pay_in_details?.account_number, copyable: true },
                  { label: 'Account Name',    value: txResult.pay_in_details?.account_name },
                  { label: 'Amount to Pay',   value: `${selectedCurrency.symbol}${txResult.pay_in_details?.amount?.toFixed(2)}` },
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
                  Transfer <strong>exactly</strong> the amount shown. The account expires — complete your transfer before{' '}
                  <strong>{txResult.pay_in_details?.expires_at
                    ? new Date(txResult.pay_in_details.expires_at).toLocaleTimeString()
                    : 'it expires'}</strong>.
                </AlertDescription>
              </Alert>
            </div>
          )}

          {/* ── STK push (Kotani) ─────────────────────────────────────── */}
          {step === 'pay_stk' && txResult && (
            <div className="space-y-4 text-center py-4">
              <div className="p-4 rounded-full bg-green-50 dark:bg-green-900/20 w-20 h-20 mx-auto flex items-center justify-center">
                <Smartphone className="h-10 w-10 text-green-600 animate-pulse" />
              </div>
              <p className="font-bold text-lg text-gray-900 dark:text-white">Check Your Phone</p>
              <p className="text-sm text-gray-500 leading-relaxed px-4">
                A payment request has been sent to <strong>{txResult.pay_in_details?.phone_number}</strong> via <strong>{txResult.pay_in_details?.telco}</strong>.
                Approve it to complete your purchase.
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

          {/* ── Redirecting ───────────────────────────────────────────── */}
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

        {/* Footer */}
        <div className="sticky bottom-0 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 px-5 py-4 rounded-b-2xl flex gap-3">
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
                  loading || step === 'redirecting' || !amount || parseFloat(amount) <= 0 ||
                  (isKotani && (!phone || !telco)) || fetchingQ
                }
                className="flex-[2] h-12 rounded-xl font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                {loading
                  ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Processing...</>
                  : `Buy ${asset.split('_')[0]}`
                }
              </Button>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}