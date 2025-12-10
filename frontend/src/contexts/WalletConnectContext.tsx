// File: frontend/src/contexts/WalletConnectContext.tsx
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { WagmiProvider } from 'wagmi'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createWeb3Modal } from '@web3modal/wagmi/react'
import { config, projectId } from '../config/walletConnect'
import { useAccount, useDisconnect, useSignMessage } from 'wagmi'
import { useAuth } from './AuthContext'
import { apiClient } from '../config/api'
import toast from 'react-hot-toast'

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1
    }
  }
})

// Create Web3Modal
createWeb3Modal({
  wagmiConfig: config,
  projectId,
  enableAnalytics: false,
  themeMode: 'dark',
  themeVariables: {
    '--w3m-accent': '#6366f1',
    '--w3m-border-radius-master': '8px'
  }
})

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

// Internal provider (uses wagmi hooks)
function WalletConnectProviderInternal({ children }: { children: ReactNode }) {
  const { address, isConnected, chainId, chain } = useAccount()
  const { disconnect } = useDisconnect()
  const { signMessageAsync } = useSignMessage()
  const { user } = useAuth()
  
  const [connectedChains, setConnectedChains] = useState<string[]>([])
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
      }
    } catch (err) {
      console.error('Failed to fetch connected wallets:', err)
    }
  }

  const connectWallet = async (blockchain: 'base' | 'celo') => {
    if (!user) {
      toast.error('Please sign in first')
      return
    }

    setIsConnecting(true)
    setError(null)

    try {
      // Verify wallet is connected
      if (!isConnected || !address) {
        toast.error('Please connect your wallet first')
        setIsConnecting(false)
        return
      }

      // Verify correct chain
      const expectedChainId = blockchain === 'base' ? 8453 : 42220
      if (chainId !== expectedChainId) {
        toast.error(`Please switch to ${blockchain === 'base' ? 'Base' : 'Celo'} network in your wallet`)
        setIsConnecting(false)
        return
      }

      // Sign message to prove ownership
      const message = `Connect ${blockchain} wallet to Seamount\n\nAddress: ${address}\nTimestamp: ${Date.now()}`
      
      toast.loading('Please sign the message in your wallet...')
      const signature = await signMessageAsync({ message })

      // Detect wallet provider
      let walletProvider = 'walletconnect'
      if ((window as any).ethereum?.isMetaMask) walletProvider = 'metamask'
      else if ((window as any).ethereum?.isCoinbaseWallet) walletProvider = 'coinbase_wallet'
      else if ((window as any).ethereum?.isRabby) walletProvider = 'rabby'

      // Save to backend
      const response = await apiClient.post('/api/v1/wallet/connect', {
        blockchain,
        address,
        wallet_provider: walletProvider,
        signature,
        message
      })

      if (response.data.success) {
        setConnectedChains(prev => [...new Set([...prev, blockchain])])
        toast.success(`${blockchain === 'base' ? 'Base' : 'Celo'} wallet connected!`)
        setError(null)
      } else {
        throw new Error(response.data.error || 'Failed to connect wallet')
      }
    } catch (err: any) {
      console.error('Wallet connection error:', err)
      const errorMsg = err.message || 'Failed to connect wallet'
      setError(errorMsg)
      toast.error(errorMsg)
      throw err
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
        toast.success(`${blockchain === 'base' ? 'Base' : 'Celo'} wallet disconnected`)
        
        // If disconnecting current chain, disconnect from wallet provider too
        if (chainId === (blockchain === 'base' ? 8453 : 42220)) {
          disconnect()
        }
      }
    } catch (err: any) {
      console.error('Wallet disconnection error:', err)
      toast.error('Failed to disconnect wallet')
      throw err
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

// Main provider (wraps with Wagmi/QueryClient)
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