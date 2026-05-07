// File: frontend/src/components/wallet/WithdrawModal.tsx
import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { loadMoonPay } from '@moonpay/moonpay-js'
import { api } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import { useWallet } from '@/contexts/WalletContext'
import { Button } from '@/components/ui/button.tsx'
import { Input } from '@/components/ui/input.tsx'
import { Label } from '@/components/ui/label.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import {
  Dialog, DialogContent, DialogDescription,
  DialogHeader, DialogTitle,
} from '@/components/ui/dialog.tsx'
import {
  Loader2, ArrowDownToLine, Info, AlertCircle, ShieldCheck,
  Globe, Banknote, Building2, Smartphone, CheckCircle2,
} from 'lucide-react'

interface WithdrawModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Provider = 'local' | 'moonpay'

// ── MoonPay sell assets (ALGO excluded — not supported) ───────────
const MOONPAY_ASSET_GROUPS = {
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

// ── Local provider: all assets ────────────────────────────────────
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
  { code: 'NGN', name: 'Nigerian Naira',     symbol: '₦',   flag: '🇳🇬', methods: ['bank_transfer'],              mobile_providers: [] },
  { code: 'KES', name: 'Kenyan Shilling',    symbol: 'KSh', flag: '🇰🇪', methods: ['bank_transfer','mobile_money'], mobile_providers: ['mpesa','airtel'] },
  { code: 'GHS', name: 'Ghanaian Cedi',      symbol: 'GH₵', flag: '🇬🇭', methods: ['bank_transfer','mobile_money'], mobile_providers: ['mtn','vodafone','airteltigo'] },
  { code: 'ZAR', name: 'South African Rand', symbol: 'R',   flag: '🇿🇦', methods: ['bank_transfer'],              mobile_providers: [] },
  { code: 'UGX', name: 'Ugandan Shilling',   symbol: 'USh', flag: '🇺🇬', methods: ['mobile_money'],              mobile_providers: ['mtn','airtel'] },
  { code: 'TZS', name: 'Tanzanian Shilling', symbol: 'TSh', flag: '🇹🇿', methods: ['mobile_money'],              mobile_providers: ['mpesa','airtel','tigo'] },
  { code: 'RWF', name: 'Rwandan Franc',      symbol: 'FRw', flag: '🇷🇼', methods: ['mobile_money'],              mobile_providers: ['mtn','airtel'] },
  { code: 'ZMW', name: 'Zambian Kwacha',     symbol: 'ZK',  flag: '🇿🇲', methods: ['mobile_money'],              mobile_providers: ['mtn','airtel','zamtel'] },
]

const MOONPAY_FIAT = [
  { code: 'USD', flag: '🇺🇸' }, { code: 'EUR', flag: '🇪🇺' }, { code: 'GBP', flag: '🇬🇧' },
  { code: 'NGN', flag: '🇳🇬' }, { code: 'KES', flag: '🇰🇪' }, { code: 'GHS', flag: '🇬🇭' },
  { code: 'ZAR', flag: '🇿🇦' },
]

const MOBILE_PROVIDER_LABELS: Record<string, string> = {
  mpesa: 'M-Pesa', airtel: 'Airtel Money', mtn: 'MTN MoMo',
  vodafone: 'Vodafone Cash', airteltigo: 'AirtelTigo', tigo: 'Tigo Cash', zamtel: 'Zamtel',
}

const NIGERIAN_BANKS = [
  { code: '044', name: 'Access Bank' },     { code: '058', name: 'GTBank' },
  { code: '011', name: 'First Bank' },      { code: '057', name: 'Zenith Bank' },
  { code: '033', name: 'UBA' },             { code: '032', name: 'Union Bank' },
  { code: '070', name: 'Fidelity Bank' },   { code: '035', name: 'Wema Bank' },
  { code: '050', name: 'Ecobank' },         { code: '232', name: 'Sterling Bank' },
  { code: '999240', name: 'Kuda Bank' },    { code: '120001', name: 'Opay' },
  { code: '100033', name: 'Palmpay' },      { code: '120003', name: 'Moniepoint MFB' },
  { code: '214', name: 'FCMB' },            { code: '221', name: 'Stanbic IBTC' },
]

