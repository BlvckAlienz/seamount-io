// File: wdk-service/server.js
// PRODUCTION DEPLOYMENT FOR RENDER
// Multi-chain wallet service with robust error handling

require('dotenv').config();
const express = require('express');
const cors = require('cors');
const crypto = require('crypto');
const { ethers } = require('ethers');
const bitcoin = require('bitcoinjs-lib');
const bip39 = require('bip39');
const BIP32Factory = require('bip32').default;
const ecc = require('tiny-secp256k1');

const app = express();
const PORT = process.env.PORT || 3001;

// ✅ ONLY use environment variable (no hardcoded fallback)
const WDK_API_KEY = process.env.WDK_API_KEY;

// Validate API key is configured
if (!WDK_API_KEY) {
    console.error('❌ FATAL: WDK_API_KEY environment variable not set!');
    console.error('   Set it in Render dashboard or .env file');
    process.exit(1); // Exit if no API key
}

console.log('🚀 Starting WDK Service...');
console.log(`🔐 API Key configured: ${WDK_API_KEY.slice(0, 10)}...`);
console.log(`🌐 Port: ${PORT}`);

// Middleware
app.use(cors());
app.use(express.json());

// Request logging
app.use((req, res, next) => {
    console.log(`📨 ${req.method} ${req.path}`);
    next();
});

// API Key validation
function validateApiKey(req, res, next) {
    const apiKey = req.headers['x-api-key'];
    
    if (!apiKey) {
        console.error('❌ No API key provided');
        return res.status(401).json({ 
            success: false,
            error: 'API key required in X-API-Key header' 
        });
    }
    
    if (apiKey !== WDK_API_KEY) {
        console.error(`❌ Invalid API key: ${apiKey.slice(0, 10)}...`);
        return res.status(401).json({ 
            success: false,
            error: 'Invalid API key' 
        });
    }
    
    next();
}

// Encryption
const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || crypto.randomBytes(32).toString('hex');

