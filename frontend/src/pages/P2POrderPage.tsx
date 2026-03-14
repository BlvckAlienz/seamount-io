// FILE: frontend/src/pages/P2POrderPage.tsx
// Order detail page — shown after buyer places an order.
// Handles: 15-min timer, payment details reveal, receipt upload,
// live P2P chat, merchant release flow. Works for both buyer and merchant.

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { supabase } from '@/lib/supabase'
import { apiClient } from '@/config/api'
import { useAuth } from '@/contexts/AuthContext'
import toast from 'react-hot-toast'
import {
  Clock, CheckCircle, XCircle, Upload, Send,
  ShieldCheck, AlertCircle, Loader2, Copy,
  ArrowLeft, RefreshCw
} from 'lucide-react'
import { Button } from '@/components/ui/button.tsx'
import { Alert, AlertDescription } from '@/components/ui/alert.tsx'
import { Badge } from '@/components/ui/badge.tsx'

// ─────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────
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
    payment_details: Record<string, string>
  }
}

interface Message {
  id: string
  sender_id: string | null
  message: string
  is_system: boolean
  created_at: string
}

// ─────────────────────────────────────────────────────────────
// STATUS CONFIG
// ─────────────────────────────────────────────────────────────
const STATUS_CONFIG: Record<string, {
  label: string
  color: string
  icon: typeof Clock
  description: string
}> = {
  payment_window: {
    label: 'Awaiting Payment',
    color: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    icon: Clock,
    description: 'Complete your payment before the timer expires'
  },
  paid: {
    label: 'Payment Sent',
    color: 'bg-blue-100 text-blue-800 border-blue-300',
    icon: CheckCircle,
    description: 'Waiting for merchant to confirm and release tokens'
  },
  confirming: {
    label: 'Releasing Tokens',
    color: 'bg-purple-100 text-purple-800 border-purple-300',
    icon: Loader2,
    description: 'Merchant confirmed. Tokens are being released...'
  },
  completed: {
    label: 'Completed',
    color: 'bg-green-100 text-green-800 border-green-300',
    icon: CheckCircle,
    description: 'Tokens have been released to your wallet'
  },
  cancelled: {
    label: 'Cancelled',
    color: 'bg-gray-100 text-gray-700 border-gray-300',
    icon: XCircle,
    description: 'This order has been cancelled'
  },
  disputed: {
    label: 'Disputed',
    color: 'bg-red-100 text-red-800 border-red-300',
    icon: AlertCircle,
    description: 'This order is under review by Seamount support'
  }
}

