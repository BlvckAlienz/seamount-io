// FILE: frontend/src/pages/AdminDashboard.tsx
// Full rebuild — real data only. Zero placeholders.
// Sections: KPIs · On-Ramp Monitor · Fee Treasury ·
//           Blockchain Txns · P2P Command Center · User Pipeline

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@/config/api'
import { useAuth } from '@/contexts/AuthContext'
import { supabase } from '@/lib/supabase'
import toast from 'react-hot-toast'
import {
  ArrowLeft, RefreshCw, AlertTriangle, CheckCircle,
  XCircle, Clock, Users, TrendingUp, DollarSign,
  Activity, ShoppingBag, Shield, ChevronDown,
  ChevronUp, ExternalLink, Loader2, BadgeCheck, Send
} from 'lucide-react'

// ─────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────
interface OnrampSummary {
  total_attempts: number
  completed: number
  pending_payment: number
  failed: number
  conversion_rate_pct: number
  total_fiat_initiated: number
  total_fiat_completed: number
  total_seamount_fees: number
}
interface FeeSummary {
  total_records: number
  collected: number
  pending: number
  failed: number
  collection_rate_pct: number
  by_chain: Record<string, number>
}
interface BlockchainSummary {
  total_transactions: number
  total_volume: number
  total_platform_fees: number
  by_chain: Record<string, number>
  by_asset: Record<string, number>
  by_status: Record<string, number>
}
interface UserSummary {
  total_users: number
  onboarding_complete: number
  wallets_created: number
  by_kyc_status: Record<string, number>
  by_account_type: Record<string, number>
}
interface P2PSummary {
  merchants: {
    total: number
    by_status: Record<string, number>
    pending_approval: { id: string; display_name: string; user_email: string; created_at: string }[]
    all: any[]
  }
  listings: { total: number; active: number }
  orders: { total: number; by_status: Record<string, number>; total_volume: number; recent: any[] }
}

interface AdminOrderModalProps {
  orderId: string | null
  onClose: () => void
}

