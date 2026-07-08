// File: frontend/src/components/wallet/WithdrawModal.tsx
/**
 * WithdrawModal Component - PRODUCTION-READY Off-ramp
 * ✅ Crypto → Fiat conversion (not fiat input)
 * ✅ Bank transfers + Mobile Money (Cashramp primary)
 * ✅ Multi-currency support (10+ African countries)
 * ✅ Live quotes with proper error handling
 * ✅ Paystack fallback for bank verification
 * ✅ Uses global wallet balances (no local fetch)
 * ✅ Busha + Kotani Pay as addon rails (Option A)
 */

import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button.tsx'
import { Input } from '@/components/ui/input.tsx'
import { Label } from '@/components/ui/label.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import { Loader2, ArrowDownToLine, AlertCircle, CheckCircle2, Building2, Smartphone, Info, Wallet, X } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useWallet } from '@/contexts/WalletContext'

// ─────────────────────────────────────────────────────────────
// EXISTING constants — untouched
// ─────────────────────────────────────────────────────────────
const ASSET_GROUPS = {
  algorand: [
    { value: 'ALGO', label: 'Algorand (ALGO)', icon: 'Ⱥ' },
    { value: 'USDT', label: 'Tether (Algorand)', icon: '₮' },
    { value: 'USDCa', label: 'USD Coin (USDCa)', icon: '◎' },
    { value: 'goBTC', label: 'Wrapped Bitcoin', icon: '₿' },
    { value: 'goETH', label: 'Wrapped Ethereum', icon: 'Ξ' },
  ],
  bitcoin: [{ value: 'BTC', label: 'Bitcoin (BTC)', icon: '₿' }],
  ethereum: [
    { value: 'ETH', label: 'Ethereum (ETH)', icon: 'Ξ' },
    { value: 'USDT_ETH', label: 'Tether (Ethereum)', icon: '₮' },
    { value: 'USDC_ETH', label: 'USD Coin (Ethereum)', icon: '◎' },
  ],
  polygon: [
    { value: 'MATIC', label: 'Polygon (MATIC)', icon: '▶' },
    { value: 'USDT_POLYGON', label: 'Tether (Polygon)', icon: '₮' },
    { value: 'USDC_POLYGON', label: 'USD Coin (Polygon)', icon: '◎' },
  ],
  tron: [
    { value: 'TRX', label: 'TRON (TRX)', icon: '⚡' },
    { value: 'USDT_TRON', label: 'Tether (Tron)', icon: '₮' },
  ],
  solana: [
    { value: 'SOL', label: 'Solana (SOL)', icon: '◎' },
    { value: 'USDT_SOLANA', label: 'Tether (Solana)', icon: '₮' },
    { value: 'USDC_SOLANA', label: 'USD Coin (Solana)', icon: '◎' },
  ]
}

const CHAIN_NAMES: { [key: string]: string } = {
  'algorand': '🟢 Algorand',
  'bitcoin':  '🟠 Bitcoin',
  'ethereum': '🔵 Ethereum',
  'polygon':  '🟣 Polygon',
  'tron':     '🔴 Tron',
  'solana':   '🟣 Solana'
}

// EXISTING — includes XOF + XAF added as Kotani-only (additive)
const WITHDRAWAL_CURRENCIES = [
  { code: 'NGN', name: 'Nigerian Naira',      symbol: '₦',    flag: '🇳🇬', methods: ['bank_transfer'],              mobile_providers: [],                                           providers: ['cashramp', 'paystack'] },
  { code: 'KES', name: 'Kenyan Shilling',     symbol: 'KSh',  flag: '🇰🇪', methods: ['bank_transfer','mobile_money'], mobile_providers: ['mpesa','airtel'],                          providers: ['cashramp'] },
  { code: 'GHS', name: 'Ghanaian Cedi',       symbol: 'GH₵',  flag: '🇬🇭', methods: ['bank_transfer','mobile_money'], mobile_providers: ['mtn','vodafone','airteltigo'],             providers: ['cashramp'] },
  { code: 'ZAR', name: 'South African Rand',  symbol: 'R',    flag: '🇿🇦', methods: ['bank_transfer'],              mobile_providers: [],                                           providers: ['cashramp'] },
  { code: 'UGX', name: 'Ugandan Shilling',    symbol: 'USh',  flag: '🇺🇬', methods: ['mobile_money'],              mobile_providers: ['mtn','airtel'],                            providers: ['cashramp'] },
  { code: 'TZS', name: 'Tanzanian Shilling',  symbol: 'TSh',  flag: '🇹🇿', methods: ['mobile_money'],              mobile_providers: ['mpesa','airtel','tigo'],                   providers: ['cashramp'] },
  { code: 'RWF', name: 'Rwandan Franc',       symbol: 'FRw',  flag: '🇷🇼', methods: ['mobile_money'],              mobile_providers: ['mtn','airtel'],                            providers: ['cashramp'] },
  { code: 'ZMW', name: 'Zambian Kwacha',      symbol: 'ZK',   flag: '🇿🇲', methods: ['mobile_money'],              mobile_providers: ['mtn','airtel','zamtel'],                   providers: ['cashramp'] },
  // NEW (additive) — Kotani-only currencies
  { code: 'XOF', name: 'West African CFA',    symbol: 'CFA',  flag: '🌍',  methods: ['mobile_money'],              mobile_providers: ['orange','mtn'],                            providers: ['kotani'] },
  { code: 'XAF', name: 'Central African CFA', symbol: 'FCFA', flag: '🌍',  methods: ['mobile_money'],              mobile_providers: ['orange','mtn'],                            providers: ['kotani'] },
]

const NIGERIAN_BANKS = [
  { code: '044', name: 'Access Bank' },
  { code: '023', name: 'Citibank Nigeria' },
  { code: '050', name: 'Ecobank Nigeria' },
  { code: '070', name: 'Fidelity Bank' },
  { code: '011', name: 'First Bank of Nigeria' },
  { code: '214', name: 'FCMB (First City Monument Bank)' },
  { code: '058', name: 'GTBank (Guaranty Trust)' },
  { code: '030', name: 'Heritage Bank' },
  { code: '301', name: 'Jaiz Bank' },
  { code: '082', name: 'Keystone Bank' },
  { code: '526', name: 'Parallex Bank' },
  { code: '076', name: 'Polaris Bank' },
  { code: '101', name: 'Providus Bank' },
  { code: '221', name: 'Stanbic IBTC Bank' },
  { code: '068', name: 'Standard Chartered Bank Nigeria' },
  { code: '232', name: 'Sterling Bank' },
  { code: '100', name: 'SunTrust Bank' },
  { code: '032', name: 'Union Bank of Nigeria' },
  { code: '033', name: 'UBA (United Bank for Africa)' },
  { code: '215', name: 'Unity Bank' },
  { code: '035', name: 'Wema Bank (ALAT)' },
  { code: '057', name: 'Zenith Bank' },
  { code: '999240', name: 'Kuda Bank' },
  { code: '120001', name: 'Opay (OPay Digital Services)' },
  { code: '100033', name: 'Palmpay' },
  { code: '120003', name: 'Moniepoint MFB' },
  { code: '100026', name: 'Carbon (Paylater)' },
  { code: '090325', name: 'Fairmoney MFB' },
  { code: '090267', name: 'Kuda MFB' },
  { code: '035A', name: 'ALAT by Wema' },
  { code: '000036', name: 'Globus Bank' },
  { code: '000026', name: 'Taj Bank' },
  { code: '000031', name: 'Titan Trust Bank' },
  { code: '000029', name: 'Optimus Bank' },
  { code: '000025', name: 'Lotus Bank' },
  { code: '000027', name: 'Paga' },
  { code: '100002', name: 'Paga MFB' },
  { code: '090115', name: 'Empire Trust MFB' },
  { code: '090261', name: 'Mint MFB' },
  { code: '090303', name: 'Aella MFB' },
  { code: '100004', name: 'ASO Savings & Loans' },
]

