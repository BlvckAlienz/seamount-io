// File: frontend/src/config/walletConnect.ts
import { defaultWagmiConfig } from '@web3modal/wagmi/react/config'
import { cookieStorage, createStorage } from 'wagmi'
import { base, celo } from 'wagmi/chains'

// ⚠️ REPLACE WITH YOUR ACTUAL PROJECT ID FROM https://cloud.reown.com
export const projectId = import.meta.env.VITE_REOWN_PROJECT_ID || 'PASTE_YOUR_PROJECT_ID_HERE'

if (!projectId || projectId === 'PASTE_YOUR_PROJECT_ID_HERE') {
  console.warn('⚠️ VITE_REOWN_PROJECT_ID not set - WalletConnect will not work in production')
}

// App metadata
const metadata = {
  name: 'Seamount',
  description: 'Cross-border payments & multi-chain treasury',
  url: 'https://seamount.io',
  icons: ['https://seamount.io/logo.png']
}

// Only Base and Celo use WalletConnect
const chains = [base, celo] as const

// Wagmi configuration
export const config = defaultWagmiConfig({
  chains,
  projectId,
  metadata,
  ssr: false,
  storage: createStorage({
    storage: cookieStorage
  }),
  enableWalletConnect: true,
  enableInjected: true, // MetaMask, Coinbase Wallet
  enableEIP6963: true,  // Modern wallet discovery
  enableCoinbase: true  // Coinbase Wallet native
})