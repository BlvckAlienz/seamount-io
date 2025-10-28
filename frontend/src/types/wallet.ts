// File: frontend/src/types/wallet.ts
export interface WalletSeeds {
  user_id: string
  warning: string
  backup_instruction: string
  algorand_seed: string | null
  wdk_seed: string | null
  wallet_addresses: {
    [chain: string]: string
  }
}

export interface AuthUser {
  id: string
  email: string
  access_token: string
  user_metadata?: {
    first_name?: string
    last_name?: string
  }
}