// FILE: frontend/src/pages/PaymentsPage.tsx

import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import Sidebar from '@/components/layout/Sidebar'
import { MerchantListings } from '@/components/p2p/MerchantListings'
import { SellListings } from '@/components/p2p/SellListings'
import { FundWalletModal } from '@/components/wallet/FundWalletModal'
import { SendForm } from '@/components/payments/SendForm'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'
import {
  ArrowDownToLine, ArrowDownUp, ShoppingBag, ArrowUpRight,
  ClipboardList, Loader2, ChevronRight
} from 'lucide-react'

type Tab = 'p2p' | 'sell' | 'fund' | 'send' | 'orders'

const STATUS_PILL: Record<string, string> = {
  payment_window: 'bg-yellow-100 text-yellow-800',
  paid:           'bg-blue-100 text-blue-800',
  confirming:     'bg-purple-100 text-purple-800',
  completed:      'bg-green-100 text-green-800',
  cancelled:      'bg-gray-100 text-gray-600',
  expired: 'bg-orange-100 text-orange-700',
  disputed:       'bg-red-100 text-red-800',
}

const TABS: { id: Tab; label: string; icon: typeof ShoppingBag }[] = [
  { id: 'p2p',    label: 'Buy via P2P',  icon: ShoppingBag     },
  { id: 'sell',   label: 'Sell via P2P', icon: ArrowDownUp },
  { id: 'fund',   label: 'Fund Wallet',  icon: ArrowDownToLine },
  { id: 'send',   label: 'Send',         icon: ArrowUpRight    },
  { id: 'orders', label: 'My Orders',    icon: ClipboardList   },
]

const TAB_DESC: Record<Tab, string> = {
  p2p:    'Buy crypto directly from verified merchants using local payment methods — lowest fees',
  sell:   'Sell your crypto to verified merchants for local fiat — direct bank or mobile money payout',
  fund:   'Buy crypto instantly with your local currency via card or bank transfer',
  send:   'Send crypto to any wallet address across all supported chains',
  orders: 'Track your P2P buy and sell orders — active, completed and expired',
}

