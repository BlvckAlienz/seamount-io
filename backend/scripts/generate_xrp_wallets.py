# File: backend/scripts/generate_xrp_wallets.py
"""
One-time script: Generate 3 Seamount XRPL wallets.
Run ONCE on testnet. Save the output to your .env file immediately.
Never run again — running again creates new wallets and orphans the old ones.

Usage:
    python -m backend.scripts.generate_xrp_wallets
"""

from xrpl.core import keypairs
from xrpl.wallet import Wallet


def generate_wallet(name: str) -> dict:
    """Generate a brand new XRPL wallet from scratch."""
    seed = keypairs.generate_seed()       # Creates a random secret password
    wallet = Wallet.from_seed(seed)       # Derives the address from that password
    return {
        "name": name,
        "address": wallet.classic_address,  # starts with 'r'
        "seed": seed,                        # starts with 's'
    }


def main():
    print("\n" + "="*60)
    print("  SEAMOUNT XRPL WALLET GENERATOR")
    print("  Run ONCE. Save output. Never share seeds.")
    print("="*60 + "\n")

    wallets = [
        generate_wallet("HOT WALLET    (user deposits)"),
        generate_wallet("DeFi WALLET   (AMM / yield)"),
        generate_wallet("ADMIN WALLET  (credentials)"),
    ]

    print("Copy these into your .env file:\n")
    print("# ── XRP Ledger ─────────────────────────────────────")
    print("XRP_NETWORK=testnet\n")

    labels = [
        ("XRP_HOT_WALLET_ADDRESS",   "XRP_HOT_WALLET_SEED"),
        ("XRP_DEFI_WALLET_ADDRESS",  "XRP_DEFI_WALLET_SEED"),
        ("XRP_ADMIN_WALLET_ADDRESS", "XRP_ADMIN_WALLET_SEED"),
    ]

    for i, wallet in enumerate(wallets):
        addr_key, seed_key = labels[i]
        print(f"# {wallet['name']}")
        print(f"{addr_key}={wallet['address']}")
        print(f"{seed_key}={wallet['seed']}")
        print()

    print("="*60)
    print("NEXT STEP: Fund each address with testnet XRP here:")
    print("https://faucet.altnet.rippletest.net/accounts")
    print("")
    print("Paste each 'r...' address into the faucet — one at a time.")
    print("Each wallet needs at least 1 XRP to exist on the network.")
    print("="*60 + "\n")

    print("⚠️  SECURITY REMINDERS:")
    print("  - Seeds (s...) are your MASTER PASSWORDS. Treat like a bank PIN.")
    print("  - Never commit seeds to Git. Add .env to .gitignore.")
    print("  - For production: store seeds in AWS KMS or similar vault.")
    print("  - This script generates NEW wallets every time — only run ONCE.\n")


if __name__ == "__main__":
    main()