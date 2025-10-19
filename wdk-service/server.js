// File: wdk-service/server.js
// Seamount Multi-Chain Wallet Service (Direct Implementation)

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
const SEAMOUNT_API_KEY = 'smnt_wdk_847c0b86c8c0773b72e0336cb50ce32b';

// Middleware
app.use(cors());
app.use(express.json());

function validateApiKey(req, res, next) {
    const apiKey = req.headers['x-api-key'];
    if (!apiKey || apiKey !== SEAMOUNT_API_KEY) {
        return res.status(401).json({ error: 'Invalid API key' });
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
    const algorithm = 'aes-256-cbc';
    const key = Buffer.from(ENCRYPTION_KEY.slice(0, 32));
    const parts = text.split(':');
    const iv = Buffer.from(parts[0], 'hex');
    const encrypted = parts[1];
    const decipher = crypto.createDecipheriv(algorithm, key, iv);
    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
}

// Blockchain providers
const providers = {
    ethereum: new ethers.JsonRpcProvider(
        process.env.ETHEREUM_RPC || 'https://eth-mainnet.g.alchemy.com/v2/demo'
    ),
    polygon: new ethers.JsonRpcProvider(
        process.env.POLYGON_RPC || 'https://polygon-rpc.com'
    ),
    arbitrum: new ethers.JsonRpcProvider(
        process.env.ARBITRUM_RPC || 'https://arb1.arbitrum.io/rpc'
    )
};

// BIP32 setup for Bitcoin
const bip32 = BIP32Factory(ecc);

// ============================================================================
// WALLET GENERATION
// ============================================================================

function generateSeedPhrase() {
    return bip39.generateMnemonic(128); // 12 words
}

function validateSeedPhrase(mnemonic) {
    return bip39.validateMnemonic(mnemonic);
}

async function createEVMWallet(mnemonic, index = 0) {
    // Create wallet from mnemonic directly
    const wallet = ethers.Wallet.fromPhrase(mnemonic);
    
    // Derive child wallet if index > 0
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
}

async function createBitcoinWallet(mnemonic, index = 0) {
    const seed = await bip39.mnemonicToSeed(mnemonic);
    const root = bip32.fromSeed(seed);
    const path = `m/84'/0'/0'/0/${index}`; // Native SegWit
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
}

// ============================================================================
// ENDPOINTS
// ============================================================================

app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        version: '1.0.0',
        chains: ['ethereum', 'polygon', 'arbitrum', 'bitcoin'],
        timestamp: new Date().toISOString()
    });
});

