// FILE: frontend/src/pages/P2POrderPage.tsx
// Buyer view: timer, payment details, receipt upload, chat
// Merchant view: order summary, receipt preview, release button, chat

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { supabase } from '@/lib/supabase'
import { apiClient } from '@/config/api'
import { useAuth } from '@/contexts/AuthContext'
import toast from 'react-hot-toast'
import {
  Clock, CheckCircle, XCircle, Upload, Send,
  ShieldCheck, AlertCircle, Loader2, Copy,
  ArrowLeft, RefreshCw, Eye, ChevronDown, ChevronUp
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'

// ── TYPES ─────────────────────────────────────────────────────
interface Order {
  id: string
  order_number: string
  token: string
  fiat_currency: string
  fiat_amount: number
  token_amount: number
  price_per_token: number
  payment_method: string
  status: string
  payment_deadline: string
  payment_receipt_url: string | null
  release_tx_hash: string | null
  platform_fee_bps: number
  buyer_id: string
  merchant_id: string
  created_at: string
  order_type: 'buy' | 'sell'
  seller_payout_method: string | null
  seller_payout_details: Record<string, string> | null
  token_tx_hash: string | null
  fiat_proof_url: string | null
  p2p_merchants: {
    id: string
    display_name: string
    verified: boolean
    avg_release_time_mins: number
    user_id: string
  }
  // merchant_receive_address comes from p2p_listings join
  p2p_listings: {
    payment_details: Record<string, any>
    merchant_receive_address?: string
  }
}

interface Message {
  id: string
  sender_id: string | null
  message: string
  is_system: boolean
  created_at: string
  visibility: 'all' | 'buyer_admin' | 'merchant_admin' | 'admin_only'
  sender_role: 'user' | 'system' | 'admin'
}

// ── STATUS CONFIG — separate desc for buyer vs merchant ───────
const STATUS_CFG: Record<string, {
  label: string; color: string
  buyerDesc: string; merchantDesc: string
  sellerDesc?: string; merchantSellDesc?: string
}> = {
  payment_window: {
    label: 'Awaiting Payment',
    color: 'bg-yellow-500/20 text-yellow-800 dark:text-yellow-300 border-yellow-400 dark:border-yellow-500/40',
    buyerDesc:       'Complete your payment before the timer expires',
    merchantDesc:    'Waiting for buyer to make payment and upload receipt',
    sellerDesc:      'Send your tokens to the merchant\'s wallet address below before the timer expires',
    merchantSellDesc:'Waiting for seller to send tokens to your wallet',
  },
  paid: {
    label: 'Tokens Sent',
    color: 'bg-blue-500/20 text-blue-800 dark:text-blue-300 border-blue-400 dark:border-blue-500/40',
    buyerDesc:       'Waiting for merchant to verify and release tokens',
    merchantDesc:    'Buyer has paid — verify receipt and release tokens',
    sellerDesc:      'Tokens submitted — waiting for merchant to verify on-chain and release fiat',
    merchantSellDesc:'Seller claims tokens sent — verify on block explorer then release fiat',
  },
  confirming: {
    label: 'Releasing',
    color: 'bg-purple-500/20 text-purple-800 dark:text-purple-300 border-purple-400 dark:border-purple-500/40',
    buyerDesc:       'Merchant confirmed. Tokens are being released to your wallet...',
    merchantDesc:    'Token release in progress...',
    sellerDesc:      'Merchant has sent fiat to your account — confirm receipt below',
    merchantSellDesc:'Fiat sent — waiting for seller to confirm receipt',
  },
  completed: {
    label: 'Completed',
    color: 'bg-green-500/20 text-green-800 dark:text-green-300 border-green-400 dark:border-green-500/40',
    buyerDesc:       'Tokens have been released to your wallet',
    merchantDesc:    'Order fulfilled. Tokens released successfully.',
    sellerDesc:      'Fiat received. Order completed!',
    merchantSellDesc:'Order fulfilled. Tokens received, fiat sent.',
  },
  cancelled: {
    label: 'Cancelled',
    color: 'bg-gray-200 dark:bg-gray-700/50 text-gray-600 dark:text-gray-400 border-gray-300 dark:border-gray-600',
    buyerDesc:    'This order has been cancelled',
    merchantDesc: 'This order was cancelled',
    sellerDesc:   'This order was cancelled',
    merchantSellDesc: 'This order was cancelled',
  },
  expired: {
    label: 'Expired',
    color: 'bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 border-orange-300 dark:border-orange-500/40',
    buyerDesc:    'Payment window elapsed — order expired',
    merchantDesc: 'Buyer did not pay in time. Order expired.',
    sellerDesc:   'You did not send tokens in time. Order expired.',
    merchantSellDesc: 'Seller did not send tokens in time. Order expired.',
  },
  disputed: {
    label: 'Disputed',
    color: 'bg-red-500/20 text-red-800 dark:text-red-300 border-red-400 dark:border-red-500/40',
    buyerDesc:    'Under review by Seamount support',
    merchantDesc: 'Under review by Seamount support',
    sellerDesc:   'Under review by Seamount support',
    merchantSellDesc: 'Under review by Seamount support',
  },
}

// ── Flatten nested payment_details ────────────────────────────
function flattenPaymentDetails(details: Record<string, any>): { key: string; value: string }[] {
  const rows: { key: string; value: string }[] = []
  for (const [method, val] of Object.entries(details ?? {})) {
    if (val && typeof val === 'object') {
      for (const [k, v] of Object.entries(val)) {
        rows.push({ key: k.replace(/_/g, ' '), value: String(v) })
      }
    } else {
      rows.push({ key: method, value: String(val) })
    }
  }
  return rows
}

// ── SHARED CHAT ───────────────────────────────────────────────
function ChatPanel({
  messages, userId, chatMsg, setChatMsg,
  onSend, sending, chatRef, disabled
}: {
  messages: Message[]
  userId: string
  chatMsg: string
  setChatMsg: (v: string) => void
  onSend: () => void
  sending: boolean
  chatRef: React.RefObject<HTMLDivElement>
  disabled: boolean
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
      <div className="px-4 py-2.5 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between gap-2">
        <h3 className="font-semibold text-sm text-gray-900 dark:text-white">Order Chat</h3>
        <span className="text-xs text-gray-400 dark:text-gray-500 flex items-center gap-1">
          <RefreshCw className="h-3 w-3" />
          Hit refresh above to see new messages
        </span>
      </div>
      <div className="overflow-y-auto max-h-60 p-3 space-y-2">
        {messages.length === 0 && (
          <p className="text-center text-xs text-gray-400 py-4">No messages yet</p>
        )}
        {messages.map(msg => (
          <div key={msg.id}
            className={`flex ${msg.is_system ? 'justify-center' : msg.sender_id === userId ? 'justify-end' : 'justify-start'}`}>
            {msg.is_system ? (
              <span className="text-xs text-gray-400 bg-gray-50 dark:bg-gray-900 px-3 py-1.5 rounded-full border border-gray-200 dark:border-gray-700 max-w-xs text-center">
                {msg.message}
              </span>
            ) : (
              <div className={`max-w-[75%] px-3 py-1.5 rounded-xl text-sm ${
                msg.sender_id === userId
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded-bl-none'
              }`}>
                {msg.message}
              </div>
            )}
          </div>
        ))}
        <div ref={chatRef} />
      </div>
      {!disabled && (
        <div className="p-3 border-t border-gray-100 dark:border-gray-700 flex gap-2">
          <input
            type="text"
            value={chatMsg}
            onChange={e => setChatMsg(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend() }
            }}
            placeholder="Type a message..."
            className="flex-1 text-sm px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 dark:text-white"
          />
          <Button size="sm" onClick={onSend} disabled={sending || !chatMsg.trim()}
            className="px-3 bg-blue-600 hover:bg-blue-700 text-white">
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      )}
    </div>
  )
}

