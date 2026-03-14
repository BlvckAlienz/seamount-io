// FILE: frontend/src/components/p2p/MerchantListings.tsx
// Binance P2P-style merchant listing page.
// Token list mirrors ASSET_GROUPS in SendForm.tsx exactly.

import { useState, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button.tsx'
import { Input } from '@/components/ui/input.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.tsx'
import { Badge } from '@/components/ui/badge.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import {
  Loader2, ShieldCheck, Clock, Star,
  TrendingUp, Search, SlidersHorizontal, RefreshCw
} from 'lucide-react'
import { PlaceOrderModal } from './PlaceOrderModal'

// ─────────────────────────────────────────────────────────────
// TOKEN + CHAIN DATA (mirrors SendForm.tsx ASSET_GROUPS exactly)
// ─────────────────────────────────────────────────────────────
const ASSET_GROUPS = [
  {
    chain: 'algorand',
    chainLabel: '🟢 Algorand',
    tokens: [
      { value: 'ALGO',  label: 'Algorand (ALGO)',       icon: 'Ⱥ' },
      { value: 'USDT',  label: 'Tether (Algorand)',      icon: '₮' },
      { value: 'USDCa', label: 'USD Coin (USDCa)',       icon: '◎' },
      { value: 'goBTC', label: 'Wrapped Bitcoin',        icon: '₿' },
      { value: 'goETH', label: 'Wrapped Ethereum',       icon: 'Ξ' },
    ]
  },
  {
    chain: 'bitcoin',
    chainLabel: '🟠 Bitcoin',
    tokens: [
      { value: 'BTC',   label: 'Bitcoin (BTC)',          icon: '₿' },
    ]
  },
  {
    chain: 'ethereum',
    chainLabel: '🔵 Ethereum',
    tokens: [
      { value: 'ETH',       label: 'Ethereum (ETH)',     icon: 'Ξ' },
      { value: 'USDT_ETH',  label: 'Tether (Ethereum)',  icon: '₮' },
      { value: 'USDC_ETH',  label: 'USD Coin (Ethereum)',icon: '◎' },
    ]
  },
  {
    chain: 'polygon',
    chainLabel: '🟣 Polygon',
    tokens: [
      { value: 'MATIC',          label: 'Polygon (MATIC)',    icon: '⬣' },
      { value: 'USDT_POLYGON',   label: 'Tether (Polygon)',   icon: '₮' },
      { value: 'USDC_POLYGON',   label: 'USD Coin (Polygon)', icon: '◎' },
    ]
  },
  {
    chain: 'tron',
    chainLabel: '🔴 Tron',
    tokens: [
      { value: 'TRX',        label: 'TRON (TRX)',         icon: '⚡' },
      { value: 'USDT_TRON',  label: 'Tether (Tron)',      icon: '₮' },
    ]
  },
  {
    chain: 'solana',
    chainLabel: '🟣 Solana',
    tokens: [
      { value: 'SOL',          label: 'Solana (SOL)',         icon: '◎' },
      { value: 'USDT_SOLANA',  label: 'Tether (Solana)',      icon: '₮' },
      { value: 'USDC_SOLANA',  label: 'USD Coin (Solana)',    icon: '◎' },
    ]
  }
]

// Flat list for lookup
const ALL_TOKENS = ASSET_GROUPS.flatMap(g => g.tokens.map(t => ({ ...t, chain: g.chain, chainLabel: g.chainLabel })))

// Popular tokens shown as quick-select tabs (mirrors Binance's tab row)
const QUICK_TABS = ['USDT_TRON', 'USDT_POLYGON', 'USDC_ETH', 'USDC_POLYGON', 'BTC', 'ETH', 'SOL']

const FIAT_CURRENCIES = ['USD','KES','GBP','EUR','NGN','GHS','UGX','TZS','ZAR','INR','PHP']

// ─────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────
interface Merchant {
  id: string
  display_name: string
  verified: boolean
  total_orders: number
  completion_rate: number
  avg_release_time_mins: number
  is_online: boolean
}

interface Listing {
  id: string
  token: string
  fiat_currency: string
  price_per_token: number
  min_order_fiat: number
  max_order_fiat: number
  available_amount: number
  payment_methods: string[]
  terms: string | null
  p2p_merchants: Merchant
}