// ── Order History Component ────────────────────────────────────
function OrderHistory() {
  const { user }    = useAuth()
  const navigate    = useNavigate()
  const [orders,    setOrders]    = useState<any[]>([])
  const [loading,   setLoading]   = useState(true)
  const [filter,    setFilter]    = useState<string>('all')

  const fetchOrders = useCallback(async () => {
    if (!user?.id) return
    setLoading(true)
    try {
      const { data } = await supabase
        .from('p2p_orders')
        .select('id, order_number, token, fiat_currency, fiat_amount, token_amount, status, order_type, created_at, p2p_merchants(display_name)')
        .eq('buyer_id', user.id)
        .order('created_at', { ascending: false })
      setOrders(data ?? [])
    } finally {
      setLoading(false)
    }
  }, [user?.id])

  useEffect(() => { fetchOrders() }, [fetchOrders])

  const filtered = filter === 'all'
    ? orders
    : orders.filter(o => o.status === filter)

  const counts = orders.reduce((acc, o) => {
    acc[o.status] = (acc[o.status] ?? 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="space-y-4">
      {/* Filter pills */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'payment_window', 'paid', 'completed', 'expired', 'cancelled', 'disputed'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-full text-xs font-semibold capitalize transition
              ${filter === f
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}>
            {f === 'all' ? `All (${orders.length})` :
             f === 'payment_window' ? `Pending (${counts[f] ?? 0})` :
             f === 'expired' ? `Expired (${counts[f] ?? 0})` :
             `${f.charAt(0).toUpperCase() + f.slice(1)} (${counts[f] ?? 0})`}
          </button>
        ))}
      </div>

      {/* List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-7 w-7 animate-spin text-blue-500" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <ClipboardList className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-semibold">No orders yet</p>
          <p className="text-sm mt-1">Your P2P buy orders will appear here</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(o => {
            const tokenDisplay = o.token?.split('_')[0]
            return (
              <button key={o.id} onClick={() => navigate(`/p2p/orders/${o.id}`)}
                className="w-full bg-white rounded-xl border border-gray-200 px-4 py-3 flex items-center gap-4 hover:border-blue-300 hover:shadow-sm transition text-left">
                {/* Left: token + merchant */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-gray-900 text-sm">{tokenDisplay}</span>
                    {o.order_type === 'sell' && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-semibold">
                        SELL
                      </span>
                    )}
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_PILL[o.status] ?? 'bg-gray-100 text-gray-500'}`}>
                      {o.status === 'payment_window' ? 'Pending' : o.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5 truncate">
                    {(o.p2p_merchants as any)?.display_name ?? 'Merchant'} · #{o.order_number?.slice(-8)}
                  </p>
                </div>
                {/* Right: amounts */}
                <div className="text-right flex-shrink-0">
                  <p className="font-semibold text-sm text-blue-600">{o.token_amount?.toFixed(4)} {tokenDisplay}</p>
                  <p className="text-xs text-gray-400">{o.fiat_amount?.toLocaleString()} {o.fiat_currency}</p>
                </div>
                <ChevronRight className="h-4 w-4 text-gray-300 flex-shrink-0" />
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────
const PaymentsPage = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState<Tab>('p2p')
  const [showFund,  setShowFund]  = useState(false)
  const [showSend,  setShowSend]  = useState(false)

  useEffect(() => {
    const tab = searchParams.get('tab') as Tab | null
    if (tab && ['p2p', 'fund', 'send', 'orders'].includes(tab)) {
      setActiveTab(tab)
      if (tab === 'fund') setShowFund(true)
      if (tab === 'send') setShowSend(true)
    }
  }, [])

  const handleTabClick = (tab: Tab) => {
    setActiveTab(tab)
    setSearchParams({ tab })
    if (tab === 'fund') setShowFund(true)
    if (tab === 'send') setShowSend(true)
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
        <div className="max-w-5xl mx-auto">

          <div className="mb-6">
            <h1 className="text-2xl md:text-3xl font-bold text-white">Payments</h1>
            <p className="text-sm text-gray-400 mt-1">Buy, send, and manage crypto across all supported chains</p>
          </div>

          {/* Tab bar */}
          <div className="flex gap-1 mb-5 bg-gray-800/60 rounded-xl p-1.5 border border-gray-700 w-fit overflow-x-auto">
            {TABS.map(tab => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button key={tab.id} onClick={() => handleTabClick(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all whitespace-nowrap
                    ${isActive
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                      : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
                    }`}>
                  <Icon className="h-4 w-4" />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              )
            })}
          </div>

          <p className="text-sm text-gray-400 mb-5">{TAB_DESC[activeTab]}</p>

          {/* P2P */}
          {activeTab === 'p2p' && (
            <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
              <MerchantListings />
            </div>
          )}

          {/* Sell via P2P */}
          {activeTab === 'sell' && (
            <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
              <SellListings />
            </div>
          )}H

          {/* My Orders */}
          {activeTab === 'orders' && <OrderHistory />}

          {/* Fund */}
          {activeTab === 'fund' && (
            <div className="flex flex-col items-center justify-center py-16 gap-6">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500/20 to-indigo-500/20 border border-blue-500/30 flex items-center justify-center">
                <ArrowDownToLine className="h-10 w-10 text-blue-400" />
              </div>
              <div className="text-center">
                <h2 className="text-xl font-bold text-white mb-2">Fund Your Wallet</h2>
                <p className="text-gray-400 text-sm max-w-sm">Buy crypto instantly with your local currency. Smart provider routing for best rates.</p>
              </div>
              <div className="grid grid-cols-2 gap-3 text-center text-sm w-full max-w-xs">
                {[['< 30 sec','Settlement'],['~1–3.5%','Fee'],['13+','Currencies'],['6 chains','Chains']].map(([v, l], i) => (
                  <div key={i} className="bg-gray-800/50 rounded-xl p-3 border border-gray-700">
                    <div className="text-blue-400 font-bold">{v}</div>
                    <div className="text-gray-500 text-xs mt-0.5">{l}</div>
                  </div>
                ))}
              </div>
              <button onClick={() => setShowFund(true)}
                className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl transition-all flex items-center gap-2">
                <ArrowDownToLine className="h-5 w-5" /> Open Fund Wallet
              </button>
            </div>
          )}

          {/* Send */}
          {activeTab === 'send' && (
            <div className="flex flex-col items-center justify-center py-16 gap-6">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-green-500/20 to-emerald-500/20 border border-green-500/30 flex items-center justify-center">
                <ArrowUpRight className="h-10 w-10 text-green-400" />
              </div>
              <div className="text-center">
                <h2 className="text-xl font-bold text-white mb-2">Send Crypto</h2>
                <p className="text-gray-400 text-sm max-w-sm">Send any token to any wallet. Smart routing + QR code scanning supported.</p>
              </div>
              <div className="grid grid-cols-2 gap-3 text-center text-sm w-full max-w-xs">
                {[['0.4 sec','Fastest'],['< $0.01','Lowest fee'],['18+','Tokens'],['6 chains','Chains']].map(([v, l], i) => (
                  <div key={i} className="bg-gray-800/50 rounded-xl p-3 border border-gray-700">
                    <div className="text-green-400 font-bold">{v}</div>
                    <div className="text-gray-500 text-xs mt-0.5">{l}</div>
                  </div>
                ))}
              </div>
              <button onClick={() => setShowSend(true)}
                className="px-8 py-3 bg-green-600 hover:bg-green-700 text-white font-bold rounded-xl transition-all flex items-center gap-2">
                <ArrowUpRight className="h-5 w-5" /> Open Send Form
              </button>
            </div>
          )}

        </div>
      </div>

      <FundWalletModal open={showFund} onOpenChange={setShowFund} />
      <SendForm open={showSend} onOpenChange={setShowSend} />
    </div>
  )
}

export default PaymentsPage