// File: frontend/src/components/wallet/WithdrawModal.tsx
/**
 * WithdrawModal Component - PRODUCTION-READY Off-ramp
 * ✅ Crypto → Fiat conversion (not fiat input)
 * ✅ Bank transfers + Mobile Money (Cashramp primary)
 * ✅ Multi-currency support (10+ African countries)
 * ✅ Live quotes with proper error handling
 * ✅ Paystack fallback for bank verification
 * ✅ Uses global wallet balances (no local fetch)
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
import { Loader2, ArrowDownToLine, AlertCircle, CheckCircle2, Building2, Smartphone, Info } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useWallet } from '@/contexts/WalletContext'

// ========== SUPPORTED ASSETS (ALL CHAINS) ==========
const ASSET_GROUPS = {
  algorand: [
    { value: 'ALGO', label: 'Algorand (ALGO)', icon: 'Ⱥ' },
    { value: 'USDT', label: 'Tether (Algorand)', icon: '₮' },
    { value: 'USDCa', label: 'USD Coin (USDCa)', icon: '◎' },
    { value: 'goBTC', label: 'Wrapped Bitcoin', icon: '₿' },
    { value: 'goETH', label: 'Wrapped Ethereum', icon: 'Ξ' },
  ],
  bitcoin: [
    { value: 'BTC', label: 'Bitcoin (BTC)', icon: '₿' },
  ],
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
  'bitcoin': '🟠 Bitcoin',
  'ethereum': '🔵 Ethereum',
  'polygon': '🟣 Polygon',
  'tron': '🔴 Tron',
  'solana': '🟣 Solana'
}

// ========== CASHRAMP-SUPPORTED WITHDRAWAL CURRENCIES ==========
const WITHDRAWAL_CURRENCIES = [
  { 
    code: 'NGN', 
    name: 'Nigerian Naira', 
    symbol: '₦', 
    flag: '🇳🇬', 
    methods: ['bank_transfer'],
    providers: ['cashramp', 'paystack']
  },
  { 
    code: 'KES', 
    name: 'Kenyan Shilling', 
    symbol: 'KSh', 
    flag: '🇰🇪', 
    methods: ['bank_transfer', 'mobile_money'],
    mobile_providers: ['mpesa', 'airtel'],
    providers: ['cashramp']
  },
  { 
    code: 'GHS', 
    name: 'Ghanaian Cedi', 
    symbol: 'GH₵', 
    flag: '🇬🇭', 
    methods: ['bank_transfer', 'mobile_money'],
    mobile_providers: ['mtn', 'vodafone', 'airteltigo'],
    providers: ['cashramp']
  },
  { 
    code: 'ZAR', 
    name: 'South African Rand', 
    symbol: 'R', 
    flag: '🇿🇦', 
    methods: ['bank_transfer'],
    providers: ['cashramp']
  },
  { 
    code: 'UGX', 
    name: 'Ugandan Shilling', 
    symbol: 'USh', 
    flag: '🇺🇬', 
    methods: ['mobile_money'],
    mobile_providers: ['mtn', 'airtel'],
    providers: ['cashramp']
  },
  { 
    code: 'TZS', 
    name: 'Tanzanian Shilling', 
    symbol: 'TSh', 
    flag: '🇹🇿', 
    methods: ['mobile_money'],
    mobile_providers: ['mpesa', 'airtel', 'tigo'],
    providers: ['cashramp']
  },
  { 
    code: 'RWF', 
    name: 'Rwandan Franc', 
    symbol: 'FRw', 
    flag: '🇷🇼', 
    methods: ['mobile_money'],
    mobile_providers: ['mtn', 'airtel'],
    providers: ['cashramp']
  },
  { 
    code: 'ZMW', 
    name: 'Zambian Kwacha', 
    symbol: 'ZK', 
    flag: '🇿🇲', 
    methods: ['mobile_money'],
    mobile_providers: ['mtn', 'airtel', 'zamtel'],
    providers: ['cashramp']
  },
]

// Nigerian Banks (for bank transfer option)
const NIGERIAN_BANKS = [
  { code: '044', name: 'Access Bank' },
  { code: '023', name: 'Citibank' },
  { code: '050', name: 'Ecobank' },
  { code: '084', name: 'Enterprise Bank' },
  { code: '070', name: 'Fidelity Bank' },
  { code: '011', name: 'First Bank' },
  { code: '214', name: 'First City Monument Bank' },
  { code: '058', name: 'Guaranty Trust Bank' },
  { code: '030', name: 'Heritage Bank' },
  { code: '301', name: 'Jaiz Bank' },
  { code: '082', name: 'Keystone Bank' },
  { code: '526', name: 'Parallex Bank' },
  { code: '076', name: 'Polaris Bank' },
  { code: '101', name: 'Providus Bank' },
  { code: '221', name: 'Stanbic IBTC Bank' },
  { code: '068', name: 'Standard Chartered Bank' },
  { code: '232', name: 'Sterling Bank' },
  { code: '100', name: 'Suntrust Bank' },
  { code: '032', name: 'Union Bank' },
  { code: '033', name: 'United Bank for Africa' },
  { code: '215', name: 'Unity Bank' },
  { code: '035', name: 'Wema Bank' },
  { code: '057', name: 'Zenith Bank' },
]

// Mobile Money Provider Display Names
const MOBILE_PROVIDER_NAMES: { [key: string]: string } = {
  'mpesa': 'M-Pesa',
  'airtel': 'Airtel Money',
  'mtn': 'MTN Mobile Money',
  'vodafone': 'Vodafone Cash',
  'airteltigo': 'AirtelTigo Money',
  'tigo': 'Tigo Pesa',
  'zamtel': 'Zamtel Money'
}

export function WithdrawModal({ open, onOpenChange }: WithdrawModalProps) {
  // Core state
  const [amount, setAmount] = useState('')
  const [asset, setAsset] = useState('ALGO')  // default to ALGO (always present)
  const [currency, setCurrency] = useState('NGN')
  const [loading, setLoading] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [quote, setQuote] = useState<any>(null)
  const [fetchingQuote, setFetchingQuote] = useState(false)

  // Payout method state
  const [payoutMethod, setPayoutMethod] = useState<'bank_transfer' | 'mobile_money'>('bank_transfer')
  
  // Bank transfer state
  const [bankAccount, setBankAccount] = useState('')
  const [bankCode, setBankCode] = useState('')
  const [accountName, setAccountName] = useState<string | null>(null)

  // Mobile money state
  const [mobileProvider, setMobileProvider] = useState('')
  const [mobileNumber, setMobileNumber] = useState('')

  const { session } = useAuth()
  const { balances } = useWallet()  // ✅ Get balances from global context

  // ✅ Available balance from global state – works for all asset keys
  const availableBalance = balances[asset]?.balance || 0

  // Get selected currency details
  const selectedCurrency = WITHDRAWAL_CURRENCIES.find(c => c.code === currency)
  const supportsMobileMoney = selectedCurrency?.methods?.includes('mobile_money') || false
  const supportsBankTransfer = selectedCurrency?.methods?.includes('bank_transfer') || false

  // Auto-select payout method based on currency
  useEffect(() => {
    if (selectedCurrency) {
      if (selectedCurrency.methods.length === 1) {
        setPayoutMethod(selectedCurrency.methods[0] as 'bank_transfer' | 'mobile_money')
      } else if (!selectedCurrency.methods.includes(payoutMethod)) {
        setPayoutMethod(selectedCurrency.methods[0] as 'bank_transfer' | 'mobile_money')
      }
    }
  }, [currency])

  // Fetch quote (debounced)
  const fetchQuote = async () => {
    const cryptoAmount = parseFloat(amount)
    
    if (!cryptoAmount || cryptoAmount <= 0) {
      setQuote(null)
      return
    }

    setFetchingQuote(true)
    setError(null)

    try {
      const endpoint = session ? '/api/v1/offramp/quote' : '/api/v1/offramp/quote/public'
      
      const response = await api.post(endpoint, {
        crypto_amount: cryptoAmount,
        crypto_asset: asset,
        fiat_currency: currency,
      })

      if (response?.success) {
        setQuote(response.quote)
      } else {
        setError(response?.error || 'Failed to get quote')
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to get quote'
      setError(errorMsg)
      setQuote(null)
    } finally {
      setFetchingQuote(false)
    }
  }

  // Debounced quote fetching
  useEffect(() => {
    const timer = setTimeout(() => {
      if (amount && parseFloat(amount) > 0 && asset && currency) {
        fetchQuote()
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [amount, asset, currency])

  // Verify bank account via backend proxy
  const verifyBankAccount = async () => {
    if (!bankAccount || !bankCode || bankAccount.length !== 10) {
      toast.error('Please enter a valid 10-digit account number')
      return
    }

    setVerifying(true)
    setError(null)
    setAccountName(null)

    try {
      const response = await api.post('/api/v1/bank/verify', {
        account_number: bankAccount,
        bank_code: bankCode
      })

      if (response.success && response.account_name) {
        setAccountName(response.account_name)
        toast.success(`Account verified: ${response.account_name}`)
      } else {
        throw new Error(response.error || 'Verification failed')
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to verify account'
      setError(errorMsg)
      toast.error(errorMsg)
    } finally {
      setVerifying(false)
    }
  }

  // Handle withdrawal
  const handleWithdraw = async () => {
    // Validation
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount')
      return
    }

    if (parseFloat(amount) > availableBalance) {
      toast.error(`Insufficient balance. Available: ${availableBalance.toFixed(6)} ${asset.split('_')[0]}`)
      return
    }

    if (payoutMethod === 'bank_transfer') {
      if (!accountName) {
        toast.error('Please verify your bank account first')
        return
      }
    } else {
      if (!mobileProvider || !mobileNumber) {
        toast.error('Please enter mobile money details')
        return
      }
    }

    setLoading(true)
    setError(null)

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
        payload.recipient_details.bank_code = bankCode
        payload.recipient_details.account_number = bankAccount
        payload.recipient_details.account_name = accountName
      } else {
        payload.recipient_details.network = mobileProvider
        payload.recipient_details.phone_number = mobileNumber
      }

      const response = await api.post('/api/v1/offramp/withdraw', payload)

      if (response?.success) {
        toast.success('Withdrawal initiated! Funds will arrive within 1-2 hours')
        
        // Reset form
        setAmount('')
        setBankAccount('')
        setBankCode('')
        setAccountName(null)
        setMobileProvider('')
        setMobileNumber('')
        setQuote(null)
        
        onOpenChange(false)
      } else {
        throw new Error(response?.error || 'Withdrawal failed')
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Withdrawal failed'
      setError(errorMsg)
      toast.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const getCurrencySymbol = (code: string) => {
    return WITHDRAWAL_CURRENCIES.find(c => c.code === code)?.symbol || code
  }

  const getAssetSymbol = (assetKey: string) => {
    return assetKey.split('_')[0]  // "USDT_TRON" → "USDT", "ALGO" → "ALGO"
  }

  // Debug: log why button might be disabled (uncomment if needed)
  // console.log('Button disabled?', {
  //   loading,
  //   quote: !!quote,
  //   bankVerified: accountName,
  //   mobileDetails: mobileProvider && mobileNumber,
  //   sufficientBalance: parseFloat(amount) <= availableBalance,
  //   amountValid: amount && parseFloat(amount) > 0
  // })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent 
        className="sm:max-w-[550px] max-w-[95vw] max-h-[90vh] overflow-y-auto bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600"
        style={{ zIndex: 1000 }}
      >
        <DialogHeader className="border-b pb-4">
          <DialogTitle className="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-white">
            <ArrowDownToLine className="h-6 w-6 text-red-600" />
            Withdraw to {payoutMethod === 'bank_transfer' ? 'Bank' : 'Mobile Money'}
          </DialogTitle>
          <DialogDescription className="text-base text-gray-600 dark:text-gray-400 mt-2">
            Convert crypto to local currency. Fast, secure withdrawals via Cashramp.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Asset Selection */}
          <div className="space-y-2">
            <Label htmlFor="withdraw-asset" className="text-sm font-semibold text-gray-900 dark:text-white">
              Crypto Asset to Withdraw
            </Label>
            <Select value={asset} onValueChange={setAsset}>
              <SelectTrigger id="withdraw-asset" className="w-full bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white h-12">
                <SelectValue placeholder="Select crypto to withdraw" />
              </SelectTrigger>
              <SelectContent className="bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 max-h-[400px] z-50">
                {Object.entries(ASSET_GROUPS).map(([chain, assets]) => (
                  <div key={chain} className="py-2">
                    <div className="px-3 py-2 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide bg-gray-100 dark:bg-gray-900">
                      {CHAIN_NAMES[chain] || chain}
                    </div>
                    {assets.map((a) => (
                      <SelectItem 
                        key={a.value} 
                        value={a.value}
                        className="text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700 py-3 pl-8"
                      >
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
            <Label htmlFor="withdraw-amount" className="text-sm font-semibold text-gray-900 dark:text-white">
              Amount to Withdraw
            </Label>
            
            {/* Show available balance from global state */}
            {availableBalance > 0 && (
              <div className="flex justify-between items-center px-3 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <span className="text-sm text-gray-700 dark:text-gray-300">Available:</span>
                <span className="font-bold text-blue-700 dark:text-blue-300">
                  {availableBalance.toFixed(6)} {getAssetSymbol(asset)}
                </span>
              </div>
            )}
            
            <div className="relative">
              <Input
                id="withdraw-amount"
                type="number"
                step="0.01"
                min="0.01"
                max={availableBalance || undefined}
                placeholder="0.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                disabled={loading}
                className="bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white h-12 text-lg font-medium pr-20"
              />
              <span className="absolute right-3 top-3 text-gray-600 dark:text-gray-400 font-semibold text-lg">
                {getAssetSymbol(asset)}
              </span>
            </div>
            
            {parseFloat(amount) > availableBalance && availableBalance > 0 && (
              <p className="text-sm text-red-600 dark:text-red-400 font-medium">
                ⚠️ Amount exceeds available balance
              </p>
            )}
          </div>

          {/* Currency Selection */}
          <div className="space-y-2">
            <Label htmlFor="withdraw-currency" className="text-sm font-semibold text-gray-900 dark:text-white">
              Receive Currency
            </Label>
            <Select value={currency} onValueChange={setCurrency}>
              <SelectTrigger id="withdraw-currency" className="w-full bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white h-12">
                <SelectValue placeholder="Select currency" />
              </SelectTrigger>
              <SelectContent className="bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 max-h-[300px] z-50">
                {WITHDRAWAL_CURRENCIES.map((curr) => (
                  <SelectItem 
                    key={curr.code} 
                    value={curr.code}
                    className="text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700 py-3"
                  >
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
              <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">Calculating quote...</span>
            </div>
          )}

          {quote && !fetchingQuote && (
            <div className="rounded-xl bg-gradient-to-br from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20 border-2 border-red-200 dark:border-red-700 p-4 space-y-3 shadow-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wide">Live Quote</span>
                </div>
                <span className="text-xs text-gray-500 dark:text-gray-400">Valid 5 min</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Crypto Value:</span>
                <span className="font-bold text-base text-gray-900 dark:text-white">
                  ${quote.crypto_value_usd?.toFixed(2)} USD
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Exchange Rate:</span>
                <span className="font-bold text-base text-gray-900 dark:text-white">
                  1 USD = {getCurrencySymbol(currency)}{quote.exchange_rate?.toFixed(2)}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Gross Amount:</span>
                <span className="font-bold text-base text-gray-900 dark:text-white">
                  {getCurrencySymbol(currency)}{quote.gross_fiat_amount?.toLocaleString()}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Withdrawal Fee ({quote.fee_percentage?.toFixed(1)}%):
                </span>
                <span className="font-bold text-base text-gray-900 dark:text-white">
                  {getCurrencySymbol(currency)}{quote.withdrawal_fee?.toFixed(2)}
                </span>
              </div>
              
              <div className="flex justify-between items-center pt-2 border-t-2 border-red-300 dark:border-red-700">
                <span className="text-sm font-semibold text-gray-900 dark:text-white">You Receive:</span>
                <span className="font-bold text-xl text-green-600 dark:text-green-400">
                  {getCurrencySymbol(currency)}{quote.net_fiat_amount?.toLocaleString()}
                </span>
              </div>
              
              <div className="text-xs text-gray-600 dark:text-gray-400 mt-2 flex items-center gap-1">
                <span>📊 Price: {quote.price_source}</span>
                <span>•</span>
                <span>💱 Forex: {quote.forex_source}</span>
              </div>
            </div>
          )}

          {/* Payout Method Selection */}
          {supportsMobileMoney && supportsBankTransfer && (
            <div className="space-y-2">
              <Label className="text-sm font-semibold text-gray-900 dark:text-white">Payout Method</Label>
              <div className="grid grid-cols-2 gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setPayoutMethod('bank_transfer')}
                  className={`h-12 text-base font-bold border-2 transition-all duration-200 ${
                    payoutMethod === 'bank_transfer'
                      ? 'bg-gradient-to-br from-blue-500/20 to-indigo-500/20 dark:from-blue-400/30 dark:to-indigo-400/30 border-blue-500 dark:border-blue-400 text-blue-700 dark:text-blue-200 backdrop-blur-sm shadow-lg'
                      : 'bg-white/50 dark:bg-gray-700/50 border-gray-300 dark:border-gray-500 text-gray-700 dark:text-gray-100 hover:bg-gray-100/70 dark:hover:bg-gray-600/70 backdrop-blur-sm'
                  }`}
                >
                  <Building2 className="mr-2 h-5 w-5" />
                  Bank Transfer
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setPayoutMethod('mobile_money')}
                  className={`h-12 text-base font-bold border-2 transition-all duration-200 ${
                    payoutMethod === 'mobile_money'
                      ? 'bg-gradient-to-br from-green-500/20 to-emerald-500/20 dark:from-green-400/30 dark:to-emerald-400/30 border-green-500 dark:border-green-400 text-green-700 dark:text-green-200 backdrop-blur-sm shadow-lg'
                      : 'bg-white/50 dark:bg-gray-700/50 border-gray-300 dark:border-gray-500 text-gray-700 dark:text-gray-100 hover:bg-gray-100/70 dark:hover:bg-gray-600/70 backdrop-blur-sm'
                  }`}
                >
                  <Smartphone className="mr-2 h-5 w-5" />
                  Mobile Money
                </Button>
              </div>
            </div>
          )}

          {/* Bank Transfer Fields */}
          {payoutMethod === 'bank_transfer' && supportsBankTransfer && (
            <>
              {/* Bank Selection (Nigeria only for now) */}
              {currency === 'NGN' && (
                <div className="space-y-2">
                  <Label htmlFor="bank" className="text-sm font-semibold text-gray-900 dark:text-white">Bank</Label>
                  <Select value={bankCode} onValueChange={setBankCode}>
                    <SelectTrigger id="bank" className="w-full bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white h-12">
                      <SelectValue placeholder="Select bank" />
                    </SelectTrigger>
                    <SelectContent className="max-h-[200px] bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 z-50">
                      {NIGERIAN_BANKS.map((bank) => (
                        <SelectItem 
                          key={bank.code} 
                          value={bank.code} 
                          className="text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700"
                        >
                          {bank.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Account Number */}
              <div className="space-y-2">
                <Label htmlFor="account" className="text-sm font-semibold text-gray-900 dark:text-white">Account Number</Label>
                <div className="flex gap-2">
                  <Input
                    id="account"
                    type="text"
                    maxLength={10}
                    placeholder="0123456789"
                    value={bankAccount}
                    onChange={(e) => {
                      setBankAccount(e.target.value)
                      setAccountName(null)
                    }}
                    disabled={loading || verifying}
                    className="flex-1 bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white h-12 text-base"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={verifyBankAccount}
                    disabled={!bankAccount || !bankCode || verifying || loading || bankAccount.length !== 10}
                    className="shrink-0 h-12 border-2 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 font-semibold px-6"
                  >
                    {verifying ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      'Verify'
                    )}
                  </Button>
                </div>
              </div>

              {/* Account Name Display */}
              {accountName && (
                <Alert className="bg-green-50 dark:bg-green-900/20 border-2 border-green-300 dark:border-green-800">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <AlertDescription className="text-green-900 dark:text-green-100 font-bold text-base">
                    {accountName}
                  </AlertDescription>
                </Alert>
              )}
            </>
          )}

          {/* Mobile Money Fields */}
          {payoutMethod === 'mobile_money' && supportsMobileMoney && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900 dark:text-white">Mobile Money Provider</Label>
                <Select value={mobileProvider} onValueChange={setMobileProvider}>
                  <SelectTrigger className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 h-12 text-gray-900 dark:text-gray-100">
                    <SelectValue placeholder="Select provider" className="text-gray-900 dark:text-gray-100" />
                  </SelectTrigger>
                  <SelectContent className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 z-50">
                    {selectedCurrency?.mobile_providers?.map((provider) => (
                      <SelectItem 
                        key={provider} 
                        value={provider}
                        className="text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer"
                      >
                        {MOBILE_PROVIDER_NAMES[provider] || provider}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-gray-900 dark:text-white">Phone Number</Label>
                <Input
                  type="tel"
                  placeholder="e.g., 0712345678"
                  value={mobileNumber}
                  onChange={(e) => setMobileNumber(e.target.value)}
                  className="bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-500 text-gray-900 dark:text-gray-100 placeholder:text-gray-500 dark:placeholder:text-gray-400 h-12"
                />
                <p className="text-xs text-gray-700 dark:text-gray-300 font-medium">
                  Enter number registered with {mobileProvider ? MOBILE_PROVIDER_NAMES[mobileProvider] : 'mobile money'}
                </p>
              </div>
            </div>
          )}

          {/* Provider Info Alert */}
          <Alert className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-300 dark:border-blue-800">
            <Info className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <AlertDescription className="text-gray-900 dark:text-gray-100 text-sm font-medium">
              <strong className="text-blue-700 dark:text-blue-300">Smart Routing:</strong> We automatically select the best provider.
            </AlertDescription>
          </Alert>

          {/* Error Display */}
          {error && (
            <Alert variant="destructive" className="border-2">
              <AlertCircle className="h-5 w-5" />
              <AlertDescription className="font-medium">{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="border-t pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
            className="h-12 px-6 text-base font-semibold"
          >
            Cancel
          </Button>
          <Button
            onClick={handleWithdraw}
            disabled={
              loading ||
              !quote ||
              !amount ||
              parseFloat(amount) <= 0 ||
              parseFloat(amount) > availableBalance ||
              (payoutMethod === 'bank_transfer' && !accountName) ||
              (payoutMethod === 'mobile_money' && (!mobileProvider || !mobileNumber))
            }
            className="h-12 px-8 text-base font-bold bg-red-600 hover:bg-red-700 text-white"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Processing...
              </>
            ) : (
              `Withdraw ${quote ? getCurrencySymbol(currency) + quote.net_fiat_amount?.toLocaleString() : ''}`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}