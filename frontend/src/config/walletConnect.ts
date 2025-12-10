// File: frontend/src/config/walletConnect.ts
import { createAppKit } from '@reown/appkit/react'
import { WagmiAdapter } from '@reown/appkit-adapter-wagmi'
import { base, celo } from '@reown/appkit/networks'
import { QueryClient } from '@tanstack/react-query'
import { WagmiProvider } from 'wagmi'

// ⚠️ REPLACE WITH YOUR PROJECT ID FROM https://cloud.reown.com
export const projectId = import.meta.env.VITE_REOWN_PROJECT_ID || 'PASTE_YOUR_PROJECT_ID_HERE'

if (!projectId || projectId === 'PASTE_YOUR_PROJECT_ID_HERE') {
  console.warn('⚠️ VITE_REOWN_PROJECT_ID not set - WalletConnect will not work')
}

// 1️⃣ Create Wagmi Adapter
export const wagmiAdapter = new WagmiAdapter({
  projectId,
  networks: [base, celo]
})

// 2️⃣ Create AppKit Modal
export const modal = createAppKit({
  adapters: [wagmiAdapter],
  networks: [base, celo],
  projectId,
  metadata: {
    name: 'Seamount',
    description: 'Cross-border payments & multi-chain treasury',
    url: 'https://seamount.io',
    icons: ['https://seamount.io/logo.png']
  },
  features: {
    analytics: false
  }
})

// 3️⃣ Export Wagmi Config
export const config = wagmiAdapter.wagmiConfig

// 4️⃣ Query Client
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1
    }
  }
})

export { WagmiProvider }