// ─────────────────────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────────────────────
export function MerchantListings() {
  const [selectedToken, setSelectedToken]   = useState('USDT_TRON')
  const [fiatCurrency,  setFiatCurrency]    = useState('USD')
  const [amountFilter,  setAmountFilter]    = useState('')
  const [paymentFilter, setPaymentFilter]   = useState('all')
  const [listings,      setListings]        = useState<Listing[]>([])
  const [loading,       setLoading]         = useState(false)
  const [error,         setError]           = useState<string | null>(null)
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null)
  const [showFilters,   setShowFilters]     = useState(false)

  const selectedTokenMeta = ALL_TOKENS.find(t => t.value === selectedToken)

  // ── Fetch listings ────────────────────────────────────────
  const fetchListings = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      let query = supabase
        .from('p2p_listings')
        .select(`
          id, token, fiat_currency, price_per_token,
          min_order_fiat, max_order_fiat, available_amount,
          payment_methods, terms,
          p2p_merchants (
            id, display_name, verified, total_orders,
            completion_rate, avg_release_time_mins, is_online
          )
        `)
        .eq('token', selectedToken)
        .eq('fiat_currency', fiatCurrency)
        .eq('is_active', true)
        .order('price_per_token', { ascending: true })

      if (amountFilter && parseFloat(amountFilter) > 0) {
        const amt = parseFloat(amountFilter)
        query = query.lte('min_order_fiat', amt).gte('max_order_fiat', amt)
      }

      const { data, error: qErr } = await query
      if (qErr) throw qErr

      let results = (data ?? []) as unknown as Listing[]

      // Filter by payment method client-side
      if (paymentFilter !== 'all') {
        results = results.filter(l =>
          (l.payment_methods ?? []).some(pm =>
            pm.toLowerCase().includes(paymentFilter.toLowerCase())
          )
        )
      }

      setListings(results)
    } catch (err: any) {
      setError(err.message ?? 'Failed to load listings')
    } finally {
      setLoading(false)
    }
  }, [selectedToken, fiatCurrency, amountFilter, paymentFilter])

  useEffect(() => { fetchListings() }, [fetchListings])

  // ─────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────
  return (
    <div className="w-full max-w-5xl mx-auto px-2 sm:px-4 py-6 space-y-4">

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">P2P Trading</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Buy crypto directly from verified merchants
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchListings}
          disabled={loading}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* ── Quick Token Tabs ── */}
      <div className="overflow-x-auto">
        <div className="flex gap-2 min-w-max pb-1">
          {QUICK_TABS.map(tok => {
            const meta = ALL_TOKENS.find(t => t.value === tok)
            if (!meta) return null
            return (
              <button
                key={tok}
                onClick={() => setSelectedToken(tok)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold whitespace-nowrap transition-all
                  ${selectedToken === tok
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                  }`}
              >
                <span>{meta.icon}</span>
                <span>{tok.split('_')[0]}</span>
                {tok.includes('_') && (
                  <span className="text-xs opacity-70">({tok.split('_')[1]})</span>
                )}
              </button>
            )
          })}

          {/* More tokens via dropdown */}
          <Select value={selectedToken} onValueChange={setSelectedToken}>
            <SelectTrigger className="w-36 h-9 rounded-full text-sm font-semibold bg-gray-100 dark:bg-gray-800 border-0">
              <SelectValue placeholder="More tokens" />
            </SelectTrigger>
            <SelectContent className="max-h-80">
              {ASSET_GROUPS.map(group => (
                <div key={group.chain}>
                  <div className="px-3 py-1.5 text-xs font-bold text-gray-400 uppercase tracking-wide bg-gray-50 dark:bg-gray-900">
                    {group.chainLabel}
                  </div>
                  {group.tokens.map(t => (
                    <SelectItem key={t.value} value={t.value} className="pl-5">
                      <span className="flex items-center gap-2">
                        <span>{t.icon}</span>
                        <span>{t.label}</span>
                      </span>
                    </SelectItem>
                  ))}
                </div>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* ── Filters Row ── */}
      <div className="flex flex-wrap gap-3 items-end">

        {/* Fiat Currency */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Pay With
          </label>
          <Select value={fiatCurrency} onValueChange={setFiatCurrency}>
            <SelectTrigger className="w-28 h-10">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FIAT_CURRENCIES.map(f => (
                <SelectItem key={f} value={f}>{f}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Amount */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Amount ({fiatCurrency})
          </label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              type="number"
              placeholder="Enter amount"
              value={amountFilter}
              onChange={e => setAmountFilter(e.target.value)}
              className="pl-9 h-10 w-40"
            />
          </div>
        </div>

        {/* Payment Method */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Payment Method
          </label>
          <Select value={paymentFilter} onValueChange={setPaymentFilter}>
            <SelectTrigger className="w-44 h-10">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Methods</SelectItem>
              <SelectItem value="M-Pesa">M-Pesa</SelectItem>
              <SelectItem value="Airtel Money">Airtel Money</SelectItem>
              <SelectItem value="Equity Bank">Equity Bank</SelectItem>
              <SelectItem value="Bank Transfer">Bank Transfer</SelectItem>
              <SelectItem value="Paybill">M-Pesa Paybill</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="h-10 gap-2 self-end"
          onClick={() => { setAmountFilter(''); setPaymentFilter('all') }}
        >
          Clear
        </Button>
      </div>

      {/* ── Results Header ── */}
      <div className="hidden md:grid grid-cols-[2fr_1.5fr_2fr_2fr_1fr] gap-4 px-4 py-2 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide border-b border-gray-200 dark:border-gray-700">
        <span>Advertiser</span>
        <span>Price / Token</span>
        <span>Available · Limit</span>
        <span>Payment</span>
        <span className="text-right">Trade</span>
      </div>

      {/* ── Listings ── */}
      {loading && (
        <div className="flex justify-center items-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!loading && !error && listings.length === 0 && (
        <div className="text-center py-16 text-gray-500 dark:text-gray-400">
          <TrendingUp className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-semibold">No merchants available</p>
          <p className="text-sm mt-1">
            Try a different token, fiat currency, or payment method.
          </p>
        </div>
      )}

      {!loading && listings.map(listing => (
        <MerchantCard
          key={listing.id}
          listing={listing}
          fiatCurrency={fiatCurrency}
          tokenMeta={selectedTokenMeta}
          onBuy={() => setSelectedListing(listing)}
        />
      ))}

      {/* ── Place Order Modal ── */}
      {selectedListing && (
        <PlaceOrderModal
          listing={selectedListing}
          fiatCurrency={fiatCurrency}
          tokenMeta={selectedTokenMeta}
          open={!!selectedListing}
          onOpenChange={open => { if (!open) setSelectedListing(null) }}
        />
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// MERCHANT CARD
// ─────────────────────────────────────────────────────────────
function MerchantCard({
  listing, fiatCurrency, tokenMeta, onBuy
}: {
  listing: Listing
  fiatCurrency: string
  tokenMeta: typeof ALL_TOKENS[0] | undefined
  onBuy: () => void
}) {
  const m = listing.p2p_merchants
  const tokenDisplay = listing.token.split('_')[0]

  return (
    <div className="grid grid-cols-1 md:grid-cols-[2fr_1.5fr_2fr_2fr_1fr] gap-4 items-center p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-500 transition-all">

      {/* Col 1: Merchant Info */}
      <div className="flex items-center gap-3">
        <div className="relative flex-shrink-0">
          <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-sm">
            {m.display_name.charAt(0).toUpperCase()}
          </div>
          <span className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white dark:border-gray-800 ${m.is_online ? 'bg-green-500' : 'bg-gray-400'}`} />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-semibold text-sm text-gray-900 dark:text-white">
              {m.display_name}
            </span>
            {m.verified && (
              <ShieldCheck className="h-3.5 w-3.5 text-blue-500" />
            )}
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-xs text-gray-500">{m.total_orders} orders</span>
            <span className="text-xs text-gray-500">
              <Star className="h-3 w-3 inline text-yellow-400 mr-0.5" />
              {m.completion_rate.toFixed(1)}%
            </span>
            <span className="text-xs text-gray-500">
              <Clock className="h-3 w-3 inline mr-0.5" />
              {m.avg_release_time_mins} min
            </span>
          </div>
        </div>
      </div>

      {/* Col 2: Price */}
      <div>
        <div className="text-lg font-bold text-gray-900 dark:text-white">
          {listing.price_per_token.toLocaleString()} {fiatCurrency}
        </div>
        <div className="text-xs text-gray-500">per {tokenDisplay}</div>
      </div>

      {/* Col 3: Available + Limit */}
      <div className="space-y-0.5">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <span className="text-gray-500 text-xs">Available: </span>
          {listing.available_amount.toFixed(4)} {tokenDisplay}
        </div>
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <span className="text-gray-500 text-xs">Limit: </span>
          {listing.min_order_fiat.toLocaleString()} – {listing.max_order_fiat.toLocaleString()} {fiatCurrency}
        </div>
      </div>

      {/* Col 4: Payment Methods */}
      <div className="flex flex-wrap gap-1.5">
        {(listing.payment_methods ?? []).slice(0, 3).map(pm => (
          <Badge
            key={pm}
            variant="secondary"
            className="text-xs px-2 py-0.5 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800"
          >
            {pm}
          </Badge>
        ))}
        {(listing.payment_methods ?? []).length > 3 && (
          <Badge variant="secondary" className="text-xs">
            +{listing.payment_methods.length - 3}
          </Badge>
        )}
      </div>

      {/* Col 5: Buy Button */}
      <div className="flex justify-end">
        <Button
          onClick={onBuy}
          disabled={!m.is_online}
          className="bg-green-600 hover:bg-green-700 text-white font-bold px-5 h-10 disabled:opacity-50"
        >
          {m.is_online ? `Buy ${tokenDisplay}` : 'Offline'}
        </Button>
      </div>

    </div>
  )
}