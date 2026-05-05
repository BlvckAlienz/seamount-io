// File: frontend/src/components/wallet/FundWalletModal.tsx
import { useState, useEffect } from 'react'
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
import { Loader2, Wallet, Info, AlertCircle, ShieldCheck } from 'lucide-react'

interface FundWalletModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const ONRAMP_ASSET_GROUPS = {
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
    { value: 'MATIC',        label: 'Polygon (MATIC)',     icon: '▶' },
    { value: 'USDT_POLYGON', label: 'Tether (Polygon)',    icon: '₮' },
    { value: 'USDC_POLYGON', label: 'USD Coin (Polygon)',  icon: '◎' },
  ],
  '🔴 Tron': [
    { value: 'TRX',       label: 'TRON (TRX)',      icon: '⚡' },
    { value: 'USDT_TRON', label: 'Tether (Tron)',   icon: '₮' },
  ],
  '🟣 Solana': [
    { value: 'SOL',         label: 'Solana (SOL)',        icon: '◎' },
    { value: 'USDT_SOLANA', label: 'Tether (Solana)',     icon: '₮' },
    { value: 'USDC_SOLANA', label: 'USD Coin (Solana)',   icon: '◎' },
  ],
}

// Algorand-native assets not supported by MoonPay — remap silently
const ASSET_FALLBACK: Record<string, string> = {
  'goBTC': 'BTC', 'goETH': 'ETH', 'USDCa': 'USDC_ETH', 'USDT_ALGO': 'USDT_TRON',
}

const FIAT_OPTIONS = [
  { code: 'USD', flag: '🇺🇸' }, { code: 'EUR', flag: '🇪🇺' }, { code: 'GBP', flag: '🇬🇧' },
  { code: 'NGN', flag: '🇳🇬' }, { code: 'KES', flag: '🇰🇪' }, { code: 'GHS', flag: '🇬🇭' },
  { code: 'ZAR', flag: '🇿🇦' },
]

export function FundWalletModal({ open, onOpenChange }: FundWalletModalProps) {
  const [asset, setAsset]     = useState('USDT_TRON')
  const [amount, setAmount]   = useState('')
  const [currency, setCurrency] = useState('USD')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)

  const { session } = useAuth()

  useEffect(() => {
    if (!open) return
    const pre = sessionStorage.getItem('preselected_asset')
    if (pre) {
      setAsset(ASSET_FALLBACK[pre] ?? pre)
      sessionStorage.removeItem('preselected_asset')
    }
  }, [open])

  const handleBuy = async () => {
    if (!session) { toast.error('Sign in to buy crypto'); return }
    setLoading(true)
    setError(null)
    try {
      const res = await api.post('/api/v1/moonpay/url/onramp', {
        asset,
        base_currency_code:   currency,
        base_currency_amount: amount ? parseFloat(amount) : undefined,
      })
      if (!res?.success) throw new Error(res?.detail || 'Failed to initialize payment')

      const moonPayFactory = await loadMoonPay()
      const sdk = moonPayFactory({
        flow: 'buy', environment: 'production', variant: 'overlay',
        params: res.params,
      })
      sdk.on('transactionCompleted', () => {
        toast.success('🎉 Purchase complete! Crypto arriving shortly.')
        onOpenChange(false)
      })
      sdk.show()
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Payment failed'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const selectedAssetLabel = Object.values(ONRAMP_ASSET_GROUPS)
    .flat().find(a => a.value === asset)

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
              <div className="p-2 rounded-xl bg-blue-50 dark:bg-blue-900/30">
                <Wallet className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              Buy Crypto
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Card, bank transfer, Apple Pay & Google Pay. 160+ countries.
            </DialogDescription>
          </DialogHeader>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">

          {/* Asset */}
          <div className="space-y-1.5">
            <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Select Asset
            </Label>
            <Select value={asset} onValueChange={setAsset}>
              <SelectTrigger className="w-full h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="max-h-72 rounded-xl bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 z-[9999]">
                {Object.entries(ONRAMP_ASSET_GROUPS).map(([chain, assets]) => (
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

            {asset === 'MATIC' && (
              <p className="text-xs text-purple-600 dark:text-purple-400">
                ℹ️ MATIC runs on the POL network — delivered to your Polygon address.
              </p>
            )}
          </div>

          {/* Amount + Currency row */}
          <div className="space-y-1.5">
            <Label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Amount <span className="font-normal text-gray-400">(optional pre-fill)</span>
            </Label>
            <div className="flex gap-2">
              <Input
                type="number"
                placeholder="0.00"
                value={amount}
                onChange={e => setAmount(e.target.value)}
                disabled={loading}
                className="flex-1 h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
              <Select value={currency} onValueChange={setCurrency}>
                <SelectTrigger className="w-24 h-12 rounded-xl border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
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
          </div>

          {/* Trust badges */}
          <div className="grid grid-cols-3 gap-2">
            {[
              { icon: '🔒', text: 'KYC secured' },
              { icon: '⚡', text: 'Instant delivery' },
              { icon: '🌍', text: '160+ countries' },
            ].map(b => (
              <div key={b.text} className="flex flex-col items-center gap-1 p-2.5 rounded-xl bg-gray-50 dark:bg-gray-800 text-center">
                <span className="text-lg">{b.icon}</span>
                <span className="text-[10px] font-medium text-gray-500 dark:text-gray-400">{b.text}</span>
              </div>
            ))}
          </div>

          {/* Info */}
          <Alert className="border border-blue-100 dark:border-blue-900 bg-blue-50 dark:bg-blue-900/20 rounded-xl py-3">
            <Info className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
            <AlertDescription className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
              Powered by <strong className="text-blue-600 dark:text-blue-400">MoonPay</strong> —
              crypto delivered directly to your Seamount wallet after payment.
            </AlertDescription>
          </Alert>

          {error && (
            <Alert variant="destructive" className="rounded-xl border py-3">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <AlertDescription className="text-xs">{error}</AlertDescription>
            </Alert>
          )}
        </div>

        {/* Footer — sticky on mobile */}
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
            onClick={handleBuy}
            disabled={loading}
            className="flex-[2] h-12 rounded-xl font-bold bg-blue-600 hover:bg-blue-700 text-white"
          >
            {loading
              ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Launching...</>
              : <><ShieldCheck className="mr-2 h-4 w-4" />Buy {selectedAssetLabel?.label ?? asset}</>
            }
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}