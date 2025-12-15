import { createAppKit } from '@reown/appkit/react'
import { WagmiAdapter } from '@reown/appkit-adapter-wagmi'
import { base, celo } from '@reown/appkit/networks'
import { QueryClient } from '@tanstack/react-query'
import { WagmiProvider } from 'wagmi'

export const projectId = 'cc4e6128dba540ad2ef4a2d8328c8c90'

if (!projectId) {
  console.error('❌ VITE_REOWN_PROJECT_ID not set - WalletConnect will not work')
  throw new Error('Missing WalletConnect Project ID')
}

console.log('✅ WalletConnect Project ID loaded:', projectId.slice(0, 8) + '...')

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
    url: 'https://www.seamount.io',
    icons: ['https://www.seamount.io/logo.png']
  },
  features: {
    analytics: false, // 🚨 DISABLE to fix 403 error
    email: false,
    socials: false,
    allWallets: true
  },
  themeVariables: {
    '--w3m-accent': '#0052FF',
    '--w3m-border-radius-master': '12px'
  }
})

// 3️⃣ Export Wagmi Config
export const config = wagmiAdapter.wagmiConfig

// 4️⃣ Query Client
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000
    }
  }
})

export { WagmiProvider }

// ============================================================================
// 🔇 SUPPRESS WALLETCONNECT PULSE 403 ERRORS
// ============================================================================
if (typeof window !== 'undefined') {
  const originalFetch = window.fetch;
  
  window.fetch = async (...args) => {
    const url = args[0]?.toString() || '';
    
    // ✅ Block pulse.walletconnect.org requests entirely
    if (url.includes('pulse.walletconnect.org')) {
      console.log('ℹ️ WalletConnect analytics disabled - blocking pulse request');
      // Return fake successful response immediately
      return new Response(JSON.stringify({ success: true }), { 
        status: 200,
        statusText: 'OK',
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // All other requests proceed normally
    return originalFetch(...args);
  };
}