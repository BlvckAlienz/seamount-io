// usds-mint-tokens.js
// Location: /backend/scripts/usds-mint-tokens.js

import { Connection, Keypair, PublicKey } from '@solana/web3.js';
import * as splToken from '@solana/spl-token';
import fs from 'fs';
import path from 'path';

class USDSMinter {
    constructor() {
        this.connection = new Connection('https://api.devnet.solana.com', 'confirmed');
        this.usdsMint = new PublicKey('91fRwS9ifeJCduXjS8ajEpCpsuz89W51LKkSDHvjxiuz');
        this.masterKeypair = this.loadMasterWallet();
        this.maxRetries = 3;
        this.retryDelay = 2000;
        
        // Initialize Token instance for legacy API
        this.token = new splToken.Token(
            this.connection,
            this.usdsMint,
            splToken.TOKEN_PROGRAM_ID,
            this.masterKeypair
        );
        
        console.log('🔍 Using legacy SPL Token API');
    }

    loadMasterWallet() {
        const possiblePaths = [
            path.join(process.cwd(), 'wallets', 'master-wallet.json'),
            path.join(process.cwd(), 'deployment-artifacts', 'master-wallet.json'),
            path.join(process.cwd(), 'deployment-artifacts', 'wallet.json')
        ];

        for (const walletPath of possiblePaths) {
            try {
                if (fs.existsSync(walletPath)) {
                    console.log(`🔍 Found wallet at: ${walletPath}`);
                    const keypairData = JSON.parse(fs.readFileSync(walletPath, 'utf8'));
                    
                    let secretKey;
                    if (Array.isArray(keypairData)) {
                        secretKey = new Uint8Array(keypairData);
                    } else if (keypairData.secretKey) {
                        secretKey = new Uint8Array(keypairData.secretKey);
                    } else if (keypairData.privateKey) {
                        secretKey = new Uint8Array(keypairData.privateKey);
                    } else if (keypairData._keypair && keypairData._keypair.secretKey) {
                        secretKey = new Uint8Array(keypairData._keypair.secretKey);
                    }

                    if (secretKey && secretKey.length === 64) {
                        const keypair = Keypair.fromSecretKey(secretKey);
                        console.log(`✅ Loaded mint authority: ${keypair.publicKey.toBase58()}`);
                        return keypair;
                    }
                }
            } catch (error) {
                console.error(`❌ Error loading wallet from ${walletPath}:`, error.message);
                continue;
            }
        }

        throw new Error('❌ Master wallet not found');
    }

