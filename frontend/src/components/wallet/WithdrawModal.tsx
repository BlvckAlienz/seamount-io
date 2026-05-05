// File: frontend/src/components/wallet/WithdrawModal.tsx
import { useState } from 'react'
import { toast } from 'sonner'
import { loadMoonPay } from '@moonpay/moonpay-js'
import { api } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import { useWallet } from '@/contexts/WalletContext'
import { Button } from '@/components/ui/button.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx'
import { Label } from '@/components/ui/label.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import {
  Dialog, DialogContent, DialogDescription,
  DialogHeader, DialogTitle,
} from '@/components/ui/dialog.tsx'
import { Loader2, ArrowDownToLine, Info, AlertCircle, ShieldCheck } from 'lucide-react'

interface WithdrawModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const OFFRAMP_ASSET_GROUPS = {
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

const FIAT_OPTIONS = [
  { code: 'USD', flag: '🇺🇸' }, { code: 'EUR', flag: '🇪🇺' }, { code: 'GBP', flag: '🇬🇧' },
  { code: 'NGN', flag: '🇳🇬' }, { code: 'KES', flag: '🇰🇪' }, { code: 'GHS', flag: '🇬🇭' },
  { code: 'ZAR', flag: '🇿🇦' },
]

export function WithdrawModal({ open, onOpenChange }: WithdrawModalProps) {
  const [asset, setAsset]           = useState('USDT_TRON')
  const [fiatCurrency, setFiatCurrency] = useState('USD')
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState<string | null>(null)

  const { session }  = useAuth()
  const { balances } = useWallet()

  const assetSymbol      = asset.split('_')[0]
  const availableBalance = balances?.[asset]?.balance ?? 0
  const hasAlgoBalance   = (balances?.['ALGO']?.balance ?? 0) > 0

  const handleSell = async () => {
    if (!session) { toast.error('Sign in to sell crypto'); return }
    if (availableBalance <= 0) {
      toast.error(`No ${assetSymbol} balance to sell`)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await api.post('/api/v1/moonpay/url/offramp', {
        asset,
        quote_currency_code: fiatCurrency,
      })
      if (!res?.success) throw new Error(res?.detail || 'Failed to initialize withdrawal')

      const moonPayFactory = await loadMoonPay()
      const sdk = moonPayFactory({
        flow: 'sell', environment: 'production', variant: 'overlay',
        params: res.params,
      })
      sdk.on('transactionCompleted', () => {
        toast.success('✅ Withdrawal initiated! Bank settlement varies by country.')
        onOpenChange(false)
      })
      sdk.show()
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Withdrawal failed'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

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
              Sell crypto and receive fiat to your bank or card globally.
            </DialogDescription>
          </DialogHeader>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">

          {/* Asset */}
          <div className="space-y-1.5">
            <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Select Asset to Sell
            </Label>
            <Select value={asset} onValueChange={setAsset}>
              <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="max-h-72 rounded-xl bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                {Object.entries(OFFRAMP_ASSET_GROUPS).map(([chain, assets]) => (
                  <div key={chain}>
                    <div className="px-3 py-1.5 text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest bg-gray-50 dark:bg-gray-900">
                      {chain}
                    </div>
                    {assets.map(a => (
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
            {availableBalance > 0 && (
              <div className="flex justify-between items-center px-3 py-2 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-100 dark:border-green-800">
                <span className="text-xs text-gray-500 dark:text-gray-400">Available</span>
                <span className="text-sm font-bold text-green-700 dark:text-green-400">
                  {availableBalance.toFixed(6)} {assetSymbol}
                </span>
              </div>
            )}

            {availableBalance <= 0 && (
              <div className="flex justify-between items-center px-3 py-2 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-800">
                <span className="text-xs text-amber-700 dark:text-amber-400">
                  No {assetSymbol} balance. Fund your wallet first.
                </span>
              </div>
            )}

            {asset === 'MATIC' && (
              <p className="text-xs text-purple-600 dark:text-purple-400">
                ℹ️ MoonPay withdraws MATIC from your Polygon address.
              </p>
            )}

            {hasAlgoBalance && (
              <p className="text-xs text-amber-600 dark:text-amber-400">
                ⚠️ ALGO cannot be sold via MoonPay — swap to USDT first.
              </p>
            )}
          </div>

          {/* Receive Currency */}
          <div className="space-y-1.5">
            <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Receive In
            </Label>
            <Select value={fiatCurrency} onValueChange={setFiatCurrency}>
              <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="rounded-xl bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                {FIAT_OPTIONS.map(c => (
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

          {/* Info */}
          <Alert className="border border-red-100 dark:border-red-900 bg-red-50 dark:bg-red-900/20 rounded-xl py-3">
            <Info className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
            <AlertDescription className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
              Powered by <strong className="text-red-600 dark:text-red-400">MoonPay</strong> —
              they collect your crypto from your wallet and transfer fiat to your bank.
            </AlertDescription>
          </Alert>

          {error && (
            <Alert variant="destructive" className="rounded-xl border py-3">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <AlertDescription className="text-xs">{error}</AlertDescription>
            </Alert>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 px-5 py-4 rounded-b-2xl flex gap-3">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
            className="flex-1 h-12 rounded-xl border-gray-200 dark:border-gray-700 font-semibold"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSell}
            disabled={loading || availableBalance <= 0}
            className="flex-[2] h-12 rounded-xl font-bold bg-red-600 hover:bg-red-700 text-white disabled:opacity-50"
          >
            {loading
              ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Launching...</>
              : <><ShieldCheck className="mr-2 h-4 w-4" />Sell {assetSymbol}</>
            }
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}