const KENYAN_BANKS = [
  { code: '01', name: 'Kenya Commercial Bank (KCB)' },
  { code: '02', name: 'Equity Bank Kenya' },
  { code: '03', name: 'Co-operative Bank of Kenya' },
  { code: '04', name: 'NCBA Bank Kenya' },
  { code: '05', name: 'Absa Bank Kenya' },
  { code: '06', name: 'Standard Chartered Bank Kenya' },
  { code: '07', name: 'I&M Bank Kenya' },
  { code: '08', name: 'Diamond Trust Bank (DTB)' },
  { code: '09', name: 'Family Bank Kenya' },
  { code: '10', name: 'Stanbic Bank Kenya' },
  { code: '11', name: 'Bank of Africa Kenya' },
  { code: '12', name: 'Citibank Kenya' },
  { code: '13', name: 'HFC Bank (Housing Finance)' },
  { code: '14', name: 'National Bank of Kenya' },
  { code: '15', name: 'Prime Bank Kenya' },
  { code: '16', name: 'SBM Bank Kenya' },
  { code: '17', name: 'Sidian Bank' },
  { code: '18', name: 'Spire Bank' },
  { code: '19', name: 'Trans-National Bank' },
  { code: '20', name: 'UBA Kenya' },
  { code: '21', name: 'Victoria Commercial Bank' },
  { code: 'D01', name: 'M-Pesa (Safaricom)' },
  { code: 'D02', name: 'Airtel Money Kenya' },
  { code: 'D03', name: 'T-Kash (Telkom Kenya)' },
  { code: 'D04', name: 'Equity EazzyBanking' },
  { code: 'D05', name: 'KCB M-Pesa' },
  { code: 'D06', name: 'MCo-op Cash' },
]

const MOBILE_PROVIDER_NAMES: { [key: string]: string } = {
  'mpesa': 'M-Pesa',
  'airtel': 'Airtel Money',
  'mtn': 'MTN Mobile Money',
  'vodafone': 'Vodafone Cash',
  'airteltigo': 'AirtelTigo Money',
  'tigo': 'Tigo Pesa',
  'zamtel': 'Zamtel Money',
  'orange': 'Orange Money',
}

// ─────────────────────────────────────────────────────────────
// NEW — addon constants only
// ─────────────────────────────────────────────────────────────
type WithdrawProvider = 'cashramp' | 'busha' | 'kotani' | 'wapipay'

// Capability matrix — drives tab visibility per currency
const OFFRAMP_PROVIDER_CURRENCIES: Record<WithdrawProvider, string[]> = {
  cashramp: ['NGN','KES','GHS','ZAR','UGX','TZS','RWF','ZMW'],
  busha:    ['NGN','KES'],
  kotani:   ['KES','GHS','UGX','TZS','RWF','ZMW','XOF','XAF','ZAR'],
  wapipay:  ['KES', 'UGX', 'TZS', 'RWF', 'ZMW'],
}

const WITHDRAW_PROVIDER_META: Record<WithdrawProvider, { label: string; sublabel: string; activeClass: string }> = {
  cashramp: { label: 'Cashramp',   sublabel: 'Smart routing · Africa', activeClass: 'border-blue-500 bg-blue-50 text-blue-700'      },
  busha:    { label: 'Busha',      sublabel: 'Bank transfer · NGN/KES', activeClass: 'border-purple-500 bg-purple-50 text-purple-700' },
  kotani:   { label: 'Kotani Pay', sublabel: 'Mobile money · Africa',   activeClass: 'border-orange-500 bg-orange-50 text-orange-700' },
  wapipay:  { label: 'WapiPay', sublabel: 'Bank wire · EA corridors', activeClass: 'border-cyan-500 bg-cyan-50 dark:bg-cyan-900/20 text-cyan-700 dark:text-cyan-300' },
}

// Kotani telcos for offramp
const KOTANI_OFFRAMP_TELCOS: Record<string, { id: string; name: string }[]> = {
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

// Derive which providers are available for a given currency
const getAvailableWithdrawProviders = (curr: string): WithdrawProvider[] =>
  (Object.entries(OFFRAMP_PROVIDER_CURRENCIES) as [WithdrawProvider, string[]][])
    .filter(([, currencies]) => currencies.includes(curr))
    .map(([p]) => p)

// ── NEW — WapiPay addon constants ──────────────────────────────
const WAPIPAY_COUNTRY_MAP: Record<string, string> = {
  KES: 'KE', UGX: 'UG', TZS: 'TZ', RWF: 'RW', ZMW: 'ZM',
}
const WAPIPAY_MOBILE_NETWORKS: Record<string, { id: string; name: string }[]> = {
  KES: [{ id: 'MPESA', name: 'M-Pesa' }, { id: 'AIRTEL', name: 'Airtel Money' }],
  UGX: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'AIRTEL', name: 'Airtel Money' }],
  TZS: [{ id: 'MPESA', name: 'M-Pesa' }, { id: 'AIRTEL', name: 'Airtel' }, { id: 'TIGO', name: 'Tigo Cash' }],
  RWF: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'AIRTEL', name: 'Airtel Money' }],
  ZMW: [{ id: 'MTN', name: 'MTN MoMo' }, { id: 'AIRTEL', name: 'Airtel Money' }],
}

interface WithdrawModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function WithdrawModal({ open, onOpenChange }: WithdrawModalProps) {
  // ─────────────────────────────────────────────────────────
  // EXISTING STATE — untouched
  // ─────────────────────────────────────────────────────────
  const [amount, setAmount]           = useState('')
  const [asset, setAsset]             = useState('ALGO')
  const [currency, setCurrency]       = useState('NGN')
  const [loading, setLoading]         = useState(false)
  const [verifying, setVerifying]     = useState(false)
  const [error, setError]             = useState<string | null>(null)
  const [quote, setQuote]             = useState<any>(null)
  const [fetchingQuote, setFetchingQuote] = useState(false)

  const [payoutMethod, setPayoutMethod] = useState<'bank_transfer' | 'mobile_money'>('bank_transfer')

  const [bankAccount, setBankAccount] = useState('')
  const [bankCode, setBankCode]       = useState('')
  const [accountName, setAccountName] = useState<string | null>(null)

  const [mobileProvider, setMobileProvider] = useState('')
  const [mobileNumber, setMobileNumber]     = useState('')

  const { session }  = useAuth()
  const { balances } = useWallet()

  const availableBalance = balances[asset]?.balance || 0

  const selectedCurrency    = WITHDRAWAL_CURRENCIES.find(c => c.code === currency)
  const supportsMobileMoney = selectedCurrency?.methods?.includes('mobile_money') || false
  const supportsBankTransfer = selectedCurrency?.methods?.includes('bank_transfer') || false

