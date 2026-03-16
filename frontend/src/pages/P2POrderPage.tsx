const [showReceipt,  setShowReceipt]  = useState(false)

  // ── Inline header — avoids inner-component remount bug ───────
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

  // ── Inline status banner — role-aware ─────────────────────────
  const renderStatus = (isMerchantView: boolean) => (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${statusCfg?.color}`}>
      {order?.status === 'confirming'
        ? <Loader2 className="h-4 w-4 animate-spin flex-shrink-0" />
        : <Clock className="h-4 w-4 flex-shrink-0" />
      }
      <div className="flex-1">
        <p className="font-bold text-sm">{statusCfg?.label}</p>
        <p className="text-xs opacity-80">
          {isMerchantView ? statusCfg?.merchantDesc : statusCfg?.buyerDesc}
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
  )// FILE: frontend/src/pages/P2POrderPage.tsx
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
import { Button } from '@/components/ui/button.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'

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
  p2p_merchants: {
    id: string
    display_name: string
    verified: boolean
    avg_release_time_mins: number
    user_id: string
  }
  p2p_listings: {
    payment_details: Record<string, any>
  }
}

interface Message {
  id: string
  sender_id: string | null
  message: string
  is_system: boolean
  created_at: string
}

// ── STATUS CONFIG — separate desc for buyer vs merchant ───────
const STATUS_CFG: Record<string, {
  label: string; color: string
  buyerDesc: string; merchantDesc: string
}> = {
  payment_window: {
    label: 'Awaiting Payment',
    color: 'bg-yellow-500/20 text-yellow-800 dark:text-yellow-300 border-yellow-400 dark:border-yellow-500/40',
    buyerDesc:     'Complete your payment before the timer expires',
    merchantDesc:  'Waiting for buyer to make payment and upload receipt'
  },
  paid: {
    label: 'Payment Sent',
    color: 'bg-blue-500/20 text-blue-800 dark:text-blue-300 border-blue-400 dark:border-blue-500/40',
    buyerDesc:     'Waiting for merchant to verify and release tokens',
    merchantDesc:  'Buyer has paid — verify receipt and release tokens'
  },
  confirming: {
    label: 'Releasing Tokens',
    color: 'bg-purple-500/20 text-purple-800 dark:text-purple-300 border-purple-400 dark:border-purple-500/40',
    buyerDesc:     'Merchant confirmed. Tokens are being released to your wallet...',
    merchantDesc:  'Token release in progress...'
  },
  completed: {
    label: 'Completed',
    color: 'bg-green-500/20 text-green-800 dark:text-green-300 border-green-400 dark:border-green-500/40',
    buyerDesc:     'Tokens have been released to your wallet',
    merchantDesc:  'Order fulfilled. Tokens released successfully.'
  },
  cancelled: {
    label: 'Cancelled',
    color: 'bg-gray-200 dark:bg-gray-700/50 text-gray-600 dark:text-gray-400 border-gray-300 dark:border-gray-600',
    buyerDesc:     'This order has been cancelled',
    merchantDesc:  'This order was cancelled'
  },
  disputed: {
    label: 'Disputed',
    color: 'bg-red-500/20 text-red-800 dark:text-red-300 border-red-400 dark:border-red-500/40',
    buyerDesc:     'Under review by Seamount support',
    merchantDesc:  'Under review by Seamount support'
  },
}

// ── Flatten nested payment_details ────────────────────────────
// Handles {"Airtel Money": {"phone_number":"...","account_name":"..."}}
// and flat {"Airtel Money": "07123..."}
function flattenPaymentDetails(
  details: Record<string, any>
): { key: string; value: string }[] {
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
      <div className="px-4 py-2.5 border-b border-gray-100 dark:border-gray-700">
        <h3 className="font-semibold text-sm text-gray-900 dark:text-white">Order Chat</h3>
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

  const refresh = useCallback(async () => {
    setRefreshing(true)
    await fetchOrder()
    await fetchMessages()
    setRefreshing(false)
  }, [fetchOrder, fetchMessages])

  const fileRef    = useRef<HTMLInputElement>(null)
  const chatRef    = useRef<HTMLDivElement>(null)
  const timerRef   = useRef<ReturnType<typeof setInterval> | null>(null)

  const isBuyer    = order?.buyer_id === user?.id
  const isMerchant = order?.p2p_merchants?.user_id === user?.id
  const tokenDisplay = (order?.token ?? '').split('_')[0]
  const statusCfg  = order ? (STATUS_CFG[order.status] ?? STATUS_CFG.cancelled) : null
  const paymentRows = flattenPaymentDetails(order?.p2p_listings?.payment_details ?? {})
  const platformFee = order ? (order.token_amount * order.platform_fee_bps) / 10000 : 0

  // ── Fetch ────────────────────────────────────────────────────
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

  const fetchMessages = useCallback(async () => {
    if (!id) return
    const { data } = await supabase
      .from('p2p_messages').select('*')
      .eq('order_id', id).order('created_at', { ascending: true })
    if (data) setMessages(data)
  }, [id])

  useEffect(() => { fetchOrder(); fetchMessages() }, [fetchOrder, fetchMessages])

  // Realtime order
  useEffect(() => {
    if (!id) return
    const ch = supabase.channel(`order:${id}`)
      .on('postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'p2p_orders', filter: `id=eq.${id}` },
        p => setOrder(prev => prev ? { ...prev, ...p.new } : prev))
      .subscribe()
    return () => { supabase.removeChannel(ch) }
  }, [id])

  // Realtime messages
  useEffect(() => {
    if (!id) return
    const ch = supabase.channel(`msgs:${id}`)
      .on('postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'p2p_messages', filter: `order_id=eq.${id}` },
        p => setMessages(prev => [...prev, p.new as Message]))
      .subscribe()
    return () => { supabase.removeChannel(ch) }
  }, [id])

  // Timer
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
      if (rem === 0) { clearInterval(timerRef.current!); fetchOrder() }
    }
    tick()
    timerRef.current = setInterval(tick, 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [order?.payment_deadline, order?.status, fetchOrder])

  // Scroll chat
  useEffect(() => {
    chatRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const formatTime = (s: number) =>
    `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`

  const copy = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    toast.success(`${label} copied!`)
  }

  // ── Receipt upload ────────────────────────────────────────────
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

  // ── Release tokens ────────────────────────────────────────────
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

  // ── Cancel ────────────────────────────────────────────────────
  const handleCancel = async () => {
    if (!id || !confirm('Cancel this order?')) return
    try {
      await apiClient.patch(`/api/p2p/orders/${id}/cancel`)
      toast.success('Order cancelled'); fetchOrder()
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? 'Failed')
    }
  }

  // ── Chat ──────────────────────────────────────────────────────
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

  // ── Shared header ─────────────────────────────────────────────
  const PageHeader = ({ backPath }: { backPath: string }) => (
    <div className="flex items-center gap-3">
      <Button variant="ghost" size="sm" onClick={() => navigate(backPath)} className="p-2">
        <ArrowLeft className="h-4 w-4" />
      </Button>
      <div className="flex-1">
        <h1 className="text-base font-bold text-gray-900 dark:text-white">
          Order #{order.order_number}
        </h1>
        <p className="text-xs text-gray-500">{new Date(order.created_at).toLocaleString()}</p>
      </div>
      <Button variant="ghost" size="sm" onClick={fetchOrder} className="p-2">
        <RefreshCw className="h-4 w-4" />
      </Button>
    </div>
  )

  // ── Shared status banner — role-aware ────────────────────────
  const StatusBanner = ({ isMerchantView }: { isMerchantView: boolean }) => (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${statusCfg?.color}`}>
      {order.status === 'confirming'
        ? <Loader2 className="h-4 w-4 animate-spin flex-shrink-0" />
        : <Clock className="h-4 w-4 flex-shrink-0" />
      }
      <div className="flex-1">
        <p className="font-bold text-sm">{statusCfg?.label}</p>
        <p className="text-xs opacity-80">
          {isMerchantView ? statusCfg?.merchantDesc : statusCfg?.buyerDesc}
        </p>
      </div>
      {order.status === 'payment_window' && timeLeft > 0 && (
        <span className={`font-mono font-bold text-lg flex-shrink-0 ${
          timeLeft < 120 ? 'text-red-600 dark:text-red-400' : ''
        }`}>
          {formatTime(timeLeft)}
        </span>
      )}
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
            disabled={['completed', 'cancelled'].includes(order.status)}
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
            { label: 'Platform fee', value: `${platformFee.toFixed(6)} ${tokenDisplay}` },
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
        {isBuyer && order.status === 'paid' && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
            <p className="text-xs text-gray-500">
              Already paid? If the merchant does not release tokens within 15 minutes
              of confirming your payment, you can raise a dispute.
            </p>
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
                } catch { toast.error('Failed to raise dispute') }
              }}
              className="w-full text-orange-600 border-orange-200 hover:bg-orange-50 text-xs"
            >
              ⚠️ Raise a Dispute
            </Button>
          </div>
        )}

        <ChatPanel
          messages={messages} userId={user?.id ?? ''}
          chatMsg={chatMsg} setChatMsg={setChatMsg}
          onSend={sendChat} sending={sendingChat}
          chatRef={chatRef}
          disabled={['completed', 'cancelled'].includes(order.status)}
        />
      </div>
    </div>
  )
}