function AdminOrderModal({ orderId, onClose }: AdminOrderModalProps) {
  const [data,       setData]       = useState<any>(null)
  const [loading,    setLoading]    = useState(false)
  const [msgText,    setMsgText]    = useState('')
  const [recipient,  setRecipient]  = useState<'buyer' | 'merchant' | 'both'>('buyer')
  const [sending,    setSending]    = useState(false)

  useEffect(() => {
    if (!orderId) return

    setLoading(true)
    apiClient.get(`/api/v1/admin/p2p/orders/${orderId}`)
      .then(r => setData(r.data))
      .catch(() => toast.error('Failed to load order'))
      .finally(() => setLoading(false))

    // Realtime — admin sees ALL messages regardless of visibility
    const ch = supabase
      .channel(`admin-msgs:${orderId}`)
      .on(
        'postgres_changes',
        {
          event:  'INSERT',
          schema: 'public',
          table:  'p2p_messages',
          filter: `order_id=eq.${orderId}`,
        },
        (p) => {
          // Append directly — no visibility filter for admin
          setData((prev: any) => {
            if (!prev) return prev
            return {
              ...prev,
              messages: [...(prev.messages || []), p.new]
            }
          })
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          console.log(`[Admin Realtime] Subscribed to msgs for order ${orderId}`)
        }
      })

    return () => { supabase.removeChannel(ch) }
  }, [orderId])

  const sendMessage = async () => {
    if (!msgText.trim() || !orderId) return
    setSending(true)
    try {
      await apiClient.post(`/api/v1/admin/p2p/orders/${orderId}/message`, {
        message: msgText.trim(),
        recipient
      })
      toast.success(`Message sent to ${recipient}`)
      setMsgText('')
      // No manual re-fetch needed — Realtime subscription above
      // delivers the new message instantly via postgres_changes INSERT
    } catch {
      toast.error('Failed to send message')
    } finally {
      setSending(false)
    }
  }

  if (!orderId) return null

  const order = data?.order
  const messages: any[] = data?.messages || []
  const audit: any[] = data?.audit_log || []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <h2 className="font-bold text-white text-base">
            🛡️ Admin Order View
            {order && <span className="ml-2 font-mono text-blue-400">#{order.order_number}</span>}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl leading-none">✕</button>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
          </div>
        ) : order ? (
          <div className="p-5 space-y-5">

            {/* Order summary */}
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                ['Status',   order.status],
                ['Token',    `${order.token_amount?.toFixed(4)} ${order.token?.split('_')[0]}`],
                ['Fiat',     `${order.fiat_amount?.toLocaleString()} ${order.fiat_currency}`],
                ['Buyer',    order.buyer?.email || order.buyer_id],
                ['Merchant', order.p2p_merchants?.display_name || '—'],
                ['Tx Hash',  order.release_tx_hash ? order.release_tx_hash.slice(0,16)+'...' : '—'],
                ['Chain Tx Status', order.blockchain_tx?.status || 'N/A'],
                ['Created',  new Date(order.created_at).toLocaleString()],
              ].map(([label, value]) => (
                <div key={String(label)} className="bg-gray-800/60 rounded-lg px-3 py-2">
                  <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
                  <div className="text-white text-sm font-medium mt-0.5 break-all">{String(value)}</div>
                </div>
              ))}
            </div>

            {/* ⚠️ Status mismatch warning */}
            {order.blockchain_tx && order.blockchain_tx.status === 'completed'
              && ['disputed', 'expired', 'cancelled'].includes(order.status) && (
              <div className="bg-red-900/20 border border-red-500/40 rounded-xl px-4 py-3 text-sm text-red-300">
                ⚠️ <strong>Status mismatch:</strong> blockchain_transactions shows{' '}
                <span className="font-mono">completed</span> but p2p_orders is{' '}
                <span className="font-mono text-red-400">{order.status}</span>.{' '}
                The on-chain transfer executed but the order was subsequently {order.status}.
                Trust <strong>p2p_orders.status</strong> as the business truth.
              </div>
            )}

            {/* Chat — split by recipient visibility */}
            <div className="bg-gray-800/50 rounded-xl border border-gray-700 overflow-hidden">
              <div className="px-4 py-2.5 border-b border-gray-700 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">Order Chat</h3>
                <span className="text-xs text-gray-500">
                  🔒 = private admin message | Buyer/Merchant see only their own
                </span>
              </div>
              <div className="max-h-52 overflow-y-auto p-3 space-y-2">
                {messages.map((msg: any) => {
                  const isAdminMsg  = msg.sender_role === 'admin'
                  const isSystem    = msg.is_system
                  const visLabel    = msg.visibility === 'buyer_admin'
                    ? '→ Buyer only 🔒'
                    : msg.visibility === 'merchant_admin'
                    ? '→ Merchant only 🔒'
                    : ''
                  return (
                    <div key={msg.id} className={`flex ${isSystem ? 'justify-center' : isAdminMsg ? 'justify-end' : 'justify-start'}`}>
                      {isSystem ? (
                        <span className="text-xs text-gray-400 bg-gray-900 px-3 py-1 rounded-full border border-gray-700 max-w-xs text-center">
                          {msg.message}
                        </span>
                      ) : (
                        <div className={`max-w-[75%] px-3 py-1.5 rounded-xl text-xs ${
                          isAdminMsg
                            ? 'bg-purple-700 text-white rounded-br-none'
                            : 'bg-gray-700 text-gray-100 rounded-bl-none'
                        }`}>
                          {msg.message}
                          {visLabel && <div className="text-[10px] text-purple-300 mt-0.5">{visLabel}</div>}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>

              {/* Admin send */}
              <div className="p-3 border-t border-gray-700 space-y-2">
                {/* Recipient selector */}
                <div className="flex gap-2">
                  {(['buyer', 'merchant', 'both'] as const).map(r => (
                    <button key={r} onClick={() => setRecipient(r)}
                      className={`px-3 py-1 rounded-full text-xs font-semibold capitalize transition ${
                        recipient === r
                          ? 'bg-purple-600 text-white'
                          : 'bg-gray-700 text-gray-400 hover:text-white'
                      }`}>
                      {r === 'both' ? 'Both parties' : r}
                    </button>
                  ))}
                  <span className="text-xs text-gray-500 ml-auto self-center">
                    {recipient === 'buyer' && '🔒 Merchant cannot see this'}
                    {recipient === 'merchant' && '🔒 Buyer cannot see this'}
                    {recipient === 'both' && 'Visible to all'}
                  </span>
                </div>
                <div className="flex gap-2">
                  <input
                    value={msgText}
                    onChange={e => setMsgText(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
                    placeholder={`Message to ${recipient}...`}
                    className="flex-1 text-sm px-3 py-2 rounded-lg border border-gray-600 bg-gray-900 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                  <button onClick={sendMessage} disabled={sending || !msgText.trim()}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-semibold disabled:opacity-50 flex items-center gap-1">
                    {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                    Send
                  </button>
                </div>
              </div>
            </div>

            {/* Audit log */}
            {audit.length > 0 && (
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Audit Trail</p>
                <div className="space-y-1">
                  {audit.map((a: any) => (
                    <div key={a.id} className="text-xs text-gray-400 flex gap-2">
                      <span className="text-gray-600">{new Date(a.created_at).toLocaleTimeString()}</span>
                      <span>{a.event_type}</span>
                      {a.prev_status && <><span className="text-gray-600">→</span><span className="text-yellow-400">{a.prev_status}</span></>}
                      <span className="text-gray-600">→</span>
                      <span className="text-green-400">{a.new_status}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-12">Order not found</p>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────
const KPI = ({
  label, value, sub, icon: Icon, color, alert
}: {
  label: string; value: string | number; sub?: string
  icon: any; color: string; alert?: boolean
}) => (
  <div className={`bg-gray-800/50 rounded-xl p-4 border ${alert ? 'border-red-500/40' : 'border-gray-700'}`}>
    <div className="flex items-center justify-between mb-2">
      <span className="text-xs text-gray-400 uppercase tracking-wide">{label}</span>
      <Icon className={`h-4 w-4 ${color}`} />
    </div>
    <div className={`text-2xl font-bold ${color}`}>{value}</div>
    {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
  </div>
)

const Section = ({ title, icon: Icon, children, defaultOpen = true }: {
  title: string; icon: any; children: React.ReactNode; defaultOpen?: boolean
}) => {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-gray-800/40 rounded-2xl border border-gray-700 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-800/60 transition"
      >
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Icon className="h-5 w-5 text-blue-400" />
          {title}
        </h2>
        {open ? <ChevronUp className="h-4 w-4 text-gray-500" /> : <ChevronDown className="h-4 w-4 text-gray-500" />}
      </button>
      {open && <div className="px-5 pb-5">{children}</div>}
    </div>
  )
}

const StatusPill = ({ status }: { status: string }) => {
  const map: Record<string, string> = {
    completed: 'bg-green-500/20 text-green-400',
    collected: 'bg-green-500/20 text-green-400',
    approved:  'bg-green-500/20 text-green-400',
    success:   'bg-green-500/20 text-green-400',
    pending_payment: 'bg-yellow-500/20 text-yellow-400',
    pending:   'bg-yellow-500/20 text-yellow-400',
    failed:    'bg-red-500/20 text-red-400',
    cancelled: 'bg-red-500/20 text-red-400',
    disputed:  'bg-red-500/20 text-red-400',
    rejected:  'bg-red-500/20 text-red-400',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${map[status] ?? 'bg-gray-700 text-gray-400'}`}>
      {status}
    </span>
  )
}

const BreakdownBar = ({ data, colorClass = 'bg-blue-500' }: {
  data: Record<string, number>; colorClass?: string
}) => {
  const total = Object.values(data).reduce((a, b) => a + b, 0)
  if (total === 0) return <span className="text-xs text-gray-500">No data</span>
  return (
    <div className="space-y-1.5">
      {Object.entries(data).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
        <div key={k} className="flex items-center gap-2">
          <span className="text-xs text-gray-400 w-28 truncate">{k}</span>
          <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${colorClass} rounded-full`}
              style={{ width: `${(v / total) * 100}%` }}
            />
          </div>
          <span className="text-xs text-gray-300 w-12 text-right font-mono">{v}</span>
        </div>
      ))}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────
export const AdminDashboard = () => {
  const { userProfile } = useAuth()
  const navigate = useNavigate()

  const [loading,      setLoading]      = useState(true)
  const [refreshing,   setRefreshing]   = useState(false)
  const [onramp,       setOnramp]       = useState<any>(null)
  const [fees,         setFees]         = useState<any>(null)
  const [blockchain,   setBlockchain]   = useState<any>(null)
  const [users,        setUsers]        = useState<any>(null)
  const [p2p,          setP2p]          = useState<any>(null)
  const [reviewingId,  setReviewingId]  = useState<string | null>(null)
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null)

  // Guard
  useEffect(() => {
    if (userProfile && !userProfile.is_admin) {
      toast.error('Admin access required')
      navigate('/dashboard')
    }
  }, [userProfile, navigate])

  const fetchAll = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    try {
      const [onrampRes, feesRes, blockRes, usersRes, p2pRes] = await Promise.all([
        apiClient.get('/api/v1/admin/onramp/summary?days=30'),
        apiClient.get('/api/v1/admin/fees/treasury'),
        apiClient.get('/api/v1/admin/blockchain/summary?days=30'),
        apiClient.get('/api/v1/admin/users/pipeline'),
        apiClient.get('/api/v1/admin/p2p/overview'),
      ])
      if (onrampRes.data?.success)  setOnramp(onrampRes.data)
      if (feesRes.data?.success)    setFees(feesRes.data)
      if (blockRes.data?.success)   setBlockchain(blockRes.data)
      if (usersRes.data?.success)   setUsers(usersRes.data)
      if (p2pRes.data?.success)     setP2p(p2pRes.data)
    } catch (err) {
      toast.error('Failed to load dashboard data')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  // Auto-refresh every 60s
  useEffect(() => {
    const t = setInterval(() => fetchAll(true), 60000)
    return () => clearInterval(t)
  }, [fetchAll])

  const handleMerchantReview = async (merchantId: string, action: 'approved' | 'rejected') => {
    setReviewingId(merchantId)
    try {
      await apiClient.patch(`/api/v1/admin/p2p/merchants/${merchantId}/review`, { action })
      toast.success(`Merchant ${action}`)
      fetchAll(true)
    } catch {
      toast.error('Review action failed')
    } finally {
      setReviewingId(null)
    }
  }

  if (loading) return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin text-blue-500 mx-auto mb-3" />
        <p className="text-gray-400 text-sm">Loading platform data...</p>
      </div>
    </div>
  )

  const os: OnrampSummary     = onramp?.summary  || {}
  const fs: FeeSummary        = fees?.summary    || {}
  const bs: BlockchainSummary = blockchain?.summary || {}
  const us: UserSummary       = users?.summary   || {}

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-4 md:p-6">
      <div className="max-w-7xl mx-auto space-y-5">

        {/* ── Header ── */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/dashboard')}
              className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-400 transition">
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-white">Platform Command Center</h1>
              <p className="text-xs text-gray-500 mt-0.5">
                Live data · Auto-refreshes every 60s
                {refreshing && <span className="ml-2 text-blue-400">↻ refreshing</span>}
              </p>
            </div>
          </div>
          <button onClick={() => fetchAll(true)} disabled={refreshing}
            className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm font-medium transition">
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* ── TOP KPIs ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <KPI label="Total Users"      value={us.total_users ?? '—'}    sub={`${us.wallets_created ?? 0} wallets ready`} icon={Users}      color="text-blue-400" />
          <KPI label="On-ramp Attempts" value={os.total_attempts ?? '—'} sub={`${os.conversion_rate_pct ?? 0}% converted`}  icon={TrendingUp}  color="text-green-400" alert={(os.pending_payment ?? 0) > 5} />
          <KPI label="Stuck Payments"   value={onramp?.stuck_count ?? '—'} sub="pending > 2h"                               icon={AlertTriangle} color="text-red-400" alert={(onramp?.stuck_count ?? 0) > 0} />
          <KPI label="Fees Collected"   value={`$${(fs.collected ?? 0).toFixed(4)}`} sub={`${fs.collection_rate_pct ?? 0}% rate`} icon={DollarSign} color="text-yellow-400" />
          <KPI label="Blockchain Txns"  value={bs.total_transactions ?? '—'} sub={`$${(bs.total_volume ?? 0).toFixed(2)} vol`} icon={Activity}   color="text-purple-400" />
          <KPI label="P2P Merchants"    value={p2p?.merchants?.total ?? '—'} sub={`${p2p?.merchants?.by_status?.pending ?? 0} pending review`} icon={BadgeCheck} color="text-orange-400" alert={(p2p?.merchants?.by_status?.pending ?? 0) > 0} />
        </div>

        {/* ── ON-RAMP MONITOR ── */}
        <Section title="On-Ramp Monitor — Flutterwave" icon={TrendingUp}>
          {/* Funnel */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            {[
              { label: 'Initiated',       value: os.total_attempts,      color: 'text-blue-400'   },
              { label: 'Completed',        value: os.completed,           color: 'text-green-400'  },
              { label: 'Pending Payment',  value: os.pending_payment,     color: 'text-yellow-400' },
              { label: 'Failed',           value: os.failed,              color: 'text-red-400'    },
            ].map(s => (
              <div key={s.label} className="bg-gray-900/50 rounded-xl p-3 border border-gray-700 text-center">
                <div className={`text-xl font-bold ${s.color}`}>{s.value ?? '—'}</div>
                <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>

          <div className="grid md:grid-cols-2 gap-5 mb-5">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">By Status</p>
              <BreakdownBar data={onramp?.by_status ?? {}} colorClass="bg-blue-500" />
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">By Currency</p>
              <BreakdownBar data={onramp?.by_currency ?? {}} colorClass="bg-green-500" />
            </div>
          </div>

          {/* Stuck payments */}
          {(onramp?.stuck_payments?.length ?? 0) > 0 && (
            <div className="mb-4">
              <p className="text-xs font-bold text-red-400 uppercase tracking-wide mb-2">
                ⚠️ Stuck Payments ({onramp.stuck_count}) — Pending &gt; 2 Hours
              </p>
              <div className="space-y-2">
                {onramp.stuck_payments.slice(0, 5).map((r: any) => (
                  <div key={r.id} className="flex items-center gap-3 bg-red-900/10 border border-red-500/20 rounded-lg px-3 py-2 text-sm">
                    <AlertTriangle className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
                    <span className="text-gray-300 flex-1 truncate">{r.user_email}</span>
                    <span className="text-white font-mono">{r.amount_fiat} {r.currency}</span>
                    <span className="text-gray-500 text-xs">{new Date(r.created_at).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent feed */}
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Recent Attempts</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 border-b border-gray-700">
                  <th className="text-left pb-2 pr-4">User</th>
                  <th className="text-left pb-2 pr-4">Amount</th>
                  <th className="text-left pb-2 pr-4">Asset</th>
                  <th className="text-left pb-2 pr-4">Provider</th>
                  <th className="text-left pb-2 pr-4">Status</th>
                  <th className="text-left pb-2">Date</th>
                </tr>
              </thead>
              <tbody>
                {(onramp?.recent ?? []).map((r: any) => (
                  <tr key={r.id} className="border-b border-gray-800 hover:bg-gray-800/30">
                    <td className="py-2 pr-4 text-gray-300 truncate max-w-[140px]">{r.user_email}</td>
                    <td className="py-2 pr-4 text-white font-mono">{r.amount_fiat} {r.currency}</td>
                    <td className="py-2 pr-4 text-gray-400">{r.crypto_asset}</td>
                    <td className="py-2 pr-4 text-gray-400">{r.provider}</td>
                    <td className="py-2 pr-4"><StatusPill status={r.status} /></td>
                    <td className="py-2 text-gray-500 text-xs">{new Date(r.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        {/* ── FEE TREASURY ── */}
        <Section title="Fee Treasury" icon={DollarSign}>
          <div className="grid grid-cols-3 gap-3 mb-4">
            {[
              { label: 'Collected', value: `$${(fs.collected ?? 0).toFixed(6)}`, color: 'text-green-400' },
              { label: 'Pending',   value: `$${(fs.pending   ?? 0).toFixed(6)}`, color: 'text-yellow-400' },
              { label: 'Failed',    value: `$${(fs.failed    ?? 0).toFixed(6)}`, color: 'text-red-400' },
            ].map(s => (
              <div key={s.label} className="bg-gray-900/50 rounded-xl p-3 border border-gray-700 text-center">
                <div className={`text-lg font-bold font-mono ${s.color}`}>{s.value}</div>
                <div className="text-xs text-gray-500">{s.label}</div>
              </div>
            ))}
          </div>
          <div className="mb-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">By Chain</p>
            <BreakdownBar data={fs.by_chain ?? {}} colorClass="bg-yellow-500" />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 border-b border-gray-700">
                  <th className="text-left pb-2 pr-3">Chain</th>
                  <th className="text-left pb-2 pr-3">Asset</th>
                  <th className="text-left pb-2 pr-3">Amount</th>
                  <th className="text-left pb-2 pr-3">Status</th>
                  <th className="text-left pb-2">Collected Tx</th>
                </tr>
              </thead>
              <tbody>
                {(fees?.records ?? []).map((r: any) => (
                  <tr key={r.id} className="border-b border-gray-800 hover:bg-gray-800/30">
                    <td className="py-2 pr-3 text-gray-300">{r.chain}</td>
                    <td className="py-2 pr-3 text-gray-300">{r.asset}</td>
                    <td className="py-2 pr-3 text-white font-mono">{parseFloat(r.fee_amount).toFixed(6)}</td>
                    <td className="py-2 pr-3"><StatusPill status={r.status} /></td>
                    <td className="py-2 text-gray-500 font-mono text-xs truncate max-w-[100px]">
                      {r.collected_tx_id ? r.collected_tx_id.slice(0, 12) + '...' : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        {/* ── BLOCKCHAIN TRANSACTIONS ── */}
        <Section title="Blockchain Transactions" icon={Activity}>
          <div className="grid md:grid-cols-2 gap-5 mb-4">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">By Chain</p>
              <BreakdownBar data={bs.by_chain ?? {}} colorClass="bg-purple-500" />
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">By Asset</p>
              <BreakdownBar data={bs.by_asset ?? {}} colorClass="bg-indigo-500" />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 border-b border-gray-700">
                  <th className="text-left pb-2 pr-3">User</th>
                  <th className="text-left pb-2 pr-3">Type</th>
                  <th className="text-left pb-2 pr-3">Amount</th>
                  <th className="text-left pb-2 pr-3">Chain/Asset</th>
                  <th className="text-left pb-2 pr-3">Status</th>
                  <th className="text-left pb-2">Tx Hash</th>
                </tr>
              </thead>
              <tbody>
                {(blockchain?.recent ?? []).map((r: any) => (
                  <tr key={r.id} className="border-b border-gray-800 hover:bg-gray-800/30">
                    <td className="py-2 pr-3 text-gray-300 truncate max-w-[130px]">{r.user_email}</td>
                    <td className="py-2 pr-3 text-gray-400">{r.transaction_type}</td>
                    <td className="py-2 pr-3 text-white font-mono">{parseFloat(r.amount).toFixed(4)} {r.asset?.split('_')[0]}</td>
                    <td className="py-2 pr-3 text-gray-400">{r.chain}</td>
                    <td className="py-2 pr-3"><StatusPill status={r.status} /></td>
                    <td className="py-2 text-blue-400 font-mono text-xs">
                      {r.txn_hash ? (
                        <span title={r.txn_hash}>{r.txn_hash.slice(0, 10)}...</span>
                      ) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        {/* ── P2P COMMAND CENTER ── */}
        <Section title="P2P Command Center" icon={ShoppingBag}>
          <div className="grid grid-cols-3 gap-3 mb-5">
            {[
              { label: 'Total Merchants', value: p2p?.merchants?.total ?? 0 },
              { label: 'Active Listings', value: p2p?.listings?.active ?? 0 },
              { label: 'Total Orders',    value: p2p?.orders?.total ?? 0    },
            ].map(s => (
              <div key={s.label} className="bg-gray-900/50 rounded-xl p-3 border border-gray-700 text-center">
                <div className="text-xl font-bold text-white">{s.value}</div>
                <div className="text-xs text-gray-500">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Merchant Approval Queue */}
          {(p2p?.merchants?.pending_approval?.length ?? 0) > 0 && (
            <div className="mb-5">
              <p className="text-xs font-bold text-orange-400 uppercase tracking-wide mb-2">
                🔔 Pending Merchant Applications ({p2p.merchants.pending_approval.length})
              </p>
              <div className="space-y-2">
                {p2p.merchants.pending_approval.map((m: any) => (
                  <div key={m.id}
                    className="flex items-center gap-3 bg-orange-900/10 border border-orange-500/20 rounded-xl px-4 py-3">
                    <div className="flex-1">
                      <p className="text-white font-semibold text-sm">{m.display_name}</p>
                      <p className="text-gray-400 text-xs">{m.user_email}</p>
                      <p className="text-gray-600 text-xs">Applied {new Date(m.created_at).toLocaleDateString()}</p>
                    </div>
                    <button
                      onClick={() => handleMerchantReview(m.id, 'approved')}
                      disabled={reviewingId === m.id}
                      className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs font-bold rounded-lg transition gap-1 flex items-center disabled:opacity-50"
                    >
                      {reviewingId === m.id
                        ? <Loader2 className="h-3 w-3 animate-spin" />
                        : <CheckCircle className="h-3 w-3" />
                      }
                      Approve
                    </button>
                    <button
                      onClick={() => handleMerchantReview(m.id, 'rejected')}
                      disabled={reviewingId === m.id}
                      className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-lg transition gap-1 flex items-center disabled:opacity-50"
                    >
                      <XCircle className="h-3 w-3" /> Reject
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2 mt-4">Recent Orders</p>
            <div className="space-y-1 mb-5">
              {(p2p?.orders?.recent ?? []).map((o: any) => (
                <button
                  key={o.id}
                  onClick={() => setSelectedOrderId(o.id)}
                  className="w-full flex items-center gap-3 bg-gray-900/40 rounded-xl px-4 py-2.5 border border-gray-700 hover:border-purple-500/40 transition text-left"
                >
                  <span className="font-mono text-xs text-gray-400">#{String(o.id).slice(-8)}</span>
                  <span className="text-white text-xs font-medium flex-1">
                    {o.token?.split('_')[0]} — {o.token_amount?.toFixed(4)}
                  </span>
                  <StatusPill status={o.status} />
                  <span className="text-xs text-gray-500">{new Date(o.created_at).toLocaleDateString()}</span>
                  <ExternalLink className="h-3.5 w-3.5 text-purple-400" />
                </button>
              ))}
            </div>
            
          {/* All merchants */}
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">All Merchants</p>
          <div className="space-y-2">
            {(p2p?.merchants?.all ?? []).map((m: any) => (
              <div key={m.id}
                className="flex items-center gap-3 bg-gray-900/40 rounded-xl px-4 py-3 border border-gray-700">
                <div className="flex-1">
                  <span className="text-white font-medium text-sm">{m.display_name}</span>
                </div>
                <StatusPill status={m.status} />
                <span className={`text-xs ${m.is_online ? 'text-green-400' : 'text-gray-500'}`}>
                  {m.is_online ? '● Online' : '○ Offline'}
                </span>
                <span className="text-xs text-gray-500">{m.total_orders} orders</span>
                <span className="text-xs text-gray-500">{parseFloat(m.completion_rate).toFixed(0)}% completion</span>
              </div>
            ))}
          </div>
        </Section>

        {/* ── USER PIPELINE ── */}
        <Section title="User Pipeline" icon={Users}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            {[
              { label: 'Total Users',          value: us.total_users        },
              { label: 'Onboarding Complete',  value: us.onboarding_complete },
              { label: 'Wallets Ready',         value: us.wallets_created    },
              { label: 'Wallets Pending',       value: us.wallets_pending    },
            ].map(s => (
              <div key={s.label} className="bg-gray-900/50 rounded-xl p-3 border border-gray-700 text-center">
                <div className="text-xl font-bold text-white">{s.value ?? '—'}</div>
                <div className="text-xs text-gray-500">{s.label}</div>
              </div>
            ))}
          </div>
          <div className="grid md:grid-cols-2 gap-5 mb-5">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">KYC Status</p>
              <BreakdownBar data={us.by_kyc_status ?? {}} colorClass="bg-blue-500" />
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Account Type</p>
              <BreakdownBar data={us.by_account_type ?? {}} colorClass="bg-teal-500" />
            </div>
          </div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Recent Signups</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 border-b border-gray-700">
                  <th className="text-left pb-2 pr-3">Name</th>
                  <th className="text-left pb-2 pr-3">Email</th>
                  <th className="text-left pb-2 pr-3">Country</th>
                  <th className="text-left pb-2 pr-3">KYC</th>
                  <th className="text-left pb-2 pr-3">Wallet</th>
                  <th className="text-left pb-2">Joined</th>
                </tr>
              </thead>
              <tbody>
                {(users?.recent_signups ?? []).map((u: any) => (
                  <tr key={u.user_id} className="border-b border-gray-800 hover:bg-gray-800/30">
                    <td className="py-2 pr-3 text-white">{u.name || '—'}</td>
                    <td className="py-2 pr-3 text-gray-400 truncate max-w-[150px]">{u.email}</td>
                    <td className="py-2 pr-3 text-gray-400">{u.country ?? '—'}</td>
                    <td className="py-2 pr-3"><StatusPill status={u.kyc_status ?? 'unknown'} /></td>
                    <td className="py-2 pr-3">
                      <span className={`text-xs ${u.wallet_ready ? 'text-green-400' : 'text-gray-500'}`}>
                        {u.wallet_ready ? '✓ Ready' : '✗ Pending'}
                      </span>
                    </td>
                    <td className="py-2 text-gray-500 text-xs">
                      {new Date(u.joined).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

      </div>
      <AdminOrderModal
        orderId={selectedOrderId}
        onClose={() => setSelectedOrderId(null)}
      />
    </div>
  )
}

export default AdminDashboard