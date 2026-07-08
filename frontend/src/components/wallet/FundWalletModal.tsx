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
import { Loader2, Wallet, Info, AlertCircle, ShieldCheck, Globe, Banknote, X, Smartphone, Copy, CheckCircle2 } from 'lucide-react'

interface FundWalletModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// ─────────────────────────────────────────────────────────────
// EXISTING — untouched
// ─────────────────────────────────────────────────────────────
type Provider = 'local' | 'moonpay' | 'busha' | 'kotani' | 'wapipay'

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

const MOONPAY_ASSET_FALLBACK: Record<string, string> = {
  goBTC: 'BTC', goETH: 'ETH', USDCa: 'USDC_ETH', USDT_ALGO: 'USDT_TRON',
}
// ─────────────────────────────────────────────────────────────
// NEW — addon constants only
// ─────────────────────────────────────────────────────────────

// Capability matrix — single source of truth for currency-aware tab visibility
const ONRAMP_PROVIDER_CURRENCIES: Record<Provider, string[]> = {
  local:   ['NGN','KES','GHS','ZAR','UGX','TZS','RWF','XOF','XAF','ZMW','USD','GBP','EUR'],
  moonpay: ['USD','EUR','GBP','NGN','KES','GHS','ZAR'],
  busha:   ['NGN','KES'],
  kotani:  ['KES','GHS','UGX','TZS','RWF','XOF','XAF','ZMW','ZAR'],
  wapipay: ['NGN'],
}

// Provider metadata for rendering toggle buttons
const PROVIDER_META: Record<Provider, { label: string; sublabel: string; icon: React.ReactNode; activeClass: string }> = {
  local:   { label: 'Paystack / Flutterwave', sublabel: 'NGN · KES · GHS & more', icon: <Banknote className="h-5 w-5" />, activeClass: 'border-green-500 bg-green-50 text-green-700' },
  moonpay: { label: 'MoonPay',               sublabel: 'Card · Apple Pay · 160+',  icon: <Globe className="h-5 w-5" />,   activeClass: 'border-blue-500 bg-blue-50 text-blue-700'  },
  busha:   { label: 'Busha',                 sublabel: 'Bank transfer · NGN/KES',  icon: <Wallet className="h-5 w-5" />,  activeClass: 'border-purple-500 bg-purple-50 text-purple-700' },
  kotani:  { label: 'Kotani Pay',            sublabel: 'Mobile money · Africa',    icon: <Smartphone className="h-5 w-5" />, activeClass: 'border-orange-500 bg-orange-50 text-orange-700' },
  wapipay: {
    label: 'WapiPay',
    sublabel: 'NGN Virtual Account',
    icon: <Globe className="h-5 w-5" />,
    activeClass: 'border-cyan-500 bg-cyan-50 dark:bg-cyan-900/20 text-cyan-700 dark:text-cyan-300',
  },
}

// Asset remapping when switching to Busha (unsupported Algorand-native assets)
const BUSHA_ASSET_FALLBACK: Record<string, string> = {
  goBTC: 'BTC', goETH: 'ETH', USDCa: 'USDC_ETH', USDT_ALGO: 'USDT_TRON', ALGO: 'BTC',
}

// Asset remapping when switching to Kotani
const KOTANI_ASSET_FALLBACK: Record<string, string> = {
  goBTC: 'BTC', goETH: 'ETH', USDCa: 'USDC_ETH', USDT_ALGO: 'USDT_TRON', ALGO: 'BTC', MATIC: 'USDT_POLYGON',
}

// Kotani telco options per currency
const KOTANI_ONRAMP_TELCOS: Record<string, { id: string; name: string }[]> = {
  KES: [{ id: 'MPESA', name: 'M-Pesa' }, { id: 'AIRTEL', name: 'Airtel Money' }],
  GHS: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'VODAFONE', name: 'Vodafone Cash' }, { id: 'AIRTELTIGO', name: 'AirtelTigo' }],
  UGX: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'AIRTEL', name: 'Airtel Money' }],
  TZS: [{ id: 'MPESA', name: 'M-Pesa' }, { id: 'AIRTEL', name: 'Airtel' }, { id: 'TIGO', name: 'Tigo Cash' }],
  RWF: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'AIRTEL', name: 'Airtel Money' }],
  ZMW: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'AIRTEL', name: 'Airtel Money' }, { id: 'ZAMTEL', name: 'Zamtel' }],
  XOF: [{ id: 'ORANGE', name: 'Orange Money' }, { id: 'MTN', name: 'MTN MoMo' }],
  XAF: [{ id: 'ORANGE', name: 'Orange Money' }, { id: 'MTN', name: 'MTN MoMo' }],
  ZAR: [{ id: 'MTN', name: 'MTN MoMo' }],
}

// Derive available providers for a given currency
const getAvailableProviders = (curr: string): Provider[] =>
  (Object.entries(ONRAMP_PROVIDER_CURRENCIES) as [Provider, string[]][])
    .filter(([, currencies]) => currencies.includes(curr))
    .map(([p]) => p)

