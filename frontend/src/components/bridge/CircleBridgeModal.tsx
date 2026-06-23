// FILE: frontend/src/components/bridge/CircleBridgeModal.tsx
// Circle CCTP Cross-Chain USDC Bridge
// Clean 3-step flow: Configure → Review (with fees) → Status tracking

import React, { useState, useEffect, useCallback } from 'react'
import { X, ArrowRight, Bridge, Loader2, CheckCircle2, AlertCircle, RefreshCw, Info } from 'lucide-react'
import { apiClient } from '@/config/api'
import toast from 'react-hot-toast'

interface CircleBridgeModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// Curated mainnet chains (subset of App Kit supported)
const BRIDGE_CHAINS = [
  { id: 'Ethereum',  label: 'Ethereum',  icon: '⬡', explorer: 'etherscan.io' },
  { id: 'Polygon',   label: 'Polygon',   icon: '⬣', explorer: 'polygonscan.com' },
  { id: 'Base',      label: 'Base',      icon: '🔵', explorer: 'basescan.org' },
  { id: 'Arbitrum',  label: 'Arbitrum',  icon: '🔷', explorer: 'arbiscan.io' },
  { id: 'Avalanche', label: 'Avalanche', icon: '🔺', explorer: 'snowtrace.io' },
  { id: 'Solana',    label: 'Solana',    icon: '◎', explorer: 'explorer.solana.com' },
]

type BridgeStep = { name: string; state: 'pending' | 'success' | 'error' | 'noop'; txHash?: string; explorerUrl?: string; error?: string }
type BridgeState = 'idle' | 'estimating' | 'ready' | 'bridging' | 'done' | 'error'

const STEP_LABELS: Record<string, string> = {
  approve         : 'Approving USDC spend',
  burn            : 'Burning USDC on source chain',
  fetchAttestation: 'Waiting for Circle attestation',
  mint            : 'Minting USDC on destination',
}

