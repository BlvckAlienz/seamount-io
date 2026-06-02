// File: frontend/src/components/wallet/WithdrawModal.tsx
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import { useWallet } from '@/contexts/WalletContext'
import { Button } from '@/components/ui/button.tsx'
import { Input } from '@/components/ui/input.tsx'
import { Label } from '@/components/ui/label.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog.tsx'
import { Loader2, ArrowDownToLine, Info, AlertCircle, CheckCircle2, Building2, Smartphone } from 'lucide-react'

// ── Types ──────────────────────────────────────────────────────────────────────
type Step = 'configure' | 'submitting' | 'processing' | 'done'

interface WithdrawModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// ── Currency catalogue ─────────────────────────────────────────────────────────
const CURRENCIES = [
  { code: 'NGN', name: 'Nigerian Naira',     symbol: '₦',    flag: '🇳🇬', provider: 'busha',       payout: 'bank_transfer' },
  { code: 'KES', name: 'Kenyan Shilling',    symbol: 'KSh',  flag: '🇰🇪', provider: 'busha',       payout: 'mobile_money'  },
  { code: 'GHS', name: 'Ghanaian Cedi',      symbol: 'GH₵',  flag: '🇬🇭', provider: 'kotani',      payout: 'mobile_money'  },
  { code: 'UGX', name: 'Ugandan Shilling',   symbol: 'USh',  flag: '🇺🇬', provider: 'kotani',      payout: 'mobile_money'  },
  { code: 'TZS', name: 'Tanzanian Shilling', symbol: 'TSh',  flag: '🇹🇿', provider: 'kotani',      payout: 'mobile_money'  },
  { code: 'RWF', name: 'Rwandan Franc',      symbol: 'FRw',  flag: '🇷🇼', provider: 'kotani',      payout: 'mobile_money'  },
  { code: 'ZMW', name: 'Zambian Kwacha',     symbol: 'ZK',   flag: '🇿🇲', provider: 'kotani',      payout: 'mobile_money'  },
  { code: 'ZAR', name: 'South African Rand', symbol: 'R',    flag: '🇿🇦', provider: 'flutterwave', payout: 'bank_transfer' },
]

const PROVIDER_LABEL: Record<string, string> = {
  busha: 'Busha', kotani: 'Kotani Pay', flutterwave: 'Flutterwave',
}

// ── Asset catalogue ────────────────────────────────────────────────────────────
const ASSET_GROUPS = {
  '🟢 Algorand':  [{ value: 'ALGO', label: 'Algorand (ALGO)', icon: 'Ⱥ' }],
  '🟠 Bitcoin':   [{ value: 'BTC',  label: 'Bitcoin (BTC)',   icon: '₿' }],
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

// Assets NOT supported by Busha/Kotani offramp (Algorand-native only)
const OFFRAMP_UNSUPPORTED = new Set(['ALGO', 'USDT_ALGO', 'USDCa', 'goBTC', 'goETH'])

const KOTANI_TELCOS: Record<string, { id: string; name: string }[]> = {
  KES: [{ id: 'MPESA', name: 'M-Pesa' }, { id: 'AIRTEL', name: 'Airtel Money' }],
  GHS: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'VODAFONE', name: 'Vodafone Cash' }, { id: 'AIRTELTIGO', name: 'AirtelTigo' }],
  UGX: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'AIRTEL', name: 'Airtel Money' }],
  TZS: [{ id: 'MPESA', name: 'M-Pesa' }, { id: 'AIRTEL', name: 'Airtel' }, { id: 'TIGO', name: 'Tigo Cash' }],
  RWF: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'AIRTEL', name: 'Airtel Money' }],
  ZMW: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'AIRTEL', name: 'Airtel Money' }, { id: 'ZAMTEL', name: 'Zamtel' }],
}

const NIGERIAN_BANKS = [
  { code: '044', name: 'Access Bank' },  { code: '058', name: 'GTBank' },
  { code: '011', name: 'First Bank' },   { code: '057', name: 'Zenith Bank' },
  { code: '033', name: 'UBA' },          { code: '032', name: 'Union Bank' },
  { code: '070', name: 'Fidelity Bank' },{ code: '035', name: 'Wema Bank' },
  { code: '050', name: 'Ecobank' },      { code: '232', name: 'Sterling Bank' },
  { code: '999240', name: 'Kuda Bank' }, { code: '120001', name: 'Opay' },
  { code: '100033', name: 'Palmpay' },   { code: '120003', name: 'Moniepoint MFB' },
  { code: '214', name: 'FCMB' },         { code: '221', name: 'Stanbic IBTC' },
]

