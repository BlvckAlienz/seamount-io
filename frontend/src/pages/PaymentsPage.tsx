// FILE: frontend/src/pages/PaymentsPage.tsx
// Rebuilt as a proper page — Sidebar + dark gradient + 3 tabs.
// Replaces the old switch/mode orchestrator that was never wired up.

import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import Sidebar from '@/components/layout/Sidebar'
import { MerchantListings } from '@/components/p2p/MerchantListings'
import { FundWalletModal } from '@/components/wallet/FundWalletModal'
import { SendForm } from '@/components/payments/SendForm'
import { ArrowDownToLine, ShoppingBag, ArrowUpRight } from 'lucide-react'

type Tab = 'p2p' | 'fund' | 'send'

const TABS: { id: Tab; label: string; icon: typeof ShoppingBag; description: string }[] = [
  {
    id: 'p2p',
    label: 'Buy via P2P',
    icon: ShoppingBag,
    description: 'Buy crypto from verified merchants with local payment methods'
  },
  {
    id: 'fund',
    label: 'Fund Wallet',
    icon: ArrowDownToLine,
    description: 'Buy crypto instantly with your local currency via card or bank'
  },
  {
    id: 'send',
    label: 'Send',
    icon: ArrowUpRight,
    description: 'Send crypto to any wallet address across all supported chains'
  },
]

const PaymentsPage = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const [activeTab, setActiveTab]   = useState<Tab>('p2p')
  const [showFund,  setShowFund]    = useState(false)
  const [showSend,  setShowSend]    = useState(false)

  // Support deep-linking: /payments?tab=fund opens Fund tab directly
  useEffect(() => {
    const tab = searchParams.get('tab') as Tab | null
    if (tab && ['p2p', 'fund', 'send'].includes(tab)) {
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

          {/* ── Header ── */}
          <div className="mb-6">
            <h1 className="text-2xl md:text-3xl font-bold text-white">Payments</h1>
            <p className="text-sm text-gray-400 mt-1">
              Buy, send, and manage crypto across all supported chains
            </p>
          </div>

          {/* ── Tab Bar ── */}
          <div className="flex gap-2 mb-6 bg-gray-800/50 rounded-xl p-1.5 border border-gray-700 w-fit">
            {TABS.map(tab => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabClick(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all
                    ${isActive
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                      : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
                    }`}
                >
                  <Icon className="h-4 w-4" />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              )
            })}
          </div>

          {/* ── Active Tab Description ── */}
          <p className="text-sm text-gray-500 mb-4">
            {TABS.find(t => t.id === activeTab)?.description}
          </p>

          {/* ── Tab Content ── */}

          {/* P2P — renders MerchantListings inline */}
          {activeTab === 'p2p' && (
            <div className="bg-gray-800/30 rounded-2xl border border-gray-700/50 p-2 sm:p-4">
              <MerchantListings />
            </div>
          )}

          {/* Fund — shows a CTA card that opens the modal */}
          {activeTab === 'fund' && (
            <div className="flex flex-col items-center justify-center py-16 gap-6">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500/20 to-indigo-500/20 border border-blue-500/30 flex items-center justify-center">
                <ArrowDownToLine className="h-10 w-10 text-blue-400" />
              </div>
              <div className="text-center">
                <h2 className="text-xl font-bold text-white mb-2">Fund Your Wallet</h2>
                <p className="text-gray-400 text-sm max-w-sm">
                  Buy crypto instantly with your local currency using card, bank transfer, or mobile money.
                  Powered by smart provider routing for best rates.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 text-center text-sm w-full max-w-xs">
                {[
                  { label: 'Settlement',  value: '< 30 sec' },
                  { label: 'Fee',         value: '~1–3.5%'  },
                  { label: 'Currencies',  value: '13+'       },
                  { label: 'Chains',      value: '6 chains'  },
                ].map((s, i) => (
                  <div key={i} className="bg-gray-800/50 rounded-xl p-3 border border-gray-700">
                    <div className="text-blue-400 font-bold">{s.value}</div>
                    <div className="text-gray-500 text-xs mt-0.5">{s.label}</div>
                  </div>
                ))}
              </div>
              <button
                onClick={() => setShowFund(true)}
                className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl transition-all gap-2 flex items-center"
              >
                <ArrowDownToLine className="h-5 w-5" />
                Open Fund Wallet
              </button>
            </div>
          )}

          {/* Send — shows a CTA card that opens the modal */}
          {activeTab === 'send' && (
            <div className="flex flex-col items-center justify-center py-16 gap-6">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-green-500/20 to-emerald-500/20 border border-green-500/30 flex items-center justify-center">
                <ArrowUpRight className="h-10 w-10 text-green-400" />
              </div>
              <div className="text-center">
                <h2 className="text-xl font-bold text-white mb-2">Send Crypto</h2>
                <p className="text-gray-400 text-sm max-w-sm">
                  Send any supported token to any wallet address. Smart routing automatically
                  selects the optimal chain. QR code scanning supported.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 text-center text-sm w-full max-w-xs">
                {[
                  { label: 'Fastest chain', value: '0.4 sec'  },
                  { label: 'Lowest fee',    value: '< $0.01'  },
                  { label: 'Tokens',        value: '18+'       },
                  { label: 'Chains',        value: '6 chains'  },
                ].map((s, i) => (
                  <div key={i} className="bg-gray-800/50 rounded-xl p-3 border border-gray-700">
                    <div className="text-green-400 font-bold">{s.value}</div>
                    <div className="text-gray-500 text-xs mt-0.5">{s.label}</div>
                  </div>
                ))}
              </div>
              <button
                onClick={() => setShowSend(true)}
                className="px-8 py-3 bg-green-600 hover:bg-green-700 text-white font-bold rounded-xl transition-all gap-2 flex items-center"
              >
                <ArrowUpRight className="h-5 w-5" />
                Open Send Form
              </button>
            </div>
          )}

        </div>
      </div>

      {/* ── Modals ── */}
      <FundWalletModal
        open={showFund}
        onOpenChange={open => {
          setShowFund(open)
          if (!open && activeTab === 'fund') setActiveTab('fund')
        }}
      />
      <SendForm
        open={showSend}
        onOpenChange={open => {
          setShowSend(open)
          if (!open && activeTab === 'send') setActiveTab('send')
        }}
      />
    </div>
  )
}

export default PaymentsPage