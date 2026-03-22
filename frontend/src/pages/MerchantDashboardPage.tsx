// FILE: frontend/src/pages/MerchantDashboardPage.tsx
// Merchant command center — manage listings, handle orders, view stats.
// Matches DashboardPage.tsx visual pattern: Sidebar + dark gradient + modals.

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@/config/api'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'
import toast from 'react-hot-toast'
import Sidebar from '@/components/layout/Sidebar'
import {
  BadgeCheck, TrendingUp, ShoppingBag, Star,
  Plus, Pause, Play, Trash2, Eye, RefreshCw,
  Clock, CheckCircle, XCircle, AlertCircle,
  ChevronRight, Loader2, Edit3
} from 'lucide-react'
import { Button } from '@/components/ui/button.tsx'
import { Badge } from '@/components/ui/badge.tsx'
import { MerchantOnboardingModal } from '@/components/p2p/MerchantOnboardingModal'
import { CreateListingModal } from '@/components/p2p/CreateListingModal'
import { CreateSellListingModal } from '@/components/p2p/CreateSellListingModal'

// ── TYPES ─────────────────────────────────────────────────────
interface MerchantProfile {
  id: string
  display_name: string
  verified: boolean
  total_orders: number
  completion_rate: number
  avg_release_time_mins: number
  is_online: boolean
  created_at: string
  status: 'pending' | 'approved' | 'rejected'
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
  is_active: boolean
  created_at: string
}

interface Order {
  id: string
  order_number: string
  token: string
  fiat_currency: string
  fiat_amount: number
  token_amount: number
  status: string
  payment_receipt_url: string | null
  payment_deadline: string
  created_at: string
  buyer_id: string
}

