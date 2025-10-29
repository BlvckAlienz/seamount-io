// File: frontend/src/pages/wallet-recovery.tsx
// ✅ PRODUCTION READY - React Router Version
import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom' // ✅ React Router navigation

interface WalletSeeds {
  user_id: string
  warning: string
  backup_instruction: string
  algorand_seed: string | null
  wdk_seed: string | null
  wallet_addresses: {
    [chain: string]: string
  }
  wdk_service_status?: string // ✅ Added service status
}

const WalletRecovery = () => {
  const { user } = useAuth()
  const navigate = useNavigate() // ✅ React Router navigation
  const [seeds, setSeeds] = useState<WalletSeeds | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) {
      navigate('/login')
      return
    }
    fetchSeeds()
  }, [user, navigate])

  const fetchSeeds = async () => {
    try {
      const response = await fetch('/api/wallet-recovery/seeds', {
        headers: {
          'Authorization': `Bearer ${user.access_token}`
        }
      })
      
      if (!response.ok) throw new Error('Failed to fetch seeds')
      
      const data: WalletSeeds = await response.json()
      setSeeds(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // ✅ Fixed navigation handler
  const handleReturnToDashboard = () => {
    navigate('/dashboard')
  }

  if (loading) return <div className="p-8 text-center">Loading your wallet seeds...</div>
  if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Security Warning */}
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-8">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-lg font-medium text-red-800">Security Warning</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>These seed phrases control access to your digital assets. Anyone with these seeds can steal your funds.</p>
                <p className="mt-1"><strong>Never share these with anyone! Not even Seamount support!</strong></p>
              </div>
            </div>
          </div>
        </div>

        <h1 className="text-3xl font-bold text-gray-900 mb-2">Wallet Recovery Seeds</h1>
        <p className="text-gray-600 mb-8">Save these seeds securely to recover your wallets if you lose access.</p>

        {/* Algorand Seed */}
        {seeds?.algorand_seed && (
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">🌐 Algorand Seed Phrase</h2>
            <div className="bg-gray-50 p-4 rounded border">
              <p className="text-lg font-mono select-all">{seeds.algorand_seed}</p>
            </div>
            <p className="text-sm text-gray-500 mt-2">Address: {seeds.wallet_addresses?.algorand}</p>
          </div>
        )}

        {/* WDK Seed */}
        {seeds?.wdk_seed && (
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">🔗 Multi-Chain Seed (WDK)</h2>
            <p className="text-gray-600 mb-4">This single seed controls your Bitcoin, Ethereum, Polygon, and Tron wallets.</p>
            
            {/* ✅ Service Status Indicator */}
            {seeds.wdk_service_status && (
              <div className={`mb-4 p-3 rounded-lg text-sm ${
                seeds.wdk_service_status === 'offline' 
                  ? 'bg-yellow-50 border border-yellow-200 text-yellow-800'
                  : 'bg-blue-50 border border-blue-200 text-blue-800'
              }`}>
                {seeds.wdk_service_status === 'offline' ? '⚠️' : '🔄'} {seeds.wdk_seed}
              </div>
            )}
            
            {!seeds.wdk_service_status && (
              <div className="bg-gray-50 p-4 rounded border">
                <p className="text-lg font-mono select-all">{seeds.wdk_seed}</p>
              </div>
            )}
            
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
              {Object.entries(seeds.wallet_addresses || {}).map(([chain, address]) => 
                chain !== 'algorand' && (
                  <div key={chain} className="flex justify-between">
                    <span className="font-medium capitalize">{chain}:</span>
                    <span className="text-gray-600 font-mono text-xs">{address}</span>
                  </div>
                )
              )}
            </div>
          </div>
        )}

        {/* No Seeds Available */}
        {(!seeds?.algorand_seed && !seeds?.wdk_seed) && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-yellow-800 mb-2">No Seeds Available</h2>
            <p className="text-yellow-700">
              Your wallet seeds are not available at the moment. This could be because:
            </p>
            <ul className="list-disc list-inside mt-2 text-yellow-700">
              <li>Your wallets are still being created</li>
              <li>The seed recovery service is temporarily unavailable</li>
              <li>There was an issue decrypting your seeds</li>
            </ul>
            <p className="mt-3 text-yellow-700 font-medium">
              Please try again in a few minutes or contact support if this persists.
            </p>
          </div>
        )}

        {/* Backup Confirmation */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-blue-800 mb-2">✅ Backup Confirmation</h3>
          <p className="text-blue-700 mb-4">I have securely stored both seed phrases and understand that losing them means permanent loss of my funds.</p>
          <button
            onClick={handleReturnToDashboard} // ✅ Fixed navigation
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            I've Saved My Seeds - Return to Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}

export default WalletRecovery