export function FundWalletModal({ open, onOpenChange }: FundWalletModalProps) {
  // ─────────────────────────────────────────────────────────
  // EXISTING STATE — untouched
  // ─────────────────────────────────────────────────────────
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

  // ─────────────────────────────────────────────────────────
  // NEW STATE — addon only, zero collision with existing
  // ─────────────────────────────────────────────────────────
  // Busha onramp state
  const [bushaQuote, setBushaQuote]               = useState<any>(null)
  const [bushaFetchingQuote, setBushaFetchingQuote] = useState(false)
  const [bushaPayInStep, setBushaPayInStep]         = useState<'form' | 'bank_details'>('form')
  const [bushaPayInDetails, setBushaPayInDetails]   = useState<any>(null)
  const [bushaAccountCopied, setBushaAccountCopied] = useState(false)
  // Kotani onramp state
  const [kotaniQuote, setKotaniQuote]                 = useState<any>(null)
  const [kotaniFetchingQuote, setKotaniFetchingQuote] = useState(false)
  const [kotaniPhone, setKotaniPhone]                 = useState('')
  const [kotaniTelco, setKotaniTelco]                 = useState('')
  const [kotaniPayInSent, setKotaniPayInSent]         = useState(false)
  const [kotaniPayInDetails, setKotaniPayInDetails]   = useState<any>(null)
  // WapiPay onramp state
  const [wapiVA, setWapiVA]               = useState<any>(null)
  const [wapiVALoading, setWapiVALoading] = useState(false)

  // ─────────────────────────────────────────────────────────
  // EXISTING useEffects — untouched
  // ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!open) return
    const pre = sessionStorage.getItem('preselected_asset')
    if (pre) {
      setAsset(pre)
      sessionStorage.removeItem('preselected_asset')
    }
  }, [open])

  useEffect(() => {
    if (provider === 'moonpay') {
      const safe = MOONPAY_ASSET_FALLBACK[asset]
      if (safe) setAsset(safe)
    }
  }, [provider])

  useEffect(() => { setQuote(null) }, [asset, currency, amount])

  useEffect(() => {
    if (provider !== 'local') return
    if (!amount || parseFloat(amount) <= 0) { setQuote(null); return }
    const timer = setTimeout(fetchQuote, 500)
    return () => clearTimeout(timer)
  }, [amount, currency, asset, provider])

  // ─────────────────────────────────────────────────────────
  // NEW useEffects — addon only
  // ─────────────────────────────────────────────────────────

  // Capability matrix: auto-fallback when currency no longer supports current provider
  useEffect(() => {
    const avail = getAvailableProviders(currency)
    if (!avail.includes(provider)) {
      setProvider(avail[0] || 'local')
    }
    setError(null)
  }, [currency])

  // Asset remapping when switching TO busha or kotani
  useEffect(() => {
    if (provider === 'busha') {
      const safe = BUSHA_ASSET_FALLBACK[asset]
      if (safe) setAsset(safe)
      // Ensure currency is Busha-compatible
      if (!ONRAMP_PROVIDER_CURRENCIES.busha.includes(currency)) setCurrency('NGN')
      setBushaQuote(null); setBushaPayInStep('form'); setBushaPayInDetails(null)
    }
    if (provider === 'kotani') {
      const safe = KOTANI_ASSET_FALLBACK[asset]
      if (safe) setAsset(safe)
      // Ensure currency is Kotani-compatible
      if (!ONRAMP_PROVIDER_CURRENCIES.kotani.includes(currency)) setCurrency('KES')
      setKotaniQuote(null); setKotaniPayInSent(false); setKotaniPayInDetails(null)
      setKotaniPhone(''); setKotaniTelco('')
    }
    if (provider === 'wapipay') {
      if (!ONRAMP_PROVIDER_CURRENCIES.wapipay.includes(currency)) setCurrency('NGN')
      setWapiVA(null)
    }
    setError(null)
  }, [provider])

  // Clear new quotes when inputs change
  useEffect(() => {
    setBushaQuote(null)
    setKotaniQuote(null)
  }, [asset, currency, amount])

  // Debounced Busha quote
  useEffect(() => {
    if (provider !== 'busha') return
    if (!amount || parseFloat(amount) <= 0) { setBushaQuote(null); return }
    const timer = setTimeout(fetchBushaQuote, 500)
    return () => clearTimeout(timer)
  }, [amount, currency, asset, provider])

  // Debounced Kotani quote
  useEffect(() => {
    if (provider !== 'kotani') return
    if (!amount || parseFloat(amount) <= 0) { setKotaniQuote(null); return }
    const timer = setTimeout(fetchKotaniQuote, 500)
    return () => clearTimeout(timer)
  }, [amount, currency, asset, provider])

  // ─────────────────────────────────────────────────────────
  // EXISTING handlers — untouched
  // ─────────────────────────────────────────────────────────
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

  const handleMoonPay = async () => {
    if (!session) { toast.error('Sign in to buy crypto'); return }
    setLoading(true); setError(null)
    try {
      const walletRes = await api.post('/api/v1/moonpay/url/onramp', {
        asset,
        base_currency_code: mpCurrency,
      })
      if (!walletRes?.success) throw new Error('Failed to get wallet params')
      const moonPayInit = await loadMoonPay()
      if (!moonPayInit) throw new Error('MoonPay SDK failed to load')
      const { signature: _, ...sdkParams } = walletRes.params
      const widget = moonPayInit({
        flow: 'buy',
        environment: 'production',
        variant: 'overlay',
        params: sdkParams,
        handlers: {
          async onTransactionCompleted() {
            toast.success('🎉 Purchase complete!')
            onOpenChange(false)
          },
          onCloseOverlay() { onOpenChange(false) },
          onError(error: any) {
            setError('MoonPay encountered an error. Please try again.')
            onOpenChange(false)
          },
        },
      })
      const urlToSign: string = widget.generateUrlForSigning()
      const urlObj = new URL(urlToSign)
      const queryString = urlObj.search.slice(1)
      const signRes = await api.post('/api/v1/moonpay/sign', { query_string: queryString })
      if (!signRes?.success) throw new Error('Signature generation failed')
      widget.updateSignature(signRes.signature)
      onOpenChange(false)
      setTimeout(() => { widget.show() }, 100)
    } catch (err: any) {
      const msg = err?.message || 'MoonPay initialization failed'
      setError(msg); toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  // ─────────────────────────────────────────────────────────
  // NEW handlers — addon only
  // ─────────────────────────────────────────────────────────
  const fetchBushaQuote = async () => {
    setBushaFetchingQuote(true); setError(null)
    try {
      const res = await api.post('/api/v1/busha/onramp/quote', {
        amount_fiat: parseFloat(amount), currency, crypto_asset: asset,
      })
      if (res?.success) setBushaQuote(res)
      else setError(res?.message || res?.detail || 'Failed to get Busha quote')
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Busha quote failed')
      setBushaQuote(null)
    } finally { setBushaFetchingQuote(false) }
  }

  const fetchKotaniQuote = async () => {
    setKotaniFetchingQuote(true); setError(null)
    try {
      const res = await api.post('/api/v1/kotani/onramp/quote', {
        amount_fiat: parseFloat(amount), currency, crypto_asset: asset,
      })
      if (res?.success) setKotaniQuote(res)
      else setError(res?.message || res?.detail || 'Failed to get Kotani quote')
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Kotani quote failed')
      setKotaniQuote(null)
    } finally { setKotaniFetchingQuote(false) }
  }

  const handleBusha = async () => {
    if (!session) { toast.error('Sign in to buy crypto'); return }
    if (!amount || parseFloat(amount) <= 0) { toast.error('Enter a valid amount'); return }
    setLoading(true); setError(null)
    try {
      const res = await api.post('/api/v1/busha/onramp/initialize', {
        amount_fiat: parseFloat(amount), currency, crypto_asset: asset,
      })
      const data = res.data || res
      if (data?.success) {
        setBushaPayInDetails(data)
        setBushaPayInStep('bank_details')
        toast.success('Bank account ready — transfer the exact amount shown.')
      } else {
        throw new Error(data?.message || data?.detail || 'Busha initialization failed')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Busha failed'
      setError(msg); toast.error(msg)
    } finally { setLoading(false) }
  }

  const handleKotani = async () => {
    if (!session) { toast.error('Sign in to buy crypto'); return }
    if (!amount || parseFloat(amount) <= 0) { toast.error('Enter a valid amount'); return }
    if (!kotaniPhone) { toast.error('Enter your phone number'); return }
    if (!kotaniTelco) { toast.error('Select your mobile network'); return }
    setLoading(true); setError(null)
    try {
      const res = await api.post('/api/v1/kotani/onramp/initialize', {
        amount_fiat: parseFloat(amount), currency, crypto_asset: asset,
        phone_number: kotaniPhone, network: kotaniTelco,
      })
      const data = res.data || res
      if (data?.success) {
        setKotaniPayInDetails(data)
        setKotaniPayInSent(true)
        toast.success('Payment request sent to your phone!')
      } else {
        throw new Error(data?.message || data?.detail || 'Kotani initialization failed')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Kotani failed'
      setError(msg); toast.error(msg)
    } finally { setLoading(false) }
  }

  const handleBushaCopyAccount = () => {
    const acct = bushaPayInDetails?.pay_in_details?.account_number
    if (acct) { navigator.clipboard.writeText(acct); setBushaAccountCopied(true); toast.success('Copied!'); setTimeout(() => setBushaAccountCopied(false), 2000) }
  }

  // ─────────────────────────────────────────────────────────
  // EXISTING computed values — untouched
  // ─────────────────────────────────────────────────────────
  const selectedCurrency = LOCAL_CURRENCIES.find(c => c.code === currency)
  const activeGroups     = provider === 'moonpay' ? MOONPAY_ASSET_GROUPS : LOCAL_ASSET_GROUPS
  const selectedLabel    = Object.values(activeGroups).flat().find((a: any) => a.value === asset)

  // NEW computed values
  const availableProviders = getAvailableProviders(currency)
  const bushaOnrampCurrencies = LOCAL_CURRENCIES.filter(c => ONRAMP_PROVIDER_CURRENCIES.busha.includes(c.code))
  const kotaniOnrampCurrencies = LOCAL_CURRENCIES.filter(c => ONRAMP_PROVIDER_CURRENCIES.kotani.includes(c.code))
  const kotaniTelcos = KOTANI_ONRAMP_TELCOS[currency] ?? []
  const selectedBushaCurrency = LOCAL_CURRENCIES.find(c => c.code === currency)
  const selectedKotaniCurrency = LOCAL_CURRENCIES.find(c => c.code === currency)
  
  const handleWapiPay = async () => {
    if (!session) { toast.error('Sign in to continue'); return }
    setWapiVALoading(true); setError(null)
    try {
      const res = await api.get('/api/v1/wapipay/virtual-account')
      if (res?.success) setWapiVA(res)
      else throw new Error(res?.error || 'Could not load account')
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'WapiPay unavailable')
    } finally { setWapiVALoading(false) }
  }

  // Dispatch to correct handler based on provider
  const handleSubmit = () => {
    if (provider === 'moonpay') return handleMoonPay()
    if (provider === 'busha')   return handleBusha()
    if (provider === 'kotani')  return handleKotani()
    if (provider === 'wapipay') return handleWapiPay()
    return handleLocalPay()
  }

  // Submit button disabled state (each provider has its own logic)
  const isSubmitDisabled = loading || fetchingQuote ||
    (provider === 'local'   && (!amount || parseFloat(amount) <= 0)) ||
    (provider === 'busha'   && (bushaFetchingQuote || (!amount || parseFloat(amount) <= 0) || bushaPayInStep === 'bank_details')) ||
    (provider === 'kotani'  && (kotaniFetchingQuote || (!amount || parseFloat(amount) <= 0) || !kotaniPhone || !kotaniTelco || kotaniPayInSent)) ||
    (provider === 'wapipay'  && (wapiVALoading || !!wapiVA))
    

  // Submit button label
  const submitLabel = (() => {
    if (loading) return <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Launching...</>
    if (provider === 'moonpay') return <><ShieldCheck className="mr-2 h-4 w-4" />Buy with MoonPay</>
    if (provider === 'busha')   return <><Wallet className="mr-2 h-4 w-4" />Get Bank Account</>
    if (provider === 'kotani')  return <><Smartphone className="mr-2 h-4 w-4" />Send Payment Request</>
    if (provider === 'wapipay') return <><Globe className="mr-2 h-4 w-4" />Get NGN Account</>
    return <><Wallet className="mr-2 h-4 w-4" />Pay {selectedCurrency?.symbol}{amount || '0'}</>
  })()

  // Submit button colour
  const submitClass = (() => {
    if (provider === 'moonpay') return 'bg-blue-600 hover:bg-blue-700'
    if (provider === 'busha')   return 'bg-purple-600 hover:bg-purple-700'
    if (provider === 'kotani')  return 'bg-orange-600 hover:bg-orange-700'
    if (provider === 'wapipay') return 'bg-cyan-600 hover:bg-cyan-700'
    return 'bg-green-600 hover:bg-green-700'
  })()

  // ─────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="
        w-[95vw] max-w-md
        max-h-[92dvh] overflow-y-auto
        rounded-2xl p-0
        bg-white
        border border-gray-200
        shadow-2xl
      ">
        {/* Sticky Header — original structure preserved */}
        <div className="sticky top-0 z-10 bg-white border-b border-gray-100 px-5 pt-5 pb-4 rounded-t-2xl">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle className="flex items-center gap-2 text-lg font-bold text-gray-900">
                <div className="p-2 rounded-xl bg-blue-50">
                  <Wallet className="h-5 w-5 text-blue-600" />
                </div>
                Buy Crypto
              </DialogTitle>
              <button
                onClick={() => onOpenChange(false)}
                className="rounded-full p-1.5 hover:bg-gray-100 transition-colors"
                aria-label="Close"
              >
                <X className="h-4 w-4 text-gray-500" />
              </button>
            </div>
            <DialogDescription className="text-sm text-gray-500 mt-1">
              Card, bank transfer, Apple Pay & Google Pay. 160+ countries.
            </DialogDescription>
          </DialogHeader>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">

          {/* ── Provider Toggle — dynamically shows only capable providers ── */}
          <div className="grid grid-cols-2 gap-2">
            {availableProviders.map(p => {
              const meta = PROVIDER_META[p]
              const isActive = provider === p
              return (
                <button
                  key={p}
                  onClick={() => { setProvider(p); setError(null) }}
                  className={`flex flex-col items-center gap-1 py-3 px-2 rounded-xl border-2 text-sm font-semibold transition-all ${
                    isActive
                      ? meta.activeClass
                      : 'border-gray-200 text-gray-500 hover:border-gray-300'
                  }`}
                >
                  {meta.icon}
                  <span>{meta.label}</span>
                  <span className="text-[10px] font-normal opacity-70">{meta.sublabel}</span>
                </button>
              )
            })}
          </div>

          {/* ── Asset Selection — shared across all providers ── */}
          <div className="space-y-1.5">
            <Label className="text-sm font-semibold text-gray-700">
              Select Asset to Receive
            </Label>
            <Select value={asset} onValueChange={setAsset}>
              <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 bg-gray-50 text-gray-900">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="max-h-72 rounded-xl bg-white border-gray-200 z-[9999]">
                {Object.entries(activeGroups).map(([chain, assets]) => (
                  <div key={chain}>
                    <div className="px-3 py-1.5 text-[10px] font-bold text-gray-400 uppercase tracking-widest bg-gray-50">
                      {chain}
                    </div>
                    {(assets as any[]).map((a: any) => (
                      <SelectItem key={a.value} value={a.value}
                        className="py-2.5 pl-6 text-sm text-gray-900 cursor-pointer">
                        <span className="mr-2">{a.icon}</span>{a.label}
                      </SelectItem>
                    ))}
                  </div>
                ))}
              </SelectContent>
            </Select>
            {asset === 'MATIC' && (
              <p className="text-xs text-purple-600">
                ℹ️ MATIC runs on the POL network — delivered to your Polygon address.
              </p>
            )}
            {provider === 'moonpay' && (
              <p className="text-xs text-amber-600">
                ⚠️ Algorand-native assets (goBTC, goETH, USDCa) not supported by MoonPay. Switch to Local Payment for those.
              </p>
            )}
            {provider === 'busha' && BUSHA_ASSET_FALLBACK[asset] && (
              <p className="text-xs text-purple-600">
                ℹ️ Algorand-native assets remapped to their cross-chain equivalent for Busha.
              </p>
            )}
            {provider === 'kotani' && KOTANI_ASSET_FALLBACK[asset] && (
              <p className="text-xs text-orange-600">
                ℹ️ Asset remapped to supported equivalent for Kotani Pay.
              </p>
            )}
          </div>

          {/* ═══════════════════════════════════════════════════════
              EXISTING — LOCAL PAYMENT FLOW (untouched)
          ═══════════════════════════════════════════════════════ */}
          {provider === 'local' && (
            <>
              {/* Currency */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700">Your Currency</Label>
                <Select value={currency} onValueChange={v => { setCurrency(v); setQuote(null) }}>
                  <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 bg-gray-50 text-gray-900">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200 max-h-[260px] z-[9999]">
                    {LOCAL_CURRENCIES.map(c => (
                      <SelectItem key={c.code} value={c.code}
                        className="text-gray-900 hover:bg-gray-100 py-2.5">
                        <span className="text-base mr-2">{c.flag}</span>
                        <span className="font-medium">{c.symbol}</span>
                        <span className="ml-1 text-gray-500">{c.name}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Amount */}
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700">Amount</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-semibold">
                    {selectedCurrency?.symbol}
                  </span>
                  <Input type="number" placeholder="0.00" value={amount}
                    onChange={e => setAmount(e.target.value)} disabled={loading}
                    className="pl-10 h-12 rounded-xl border-gray-200 bg-gray-50 text-gray-900 text-base"
                  />
                </div>
                <p className="text-xs text-gray-400">
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
                <div className="rounded-xl bg-blue-50 border border-blue-100 p-3.5 space-y-2">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Live Quote</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Fee ({quote.total_fee_pct?.toFixed(1)}%)</span>
                    <span className="text-gray-600">-{selectedCurrency?.symbol}{quote.total_fee?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-bold pt-1.5 border-t border-blue-200">
                    <span className="text-gray-800 text-sm">You Receive</span>
                    <span className="text-green-600 text-sm">
                      {quote.crypto_to_receive?.toFixed(4)} {asset.split('_')[0]}
                    </span>
                  </div>
                </div>
              )}

              <Alert className="border border-green-100 bg-green-50 rounded-xl py-3">
                <Info className="h-4 w-4 text-green-600 shrink-0 mt-0.5" />
                <AlertDescription className="text-xs text-gray-700 leading-relaxed">
                  <strong className="text-green-700">Smart routing</strong> — best provider auto-selected for your currency. Crypto credited instantly after payment.
                  {currency === 'NGN' && <span className="block mt-1 text-blue-600">🔵 Powered by Paystack for NGN</span>}
                </AlertDescription>
              </Alert>
            </>
          )}

          {/* ═══════════════════════════════════════════════════════
              EXISTING — MOONPAY FLOW (untouched)
          ═══════════════════════════════════════════════════════ */}
          {provider === 'moonpay' && (
            <>
              <div className="space-y-1.5">
                <Label className="text-sm font-semibold text-gray-700">
                  Amount <span className="font-normal text-gray-400">(optional pre-fill)</span>
                </Label>
                <div className="flex gap-2">
                  <Input type="number" placeholder="0.00" value={amount}
                    onChange={e => setAmount(e.target.value)} disabled={loading}
                    className="flex-1 h-12 rounded-xl border-gray-200 bg-gray-50 text-gray-900"
                  />
                  <Select value={mpCurrency} onValueChange={setMpCurrency}>
                    <SelectTrigger className="w-24 h-12 rounded-xl border-gray-200 bg-gray-50 text-gray-900">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl bg-white border-gray-200 z-[9999]">
                      {MOONPAY_FIAT.map(c => (
                        <SelectItem key={c.code} value={c.code} className="text-gray-900">
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
                  <div key={b.text} className="flex flex-col items-center gap-1 p-2.5 rounded-xl bg-gray-50 text-center">
                    <span className="text-lg">{b.icon}</span>
                    <span className="text-[10px] font-medium text-gray-500">{b.text}</span>
                  </div>
                ))}
              </div>

              <Alert className="border border-blue-100 bg-blue-50 rounded-xl py-3">
                <Info className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
                <AlertDescription className="text-xs text-gray-700 leading-relaxed">
                  Powered by <strong className="text-blue-600">MoonPay</strong> —
                  crypto delivered directly to your Seamount wallet. Apple Pay & Google Pay open in a new tab.
                </AlertDescription>
              </Alert>
            </>
          )}

          {/* ═══════════════════════════════════════════════════════
              NEW — BUSHA FLOW (addon)
          ═══════════════════════════════════════════════════════ */}
          {provider === 'busha' && (
            <>
              {bushaPayInStep === 'form' && (
                <>
                  {/* Busha currency — filtered to NGN / KES */}
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700">Your Currency</Label>
                    <Select value={currency} onValueChange={v => { setCurrency(v); setBushaQuote(null) }}>
                      <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 bg-gray-50 text-gray-900">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-white border-gray-200 z-[9999]">
                        {bushaOnrampCurrencies.map(c => (
                          <SelectItem key={c.code} value={c.code} className="text-gray-900 py-2.5">
                            <span className="text-base mr-2">{c.flag}</span>
                            <span className="font-medium">{c.symbol}</span>
                            <span className="ml-1 text-gray-500">{c.name}</span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Amount */}
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700">Amount</Label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-semibold">
                        {selectedBushaCurrency?.symbol}
                      </span>
                      <Input type="number" placeholder="0.00" value={amount}
                        onChange={e => setAmount(e.target.value)} disabled={loading}
                        className="pl-10 h-12 rounded-xl border-gray-200 bg-gray-50 text-gray-900 text-base"
                      />
                    </div>
                    <p className="text-xs text-gray-400">
                      Minimum: {selectedBushaCurrency?.symbol}{currency === 'NGN' ? '1,000' : '10'}
                    </p>
                  </div>

                  {/* Busha live quote */}
                  {bushaFetchingQuote && (
                    <div className="flex items-center gap-2 py-1">
                      <Loader2 className="h-4 w-4 animate-spin text-purple-500" />
                      <span className="text-xs text-gray-400">Fetching Busha quote...</span>
                    </div>
                  )}
                  {bushaQuote && !bushaFetchingQuote && (
                    <div className="rounded-xl bg-purple-50 border border-purple-100 p-3.5 space-y-2">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Live Quote · Busha</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">You pay (gross)</span>
                        <span className="text-gray-600 font-medium">
                          {selectedBushaCurrency?.symbol}{parseFloat(bushaQuote.gross_amount || 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">Fee ({bushaQuote.markup_pct?.toFixed(1)}%)</span>
                        <span className="text-gray-600">
                          -{selectedBushaCurrency?.symbol}{parseFloat(bushaQuote.markup_amount || 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between font-bold pt-1.5 border-t border-purple-200">
                        <span className="text-gray-800 text-sm">You Receive</span>
                        <span className="text-green-600 text-sm">
                          {parseFloat(bushaQuote.crypto_amount || 0).toFixed(6)} {asset.split('_')[0]}
                        </span>
                      </div>
                    </div>
                  )}

                  <Alert className="border border-purple-100 bg-purple-50 rounded-xl py-3">
                    <Info className="h-4 w-4 text-purple-600 shrink-0 mt-0.5" />
                    <AlertDescription className="text-xs text-gray-700 leading-relaxed">
                      <strong className="text-purple-700">Busha Direct</strong> — a temporary bank account will be generated. Transfer the exact amount within the expiry window to complete your purchase.
                    </AlertDescription>
                  </Alert>
                </>
              )}

              {bushaPayInStep === 'bank_details' && bushaPayInDetails && (
                <>
                  <div className="rounded-xl border-2 border-purple-200 overflow-hidden">
                    <div className="bg-purple-50 px-4 py-3 flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5 text-purple-600" />
                      <span className="font-bold text-purple-700 text-sm">Transfer to this account</span>
                    </div>
                    {[
                      { label: 'Bank Name',      value: bushaPayInDetails.pay_in_details?.bank_name },
                      { label: 'Account Number', value: bushaPayInDetails.pay_in_details?.account_number, copy: true },
                      { label: 'Account Name',   value: bushaPayInDetails.pay_in_details?.account_name },
                      { label: 'Amount to Pay',  value: `${selectedBushaCurrency?.symbol}${parseFloat(bushaPayInDetails.pay_in_details?.amount || 0).toFixed(2)}`, highlight: true },
                    ].map(row => (
                      <div key={row.label} className="flex justify-between items-center px-4 py-3 border-t border-purple-100">
                        <span className="text-xs text-gray-500">{row.label}</span>
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-semibold ${row.highlight ? 'text-purple-700 text-base' : 'text-gray-900'}`}>
                            {row.value}
                          </span>
                          {row.copy && (
                            <button onClick={handleBushaCopyAccount} className="text-purple-500 hover:text-purple-700">
                              {bushaAccountCopied ? <CheckCircle2 className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  <Alert className="border border-amber-200 bg-amber-50 rounded-xl py-3">
                    <Info className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                    <AlertDescription className="text-xs text-amber-800 leading-relaxed">
                      Transfer <strong>exactly</strong> the amount shown. Account expires at{' '}
                      <strong>
                        {bushaPayInDetails.pay_in_details?.expires_at
                          ? new Date(bushaPayInDetails.pay_in_details.expires_at).toLocaleTimeString()
                          : 'expiry'}
                      </strong>. Crypto will be credited automatically after payment clears.
                    </AlertDescription>
                  </Alert>
                </>
              )}
            </>
          )}

          {/* ═══════════════════════════════════════════════════════
              NEW — KOTANI PAY FLOW (addon)
          ═══════════════════════════════════════════════════════ */}
          {provider === 'kotani' && (
            <>
              {!kotaniPayInSent ? (
                <>
                  {/* Kotani currency — filtered to Kotani-supported */}
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700">Your Currency</Label>
                    <Select value={currency} onValueChange={v => { setCurrency(v); setKotaniQuote(null); setKotaniTelco('') }}>
                      <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 bg-gray-50 text-gray-900">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-white border-gray-200 max-h-[260px] z-[9999]">
                        {kotaniOnrampCurrencies.map(c => (
                          <SelectItem key={c.code} value={c.code} className="text-gray-900 py-2.5">
                            <span className="text-base mr-2">{c.flag}</span>
                            <span className="font-medium">{c.symbol}</span>
                            <span className="ml-1 text-gray-500">{c.name}</span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Amount */}
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700">Amount</Label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-semibold">
                        {selectedKotaniCurrency?.symbol}
                      </span>
                      <Input type="number" placeholder="0.00" value={amount}
                        onChange={e => setAmount(e.target.value)} disabled={loading}
                        className="pl-10 h-12 rounded-xl border-gray-200 bg-gray-50 text-gray-900 text-base"
                      />
                    </div>
                  </div>

                  {/* Mobile network */}
                  {kotaniTelcos.length > 0 && (
                    <div className="space-y-1.5">
                      <Label className="text-sm font-semibold text-gray-700">Mobile Network</Label>
                      <Select value={kotaniTelco} onValueChange={setKotaniTelco}>
                        <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 bg-gray-50 text-gray-900">
                          <SelectValue placeholder="Select network" />
                        </SelectTrigger>
                        <SelectContent className="bg-white border-gray-200 z-[9999]">
                          {kotaniTelcos.map(t => (
                            <SelectItem key={t.id} value={t.id} className="text-gray-900 py-2.5">{t.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  {/* Phone number */}
                  <div className="space-y-1.5">
                    <Label className="text-sm font-semibold text-gray-700">Phone Number</Label>
                    <Input
                      type="tel" placeholder="e.g. 0712345678"
                      value={kotaniPhone} onChange={e => setKotaniPhone(e.target.value)}
                      disabled={loading}
                      className="h-12 rounded-xl border-gray-200 bg-gray-50 text-gray-900"
                    />
                  </div>

                  {/* Kotani live quote */}
                  {kotaniFetchingQuote && (
                    <div className="flex items-center gap-2 py-1">
                      <Loader2 className="h-4 w-4 animate-spin text-orange-500" />
                      <span className="text-xs text-gray-400">Fetching Kotani quote...</span>
                    </div>
                  )}
                  {kotaniQuote && !kotaniFetchingQuote && (
                    <div className="rounded-xl bg-orange-50 border border-orange-100 p-3.5 space-y-2">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Live Quote · Kotani Pay</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">Fee ({kotaniQuote.markup_pct?.toFixed(1)}%)</span>
                        <span className="text-gray-600">
                          -{parseFloat(kotaniQuote.markup_crypto || 0).toFixed(6)} {asset.split('_')[0]}
                        </span>
                      </div>
                      <div className="flex justify-between font-bold pt-1.5 border-t border-orange-200">
                        <span className="text-gray-800 text-sm">You Receive</span>
                        <span className="text-green-600 text-sm">
                          {parseFloat(kotaniQuote.net_crypto || 0).toFixed(6)} {asset.split('_')[0]}
                        </span>
                      </div>
                    </div>
                  )}

                  <Alert className="border border-orange-100 bg-orange-50 rounded-xl py-3">
                    <Info className="h-4 w-4 text-orange-600 shrink-0 mt-0.5" />
                    <AlertDescription className="text-xs text-gray-700 leading-relaxed">
                      <strong className="text-orange-700">Kotani Pay</strong> — a payment request (STK push) will be sent to your phone. Approve it to complete the purchase.
                    </AlertDescription>
                  </Alert>
                </>
              ) : (
                /* STK push sent confirmation */
                <div className="text-center py-4 space-y-3">
                  <div className="p-4 rounded-full bg-orange-50 w-20 h-20 mx-auto flex items-center justify-center">
                    <Smartphone className="h-10 w-10 text-orange-500 animate-pulse" />
                  </div>
                  <p className="font-bold text-lg text-gray-900">Check Your Phone</p>
                  <p className="text-sm text-gray-500 leading-relaxed px-4">
                    A payment request has been sent to <strong>{kotaniPayInDetails?.pay_in_details?.phone_number || kotaniPhone}</strong> via{' '}
                    <strong>{kotaniPayInDetails?.pay_in_details?.telco || kotaniTelco}</strong>. Approve it to complete your purchase.
                  </p>
                  <div className="rounded-xl bg-gray-50 border border-gray-200 p-3">
                    <p className="text-xs text-gray-500">Amount</p>
                    <p className="text-xl font-bold text-gray-900">
                      {selectedKotaniCurrency?.symbol}{parseFloat(amount).toFixed(2)} {currency}
                    </p>
                  </div>
                  <p className="text-xs text-gray-400">Crypto will appear in your wallet within 2–5 minutes after approval.</p>
                </div>
              )}
            </>
          )}

          {/* ═══════════ WAPIPAY — NGN VIRTUAL ACCOUNT FLOW ═══════════ */}
          {provider === 'wapipay' && (
            <>
              {!wapiVA ? (
                <Alert className="border border-cyan-100 dark:border-cyan-900 bg-cyan-50 dark:bg-cyan-900/20 rounded-xl py-3">
                  <Info className="h-4 w-4 text-cyan-600 shrink-0 mt-0.5" />
                  <AlertDescription className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                    <strong className="text-cyan-700 dark:text-cyan-400">WapiPay Virtual Account</strong> — we'll assign you a dedicated NGN bank account. Transfer any amount anytime — crypto is credited automatically.
                  </AlertDescription>
                </Alert>
              ) : (
                <div className="rounded-xl border-2 border-cyan-200 dark:border-cyan-700 overflow-hidden">
                  <div className="bg-cyan-50 dark:bg-cyan-900/30 px-4 py-3 flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-cyan-600" />
                    <span className="font-bold text-cyan-700 dark:text-cyan-300 text-sm">Your NGN Deposit Account</span>
                  </div>
                  {[
                    { label: 'Bank Name',      value: wapiVA.bank_name },
                    { label: 'Account Number', value: wapiVA.account_number },
                    { label: 'Account Name',   value: wapiVA.account_name },
                  ].map(row => (
                    <div key={row.label} className="flex justify-between items-center px-4 py-3 border-t border-cyan-100 dark:border-cyan-800">
                      <span className="text-xs text-gray-500 dark:text-gray-400">{row.label}</span>
                      <span className="text-sm font-semibold text-gray-900 dark:text-white">{row.value}</span>
                    </div>
                  ))}
                  <div className="px-4 py-3 border-t border-cyan-100 dark:border-cyan-800 bg-cyan-50/50 dark:bg-cyan-900/20">
                    <p className="text-xs text-cyan-700 dark:text-cyan-300">{wapiVA.instruction}</p>
                  </div>
                </div>
              )}
              {wapiVALoading && (
                <div className="flex items-center gap-2 py-2">
                  <Loader2 className="h-4 w-4 animate-spin text-cyan-500" />
                  <span className="text-xs text-gray-400">Loading your account...</span>
                </div>
              )}
            </>
          )}

          {/* Error — shared across all providers */}
          {error && (
            <Alert variant="destructive" className="rounded-xl border py-3">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <AlertDescription className="text-xs">{error}</AlertDescription>
            </Alert>
          )}
        </div>

        {/* Sticky Footer */}
        <div className="sticky bottom-0 bg-white border-t border-gray-100 px-5 py-4 rounded-b-2xl space-y-3">
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}
              className="flex-1 h-12 rounded-xl border-gray-200 font-semibold">
              Cancel
            </Button>
            {(provider === 'busha' && bushaPayInStep === 'bank_details') || (provider === 'kotani' && kotaniPayInSent) || (provider === 'wapipay' && !!wapiVA) ? (
              <Button onClick={() => onOpenChange(false)}
                className="flex-[2] h-12 rounded-xl font-bold text-white bg-green-600 hover:bg-green-700">
                Done
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                disabled={isSubmitDisabled}
                className={`flex-[2] h-12 rounded-xl font-bold text-white ${submitClass}`}
              >
                {submitLabel}
              </Button>
            )}
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