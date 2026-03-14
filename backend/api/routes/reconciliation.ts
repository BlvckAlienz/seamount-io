// FILE: backend/api/routes/reconciliation.ts
// Downloadable order history for merchants and users.
// Webhooks notify connected systems automatically on every completion.

import { Router } from 'express'
import { createClient } from '@supabase/supabase-js'
import { stringify } from 'csv-stringify/sync'
import crypto from 'crypto'

const router = Router()
const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_KEY!)

// GET /api/reconciliation/export?from=&to=&format=csv|json
router.get('/export', async (req, res) => {
  const { from, to, format = 'json' } = req.query
  const userId = (req as any).user?.id

  let query = supabase
    .from('p2p_orders')
    .select([
      'order_number', 'token', 'fiat_currency', 'fiat_amount',
      'token_amount', 'price_per_token', 'platform_fee_bps',
      'status', 'payment_method', 'release_tx_hash',
      'created_at', 'updated_at'
    ].join(','))
    .eq('status', 'completed')

  if (from) query = query.gte('created_at', from as string)
  if (to)   query = query.lte('created_at', to as string)

  const { data, error } = await query
  if (error) return res.status(500).json({ error: error.message })

  if (format === 'csv') {
    const csv = stringify(data ?? [], { header: true })
    res.setHeader('Content-Type', 'text/csv')
    res.setHeader('Content-Disposition', 'attachment; filename="seamount_orders.csv"')
    return res.send(csv)
  }

  res.json({ count: data?.length ?? 0, orders: data })
})

// POST webhook dispatch — called internally after order.completed
export async function dispatchWebhooks(orderId: string, event: string) {
  const { data: subs } = await supabase
    .from('webhook_subscriptions')
    .select('*')
    .contains('events', [event])
    .eq('is_active', true)

  for (const sub of (subs ?? [])) {
    const payload = JSON.stringify({ event, orderId, timestamp: Date.now() })
    const sig = crypto.createHmac('sha256', sub.secret).update(payload).digest('hex')
    await fetch(sub.url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Seamount-Signature': sig
      },
      body: payload
    }).catch(err => console.error('Webhook delivery failed:', err.message))
  }
}

export default router