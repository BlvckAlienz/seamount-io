// FILE: frontend/src/components/p2p/SellListings.tsx

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/config/api'
import { SellOrderModal } from './SellOrderModal'
import { ShieldCheck, Star, Clock, ChevronRight, Loader2, RefreshCw } from 'lucide-react'

const TOKEN_OPTIONS = [
  { value: '', label: 'All Tokens' },
  { value: 'ALGO',         label: 'ALGO'          },
  { value: 'USDT_ALGO',    label: 'USDT (Algorand)' },
  { value: 'USDCa',        label: 'USDCa'         },
  { value: 'goBTC',        label: 'goBTC'         },
  { value: 'goETH',        label: 'goETH'         },
  { value: 'BTC',          label: 'BTC'           },
  { value: 'ETH',          label: 'ETH'           },
  { value: 'USDT_ETH',     label: 'USDT (ETH)'    },
  { value: 'USDC_ETH',     label: 'USDC (ETH)'    },
  { value: 'MATIC',        label: 'MATIC'         },
  { value: 'USDT_POLYGON', label: 'USDT (Polygon)'},
  { value: 'USDC_POLYGON', label: 'USDC (Polygon)'},
  { value: 'TRX',          label: 'TRX'           },
  { value: 'USDT_TRON',    label: 'USDT (Tron) ⭐' },
  { value: 'SOL',          label: 'SOL'           },
  { value: 'USDT_SOLANA',  label: 'USDT (Solana)' },
  { value: 'USDC_SOLANA',  label: 'USDC (Solana)' },
]

const FIAT_OPTIONS = ['', 'KES', 'NGN', 'GHS', 'UGX', 'TZS', 'ZAR', 'USD', 'GBP', 'EUR']

export function SellListings() {
  const [listings,        setListings]  = useState<any[]>([])
  const [loading,         setLoading]   = useState(true)
  const [filterToken,     setFilterToken] = useState('')
  const [filterFiat,      setFilterFiat]  = useState('')
  const [selectedListing, setSelected]  = useState<any | null>(null)

  const fetchListings = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filterToken) params.append('token', filterToken)
      if (filterFiat)  params.append('fiat_currency', filterFiat)
      const res = await apiClient.get(`/api/p2p/sell/listings?${params}`)
      if (res.data?.success) setListings(res.data.listings)
    } catch { /* silent */ }
    finally { setLoading(false) }
  }, [filterToken, filterFiat])

  useEffect(() => { fetchListings() }, [fetchListings])

  if (loading) return (
    <div className="flex justify-center py-16">
      <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
    </div>
  )

  return (
    <div className="p-4 space-y-4">

      {/* Filters */}
      <div className="flex gap-2 flex-wrap items-center justify-between">
        <div className="flex gap-2">
          <select
            value={filterToken}
            onChange={e => setFilterToken(e.target.value)}
            className="text-sm px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            {TOKEN_OPTIONS.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <select
            value={filterFiat}
            onChange={e => setFilterFiat(e.target.value)}
            className="text-sm px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            {FIAT_OPTIONS.map(f => (
              <option key={f} value={f}>{f || 'All Currencies'}</option>
            ))}
          </select>
        </div>
        <button onClick={fetchListings} className="text-gray-400 hover:text-gray-600 transition">
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Listings */}
      {listings.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="font-semibold">No sell listings available</p>
          <p className="text-sm mt-1">Check back later or try different filters</p>
        </div>
      ) : listings.map((listing: any) => {
        const m = listing.p2p_merchants
        const tokenDisplay = listing.token?.split('_')[0]
        return (
          <div key={listing.id}
            className="bg-white border border-gray-200 rounded-xl p-4 hover:border-orange-300 hover:shadow-sm transition">

            {/* Merchant row */}
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 rounded-full bg-orange-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                {m?.display_name?.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1 font-semibold text-gray-900 text-sm">
                  <span className="truncate">{m?.display_name}</span>
                  {m?.verified && <ShieldCheck className="h-3.5 w-3.5 text-blue-500 flex-shrink-0" />}
                  {m?.is_online && (
                    <span className="ml-1 w-1.5 h-1.5 bg-green-500 rounded-full flex-shrink-0" />
                  )}
                </div>
                <div className="flex gap-3 text-xs text-gray-500 mt-0.5">
                  <span>{m?.total_orders} orders</span>
                  <span>
                    <Star className="h-3 w-3 inline text-yellow-400 mr-0.5" />
                    {m?.completion_rate?.toFixed(1)}%
                  </span>
                  <span>
                    <Clock className="h-3 w-3 inline mr-0.5" />
                    {m?.avg_release_time_mins}min pay
                  </span>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-lg font-bold text-orange-600">
                  {listing.price_per_token?.toLocaleString()} {listing.fiat_currency}
                </div>
                <div className="text-xs text-gray-500">per {tokenDisplay}</div>
              </div>
            </div>

            {/* Details + CTA */}
            <div className="flex items-center justify-between text-sm">
              <div className="space-y-0.5">
                <div className="text-xs text-gray-500">
                  Limit:{' '}
                  <span className="text-gray-900 font-medium">
                    {listing.min_order_fiat?.toLocaleString()} – {listing.max_order_fiat?.toLocaleString()} {listing.fiat_currency}
                  </span>
                </div>
                <div className="text-xs text-gray-500">
                  Pays via:{' '}
                  <span className="text-gray-900 font-medium">
                    {(listing.payment_methods || []).slice(0, 2).join(', ')}
                    {(listing.payment_methods || []).length > 2 && ` +${listing.payment_methods.length - 2}`}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelected(listing)}
                className="flex items-center gap-1.5 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white text-sm font-bold rounded-lg transition"
              >
                Sell {tokenDisplay} <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )
      })}

      {/* Order modal */}
      {selectedListing && (
        <SellOrderModal
          listing={selectedListing}
          open={!!selectedListing}
          onOpenChange={open => { if (!open) setSelected(null) }}
        />
      )}
    </div>
  )
}