    async retryOperation(operation, operationName) {
        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                return await operation();
            } catch (error) {
                console.log(`⚠️  ${operationName} attempt ${attempt} failed: ${error.message}`);
                
                if (attempt === this.maxRetries) {
                    throw error;
                }
                
                console.log(`🔄 Retrying in ${this.retryDelay}ms...`);
                await new Promise(resolve => setTimeout(resolve, this.retryDelay));
            }
        }
    }

    async verifyMintAuthority() {
        try {
            const mintInfo = await this.retryOperation(
                () => this.token.getMintInfo(),
                'Get mint info'
            );
            
            const mintAuthority = mintInfo.mintAuthority;
            
            console.log(`🔐 Mint authority: ${mintAuthority?.toBase58()}`);
            console.log(`👤 Your wallet: ${this.masterKeypair.publicKey.toBase58()}`);
            
            if (mintAuthority && mintAuthority.equals(this.masterKeypair.publicKey)) {
                console.log('✅ You are the mint authority!');
                return true;
            } else {
                console.log('❌ You are NOT the mint authority');
                return false;
            }
        } catch (error) {
            console.error('❌ Failed to verify mint authority:', error.message);
            console.log('🔄 Proceeding anyway...');
            return true;
        }
    }

    async mintTokens(amount) {
        try {
            console.log(`🔄 Minting ${amount} USDS tokens...`);

            // Get or create associated token account
            const associatedTokenAddress = await this.retryOperation(
                () => splToken.Token.getAssociatedTokenAddress(
                    splToken.ASSOCIATED_TOKEN_PROGRAM_ID,
                    splToken.TOKEN_PROGRAM_ID,
                    this.usdsMint,
                    this.masterKeypair.publicKey
                ),
                'Get associated token address'
            );

            console.log(`📋 Token account: ${associatedTokenAddress.toBase58()}`);

            // Check if account exists, create if not
            try {
                await this.token.getAccountInfo(associatedTokenAddress);
                console.log('✅ Token account exists');
            } catch (error) {
                console.log('🔄 Creating associated token account...');
                
                await this.retryOperation(
                    () => splToken.Token.createAssociatedTokenAccount(
                        this.connection,
                        this.masterKeypair,
                        this.usdsMint,
                        this.masterKeypair.publicKey
                    ),
                    'Create token account'
                );
                console.log('✅ Token account created');
            }

            // Mint tokens
            const mintAmount = amount * 1e6;
            const startTime = Date.now();
            
            const mintTx = await this.retryOperation(
                () => this.token.mintTo(
                    associatedTokenAddress,
                    this.masterKeypair,
                    [],
                    mintAmount
                ),
                'Mint tokens'
            );

            const endTime = Date.now();
            
            console.log(`✅ Minted ${amount} USDS in ${endTime - startTime}ms`);
            console.log(`📋 Transaction: ${mintTx}`);

            // Verify balance
            const balance = await this.getBalance();
            console.log(`💰 New balance: ${balance} USDS`);

            return mintTx;

        } catch (error) {
            console.error('❌ Minting failed:', error.message);
            
            if (error.message.includes('insufficient funds')) {
                console.log('💡 Need more SOL? Run: solana airdrop 2 --url devnet');
            } else if (error.message.includes('blockhash')) {
                console.log('💡 Network congestion. Try again in a few seconds.');
            } else if (error.message.includes('TokenAccountNotFoundError')) {
                console.log('💡 Token account creation failed. Check mint authority.');
            }
            
            throw error;
        }
    }

    async getBalance() {
        try {
            const associatedTokenAddress = await splToken.Token.getAssociatedTokenAddress(
                splToken.ASSOCIATED_TOKEN_PROGRAM_ID,
                splToken.TOKEN_PROGRAM_ID,
                this.usdsMint,
                this.masterKeypair.publicKey
            );

            const tokenAccount = await this.token.getAccountInfo(associatedTokenAddress);
            return Number(tokenAccount.amount) / 1e6;

        } catch (error) {
            console.log('❌ No token account found');
            return 0;
        }
    }

    async fundTestWallet() {
        console.log('🚀 Starting USDS Test Wallet Funding...');
        console.log('='.repeat(50));

        try {
            // Check SOL balance
            const balance = await this.connection.getBalance(this.masterKeypair.publicKey);
            console.log(`💰 SOL balance: ${balance / 1e9} SOL`);
            
            if (balance < 1000000) {
                console.log('⚠️  Low SOL balance. Getting airdrop...');
                console.log('Run: solana airdrop 2 --url devnet');
                return;
            }

            // Verify mint authority
            if (!(await this.verifyMintAuthority())) {
                console.log('⚠️  Mint authority check failed, but proceeding...');
            }

            // Check current balance
            const currentBalance = await this.getBalance();
            console.log(`💰 Current balance: ${currentBalance} USDS`);

            // Mint test tokens
            const mintAmount = 100000;
            await this.mintTokens(mintAmount);

            console.log('🎉 Test wallet funded successfully!');
            console.log('✅ Ready for transfer tests');

        } catch (error) {
            console.error('❌ Funding failed:', error.message);
            
            if (error.message.includes('insufficient funds')) {
                console.log('💡 Run: solana airdrop 2 --url devnet');
            }
        }
    }
}

// Execute funding
const minter = new USDSMinter();
minter.fundTestWallet().catch(console.error);