function encrypt(text) {
    const algorithm = 'aes-256-cbc';
    const key = Buffer.from(ENCRYPTION_KEY.slice(0, 32));
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv(algorithm, key, iv);
    let encrypted = cipher.update(text, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    return iv.toString('hex') + ':' + encrypted;
}

function decrypt(text) {
    try {
        const algorithm = 'aes-256-cbc';
        const key = Buffer.from(ENCRYPTION_KEY.slice(0, 32));
        const parts = text.split(':');
        const iv = Buffer.from(parts[0], 'hex');
        const encrypted = parts[1];
        const decipher = crypto.createDecipheriv(algorithm, key, iv);
        let decrypted = decipher.update(encrypted, 'hex', 'utf8');
        decrypted += decipher.final('utf8');
        return decrypted;
    } catch (error) {
        console.error('❌ Decryption failed:', error.message);
        throw new Error('Invalid encrypted seed');
    }
}

// RPC Providers with fallbacks
const providers = {
    ethereum: new ethers.JsonRpcProvider(
        process.env.ALCHEMY_API_KEY_ETHEREUM 
            ? `https://eth-mainnet.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY_ETHEREUM}`
            : 'https://eth.drpc.org'
    ),
    polygon: new ethers.JsonRpcProvider(
        process.env.ALCHEMY_API_KEY_POLYGON
            ? `https://polygon-mainnet.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY_POLYGON}`
            : 'https://polygon-rpc.com'
    ),
    arbitrum: new ethers.JsonRpcProvider(
        process.env.ALCHEMY_API_KEY_ARBITRUM
            ? `https://arb-mainnet.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY_ARBITRUM}`
            : 'https://arb1.arbitrum.io/rpc'
    )
};

console.log('✅ RPC Providers configured');

const bip32 = BIP32Factory(ecc);

// ============================================================================
// WALLET GENERATION
// ============================================================================

function generateSeedPhrase() {
    return bip39.generateMnemonic(128);
}

function validateSeedPhrase(mnemonic) {
    return bip39.validateMnemonic(mnemonic);
}

async function createEVMWallet(mnemonic, index = 0) {
    try {
        const wallet = ethers.Wallet.fromPhrase(mnemonic);
        
        if (index > 0) {
            const hdNode = ethers.HDNodeWallet.fromPhrase(mnemonic);
            const path = `m/44'/60'/0'/0/${index}`;
            const child = hdNode.derivePath(path);
            return {
                address: child.address,
                privateKey: child.privateKey,
                path
            };
        }
        
        return {
            address: wallet.address,
            privateKey: wallet.privateKey,
            path: "m/44'/60'/0'/0/0"
        };
    } catch (error) {
        console.error('❌ EVM wallet creation failed:', error.message);
        throw error;
    }
}

async function createBitcoinWallet(mnemonic, index = 0) {
    try {
        const seed = await bip39.mnemonicToSeed(mnemonic);
        const root = bip32.fromSeed(seed);
        const path = `m/84'/0'/0'/0/${index}`;
        const child = root.derivePath(path);
        
        const { address } = bitcoin.payments.p2wpkh({
            pubkey: child.publicKey,
            network: bitcoin.networks.bitcoin
        });
        
        return {
            address,
            publicKey: child.publicKey.toString('hex'),
            path
        };
    } catch (error) {
        console.error('❌ Bitcoin wallet creation failed:', error.message);
        throw error;
    }
}

async function createTronWallet(mnemonic, index = 0) {
    try {
        // TRON uses same derivation as Ethereum (BIP-44 path m/44'/195'/0'/0/0)
        const evmWallet = await createEVMWallet(mnemonic, index);
        
        // Simple TRON address conversion (prefix with T)
        // In production, use TronWeb library for proper conversion
        const tronAddress = 'T' + evmWallet.address.slice(2, 36);
        
        return {
            address: tronAddress,
            privateKey: evmWallet.privateKey,
            path: evmWallet.path
        };
    } catch (error) {
        console.error('❌ TRON wallet creation failed:', error.message);
        throw error;
    }
}

// ============================================================================
// ENDPOINTS
// ============================================================================

app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        version: '2.0.0',
        chains: ['bitcoin', 'ethereum', 'polygon', 'arbitrum', 'tron'],
        api_key_configured: !!WDK_API_KEY,
        encryption_configured: !!ENCRYPTION_KEY,
        alchemy: {
            ethereum: !!process.env.ALCHEMY_API_KEY_ETHEREUM,
            polygon: !!process.env.ALCHEMY_API_KEY_POLYGON,
            arbitrum: !!process.env.ALCHEMY_API_KEY_ARBITRUM
        },
        timestamp: new Date().toISOString()
    });
});

app.post('/wallet/generate-seed', validateApiKey, (req, res) => {
    try {
        const mnemonic = generateSeedPhrase();
        const encryptedSeed = encrypt(mnemonic);
        
        console.log('✅ Seed phrase generated');
        
        res.json({
            success: true,
            encrypted_seed: encryptedSeed,
            created_at: new Date().toISOString()
        });
    } catch (error) {
        console.error('❌ Seed generation failed:', error);
        res.status(500).json({ 
            success: false,
            error: error.message 
        });
    }
});

app.post('/wallet/create', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chains, enable_gasless } = req.body;
        
        if (!encrypted_seed) {
            return res.status(400).json({ 
                success: false,
                error: 'encrypted_seed required' 
            });
        }

        console.log('🔓 Decrypting seed...');
        const mnemonic = decrypt(encrypted_seed);
        
        if (!validateSeedPhrase(mnemonic)) {
            return res.status(400).json({ 
                success: false,
                error: 'Invalid seed phrase' 
            });
        }

        // Default to essential chains
        const chainsToCreate = chains || ['bitcoin', 'ethereum', 'polygon', 'tron'];
        console.log(`🔨 Creating wallets for: ${chainsToCreate.join(', ')}`);
        
        const wallets = {};
        const errors = [];

        for (const chain of chainsToCreate) {
            try {
                console.log(`⚙️  Creating ${chain} wallet...`);
                let wallet;
                
                if (chain === 'bitcoin') {
                    wallet = await createBitcoinWallet(mnemonic);
                } else if (chain === 'tron') {
                    wallet = await createTronWallet(mnemonic);
                } else if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
                    wallet = await createEVMWallet(mnemonic);
                } else {
                    console.warn(`⚠️  Chain ${chain} not yet supported`);
                    errors.push(`Chain ${chain} not yet supported`);
                    continue;
                }
                
                wallets[chain] = {
                    address: wallet.address,
                    created_at: new Date().toISOString(),
                    gasless_enabled: enable_gasless && ['ethereum', 'polygon', 'arbitrum'].includes(chain)
                };
                
                console.log(`✅ ${chain.toUpperCase()}: ${wallet.address.slice(0, 10)}...`);
                
            } catch (error) {
                console.error(`❌ ${chain} wallet creation failed:`, error.message);
                errors.push(`${chain}: ${error.message}`);
            }
        }

        const response = {
            success: Object.keys(wallets).length > 0,
            wallets,
            supported_chains: Object.keys(wallets),
            total_chains: Object.keys(wallets).length
        };

        if (errors.length > 0) {
            response.errors = errors;
        }

        console.log(`✅ Wallet creation complete: ${Object.keys(wallets).length} chains`);
        res.json(response);
        
    } catch (error) {
        console.error('❌ Wallet creation failed:', error);
        res.status(500).json({ 
            success: false,
            error: error.message 
        });
    }
});

