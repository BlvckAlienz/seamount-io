// File: wdk-service/server.js
// Seamount WDK Wrapper - Multi-Chain Wallet Service

const express = require('express');
const cors = require('cors');
const WDK = require('@tetherto/wdk').default;
const WalletManagerEvm = require('@tetherto/wdk-wallet-evm').default;
const WalletManagerBtc = require('@tetherto/wdk-wallet-btc').default;
const WalletManagerTon = require('@tetherto/wdk-wallet-ton').default;
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// In-memory cache (use Redis in production)
const walletCache = new Map();
const CACHE_TTL = 3600000; // 1 hour

// Security: API key validation
const SEAMOUNT_API_KEY = process.env.SEAMOUNT_API_KEY || 'smnt_dev_key';

function validateApiKey(req, res, next) {
    const apiKey = req.headers['x-api-key'];
    if (!apiKey || apiKey !== SEAMOUNT_API_KEY) {
        return res.status(401).json({ error: 'Invalid API key' });
    }
    next();
}

// Encryption for seed phrases
const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || crypto.randomBytes(32).toString('hex');
const algorithm = 'aes-256-cbc';

function encrypt(text) {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv(algorithm, Buffer.from(ENCRYPTION_KEY.slice(0, 32)), iv);
    let encrypted = cipher.update(text);
    encrypted = Buffer.concat([encrypted, cipher.final()]);
    return iv.toString('hex') + ':' + encrypted.toString('hex');
}

function decrypt(text) {
    const parts = text.split(':');
    const iv = Buffer.from(parts.shift(), 'hex');
    const encryptedText = Buffer.from(parts.join(':'), 'hex');
    const decipher = crypto.createDecipheriv(algorithm, Buffer.from(ENCRYPTION_KEY.slice(0, 32)), iv);
    let decrypted = decipher.update(encryptedText);
    decrypted = Buffer.concat([decrypted, decipher.final()]);
    return decrypted.toString();
}

// Get or create WDK instance
async function getWdkInstance(seedPhrase) {
    const cacheKey = crypto.createHash('sha256').update(seedPhrase).digest('hex');
    
    if (walletCache.has(cacheKey)) {
        const cached = walletCache.get(cacheKey);
        if (Date.now() - cached.timestamp < CACHE_TTL) {
            return cached.wdk;
        }
    }

    const wdk = new WDK(seedPhrase)
        .registerWallet('ethereum', WalletManagerEvm, {
            rpcUrl: process.env.ETHEREUM_RPC || 'https://eth-mainnet.g.alchemy.com/v2/demo'
        })
        .registerWallet('polygon', WalletManagerEvm, {
            rpcUrl: process.env.POLYGON_RPC || 'https://polygon-rpc.com'
        })
        .registerWallet('arbitrum', WalletManagerEvm, {
            rpcUrl: process.env.ARBITRUM_RPC || 'https://arb1.arbitrum.io/rpc'
        })
        .registerWallet('bitcoin', WalletManagerBtc, {
            network: process.env.BTC_NETWORK || 'mainnet'
        })
        .registerWallet('ton', WalletManagerTon, {
            network: process.env.TON_NETWORK || 'mainnet'
        });

    walletCache.set(cacheKey, { wdk, timestamp: Date.now() });
    return wdk;
}

// ============================================================================
// ENDPOINTS
// ============================================================================

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        version: '1.0.0',
        chains: ['ethereum', 'polygon', 'arbitrum', 'bitcoin', 'ton'],
        timestamp: new Date().toISOString()
    });
});

