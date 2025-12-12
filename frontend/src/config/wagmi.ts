// src/config/wagmi.ts
import { createConfig, http } from 'wagmi';
import { base, mainnet } from 'wagmi/chains';
import { injected, walletConnect } from 'wagmi/connectors';

// Your WalletConnect Project ID
const projectId = 'cc4e6128dba540ad2ef4a2d8328c8c90';

export const config = createConfig({
  chains: [base, mainnet],
  connectors: [
    injected(),
    walletConnect({
      projectId,
      metadata: {
        name: 'Seamount',
        description: 'Seamount Platform',
        url: typeof window !== 'undefined' ? window.location.origin : 'https://seamount.io',
        icons: ['https://seamount.io/icon.png']
      }
    })
  ],
  transports: {
    [base.id]: http(),
    [mainnet.id]: http(),
  },
  ssr: false,
});