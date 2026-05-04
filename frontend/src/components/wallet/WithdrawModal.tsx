// File: frontend/src/components/wallet/WithdrawModal.tsx
/**
 * WithdrawModal — Dual Provider: Cashramp/Paystack + MoonPay Sell
 * - Cashramp/Paystack: African bank + mobile money, live quote, account verify
 * - MoonPay: Global sell, fiat payout to bank/card
 */

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
import {
  Dialog, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import {
  Loader2, ArrowDownToLine, AlertCircle, CheckCircle2,
  Building2, Smartphone, Info, Globe, Banknote,
} from 'lucide-react'

interface WithdrawModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Provider = 'cashramp' | 'moonpay'

// ── Cashramp/Paystack currencies ──────────────────────────────────
const CASHRAMP_CURRENCIES = [
  { code: 'NGN', name: 'Nigerian Naira',     symbol: '₦',   flag: '🇳🇬', methods: ['bank_transfer'], providers: ['cashramp', 'paystack'] },
  { code: 'KES', name: 'Kenyan Shilling',    symbol: 'KSh', flag: '🇰🇪', methods: ['bank_transfer', 'mobile_money'], mobile_providers: ['mpesa', 'airtel'], providers: ['cashramp'] },
  { code: 'GHS', name: 'Ghanaian Cedi',      symbol: 'GH₵', flag: '🇬🇭', methods: ['bank_transfer', 'mobile_money'], mobile_providers: ['mtn', 'vodafone', 'airteltigo'], providers: ['cashramp'] },
  { code: 'ZAR', name: 'South African Rand', symbol: 'R',   flag: '🇿🇦', methods: ['bank_transfer'], providers: ['cashramp'] },
  { code: 'UGX', name: 'Ugandan Shilling',   symbol: 'USh', flag: '🇺🇬', methods: ['mobile_money'], mobile_providers: ['mtn', 'airtel'], providers: ['cashramp'] },
  { code: 'TZS', name: 'Tanzanian Shilling', symbol: 'TSh', flag: '🇹🇿', methods: ['mobile_money'], mobile_providers: ['mpesa', 'airtel', 'tigo'], providers: ['cashramp'] },
  { code: 'RWF', name: 'Rwandan Franc',      symbol: 'FRw', flag: '🇷🇼', methods: ['mobile_money'], mobile_providers: ['mtn', 'airtel'], providers: ['cashramp'] },
  { code: 'ZMW', name: 'Zambian Kwacha',     symbol: 'ZK',  flag: '🇿🇲', methods: ['mobile_money'], mobile_providers: ['mtn', 'airtel', 'zamtel'], providers: ['cashramp'] },
]

const MOONPAY_FIAT = ['USD', 'EUR', 'GBP', 'NGN', 'KES', 'GHS', 'ZAR']

const MOBILE_PROVIDER_NAMES: Record<string, string> = {
  mpesa: 'M-Pesa', airtel: 'Airtel Money', mtn: 'MTN MoMo',
  vodafone: 'Vodafone Cash', airteltigo: 'AirtelTigo', tigo: 'Tigo Cash', zamtel: 'Zamtel',
}

// ── Asset groups for Cashramp (full) ─────────────────────────────
const CASHRAMP_ASSET_GROUPS = {
  algorand: [
    { value: 'ALGO',      label: 'Algorand (ALGO)',         icon: 'Ⱥ' },
    { value: 'USDT_ALGO', label: 'Tether (Algorand)',       icon: '₮' },
    { value: 'USDCa',     label: 'USD Coin (USDCa)',        icon: '◎' },
    { value: 'goBTC',     label: 'Wrapped Bitcoin (goBTC)', icon: '₿' },
    { value: 'goETH',     label: 'Wrapped Ethereum (goETH)',icon: 'Ξ' },
  ],
  bitcoin:  [{ value: 'BTC', label: 'Bitcoin (BTC)', icon: '₿' }],
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
    { value: 'TRX',       label: 'TRON (TRX)',      icon: '⚡' },
    { value: 'USDT_TRON', label: 'Tether (Tron)',   icon: '₮' },
  ],
  solana: [
    { value: 'SOL',         label: 'Solana (SOL)',        icon: '◎' },
    { value: 'USDT_SOLANA', label: 'Tether (Solana)',     icon: '₮' },
    { value: 'USDC_SOLANA', label: 'USD Coin (Solana)',   icon: '◎' },
  ],
}