  // ─────────────────────────────────────────────────────────
  // NEW STATE — addon only
  // ─────────────────────────────────────────────────────────
  const [withdrawProvider, setWithdrawProvider] = useState<WithdrawProvider>('cashramp')
  // Busha offramp state
  const [bushaWBankCode, setBushaWBankCode]         = useState('')
  const [bushaWBankAccount, setBushaWBankAccount]   = useState('')
  const [bushaWAccountName, setBushaWAccountName]   = useState<string | null>(null)
  const [bushaWPhone, setBushaWPhone]               = useState('')
  const [bushaWQuote, setBushaWQuote]               = useState<any>(null)
  const [bushaWFetchingQuote, setBushaWFetchingQuote] = useState(false)
  const [bushaWVerifying, setBushaWVerifying]       = useState(false)
  // Kotani offramp state
  const [kotaniWPhone, setKotaniWPhone]               = useState('')
  const [kotaniWTelco, setKotaniWTelco]               = useState('')
  const [kotaniWQuote, setKotaniWQuote]               = useState<any>(null)
  const [kotaniWFetchingQuote, setKotaniWFetchingQuote] = useState(false)
  // WapiPay offramp state
  const [wapiWPhone, setWapiWPhone]   = useState('')
  const [wapiWNetwork, setWapiWNetwork] = useState('')
  const [wapiWQuote, setWapiWQuote]   = useState<any>(null)
  const [wapiWFetching, setWapiWFetching] = useState(false)