// Generate new seed phrase
app.post('/wallet/generate-seed', validateApiKey, (req, res) => {
    try {
        const seedPhrase = WDK.getRandomSeedPhrase();
        const encryptedSeed = encrypt(seedPhrase);
        
        res.json({
            success: true,
            encrypted_seed: encryptedSeed,
            message: 'Seed phrase generated - store encrypted_seed securely'
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Create multi-chain wallet
app.post('/wallet/create', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chains } = req.body;
        
        if (!encrypted_seed) {
            return res.status(400).json({ error: 'encrypted_seed required' });
        }

        const seedPhrase = decrypt(encrypted_seed);
        const wdk = await getWdkInstance(seedPhrase);

        const chainsToCreate = chains || ['ethereum', 'bitcoin', 'polygon'];
        const wallets = {};

        for (const chain of chainsToCreate) {
            try {
                const account = await wdk.getAccount(chain, 0);
                const address = await account.getAddress();
                
                wallets[chain] = {
                    address,
                    index: 0,
                    created_at: new Date().toISOString()
                };
            } catch (error) {
                console.error(`Failed to create ${chain} wallet:`, error.message);
            }
        }

        res.json({
            success: true,
            wallets,
            supported_chains: chainsToCreate
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get balance for specific chain
app.post('/wallet/balance', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chain, index = 0 } = req.body;

        if (!encrypted_seed || !chain) {
            return res.status(400).json({ error: 'encrypted_seed and chain required' });
        }

        const seedPhrase = decrypt(encrypted_seed);
        const wdk = await getWdkInstance(seedPhrase);
        const account = await wdk.getAccount(chain, index);
        
        const address = await account.getAddress();
        const balance = await account.getBalance();

        res.json({
            success: true,
            chain,
            address,
            balance: balance.toString(),
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get unified balance across all chains
app.post('/wallet/balance-unified', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chains } = req.body;

        if (!encrypted_seed) {
            return res.status(400).json({ error: 'encrypted_seed required' });
        }

        const seedPhrase = decrypt(encrypted_seed);
        const wdk = await getWdkInstance(seedPhrase);
        const chainsToQuery = chains || ['ethereum', 'bitcoin', 'polygon'];

        const balances = {};
        let totalUsd = 0;

        // Mock prices (integrate real oracle in production)
        const prices = {
            ethereum: 2650,
            bitcoin: 63500,
            polygon: 0.65,
            ton: 2.5
        };

        for (const chain of chainsToQuery) {
            try {
                const account = await wdk.getAccount(chain, 0);
                const balance = await account.getBalance();
                const balanceNum = parseFloat(balance.toString());
                const usdValue = balanceNum * (prices[chain] || 0);

                balances[chain] = {
                    balance: balance.toString(),
                    usd_value: usdValue
                };

                totalUsd += usdValue;
            } catch (error) {
                console.error(`Balance query failed for ${chain}:`, error.message);
                balances[chain] = { balance: '0', usd_value: 0, error: error.message };
            }
        }

        res.json({
            success: true,
            balances,
            total_usd: totalUsd,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Send transaction
app.post('/wallet/send', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chain, to, amount, index = 0 } = req.body;

        if (!encrypted_seed || !chain || !to || !amount) {
            return res.status(400).json({ 
                error: 'encrypted_seed, chain, to, and amount required' 
            });
        }

        const seedPhrase = decrypt(encrypted_seed);
        const wdk = await getWdkInstance(seedPhrase);
        const account = await wdk.getAccount(chain, index);

        const tx = {
            to,
            value: amount,
            data: '0x'
        };

        const { hash, fee } = await account.sendTransaction(tx);

        res.json({
            success: true,
            tx_hash: hash,
            fee: fee.toString(),
            chain,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get transaction by hash
app.post('/wallet/transaction', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chain, tx_hash } = req.body;

        if (!encrypted_seed || !chain || !tx_hash) {
            return res.status(400).json({ 
                error: 'encrypted_seed, chain, and tx_hash required' 
            });
        }

        const seedPhrase = decrypt(encrypted_seed);
        const wdk = await getWdkInstance(seedPhrase);
        const account = await wdk.getAccount(chain, 0);

        const txDetails = await account.getTransaction(tx_hash);

        res.json({
            success: true,
            transaction: txDetails,
            chain,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get fee estimates
app.post('/wallet/fee-estimate', validateApiKey, async (req, res) => {
    try {
        const { chain } = req.body;

        if (!chain) {
            return res.status(400).json({ error: 'chain required' });
        }

        // Create minimal WDK instance just for fee query
        const wdk = new WDK(WDK.getRandomSeedPhrase())
            .registerWallet(chain, 
                chain === 'bitcoin' ? WalletManagerBtc : WalletManagerEvm,
                {}
            );

        const feeRates = await wdk.getFeeRates(chain);

        res.json({
            success: true,
            chain,
            fee_rates: feeRates,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Validate address
app.post('/wallet/validate-address', validateApiKey, async (req, res) => {
    try {
        const { chain, address } = req.body;

        if (!chain || !address) {
            return res.status(400).json({ error: 'chain and address required' });
        }

        // Basic validation (enhance with chain-specific validators)
        let isValid = false;

        if (chain === 'bitcoin') {
            isValid = /^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$/.test(address);
        } else if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
            isValid = /^0x[a-fA-F0-9]{40}$/.test(address);
        } else if (chain === 'ton') {
            isValid = /^[A-Za-z0-9_-]{48}$/.test(address);
        }

        res.json({
            success: true,
            chain,
            address,
            is_valid: isValid
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Error handling
app.use((err, req, res, next) => {
    console.error('Unhandled error:', err);
    res.status(500).json({ 
        error: 'Internal server error',
        message: err.message 
    });
});

// Start server
app.listen(PORT, () => {
    console.log(`✅ WDK Service running on port ${PORT}`);
    console.log(`📡 Health check: http://localhost:${PORT}/health`);
    console.log(`🔐 API Key required: ${SEAMOUNT_API_KEY.slice(0, 10)}...`);
});

module.exports = app;