// ── Asset groups for MoonPay sell (ALGO excluded) ─────────────────
const MOONPAY_ASSET_GROUPS = {
  bitcoin:  [{ value: 'BTC',          label: 'Bitcoin (BTC)',        icon: '₿' }],
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
    { value: 'TRX',       label: 'TRON (TRX)',    icon: '⚡' },
    { value: 'USDT_TRON', label: 'Tether (Tron)', icon: '₮' },
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

const NIGERIAN_BANKS = [
  { code: '044', name: 'Access Bank' }, { code: '050', name: 'Ecobank Nigeria' },
  { code: '070', name: 'Fidelity Bank' }, { code: '011', name: 'First Bank' },
  { code: '058', name: 'GTBank' }, { code: '033', name: 'UBA' },
  { code: '057', name: 'Zenith Bank' }, { code: '035', name: 'Wema Bank' },
  { code: '032', name: 'Union Bank' }, { code: '999240', name: 'Kuda Bank' },
  { code: '120001', name: 'Opay' }, { code: '100033', name: 'Palmpay' },
  { code: '120003', name: 'Moniepoint MFB' },
]

export function WithdrawModal({ open, onOpenChange }: WithdrawModalProps) {
  const [provider, setProvider]       = useState<Provider>('cashramp')
  const [asset, setAsset]             = useState('USDT_TRON')
  const [currency, setCurrency]       = useState('NGN')
  const [mpFiat, setMpFiat]           = useState('USD')
  const [amount, setAmount]           = useState('')
  const [payoutMethod, setPayoutMethod] = useState<'bank_transfer' | 'mobile_money'>('bank_transfer')
  const [bankCode, setBankCode]       = useState('')
  const [bankAccount, setBankAccount] = useState('')
  const [accountName, setAccountName] = useState<string | null>(null)
  const [mobileProvider, setMobileProvider] = useState('')
  const [mobileNumber, setMobileNumber]     = useState('')
  const [loading, setLoading]         = useState(false)
  const [verifying, setVerifying]     = useState(false)
  const [error, setError]             = useState<string | null>(null)
  const [quote, setQuote]             = useState<any>(null)
  const [fetchingQuote, setFetchingQuote] = useState(false)

  const { session }  = useAuth()
  const { balances } = useWallet()

  const selectedCurrency     = CASHRAMP_CURRENCIES.find(c => c.code === currency)
  const supportsBankTransfer = selectedCurrency?.methods.includes('bank_transfer')
  const supportsMobileMoney  = selectedCurrency?.methods.includes('mobile_money')
  const assetSymbol          = asset.split('_')[0]
  const availableBalance     = balances[asset]?.balance ?? 0

  // Switch to USDT_TRON if MoonPay selected and current asset is Algorand-native
  useEffect(() => {
    if (provider === 'moonpay') {
      const algorandOnly = ['ALGO', 'USDT_ALGO', 'USDCa', 'goBTC', 'goETH']
      if (algorandOnly.includes(asset)) setAsset('USDT_TRON')
    }
  }, [provider])

  // Debounced quote for Cashramp flow
  useEffect(() => {
    if (provider !== 'cashramp') return
    const timer = setTimeout(() => {
      if (amount && parseFloat(amount) > 0) fetchOfframpQuote()
    }, 500)
    return () => clearTimeout(timer)
  }, [amount, currency, asset, provider])

  const fetchOfframpQuote = async () => {
    setFetchingQuote(true); setError(null)
    try {
      const response = await api.post('/api/v1/offramp/quote', {
        crypto_asset: asset, amount_crypto: parseFloat(amount), currency,
      })
      if (response?.success) setQuote(response.quote)
      else setError(response?.error || 'Failed to get quote')
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
      const response = await api.post('/api/v1/bank-verification/verify', {
        account_number: bankAccount, bank_code: bankCode, currency,
      })
      if (response?.success && response?.account_name) {
        setAccountName(response.account_name)
        toast.success(`Account verified: ${response.account_name}`)
      } else {
        toast.error('Account not found. Check number and bank.')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Verification failed')
    } finally {
      setVerifying(false)
    }
  }

  // ── Cashramp / Paystack offramp handler ───────────────────────
  const handleCashramp = async () => {
    if (!amount || parseFloat(amount) <= 0) { toast.error('Enter a valid amount'); return }
    if (parseFloat(amount) > availableBalance) { toast.error('Insufficient balance'); return }
    if (payoutMethod === 'bank_transfer' && !accountName) { toast.error('Please verify your bank account'); return }
    if (payoutMethod === 'mobile_money' && (!mobileProvider || !mobileNumber)) { toast.error('Enter mobile money details'); return }

    setLoading(true); setError(null)
    try {
      const payload: any = {
        crypto_asset: asset, amount_crypto: parseFloat(amount),
        currency, payout_method: payoutMethod,
      }
      if (payoutMethod === 'bank_transfer') {
        payload.bank_code = bankCode
        payload.bank_account = bankAccount
        payload.account_name = accountName
      } else {
        payload.mobile_provider = mobileProvider
        payload.mobile_number = mobileNumber
      }
      const response = await api.post('/api/v1/offramp/initialize', payload)
      const data = response.data || response
      if (data?.success) {
        toast.success('Withdrawal initiated! Funds will arrive shortly.')
        onOpenChange(false)
      } else {
        throw new Error(data?.detail || data?.error || 'Withdrawal failed')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to initialize withdrawal'
      setError(msg); toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  // ── MoonPay sell handler ───────────────────────────────────────
  const handleMoonPay = async () => {
    if (!session) { toast.error('Please sign in'); return }
    if (availableBalance <= 0) { toast.error(`No ${assetSymbol} balance to sell`); return }

    setLoading(true); setError(null)
    try {
      const response = await api.post('/api/v1/moonpay/url/offramp', {
        asset, quote_currency_code: mpFiat,
      })
      if (!response?.success) throw new Error(response?.detail || 'Failed to initialize MoonPay')
      const moonPayFactory = await loadMoonPay()
      const moonPaySdk = moonPayFactory({
        flow: 'sell', environment: 'production', variant: 'overlay',
        params: response.params,
      })
      moonPaySdk.on('transactionCompleted', () => {
        toast.success("✅ Withdrawal initiated! Funds will arrive per your bank's schedule.")
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

  const activeGroups = provider === 'moonpay' ? MOONPAY_ASSET_GROUPS : CASHRAMP_ASSET_GROUPS

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-[480px] max-w-[95vw] max-h-[90vh] overflow-y-auto bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600"
        style={{ zIndex: 1000 }}
      >
        <DialogHeader className="border-b pb-4">
          <DialogTitle className="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-white">
            <ArrowDownToLine className="h-6 w-6 text-red-600" />
            Sell Crypto
          </DialogTitle>
          <DialogDescription className="text-gray-600 dark:text-gray-400 mt-1">
            Convert crypto to fiat. Choose your preferred provider.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* ── Provider Toggle ── */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold text-gray-900 dark:text-white">Payout Provider</Label>
            <div className="grid grid-cols-2 gap-2">
              <Button type="button" variant="outline"
                onClick={() => { setProvider('cashramp'); setError(null) }}
                className={`h-14 flex-col gap-1 border-2 text-sm font-bold transition-all ${
                  provider === 'cashramp'
                    ? 'border-green-500 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                    : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400'
                }`}
              >
                <Banknote className="h-5 w-5" />
                <span>Cashramp / FW</span>
                <span className="text-xs font-normal opacity-70">Africa + Mobile Money</span>
              </Button>
              <Button type="button" variant="outline"
                onClick={() => { setProvider('moonpay'); setError(null) }}
                className={`h-14 flex-col gap-1 border-2 text-sm font-bold transition-all ${
                  provider === 'moonpay'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                    : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400'
                }`}
              >
                <Globe className="h-5 w-5" />
                <span>MoonPay</span>
                <span className="text-xs font-normal opacity-70">Global bank/card</span>
              </Button>
            </div>
          </div>

          {/* ── Asset Selection ── */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold text-gray-900 dark:text-white">Crypto to Sell</Label>
            <Select value={asset} onValueChange={setAsset}>
              <SelectTrigger className="w-full h-12 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100">
                <SelectValue />
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

            {/* Balance */}
            {availableBalance > 0 && (
              <div className="flex justify-between px-3 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 text-sm">
                <span className="text-gray-600 dark:text-gray-400">Available:</span>
                <span className="font-bold text-blue-700 dark:text-blue-300">
                  {availableBalance.toFixed(6)} {assetSymbol}
                </span>
              </div>
            )}
          </div>

          {/* ── CASHRAMP FLOW ── */}
          {provider === 'cashramp' && (
            <>
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900 dark:text-white">Payout Currency</Label>
                <Select value={currency} onValueChange={v => { setCurrency(v); setAccountName(null); setBankCode(''); setBankAccount('') }}>
                  <SelectTrigger className="w-full h-12 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 max-h-[300px] z-50">
                    {CASHRAMP_CURRENCIES.map(c => (
                      <SelectItem key={c.code} value={c.code}
                        className="text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-600 py-3">
                        <span className="text-xl mr-2">{c.flag}</span>
                        <span className="font-medium">{c.symbol} {c.name}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900 dark:text-white">Amount to Sell ({assetSymbol})</Label>
                <Input type="number" placeholder="0.00" value={amount}
                  onChange={e => { setAmount(e.target.value); setQuote(null) }}
                  disabled={loading}
                  className="h-12 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100"
                />
              </div>

              {/* Quote */}
              {fetchingQuote && (
                <div className="flex items-center gap-2 py-2">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                  <span className="text-sm text-gray-500">Getting quote...</span>
                </div>
              )}
              {quote && !fetchingQuote && (
                <div className="rounded-xl bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-700 p-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Fee</span>
                    <span>-{selectedCurrency?.symbol}{quote.total_fee?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-base border-t border-red-300 dark:border-red-700 pt-2">
                    <span>You Receive</span>
                    <span className="text-green-600 dark:text-green-400">
                      {selectedCurrency?.symbol}{quote.net_fiat_amount?.toLocaleString()}
                    </span>
                  </div>
                </div>
              )}

              {/* Payout Method */}
              {(supportsBankTransfer && supportsMobileMoney) && (
                <div className="space-y-2">
                  <Label className="text-sm font-semibold text-gray-900 dark:text-white">Payout Method</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Button type="button" variant="outline"
                      onClick={() => setPayoutMethod('bank_transfer')}
                      className={`h-11 border-2 font-bold ${payoutMethod === 'bank_transfer' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : ''}`}
                    >
                      <Building2 className="mr-2 h-4 w-4" />Bank Transfer
                    </Button>
                    <Button type="button" variant="outline"
                      onClick={() => setPayoutMethod('mobile_money')}
                      className={`h-11 border-2 font-bold ${payoutMethod === 'mobile_money' ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : ''}`}
                    >
                      <Smartphone className="mr-2 h-4 w-4" />Mobile Money
                    </Button>
                  </div>
                </div>
              )}

              {/* Bank Transfer Fields */}
              {payoutMethod === 'bank_transfer' && supportsBankTransfer && (
                <>
                  {currency === 'NGN' && (
                    <div className="space-y-2">
                      <Label className="text-sm font-semibold text-gray-900 dark:text-white">Bank</Label>
                      <Select value={bankCode} onValueChange={v => { setBankCode(v); setAccountName(null) }}>
                        <SelectTrigger className="h-12 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100">
                          <SelectValue placeholder="Select bank" />
                        </SelectTrigger>
                        <SelectContent className="max-h-[200px] bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 z-50">
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
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold text-gray-900 dark:text-white">Account Number</Label>
                    <div className="flex gap-2">
                      <Input type="text" maxLength={10} placeholder="0123456789"
                        value={bankAccount}
                        onChange={e => { setBankAccount(e.target.value); setAccountName(null) }}
                        disabled={loading || verifying}
                        className="flex-1 h-12 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100"
                      />
                      <Button type="button" variant="outline"
                        onClick={verifyBankAccount}
                        disabled={!bankAccount || !bankCode || verifying || loading || bankAccount.length !== 10}
                        className="h-12 border-2 font-semibold px-5"
                      >
                        {verifying ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Verify'}
                      </Button>
                    </div>
                  </div>
                  {accountName && (
                    <Alert className="bg-green-50 dark:bg-green-900/20 border-2 border-green-300 dark:border-green-800">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <AlertDescription className="text-green-900 dark:text-green-100 font-bold">{accountName}</AlertDescription>
                    </Alert>
                  )}
                </>
              )}

              {/* Mobile Money Fields */}
              {payoutMethod === 'mobile_money' && supportsMobileMoney && (
                <div className="space-y-3">
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold text-gray-900 dark:text-white">Mobile Provider</Label>
                    <Select value={mobileProvider} onValueChange={setMobileProvider}>
                      <SelectTrigger className="h-12 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100">
                        <SelectValue placeholder="Select provider" />
                      </SelectTrigger>
                      <SelectContent className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 z-50">
                        {selectedCurrency?.mobile_providers?.map(p => (
                          <SelectItem key={p} value={p} className="text-gray-900 dark:text-gray-100">
                            {MOBILE_PROVIDER_NAMES[p] || p}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold text-gray-900 dark:text-white">Phone Number</Label>
                    <Input type="tel" placeholder="e.g. 0712345678"
                      value={mobileNumber} onChange={e => setMobileNumber(e.target.value)}
                      className="h-12 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100"
                    />
                  </div>
                </div>
              )}

              <Alert className="bg-green-50 dark:bg-green-900/20 border-2 border-green-200 dark:border-green-800">
                <Info className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-sm text-gray-800 dark:text-gray-200">
                  <strong className="text-green-700 dark:text-green-300">Cashramp / Paystack</strong> — Direct bank payout & mobile money across Africa.
                </AlertDescription>
              </Alert>
            </>
          )}

          {/* ── MOONPAY FLOW ── */}
          {provider === 'moonpay' && (
            <>
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900 dark:text-white">Receive Currency</Label>
                <Select value={mpFiat} onValueChange={setMpFiat}>
                  <SelectTrigger className="w-full h-12 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white dark:bg-gray-700 z-50">
                    {MOONPAY_FIAT.map(c => (
                      <SelectItem key={c} value={c} className="text-gray-900 dark:text-white">{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {asset === 'MATIC' && (
                <p className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                  ℹ️ MATIC sells on the POL network. MoonPay withdraws from your Polygon address.
                </p>
              )}
              <Alert className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800">
                <Info className="h-4 w-4 text-blue-600" />
                <AlertDescription className="text-sm text-gray-800 dark:text-gray-200">
                  <strong className="text-blue-700 dark:text-blue-300">MoonPay</strong> collects your crypto and pays out to your bank or card globally.
                  Settlement time varies by country.
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
            onClick={provider === 'moonpay' ? handleMoonPay : handleCashramp}
            disabled={
              loading ||
              (provider === 'cashramp' && (
                !amount || parseFloat(amount) <= 0 ||
                parseFloat(amount) > availableBalance ||
                (payoutMethod === 'bank_transfer' && !accountName) ||
                (payoutMethod === 'mobile_money' && (!mobileProvider || !mobileNumber))
              )) ||
              (provider === 'moonpay' && availableBalance <= 0)
            }
            className={`h-11 px-8 font-bold text-white ${
              provider === 'moonpay' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-red-600 hover:bg-red-700'
            }`}
          >
            {loading ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Preparing...</>
            ) : provider === 'moonpay' ? (
              <><Globe className="mr-2 h-4 w-4" />Open MoonPay Sell</>
            ) : (
              `Withdraw ${quote ? `${CASHRAMP_CURRENCIES.find(c=>c.code===currency)?.symbol}${quote.net_fiat_amount?.toLocaleString()}` : assetSymbol}`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}