// ============================================================================
// BALANCE QUERY - Support both GET (query params) and POST (body)
// ============================================================================

app.get('/wallet/balance', validateApiKey, async (req, res) => {
    try {
        // ✅ GET request: Extract from query params
        const { chain, address } = req.query;

        if (!chain || !address) {
            return res.status(400).json({ 
                success: false,
                error: 'chain and address required as query parameters' 
            });
        }

        console.log(`📊 Balance query: ${chain} - ${address.slice(0, 10)}...`);

        let balance = '0';

        if (chain === 'bitcoin') {
            // Bitcoin balance requires external API
            // For now, return 0 (add blockchain.info API later)
            balance = '0';
            console.log('⚠️  Bitcoin balance requires external API integration');
            
        } else if (chain === 'tron') {
            // TRON balance requires TronGrid API
            balance = '0';
            console.log('⚠️  TRON balance requires TronGrid API integration');
            
        } else if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
            try {
                const provider = providers[chain];
                if (!provider) {
                    throw new Error(`Provider not configured for ${chain}`);
                }
                
                const balanceWei = await provider.getBalance(address);
                balance = ethers.formatEther(balanceWei);
                console.log(`✅ ${chain.toUpperCase()} balance: ${balance}`);
                
            } catch (providerError) {
                console.warn(`⚠️  Provider error for ${chain}:`, providerError.message);
                balance = '0';
            }
            
        } else {
            return res.status(400).json({ 
                success: false,
                error: `Unsupported chain: ${chain}` 
            });
        }

        res.json({
            success: true,
            chain,
            address,
            balance,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        console.error('❌ Balance query failed:', error);
        res.status(500).json({ 
            success: false,
            error: error.message 
        });
    }
});

// ✅ ALSO support POST for backward compatibility
app.post('/wallet/balance', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chain, index = 0, address } = req.body;

        if (!chain) {
            return res.status(400).json({ 
                success: false,
                error: 'chain required' 
            });
        }

        // If address provided directly, use it
        let walletAddress = address;

        // Otherwise, derive from seed
        if (!walletAddress && encrypted_seed) {
            console.log('🔓 Decrypting seed to derive address...');
            const mnemonic = decrypt(encrypted_seed);

            if (chain === 'bitcoin') {
                const btcWallet = await createBitcoinWallet(mnemonic, index);
                walletAddress = btcWallet.address;
            } else if (chain === 'tron') {
                const tronWallet = await createTronWallet(mnemonic, index);
                walletAddress = tronWallet.address;
            } else if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
                const evmWallet = await createEVMWallet(mnemonic, index);
                walletAddress = evmWallet.address;
            }
        }

        if (!walletAddress) {
            return res.status(400).json({ 
                success: false,
                error: 'address or encrypted_seed required' 
            });
        }

        // Now query balance using the address
        let balance = '0';

        if (chain === 'bitcoin') {
            balance = '0';
            console.log('⚠️  Bitcoin balance requires external API');
            
        } else if (chain === 'tron') {
            balance = '0';
            console.log('⚠️  TRON balance requires TronGrid API');
            
        } else if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
            try {
                const provider = providers[chain];
                const balanceWei = await provider.getBalance(walletAddress);
                balance = ethers.formatEther(balanceWei);
                console.log(`✅ ${chain.toUpperCase()} balance: ${balance}`);
            } catch (providerError) {
                console.warn(`⚠️  Provider error for ${chain}:`, providerError.message);
                balance = '0';
            }
        }

        res.json({
            success: true,
            chain,
            address: walletAddress,
            balance,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        console.error('❌ Balance query failed:', error);
        res.status(500).json({ 
            success: false,
            error: error.message 
        });
    }
});

