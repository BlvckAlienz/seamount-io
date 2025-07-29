// get-faucet-info.js
// Location: /scripts/get-faucet-info.js

import PersistentWalletGenerator from './persistent-wallet-generator.js';

/**
 * Display wallet address for faucet funding
 */

console.log('🚰 SOLANA DEVNET FAUCET FUNDING');
console.log('================================\n');

const generator = new PersistentWalletGenerator();
const walletAddress = generator.displayFaucetInfo();

console.log('\n💡 Pro Tips:');
console.log('• Use the same wallet address for all deployments');
console.log('• Check balance before deploying: solana balance <address> --url devnet');
console.log('• Alternative faucets: https://solfaucet.com, https://faucet.quicknode.com');
console.log('\n🔥 Ready to deploy once funded!');