// Algorand assets not supported by MoonPay sell
const ALGO_ASSETS = ['ALGO', 'USDT_ALGO', 'USDCa', 'goBTC', 'goETH']

export function WithdrawModal({ open, onOpenChange }: WithdrawModalProps) {
  const [provider, setProvider]         = useState<Provider>('local')
  const [asset, setAsset]               = useState('USDT_TRON')
  const [currency, setCurrency]         = useState('NGN')
  const [mpFiat, setMpFiat]             = useState('USD')
  const [amount, setAmount]             = useState('')
  const [payoutMethod, setPayoutMethod] = useState<'bank_transfer' | 'mobile_money'>('bank_transfer')
  const [bankCode, setBankCode]         = useState('')
  const [bankAccount, setBankAccount]   = useState('')
  const [accountName, setAccountName]   = useState<string | null>(null)
  const [mobileProvider, setMobileProvider] = useState('')
  const [mobileNumber, setMobileNumber]     = useState('')
  const [loading, setLoading]           = useState(false)
  const [verifying, setVerifying]       = useState(false)
  const [error, setError]               = useState<string | null>(null)
  const [quote, setQuote]               = useState<any>(null)
  const [fetchingQuote, setFetchingQuote] = useState(false)

  const { session }  = useAuth()
  const { balances } = useWallet()

  const selectedCurrency     = LOCAL_CURRENCIES.find(c => c.code === currency)
  const supportsBankTransfer = selectedCurrency?.methods.includes('bank_transfer') ?? false
  const supportsMobileMoney  = selectedCurrency?.methods.includes('mobile_money') ?? false
  const assetSymbol          = asset.split('_')[0]
  const availableBalance     = balances?.[asset]?.balance ?? 0
  const hasAlgoBalance       = (balances?.['ALGO']?.balance ?? 0) > 0

  // Auto-switch payout method when currency changes
  useEffect(() => {
    if (!supportsBankTransfer && supportsMobileMoney) setPayoutMethod('mobile_money')
    else setPayoutMethod('bank_transfer')
    setAccountName(null); setBankCode(''); setBankAccount(''); setQuote(null)
  }, [currency])

  // When MoonPay selected, remap Algorand assets
  useEffect(() => {
    if (provider === 'moonpay' && ALGO_ASSETS.includes(asset)) setAsset('USDT_TRON')
  }, [provider])

  // Debounced quote for local flow
  useEffect(() => {
    if (provider !== 'local') return
    if (!amount || parseFloat(amount) <= 0) { setQuote(null); return }
    const timer = setTimeout(fetchOfframpQuote, 500)
    return () => clearTimeout(timer)
  }, [amount, currency, asset, provider])

  const fetchOfframpQuote = async () => {
    setFetchingQuote(true); setError(null)
    try {
      const res = await api.post('/api/v1/offramp/quote', {
        crypto_asset: asset,
        amount_crypto: parseFloat(amount),
        currency,
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

  const verifyBankAccount = async () => {
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
        toast.error('Account not found. Check the number and bank.')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Verification failed')
    } finally {
      setVerifying(false)
    }
  }

  // ── Local provider handler ─────────────────────────────────────
  const handleLocalWithdraw = async () => {
    if (!amount || parseFloat(amount) <= 0) { toast.error('Enter a valid amount'); return }
    if (parseFloat(amount) > availableBalance) { toast.error('Insufficient balance'); return }
    if (payoutMethod === 'bank_transfer' && !accountName) { toast.error('Verify your bank account first'); return }
    if (payoutMethod === 'mobile_money' && (!mobileProvider || !mobileNumber)) { toast.error('Enter mobile money details'); return }

    setLoading(true); setError(null)
    try {
      const payload: any = {
        crypto_asset: asset,
        amount_crypto: parseFloat(amount),
        currency,
        payout_method: payoutMethod,
      }
      if (payoutMethod === 'bank_transfer') {
        payload.bank_code    = bankCode
        payload.bank_account = bankAccount
        payload.account_name = accountName
      } else {
        payload.mobile_provider = mobileProvider
        payload.mobile_number   = mobileNumber
      }
      const res = await api.post('/api/v1/offramp/initialize', payload)
      const data = res.data || res
      if (data?.success) {
        toast.success('Withdrawal initiated! Funds will arrive shortly.')
        onOpenChange(false)
      } else {
        throw new Error(data?.detail || data?.error || 'Withdrawal failed')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Withdrawal failed'
      setError(msg); toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  // ── MoonPay sell handler (correct SDK API) ────────────────────
  const handleMoonPay = async () => {
    if (!session) { toast.error('Sign in to sell crypto'); return }
    if (availableBalance <= 0) { toast.error(`No ${assetSymbol} balance to sell`); return }

    setLoading(true); setError(null)
    try {
      // 1. Get wallet / params from offramp endpoint
      const walletRes = await api.post('/api/v1/moonpay/url/offramp', {
        asset,
        quote_currency_code: mpFiat,
      })
      if (!walletRes?.success) throw new Error(walletRes?.detail || 'Failed to initialize')

      // 2. Initialize MoonPay SDK WITHOUT signature
      const moonPayInit = await loadMoonPay()
      if (!moonPayInit) throw new Error('MoonPay SDK failed to load')

      const { signature: _, ...sdkParams } = walletRes.params
      const widget = moonPayInit({
        flow: 'sell',
        environment: 'production',
        variant: 'overlay',
        params: sdkParams,
        handlers: {
          async onTransactionCompleted() {
            toast.success('🎉 Sale complete!')
            onOpenChange(false)
          },
          onCloseOverlay() {
            onOpenChange(false)
          },
          onError(error: any) {
            logger.error?.('MoonPay error:', error)
            setTimeout(() => {
              const iframe = document.querySelector('iframe[src*="moonpay"]')
              iframe?.parentElement?.remove()
            }, 300)
            setError('MoonPay encountered an error. Please try again.')
            onOpenChange(false)
          },
        },
      })

      // 3. Generate exact URL from SDK and sign it
      const urlToSign: string = widget.generateUrlForSigning()
      const urlObj = new URL(urlToSign)
      const queryString = urlObj.search.slice(1)

      const signRes = await api.post('/api/v1/moonpay/sign', { query_string: queryString })
      if (!signRes?.success) throw new Error('Signature generation failed')

      // 4. Apply signature, then close modal and show widget
      widget.updateSignature(signRes.signature)

      // Close the Seamount modal before showing MoonPay overlay ── prevents frozen widget
      onOpenChange(false)
      setTimeout(() => {
        widget.show()
      }, 100)

    } catch (err: any) {
      const msg = err?.message || 'MoonPay initialization failed'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const activeGroups = provider === 'moonpay' ? MOONPAY_ASSET_GROUPS : LOCAL_ASSET_GROUPS

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
              <div className="p-2 rounded-xl bg-red-50 dark:bg-red-900/30">
                <ArrowDownToLine className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
              Sell Crypto
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Convert crypto to fiat. Choose your payout provider.
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
              <span>Local Payout</span>
              <span className="text-[10px] font-normal opacity-70">Bank · Mobile Money</span>
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
              <span className="text-[10px] font-normal opacity-70">Global bank/card</span>
            </button>
          </div>

          {/* Asset Selection */}
          <div className="space-y-1.5">
            <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Asset to Sell</Label>
            <Select value={asset} onValueChange={v => { setAsset(v); setQuote(null) }}>
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

            {/* Balance chip */}
            {availableBalance > 0
              ? (
                <div className="flex justify-between items-center px-3 py-2 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-100 dark:border-green-800">
                  <span className="text-xs text-gray-500 dark:text-gray-400">Available</span>
                  <span className="text-sm font-bold text-green-700 dark:text-green-400">
                    {availableBalance.toFixed(6)} {assetSymbol}
                  </span>
                </div>
              ) : (
                <div className="px-3 py-2 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-800">
                  <span className="text-xs text-amber-700 dark:text-amber-400">
                    No {assetSymbol} balance — fund your wallet first.
                  </span>
                </div>
              )
            }

            {asset === 'MATIC' && (
              <p className="text-xs text-purple-600 dark:text-purple-400">
                ℹ️ MATIC withdrawn from your Polygon address.
              </p>
            )}
            {provider === 'moonpay' && hasAlgoBalance && (
              <p className="text-xs text-amber-600 dark:text-amber-400">
                ⚠️ ALGO cannot be sold via MoonPay — use Local Payout or swap to USDT first.
              </p>
            )}
          </div>

          {/* ── LOCAL PAYOUT FLOW ── */}
          {provider === 'local' && (
            <>
              {/* Currency */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Receive Currency</Label>
                <Select value={currency} onValueChange={setCurrency}>
                  <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 max-h-[200px] z-[9999]">
                    {LOCAL_CURRENCIES.map(c => (
                      <SelectItem key={c.code} value={c.code}
                        className="text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-600 py-2.5">
                        <span className="text-base mr-2">{c.flag}</span>
                        <span className="font-medium">{c.name} ({c.code})</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Amount */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Amount to Sell ({assetSymbol})
                </Label>
                <Input type="number" placeholder="0.000000" value={amount}
                  onChange={e => { setAmount(e.target.value); setQuote(null) }} disabled={loading}
                  className="h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
              </div>

              {/* Quote */}
              {fetchingQuote && (
                <div className="flex items-center gap-2 py-1">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                  <span className="text-xs text-gray-400">Getting quote...</span>
                </div>
              )}
              {quote && !fetchingQuote && (
                <div className="rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800 p-3.5 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">Fee</span>
                    <span className="text-gray-600 dark:text-gray-300">
                      -{selectedCurrency?.symbol}{quote.total_fee?.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between font-bold pt-1.5 border-t border-red-200 dark:border-red-700">
                    <span className="text-gray-800 dark:text-white text-sm">You Receive</span>
                    <span className="text-green-600 dark:text-green-400 text-sm">
                      {selectedCurrency?.symbol}{quote.net_fiat_amount?.toLocaleString()}
                    </span>
                  </div>
                </div>
              )}

              {/* Payout Method Toggle (only shown when both supported) */}
              {supportsBankTransfer && supportsMobileMoney && (
                <div className="space-y-1.5">
                  <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Payout Method</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => setPayoutMethod('bank_transfer')}
                      className={`flex items-center justify-center gap-2 py-2.5 rounded-xl border-2 text-sm font-semibold transition-all ${
                        payoutMethod === 'bank_transfer'
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                          : 'border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400'
                      }`}
                    >
                      <Building2 className="h-4 w-4" />Bank
                    </button>
                    <button
                      onClick={() => setPayoutMethod('mobile_money')}
                      className={`flex items-center justify-center gap-2 py-2.5 rounded-xl border-2 text-sm font-semibold transition-all ${
                        payoutMethod === 'mobile_money'
                          ? 'border-green-500 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                          : 'border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400'
                      }`}
                    >
                      <Smartphone className="h-4 w-4" />Mobile Money
                    </button>
                  </div>
                </div>
              )}

              {/* Bank Transfer Fields */}
              {payoutMethod === 'bank_transfer' && supportsBankTransfer && (
                <>
                  {currency === 'NGN' && (
                    <div className="space-y-1.5">
                      <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Bank</Label>
                      <Select value={bankCode} onValueChange={v => { setBankCode(v); setAccountName(null) }}>
                        <SelectTrigger className="h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
                          <SelectValue placeholder="Select bank" />
                        </SelectTrigger>
                        <SelectContent className="max-h-[200px] bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                          {NIGERIAN_BANKS.map(b => (
                            <SelectItem key={b.code} value={b.code}
                              className="text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700">
                              {b.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Account Number</Label>
                    <div className="flex gap-2">
                      <Input type="text" maxLength={10} placeholder="0123456789"
                        value={bankAccount}
                        onChange={e => { setBankAccount(e.target.value); setAccountName(null) }}
                        disabled={loading || verifying}
                        className="flex-1 h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                      />
                      <Button type="button" variant="outline"
                        onClick={verifyBankAccount}
                        disabled={!bankAccount || !bankCode || verifying || loading || bankAccount.length !== 10}
                        className="h-12 rounded-xl border-2 border-gray-200 dark:border-gray-700 font-semibold px-4">
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
                </>
              )}

              {/* Mobile Money Fields */}
              {payoutMethod === 'mobile_money' && supportsMobileMoney && (
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Mobile Provider</Label>
                    <Select value={mobileProvider} onValueChange={setMobileProvider}>
                      <SelectTrigger className="h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
                        <SelectValue placeholder="Select provider" />
                      </SelectTrigger>
                      <SelectContent className="bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                        {selectedCurrency?.mobile_providers.map(p => (
                          <SelectItem key={p} value={p} className="text-gray-900 dark:text-white">
                            {MOBILE_PROVIDER_LABELS[p] || p}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Phone Number</Label>
                    <Input type="tel" placeholder="e.g. 0712345678"
                      value={mobileNumber} onChange={e => setMobileNumber(e.target.value)}
                      className="h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    />
                  </div>
                </div>
              )}

              <Alert className="border border-green-100 dark:border-green-900 bg-green-50 dark:bg-green-900/20 rounded-xl py-3">
                <Info className="h-4 w-4 text-green-600 shrink-0 mt-0.5" />
                <AlertDescription className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                  <strong className="text-green-700 dark:text-green-400">Smart routing</strong> — best provider auto-selected. Direct bank &amp; mobile money payout across Africa.
                </AlertDescription>
              </Alert>
            </>
          )}

          {/* ── MOONPAY FLOW ── */}
          {provider === 'moonpay' && (
            <>
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Receive In</Label>
                <Select value={mpFiat} onValueChange={setMpFiat}>
                  <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
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

              {/* Trust badges */}
              <div className="grid grid-cols-3 gap-2">
                {[
                  { icon: '🔒', text: 'KYC secured' },
                  { icon: '🏦', text: 'Bank payout' },
                  { icon: '🌍', text: '160+ countries' },
                ].map(b => (
                  <div key={b.text} className="flex flex-col items-center gap-1 p-2.5 rounded-xl bg-gray-50 dark:bg-gray-800 text-center">
                    <span className="text-lg">{b.icon}</span>
                    <span className="text-[10px] font-medium text-gray-500 dark:text-gray-400">{b.text}</span>
                  </div>
                ))}
              </div>

              <Alert className="border border-red-100 dark:border-red-900 bg-red-50 dark:bg-red-900/20 rounded-xl py-3">
                <Info className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
                <AlertDescription className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                  Powered by <strong className="text-red-600 dark:text-red-400">MoonPay</strong> —
                  they collect your crypto and transfer fiat to your bank or card.
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
        <div className="sticky bottom-0 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 px-5 py-4 rounded-b-2xl flex gap-3">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}
            className="flex-1 h-12 rounded-xl border-gray-200 dark:border-gray-700 font-semibold">
            Cancel
          </Button>
          <Button
            onClick={provider === 'moonpay' ? handleMoonPay : handleLocalWithdraw}
            disabled={
              loading ||
              availableBalance <= 0 ||
              (provider === 'local' && (
                !amount || parseFloat(amount) <= 0 ||
                parseFloat(amount) > availableBalance ||
                (payoutMethod === 'bank_transfer' && !accountName) ||
                (payoutMethod === 'mobile_money' && (!mobileProvider || !mobileNumber))
              ))
            }
            className={`flex-[2] h-12 rounded-xl font-bold text-white disabled:opacity-50 ${
              provider === 'moonpay'
                ? 'bg-blue-600 hover:bg-blue-700'
                : 'bg-red-600 hover:bg-red-700'
            }`}
          >
            {loading
              ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Launching...</>
              : provider === 'moonpay'
                ? <><ShieldCheck className="mr-2 h-4 w-4" />Sell via MoonPay</>
                : `Withdraw ${quote ? `${selectedCurrency?.symbol}${quote.net_fiat_amount?.toLocaleString()}` : assetSymbol}`
            }
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}