app.post('/wallet/generate-seed', validateApiKey, (req, res) => {
    try {
        const mnemonic = generateSeedPhrase();
        const encryptedSeed = encrypt(mnemonic);
        
        res.json({
            success: true,
            encrypted_seed: encryptedSeed,
            message: 'Seed phrase generated'
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/wallet/create', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chains } = req.body;
        
        if (!encrypted_seed) {
            return res.status(400).json({ error: 'encrypted_seed required' });
        }

        const mnemonic = decrypt(encrypted_seed);
        
        if (!validateSeedPhrase(mnemonic)) {
            return res.status(400).json({ error: 'Invalid seed phrase' });
        }

        const chainsToCreate = chains || ['ethereum', 'bitcoin', 'polygon'];
        const wallets = {};

        for (const chain of chainsToCreate) {
            try {
                if (chain === 'bitcoin') {
                    const btcWallet = await createBitcoinWallet(mnemonic);
                    wallets[chain] = {
                        address: btcWallet.address,
                        index: 0,
                        created_at: new Date().toISOString()
                    };
                } else if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
                    const evmWallet = await createEVMWallet(mnemonic);
                    wallets[chain] = {
                        address: evmWallet.address,
                        index: 0,
                        created_at: new Date().toISOString()
                    };
                }
            } catch (error) {
                console.error(`Failed to create ${chain} wallet:`, error.message);
            }
        }

        res.json({
            success: true,
            wallets,
            supported_chains: Object.keys(wallets)
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/wallet/balance', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chain, index = 0 } = req.body;

        if (!encrypted_seed || !chain) {
            return res.status(400).json({ error: 'encrypted_seed and chain required' });
        }

        const mnemonic = decrypt(encrypted_seed);
        let address, balance;

        if (chain === 'bitcoin') {
            const btcWallet = await createBitcoinWallet(mnemonic, index);
            address = btcWallet.address;
            balance = '0'; // Requires external Bitcoin API (Blockchair/Blockcypher)
        } else if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
            const evmWallet = await createEVMWallet(mnemonic, index);
            address = evmWallet.address;
            
            const provider = providers[chain];
            const balanceWei = await provider.getBalance(address);
            balance = ethers.formatEther(balanceWei);
        } else {
            return res.status(400).json({ error: 'Unsupported chain' });
        }

        res.json({
            success: true,
            chain,
            address,
            balance,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/wallet/balance-unified', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chains } = req.body;

        if (!encrypted_seed) {
            return res.status(400).json({ error: 'encrypted_seed required' });
        }

        const mnemonic = decrypt(encrypted_seed);
        const chainsToQuery = chains || ['ethereum', 'polygon', 'bitcoin'];

        const balances = {};
        let totalUsd = 0;

        const prices = {
            ethereum: 2650,
            polygon: 0.65,
            arbitrum: 2650,
            bitcoin: 63500
        };

        for (const chain of chainsToQuery) {
            try {
                if (chain === 'bitcoin') {
                    const btcWallet = await createBitcoinWallet(mnemonic);
                    balances[chain] = {
                        balance: '0',
                        usd_value: 0,
                        address: btcWallet.address
                    };
                } else if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
                    const evmWallet = await createEVMWallet(mnemonic);
                    const provider = providers[chain];
                    const balanceWei = await provider.getBalance(evmWallet.address);
                    const balance = ethers.formatEther(balanceWei);
                    const balanceNum = parseFloat(balance);
                    const usdValue = balanceNum * prices[chain];

                    balances[chain] = {
                        balance,
                        usd_value: usdValue,
                        address: evmWallet.address
                    };

                    totalUsd += usdValue;
                }
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

app.post('/wallet/send', validateApiKey, async (req, res) => {
    try {
        const { encrypted_seed, chain, to, amount, index = 0 } = req.body;

        if (!encrypted_seed || !chain || !to || !amount) {
            return res.status(400).json({ 
                error: 'encrypted_seed, chain, to, and amount required' 
            });
        }

        const mnemonic = decrypt(encrypted_seed);

        if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
            const evmWallet = await createEVMWallet(mnemonic, index);
            const provider = providers[chain];
            const wallet = new ethers.Wallet(evmWallet.privateKey, provider);

            const tx = await wallet.sendTransaction({
                to,
                value: ethers.parseEther(amount)
            });

            const receipt = await tx.wait();

            res.json({
                success: true,
                tx_hash: receipt.hash,
                fee: ethers.formatEther(receipt.gasUsed * receipt.gasPrice),
                chain,
                timestamp: new Date().toISOString()
            });
        } else if (chain === 'bitcoin') {
            res.status(501).json({ 
                error: 'Bitcoin transactions require UTXO management - use external service' 
            });
        } else {
            res.status(400).json({ error: 'Unsupported chain' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/wallet/fee-estimate', validateApiKey, async (req, res) => {
    try {
        const { chain } = req.body;

        if (!chain) {
            return res.status(400).json({ error: 'chain required' });
        }

        if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
            const provider = providers[chain];
            const feeData = await provider.getFeeData();

            res.json({
                success: true,
                chain,
                fee_rates: {
                    gasPrice: ethers.formatUnits(feeData.gasPrice || 0n, 'gwei'),
                    maxFeePerGas: ethers.formatUnits(feeData.maxFeePerGas || 0n, 'gwei'),
                    maxPriorityFeePerGas: ethers.formatUnits(feeData.maxPriorityFeePerGas || 0n, 'gwei')
                },
                timestamp: new Date().toISOString()
            });
        } else {
            res.status(400).json({ error: 'Unsupported chain' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/wallet/validate-address', validateApiKey, (req, res) => {
    try {
        const { chain, address } = req.body;

        if (!chain || !address) {
            return res.status(400).json({ error: 'chain and address required' });
        }

        let isValid = false;

        if (chain === 'bitcoin') {
            isValid = /^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$/.test(address);
        } else if (['ethereum', 'polygon', 'arbitrum'].includes(chain)) {
            isValid = ethers.isAddress(address);
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
    console.error('Error:', err);
    res.status(500).json({ 
        error: 'Internal server error',
        message: err.message 
    });
});

app.listen(PORT, () => {
    console.log(`✅ Multi-Chain Wallet Service running on port ${PORT}`);
    console.log(`📡 Health: http://localhost:${PORT}/health`);
    console.log(`🔐 API Key: ${SEAMOUNT_API_KEY.slice(0, 10)}...`);
});