// ── Component ──────────────────────────────────────────────────────────────────
export function WithdrawModal({ open, onOpenChange }: WithdrawModalProps) {
  const [step, setStep]           = useState<Step>('configure')
  const [asset, setAsset]         = useState('USDT_TRON')
  const [currency, setCurrency]   = useState('NGN')
  const [amount, setAmount]       = useState('')
  // Bank fields (NGN)
  const [bankCode, setBankCode]   = useState('')
  const [bankAccount, setBankAccount] = useState('')
  const [accountName, setAccountName] = useState<string | null>(null)
  const [verifying, setVerifying] = useState(false)
  // Mobile money fields
  const [phone, setPhone]         = useState('')
  const [telco, setTelco]         = useState('')
  // State
  const [quote, setQuote]         = useState<any>(null)
  const [loading, setLoading]     = useState(false)
  const [fetchingQ, setFetchingQ] = useState(false)
  const [error, setError]         = useState<string | null>(null)

  const { session }  = useAuth()
  const { balances } = useWallet()

  const selectedCurrency = CURRENCIES.find(c => c.code === currency)!
  const isBusha          = selectedCurrency.provider === 'busha'
  const isKotani         = selectedCurrency.provider === 'kotani'
  const isFlutter        = selectedCurrency.provider === 'flutterwave'
  const isBankPayout     = selectedCurrency.payout === 'bank_transfer'
  const telcos           = KOTANI_TELCOS[currency] ?? []
  const assetSymbol      = asset.split('_')[0]
  const availableBalance = balances?.[asset]?.balance ?? 0
  const isUnsupported    = OFFRAMP_UNSUPPORTED.has(asset)

  useEffect(() => {
    if (!open) { setStep('configure'); setQuote(null); setError(null); return }
  }, [open])

  useEffect(() => {
    setQuote(null); setAccountName(null); setError(null)
    setBankCode(''); setBankAccount(''); setPhone(''); setTelco('')
  }, [currency])

  useEffect(() => { setQuote(null) }, [asset, amount])

  // Debounced quote
  useEffect(() => {
    if (!amount || parseFloat(amount) <= 0) { setQuote(null); return }
    const t = setTimeout(fetchQuote, 600)
    return () => clearTimeout(t)
  }, [amount, currency, asset])

  const fetchQuote = async () => {
    if (!amount || parseFloat(amount) <= 0 || isUnsupported) return
    setFetchingQ(true); setError(null)
    try {
      const endpoint = isBusha ? '/api/v1/busha/offramp/quote' : '/api/v1/kotani/offramp/quote'
      const res = await api.post(endpoint, {
        crypto_asset:  asset,
        crypto_amount: parseFloat(amount),
        currency,
      })
      if (res?.success) setQuote(res)
      else setError(res?.message || 'Failed to fetch quote')
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Quote failed')
    } finally {
      setFetchingQ(false)
    }
  }

  const verifyBank = async () => {
    if (!bankAccount || !bankCode) return
    setVerifying(true); setAccountName(null)
    try {
      const res = await api.post('/api/v1/bank-verification/verify', {
        account_number: bankAccount, bank_code: bankCode, currency,
      })
      if (res?.success && res?.account_name) {
        setAccountName(res.account_name)
        toast.success(`Verified: ${res.account_name}`)
      } else {
        toast.error('Account not found. Check details.')
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Verification failed')
    } finally {
      setVerifying(false)
    }
  }

  const handleWithdraw = async () => {
    if (!session)                              { toast.error('Sign in to continue'); return }
    if (!amount || parseFloat(amount) <= 0)    { toast.error('Enter a valid amount'); return }
    if (parseFloat(amount) > availableBalance) { toast.error('Insufficient balance'); return }
    if (isBusha && isBankPayout && !accountName) { toast.error('Verify your bank account first'); return }
    if ((isBusha && !isBankPayout || isKotani) && (!phone || !telco)) {
      toast.error('Enter phone number and select network'); return
    }
    if (isUnsupported) { toast.error('Swap to a supported asset before withdrawing'); return }

    setLoading(true); setError(null); setStep('submitting')
    try {
      if (isFlutter) {
        // Existing Flutterwave offramp
        const res = await api.post('/api/v1/offramp/initialize', {
          crypto_asset: asset, amount_crypto: parseFloat(amount),
          currency, payout_method: 'bank_transfer',
          bank_code: bankCode, bank_account: bankAccount, account_name: accountName,
        })
        const data = res.data || res
        if (data?.success) {
          setStep('done')
          toast.success('Withdrawal initiated!')
        } else {
          throw new Error(data?.detail || 'Withdrawal failed')
        }
        return
      }

      if (isBusha) {
        const body: any = {
          crypto_asset: asset, crypto_amount: parseFloat(amount), currency,
        }
        if (isBankPayout) {
          body.bank_code      = bankCode
          body.account_number = bankAccount
          body.account_name   = accountName
        } else {
          body.phone_number = phone
        }
        const res = await api.post('/api/v1/busha/offramp/initialize', body)
        if (!res?.success) throw new Error(res?.message || 'Withdrawal failed')
        setStep('done')
        toast.success('Withdrawal submitted! Funds arriving in 5–15 minutes.')
        return
      }

      if (isKotani) {
        const res = await api.post('/api/v1/kotani/offramp/initialize', {
          crypto_asset: asset, crypto_amount: parseFloat(amount),
          currency, phone_number: phone, telco_id: telco,
        })
        if (!res?.success) throw new Error(res?.message || 'Withdrawal failed')
        setStep('done')
        toast.success('Withdrawal submitted! Funds arriving via mobile money in 2–10 minutes.')
        return
      }

    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || 'Withdrawal failed'
      setError(msg); toast.error(msg); setStep('configure')
    } finally {
      setLoading(false)
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] max-w-md max-h-[92dvh] overflow-y-auto rounded-2xl p-0 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 shadow-2xl">

        {/* Header */}
        <div className="sticky top-0 z-10 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 px-5 pt-5 pb-4 rounded-t-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg font-bold text-gray-900 dark:text-white">
              <div className="p-2 rounded-xl bg-red-50 dark:bg-red-900/30">
                <ArrowDownToLine className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
              Sell Crypto
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Convert crypto to local currency. Sent directly to your bank or mobile wallet.
            </DialogDescription>
          </DialogHeader>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">

          {/* ── CONFIGURE / SUBMITTING ─────────────────────────────────── */}
          {(step === 'configure' || step === 'submitting') && (
            <>
              {/* Currency */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Receive In</Label>
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
                  {' · '}{isBankPayout ? 'Bank transfer' : 'Mobile money'}
                </p>
              </div>

              {/* Asset */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Asset to Sell</Label>
                <Select value={asset} onValueChange={v => { setAsset(v); setQuote(null) }}>
                  <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="max-h-72 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                    {Object.entries(ASSET_GROUPS).map(([chain, assets]) => (
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

                {/* Balance chip */}
                {availableBalance > 0 ? (
                  <div className="flex justify-between items-center px-3 py-2 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-100 dark:border-green-800">
                    <span className="text-xs text-gray-500">Available</span>
                    <span className="text-sm font-bold text-green-700 dark:text-green-400">
                      {availableBalance.toFixed(6)} {assetSymbol}
                    </span>
                  </div>
                ) : (
                  <div className="px-3 py-2 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-800">
                    <span className="text-xs text-amber-700">No {assetSymbol} balance — buy first.</span>
                  </div>
                )}

                {isUnsupported && (
                  <Alert className="rounded-xl border border-amber-200 bg-amber-50 py-2">
                    <AlertCircle className="h-4 w-4 text-amber-600 shrink-0" />
                    <AlertDescription className="text-xs text-amber-800">
                      {assetSymbol} cannot be sold directly via fiat offramp. Swap it to USDT first, then withdraw.
                    </AlertDescription>
                  </Alert>
                )}
              </div>

              {/* Amount */}
              {!isUnsupported && (
                <div className="space-y-1.5">
                  <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Amount ({assetSymbol})
                  </Label>
                  <div className="flex gap-2">
                    <Input
                      type="number" placeholder="0.000000" value={amount}
                      onChange={e => setAmount(e.target.value)} disabled={loading}
                      className="flex-1 h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800"
                    />
                    <Button
                      variant="outline" type="button"
                      onClick={() => setAmount(availableBalance.toFixed(6))}
                      disabled={availableBalance <= 0}
                      className="h-12 px-4 rounded-xl border-2 border-gray-200 dark:border-gray-700 text-xs font-semibold"
                    >
                      MAX
                    </Button>
                  </div>
                </div>
              )}

              {/* Quote */}
              {fetchingQ && (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                  <span className="text-xs text-gray-400">Fetching quote...</span>
                </div>
              )}
              {quote && !fetchingQ && (
                <div className="rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800 p-3.5 space-y-2">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Live Quote</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Seamount fee (2.5%)</span>
                    <span className="text-gray-600">
                      {isBusha
                        ? `${selectedCurrency.symbol}${parseFloat(quote.markup_amount || 0).toFixed(2)}`
                        : `${parseFloat(quote.markup_crypto || 0).toFixed(6)} ${assetSymbol}`
                      }
                    </span>
                  </div>
                  <div className="flex justify-between font-bold pt-1.5 border-t border-red-200 dark:border-red-700">
                    <span className="text-gray-800 dark:text-white text-sm">You Receive</span>
                    <span className="text-green-600 dark:text-green-400 text-sm">
                      {selectedCurrency.symbol}{parseFloat(quote.net_fiat || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              )}

              {/* ── NGN bank fields (Busha) ─────────────────────────── */}
              {isBusha && isBankPayout && (
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Bank</Label>
                    <Select value={bankCode} onValueChange={v => { setBankCode(v); setAccountName(null) }}>
                      <SelectTrigger className="h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                        <SelectValue placeholder="Select bank" />
                      </SelectTrigger>
                      <SelectContent className="max-h-[200px] bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                        {NIGERIAN_BANKS.map(b => (
                          <SelectItem key={b.code} value={b.code} className="text-gray-900 dark:text-white">{b.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Account Number</Label>
                    <div className="flex gap-2">
                      <Input
                        type="text" maxLength={10} placeholder="0123456789"
                        value={bankAccount}
                        onChange={e => { setBankAccount(e.target.value); setAccountName(null) }}
                        disabled={loading || verifying}
                        className="flex-1 h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800"
                      />
                      <Button
                        type="button" variant="outline" onClick={verifyBank}
                        disabled={!bankAccount || !bankCode || verifying || loading || bankAccount.length !== 10}
                        className="h-12 rounded-xl border-2 border-gray-200 dark:border-gray-700 font-semibold px-4"
                      >
                        {verifying ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Verify'}
                      </Button>
                    </div>
                  </div>
                  {accountName && (
                    <Alert className="rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 py-2.5">
                      <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />
                      <AlertDescription className="text-sm font-bold text-green-800 dark:text-green-200">
                        {accountName}
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              )}

              {/* ── KES mobile money (Busha) ────────────────────────── */}
              {isBusha && !isBankPayout && (
                <div className="space-y-1.5">
                  <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">M-Pesa Phone Number</Label>
                  <Input
                    type="tel" placeholder="e.g. 0712345678" value={phone}
                    onChange={e => setPhone(e.target.value)}
                    className="h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800"
                  />
                </div>
              )}

              {/* ── Mobile money (Kotani) ───────────────────────────── */}
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

              <Alert className="border border-green-100 dark:border-green-900 bg-green-50 dark:bg-green-900/20 rounded-xl py-3">
                <Info className="h-4 w-4 text-green-600 shrink-0 mt-0.5" />
                <AlertDescription className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                  {isBusha && isBankPayout  && 'Funds will be sent directly to your verified bank account within 5–15 minutes.'}
                  {isBusha && !isBankPayout && 'Funds will be sent to your M-Pesa wallet within 5–15 minutes.'}
                  {isKotani                  && 'Funds will be sent to your mobile money wallet within 2–10 minutes.'}
                  {isFlutter                 && 'Funds will be sent to your bank account via Flutterwave.'}
                </AlertDescription>
              </Alert>
            </>
          )}

          {/* ── DONE ──────────────────────────────────────────────────── */}
          {step === 'done' && (
            <div className="text-center py-6 space-y-3">
              <div className="p-4 rounded-full bg-green-50 dark:bg-green-900/20 w-20 h-20 mx-auto flex items-center justify-center">
                <CheckCircle2 className="h-10 w-10 text-green-600" />
              </div>
              <p className="font-bold text-lg text-gray-900 dark:text-white">Withdrawal Submitted</p>
              <p className="text-sm text-gray-500 px-4">
                {isBankPayout
                  ? 'Funds will arrive in your bank account within 5–15 minutes.'
                  : 'Funds will arrive in your mobile wallet within 2–10 minutes.'}
              </p>
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
          {step === 'done' ? (
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
                onClick={handleWithdraw}
                disabled={
                  loading || availableBalance <= 0 || isUnsupported ||
                  !amount || parseFloat(amount) <= 0 || parseFloat(amount) > availableBalance ||
                  (isBusha && isBankPayout && !accountName) ||
                  (isBusha && !isBankPayout && !phone) ||
                  (isKotani && (!phone || !telco)) ||
                  fetchingQ
                }
                className="flex-[2] h-12 rounded-xl font-bold text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
              >
                {loading
                  ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Processing...</>
                  : quote
                    ? `Receive ${selectedCurrency.symbol}${parseFloat(quote.net_fiat || 0).toFixed(2)}`
                    : `Sell ${assetSymbol}`
                }
              </Button>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}