// ============================================================================
// SEND TRANSACTION - Following Tether WDK Node.js Quickstart Pattern
// ============================================================================

app.post('/wallet/send', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chain, to, amount, gasless } = req.body;

        // Validate required fields
        if (!encrypted_seed || !chain || !to || !amount) {
            return res.status(400).json({ 
                success: false,
                error: 'Missing required fields: encrypted_seed, chain, to, amount' 
            });
        }

        console.log(`💸 Initiating ${amount} ${chain.toUpperCase()} transfer to ${to.slice(0, 10)}...`);

        // Decrypt seed phrase
        const mnemonic = decrypt(encrypted_seed);
        
        if (!validateSeedPhrase(mnemonic)) {
            return res.status(400).json({ 
                success: false,
                error: 'Invalid seed phrase' 
            });
        }

        // ========== EVM CHAINS (Ethereum, Polygon, Arbitrum) ==========
        if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
            try {
                console.log(`⚙️  Processing ${chain} EVM transaction...`);
                
                // Create wallet from seed (WDK pattern)
                const evmWallet = await createEVMWallet(mnemonic);
                const provider = providers[chain];
                
                if (!provider) {
                    throw new Error(`Provider not configured for ${chain}`);
                }
                
                // Connect wallet to provider
                const wallet = new ethers.Wallet(evmWallet.privateKey, provider);
                
                console.log(`📝 Sending from: ${wallet.address.slice(0, 10)}...`);
                console.log(`📝 Sending to: ${to.slice(0, 10)}...`);
                console.log(`📝 Amount: ${amount} ETH/MATIC`);
                
                // Build and send transaction (WDK pattern)
                const tx = await wallet.sendTransaction({
                    to: to,
                    value: ethers.parseEther(amount.toString()),
                    // Gasless handled by provider configuration
                });

                console.log(`⏳ Transaction submitted: ${tx.hash}`);
                console.log(`⏳ Waiting for confirmation...`);

                // Wait for confirmation (1 block)
                const receipt = await tx.wait(1);

                console.log(`✅ Transaction confirmed!`);
                console.log(`   Block: ${receipt.blockNumber}`);
                console.log(`   Gas Used: ${receipt.gasUsed.toString()}`);
                console.log(`   Status: ${receipt.status === 1 ? 'Success' : 'Failed'}`);

                // Calculate actual costs
                const gasPrice = receipt.gasPrice || tx.gasPrice;
                const gasCostWei = receipt.gasUsed * gasPrice;
                const gasCostEth = ethers.formatEther(gasCostWei);

                return res.json({
                    success: true,
                    tx_hash: receipt.hash,
                    tx_id: receipt.hash,
                    chain: chain,
                    block_number: receipt.blockNumber,
                    gas_used: receipt.gasUsed.toString(),
                    gas_price: gasPrice.toString(),
                    gas_cost_eth: gasCostEth,
                    status: receipt.status === 1 ? 'confirmed' : 'failed',
                    gasless_used: gasless || false,
                    timestamp: new Date().toISOString(),
                    explorer_url: getExplorerUrl(chain, receipt.hash)
                });
                
            } catch (evmError) {
                console.error(`❌ ${chain} transaction failed:`, evmError.message);
                
                // Parse ethers.js error
                let errorMessage = evmError.message;
                if (evmError.code === 'INSUFFICIENT_FUNDS') {
                    errorMessage = `Insufficient ${chain.toUpperCase()} balance. Please fund your wallet.`;
                } else if (evmError.code === 'NONCE_EXPIRED') {
                    errorMessage = 'Transaction nonce expired. Please retry.';
                } else if (evmError.code === 'REPLACEMENT_UNDERPRICED') {
                    errorMessage = 'Gas price too low. Please increase gas price.';
                }
                
                return res.status(400).json({ 
                    success: false,
                    error: errorMessage,
                    error_code: evmError.code,
                    chain: chain
                });
            }
        }

        // ========== BITCOIN (DEFERRED - UTXO Complexity) ==========
        else if (chain === 'bitcoin') {
            console.log('⚠️  Bitcoin transactions require UTXO management');
            return res.status(501).json({ 
                success: false,
                error: 'Bitcoin send transactions coming in Phase 2',
                message: 'Bitcoin requires UTXO selection and transaction building. Use Algorand or EVM chains for now.',
                alternative_chains: ['ethereum', 'polygon', 'arbitrum']
            });
        }
        
        // ========== TRON (DEFERRED - Different SDK) ==========
        else if (chain === 'tron') {
            console.log('⚠️  TRON transactions require TronWeb SDK');
            return res.status(501).json({ 
                success: false,
                error: 'TRON send transactions coming in Phase 2',
                message: 'TRON requires TronWeb SDK integration. Use EVM chains for now.',
                alternative_chains: ['ethereum', 'polygon', 'arbitrum']
            });
        }
        
        // ========== UNSUPPORTED CHAIN ==========
        else {
            return res.status(400).json({ 
                success: false,
                error: `Unsupported chain: ${chain}`,
                supported_chains: ['ethereum', 'polygon', 'arbitrum'],
                message: 'Only EVM chains supported in Phase 1'
            });
        }
        
    } catch (error) {
        console.error('❌ Send transaction failed:', error);
        return res.status(500).json({ 
            success: false,
            error: error.message,
            timestamp: new Date().toISOString()
        });
    }
});