export const CircleBridgeModal: React.FC<CircleBridgeModalProps> = ({ open, onOpenChange }) => {
  const [fromChain,    setFromChain]    = useState('Ethereum')
  const [toChain,      setToChain]      = useState('Base')
  const [amount,       setAmount]       = useState('')
  const [bridgeState,  setBridgeState]  = useState<BridgeState>('idle')
  const [estimate,     setEstimate]     = useState<any>(null)
  const [bridgeResult, setBridgeResult] = useState<any>(null)
  const [steps,        setSteps]        = useState<BridgeStep[]>([])
  const [error,        setError]        = useState('')

  // Reset on close
  useEffect(() => {
    if (!open) {
      setTimeout(() => {
        setAmount(''); setEstimate(null); setBridgeResult(null)
        setSteps([]); setError(''); setBridgeState('idle')
      }, 300)
    }
  }, [open])

  // Auto-swap chains if user picks same for both
  const handleFromChain = (chain: string) => {
    setFromChain(chain)
    if (chain === toChain) setToChain(BRIDGE_CHAINS.find(c => c.id !== chain)!.id)
    setEstimate(null)
  }
  const handleToChain = (chain: string) => {
    setToChain(chain)
    if (chain === fromChain) setFromChain(BRIDGE_CHAINS.find(c => c.id !== chain)!.id)
    setEstimate(null)
  }

  const getEstimate = useCallback(async () => {
    if (!amount || parseFloat(amount) < 1) return
    setBridgeState('estimating')
    setError('')
    try {
      const res = await apiClient.post('/api/v1/circle/bridge/estimate', {
        from_chain: fromChain, to_chain: toChain, amount,
      })
      if (res.data?.success) {
        setEstimate(res.data)
        setBridgeState('ready')
      } else {
        throw new Error(res.data?.error || 'Estimate failed')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message)
      setBridgeState('idle')
    }
  }, [fromChain, toChain, amount])

  const executeBridge = async () => {
    if (!estimate) return
    setBridgeState('bridging')
    setError('')
    setSteps([])

    try {
      const res = await apiClient.post('/api/v1/circle/bridge', {
        from_chain: fromChain,
        to_chain  : toChain,
        amount,
        transfer_speed: 'FAST',
      })
      const data = res.data
      setBridgeResult(data)
      setSteps(data.steps || [])

      if (data.success || data.state === 'success') {
        setBridgeState('done')
        toast.success(`✅ ${amount} USDC bridged ${fromChain} → ${toChain}!`, { duration: 6000 })
      } else if (data.state === 'pending') {
        // Pending = in flight (attestation phase) — still show as success-ish
        setBridgeState('done')
        toast.success(`🚀 Bridge in progress — USDC will arrive on ${toChain} shortly.`, { duration: 8000 })
      } else {
        setError(data.error || 'Bridge returned unknown state')
        setBridgeState('error')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Bridge failed'
      setError(msg)
      setBridgeState('error')
      toast.error(msg)
    }
  }

  const retryBridge = async () => {
    if (!bridgeResult) return
    setBridgeState('bridging')
    setError('')
    try {
      const res = await apiClient.post('/api/v1/circle/bridge/retry', { bridge_result: bridgeResult })
      const data = res.data
      setSteps(data.steps || [])
      if (data.success || data.state === 'success') {
        setBridgeState('done')
        toast.success('✅ Bridge retry successful!')
      } else {
        setError(data.error || 'Retry failed')
        setBridgeState('error')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message)
      setBridgeState('error')
    }
  }

  if (!open) return null

  // ── Step tracker ────────────────────────────────────────────────────────────
  const StepRow = ({ step }: { step: BridgeStep }) => (
    <div className="flex items-center gap-3 py-2">
      <span className="w-5 h-5 flex-shrink-0">
        {step.state === 'success' && <CheckCircle2 className="text-green-400 w-5 h-5" />}
        {step.state === 'error'   && <AlertCircle  className="text-red-400   w-5 h-5" />}
        {step.state === 'pending' && <Loader2       className="text-blue-400  w-5 h-5 animate-spin" />}
        {step.state === 'noop' && <div className="w-5 h-5 rounded-full border border-gray-300" />}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-900 font-medium">{STEP_LABELS[step.name] || step.name}</p>
        {step.explorerUrl && (
          <a href={step.explorerUrl} target="_blank" rel="noopener noreferrer"
             className="text-xs text-blue-400 hover:text-blue-300 truncate block">
            {step.txHash?.slice(0, 16)}... ↗
          </a>
        )}
        {step.error && <p className="text-xs text-red-400 truncate">{step.error}</p>}
      </div>
    </div>
  )

  // ── Fee row helper ──────────────────────────────────────────────────────────
  const FeeRow = ({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) => (
    <div className="flex justify-between text-sm py-1">
      <span className="text-gray-500">{label}</span>
      <span className={highlight ? 'text-green-600 font-semibold' : 'text-gray-900'}>{value}</span>
    </div>
  )

  const seamountFee = estimate?.seamount_fee ? parseFloat(estimate.seamount_fee) : 0
  const cctpFees    = (estimate?.fees || []).find((f: any) => f.type === 'provider')
  const cctpFeeAmt  = cctpFees?.amount ? parseFloat(cctpFees.amount) : null
  const amountNum   = parseFloat(amount) || 0
  const estimatedReceive = amountNum - seamountFee - (cctpFeeAmt || 0)

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4"
         onClick={e => e.target === e.currentTarget && onOpenChange(false)}>
      <div className="bg-white rounded-2xl w-full max-w-md border border-gray-200 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <ArrowRight className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-gray-900 font-bold text-lg">Bridge USDC</h2>
              <p className="text-xs text-gray-500">Circle CCTP — Cross-chain transfer</p>
            </div>
          </div>
          <button onClick={() => onOpenChange(false)}
                  className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-700 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* From / To chain selectors */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 font-medium mb-1 block">From</label>
              <select value={fromChain} onChange={e => handleFromChain(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none">
                {BRIDGE_CHAINS.map(c => (
                  <option key={c.id} value={c.id} disabled={c.id === toChain}>
                    {c.icon} {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium mb-1 block">To</label>
              <select value={toChain} onChange={e => handleToChain(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none">
                {BRIDGE_CHAINS.map(c => (
                  <option key={c.id} value={c.id} disabled={c.id === fromChain}>
                    {c.icon} {c.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Amount */}
          <div>
            <label className="text-xs text-gray-500 font-medium mb-1 block">Amount (USDC)</label>
            <div className="relative">
              <input
                type="number" min="1" step="0.01"
                placeholder="Minimum 1.00"
                value={amount}
                onChange={e => { setAmount(e.target.value); setEstimate(null); setBridgeState('idle') }}
                className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-lg px-3 py-2.5 text-sm pr-16 focus:border-blue-500 focus:outline-none"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs font-medium">USDC</span>
            </div>
          </div>

          {/* Steps (during/after bridge) */}
          {steps.length > 0 && (
            <div className="bg-gray-50 rounded-xl p-3 border border-gray-200 space-y-0.5">
              {steps.map((s, i) => <StepRow key={i} step={s} />)}
            </div>
          )}

          {/* Fee estimate */}
          {estimate && bridgeState === 'ready' && (
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 space-y-1">
              <div className="flex items-center gap-2 mb-2">
                <Info className="w-4 h-4 text-blue-600" />
                <span className="text-xs text-blue-700 font-semibold uppercase tracking-wide">Fee Breakdown</span>
              </div>
              <FeeRow label="You send"          value={`${amountNum.toFixed(2)} USDC`} />
              <FeeRow label="Seamount fee (0.5%)" value={`-${seamountFee.toFixed(4)} USDC`} />
              {cctpFeeAmt !== null && (
                <FeeRow label="CCTP protocol fee" value={`-${cctpFeeAmt.toFixed(4)} USDC`} />
              )}
              <div className="border-t border-blue-200 pt-2 mt-2">
                <FeeRow label="You receive (est.)" value={`~${estimatedReceive.toFixed(2)} USDC`} highlight />
              </div>
            </div>
          )}

          {/* Error display */}
          {error && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Info */}
          <div className="flex items-start gap-2 text-xs text-gray-400">
            <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
            <span>FAST transfers: ~2–5 min. USDC only. Powered by Circle CCTP.</span>
          </div>
        </div>

        {/* Footer buttons */}
        <div className="p-5 pt-0 space-y-2">
          {bridgeState === 'idle' && (
            <button
              onClick={getEstimate}
              disabled={!amount || parseFloat(amount) < 1}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white py-3 rounded-xl font-semibold transition-colors">
              Get Estimate
            </button>
          )}

          {bridgeState === 'estimating' && (
            <button disabled className="w-full bg-blue-600/50 text-white py-3 rounded-xl font-semibold flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Estimating fees...
            </button>
          )}

          {bridgeState === 'ready' && (
            <>
              <button onClick={executeBridge}
                      className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-xl font-bold transition-colors flex items-center justify-center gap-2">
                <ArrowRight className="w-4 h-4" />
                Confirm Bridge  {amount} USDC
              </button>
              <button onClick={() => { setEstimate(null); setBridgeState('idle') }}
                      className="w-full text-gray-400 hover:text-gray-700 py-2 text-sm transition-colors">
                ← Change amount
              </button>
            </>
          )}

          {bridgeState === 'bridging' && (
            <button disabled className="w-full bg-yellow-600/50 text-white py-3 rounded-xl font-semibold flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Bridge in progress...
            </button>
          )}

          {bridgeState === 'done' && (
            <button onClick={() => onOpenChange(false)}
                    className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-xl font-bold flex items-center justify-center gap-2">
              <CheckCircle2 className="w-4 h-4" /> Done ✓
            </button>
          )}

          {bridgeState === 'error' && (
            <div className="grid grid-cols-2 gap-2">
              {bridgeResult && (
                <button onClick={retryBridge}
                        className="flex items-center justify-center gap-2 bg-yellow-600 hover:bg-yellow-700 text-white py-3 rounded-xl font-semibold transition-colors">
                  <RefreshCw className="w-4 h-4" /> Retry
                </button>
              )}
              <button onClick={() => { setError(''); setBridgeState('idle'); setEstimate(null) }}
                      className={`bg-gray-100 hover:bg-gray-200 text-gray-900 py-3 rounded-xl font-semibold ${!bridgeResult ? 'col-span-2' : ''}`}>
                Start Over
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default CircleBridgeModal