// ── MAIN COMPONENT ────────────────────────────────────────────
export default function P2POrderPage() {
  const { id }   = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [order,        setOrder]        = useState<Order | null>(null)
  const [messages,     setMessages]     = useState<Message[]>([])
  const [timeLeft,     setTimeLeft]     = useState(0)
  const [loading,      setLoading]      = useState(true)
  const [uploading,    setUploading]    = useState(false)
  const [releasing,    setReleasing]    = useState(false)
  const [chatMsg,      setChatMsg]      = useState('')
  const [sendingChat,  setSendingChat]  = useState(false)
  const [error,        setError]        = useState<string | null>(null)
  const [refreshing,   setRefreshing]   = useState(false)
  const [showReceipt,  setShowReceipt]  = useState(false)      // for merchant receipt toggle

  const fileRef    = useRef<HTMLInputElement>(null)
  const chatRef    = useRef<HTMLDivElement>(null)
  const timerRef   = useRef<ReturnType<typeof setInterval> | null>(null)
  const expireCheckRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Tracks which visibility values this user may see.
  // Using a ref avoids adding it to Realtime useEffect deps
  // (which would cause channel teardown/re-subscribe on every order load).
  const allowedVisRef = useRef<string[]>(['all'])

  // Derived values
  const isBuyer    = order?.buyer_id === user?.id
  const isMerchant = order?.p2p_merchants?.user_id === user?.id
  const tokenDisplay = (order?.token ?? '').split('_')[0]
  const statusCfg  = order ? (STATUS_CFG[order.status] ?? STATUS_CFG.cancelled) : null
  const paymentRows = flattenPaymentDetails(order?.p2p_listings?.payment_details ?? {})
  const platformFee = order ? (order.token_amount * order.platform_fee_bps) / 10000 : 0

  // ── Data fetching ────────────────────────────────────────────
  const fetchOrder = useCallback(async () => {
    if (!id) return
    try {
      const { data, error: e } = await supabase
        .from('p2p_orders')
        .select(`*, p2p_merchants(id,display_name,verified,avg_release_time_mins,user_id), p2p_listings(payment_details)`)
        .eq('id', id)
        .single()
      if (e) throw e
      setOrder(data as Order)
    } catch (e: any) { setError(e.message) }
    finally { setLoading(false) }
  }, [id])

  // Returns true if this user is allowed to see the message
  const canSeeMessage = useCallback((msg: Partial<Message>): boolean => {
    const v = msg.visibility ?? 'all'
    if (v === 'all')             return true
    if (v === 'admin_only')      return false
    if (v === 'buyer_admin')     return isBuyer    // only buyer + admin
    if (v === 'merchant_admin')  return isMerchant // only merchant + admin
    return true
  }, [isBuyer, isMerchant])

  const fetchMessages = useCallback(async () => {
    if (!id) return
    const { data } = await supabase
      .from('p2p_messages')
      .select('*')
      .eq('order_id', id)
      .in('visibility', allowedVisRef.current)  // DB-level filter — primary enforcement
      .order('created_at', { ascending: true })
    if (data) setMessages(data as Message[])
  }, [id])
  // ↑ NO canSeeMessage / isBuyer / isMerchant in deps.
  //   allowedVisRef is a ref — reading it never triggers re-render.

  const refresh = useCallback(async () => {
    setRefreshing(true)
    await fetchOrder()
    await fetchMessages()
    setRefreshing(false)
  }, [fetchOrder, fetchMessages])

  // Initial load
  useEffect(() => { fetchOrder(); fetchMessages() }, [fetchOrder, fetchMessages])

  // Keep the visibility ref up to date whenever order loads.
  // No re-render side-effects — just a ref write.
  useEffect(() => {
    if (!order) return

    // 1. Update the ref with the correct visibility for this user
    if (isBuyer)         allowedVisRef.current = ['all', 'buyer_admin']
    else if (isMerchant) allowedVisRef.current = ['all', 'merchant_admin']
    else                 allowedVisRef.current = ['all']

    // 2. Re-fetch messages now that the ref has the correct visibility.
    //    The initial fetchMessages() fired before order loaded so it
    //    only queried visibility='all' — this corrects that.
    fetchMessages()
  }, [isBuyer, isMerchant, order?.id, fetchMessages])

  // Realtime order updates — self-healing on channel error
  useEffect(() => {
    if (!id) return
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null

    const ch = supabase.channel(`order:${id}`)
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'p2p_orders', filter: `id=eq.${id}` },
        (p) => {
          console.log('[Realtime] p2p_orders UPDATE:', p.new)
          setOrder(prev => prev ? { ...prev, ...p.new } : prev)
        }
      )
      .subscribe((status, err) => {
        if (status === 'SUBSCRIBED') {
          console.log(`[Realtime] Subscribed to order:${id}`)
        }
        if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          console.warn(`[Realtime] Channel error order:${id}`, err)
          // Self-heal: re-subscribe after 5s
          reconnectTimer = setTimeout(() => {
            console.log(`[Realtime] Reconnecting order:${id}`)
            ch.subscribe()
          }, 5000)
        }
      })

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      supabase.removeChannel(ch)
    }
  }, [id])

  // Realtime messages — ONLY depends on `id`.
  // allowedVisRef is a ref so reading it inside the callback is always
  // fresh without being in the dependency array.
  // This means the channel is set up ONCE per order and never torn down
  // due to role changes — fixing the "messages don't drop" bug.
  useEffect(() => {
    if (!id) return
    const ch = supabase
      .channel(`msgs:${id}`)
      .on(
        'postgres_changes',
        {
          event:  'INSERT',
          schema: 'public',
          table:  'p2p_messages',
          filter: `order_id=eq.${id}`,
        },
        (p) => {
          const msg = p.new as Message
          const v = msg.visibility ?? 'all'

          // Visibility gate — ref always has latest role values
          if (!allowedVisRef.current.includes(v)) return

          setMessages(prev => {
            // Deduplicate (Realtime can fire twice on flaky connections)
            if (prev.some(m => m.id === msg.id)) return prev
            return [...prev, msg]
          })
        }
      )
      .subscribe((status) => {
        if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          console.warn(`[Realtime] msgs:${id} error — resubscribing in 3s`)
          setTimeout(() => ch.subscribe(), 3000)
        }
      })

    return () => { supabase.removeChannel(ch) }
  }, [id])  // ← id ONLY. Stable for the life of the order page.

  // Timer for payment window
  useEffect(() => {
    if (!order?.payment_deadline || order.status !== 'payment_window') {
      if (timerRef.current) clearInterval(timerRef.current)
      return
    }
    const tick = () => {
      const rem = Math.max(0, Math.floor(
        (new Date(order.payment_deadline).getTime() - Date.now()) / 1000
      ))
      setTimeLeft(rem)
      if (rem === 0) {
        clearInterval(timerRef.current!)
        fetchOrder()  // immediate

        // Worker may take a few seconds to process the expiry job.
        // Poll again at +3s and +8s to catch the DB update.
        expireCheckRef.current = setTimeout(() => {
          fetchOrder()
          expireCheckRef.current = setTimeout(() => fetchOrder(), 5000)
        }, 3000)
      }
    }
    tick()
    timerRef.current = setInterval(tick, 1000)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      if (expireCheckRef.current) clearTimeout(expireCheckRef.current)
    }
  }, [order?.payment_deadline, order?.status, fetchOrder])

  // Scroll chat to bottom on new messages
  useEffect(() => {
    chatRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Helpers ──────────────────────────────────────────────────
  const formatTime = (s: number) =>
    `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`

  const copy = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    toast.success(`${label} copied!`)
  }

  // ── Receipt upload ───────────────────────────────────────────
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file || !id) return
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('order_id', id)
      const res = await apiClient.post('/api/p2p/orders/receipt-upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (res.data?.success) { toast.success('Receipt uploaded!'); fetchOrder() }
      else throw new Error(res.data?.detail ?? 'Upload failed')
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? e.message)
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  // ── Release tokens ───────────────────────────────────────────
  const handleRelease = async () => {
    if (!id) return; setReleasing(true)
    try {
      const res = await apiClient.patch(`/api/p2p/orders/${id}/release`)
      if (res.data?.success) { toast.success('Tokens released!'); fetchOrder() }
      else throw new Error(res.data?.detail ?? 'Release failed')
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? e.message)
    } finally { setReleasing(false) }
  }

  // ── Cancel order (buyer only) ───────────────────────────────
  const handleCancel = async () => {
    if (!id || !confirm('Cancel this order?')) return
    try {
      await apiClient.patch(`/api/p2p/orders/${id}/cancel`)
      toast.success('Order cancelled'); fetchOrder()
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? 'Failed')
    }
  }

  // ── Send chat message ────────────────────────────────────────
  const sendChat = async () => {
    if (!chatMsg.trim() || !id || !user?.id) return
    setSendingChat(true)
    try {
      await supabase.from('p2p_messages').insert({
        order_id: id, sender_id: user.id,
        message: chatMsg.trim(), is_system: false
      })
      setChatMsg('')
    } finally { setSendingChat(false) }
  }

  // ── Inline header & status banner (role‑aware) ──────────────
  const renderHeader = (backPath: string) => (
    <div className="flex items-center gap-3">
      <Button variant="ghost" size="sm" onClick={() => navigate(backPath)} className="p-2">
        <ArrowLeft className="h-4 w-4" />
      </Button>
      <div className="flex-1">
        <h1 className="text-base font-bold text-gray-900 dark:text-white">
          Order #{order?.order_number}
        </h1>
        <p className="text-xs text-gray-500">{order ? new Date(order.created_at).toLocaleString() : ''}</p>
      </div>
      <Button variant="ghost" size="sm" onClick={refresh} disabled={refreshing} className="p-2">
        <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
      </Button>
    </div>
  )

  const renderStatus = (isMerchantView: boolean) => (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${statusCfg?.color}`}>
      {order?.status === 'confirming'
        ? <Loader2 className="h-4 w-4 animate-spin flex-shrink-0" />
        : <Clock className="h-4 w-4 flex-shrink-0" />
      }
      <div className="flex-1">
        <p className="font-bold text-sm">{statusCfg?.label}</p>
        <p className="text-xs opacity-80">
          {order?.order_type === 'sell'
            ? isMerchantView ? statusCfg?.merchantSellDesc : statusCfg?.sellerDesc
            : isMerchantView ? statusCfg?.merchantDesc     : statusCfg?.buyerDesc
          }
        </p>
      </div>
      {order?.status === 'payment_window' && timeLeft > 0 && (
        <span className={`font-mono font-bold text-lg flex-shrink-0 ${
          timeLeft < 120 ? 'text-red-600 dark:text-red-400' : ''
        }`}>
          {formatTime(timeLeft)}
        </span>
      )}
    </div>
  )

  // ── Loading / error ───────────────────────────────────────────
  if (loading) return (
    <div className="flex justify-center items-center min-h-screen bg-gray-50 dark:bg-gray-900">
      <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
    </div>
  )
  if (error || !order) return (
    <div className="max-w-lg mx-auto px-4 py-16 text-center">
      <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
      <p className="text-gray-600 dark:text-gray-400">{error ?? 'Order not found'}</p>
      <Button className="mt-6" onClick={() => navigate('/payments')}>Back to Payments</Button>
    </div>
  )

  // ════════════════════════════════════════════════════════════
  // MERCHANT VIEW
  // ════════════════════════════════════════════════════════════
  if (isMerchant) {
    return (
      <div className="min-h-screen bg-white dark:bg-gray-50 p-3 md:p-6">
        <div className="max-w-2xl mx-auto space-y-4">

          {renderHeader('/merchant')}
          {renderStatus(true)}

          {/* Order summary — light theme for merchant */}
          <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100 shadow-sm">
            {[
              { label: 'Buyer pays',  value: `${order.fiat_amount.toLocaleString()} ${order.fiat_currency}` },
              { label: 'You release', value: `${order.token_amount.toFixed(6)} ${tokenDisplay}`, hl: true },
              { label: 'Rate',        value: `${order.price_per_token.toLocaleString()} ${order.fiat_currency}/${tokenDisplay}` },
              { label: 'Via',         value: order.payment_method },
            ].map((r, i) => (
              <div key={i} className="flex justify-between px-4 py-2.5 text-sm">
                <span className="text-gray-500">{r.label}</span>
                <span className={`font-semibold ${r.hl ? 'text-blue-600' : 'text-gray-900'}`}>{r.value}</span>
              </div>
            ))}
            {order.release_tx_hash && (
              <div className="flex justify-between px-4 py-2.5 text-sm items-center">
                <span className="text-gray-500">Tx hash</span>
                <button onClick={() => copy(order.release_tx_hash!, 'Hash')}
                  className="text-blue-600 font-mono text-xs flex items-center gap-1 hover:underline">
                  {order.release_tx_hash.slice(0, 14)}... <Copy className="h-3 w-3" />
                </button>
              </div>
            )}
          </div>

          {/* Receipt */}
          {order.status === 'paid' && order.payment_receipt_url && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
              <button onClick={() => setShowReceipt(v => !v)}
                className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-gray-900 hover:bg-gray-50 transition">
                <span className="flex items-center gap-2">
                  <Eye className="h-4 w-4 text-blue-500" />
                  Payment Receipt (uploaded by buyer)
                </span>
                {showReceipt
                  ? <ChevronUp className="h-4 w-4 text-gray-400" />
                  : <ChevronDown className="h-4 w-4 text-gray-400" />
                }
              </button>
              {showReceipt && (
                <div className="px-4 pb-4">
                  <a href={order.payment_receipt_url} target="_blank" rel="noopener noreferrer"
                    className="block rounded-lg overflow-hidden border border-gray-200 hover:border-blue-400 transition">
                    <img src={order.payment_receipt_url} alt="Receipt"
                      className="w-full max-h-52 object-contain bg-gray-50"
                      onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
                    <p className="text-xs text-blue-500 text-center py-2">View full receipt ↗</p>
                  </a>
                </div>
              )}
            </div>
          )}
          
          {/* ── SELL ORDER merchant: verify tokens + release fiat ── */}
          {order.order_type === 'sell' && order.status === 'paid' && (() => {
            const fiatRef = useRef<HTMLInputElement>(null)
            const [uploading, setUploading] = useState(false)
            const token = order.token || ''
            const chain = token.includes('_') ? token.split('_')[1].toLowerCase() : 'tron'
            const explorers: Record<string, string> = {
              tron: 'https://tronscan.org/#/transaction/',
              eth: 'https://etherscan.io/tx/',
              polygon: 'https://polygonscan.com/tx/',
              solana: 'https://solscan.io/tx/',
              algorand: 'https://algoexplorer.io/tx/',
            }
            const explorerUrl = order.token_tx_hash
              ? `${explorers[chain] || explorers.tron}${order.token_tx_hash}`
              : null

            const handleFiatProof = async (e: React.ChangeEvent<HTMLInputElement>) => {
              const file = e.target.files?.[0]; if (!file || !id) return
              setUploading(true)
              try {
                const form = new FormData()
                form.append('file', file)
                const res = await apiClient.post(`/api/p2p/sell/orders/${id}/fiat-proof`, form, {
                  headers: { 'Content-Type': 'multipart/form-data' }
                })
                if (res.data?.success) { toast.success('Fiat proof uploaded! Order moved to confirming.'); fetchOrder() }
                else throw new Error(res.data?.detail ?? 'Upload failed')
              } catch (e: any) { toast.error(e.response?.data?.detail ?? e.message) }
              finally { setUploading(false); if (fiatRef.current) fiatRef.current.value = '' }
            }

            return (
              <div className="space-y-3">
                {order.order_type === 'sell' && order.status === 'paid' && (
            <div className="bg-green-50 rounded-xl border border-green-200 p-3 text-sm text-green-800">
              ✅ <strong>{order.token_amount.toFixed(6)} {order.token.split('_')[0]}</strong>{' '}
              transferred to your Seamount wallet via platform infrastructure.
              {order.token_tx_hash && (
                <span className="block text-xs text-gray-500 font-mono mt-1">
                  Tx: {order.token_tx_hash.slice(0, 20)}...
                </span>
              )}
            </div>
          )}
                <Alert className="bg-amber-500/10 border-amber-500/30 py-2.5">
                  <AlertCircle className="h-4 w-4 text-amber-400" />
                  <AlertDescription className="text-xs text-amber-200">
                    Verify the token transfer above before sending fiat. Only proceed once confirmed on-chain.
                  </AlertDescription>
                </Alert>
                <input ref={fiatRef} type="file" accept="image/*,application/pdf"
                  className="hidden" onChange={handleFiatProof} />
                <Button
                  onClick={() => fiatRef.current?.click()}
                  disabled={uploading}
                  className="w-full h-11 bg-green-600 hover:bg-green-700 text-white font-bold gap-2"
                >
                  {uploading
                    ? <><Loader2 className="h-4 w-4 animate-spin" />Uploading...</>
                    : '💸 I\'ve Sent Fiat — Upload Payment Proof'
                  }
                </Button>
              </div>
            )
          })()}

          {/* Release action */}
          {order.status === 'paid' && (
            <div className="space-y-3">
              <Alert className="bg-amber-500/10 border-amber-500/30 py-2.5">
                <AlertCircle className="h-4 w-4 text-amber-400" />
                <AlertDescription className="text-xs text-amber-200">
                  Only release after confirming payment in your bank or mobile money. This cannot be reversed.
                </AlertDescription>
              </Alert>
              <Button onClick={handleRelease} disabled={releasing}
                className="w-full h-11 bg-green-600 hover:bg-green-700 text-white font-bold gap-2">
                {releasing
                  ? <><Loader2 className="h-4 w-4 animate-spin" />Releasing...</>
                  : <>✓ Confirm & Release {order.token_amount.toFixed(4)} {tokenDisplay}</>
                }
              </Button>
            </div>
          )}

          <ChatPanel
            messages={messages} userId={user?.id ?? ''}
            chatMsg={chatMsg} setChatMsg={setChatMsg}
            onSend={sendChat} sending={sendingChat}
            chatRef={chatRef}
            disabled={['completed', 'cancelled', 'expired'].includes(order.status)}
          />
        </div>
      </div>
    )
  }

  // ════════════════════════════════════════════════════════════
  // BUYER VIEW
  // ════════════════════════════════════════════════════════════
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-3 md:p-6">
      <div className="max-w-2xl mx-auto space-y-4">

        {renderHeader('/payments')}
        {renderStatus(false)}

        {/* Order summary */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700/60">
          {[
            { label: 'You buy',      value: `${order.token_amount.toFixed(6)} ${tokenDisplay}`, hl: true },
            { label: 'You pay',      value: `${order.fiat_amount.toLocaleString()} ${order.fiat_currency}` },
            { label: 'Rate',         value: `${order.price_per_token.toLocaleString()} ${order.fiat_currency}/${tokenDisplay}` },
            { label: 'Payment via',  value: order.payment_method },
            { label: 'Merchant',     value: order.p2p_merchants.display_name },
          ].map((r, i) => (
            <div key={i} className="flex justify-between px-4 py-2.5 text-sm">
              <span className="text-gray-500 dark:text-gray-400">{r.label}</span>
              <span className={`font-semibold ${r.hl ? 'text-blue-600 dark:text-blue-400' : 'text-gray-900 dark:text-white'}`}>
                {r.value}
              </span>
            </div>
          ))}
          {order.release_tx_hash && (
            <div className="flex justify-between px-4 py-2.5 text-sm items-center">
              <span className="text-gray-500 dark:text-gray-400">Transaction</span>
              <button onClick={() => copy(order.release_tx_hash!, 'Tx hash')}
                className="text-blue-600 font-mono text-xs flex items-center gap-1 hover:underline">
                {order.release_tx_hash.slice(0, 14)}... <Copy className="h-3 w-3" />
              </button>
            </div>
          )}
        </div>

        {/* Payment details — flattened, no [object Object] */}
        {['payment_window', 'paid', 'confirming'].includes(order.status) && paymentRows.length > 0 && (
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800 p-4">
            <h3 className="font-bold text-blue-900 dark:text-blue-200 text-sm mb-3">💳 Payment Details</h3>
            <div className="space-y-2">
              {paymentRows.map((r, i) => (
                <div key={i} className="flex justify-between items-center text-sm">
                  <span className="text-blue-700 dark:text-blue-300 capitalize">{r.key}</span>
                  <button onClick={() => copy(r.value, r.key)}
                    className="flex items-center gap-1.5 font-mono font-bold text-blue-900 dark:text-blue-100 hover:text-blue-600 transition">
                    {r.value} <Copy className="h-3 w-3 opacity-60" />
                  </button>
                </div>
              ))}
            </div>
            <p className="text-xs text-blue-600 dark:text-blue-400 mt-3">
              ⚠️ Include order reference <strong>{order.order_number}</strong> in payment notes.
            </p>
          </div>
        )}

        {/* ── SELL ORDER: show wallet address + tx hash input ── */}
        {isBuyer && order.order_type === 'sell' && order.status === 'payment_window' && (() => {
          const [releasing, setReleasing] = useState(false)
          const handleRelease = async () => {
            if (!confirm(
              `This will send ${order.token_amount.toFixed(6)} ` +
              `${order.token.split('_')[0]} from your Seamount wallet ` +
              `to the merchant. Proceed?`
            )) return
            setReleasing(true)
            try {
              const res = await apiClient.patch(
                `/api/p2p/sell/orders/${id}/release-tokens`
              )
              if (res.data?.success) {
                toast.success('Token transfer initiated!')
                fetchOrder()
              } else throw new Error(res.data?.detail)
            } catch (e: any) {
              toast.error(e.response?.data?.detail ?? e.message)
            } finally { setReleasing(false) }
          }

          return (
            <div className="bg-orange-50 dark:bg-orange-900/20 rounded-xl border border-orange-200 dark:border-orange-800 p-4 space-y-3">
              <h3 className="font-bold text-orange-900 dark:text-orange-200 text-sm">
                💸 Release Your Tokens
              </h3>
              <p className="text-xs text-orange-700 dark:text-orange-300">
                Seamount will securely transfer{' '}
                <strong>{order.token_amount.toFixed(6)} {order.token.split('_')[0]}</strong>{' '}
                from your wallet to the merchant. The merchant will then
                send <strong>{order.fiat_amount.toLocaleString()} {order.fiat_currency}</strong>{' '}
                to your <strong>{order.seller_payout_method}</strong>.
              </p>
              <Alert className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 py-2">
                <AlertCircle className="h-3.5 w-3.5 text-blue-500" />
                <AlertDescription className="text-xs text-blue-800 dark:text-blue-300">
                  Tokens are held securely by Seamount until the merchant confirms fiat sent.
                </AlertDescription>
              </Alert>
              <Button
                onClick={handleRelease}
                disabled={releasing}
                className="w-full h-11 bg-orange-600 hover:bg-orange-700 text-white font-bold gap-2"
              >
                {releasing
                  ? <><Loader2 className="h-4 w-4 animate-spin" />Transferring...</>
                  : `🔒 Release ${order.token_amount.toFixed(4)} ${order.token.split('_')[0]} to Seamount`
                }
              </Button>
              <Button variant="outline" size="sm" onClick={handleCancel}
                className="w-full text-red-600 border-red-200 hover:bg-red-50 text-xs">
                Cancel Order
              </Button>
            </div>
          )
        })()}

        {/* ── SELL ORDER: seller confirms fiat received ── */}
        {isBuyer && order.order_type === 'sell' && order.status === 'confirming' && (() => {
          const [confirming, setConfirming] = useState(false)
          const handleConfirm = async () => {
            setConfirming(true)
            try {
              const res = await apiClient.patch(`/api/p2p/sell/orders/${id}/fiat-received`)
              if (res.data?.success) { toast.success('Order completed!'); fetchOrder() }
              else throw new Error(res.data?.detail)
            } catch (e: any) { toast.error(e.response?.data?.detail ?? e.message) }
            finally { setConfirming(false) }
          }
          return (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
              <h3 className="font-bold text-gray-900 dark:text-white text-sm">
                ✅ Confirm Fiat Receipt
              </h3>
              <p className="text-xs text-gray-500">
                The merchant has sent {order.fiat_amount.toLocaleString()} {order.fiat_currency} to your{' '}
                <strong>{order.seller_payout_method}</strong>.
                {order.seller_payout_details && Object.entries(order.seller_payout_details).map(([k, v]) => (
                  <span key={k} className="block mt-0.5">
                    {k.replace(/_/g, ' ')}: <strong>{String(v)}</strong>
                  </span>
                ))}
              </p>
              {order.fiat_proof_url && (
                <a href={order.fiat_proof_url} target="_blank" rel="noopener noreferrer"
                  className="block text-xs text-blue-600 hover:underline">
                  View payment proof ↗
                </a>
              )}
              <Button onClick={handleConfirm} disabled={confirming}
                className="w-full h-11 bg-green-600 hover:bg-green-700 text-white font-bold gap-2">
                {confirming ? <><Loader2 className="h-4 w-4 animate-spin" />Confirming...</> : '✓ I\'ve Received My Fiat'}
              </Button>
            </div>
          )
        })()}

        {/* Receipt upload + Cancel */}
        {isBuyer && order.status === 'payment_window' && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
            <h3 className="font-bold text-gray-900 dark:text-white text-sm">Step 2 — Upload Payment Receipt</h3>
            <p className="text-xs text-gray-500">After paying, upload a screenshot of your receipt.</p>
            {order.payment_receipt_url ? (
              <div className="flex items-center gap-2 text-green-600 text-sm font-medium">
                <CheckCircle className="h-4 w-4" /> Receipt uploaded. Awaiting merchant.
              </div>
            ) : (
              <>
                <input ref={fileRef} type="file" accept="image/*,application/pdf"
                  className="hidden" onChange={handleUpload} />
                <Button onClick={() => fileRef.current?.click()} disabled={uploading}
                  variant="outline"
                  className="w-full h-11 gap-2 border-dashed border-blue-300 bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold">
                  {uploading
                    ? <><Loader2 className="h-4 w-4 animate-spin" />Uploading...</>
                    : <><Upload className="h-4 w-4" />Upload Receipt</>
                  }
                </Button>
              </>
            )}
            <Button variant="outline" size="sm" onClick={handleCancel}
              className="w-full text-red-600 border-red-200 hover:bg-red-50 text-xs">
              Cancel Order
            </Button>
          </div>
        )}

        {/* Dispute button — shown after payment_window ends and tokens not released */}
        {isBuyer && ['paid', 'confirming', 'disputed'].includes(order.status) && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
            <p className="text-xs text-gray-500">
              {order.status === 'disputed'
                ? 'Your dispute has been submitted. Seamount support will contact you within 24 hours.'
                : 'Paid but tokens not released? You can escalate to Seamount support at any time.'
              }
            </p>
            {order.status !== 'disputed' && (
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  if (!id || !confirm('Raise a dispute for this order? Our support team will review within 24 hours.')) return
                  try {
                    await supabase.from('p2p_orders')
                        .update({ status: 'disputed' }).eq('id', id)
                    await supabase.from('p2p_messages').insert({
                        order_id: id, is_system: true,
                        message: 'Buyer has raised a dispute. Seamount support has been notified.'
                    })
                    toast.success('Dispute raised. Support will contact you within 24 hours.')
                    fetchOrder()
                  } catch (error) { toast.error('Failed to raise dispute')}
                }}
                className="w-full text-orange-600 border-orange-200 hover:bg-orange-50 text-xs"
              >
                ⚠️ Raise a Dispute
              </Button>
            )}
            {order.status === 'disputed' && (
              <div className="flex items-center gap-2 text-orange-600 text-sm font-medium">
                <AlertCircle className="h-4 w-4" /> Dispute active — under review
              </div>
            )}
          </div>
        )}

        <ChatPanel
          messages={messages} userId={user?.id ?? ''}
          chatMsg={chatMsg} setChatMsg={setChatMsg}
          onSend={sendChat} sending={sendingChat}
          chatRef={chatRef}
          disabled={['completed', 'cancelled', 'expired'].includes(order.status)}
        />
      </div>
    </div>
  )
}