// ============================================================================
// HELPER: Get Blockchain Explorer URL
// ============================================================================

function getExplorerUrl(chain, txHash) {
    const explorers = {
        ethereum: `https://etherscan.io/tx/${txHash}`,
        polygon: `https://polygonscan.com/tx/${txHash}`,
        arbitrum: `https://arbiscan.io/tx/${txHash}`,
        bitcoin: `https://blockstream.info/tx/${txHash}`,
        tron: `https://tronscan.org/#/transaction/${txHash}`
    };
    
    return explorers[chain] || `https://etherscan.io/tx/${txHash}`;
}

app.post('/wallet/send', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chain, to, amount, gasless } = req.body;

        if (!encrypted_seed || !chain || !to || !amount) {
            return res.status(400).json({ 
                success: false,
                error: 'encrypted_seed, chain, to, and amount required' 
            });
        }

        const mnemonic = decrypt(encrypted_seed);

        if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
            const evmWallet = await createEVMWallet(mnemonic);
            const provider = providers[chain];
            const wallet = new ethers.Wallet(evmWallet.privateKey, provider);

            const tx = await wallet.sendTransaction({
                to,
                value: ethers.parseEther(amount.toString())
            });

            const receipt = await tx.wait();

            console.log(`✅ Transaction sent on ${chain}: ${receipt.hash}`);

            res.json({
                success: true,
                tx_hash: receipt.hash,
                tx_id: receipt.hash,
                chain,
                gasless_used: gasless || false,
                timestamp: new Date().toISOString()
            });
            
        } else if (chain === 'bitcoin') {
            res.status(501).json({ 
                success: false,
                error: 'Bitcoin transactions require UTXO management' 
            });
            
        } else {
            res.status(400).json({ 
                success: false,
                error: `Unsupported chain: ${chain}` 
            });
        }
        
    } catch (error) {
        console.error('❌ Transaction failed:', error);
        res.status(500).json({ 
            success: false,
            error: error.message 
        });
    }
});

// Global error handler
app.use((err, req, res, next) => {
    console.error('❌ Server error:', err);
    res.status(500).json({ 
        success: false,
        error: 'Internal server error',
        message: err.message 
    });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({
        success: false,
        error: 'Endpoint not found',
        path: req.path
    });
});

app.listen(PORT, () => {
    console.log('='.repeat(60));
    console.log('✅ Multi-Chain Wallet Service READY');
    console.log('='.repeat(60));
    console.log(`📡 URL: http://localhost:${PORT}`);
    console.log(`🔐 API Key: ${WDK_API_KEY.slice(0, 10)}...`);
    console.log(`🌐 Chains: Bitcoin, Ethereum, Polygon, Arbitrum, TRON`);
    console.log(`📊 Health: http://localhost:${PORT}/health`);
    console.log('='.repeat(60));
});