  // ─────────────────────────────────────────────────────────
  // EXISTING useEffects — untouched
  // ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (selectedCurrency) {
      if (selectedCurrency.methods.length === 1) {
        setPayoutMethod(selectedCurrency.methods[0] as 'bank_transfer' | 'mobile_money')
      } else if (!selectedCurrency.methods.includes(payoutMethod)) {
        setPayoutMethod(selectedCurrency.methods[0] as 'bank_transfer' | 'mobile_money')
      }
    }
  }, [currency])

  useEffect(() => {
    const timer = setTimeout(() => {
      if (amount && parseFloat(amount) > 0 && asset && currency) {
        fetchQuote()
      }
    }, 500)
    return () => clearTimeout(timer)
  }, [amount, asset, currency])

  // ─────────────────────────────────────────────────────────
  // NEW useEffects — addon only
  // ─────────────────────────────────────────────────────────

  // Capability matrix: auto-fallback when currency changes
  useEffect(() => {
    const avail = getAvailableWithdrawProviders(currency)
    if (!avail.includes(withdrawProvider)) {
      setWithdrawProvider(avail[0] || 'cashramp')
    }
    setError(null)
  }, [currency])

  // Reset addon provider state when switching providers
  useEffect(() => {
    setError(null)
    if (withdrawProvider === 'busha') {
      // Ensure currency is Busha-compatible
      if (!OFFRAMP_PROVIDER_CURRENCIES.busha.includes(currency)) setCurrency('NGN')
      setBushaWQuote(null); setBushaWBankCode(''); setBushaWBankAccount(''); setBushaWAccountName(null); setBushaWPhone('')
    }
    if (withdrawProvider === 'kotani') {
      // Ensure currency is Kotani-compatible
      if (!OFFRAMP_PROVIDER_CURRENCIES.kotani.includes(currency)) setCurrency('KES')
      setKotaniWQuote(null); setKotaniWPhone(''); setKotaniWTelco('')
    }
  }, [withdrawProvider])

  // Debounced Busha offramp quote
  useEffect(() => {
    if (withdrawProvider !== 'busha') return
    if (!amount || parseFloat(amount) <= 0) { setBushaWQuote(null); return }
    const timer = setTimeout(fetchBushaWQuote, 500)
    return () => clearTimeout(timer)
  }, [amount, asset, currency, withdrawProvider])

  // Debounced Kotani offramp quote
  useEffect(() => {
    if (withdrawProvider !== 'kotani') return
    if (!amount || parseFloat(amount) <= 0) { setKotaniWQuote(null); return }
    const timer = setTimeout(fetchKotaniWQuote, 500)
    return () => clearTimeout(timer)
  }, [amount, asset, currency, withdrawProvider])

  // ─────────────────────────────────────────────────────────
  // EXISTING handlers — untouched
  // ─────────────────────────────────────────────────────────
  const fetchQuote = async () => {
    const cryptoAmount = parseFloat(amount)
    if (!cryptoAmount || cryptoAmount <= 0) { setQuote(null); return }
    setFetchingQuote(true); setError(null)
    try {
      const endpoint = session ? '/api/v1/offramp/quote' : '/api/v1/offramp/quote/public'
      const response = await api.post(endpoint, {
        crypto_amount: cryptoAmount, crypto_asset: asset, fiat_currency: currency,
      })
      if (response?.success) setQuote(response.quote)
      else setError(response?.error || 'Failed to get quote')
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to get quote'
      setError(errorMsg); setQuote(null)
    } finally { setFetchingQuote(false) }
  }

  const verifyBankAccount = async () => {
    if (!bankAccount || !bankCode || bankAccount.length !== 10) {
      toast.error('Please enter a valid 10-digit account number'); return
    }
    setVerifying(true); setError(null); setAccountName(null)
    try {
      const response = await api.post('/api/v1/bank/verify', {
        account_number: bankAccount, bank_code: bankCode
      })
      if (response.success && response.account_name) {
        setAccountName(response.account_name)
        toast.success(`Account verified: ${response.account_name}`)
      } else {
        throw new Error(response.error || 'Verification failed')
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to verify account'
      setError(errorMsg); toast.error(errorMsg)
    } finally { setVerifying(false) }
  }

  const handleWithdraw = async () => {
    if (!amount || parseFloat(amount) <= 0) { toast.error('Please enter a valid amount'); return }
    if (parseFloat(amount) > availableBalance) {
      toast.error(`Insufficient balance. Available: ${availableBalance.toFixed(6)} ${asset.split('_')[0]}`); return
    }
    if (payoutMethod === 'bank_transfer') {
      if (!accountName) { toast.error('Please verify your bank account first'); return }
    } else {
      if (!mobileProvider || !mobileNumber) { toast.error('Please enter mobile money details'); return }
    }
    setLoading(true); setError(null)
    try {
      const payload: any = {
        crypto_amount: parseFloat(amount),
        crypto_asset: asset,
        recipient_details: {
          country: selectedCurrency?.flag.match(/[\p{Emoji}]/gu)?.[0] === '🇳🇬' ? 'NG' :
                   selectedCurrency?.flag.match(/[\p{Emoji}]/gu)?.[0] === '🇰🇪' ? 'KE' :
                   selectedCurrency?.flag.match(/[\p{Emoji}]/gu)?.[0] === '🇬🇭' ? 'GH' :
                   selectedCurrency?.flag.match(/[\p{Emoji}]/gu)?.[0] === '🇿🇦' ? 'ZA' :
                   selectedCurrency?.flag.match(/[\p{Emoji}]/gu)?.[0] === '🇺🇬' ? 'UG' :
                   selectedCurrency?.flag.match(/[\p{Emoji}]/gu)?.[0] === '🇹🇿' ? 'TZ' :
                   selectedCurrency?.flag.match(/[\p{Emoji}]/gu)?.[0] === '🇷🇼' ? 'RW' :
                   selectedCurrency?.flag.match(/[\p{Emoji}]/gu)?.[0] === '🇿🇲' ? 'ZM' : 'NG',
          currency: currency,
          payment_method: payoutMethod,
        }
      }
      if (payoutMethod === 'bank_transfer') {
        payload.recipient_details.bank_code     = bankCode
        payload.recipient_details.account_number = bankAccount
        payload.recipient_details.account_name  = accountName
      } else {
        payload.recipient_details.network      = mobileProvider
        payload.recipient_details.phone_number = mobileNumber
      }
      const response = await api.post('/api/v1/offramp/withdraw', payload)
      if (response?.success) {
        toast.success('Withdrawal initiated! Funds will arrive within 1-2 hours')
        setAmount(''); setBankAccount(''); setBankCode(''); setAccountName(null)
        setMobileProvider(''); setMobileNumber(''); setQuote(null)
        onOpenChange(false)
      } else {
        throw new Error(response?.error || 'Withdrawal failed')
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Withdrawal failed'
      setError(errorMsg); toast.error(errorMsg)
    } finally { setLoading(false) }
  }

  const getCurrencySymbol = (code: string) => WITHDRAWAL_CURRENCIES.find(c => c.code === code)?.symbol || code
  const getAssetSymbol    = (assetKey: string) => assetKey.split('_')[0]

  // ─────────────────────────────────────────────────────────
  // NEW handlers — addon only
  // ─────────────────────────────────────────────────────────
  const fetchBushaWQuote = async () => {
    setBushaWFetchingQuote(true); setError(null)
    try {
      const res = await api.post('/api/v1/busha/offramp/quote', {
        crypto_asset: asset, crypto_amount: parseFloat(amount), currency,
      })
      if (res?.success) setBushaWQuote(res)
      else setError(res?.message || res?.detail || 'Failed to get Busha quote')
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Busha quote failed')
      setBushaWQuote(null)
    } finally { setBushaWFetchingQuote(false) }
  }

  const fetchKotaniWQuote = async () => {
    setKotaniWFetchingQuote(true); setError(null)
    try {
      const res = await api.post('/api/v1/kotani/offramp/quote', {
        crypto_asset: asset, crypto_amount: parseFloat(amount), currency,
      })
      if (res?.success) setKotaniWQuote(res)
      else setError(res?.message || res?.detail || 'Failed to get Kotani quote')
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Kotani quote failed')
      setKotaniWQuote(null)
    } finally { setKotaniWFetchingQuote(false) }
  }

  const verifyBushaWBank = async () => {
    if (!bushaWBankAccount || !bushaWBankCode || bushaWBankAccount.length !== 10) {
      toast.error('Enter a valid 10-digit account number'); return
    }
    setBushaWVerifying(true); setBushaWAccountName(null)
    try {
      const res = await api.post('/api/v1/bank/verify', {
        account_number: bushaWBankAccount, bank_code: bushaWBankCode,
      })
      if (res?.success && res?.account_name) {
        setBushaWAccountName(res.account_name)
        toast.success(`Account verified: ${res.account_name}`)
      } else {
        throw new Error(res?.error || 'Verification failed')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.message || 'Verification failed')
    } finally { setBushaWVerifying(false) }
  }

  const handleBushaWithdraw = async () => {
    if (!amount || parseFloat(amount) <= 0) { toast.error('Enter a valid amount'); return }
    if (parseFloat(amount) > availableBalance) { toast.error('Insufficient balance'); return }
    if (currency === 'NGN' && !bushaWAccountName) { toast.error('Verify your bank account first'); return }
    if (currency === 'KES' && !bushaWPhone) { toast.error('Enter your M-Pesa phone number'); return }
    setLoading(true); setError(null)
    try {
      const body: any = { crypto_asset: asset, crypto_amount: parseFloat(amount), currency }
      if (currency === 'NGN') {
        body.bank_code      = bushaWBankCode
        body.account_number = bushaWBankAccount
        body.account_name   = bushaWAccountName
      } else {
        body.phone_number = bushaWPhone
      }
      const res = await api.post('/api/v1/busha/offramp/initialize', body)
      const data = res.data || res
      if (data?.success) {
        toast.success('Withdrawal initiated via Busha! Funds arriving in 5–15 minutes.')
        setAmount(''); setBushaWBankCode(''); setBushaWBankAccount(''); setBushaWAccountName(null); setBushaWPhone(''); setBushaWQuote(null)
        onOpenChange(false)
      } else {
        throw new Error(data?.message || data?.detail || 'Busha withdrawal failed')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Busha withdrawal failed'
      setError(msg); toast.error(msg)
    } finally { setLoading(false) }
  }

  const handleKotaniWithdraw = async () => {
    if (!amount || parseFloat(amount) <= 0) { toast.error('Enter a valid amount'); return }
    if (parseFloat(amount) > availableBalance) { toast.error('Insufficient balance'); return }
    if (!kotaniWPhone) { toast.error('Enter your phone number'); return }
    if (!kotaniWTelco) { toast.error('Select your mobile network'); return }
    setLoading(true); setError(null)
    try {
      const res = await api.post('/api/v1/kotani/offramp/initialize', {
        crypto_asset: asset, crypto_amount: parseFloat(amount),
        currency, phone_number: kotaniWPhone, telco_id: kotaniWTelco,
      })
      const data = res.data || res
      if (data?.success) {
        toast.success('Withdrawal initiated via Kotani Pay! Funds arriving in 2–10 minutes.')
        setAmount(''); setKotaniWPhone(''); setKotaniWTelco(''); setKotaniWQuote(null)
        onOpenChange(false)
      } else {
        throw new Error(data?.message || data?.detail || 'Kotani withdrawal failed')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Kotani withdrawal failed'
      setError(msg); toast.error(msg)
    } finally { setLoading(false) }
  }

  const handleWapiWithdraw = async () => {
    if (!amount || parseFloat(amount) <= 0) { toast.error('Enter a valid amount'); return }
    if (parseFloat(amount) > availableBalance) { toast.error('Insufficient balance'); return }
    if (!wapiWPhone) { toast.error('Enter phone number'); return }
    if (!wapiWNetwork) { toast.error('Select mobile network'); return }
    setLoading(true); setError(null)
    try {
      const res = await api.post('/api/v1/wapipay/offramp/mobile', {
        crypto_asset:  asset,
        crypto_amount: parseFloat(amount),
        currency,
        country:       WAPIPAY_COUNTRY_MAP[currency] || 'KE',
        phone_number:  wapiWPhone,
        network:       wapiWNetwork,
      })
      const data = res.data || res
      if (data?.success) {
        toast.success('Withdrawal initiated via WapiPay! Funds arriving in 2–10 minutes.')
        setAmount(''); setWapiWPhone(''); setWapiWNetwork(''); setWapiWQuote(null)
        onOpenChange(false)
      } else {
        throw new Error(data?.detail || data?.error || 'WapiPay withdrawal failed')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'WapiPay failed'
      setError(msg); toast.error(msg)
    } finally { setLoading(false) }
  }

  // NEW computed values
  const availableWithdrawProviders  = getAvailableWithdrawProviders(currency)
  const bushaOfframpCurrencies      = WITHDRAWAL_CURRENCIES.filter(c => OFFRAMP_PROVIDER_CURRENCIES.busha.includes(c.code))
  const kotaniOfframpCurrencies     = WITHDRAWAL_CURRENCIES.filter(c => OFFRAMP_PROVIDER_CURRENCIES.kotani.includes(c.code))
  const kotaniOfframpTelcos         = KOTANI_OFFRAMP_TELCOS[currency] ?? []

  // Dispatch + disabled state — wraps existing handleWithdraw untouched
  const handleWithdrawDispatch = () => {
    if (withdrawProvider === 'busha')   return handleBushaWithdraw()
    if (withdrawProvider === 'kotani')  return handleKotaniWithdraw()
    if (withdrawProvider === 'wapipay') return handleWapiWithdraw()
    return handleWithdraw()
  }

  const isWithdrawDisabled = (() => {
    if (withdrawProvider === 'cashramp') {
      return loading || !quote || !amount || parseFloat(amount) <= 0 || parseFloat(amount) > availableBalance ||
        (payoutMethod === 'bank_transfer' && !accountName) ||
        (payoutMethod === 'mobile_money' && (!mobileProvider || !mobileNumber))
    }
    if (withdrawProvider === 'busha') {
      return loading || bushaWFetchingQuote || !bushaWQuote || !amount ||
        parseFloat(amount) <= 0 || parseFloat(amount) > availableBalance ||
        (currency === 'NGN' && !bushaWAccountName) ||
        (currency === 'KES' && !bushaWPhone)
    }
    if (withdrawProvider === 'wapipay') {
      return loading || !amount || parseFloat(amount) <= 0 ||
        parseFloat(amount) > availableBalance ||
        !wapiWPhone || !wapiWNetwork
    }
    // kotani
    return loading || kotaniWFetchingQuote || !kotaniWQuote || !amount ||
      parseFloat(amount) <= 0 || parseFloat(amount) > availableBalance ||
      !kotaniWPhone || !kotaniWTelco
  })()

  const withdrawButtonLabel = (() => {
    if (loading) return <><Loader2 className="mr-2 h-5 w-5 animate-spin" />Processing...</>
    if (withdrawProvider === 'busha')  return `Withdraw ${bushaWQuote  ? getCurrencySymbol(currency) + parseFloat(bushaWQuote.net_fiat  || 0).toLocaleString() : ''}`
    if (withdrawProvider === 'kotani') return `Withdraw ${kotaniWQuote ? getCurrencySymbol(currency) + parseFloat(kotaniWQuote.net_fiat || 0).toLocaleString() : ''}`
    return `Withdraw ${quote ? getCurrencySymbol(currency) + quote.net_fiat_amount?.toLocaleString() : ''}`
  })()

  // ─────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-[550px] max-w-[95vw] max-h-[90vh] overflow-y-auto bg-white border-2 border-gray-200"
        style={{ zIndex: 1000 }}
      >
        <DialogHeader className="border-b pb-4">
          <DialogTitle className="flex items-center gap-2 text-xl font-bold text-gray-900">
            <ArrowDownToLine className="h-6 w-6 text-red-600" />
            Withdraw to {payoutMethod === 'bank_transfer' ? 'Bank' : 'Mobile Money'}
          </DialogTitle>
          <DialogDescription className="text-base text-gray-600 mt-2">
            Convert crypto to local currency. Fast, secure withdrawals via Cashramp.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">

          {/* ── NEW: Provider Toggle — only when >1 provider available ── */}
          {availableWithdrawProviders.length > 1 && (
            <div className="space-y-2">
              <Label className="text-sm font-semibold text-gray-900">Payment Rail</Label>
              <div className="grid grid-cols-3 gap-2">
                {availableWithdrawProviders.map(p => {
                  const meta = WITHDRAW_PROVIDER_META[p]
                  return (
                    <button
                      key={p}
                      onClick={() => { setWithdrawProvider(p); setError(null) }}
                      className={`flex flex-col items-center gap-1 py-2.5 px-2 rounded-xl border-2 text-xs font-semibold transition-all ${
                        withdrawProvider === p
                          ? meta.activeClass
                          : 'border-gray-200 text-gray-500 hover:border-gray-300 bg-white'
                      }`}
                    >
                      <span className="font-bold">{meta.label}</span>
                      <span className="text-[9px] font-normal opacity-70">{meta.sublabel}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════
              EXISTING — CASHRAMP FLOW (untouched, wrapped in conditional)
          ═══════════════════════════════════════════════════════ */}
          {withdrawProvider === 'cashramp' && (
            <>
              {/* Asset Selection */}
              <div className="space-y-2">
                <Label htmlFor="withdraw-asset" className="text-sm font-semibold text-gray-900">
                  Crypto Asset to Withdraw
                </Label>
                <Select value={asset} onValueChange={setAsset}>
                  <SelectTrigger id="withdraw-asset" className="w-full bg-gray-50 border-gray-300 text-gray-900 h-12">
                    <SelectValue placeholder="Select crypto to withdraw" />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-300 max-h-[400px] z-50">
                    {Object.entries(ASSET_GROUPS).map(([chain, assets]) => (
                      <div key={chain} className="py-2">
                        <div className="px-3 py-2 text-xs font-bold text-gray-500 uppercase tracking-wide bg-gray-100">
                          {CHAIN_NAMES[chain] || chain}
                        </div>
                        {assets.map((a) => (
                          <SelectItem key={a.value} value={a.value}
                            className="text-gray-900 hover:bg-gray-100 py-3 pl-8">
                            <div className="flex items-center gap-2">
                              <span className="text-xl">{a.icon}</span>
                              <span className="font-medium">{a.label}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </div>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Crypto Amount */}
              <div className="space-y-2">
                <Label htmlFor="withdraw-amount" className="text-sm font-semibold text-gray-900">
                  Amount to Withdraw
                </Label>
                {availableBalance > 0 && (
                  <div className="flex justify-between items-center px-3 py-2 bg-blue-50 rounded-lg border border-blue-200">
                    <span className="text-sm text-gray-700">Available:</span>
                    <span className="font-bold text-blue-700">
                      {availableBalance.toFixed(6)} {getAssetSymbol(asset)}
                    </span>
                  </div>
                )}
                <div className="relative">
                  <Input
                    id="withdraw-amount" type="number" step="0.01" min="0.01"
                    max={availableBalance || undefined} placeholder="0.00" value={amount}
                    onChange={(e) => setAmount(e.target.value)} disabled={loading}
                    className="bg-gray-50 border-gray-300 text-gray-900 h-12 text-lg font-medium pr-20"
                  />
                  <span className="absolute right-3 top-3 text-gray-600 font-semibold text-lg">
                    {getAssetSymbol(asset)}
                  </span>
                </div>
                {parseFloat(amount) > availableBalance && availableBalance > 0 && (
                  <p className="text-sm text-red-600 font-medium">⚠️ Amount exceeds available balance</p>
                )}
              </div>

              {/* Currency Selection */}
              <div className="space-y-2">
                <Label htmlFor="withdraw-currency" className="text-sm font-semibold text-gray-900">
                  Receive Currency
                </Label>
                <Select value={currency} onValueChange={setCurrency}>
                  <SelectTrigger id="withdraw-currency" className="w-full bg-gray-50 border-gray-300 text-gray-900 h-12">
                    <SelectValue placeholder="Select currency" />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-300 max-h-[300px] z-50">
                    {WITHDRAWAL_CURRENCIES.filter(c => OFFRAMP_PROVIDER_CURRENCIES.cashramp.includes(c.code)).map((curr) => (
                      <SelectItem key={curr.code} value={curr.code}
                        className="text-gray-900 hover:bg-gray-100 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">{curr.flag}</span>
                          <span className="font-medium">{curr.symbol}</span>
                          <span>{curr.name} ({curr.code})</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Quote Display */}
              {fetchingQuote && (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                  <span className="ml-2 text-sm text-gray-600">Calculating quote...</span>
                </div>
              )}
              {quote && !fetchingQuote && (
                <div className="rounded-xl bg-gradient-to-br from-red-50 to-pink-50 border-2 border-red-200 p-4 space-y-3 shadow-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                      <span className="text-xs font-bold text-gray-700 uppercase tracking-wide">Live Quote</span>
                    </div>
                    <span className="text-xs text-gray-500">Valid 5 min</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-700">Crypto Value:</span>
                    <span className="font-bold text-base text-gray-900">${quote.crypto_value_usd?.toFixed(2)} USD</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-700">Exchange Rate:</span>
                    <span className="font-bold text-base text-gray-900">1 USD = {getCurrencySymbol(currency)}{quote.exchange_rate?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-700">Gross Amount:</span>
                    <span className="font-bold text-base text-gray-900">{getCurrencySymbol(currency)}{quote.gross_fiat_amount?.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-700">Withdrawal Fee ({quote.fee_percentage?.toFixed(1)}%):</span>
                    <span className="font-bold text-base text-gray-900">{getCurrencySymbol(currency)}{quote.withdrawal_fee?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center pt-2 border-t-2 border-red-300">
                    <span className="text-sm font-semibold text-gray-900">You Receive:</span>
                    <span className="font-bold text-xl text-green-600">{getCurrencySymbol(currency)}{quote.net_fiat_amount?.toLocaleString()}</span>
                  </div>
                  <div className="text-xs text-gray-600 mt-2 flex items-center gap-1">
                    <span>📊 Price: {quote.price_source}</span>
                    <span>•</span>
                    <span>💱 Forex: {quote.forex_source}</span>
                  </div>
                </div>
              )}

              {/* Payout Method Selection */}
              {supportsMobileMoney && supportsBankTransfer && (
                <div className="space-y-2">
                  <Label className="text-sm font-semibold text-gray-900">Payout Method</Label>
                  <div className="grid grid-cols-2 gap-3">
                    <Button type="button" variant="outline" onClick={() => setPayoutMethod('bank_transfer')}
                      className={`h-12 text-base font-bold border-2 transition-all duration-200 ${
                        payoutMethod === 'bank_transfer'
                          ? 'bg-gradient-to-br from-blue-500/20 to-indigo-500/20 border-blue-500 text-blue-700 backdrop-blur-sm shadow-lg'
                          : 'bg-white/50 border-gray-300 text-gray-700 hover:bg-gray-100/70 backdrop-blur-sm'
                      }`}>
                      <Building2 className="mr-2 h-5 w-5" />Bank Transfer
                    </Button>
                    <Button type="button" variant="outline" onClick={() => setPayoutMethod('mobile_money')}
                      className={`h-12 text-base font-bold border-2 transition-all duration-200 ${
                        payoutMethod === 'mobile_money'
                          ? 'bg-gradient-to-br from-green-500/20 to-emerald-500/20 border-green-500 text-green-700 backdrop-blur-sm shadow-lg'
                          : 'bg-white/50 border-gray-300 text-gray-700 hover:bg-gray-100/70 backdrop-blur-sm'
                      }`}>
                      <Smartphone className="mr-2 h-5 w-5" />Mobile Money
                    </Button>
                  </div>
                </div>
              )}

              {/* Bank Transfer Fields */}
              {payoutMethod === 'bank_transfer' && supportsBankTransfer && (
                <>
                  {(currency === 'NGN' || currency === 'KES') && (
                    <div className="space-y-2">
                      <Label htmlFor="bank" className="text-sm font-semibold text-gray-900">Bank</Label>
                      <Select value={bankCode} onValueChange={setBankCode}>
                        <SelectTrigger id="bank" className="w-full bg-gray-50 border-gray-300 text-gray-900 h-12">
                          <SelectValue placeholder="Select bank" />
                        </SelectTrigger>
                        <SelectContent className="max-h-[200px] bg-white border-gray-300 z-50">
                          {(currency === 'NGN' ? NIGERIAN_BANKS : KENYAN_BANKS).map(bank => (
                            <SelectItem key={bank.code} value={bank.code} className="text-gray-900 hover:bg-gray-100">
                              {bank.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                  <div className="space-y-2">
                    <Label htmlFor="account" className="text-sm font-semibold text-gray-900">Account Number</Label>
                    <div className="flex gap-2">
                      <Input id="account" type="text" maxLength={10} placeholder="0123456789"
                        value={bankAccount}
                        onChange={(e) => { setBankAccount(e.target.value); setAccountName(null) }}
                        disabled={loading || verifying}
                        className="flex-1 bg-gray-50 border-gray-300 text-gray-900 h-12 text-base"
                      />
                      <Button type="button" variant="outline" onClick={verifyBankAccount}
                        disabled={!bankAccount || !bankCode || verifying || loading || bankAccount.length !== 10}
                        className="shrink-0 h-12 border-2 border-gray-300 text-gray-700 hover:bg-gray-100 font-semibold px-6">
                        {verifying ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Verify'}
                      </Button>
                    </div>
                  </div>
                  {accountName && (
                    <Alert className="bg-green-50 border-2 border-green-300">
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                      <AlertDescription className="text-green-900 font-bold text-base">{accountName}</AlertDescription>
                    </Alert>
                  )}
                </>
              )}

              {/* Mobile Money Fields */}
              {payoutMethod === 'mobile_money' && supportsMobileMoney && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold text-gray-900">Mobile Money Provider</Label>
                    <Select value={mobileProvider} onValueChange={setMobileProvider}>
                      <SelectTrigger className="bg-white border-gray-300 h-12 text-gray-900">
                        <SelectValue placeholder="Select provider" />
                      </SelectTrigger>
                      <SelectContent className="bg-white border-gray-300 z-50">
                        {selectedCurrency?.mobile_providers?.map((provider) => (
                          <SelectItem key={provider} value={provider} className="text-gray-900 hover:bg-gray-100 cursor-pointer">
                            {MOBILE_PROVIDER_NAMES[provider] || provider}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold text-gray-900">Phone Number</Label>
                    <Input type="tel" placeholder="e.g., 0712345678" value={mobileNumber}
                      onChange={(e) => setMobileNumber(e.target.value)}
                      className="bg-white border-gray-300 text-gray-900 placeholder:text-gray-500 h-12"
                    />
                    <p className="text-xs text-gray-700 font-medium">
                      Enter number registered with {mobileProvider ? MOBILE_PROVIDER_NAMES[mobileProvider] : 'mobile money'}
                    </p>
                  </div>
                </div>
              )}

              {/* Provider Info Alert */}
              <Alert className="bg-blue-50 border-2 border-blue-300">
                <Info className="h-5 w-5 text-blue-600" />
                <AlertDescription className="text-gray-900 text-sm font-medium">
                  <strong className="text-blue-700">Smart Routing:</strong> We automatically select the best provider.
                </AlertDescription>
              </Alert>

              {/* Error Display */}
              {error && (
                <Alert variant="destructive" className="border-2">
                  <AlertCircle className="h-5 w-5" />
                  <AlertDescription className="font-medium">{error}</AlertDescription>
                </Alert>
              )}
            </>
          )}

          {/* ═══════════════════════════════════════════════════════
              NEW — BUSHA OFFRAMP FLOW (addon)
          ═══════════════════════════════════════════════════════ */}
          {withdrawProvider === 'busha' && (
            <>
              {/* Asset */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900">Crypto Asset to Sell</Label>
                <Select value={asset} onValueChange={setAsset}>
                  <SelectTrigger className="w-full bg-gray-50 border-gray-300 text-gray-900 h-12">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-300 max-h-[400px] z-50">
                    {Object.entries(ASSET_GROUPS).map(([chain, assets]) => (
                      <div key={chain} className="py-2">
                        <div className="px-3 py-2 text-xs font-bold text-gray-500 uppercase tracking-wide bg-gray-100">{CHAIN_NAMES[chain] || chain}</div>
                        {assets.map((a) => (
                          <SelectItem key={a.value} value={a.value} className="text-gray-900 hover:bg-gray-100 py-3 pl-8">
                            <div className="flex items-center gap-2"><span className="text-xl">{a.icon}</span><span className="font-medium">{a.label}</span></div>
                          </SelectItem>
                        ))}
                      </div>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Amount */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900">Amount to Withdraw</Label>
                {availableBalance > 0 && (
                  <div className="flex justify-between items-center px-3 py-2 bg-blue-50 rounded-lg border border-blue-200">
                    <span className="text-sm text-gray-700">Available:</span>
                    <span className="font-bold text-blue-700">{availableBalance.toFixed(6)} {getAssetSymbol(asset)}</span>
                  </div>
                )}
                <div className="relative">
                  <Input type="number" step="0.01" min="0.01" placeholder="0.00" value={amount}
                    onChange={(e) => setAmount(e.target.value)} disabled={loading}
                    className="bg-gray-50 border-gray-300 text-gray-900 h-12 text-lg font-medium pr-20"
                  />
                  <span className="absolute right-3 top-3 text-gray-600 font-semibold text-lg">{getAssetSymbol(asset)}</span>
                </div>
              </div>

              {/* Currency — Busha-supported only */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900">Receive Currency</Label>
                <Select value={currency} onValueChange={v => { setCurrency(v); setBushaWQuote(null) }}>
                  <SelectTrigger className="w-full bg-gray-50 border-gray-300 text-gray-900 h-12">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-300 z-50">
                    {bushaOfframpCurrencies.map(curr => (
                      <SelectItem key={curr.code} value={curr.code} className="text-gray-900 hover:bg-gray-100 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">{curr.flag}</span>
                          <span className="font-medium">{curr.symbol}</span>
                          <span>{curr.name} ({curr.code})</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Busha Quote */}
              {bushaWFetchingQuote && (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-6 w-6 animate-spin text-purple-600" />
                  <span className="ml-2 text-sm text-gray-600">Getting Busha quote...</span>
                </div>
              )}
              {bushaWQuote && !bushaWFetchingQuote && (
                <div className="rounded-xl bg-purple-50 border-2 border-purple-200 p-4 space-y-3">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-xs font-bold text-gray-700 uppercase tracking-wide">Live Quote · Busha</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-700">Exchange Rate:</span>
                    <span className="font-bold text-gray-900">1 {getAssetSymbol(asset)} = {getCurrencySymbol(currency)}{parseFloat(bushaWQuote.busha_rate || 0).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-700">Fee ({bushaWQuote.markup_pct}%):</span>
                    <span className="font-bold text-gray-900">-{getCurrencySymbol(currency)}{parseFloat(bushaWQuote.markup_amount || 0).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center pt-2 border-t-2 border-purple-300">
                    <span className="text-sm font-semibold text-gray-900">You Receive:</span>
                    <span className="font-bold text-xl text-green-600">{getCurrencySymbol(currency)}{parseFloat(bushaWQuote.net_fiat || 0).toLocaleString()}</span>
                  </div>
                </div>
              )}

              {/* NGN bank fields */}
              {currency === 'NGN' && (
                <>
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold text-gray-900">Bank</Label>
                    <Select value={bushaWBankCode} onValueChange={v => { setBushaWBankCode(v); setBushaWAccountName(null) }}>
                      <SelectTrigger className="w-full bg-gray-50 border-gray-300 text-gray-900 h-12">
                        <SelectValue placeholder="Select bank" />
                      </SelectTrigger>
                      <SelectContent className="max-h-[200px] bg-white border-gray-300 z-50">
                        {NIGERIAN_BANKS.map(bank => (
                          <SelectItem key={bank.code} value={bank.code} className="text-gray-900 hover:bg-gray-100">{bank.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold text-gray-900">Account Number</Label>
                    <div className="flex gap-2">
                      <Input type="text" maxLength={10} placeholder="0123456789"
                        value={bushaWBankAccount}
                        onChange={e => { setBushaWBankAccount(e.target.value); setBushaWAccountName(null) }}
                        disabled={loading || bushaWVerifying}
                        className="flex-1 bg-gray-50 border-gray-300 text-gray-900 h-12 text-base"
                      />
                      <Button type="button" variant="outline" onClick={verifyBushaWBank}
                        disabled={!bushaWBankAccount || !bushaWBankCode || bushaWVerifying || loading || bushaWBankAccount.length !== 10}
                        className="shrink-0 h-12 border-2 border-gray-300 font-semibold px-6">
                        {bushaWVerifying ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Verify'}
                      </Button>
                    </div>
                  </div>
                  {bushaWAccountName && (
                    <Alert className="bg-green-50 border-2 border-green-300">
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                      <AlertDescription className="text-green-900 font-bold text-base">{bushaWAccountName}</AlertDescription>
                    </Alert>
                  )}
                </>
              )}

              {/* KES M-Pesa */}
              {currency === 'KES' && (
                <div className="space-y-2">
                  <Label className="text-sm font-semibold text-gray-900">M-Pesa Phone Number</Label>
                  <Input type="tel" placeholder="e.g. 0712345678" value={bushaWPhone}
                    onChange={e => setBushaWPhone(e.target.value)}
                    className="bg-gray-50 border-gray-300 text-gray-900 h-12"
                  />
                </div>
              )}

              <Alert className="bg-purple-50 border-2 border-purple-300">
                <Info className="h-5 w-5 text-purple-600" />
                <AlertDescription className="text-gray-900 text-sm font-medium">
                  <strong className="text-purple-700">Busha Direct:</strong> Funds arrive in 5–15 minutes via Busha's exchange.
                </AlertDescription>
              </Alert>

              {error && (
                <Alert variant="destructive" className="border-2">
                  <AlertCircle className="h-5 w-5" />
                  <AlertDescription className="font-medium">{error}</AlertDescription>
                </Alert>
              )}
            </>
          )}

          {/* ═══════════════════════════════════════════════════════
              NEW — KOTANI PAY OFFRAMP FLOW (addon)
          ═══════════════════════════════════════════════════════ */}
          {withdrawProvider === 'kotani' && (
            <>
              {/* Asset */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900">Crypto Asset to Sell</Label>
                <Select value={asset} onValueChange={setAsset}>
                  <SelectTrigger className="w-full bg-gray-50 border-gray-300 text-gray-900 h-12">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-300 max-h-[400px] z-50">
                    {Object.entries(ASSET_GROUPS).map(([chain, assets]) => (
                      <div key={chain} className="py-2">
                        <div className="px-3 py-2 text-xs font-bold text-gray-500 uppercase tracking-wide bg-gray-100">{CHAIN_NAMES[chain] || chain}</div>
                        {assets.map((a) => (
                          <SelectItem key={a.value} value={a.value} className="text-gray-900 hover:bg-gray-100 py-3 pl-8">
                            <div className="flex items-center gap-2"><span className="text-xl">{a.icon}</span><span className="font-medium">{a.label}</span></div>
                          </SelectItem>
                        ))}
                      </div>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Amount */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900">Amount to Withdraw</Label>
                {availableBalance > 0 && (
                  <div className="flex justify-between items-center px-3 py-2 bg-blue-50 rounded-lg border border-blue-200">
                    <span className="text-sm text-gray-700">Available:</span>
                    <span className="font-bold text-blue-700">{availableBalance.toFixed(6)} {getAssetSymbol(asset)}</span>
                  </div>
                )}
                <div className="relative">
                  <Input type="number" step="0.01" min="0.01" placeholder="0.00" value={amount}
                    onChange={(e) => setAmount(e.target.value)} disabled={loading}
                    className="bg-gray-50 border-gray-300 text-gray-900 h-12 text-lg font-medium pr-20"
                  />
                  <span className="absolute right-3 top-3 text-gray-600 font-semibold text-lg">{getAssetSymbol(asset)}</span>
                </div>
              </div>

              {/* Currency — Kotani-supported only */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900">Receive Currency</Label>
                <Select value={currency} onValueChange={v => { setCurrency(v); setKotaniWQuote(null); setKotaniWTelco('') }}>
                  <SelectTrigger className="w-full bg-gray-50 border-gray-300 text-gray-900 h-12">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-300 max-h-[300px] z-50">
                    {kotaniOfframpCurrencies.map(curr => (
                      <SelectItem key={curr.code} value={curr.code} className="text-gray-900 hover:bg-gray-100 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">{curr.flag}</span>
                          <span className="font-medium">{curr.symbol}</span>
                          <span>{curr.name} ({curr.code})</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Kotani Quote */}
              {kotaniWFetchingQuote && (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-6 w-6 animate-spin text-orange-600" />
                  <span className="ml-2 text-sm text-gray-600">Getting Kotani quote...</span>
                </div>
              )}
              {kotaniWQuote && !kotaniWFetchingQuote && (
                <div className="rounded-xl bg-orange-50 border-2 border-orange-200 p-4 space-y-3">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-xs font-bold text-gray-700 uppercase tracking-wide">Live Quote · Kotani Pay</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-700">Fee ({kotaniWQuote.markup_pct}%):</span>
                    <span className="font-bold text-gray-900">-{parseFloat(kotaniWQuote.markup_crypto || 0).toFixed(6)} {getAssetSymbol(asset)}</span>
                  </div>
                  <div className="flex justify-between items-center pt-2 border-t-2 border-orange-300">
                    <span className="text-sm font-semibold text-gray-900">You Receive:</span>
                    <span className="font-bold text-xl text-green-600">{getCurrencySymbol(currency)}{parseFloat(kotaniWQuote.net_fiat || 0).toLocaleString()}</span>
                  </div>
                </div>
              )}

              {/* Mobile network */}
              {kotaniOfframpTelcos.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-sm font-semibold text-gray-900">Mobile Network</Label>
                  <Select value={kotaniWTelco} onValueChange={setKotaniWTelco}>
                    <SelectTrigger className="bg-white border-gray-300 h-12 text-gray-900">
                      <SelectValue placeholder="Select network" />
                    </SelectTrigger>
                    <SelectContent className="bg-white border-gray-300 z-50">
                      {kotaniOfframpTelcos.map(t => (
                        <SelectItem key={t.id} value={t.id} className="text-gray-900 hover:bg-gray-100 cursor-pointer">{t.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Phone number */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900">Phone Number</Label>
                <Input type="tel" placeholder="e.g., 0712345678" value={kotaniWPhone}
                  onChange={(e) => setKotaniWPhone(e.target.value)}
                  className="bg-white border-gray-300 text-gray-900 h-12"
                />
                <p className="text-xs text-gray-700 font-medium">
                  Enter number registered with {kotaniWTelco || 'mobile money'}
                </p>
              </div>

              <Alert className="bg-orange-50 border-2 border-orange-300">
                <Info className="h-5 w-5 text-orange-600" />
                <AlertDescription className="text-gray-900 text-sm font-medium">
                  <strong className="text-orange-700">Kotani Pay:</strong> Funds arrive via mobile money in 2–10 minutes.
                </AlertDescription>
              </Alert>

              {error && (
                <Alert variant="destructive" className="border-2">
                  <AlertCircle className="h-5 w-5" />
                  <AlertDescription className="font-medium">{error}</AlertDescription>
                </Alert>
              )}
            </>
          )}

          {/* ═══════════ WAPIPAY MOBILE OFFRAMP ═══════════ */}
          {withdrawProvider === 'wapipay' && (
            <>
              {/* Asset */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900 dark:text-white">Crypto Asset</Label>
                <Select value={asset} onValueChange={setAsset}>
                  <SelectTrigger className="w-full bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white h-12">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 max-h-[400px] z-50">
                    {Object.entries(ASSET_GROUPS).map(([chain, assets]) => (
                      <div key={chain} className="py-2">
                        <div className="px-3 py-2 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide bg-gray-100 dark:bg-gray-900">{CHAIN_NAMES[chain] || chain}</div>
                        {assets.map((a) => (
                          <SelectItem key={a.value} value={a.value} className="text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700 py-3 pl-8">
                            <div className="flex items-center gap-2"><span className="text-xl">{a.icon}</span><span className="font-medium">{a.label}</span></div>
                          </SelectItem>
                        ))}
                      </div>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Amount */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900 dark:text-white">Amount</Label>
                {availableBalance > 0 && (
                  <div className="flex justify-between items-center px-3 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                    <span className="text-sm text-gray-700 dark:text-gray-300">Available:</span>
                    <span className="font-bold text-blue-700 dark:text-blue-300">{availableBalance.toFixed(6)} {getAssetSymbol(asset)}</span>
                  </div>
                )}
                <div className="relative">
                  <Input type="number" step="0.01" min="0.01" placeholder="0.00" value={amount}
                    onChange={(e) => setAmount(e.target.value)} disabled={loading}
                    className="bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white h-12 text-lg font-medium pr-20"
                  />
                  <span className="absolute right-3 top-3 text-gray-600 dark:text-gray-400 font-semibold text-lg">{getAssetSymbol(asset)}</span>
                </div>
              </div>

              {/* Currency */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900 dark:text-white">Receive Currency</Label>
                <Select value={currency} onValueChange={v => { setCurrency(v); setWapiWNetwork('') }}>
                  <SelectTrigger className="w-full bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white h-12">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 z-50">
                    {WITHDRAWAL_CURRENCIES.filter(c => OFFRAMP_PROVIDER_CURRENCIES.wapipay.includes(c.code)).map(curr => (
                      <SelectItem key={curr.code} value={curr.code} className="text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">{curr.flag}</span>
                          <span className="font-medium">{curr.symbol}</span>
                          <span>{curr.name} ({curr.code})</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Mobile network */}
              {(WAPIPAY_MOBILE_NETWORKS[currency] || []).length > 0 && (
                <div className="space-y-2">
                  <Label className="text-sm font-semibold text-gray-900 dark:text-white">Mobile Network</Label>
                  <Select value={wapiWNetwork} onValueChange={setWapiWNetwork}>
                    <SelectTrigger className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 h-12 text-gray-900 dark:text-gray-100">
                      <SelectValue placeholder="Select network" />
                    </SelectTrigger>
                    <SelectContent className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 z-50">
                      {(WAPIPAY_MOBILE_NETWORKS[currency] || []).map(n => (
                        <SelectItem key={n.id} value={n.id} className="text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer">{n.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Phone */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900 dark:text-white">Phone Number</Label>
                <Input type="tel" placeholder="e.g. 0712345678" value={wapiWPhone}
                  onChange={(e) => setWapiWPhone(e.target.value)}
                  className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100 h-12"
                />
              </div>

              <Alert className="bg-cyan-50 dark:bg-cyan-900/20 border-2 border-cyan-300 dark:border-cyan-800">
                <Info className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
                <AlertDescription className="text-gray-900 dark:text-gray-100 text-sm font-medium">
                  <strong className="text-cyan-700 dark:text-cyan-300">WapiPay:</strong> Cross-border mobile money in 2–10 minutes.
                </AlertDescription>
              </Alert>

              {error && (
                <Alert variant="destructive" className="border-2">
                  <AlertCircle className="h-5 w-5" />
                  <AlertDescription className="font-medium">{error}</AlertDescription>
                </Alert>
              )}
            </>
          )}
        </div>

        <DialogFooter className="border-t pt-4">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={loading}
            className="h-12 px-6 text-base font-semibold">
            Cancel
          </Button>
          <Button
            onClick={handleWithdrawDispatch}
            disabled={isWithdrawDisabled}
            className={`h-12 px-8 text-base font-bold text-white ${
              withdrawProvider === 'busha'   ? 'bg-purple-600 hover:bg-purple-700' :
              withdrawProvider === 'kotani'  ? 'bg-orange-600 hover:bg-orange-700' :
              'bg-red-600 hover:bg-red-700'
            }`}
          >
            {withdrawButtonLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}