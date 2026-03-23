// ═══════════════════════════════════════════════════════════════
// SHARED CONSTANT — add this to a shared file or copy into each component
// frontend/src/components/p2p/p2pTokens.ts  (NEW FILE — create this)
// ═══════════════════════════════════════════════════════════════

export const P2P_TOKEN_OPTIONS = [
  // Algorand
  { value: 'ALGO',          label: 'Algorand (ALGO)',       chain: 'algorand' },
  { value: 'USDT_ALGO',     label: 'Tether (Algorand)',     chain: 'algorand' },
  { value: 'USDCa',         label: 'USD Coin (Algorand)',   chain: 'algorand' },
  { value: 'goBTC',         label: 'Wrapped Bitcoin (ALGO)',chain: 'algorand' },
  { value: 'goETH',         label: 'Wrapped ETH (ALGO)',    chain: 'algorand' },
  // Bitcoin
  { value: 'BTC',           label: 'Bitcoin (BTC)',          chain: 'bitcoin'  },
  // Ethereum
  { value: 'ETH',           label: 'Ethereum (ETH)',         chain: 'ethereum' },
  { value: 'USDT_ETH',      label: 'Tether (Ethereum)',      chain: 'ethereum' },
  { value: 'USDC_ETH',      label: 'USD Coin (Ethereum)',    chain: 'ethereum' },
  // Polygon
  { value: 'MATIC',         label: 'Polygon (MATIC)',        chain: 'polygon'  },
  { value: 'USDT_POLYGON',  label: 'Tether (Polygon)',       chain: 'polygon'  },
  { value: 'USDC_POLYGON',  label: 'USD Coin (Polygon)',     chain: 'polygon'  },
  // Tron
  { value: 'TRX',           label: 'TRON (TRX)',             chain: 'tron'     },
  { value: 'USDT_TRON',     label: 'Tether (Tron) ⭐',       chain: 'tron'     },
  // Solana
  { value: 'SOL',           label: 'Solana (SOL)',            chain: 'solana'   },
  { value: 'USDT_SOLANA',   label: 'Tether (Solana)',         chain: 'solana'   },
  { value: 'USDC_SOLANA',   label: 'USD Coin (Solana)',       chain: 'solana'   },
]

export const P2P_FIAT_OPTIONS = [
  'KES', 'NGN', 'GHS', 'UGX', 'TZS', 'ZAR', 'USD', 'GBP', 'EUR', 'INR', 'PHP'
]