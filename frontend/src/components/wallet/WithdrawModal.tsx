// File: frontend/src/components/wallet/WithdrawModal.tsx
/**
 * WithdrawModal Component - Off-ramp crypto to bank
 * Converts USDT/ALGO to NGN and sends to bank account
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { apiClient } from '@/config/api'
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
import { Loader2, ArrowDownToLine, AlertCircle, CheckCircle2 } from 'lucide-react'

interface WithdrawModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function WithdrawModal({ open, onOpenChange }: WithdrawModalProps) {
  const [amount, setAmount] = useState('')
  const [asset, setAsset] = useState('USDT_ALGO')  // ✅ Use backend key
  const [currency, setCurrency] = useState('NGN')   // ✅ NEW: Fiat currency
  const [bankAccount, setBankAccount] = useState('')
  const [bankCode, setBankCode] = useState('')
  const [accountName, setAccountName] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [quote, setQuote] = useState<any>(null)
  const [fetchingQuote, setFetchingQuote] = useState(false)

  // Nigerian Banks
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

  // ========== ALL SUPPORTED ASSETS (GROUPED BY BLOCKCHAIN) ==========

const ASSET_GROUPS = {
  algorand: [
    { value: 'ALGO', label: 'Algorand (ALGO)', icon: 'Ặ', backend_key: 'ALGO' },
    { value: 'USDT', label: 'Tether (Algorand)', icon: '₮', backend_key: 'USDT_ALGO' },
    { value: 'USDCa', label: 'USD Coin (USDCa)', icon: '◎', backend_key: 'USDCa' },
    { value: 'goBTC', label: 'Wrapped Bitcoin', icon: '₿', backend_key: 'goBTC' },
    { value: 'goETH', label: 'Wrapped Ethereum', icon: 'Ξ', backend_key: 'goETH' },
  ],
  bitcoin: [
    { value: 'BTC', label: 'Bitcoin (BTC)', icon: '₿', backend_key: 'BTC' },
  ],
  ethereum: [
    { value: 'ETH', label: 'Ethereum (ETH)', icon: 'Ξ', backend_key: 'ETH' },
    { value: 'USDT_ETH', label: 'Tether (Ethereum)', icon: '₮', backend_key: 'USDT_ETH' },
    { value: 'USDC_ETH', label: 'USD Coin (Ethereum)', icon: '◎', backend_key: 'USDC_ETH' },
  ],
  polygon: [
    { value: 'MATIC', label: 'Polygon (MATIC)', icon: '▶', backend_key: 'MATIC' },
    { value: 'USDT_POLYGON', label: 'Tether (Polygon)', icon: '₮', backend_key: 'USDT_POLYGON' },
    { value: 'USDC_POLYGON', label: 'USD Coin (Polygon)', icon: '◎', backend_key: 'USDC_POLYGON' },
  ],
  tron: [
    { value: 'TRX', label: 'TRON (TRX)', icon: '⚡', backend_key: 'TRX' },
    { value: 'USDT_TRON', label: 'Tether (Tron)', icon: '₮', backend_key: 'USDT_TRON' },
  ]
}

// Flatten for easier mapping
const ALL_ASSETS = [
  ...ASSET_GROUPS.algorand,
  ...ASSET_GROUPS.bitcoin,
  ...ASSET_GROUPS.ethereum,
  ...ASSET_GROUPS.polygon,
  ...ASSET_GROUPS.tron
]

// Chain display names
const CHAIN_NAMES: { [key: string]: string } = {
  'algorand': '🟢 Algorand',
  'bitcoin': '🟠 Bitcoin',
  'ethereum': '🔵 Ethereum',
  'polygon': '🟣 Polygon',
  'tron': '🔴 Tron'
}

// ========== SUPPORTED WITHDRAWAL CURRENCIES ==========

const WITHDRAWAL_CURRENCIES = [
  { code: 'NGN', name: 'Nigerian Naira', symbol: '₦', flag: '🇳🇬', methods: ['bank_transfer'] },
  { code: 'KES', name: 'Kenyan Shilling', symbol: 'KSh', flag: '🇰🇪', methods: ['mobile_money', 'bank_transfer'] },
  { code: 'GHS', name: 'Ghanaian Cedi', symbol: 'GH₵', flag: '🇬🇭', methods: ['mobile_money', 'bank_transfer'] },
  { code: 'ZAR', name: 'South African Rand', symbol: 'R', flag: '🇿🇦', methods: ['bank_transfer'] },
  { code: 'UGX', name: 'Ugandan Shilling', symbol: 'USh', flag: '🇺🇬', methods: ['mobile_money'] },
  { code: 'TZS', name: 'Tanzanian Shilling', symbol: 'TSh', flag: '🇹🇿', methods: ['mobile_money'] },
]

  // Verify bank account
  const verifyBankAccount = async () => {
    if (!bankAccount || !bankCode || bankAccount.length !== 10) {
      toast.error('Please enter a valid 10-digit account number')
      return
    }

    setVerifying(true)
    setError(null)
    setAccountName(null)

    try {
      const response = await apiClient.post('/api/v1/offramp/verify-account', {
        account_number: bankAccount,
        bank_code: bankCode,
      })

      setAccountName(response.data.account_name)
      toast.success(`Account verified: ${response.data.account_name}`)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to verify account'
      setError(errorMsg)
      toast.error(errorMsg)
    } finally {
      setVerifying(false)
    }
  }

  // ✅ REAL-TIME QUOTE FETCHING (NO HARDCODED RATES!)
  const fetchQuote = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      setQuote(null)
      return
    }

    setFetchingQuote(true)
    setError(null)

    try {
      const response = await apiClient.post('/api/v1/offramp/quote', {
        crypto_amount: parseFloat(amount),
        crypto_asset: asset,
        fiat_currency: currency,
      })

      if (response.data?.success) {
        setQuote(response.data.quote)
        logger.info('✅ Offramp quote fetched:', response.data.quote)
      } else {
        setError(response.data?.error || 'Failed to get quote')
      }
    } catch (err: any) {
      console.error('Quote fetch error:', err)
      const errorMsg = err.response?.data?.detail || 'Failed to get live quote'
      setError(errorMsg)
      setQuote(null)
    } finally {
      setFetchingQuote(false)
    }

    // Auto-fetch quote when amount/asset/currency changes
    useEffect(() => {
      const timer = setTimeout(() => {
        if (amount && parseFloat(amount) > 0 && asset && currency) {
          fetchQuote()
        }
      }, 500) // Debounce 500ms

      return () => clearTimeout(timer)
    }, [amount, asset, currency])

    try {
      const response = await apiClient.post('/api/v1/offramp/quote', {
        amount: parseFloat(amount),
        asset,
      })

      setQuote(response.data)
      setError(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to get quote')
      setQuote(null)
    }
  }

  // Handle withdrawal
  const handleWithdraw = async () => {
    if (!accountName) {
      toast.error('Please verify your bank account first')
      return
    }

    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.post('/api/v1/offramp/withdraw', {
        amount: parseFloat(amount),
        asset,
        bank_code: bankCode,
        account_number: bankAccount,
      })

      toast.success('Withdrawal initiated! Funds will arrive in 1-2 hours')
      
      // Reset form
      setAmount('')
      setBankAccount('')
      setBankCode('')
      setAccountName(null)
      setQuote(null)
      
      onOpenChange(false)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Withdrawal failed'
      setError(errorMsg)
      toast.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const getCurrencySymbol = (code: string) => {
    return WITHDRAWAL_CURRENCIES.find(c => c.code === code)?.symbol || code
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-w-[95vw] max-h-[85vh] overflow-y-auto bg-white dark:bg-white border-2 border-gray-300">
        <DialogHeader className="border-b pb-4">
          <DialogTitle className="flex items-center gap-2 text-xl font-bold text-gray-900">
            <ArrowDownToLine className="h-6 w-6 text-red-600" />
            Withdraw to Bank
          </DialogTitle>
          <DialogDescription className="text-base text-gray-600 mt-2">
            Convert crypto to NGN and send to your bank account
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Asset Selection */}
          <div className="space-y-2">
            <Label htmlFor="withdraw-asset" className="text-sm font-semibold text-gray-900">Asset to Withdraw</Label>
            <Select value={asset} onValueChange={setAsset}>
              <SelectTrigger id="withdraw-asset" className="w-full bg-gray-50 border-gray-300 text-gray-900 h-11">
                <SelectValue placeholder="Select crypto to withdraw" />
              </SelectTrigger>
              <SelectContent className="bg-white border-gray-300 max-h-[400px]">
                {Object.entries(ASSET_GROUPS).map(([chain, assets]) => (
                  <div key={chain} className="py-2">
                    {/* Chain Header */}
                    <div className="px-3 py-2 text-xs font-bold text-gray-500 uppercase tracking-wide bg-gray-100">
                      {CHAIN_NAMES[chain] || chain}
                    </div>
                    
                    {/* Assets in this chain */}
                    {assets.map((a) => (
                      <SelectItem 
                        key={a.backend_key} 
                        value={a.backend_key}
                        className="text-gray-900 hover:bg-gray-100 py-3 pl-8"
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
            {/* Currency Selection - NEW! */}
            <div className="space-y-2">
              <Label htmlFor="withdraw-currency" className="text-sm font-semibold text-gray-900">
                Withdraw To Currency
              </Label>
              <Select value={currency} onValueChange={setCurrency}>
                <SelectTrigger id="withdraw-currency" className="w-full bg-gray-50 border-gray-300 text-gray-900 h-11">
                  <SelectValue placeholder="Select currency" />
                </SelectTrigger>
                <SelectContent className="bg-white border-gray-300 max-h-[300px]">
                  {WITHDRAWAL_CURRENCIES.map((curr) => (
                    <SelectItem 
                      key={curr.code} 
                      value={curr.code}
                      className="text-gray-900 hover:bg-gray-100 py-3"
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
          </div>

          {/* Amount */}
          <div className="space-y-2">
            <Label htmlFor="withdraw-amount" className="text-sm font-semibold text-gray-900">Amount</Label>
            <Input
              id="withdraw-amount"
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              onBlur={fetchQuote}
              disabled={loading}
              className="bg-gray-50 border-gray-300 text-gray-900 h-11 text-base"
            />
          </div>

          {/* Quote Display - LIVE DATA! */}
          {fetchingQuote && (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
              <span className="ml-2 text-sm text-gray-600">Fetching live quote...</span>
            </div>
          )}

          {quote && !fetchingQuote && (
            <div className="rounded-lg bg-red-50 border-2 border-red-200 p-4 space-y-2">
              <div className="flex items-center gap-2 mb-3">
                <Activity className="h-5 w-5 text-green-500 animate-pulse" />
                <span className="text-xs font-bold text-gray-700 uppercase">Live Quote</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">Crypto Value:</span>
                <span className="font-bold text-base text-gray-900">
                  ${quote.crypto_value_usd?.toFixed(2)} USD
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">Exchange Rate:</span>
                <span className="font-bold text-base text-gray-900">
                  1 USD = {getCurrencySymbol(currency)}{quote.exchange_rate?.toFixed(2)}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">Gross Amount:</span>
                <span className="font-bold text-base text-gray-900">
                  {getCurrencySymbol(currency)}{quote.gross_fiat_amount?.toLocaleString()}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">Withdrawal Fee (1.8%):</span>
                <span className="font-bold text-base text-gray-900">
                  {getCurrencySymbol(currency)}{quote.withdrawal_fee?.toFixed(2)}
                </span>
              </div>
              
              <div className="flex justify-between items-center pt-2 border-t-2 border-red-300">
                <span className="text-sm font-semibold text-gray-900">You Receive:</span>
                <span className="font-bold text-xl text-green-600">
                  {getCurrencySymbol(currency)}{quote.net_fiat_amount?.toLocaleString()}
                </span>
              </div>
              
              <div className="text-xs text-gray-600 mt-2 flex items-center gap-1">
                <span>📊 Price: {quote.price_source}</span>
                <span>•</span>
                <span>💱 Forex: {quote.forex_source}</span>
              </div>
            </div>
          )}

          {/* Bank Selection */}
          <div className="space-y-2">
            <Label htmlFor="bank" className="text-sm font-semibold text-gray-900">Bank</Label>
            <Select value={bankCode} onValueChange={setBankCode}>
              <SelectTrigger id="bank" className="w-full bg-gray-50 border-gray-300 text-gray-900 h-11">
                <SelectValue placeholder="Select bank" />
              </SelectTrigger>
              <SelectContent className="max-h-[200px] bg-white border-gray-300">
                {NIGERIAN_BANKS.map((bank) => (
                  <SelectItem key={bank.code} value={bank.code} className="text-gray-900 hover:bg-gray-100">
                    {bank.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Account Number */}
          <div className="space-y-2">
            <Label htmlFor="account" className="text-sm font-semibold text-gray-900">Account Number</Label>
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
                className="flex-1 bg-gray-50 border-gray-300 text-gray-900 h-11 text-base"
              />
              <Button
                type="button"
                variant="outline"
                onClick={verifyBankAccount}
                disabled={!bankAccount || !bankCode || verifying || loading}
                className="shrink-0 h-11 border-2 border-gray-300 text-gray-700 hover:bg-gray-100 font-semibold"
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
            <Alert className="bg-green-50 border-2 border-green-300">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <AlertDescription className="text-green-900 font-bold text-base">
                {accountName}
              </AlertDescription>
            </Alert>
          )}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive" className="bg-red-50 border-2 border-red-300">
              <AlertCircle className="h-5 w-5 text-red-600" />
              <AlertDescription className="text-red-900 font-medium">{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-3 pt-4 border-t">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
            className="w-full sm:w-auto h-11 text-base font-semibold border-2 border-gray-300 text-gray-700 hover:bg-gray-100"
          >
            Cancel
          </Button>
          <Button
            onClick={handleWithdraw}
            disabled={loading || !accountName || !amount || parseFloat(amount) <= 0}
            className="w-full sm:w-auto h-11 text-base font-semibold bg-red-600 hover:bg-red-700 text-white"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <ArrowDownToLine className="mr-2 h-5 w-5" />
                Withdraw ₦{quote?.final_amount?.toLocaleString() || '0'}
              </>
            )}
          </Button>
        </DialogFooter>

        <p className="text-sm text-gray-600 text-center px-2 pb-2 font-medium">
          Withdrawals typically arrive within 1-2 hours. A 1.8% fee applies.
        </p>
      </DialogContent>
    </Dialog>
  )
}