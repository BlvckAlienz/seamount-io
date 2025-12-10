// File: frontend/src/components/WalletConnector.tsx
import React, { useState } from 'react'
import { useAppKit } from '@reown/appkit/react'
import { useWalletConnect } from '../contexts/WalletConnectContext'

interface WalletConnectorProps {
  blockchain: 'base' | 'celo'
  className?: string
}

export function WalletConnector({ blockchain, className = '' }: WalletConnectorProps) {
  const { open } = useAppKit()
  const { 
    isConnected, 
    address, 
    chainId, 
    connectWallet, 
    disconnectWallet,
    connectedChains,
    isConnecting,
    error 
  } = useWalletConnect()

  const [localError, setLocalError] = useState<string | null>(null)

  const chainInfo = {
    base: { name: 'Base', id: 8453, icon: '🔵' },
    celo: { name: 'Celo', id: 42220, icon: '🌿' }
  }

  const chain = chainInfo[blockchain]
  const isChainConnected = connectedChains.includes(blockchain)
  const isCorrectChain = chainId === chain.id

  const handleConnect = async () => {
    setLocalError(null)

    try {
      if (!isConnected) {
        // Open WalletConnect modal
        await open()
      } else if (!isCorrectChain) {
        // Ask user to switch network
        setLocalError(`Please switch to ${chain.name} network in your wallet`)
      } else {
        // Save connection to backend
        await connectWallet(blockchain)
      }
    } catch (err: any) {
      setLocalError(err.message || 'Connection failed')
    }
  }

  const handleDisconnect = async () => {
    try {
      await disconnectWallet(blockchain)
    } catch (err: any) {
      setLocalError(err.message || 'Disconnection failed')
    }
  }

  if (isChainConnected) {
    return (
      <div className={`p-4 border border-green-500 rounded-lg bg-green-50 ${className}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold text-green-900">
              {chain.icon} {chain.name} Connected
            </p>
            <p className="text-sm text-green-700">
              {address?.slice(0, 6)}...{address?.slice(-4)}
            </p>
          </div>
          <button
            onClick={handleDisconnect}
            className="px-4 py-2 text-sm text-red-600 hover:text-red-800"
          >
            Disconnect
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`p-4 border border-gray-300 rounded-lg ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="font-semibold text-gray-900">
            {chain.icon} {chain.name}
          </p>
          <p className="text-sm text-gray-600">
            Connect your existing wallet
          </p>
        </div>
        <button
          onClick={handleConnect}
          disabled={isConnecting}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {isConnecting ? 'Connecting...' : 'Connect'}
        </button>
      </div>

      {(error || localError) && (
        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error || localError}
        </div>
      )}

      {isConnected && !isCorrectChain && (
        <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-700">
          ⚠️ Please switch to {chain.name} network in your wallet
        </div>
      )}
    </div>
  )
}