// persistent-wallet-generator.js
// Location: /scripts/persistent-wallet-generator.js

import { Keypair } from '@solana/web3.js';
import fs from 'fs';
import path from 'path';

/**
 * Generate or load persistent wallet for consistent deployments
 * Creates a master wallet that persists across deployment attempts
 */

class PersistentWalletGenerator {
    constructor() {
        this.walletFile = path.join(process.cwd(), 'deployment-artifacts', 'master-wallet.json');
        this.ensureArtifactsDir();
    }
    
    ensureArtifactsDir() {
        const dir = path.dirname(this.walletFile);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    }
    
    /**
     * Generate or load existing master wallet
     */
    getMasterWallet() {
        try {
            // Check if wallet already exists
            if (fs.existsSync(this.walletFile)) {
                console.log('📂 Loading existing master wallet...');
                const walletData = JSON.parse(fs.readFileSync(this.walletFile, 'utf8'));
                const keypair = Keypair.fromSecretKey(new Uint8Array(walletData.secretKey));
                
                console.log(`✅ Master wallet loaded: ${keypair.publicKey.toBase58()}`);
                return keypair;
            }
            
            // Generate new wallet
            console.log('🆕 Generating new master wallet...');
            const keypair = Keypair.generate();
            
            // Save wallet data
            const walletData = {
                publicKey: keypair.publicKey.toBase58(),
                secretKey: Array.from(keypair.secretKey),
                createdAt: new Date().toISOString()
            };
            
            fs.writeFileSync(this.walletFile, JSON.stringify(walletData, null, 2));
            
            console.log(`✅ Master wallet generated: ${keypair.publicKey.toBase58()}`);
            console.log(`💾 Wallet saved to: ${this.walletFile}`);
            
            return keypair;
            
        } catch (error) {
            console.error('❌ Wallet generation failed:', error.message);
            throw error;
        }
    }
    
    /**
     * Display wallet info for faucet funding
     */
    displayFaucetInfo() {
        const keypair = this.getMasterWallet();
        
        console.log('\n🚰 FAUCET FUNDING INSTRUCTIONS:');
        console.log('================================');
        console.log(`Wallet Address: ${keypair.publicKey.toBase58()}`);
        console.log('Faucet URL: https://faucet.solana.com');
        console.log('Network: Devnet');
        console.log('Amount: 2 SOL (recommended)');
        console.log('\n📋 Steps:');
        console.log('1. Copy the wallet address above');
        console.log('2. Visit https://faucet.solana.com');
        console.log('3. Connect your GitHub account');
        console.log('4. Paste the wallet address');
        console.log('5. Request SOL tokens');
        console.log('6. Wait for confirmation');
        console.log('7. Run deployment script again');
        console.log('\n✅ This wallet persists across deployments!');
        
        return keypair.publicKey.toBase58();
    }
}

// CLI usage
if (import.meta.url === `file://${process.argv[1]}`) {
    const generator = new PersistentWalletGenerator();
    generator.displayFaucetInfo();
}

export default PersistentWalletGenerator;