import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { WagmiProvider } from 'wagmi'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { config, modal, queryClient } from '../config/walletConnect'
import { useAccount, useDisconnect, useSignMessage, useChainId } from 'wagmi'
import { useAuth } from './AuthContext'
import { apiClient } from '../config/api'
import toast from 'react-hot-toast'

// Context types
interface WalletConnectContextType {
  isConnected: boolean
  address: string | undefined
  chainId: number | undefined
  chainName: string | undefined
  connectWallet: (blockchain: 'base' | 'celo') => Promise<void>
  disconnectWallet: (blockchain: 'base' | 'celo') => Promise<void>
  connectedChains: string[]
  isConnecting: boolean
  error: string | null
}

const WalletConnectContext = createContext<WalletConnectContextType | undefined>(undefined)

// Internal provider
function WalletConnectProviderInternal({ children }: { children: ReactNode }) {
  const { address, isConnected, chain } = useAccount()
  const chainId = useChainId()
  const { disconnect } = useDisconnect()
  const { signMessageAsync } = useSignMessage()
  const { user } = useAuth()
  
  const [connectedChains, setConnectedChains] = useState<string[]>([])
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Chain configurations
  const CHAIN_CONFIGS = {
    base: {
      name: 'Base',
      id: 8453,
      idHex: '0x2105',
      icon: '🔵',
      color: 'from-blue-500 to-blue-700'
    },
    celo: {
      name: 'Celo',
      id: 42220,
      idHex: '0xA4EC',
      icon: '🌿',
      color: 'from-green-500 to-emerald-700'
    }
  }

  // Fetch connected wallets on mount
  useEffect(() => {
    if (user) {
      fetchConnectedWallets()
    }
  }, [user])

  const fetchConnectedWallets = async () => {
    try {
      const response = await apiClient.get('/api/v1/wallet/connected-wallets')
      if (response.data.success) {
        const chains = response.data.wallet_connect_chains || []
        setConnectedChains(chains)
        console.log('✅ Connected wallets:', chains)
      }
    } catch (err) {
      console.error('Failed to fetch connected wallets:', err)
    }
  }

  const connectWallet = async (blockchain: 'base' | 'celo') => {
    if (!user) {
      toast.error('Please sign in to connect wallets')
      return
    }

    setIsConnecting(true)
    setError(null)

    try {
      // Step 1: Open WalletConnect modal if not connected
      if (!isConnected || !address) {
        console.log('🔄 Opening WalletConnect modal...')
        await modal.open()
        
        // Wait for connection
        await new Promise(resolve => setTimeout(resolve, 2000))
        
        if (!isConnected || !address) {
          throw new Error('Wallet connection cancelled or failed')
        }
      }

      const chainConfig = CHAIN_CONFIGS[blockchain]
      
      // Step 2: Verify correct network (accept both hex and decimal)
      const currentChainId = chainId
      const isCorrectChain = currentChainId === chainConfig.id || 
                           `0x${currentChainId?.toString(16)}` === chainConfig.idHex
      
      if (!isCorrectChain) {
        console.log(`⚠️ Wrong network. Current: ${currentChainId}, Expected: ${chainConfig.id}`)
        
        try {
          // Try to switch network via WalletConnect
          await modal.open({ view: 'Networks' })
          toast.error(`Please switch to ${chainConfig.name} network in your wallet`)
          setIsConnecting(false)
          return
        } catch (switchError) {
          throw new Error(`Please switch to ${chainConfig.name} network manually`)
        }
      }

      // Step 3: Get nonce from backend
      toast.loading('Generating authentication challenge...')
      const nonceResponse = await apiClient.post('/api/v1/wallet/nonce', {
        address,
        blockchain
      })

      if (!nonceResponse.data.success) {
        throw new Error(nonceResponse.data.error || 'Failed to generate authentication challenge')
      }

      const { nonce, message } = nonceResponse.data
      toast.dismiss()

      // Step 4: Sign the nonce message
      toast.loading('Please sign the message in your wallet...')
      const signature = await signMessageAsync({ message })

      // Step 5: Detect wallet provider
      let walletProvider = 'walletconnect'
      if ((window as any).ethereum?.isMetaMask) walletProvider = 'metamask'
      else if ((window as any).ethereum?.isCoinbaseWallet) walletProvider = 'coinbase_wallet'
      else if ((window as any).ethereum?.isMiniPay) walletProvider = 'minipay'
      else if ((window as any).ethereum?.isValora) walletProvider = 'valora'

      // Step 6: Send connection request to backend
      const connectResponse = await apiClient.post('/api/v1/wallet/connect', {
        blockchain,
        address,
        wallet_provider: walletProvider,
        signature,
        nonce
      })

      if (!connectResponse.data.success) {
        throw new Error(connectResponse.data.error || 'Failed to connect wallet')
      }

      // Success!
      setConnectedChains(prev => [...new Set([...prev, blockchain])])
      toast.success(`${chainConfig.name} wallet connected successfully!`)
      setError(null)

    } catch (err: any) {
      console.error('❌ Wallet connection error:', err)
      const errorMsg = err.message || 'Failed to connect wallet'
      setError(errorMsg)
      
      if (errorMsg.includes('User rejected')) {
        toast.error('Connection rejected by user')
      } else if (errorMsg.includes('network')) {
        toast.error(`Please switch to ${CHAIN_CONFIGS[blockchain].name} network`)
      } else {
        toast.error(errorMsg)
      }
    } finally {
      setIsConnecting(false)
      toast.dismiss()
    }
  }

  const disconnectWallet = async (blockchain: 'base' | 'celo') => {
    if (!user) return

    try {
      const response = await apiClient.post('/api/v1/wallet/disconnect', { blockchain })
      
      if (response.data.success) {
        setConnectedChains(prev => prev.filter(c => c !== blockchain))
        toast.success(`${CHAIN_CONFIGS[blockchain].name} wallet disconnected`)
        
        // If disconnecting current chain, disconnect from wallet provider too
        if (chainId === CHAIN_CONFIGS[blockchain].id) {
          disconnect()
        }
      }
    } catch (err: any) {
      console.error('Wallet disconnection error:', err)
      toast.error('Failed to disconnect wallet')
    }
  }

  return (
    <WalletConnectContext.Provider
      value={{
        isConnected,
        address,
        chainId,
        chainName: chain?.name,
        connectWallet,
        disconnectWallet,
        connectedChains,
        isConnecting,
        error
      }}
    >
      {children}
    </WalletConnectContext.Provider>
  )
}

// Main provider
export function WalletConnectProvider({ children }: { children: ReactNode }) {
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <WalletConnectProviderInternal>
          {children}
        </WalletConnectProviderInternal>
      </QueryClientProvider>
    </WagmiProvider>
  )
}

// Hook to use WalletConnect
export function useWalletConnect() {
  const context = useContext(WalletConnectContext)
  if (context === undefined) {
    throw new Error('useWalletConnect must be used within WalletConnectProvider')
  }
  return context
}