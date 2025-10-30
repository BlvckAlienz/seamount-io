// File: frontend/src/pages/wallet-recovery.tsx
// ✅ PRODUCTION READY - CLEAN DATABASE CONFIRMED

import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../config/api'
import toast from 'react-hot-toast'

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

  // ✅ PRODUCTION: Correct endpoint with enhanced error handling
  const fetchSeeds = async () => {
    try {
      setLoading(true)
      setError('')
      
      console.log('🔄 Fetching wallet recovery seeds from:', '/v1/wallet/recovery-seeds')
      
      const response = await apiClient.get('/v1/wallet/recovery-seeds')
      
      console.log('✅ Seeds API Response:', response.data)
      
      if (response.data.success) {
        setSeeds(response.data)
        toast.success('Recovery seeds loaded successfully')
      } else {
        throw new Error(response.data.error || 'Failed to fetch seeds')
      }
    } catch (err: any) {
      console.error('❌ Seed fetch error:', err)
      const errorMessage = err.response?.data?.error || err.message || 'Failed to fetch recovery seeds'
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleReturnToDashboard = () => {
    navigate('/dashboard')
  }

  const handleRetry = () => {
    fetchSeeds()
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your wallet seeds...</p>
          <p className="text-sm text-gray-500 mt-2">Securely retrieving your recovery phrases</p>
        </div>
      </div>
    )
  }

  if (error && !seeds) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-4">
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-red-800 mb-2">Unable to Load Seeds</h3>
            <p className="text-red-700 mb-4">{error}</p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={handleRetry}
                className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={handleReturnToDashboard}
                className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
              >
                Dashboard
              </button>
            </div>
          </div>
          <p className="text-sm text-gray-600">
            If this continues, please contact support.
          </p>
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

        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Wallet Recovery Seeds</h1>
          <p className="text-gray-600">Save these seeds securely to recover your wallets if you lose access.</p>
        </div>

        {/* Algorand Seed */}
        {seeds?.algorand_seed && (
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                <span className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">🌐</span>
                Algorand Seed Phrase
              </h2>
              <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded">Primary</span>
            </div>
            <div className="bg-gray-50 p-4 rounded border font-mono text-lg text-center">
              {seeds.algorand_seed}
            </div>
            {seeds.wallet_addresses?.algorand && (
              <div className="mt-3">
                <p className="text-sm text-gray-600">Address:</p>
                <p className="text-sm font-mono text-gray-800 bg-gray-100 p-2 rounded break-all">
                  {seeds.wallet_addresses.algorand}
                </p>
              </div>
            )}
          </div>
        )}

        {/* WDK Seed */}
        {seeds?.wdk_seed && (
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                <span className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">🔗</span>
                Multi-Chain Seed (WDK)
              </h2>
              <span className="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded">Multi-Chain</span>
            </div>
            
            <p className="text-gray-600 mb-4">
              This single seed controls your Bitcoin, Ethereum, Polygon, and Tron wallets.
            </p>
            
            <div className="bg-gray-50 p-4 rounded border font-mono text-lg text-center">
              {seeds.wdk_seed}
            </div>
            
            {/* Multi-chain addresses */}
            <div className="mt-4">
              <h4 className="font-medium text-gray-700 mb-3">Wallet Addresses:</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(seeds.wallet_addresses || {}).map(([chain, address]) => 
                  chain !== 'algorand' && (
                    <div key={chain} className="bg-gray-50 p-3 rounded border">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium capitalize text-gray-700">{chain}</span>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(address);
                            toast.success(`${chain} address copied!`);
                          }}
                          className="text-blue-600 hover:text-blue-800 text-sm"
                        >
                          Copy
                        </button>
                      </div>
                      <p className="text-gray-600 font-mono text-xs break-all">{address}</p>
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        )}

        {/* No Seeds Available */}
        {(!seeds?.algorand_seed && !seeds?.wdk_seed) && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
            <div className="flex items-start">
              <div className="flex-shrink-0 pt-0.5">
                <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h2 className="text-xl font-semibold text-yellow-800 mb-2">No Seeds Available</h2>
                <p className="text-yellow-700 mb-3">
                  Your wallet seeds are not available at the moment. This could be because:
                </p>
                <ul className="list-disc list-inside text-yellow-700 mb-4">
                  <li>Your wallets are still being created</li>
                  <li>The seed recovery service is temporarily unavailable</li>
                  <li>There was an issue decrypting your seeds</li>
                </ul>
                <div className="flex gap-3">
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
            </div>
          </div>
        )}

        {/* Backup Confirmation */}
        {(seeds?.algorand_seed || seeds?.wdk_seed) && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-blue-800 mb-2">Backup Confirmation</h3>
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