const STATUS_BADGE: Record<string, { label: string; class: string }> = {
  payment_window: { label: 'Awaiting Payment', class: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30' },
  paid:           { label: 'Receipt Uploaded', class: 'bg-blue-500/20 text-blue-300 border-blue-500/30'   },
  confirming:     { label: 'Releasing',        class: 'bg-purple-500/20 text-purple-300 border-purple-500/30' },
  completed:      { label: 'Completed',        class: 'bg-green-500/20 text-green-300 border-green-500/30'  },
  cancelled:      { label: 'Cancelled',        class: 'bg-gray-600/40 text-gray-400 border-gray-600'       },
  expired:        { label: 'Expired', class: 'bg-orange-500/20 text-orange-300 border-orange-500/30' },
  disputed:       { label: 'Disputed',         class: 'bg-red-500/20 text-red-300 border-red-500/30'       },
}

type Tab = 'overview' | 'listings' | 'orders'

// ─────────────────────────────────────────────────────────────
export default function MerchantDashboardPage() {
  const { user } = useAuth()
  const navigate  = useNavigate()

  const [tab,             setTab]             = useState<Tab>('overview')
  const [loading,         setLoading]         = useState(true)
  const [merchant,        setMerchant]        = useState<MerchantProfile | null>(null)
  const [listings,        setListings]        = useState<Listing[]>([])
  const [orders,          setOrders]          = useState<Order[]>([])
  const [showOnboarding,    setShowOnboarding]    = useState(false)
  const [showCreateListing, setShowCreateListing] = useState(false)
  const [showCreateSellListing, setShowCreateSellListing] = useState(false)
  const [togglingId,      setTogglingId]      = useState<string | null>(null)
  const [orderFilter,     setOrderFilter]     = useState<string>('all')

  // ── Fetch merchant profile ────────────────────────────────
  const fetchMerchant = useCallback(async () => {
    try {
      const res = await apiClient.get('/api/p2p/merchants/me')
      if (res.data?.success) {
        setMerchant(res.data.merchant)
      } else {
        setMerchant(null)  // not a merchant yet
      }
    } catch {
      setMerchant(null)
    }
  }, [])

  // ── Fetch listings ────────────────────────────────────────
  const fetchListings = useCallback(async () => {
    if (!merchant?.id) return
    try {
      const res = await apiClient.get(`/api/p2p/merchants/${merchant.id}/listings`)
      if (res.data?.success) setListings(res.data.listings)
    } catch (e) {
      console.error('Listings fetch failed:', e)
    }
  }, [merchant?.id])

  // ── Fetch orders ─────────────────────────────────────────
  const fetchOrders = useCallback(async () => {
    if (!merchant?.id) return
    try {
      const res = await apiClient.get(`/api/p2p/merchants/${merchant.id}/orders`)
      if (res.data?.success) setOrders(res.data.orders)
    } catch (e) {
      console.error('Orders fetch failed:', e)
    }
  }, [merchant?.id])

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      await fetchMerchant()
      setLoading(false)
    }
    init()
  }, [fetchMerchant])

  useEffect(() => {
    if (merchant?.id) {
      fetchListings()
      fetchOrders()
    }
  }, [merchant?.id, fetchListings, fetchOrders])

  // ── Realtime: new orders ──────────────────────────────────
  useEffect(() => {
    if (!merchant?.id) return
    const channel = supabase
      .channel(`merchant-orders:${merchant.id}`)
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'p2p_orders',
        filter: `merchant_id=eq.${merchant.id}`
      }, payload => {
        toast.success('📦 New order received!')
        setOrders(prev => [payload.new as Order, ...prev])
      })
      .on('postgres_changes', {
        event: 'UPDATE',
        schema: 'public',
        table: 'p2p_orders',
        filter: `merchant_id=eq.${merchant.id}`
      }, payload => {
        setOrders(prev => prev.map(o => o.id === payload.new.id ? { ...o, ...payload.new } : o))
      })
      .subscribe()
    return () => { supabase.removeChannel(channel) }
  }, [merchant?.id])

  // ── Toggle listing active/paused ─────────────────────────
  const toggleListing = async (listingId: string, currentActive: boolean) => {
    setTogglingId(listingId)
    try {
      const res = await apiClient.patch(`/api/p2p/listings/${listingId}/toggle`)
      if (res.data?.success) {
        setListings(prev => prev.map(l =>
          l.id === listingId ? { ...l, is_active: !currentActive } : l
        ))
        toast.success(currentActive ? 'Listing paused' : 'Listing activated')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to update listing')
    } finally {
      setTogglingId(null)
    }
  }

  // ── Delete listing ────────────────────────────────────────
  const deleteListing = async (listingId: string) => {
    if (!confirm('Delete this listing? This cannot be undone.')) return
    try {
      await apiClient.delete(`/api/p2p/listings/${listingId}`)
      setListings(prev => prev.filter(l => l.id !== listingId))
      toast.success('Listing deleted')
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to delete')
    }
  }

  // ── Toggle online status ──────────────────────────────────
  const toggleOnline = async () => {
    if (!merchant) return
    try {
      const res = await apiClient.patch('/api/p2p/merchants/me/online', {
        is_online: !merchant.is_online
      })
      if (res.data?.success) {
        setMerchant(prev => prev ? { ...prev, is_online: !prev.is_online } : prev)
        toast.success(merchant.is_online ? '🔴 You are now offline' : '🟢 You are now online')
      }
    } catch {
      toast.error('Failed to update status')
    }
  }

  // ── Computed stats ────────────────────────────────────────
  const activeListings  = listings.filter(l => l.is_active).length
  const pendingOrders   = orders.filter(o => ['payment_window','paid','confirming'].includes(o.status)).length
  const completedOrders = orders.filter(o => o.status === 'completed').length
  const totalVolume     = orders.filter(o => o.status === 'completed')
    .reduce((sum, o) => sum + o.token_amount, 0)

  const filteredOrders = orderFilter === 'all'
    ? orders
    : orders.filter(o => o.status === orderFilter)

  // ─────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
        </div>
      </div>
    )
  }

  // ── Not a merchant yet ────────────────────────────────────
  if (!merchant) {
    return (
      <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="max-w-md text-center space-y-6">
            <div className="w-24 h-24 mx-auto bg-gradient-to-br from-yellow-500/20 to-orange-500/20 rounded-full flex items-center justify-center border border-yellow-500/30">
              <BadgeCheck className="h-12 w-12 text-yellow-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white mb-2">Become a Merchant</h1>
              <p className="text-gray-400 text-sm">
                Provide liquidity to Seamount users and earn fees on every completed trade.
                Takes less than 3 minutes to set up.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              {[
                { label: 'Your rate', sub: 'spread-based earnings' },
                { label: '15min', sub: 'payment window' },
                { label: '100%', sub: 'escrow protected' },
              ].map((s, i) => (
                <div key={i} className="bg-gray-800/50 rounded-xl p-3 border border-gray-700">
                  <div className="text-xl font-bold text-blue-400">{s.label}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{s.sub}</div>
                </div>
              ))}
            </div>
            <Button
              onClick={() => setShowOnboarding(true)}
              className="w-full h-12 bg-yellow-500 hover:bg-yellow-400 text-black font-bold text-base gap-2"
            >
              <BadgeCheck className="h-5 w-5" />
              Apply as Merchant
            </Button>
          </div>
        </div>
        <MerchantOnboardingModal
          open={showOnboarding}
          onOpenChange={setShowOnboarding}
          onSuccess={() => { fetchMerchant() }}
        />
      </div>
    )
  }

  if (merchant && merchant.status === 'pending') {
    return (
      <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="max-w-md text-center space-y-5">
            <div className="w-20 h-20 mx-auto bg-gradient-to-br from-yellow-500/20 to-orange-500/20 rounded-full flex items-center justify-center border border-yellow-500/30">
              <Clock className="h-10 w-10 text-yellow-400 animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white mb-2">
                Application Under Review
              </h1>
              <p className="text-gray-400 text-sm leading-relaxed">
                Your merchant application has been submitted successfully.
                Our team reviews all applications within <strong className="text-white">24–48 hours</strong>.
                You will be notified once your account is approved.
              </p>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700 text-left space-y-2">
              <p className="text-xs text-gray-500 uppercase tracking-wide font-bold">
                Application Details
              </p>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Display name</span>
                <span className="text-white font-medium">{merchant.display_name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Status</span>
                <span className="text-yellow-400 font-medium">⏳ Pending Review</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Applied</span>
                <span className="text-white">
                  {new Date(merchant.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            <p className="text-xs text-gray-600">
              Questions? Contact support from the Settings page.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (merchant && merchant.status === 'rejected') {
    return (
      <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="w-full max-w-md space-y-4">

            {/* Status card — tight */}
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 flex items-center gap-3">
              <XCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
              <div>
                <p className="text-sm font-bold text-white leading-tight">Application Not Approved</p>
                <p className="text-xs text-gray-400">You can still buy crypto. Fix issues below and reapply.</p>
              </div>
            </div>

            {/* Reasons + Steps — single combined card */}
            <div className="bg-gray-800/60 border border-gray-700 rounded-xl divide-y divide-gray-700/60">
              {/* Reasons */}
              <div className="px-4 py-3 space-y-1.5">
                <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Why it was rejected</p>
                {[
                  { icon: '🪪', text: 'KYC not completed'                   },
                  { icon: '💼', text: 'Insufficient token balance'           },
                  { icon: '📋', text: 'Incomplete profile'                   },
                  { icon: '🏦', text: 'Payment account name mismatch'        },
                ].map((r, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-gray-300">
                    <span className="w-4 text-center flex-shrink-0">{r.icon}</span>
                    {r.text}
                  </div>
                ))}
              </div>

              {/* Steps */}
              <div className="px-4 py-3 space-y-1.5">
                <p className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-2">Before reapplying</p>
                {[
                  'Complete KYC in Settings → Identity',
                  'Fund wallets with tokens you plan to sell',
                  'Ensure payment account matches your KYC name',
                ].map((step, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-gray-300">
                    <span className="w-4 h-4 rounded-full bg-blue-600 text-white text-[10px] flex items-center justify-center flex-shrink-0 font-bold">
                      {i + 1}
                    </span>
                    {step}
                  </div>
                ))}
              </div>
            </div>

            {/* CTA */}
            <button
              onClick={() => setShowOnboarding(true)}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white font-bold rounded-xl transition-all flex items-center justify-center gap-2 text-sm"
            >
              <BadgeCheck className="h-4 w-4" /> Reapply as Merchant
            </button>

            <p className="text-center text-xs text-gray-600">Questions? Settings → Support</p>
          </div>
        </div>

        <MerchantOnboardingModal
          open={showOnboarding}
          onOpenChange={setShowOnboarding}
          onSuccess={() => fetchMerchant()}
        />
      </div>
    )
  }

  // ── Merchant dashboard ────────────────────────────────────
  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
        <div className="max-w-5xl mx-auto">

          {/* ── Header ── */}
          <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-2">
                <BadgeCheck className="h-7 w-7 text-yellow-400" />
                Merchant Hub
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-gray-400 text-sm">{merchant.display_name}</span>
                {merchant.verified && (
                  <Badge className="bg-yellow-500/20 text-yellow-300 border border-yellow-500/30 text-xs">
                    ✓ Verified
                  </Badge>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={toggleOnline}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all
                  ${merchant.is_online
                    ? 'bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30'
                    : 'bg-gray-700/50 text-gray-400 border border-gray-600 hover:bg-gray-700'
                  }`}
              >
                <span className={`w-2 h-2 rounded-full ${merchant.is_online ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
                {merchant.is_online ? 'Online' : 'Offline'}
              </button>
              <Button onClick={() => setShowCreateSellListing(true)} size="sm"
                className="bg-orange-600 hover:bg-orange-700 gap-2">
                <Plus className="h-4 w-4" /> Buy Listing
              </Button>
              <Button onClick={() => setShowCreateListing(true)} size="sm"
                className="bg-blue-600 hover:bg-blue-700 gap-2">
                <Plus className="h-4 w-4" /> Sell Listing
              </Button>
            </div>
          </div>

          {/* ── Stats Row ── */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              { label: 'Total Orders',    value: merchant.total_orders,              icon: ShoppingBag, color: 'text-blue-400'   },
              { label: 'Completion Rate', value: `${merchant.completion_rate}%`,     icon: Star,        color: 'text-yellow-400' },
              { label: 'Active Listings', value: activeListings,                     icon: TrendingUp,  color: 'text-green-400'  },
              { label: 'Pending Orders',  value: pendingOrders,                      icon: Clock,       color: 'text-orange-400' },
            ].map((stat, i) => (
              <div key={i} className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-500 uppercase tracking-wide">{stat.label}</span>
                  <stat.icon className={`h-4 w-4 ${stat.color}`} />
                </div>
                <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
              </div>
            ))}
          </div>

          {/* ── Tabs ── */}
          <div className="flex gap-1 mb-5 bg-gray-800/50 rounded-xl p-1 border border-gray-700 w-fit">
            {(['overview', 'listings', 'orders'] as Tab[]).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 rounded-lg text-sm font-semibold capitalize transition-all
                  ${tab === t
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-gray-400 hover:text-white'
                  }`}
              >
                {t}
                {t === 'orders' && pendingOrders > 0 && (
                  <span className="ml-1.5 bg-orange-500 text-white text-xs rounded-full px-1.5 py-0.5">
                    {pendingOrders}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* ── Tab: Overview ── */}
          {tab === 'overview' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700 space-y-3">
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-green-400" /> Performance
                  </h3>
                  {[
                    { label: 'Completed orders', value: completedOrders },
                    { label: 'Total volume',      value: `${totalVolume.toFixed(4)} tokens` },
                    { label: 'Avg release time',  value: `${merchant.avg_release_time_mins} min` },
                    { label: 'Member since',      value: new Date(merchant.created_at).toLocaleDateString() },
                  ].map((row, i) => (
                    <div key={i} className="flex justify-between text-sm">
                      <span className="text-gray-400">{row.label}</span>
                      <span className="text-white font-medium">{String(row.value)}</span>
                    </div>
                  ))}
                </div>

                <div className="bg-gray-800/50 rounded-xl p-5 border border-gray-700 space-y-3">
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    <Clock className="h-4 w-4 text-orange-400" /> Recent Orders
                  </h3>
                  {orders.slice(0, 4).length === 0 ? (
                    <p className="text-gray-500 text-sm">No orders yet</p>
                  ) : orders.slice(0, 4).map(o => {
                    const s = STATUS_BADGE[o.status] ?? STATUS_BADGE.cancelled
                    return (
                      <button
                        key={o.id}
                        onClick={() => navigate(`/p2p/orders/${o.id}`)}
                        className="w-full flex items-center justify-between text-sm hover:bg-gray-700/50 rounded-lg px-2 py-1.5 transition"
                      >
                        <span className="text-gray-300 font-mono">#{o.order_number.slice(-8)}</span>
                        <span className="text-gray-400">{o.token_amount.toFixed(4)} {o.token.split('_')[0]}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${s.class}`}>{s.label}</span>
                        <ChevronRight className="h-3 w-3 text-gray-600" />
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {/* ── Tab: Listings ── */}
          {tab === 'listings' && (
            <div className="space-y-3">
              {listings.length === 0 ? (
                <div className="text-center py-16 text-gray-500">
                  <ShoppingBag className="h-10 w-10 mx-auto mb-3 opacity-30" />
                  <p className="font-semibold">No listings yet</p>
                  <p className="text-sm mt-1">Create your first offer to start trading</p>
                  <Button onClick={() => setShowOnboarding(true)}
                    className="mt-4 bg-blue-600 hover:bg-blue-700 gap-2">
                    <Plus className="h-4 w-4" /> Create Listing
                  </Button>
                </div>
              ) : listings.map(l => (
                <div key={l.id}
                  className={`bg-gray-800/50 rounded-xl border p-4 transition
                    ${l.is_active ? 'border-gray-700' : 'border-gray-700/40 opacity-60'}`}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{l.token.split('_')[0]}</span>
                        <span className="text-xs text-gray-500">({l.token})</span>
                        <Badge className={
                          l.listing_type === 'sell'
                            ? 'bg-orange-500/20 text-orange-400 border-orange-500/30 text-xs'
                            : 'bg-blue-500/20 text-blue-400 border-blue-500/30 text-xs'
                        }>
                          {l.listing_type === 'sell' ? 'Buy Listing' : 'Sell Listing'}
                        </Badge>
                        <Badge className={l.is_active
                          ? 'bg-green-500/20 text-green-400 border-green-500/30 text-xs'
                          : 'bg-gray-600/40 text-gray-400 border-gray-600 text-xs'}>
                          {l.is_active ? 'Active' : 'Paused'}
                        </Badge>
                      </div>
                      <div className="flex gap-4 mt-1 text-sm text-gray-400">
                        <span>{l.price_per_token.toLocaleString()} {l.fiat_currency}/token</span>
                        <span>Limit: {l.min_order_fiat.toLocaleString()}–{l.max_order_fiat.toLocaleString()} {l.fiat_currency}</span>
                        <span>Available: {l.available_amount} {l.token.split('_')[0]}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => toggleListing(l.id, l.is_active)}
                        disabled={togglingId === l.id}
                        className={`p-2 rounded-lg transition ${l.is_active
                          ? 'text-yellow-400 hover:bg-yellow-500/10'
                          : 'text-green-400 hover:bg-green-500/10'
                        }`}
                        title={l.is_active ? 'Pause' : 'Activate'}
                      >
                        {togglingId === l.id
                          ? <Loader2 className="h-4 w-4 animate-spin" />
                          : l.is_active ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />
                        }
                      </button>
                      <button
                        onClick={() => deleteListing(l.id)}
                        className="p-2 rounded-lg text-red-400 hover:bg-red-500/10 transition"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Tab: Orders ── */}
          {tab === 'orders' && (
            <div className="space-y-4">
              {/* Filter */}
              <div className="flex gap-2 flex-wrap">
                {['all', 'payment_window', 'paid', 'confirming', 'completed', 'expired', 'cancelled', 'disputed'].map(f => (
                  <button
                    key={f}
                    onClick={() => setOrderFilter(f)}
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold capitalize transition
                      ${orderFilter === f
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-500'
                      }`}
                  >
                    {f === 'all' ? 'All' : STATUS_BADGE[f]?.label ?? f}
                    {f === 'paid' && orders.filter(o => o.status === 'paid').length > 0 && (
                      <span className="ml-1.5 bg-blue-500 text-white text-xs rounded-full px-1">
                        {orders.filter(o => o.status === 'paid').length}
                      </span>
                    )}
                  </button>
                ))}
              </div>

              {filteredOrders.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <ShoppingBag className="h-8 w-8 mx-auto mb-2 opacity-30" />
                  <p>No orders in this category</p>
                </div>
              ) : filteredOrders.map(o => {
                const s = STATUS_BADGE[o.status] ?? STATUS_BADGE.cancelled
                const isPaid = o.status === 'paid'
                return (
                  <div key={o.id}
                    className={`bg-gray-800/50 rounded-xl border p-4 space-y-3
                      ${isPaid ? 'border-blue-500/40 ring-1 ring-blue-500/20' : 'border-gray-700'}`}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <span className="font-mono text-sm text-gray-300 font-bold">
                          #{o.order_number}
                        </span>
                        <span className="ml-2 text-xs text-gray-500">
                          {new Date(o.created_at).toLocaleString()}
                        </span>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full border ${s.class}`}>
                        {s.label}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-4 text-sm">
                      <span className="text-gray-400">
                        <span className="text-white font-bold">{o.token_amount.toFixed(4)}</span>{' '}
                        {o.token.split('_')[0]}
                      </span>
                      <span className="text-gray-400">
                        <span className="text-white font-bold">{o.fiat_amount.toLocaleString()}</span>{' '}
                        {o.fiat_currency}
                      </span>
                      {o.status === 'payment_window' && (
                        <span className="text-yellow-400 text-xs">
                          ⏱ Expires {new Date(o.payment_deadline).toLocaleTimeString()}
                        </span>
                      )}
                    </div>

                    {/* Action buttons per status */}
                    <div className="flex gap-2 flex-wrap">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigate(`/p2p/orders/${o.id}`)}
                        className="gap-1.5 border-gray-600 text-gray-300 hover:text-white text-xs"
                      >
                        <Eye className="h-3.5 w-3.5" /> View Order
                      </Button>

                      {isPaid && (
                        <Button
                          size="sm"
                          onClick={() => navigate(`/p2p/orders/${o.id}`)}
                          className="gap-1.5 bg-green-600 hover:bg-green-700 text-white text-xs font-bold animate-pulse"
                        >
                          <CheckCircle className="h-3.5 w-3.5" /> Review & Release Tokens
                        </Button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Onboarding modal reused for creating new listings */}
      <MerchantOnboardingModal
        open={showOnboarding}
        onOpenChange={setShowOnboarding}
        onSuccess={() => fetchMerchant()}
      />

      {/* Create listing modal — for approved merchants adding new listings */}
      {merchant && (
        <CreateListingModal
          merchantId={merchant.id}
          open={showCreateListing}
          onOpenChange={setShowCreateListing}
          onSuccess={() => {
            fetchListings()
            toast.success('Listing live on marketplace!')
          }}
        />
      )}
      {merchant && (
            <CreateSellListingModal
              merchantId={merchant.id}
              open={showCreateSellListing}
              onOpenChange={setShowCreateSellListing}
              onSuccess={() => { fetchListings(); toast.success('Buy listing live!') }}
            />
    )}
    </div>
  )
}