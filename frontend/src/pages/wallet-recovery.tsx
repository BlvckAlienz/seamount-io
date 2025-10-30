// File: frontend/src/pages/wallet-recovery.tsx
// ✅ PRODUCTION READY - WITH PROPER API INTEGRATION

import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../config/api' // ✅ ADD THIS IMPORT
import toast from 'react-hot-toast' // ✅ ADD FOR ERROR HANDLING

interface WalletSeeds {
  user_id: string
  warning: string
  backup_instruction: string
  algorand_seed: string | null
  wdk_seed: string | null
  wallet_addresses: {
    [chain: string]: string
  }
  wdk_service_status?: string
}

const WalletRecovery = () => {
  const { user } = useAuth()
  const navigate = useNavigate()
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

  // ✅ FIXED: Use proper apiClient with correct endpoint
  const fetchSeeds = async () => {
    try {
      setLoading(true)
      setError('')
      
      // ✅ CORRECT ENDPOINT: Use your actual API endpoint
      const response = await apiClient.get('/api/v1/wallet/recovery-seeds')
      
      if (response.data.success) {
        setSeeds(response.data)
        toast.success('Recovery seeds loaded successfully')
      } else {
        throw new Error(response.data.error || 'Failed to fetch seeds')
      }
    } catch (err: any) {
      console.error('Seed fetch error:', err)
      const errorMessage = err.response?.data?.error || err.message || 'Failed to fetch seeds'
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  // ✅ FIXED: Proper navigation
  const handleReturnToDashboard = () => {
    navigate('/dashboard')
  }

  // ✅ ADD: Retry function for failed loads
  const handleRetry = () => {
    fetchSeeds()
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your wallet seeds...</p>
        </div>
      </div>
    )
  }

  if (error && !seeds) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-4">
            <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading Seeds</h3>
            <p className="text-red-700 mb-4">{error}</p>
            <button
              onClick={handleRetry}
              className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
            >
              Try Again
            </button>
          </div>
          <button
            onClick={handleReturnToDashboard}
            className="text-blue-600 hover:text-blue-800 underline"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Security Warning */}
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-8">
          <div className="flex items-start">
            <div className="flex-shrink-0 pt-0.5">
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
            <div className="bg-gray-50 p-4 rounded border font-mono text-lg">
              {seeds.algorand_seed}
            </div>
            <p className="text-sm text-gray-500 mt-2">
              Address: {seeds.wallet_addresses?.algorand || 'Not available'}
            </p>
          </div>
        )}

        {/* WDK Seed */}
        {seeds?.wdk_seed && (
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">🔗 Multi-Chain Seed (WDK)</h2>
            <p className="text-gray-600 mb-4">This single seed controls your Bitcoin, Ethereum, Polygon, and Tron wallets.</p>
            
            <div className="bg-gray-50 p-4 rounded border font-mono text-lg">
              {seeds.wdk_seed}
            </div>
            
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              {Object.entries(seeds.wallet_addresses || {}).map(([chain, address]) => 
                chain !== 'algorand' && (
                  <div key={chain} className="flex flex-col">
                    <span className="font-medium capitalize text-gray-700">{chain}:</span>
                    <span className="text-gray-600 font-mono text-xs break-all">{address}</span>
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
            <div className="mt-4 flex gap-3">
              <button
                onClick={handleRetry}
                className="bg-yellow-600 text-white px-4 py-2 rounded-lg hover:bg-yellow-700 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={handleReturnToDashboard}
                className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
              >
                Return to Dashboard
              </button>
            </div>
          </div>
        )}

        {/* Backup Confirmation */}
        {(seeds?.algorand_seed || seeds?.wdk_seed) && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="text-lg font-medium text-blue-800 mb-2">✅ Backup Confirmation</h3>
            <p className="text-blue-700 mb-4">
              I have securely stored my seed phrases and understand that losing them means permanent loss of my funds.
            </p>
            <button
              onClick={handleReturnToDashboard}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              I've Saved My Seeds - Return to Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default WalletRecovery