// ─────────────────────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────────────────────
export default function P2POrderPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [order,          setOrder]          = useState<Order | null>(null)
  const [messages,       setMessages]       = useState<Message[]>([])
  const [timeLeft,       setTimeLeft]       = useState<number>(0)
  const [loading,        setLoading]        = useState(true)
  const [uploading,      setUploading]      = useState(false)
  const [releasing,      setReleasing]      = useState(false)
  const [chatMsg,        setChatMsg]        = useState('')
  const [sendingChat,    setSendingChat]    = useState(false)
  const [error,          setError]          = useState<string | null>(null)

  const fileInputRef  = useRef<HTMLInputElement>(null)
  const chatBottomRef = useRef<HTMLDivElement>(null)
  const timerRef      = useRef<ReturnType<typeof setInterval> | null>(null)

  const isBuyer    = order?.buyer_id === user?.id
  const isMerchant = order?.p2p_merchants?.user_id === user?.id
  const tokenDisplay = (order?.token ?? '').split('_')[0]
  const statusCfg  = order ? STATUS_CONFIG[order.status] ?? STATUS_CONFIG.cancelled : null

  // ── Fetch order ─────────────────────────────────────────────
  const fetchOrder = useCallback(async () => {
    if (!id) return
    try {
      const { data, error: err } = await supabase
        .from('p2p_orders')
        .select(`
          *,
          p2p_merchants (id, display_name, verified, avg_release_time_mins, user_id),
          p2p_listings  (payment_details)
        `)
        .eq('id', id)
        .single()

      if (err) throw err
      setOrder(data as Order)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [id])

  // ── Fetch messages ───────────────────────────────────────────
  const fetchMessages = useCallback(async () => {
    if (!id) return
    const { data } = await supabase
      .from('p2p_messages')
      .select('*')
      .eq('order_id', id)
      .order('created_at', { ascending: true })
    if (data) setMessages(data)
  }, [id])

  // ── Initial load ─────────────────────────────────────────────
  useEffect(() => {
    fetchOrder()
    fetchMessages()
  }, [fetchOrder, fetchMessages])

  // ── Realtime: order status changes ──────────────────────────
  useEffect(() => {
    if (!id) return
    const channel = supabase
      .channel(`order:${id}`)
      .on('postgres_changes', {
        event: 'UPDATE',
        schema: 'public',
        table: 'p2p_orders',
        filter: `id=eq.${id}`
      }, payload => {
        setOrder(prev => prev ? { ...prev, ...payload.new } : prev)
      })
      .subscribe()
    return () => { supabase.removeChannel(channel) }
  }, [id])

  // ── Realtime: new messages ───────────────────────────────────
  useEffect(() => {
    if (!id) return
    const channel = supabase
      .channel(`messages:${id}`)
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'p2p_messages',
        filter: `order_id=eq.${id}`
      }, payload => {
        setMessages(prev => [...prev, payload.new as Message])
      })
      .subscribe()
    return () => { supabase.removeChannel(channel) }
  }, [id])

  // ── Countdown timer ──────────────────────────────────────────
  useEffect(() => {
    if (!order?.payment_deadline || order.status !== 'payment_window') {
      if (timerRef.current) clearInterval(timerRef.current)
      return
    }

    const updateTimer = () => {
      const remaining = Math.max(
        0,
        Math.floor((new Date(order.payment_deadline).getTime() - Date.now()) / 1000)
      )
      setTimeLeft(remaining)
      if (remaining === 0) {
        if (timerRef.current) clearInterval(timerRef.current)
        fetchOrder() // refresh — backend will have cancelled it
      }
    }

    updateTimer()
    timerRef.current = setInterval(updateTimer, 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [order?.payment_deadline, order?.status, fetchOrder])

  // ── Scroll chat to bottom ────────────────────────────────────
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Receipt upload ───────────────────────────────────────────
  const handleReceiptUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !id) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('order_id', id)

      const res = await apiClient.post('/api/p2p/orders/receipt-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      if (res.data?.success) {
        toast.success('Receipt uploaded. Awaiting merchant confirmation.')
        fetchOrder()
      } else {
        throw new Error(res.data?.detail ?? 'Upload failed')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? err.message ?? 'Upload failed')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  // ── Merchant: release tokens ─────────────────────────────────
  const handleRelease = async () => {
    if (!id || !user?.id) return
    setReleasing(true)
    try {
      const res = await apiClient.patch(`/api/p2p/orders/${id}/release`)
      if (res.data?.success) {
        toast.success('Token release initiated!')
        fetchOrder()
      } else {
        throw new Error(res.data?.detail ?? 'Release failed')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? err.message ?? 'Release failed')
    } finally {
      setReleasing(false)
    }
  }

  // ── Buyer: cancel order ──────────────────────────────────────
  const handleCancel = async () => {
    if (!id) return
    if (!confirm('Cancel this order? This cannot be undone.')) return
    try {
      await apiClient.patch(`/api/p2p/orders/${id}/cancel`)
      toast.success('Order cancelled')
      fetchOrder()
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to cancel')
    }
  }

  // ── Send chat message ────────────────────────────────────────
  const handleSendMessage = async () => {
    if (!chatMsg.trim() || !id || !user?.id) return
    setSendingChat(true)
    try {
      await supabase.from('p2p_messages').insert({
        order_id: id,
        sender_id: user.id,
        message: chatMsg.trim(),
        is_system: false
      })
      setChatMsg('')
    } catch (err: any) {
      toast.error('Failed to send message')
    } finally {
      setSendingChat(false)
    }
  }

  // ── Copy to clipboard ────────────────────────────────────────
  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    toast.success(`${label} copied!`)
  }

  // ── Format timer ─────────────────────────────────────────────
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0')
    const s = (secs % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  // ─────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    )
  }

  if (error || !order) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 text-center">
        <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <p className="text-gray-600 dark:text-gray-400">{error ?? 'Order not found'}</p>
        <Button className="mt-6" onClick={() => navigate('/payments')}>
          Back to Payments
        </Button>
      </div>
    )
  }

  const paymentDetails = order.p2p_listings?.payment_details ?? {}
  const platformFee = (order.token_amount * order.platform_fee_bps) / 10000

  return (
    <div className="w-full max-w-3xl mx-auto px-3 sm:px-6 py-6 space-y-5">

      {/* ── Back + Header ── */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="gap-1 p-2">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            Order #{order.order_number}
          </h1>
          <p className="text-xs text-gray-500">
            {new Date(order.created_at).toLocaleString()}
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={fetchOrder} className="ml-auto p-2">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* ── Status Banner ── */}
      {statusCfg && (
        <div className={`flex items-center gap-3 p-4 rounded-xl border ${statusCfg.color}`}>
          <statusCfg.icon className={`h-5 w-5 flex-shrink-0 ${order.status === 'confirming' ? 'animate-spin' : ''}`} />
          <div>
            <p className="font-bold text-sm">{statusCfg.label}</p>
            <p className="text-xs mt-0.5">{statusCfg.description}</p>
          </div>

          {/* Countdown timer */}
          {order.status === 'payment_window' && timeLeft > 0 && (
            <div className={`ml-auto text-center px-3 py-1 rounded-lg font-mono font-bold text-lg
              ${timeLeft < 120 ? 'text-red-600 bg-red-50' : 'text-yellow-700 bg-yellow-50'}`}>
              {formatTime(timeLeft)}
            </div>
          )}
        </div>
      )}

      {/* ── Order Summary ── */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700">
        <div className="px-5 py-3 flex justify-between text-sm">
          <span className="text-gray-500">You buy</span>
          <span className="font-bold text-blue-600">{order.token_amount.toFixed(6)} {tokenDisplay}</span>
        </div>
        <div className="px-5 py-3 flex justify-between text-sm">
          <span className="text-gray-500">You pay</span>
          <span className="font-semibold text-gray-900 dark:text-white">
            {order.fiat_amount.toLocaleString()} {order.fiat_currency}
          </span>
        </div>
        <div className="px-5 py-3 flex justify-between text-sm">
          <span className="text-gray-500">Rate</span>
          <span className="text-gray-700 dark:text-gray-300">
            {order.price_per_token.toLocaleString()} {order.fiat_currency} / {tokenDisplay}
          </span>
        </div>
        <div className="px-5 py-3 flex justify-between text-sm">
          <span className="text-gray-500">Platform fee (0.3%)</span>
          <span className="text-gray-700 dark:text-gray-300">{platformFee.toFixed(6)} {tokenDisplay}</span>
        </div>
        <div className="px-5 py-3 flex justify-between text-sm">
          <span className="text-gray-500">Payment method</span>
          <span className="font-medium text-gray-900 dark:text-white">{order.payment_method}</span>
        </div>
        <div className="px-5 py-3 flex justify-between text-sm">
          <span className="text-gray-500">Merchant</span>
          <span className="flex items-center gap-1 font-medium text-gray-900 dark:text-white">
            {order.p2p_merchants.display_name}
            {order.p2p_merchants.verified && <ShieldCheck className="h-3.5 w-3.5 text-blue-500" />}
          </span>
        </div>

        {/* Release tx hash when completed */}
        {order.release_tx_hash && (
          <div className="px-5 py-3 flex justify-between text-sm items-center">
            <span className="text-gray-500">Transaction</span>
            <button
              onClick={() => copyToClipboard(order.release_tx_hash!, 'Tx hash')}
              className="flex items-center gap-1 text-blue-600 font-mono text-xs hover:underline"
            >
              {order.release_tx_hash.slice(0, 16)}...
              <Copy className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>

      {/* ── Payment Details (revealed only after order placed) ── */}
      {['payment_window', 'paid', 'confirming'].includes(order.status) &&
        Object.keys(paymentDetails).length > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800 p-5">
          <h3 className="font-bold text-blue-900 dark:text-blue-200 text-sm mb-3">
            💳 Payment Details
          </h3>
          <div className="space-y-2">
            {Object.entries(paymentDetails).map(([key, value]) => (
              <div key={key} className="flex justify-between items-center text-sm">
                <span className="text-blue-700 dark:text-blue-300 capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                <button
                  onClick={() => copyToClipboard(String(value), key)}
                  className="flex items-center gap-1.5 font-mono font-bold text-blue-900 dark:text-blue-100 hover:text-blue-600 transition"
                >
                  {String(value)}
                  <Copy className="h-3.5 w-3.5 opacity-60" />
                </button>
              </div>
            ))}
          </div>
          <p className="text-xs text-blue-600 dark:text-blue-400 mt-3">
            ⚠️ Include order reference <strong>{order.order_number}</strong> in your payment notes.
          </p>
        </div>
      )}

      {/* ── Receipt Upload (buyer only, payment_window status) ── */}
      {isBuyer && order.status === 'payment_window' && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-3">
          <h3 className="font-bold text-gray-900 dark:text-white text-sm">
            Step 2 — Upload Payment Receipt
          </h3>
          <p className="text-xs text-gray-500">
            After sending payment, upload a screenshot or photo of your receipt.
          </p>

          {order.payment_receipt_url ? (
            <div className="flex items-center gap-2 text-green-600 text-sm font-medium">
              <CheckCircle className="h-4 w-4" />
              Receipt uploaded. Awaiting merchant.
            </div>
          ) : (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,application/pdf"
                className="hidden"
                onChange={handleReceiptUpload}
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="w-full h-12 gap-2 border-2 border-dashed border-blue-300 bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold"
                variant="outline"
              >
                {uploading
                  ? <><Loader2 className="h-4 w-4 animate-spin" />Uploading...</>
                  : <><Upload className="h-4 w-4" />Upload Receipt</>
                }
              </Button>
            </>
          )}

          {/* Cancel button */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleCancel}
            className="w-full text-red-600 border-red-200 hover:bg-red-50"
          >
            Cancel Order
          </Button>
        </div>
      )}

      {/* ── Merchant: release tokens panel ── */}
      {isMerchant && order.status === 'paid' && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
          <h3 className="font-bold text-gray-900 dark:text-white text-sm">
            Confirm & Release Tokens
          </h3>

          {order.payment_receipt_url && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Buyer's Receipt
              </p>
              <a
                href={order.payment_receipt_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-lg overflow-hidden border border-gray-200 hover:border-blue-400 transition"
              >
                <img
                  src={order.payment_receipt_url}
                  alt="Payment receipt"
                  className="w-full max-h-48 object-contain bg-gray-50"
                  onError={e => {
                    // Fallback for PDFs or broken images
                    (e.target as HTMLImageElement).style.display = 'none'
                  }}
                />
                <div className="px-3 py-2 text-xs text-blue-600 text-center">
                  View full receipt ↗
                </div>
              </a>
            </div>
          )}

          <Alert className="bg-amber-50 border-amber-200">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-800 text-xs">
              Only release tokens after you have <strong>confirmed</strong> the payment
              in your bank or mobile money account. This action cannot be reversed.
            </AlertDescription>
          </Alert>

          <Button
            onClick={handleRelease}
            disabled={releasing}
            className="w-full h-12 bg-green-600 hover:bg-green-700 text-white font-bold gap-2"
          >
            {releasing
              ? <><Loader2 className="h-4 w-4 animate-spin" />Releasing...</>
              : <>Release {order.token_amount.toFixed(4)} {tokenDisplay}</>
            }
          </Button>
        </div>
      )}

      {/* ── P2P Chat ── */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 flex flex-col">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
          <h3 className="font-semibold text-sm text-gray-900 dark:text-white">Order Chat</h3>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto max-h-72 p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-center text-xs text-gray-400 py-6">No messages yet</p>
          )}
          {messages.map(msg => (
            <div
              key={msg.id}
              className={`flex ${msg.is_system ? 'justify-center' : msg.sender_id === user?.id ? 'justify-end' : 'justify-start'}`}
            >
              {msg.is_system ? (
                <span className="text-xs text-gray-400 bg-gray-50 dark:bg-gray-900 px-3 py-1.5 rounded-full border border-gray-200 dark:border-gray-700 max-w-xs text-center">
                  {msg.message}
                </span>
              ) : (
                <div className={`max-w-xs px-3 py-2 rounded-xl text-sm ${
                  msg.sender_id === user?.id
                    ? 'bg-blue-600 text-white rounded-br-none'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded-bl-none'
                }`}>
                  {msg.message}
                </div>
              )}
            </div>
          ))}
          <div ref={chatBottomRef} />
        </div>

        {/* Chat input — hidden for completed/cancelled orders */}
        {!['completed', 'cancelled'].includes(order.status) && (
          <div className="p-3 border-t border-gray-100 dark:border-gray-700 flex gap-2">
            <input
              type="text"
              value={chatMsg}
              onChange={e => setChatMsg(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage() } }}
              placeholder="Type a message..."
              className="flex-1 text-sm px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <Button
              size="sm"
              onClick={handleSendMessage}
              disabled={sendingChat || !chatMsg.trim()}
              className="px-3 bg-blue-600 hover:bg-blue-700 text-white"
            >
              {sendingChat ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}