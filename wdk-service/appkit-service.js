// FILE: wdk-service/appkit-service.js
// Circle App Kit — Bridge (CCTP), Swap, Send
// Mounted at /appkit/* in server.js
// Fee injection: 0.5% bridge, 50bps swap — automatic, non-negotiable

'use strict'

const express  = require('express')
const { ethers } = require('ethers')
const bip39    = require('bip39')
const BIP32Factory = require('bip32').default
const ecc      = require('tiny-secp256k1')
const bip32    = BIP32Factory(ecc)
const router   = express.Router()

// ── Config ────────────────────────────────────────────────────────────────────
const CIRCLE_KIT_KEY   = process.env.CIRCLE_KIT_KEY   || ''
const BRIDGE_FEE_RATE  = parseFloat(process.env.BRIDGE_FEE_RATE  || '0.005')  // 0.5%
const SWAP_FEE_BPS     = parseInt(process.env.SWAP_FEE_BPS       || '50')     // 50 bps = 0.5%
const MIN_BRIDGE_FEE   = parseFloat(process.env.MIN_BRIDGE_FEE   || '0.25')   // $0.25 minimum
const WDK_API_KEY      = process.env.WDK_API_KEY || ''

if (!CIRCLE_KIT_KEY) {
    console.warn('⚠️  CIRCLE_KIT_KEY not set — Circle Swap will fail; Bridge still works.')
}

console.log(`🔵 Circle App Kit config: bridge_fee=${(BRIDGE_FEE_RATE*100).toFixed(1)}% swap_fee=${SWAP_FEE_BPS}bps`)

// ── Treasury (fee recipient) by App Kit chain name ────────────────────────────
// EVM L2s (Base, Arbitrum, Optimism, Unichain) derive the same address as Ethereum
const TREASURY = {
    Ethereum   : process.env.TREASURY_ETHEREUM  || '0x35186f2C63550f0EF35C28670947A0425879942b',
    Polygon    : process.env.TREASURY_POLYGON   || '0x561e9a01999dEFB7956D455053F3FE6f88D47291',
    Base       : process.env.TREASURY_ETHEREUM  || '0x35186f2C63550f0EF35C28670947A0425879942b',
    Arbitrum   : process.env.TREASURY_ETHEREUM  || '0x35186f2C63550f0EF35C28670947A0425879942b',
    Avalanche  : process.env.TREASURY_ETHEREUM  || '0x35186f2C63550f0EF35C28670947A0425879942b',
    Optimism   : process.env.TREASURY_ETHEREUM  || '0x35186f2C63550f0EF35C28670947A0425879942b',
    Unichain   : process.env.TREASURY_ETHEREUM  || '0x35186f2C63550f0EF35C28670947A0425879942b',
    Linea      : process.env.TREASURY_ETHEREUM  || '0x35186f2C63550f0EF35C28670947A0425879942b',
    Sei        : process.env.TREASURY_ETHEREUM  || '0x35186f2C63550f0EF35C28670947A0425879942b',
    Solana     : process.env.TREASURY_SOLANA    || 'Ahi1L3DSJaJkcWkTgkro5a5efLwKYyH91GMxSbAhRgAt',
    // Testnets
    Ethereum_Sepolia     : '0x35186f2C63550f0EF35C28670947A0425879942b',
    Arc_Testnet          : '0x35186f2C63550f0EF35C28670947A0425879942b',
    Base_Sepolia         : '0x35186f2C63550f0EF35C28670947A0425879942b',
    Arbitrum_Sepolia     : '0x35186f2C63550f0EF35C28670947A0425879942b',
    Polygon_Amoy_Testnet : '0x561e9a01999dEFB7956D455053F3FE6f88D47291',
    Solana_Devnet        : 'Ahi1L3DSJaJkcWkTgkro5a5efLwKYyH91GMxSbAhRgAt',
}

function getTreasury(chainOrChainDef) {
    // chainDef is a ChainDefinition object from App Kit, or a plain string
    const name = typeof chainOrChainDef === 'string'
        ? chainOrChainDef
        : (chainOrChainDef?.name || '')
    return TREASURY[name] || TREASURY.Ethereum
}

// ── App Kit module loader (handles ESM packages from CJS server) ──────────────
let _modules = null

async function loadCircleModules() {
    if (_modules) return _modules
    try {
        console.log('⏳ Loading Circle App Kit ESM modules...')
        const [appKitMod, viemMod, solanaMod] = await Promise.all([
            import('@circle-fin/app-kit'),
            import('@circle-fin/adapter-viem-v2'),
            import('@circle-fin/adapter-solana-kit'),
        ])
        _modules = {
            AppKit                              : appKitMod.AppKit,
            createViemAdapterFromPrivateKey     : viemMod.createViemAdapterFromPrivateKey,
            createSolanaKitAdapterFromPrivateKey: solanaMod.createSolanaKitAdapterFromPrivateKey,
        }
        console.log('✅ Circle App Kit modules loaded successfully')
    } catch (err) {
        console.error('❌ Circle App Kit module load failed:', err.message)
        throw new Error(`Circle App Kit unavailable — run: npm install @circle-fin/app-kit @circle-fin/adapter-viem-v2 @circle-fin/adapter-solana-kit viem | Error: ${err.message}`)
    }
    return _modules
}

// ── AppKit factory — fee-injected instance ────────────────────────────────────
// Bridge fees are configured at AppKit level (per SDK design).
// Swap fees are per-call via customFee.percentageBps.
async function makeKit() {
    const { AppKit } = await loadCircleModules()
    return new AppKit({
        developerFee: {
            getFee: (params) => {
                const amount   = parseFloat(params?.amount || '0')
                const feeUsd   = Math.max(amount * BRIDGE_FEE_RATE, MIN_BRIDGE_FEE)
                const feeMicro = BigInt(Math.floor(feeUsd * 1_000_000)) // USDC = 6 decimals
                console.log(`💰 Bridge dev fee: $${feeUsd.toFixed(4)} USDC (${feeMicro} μUSDC) on ${amount} USDC`)
                return feeMicro
            },
            getFeeRecipient: (chain) => {
                const addr = getTreasury(chain)
                console.log(`🏦 Dev fee recipient [${chain?.name || chain}]: ${addr}`)
                return addr
            },
        }
    })
}

// ── Key derivation helpers ─────────────────────────────────────────────────────

/** EVM private key from BIP39 mnemonic — path m/44'/60'/0'/0/0 */
function evmPrivKeyFromSeed(plaintext_seed) {
    return ethers.Wallet.fromPhrase(plaintext_seed.trim()).privateKey
}

/**
 * Solana private key (JSON array format) from BIP39 mnemonic
 * Uses BIP44 path m/44'/501'/0'/0' — same as Phantom / hardware wallets
 */
async function solanaPrivKeyFromSeed(plaintext_seed) {
    const { Keypair } = require('@solana/web3.js')
    const seed64 = await bip39.mnemonicToSeed(plaintext_seed.trim())
    const root   = bip32.fromSeed(seed64)
    const child  = root.derivePath("m/44'/501'/0'/0'")
    const keypair = Keypair.fromSeed(child.privateKey)
    // Return 64-byte array as JSON string — accepted by createSolanaKitAdapterFromPrivateKey
    return JSON.stringify(Array.from(keypair.secretKey))
}

// Chains that are NOT EVM (require Solana adapter)
const SOLANA_CHAINS = new Set(['Solana', 'Solana_Devnet'])

/** Build the correct adapter based on chain type */
async function buildAdapter(plaintext_seed, chain) {
    const { createViemAdapterFromPrivateKey, createSolanaKitAdapterFromPrivateKey } = await loadCircleModules()

    if (SOLANA_CHAINS.has(chain)) {
        const solKey = await solanaPrivKeyFromSeed(plaintext_seed)
        return createSolanaKitAdapterFromPrivateKey({ privateKey: solKey })
    }

    // All EVM chains (Ethereum, Polygon, Base, Arbitrum, Avalanche, Optimism, etc.)
    const evmKey = evmPrivKeyFromSeed(plaintext_seed)
    return createViemAdapterFromPrivateKey({ privateKey: evmKey })
}

/** Compute bridge fee locally (mirrors AppKit getFee — used for DB logging) */
function computeBridgeFee(amount) {
    return Math.max(parseFloat(amount) * BRIDGE_FEE_RATE, MIN_BRIDGE_FEE)
}

// ── API key guard at router level ─────────────────────────────────────────────
router.use((req, res, next) => {
    const key = req.headers['x-api-key']
    if (!key || key !== WDK_API_KEY) {
        return res.status(401).json({ success: false, error: 'Invalid API key' })
    }
    next()
})

const wrap = fn => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next)


// ─────────────────────────────────────────────────────────────────────────────
// POST /appkit/bridge/estimate
// Returns fee breakdown BEFORE the user confirms — show this in the UI.
//
// Body: { from_seed, to_seed?, from_chain, to_chain, amount }
// ─────────────────────────────────────────────────────────────────────────────
router.post('/bridge/estimate', wrap(async (req, res) => {
    const { from_seed, to_seed, from_chain, to_chain, amount } = req.body

    if (!from_seed || !from_chain || !to_chain || !amount) {
        return res.status(400).json({ success: false, error: 'from_seed, from_chain, to_chain, amount required' })
    }

    if (!bip39.validateMnemonic(from_seed.trim())) {
        return res.status(400).json({ success: false, error: 'Invalid BIP39 seed (from_seed)' })
    }

    console.log(`📊 Bridge estimate: ${amount} USDC ${from_chain} → ${to_chain}`)

    const kit         = await makeKit()
    const fromAdapter = await buildAdapter(from_seed, from_chain)
    const destSeed    = (to_seed && bip39.validateMnemonic(to_seed.trim())) ? to_seed : from_seed
    const toAdapter   = await buildAdapter(destSeed, to_chain)

    const estimate = await kit.estimateBridge({
        from  : { adapter: fromAdapter, chain: from_chain },
        to    : { adapter: toAdapter,   chain: to_chain   },
        amount: String(amount),
    })

    const seamountFee = computeBridgeFee(amount)

    return res.json({
        success      : true,
        fees         : estimate.fees,
        gas_fees     : estimate.gasFees,
        seamount_fee : seamountFee.toFixed(6),
        amount       : estimate.amount,
        token        : estimate.token,
        from_chain,
        to_chain,
    })
}))

// ─────────────────────────────────────────────────────────────────────────────
// POST /appkit/bridge
// Execute CCTP USDC bridge. Fee is injected automatically via AppKit config.
//
// Body: {
//   from_seed,          BIP39 mnemonic for source chain
//   to_seed?,           BIP39 mnemonic for destination (same as from_seed if EVM→EVM)
//   from_chain,         e.g. "Ethereum", "Polygon", "Solana"
//   to_chain,           e.g. "Base", "Arbitrum", "Ethereum"
//   amount,             human-readable USDC amount e.g. "100.00"
//   recipient_address?, override destination address
//   transfer_speed?,    "FAST" (default) | "SLOW"
//   use_forwarder?,     true = Circle's Forwarding Service mints on destination
// }
// ─────────────────────────────────────────────────────────────────────────────
router.post('/bridge', wrap(async (req, res) => {
    const {
        from_seed,
        to_seed,
        from_chain,
        to_chain,
        amount,
        recipient_address,
        transfer_speed = 'FAST',
        use_forwarder  = false,
    } = req.body

    // ── Validation
    if (!from_seed || !from_chain || !to_chain || !amount) {
        return res.status(400).json({ success: false, error: 'from_seed, from_chain, to_chain, amount required' })
    }
    if (!bip39.validateMnemonic(from_seed.trim())) {
        return res.status(400).json({ success: false, error: 'Invalid BIP39 seed phrase' })
    }
    const parsedAmount = parseFloat(amount)
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
        return res.status(400).json({ success: false, error: 'amount must be a positive number' })
    }
    if (parsedAmount < 1) {
        return res.status(400).json({ success: false, error: 'Minimum bridge amount is 1 USDC' })
    }

    console.log(`🌉 Bridge START: ${amount} USDC  ${from_chain} → ${to_chain}`)
    console.log(`   Speed: ${transfer_speed}  Forwarder: ${use_forwarder}`)

    const kit         = await makeKit()
    const fromAdapter = await buildAdapter(from_seed, from_chain)

    // Build destination context
    const destSeed  = (to_seed && bip39.validateMnemonic(to_seed.trim())) ? to_seed : from_seed
    let   toContext

    if (use_forwarder && recipient_address) {
        // Forwarder + explicit recipient — no destination adapter needed
        toContext = { recipientAddress: recipient_address, chain: to_chain, useForwarder: true }
    } else if (use_forwarder) {
        const toAdapter = await buildAdapter(destSeed, to_chain)
        toContext = { adapter: toAdapter, chain: to_chain, useForwarder: true }
    } else {
        const toAdapter = await buildAdapter(destSeed, to_chain)
        toContext = { adapter: toAdapter, chain: to_chain }
        if (recipient_address) toContext.recipientAddress = recipient_address
    }

    const bridgeParams = {
        from  : { adapter: fromAdapter, chain: from_chain },
        to    : toContext,
        amount: String(amount),
        config: { transferSpeed: transfer_speed },
    }

    const result      = await kit.bridge(bridgeParams)
    const seamountFee = computeBridgeFee(amount)

    console.log(`✅ Bridge result: state=${result.state}  steps=${result.steps?.length}`)

    return res.json({
        success      : result.state === 'success' || result.state === 'pending',
        state        : result.state,
        steps        : result.steps,
        amount       : result.amount,
        token        : result.token,
        from_chain,
        to_chain,
        seamount_fee : seamountFee.toFixed(6),
        provider     : result.provider,
        source       : result.source,
        destination  : result.destination,
    })
}))

// ─────────────────────────────────────────────────────────────────────────────
// POST /appkit/bridge/retry
// Resume a partial bridge (e.g. burn succeeded but mint failed)
//
// Body: { from_seed, to_seed?, bridge_result }
// ─────────────────────────────────────────────────────────────────────────────
router.post('/bridge/retry', wrap(async (req, res) => {
    const { from_seed, to_seed, bridge_result } = req.body

    if (!from_seed || !bridge_result) {
        return res.status(400).json({ success: false, error: 'from_seed and bridge_result required' })
    }

    const fromChain = bridge_result?.source?.chain || 'Ethereum'
    const toChain   = bridge_result?.destination?.chain || 'Ethereum'

    const kit         = await makeKit()
    const fromAdapter = await buildAdapter(from_seed, fromChain)
    const destSeed    = (to_seed && bip39.validateMnemonic(to_seed.trim())) ? to_seed : from_seed
    const toAdapter   = await buildAdapter(destSeed, toChain)

    console.log(`🔄 Bridge retry: ${fromChain} → ${toChain}  state=${bridge_result.state}`)

    const retryResult = await kit.retry(bridge_result, { from: fromAdapter, to: toAdapter })

    return res.json({
        success: retryResult.state === 'success' || retryResult.state === 'pending',
        state  : retryResult.state,
        steps  : retryResult.steps,
    })
}))


// ─────────────────────────────────────────────────────────────────────────────
// POST /appkit/swap/estimate
// Preview swap output before executing
//
// Body: { from_seed, chain, token_in, token_out, amount_in }
// ─────────────────────────────────────────────────────────────────────────────
router.post('/swap/estimate', wrap(async (req, res) => {
    const { from_seed, chain, token_in, token_out, amount_in } = req.body

    if (!from_seed || !chain || !token_in || !token_out || !amount_in) {
        return res.status(400).json({ success: false, error: 'from_seed, chain, token_in, token_out, amount_in required' })
    }
    if (!CIRCLE_KIT_KEY) {
        return res.status(503).json({ success: false, error: 'CIRCLE_KIT_KEY not configured on server' })
    }

    console.log(`📊 Swap estimate: ${amount_in} ${token_in} → ${token_out} on ${chain}`)

    const kit     = await makeKit()
    const adapter = await buildAdapter(from_seed, chain)

    const estimate = await kit.estimateSwap({
        from    : { adapter, chain },
        tokenIn : token_in,
        tokenOut: token_out,
        amountIn: String(amount_in),
        config  : { kitKey: CIRCLE_KIT_KEY, slippageBps: 300 },
    })

    return res.json({
        success          : true,
        estimated_output : estimate.estimatedOutput,
        stop_limit       : estimate.stopLimit,
        fees             : estimate.fees,
        seamount_fee_bps : SWAP_FEE_BPS,
        from_address     : estimate.fromAddress,
        to_address       : estimate.toAddress,
        chain,
        token_in,
        token_out,
        amount_in,
    })
}))

// ─────────────────────────────────────────────────────────────────────────────
// POST /appkit/swap
// Execute same-chain token swap (USDC ↔ EURC, USDC ↔ native, etc.)
// 0.5% Seamount fee injected automatically.
//
// Body: {
//   from_seed,     BIP39 mnemonic
//   chain,         e.g. "Ethereum", "Polygon", "Arc_Testnet"
//   token_in,      e.g. "USDC", "EURC", "NATIVE"
//   token_out,     e.g. "EURC", "USDC"
//   amount_in,     human-readable e.g. "10.00"
//   slippage_bps?, default 300 (3%)
//   stop_limit?,   minimum output amount
// }
// ─────────────────────────────────────────────────────────────────────────────
router.post('/swap', wrap(async (req, res) => {
    const {
        from_seed,
        chain,
        token_in,
        token_out,
        amount_in,
        slippage_bps = 300,
        stop_limit,
    } = req.body

    if (!from_seed || !chain || !token_in || !token_out || !amount_in) {
        return res.status(400).json({ success: false, error: 'from_seed, chain, token_in, token_out, amount_in required' })
    }
    if (!CIRCLE_KIT_KEY) {
        return res.status(503).json({ success: false, error: 'CIRCLE_KIT_KEY not configured on server' })
    }
    if (!bip39.validateMnemonic(from_seed.trim())) {
        return res.status(400).json({ success: false, error: 'Invalid BIP39 seed phrase' })
    }

    console.log(`🔄 Circle Swap: ${amount_in} ${token_in} → ${token_out} on ${chain}  fee=${SWAP_FEE_BPS}bps`)

    const kit     = await makeKit()
    const adapter = await buildAdapter(from_seed, chain)

    const swapConfig = {
        kitKey    : CIRCLE_KIT_KEY,
        slippageBps: parseInt(slippage_bps),
        customFee : {
            percentageBps   : SWAP_FEE_BPS,
            recipientAddress: getTreasury(chain),
        },
    }
    if (stop_limit) swapConfig.stopLimit = String(stop_limit)

    const swapParams = {
        from    : { adapter, chain },
        tokenIn : token_in,
        tokenOut: token_out,
        amountIn: String(amount_in),
        config  : swapConfig,
    }

    const result = await kit.swap(swapParams)

    console.log(`✅ Circle Swap complete: txHash=${result.txHash}  out=${result.amountOut}`)

    return res.json({
        success          : true,
        state            : 'success',
        token_in         : result.tokenIn,
        token_out        : result.tokenOut,
        amount_in        : result.amountIn,
        amount_out       : result.amountOut,
        chain,
        tx_hash          : result.txHash,
        explorer_url     : result.explorerUrl,
        fees             : result.fees,
        from_address     : result.fromAddress,
        to_address       : result.toAddress,
        seamount_fee_bps : SWAP_FEE_BPS,
    })
}))


// ─────────────────────────────────────────────────────────────────────────────
// POST /appkit/send
// Send any supported token via Circle App Kit
// (Enhanced multi-chain send — better than raw WDK for USDC/EURC routing)
//
// Body: { from_seed, chain, token, amount, recipient }
// ─────────────────────────────────────────────────────────────────────────────
router.post('/send', wrap(async (req, res) => {
    const { from_seed, chain, token, amount, recipient } = req.body

    if (!from_seed || !chain || !token || !amount || !recipient) {
        return res.status(400).json({ success: false, error: 'from_seed, chain, token, amount, recipient required' })
    }
    if (!bip39.validateMnemonic(from_seed.trim())) {
        return res.status(400).json({ success: false, error: 'Invalid BIP39 seed phrase' })
    }

    console.log(`📤 Circle Send: ${amount} ${token} on ${chain} → ${recipient.slice(0, 10)}...`)

    const kit     = await makeKit()
    const adapter = await buildAdapter(from_seed, chain)

    const result = await kit.send({
        from  : { adapter, chain },
        to    : recipient,
        amount: String(amount),
        token,
    })

    console.log(`✅ Circle Send complete: state=${result.state}  tx=${result.txHash}`)

    return res.json({
        success     : result.state === 'success',
        state       : result.state,
        tx_hash     : result.txHash,
        explorer_url: result.explorerUrl,
        name        : result.name,
        chain,
        amount,
        token,
        recipient,
    })
}))


// ─────────────────────────────────────────────────────────────────────────────
// POST /appkit/send/estimate
// ─────────────────────────────────────────────────────────────────────────────
router.post('/send/estimate', wrap(async (req, res) => {
    const { from_seed, chain, token, amount, recipient } = req.body

    if (!from_seed || !chain || !token || !amount || !recipient) {
        return res.status(400).json({ success: false, error: 'from_seed, chain, token, amount, recipient required' })
    }

    const kit     = await makeKit()
    const adapter = await buildAdapter(from_seed, chain)

    const estimate = await kit.estimateSend({
        from  : { adapter, chain },
        to    : recipient,
        amount: String(amount),
        token,
    })

    return res.json({
        success : true,
        gas     : estimate.gas?.toString(),
        gas_price: estimate.gasPrice?.toString(),
        fee_eth : estimate.fee,
        chain,
        amount,
        token,
    })
}))


// ─────────────────────────────────────────────────────────────────────────────
// GET /appkit/supported-chains?type=bridge|swap
// ─────────────────────────────────────────────────────────────────────────────
router.get('/supported-chains', wrap(async (req, res) => {
    const { AppKit } = await loadCircleModules()
    const kit         = new AppKit()
    const opType      = req.query.type  // 'bridge' | 'swap' | undefined

    const chains = kit.getSupportedChains(opType || undefined)

    return res.json({
        success: true,
        type   : opType || 'all',
        chains : chains.map(c => ({
            name      : c.name,
            chain     : c.chain,
            is_testnet: c.isTestnet,
            type      : c.type,
            usdc      : c.usdcAddress,
        })),
        count  : chains.length,
    })
}))


// ─────────────────────────────────────────────────────────────────────────────
// GET /appkit/health
// ─────────────────────────────────────────────────────────────────────────────
router.get('/health', wrap(async (req, res) => {
    try {
        const mods = await loadCircleModules()
        return res.json({
            success    : true,
            status     : 'healthy',
            kit_key_set: !!CIRCLE_KIT_KEY,
            modules    : Object.keys(mods),
            bridge_fee : `${(BRIDGE_FEE_RATE * 100).toFixed(2)}%  (min $${MIN_BRIDGE_FEE})`,
            swap_fee   : `${SWAP_FEE_BPS} bps (${(SWAP_FEE_BPS / 100).toFixed(2)}%)`,
            treasury   : { ethereum: TREASURY.Ethereum, solana: TREASURY.Solana },
            timestamp  : new Date().toISOString(),
        })
    } catch (err) {
        return res.status(503).json({ success: false, status: 'unhealthy', error: err.message })
    }
}))


// ── Error handler (must be last) ──────────────────────────────────────────────
router.use((err, req, res, _next) => {
    console.error(`❌ [appkit] ${req.method} ${req.path} —`, err.message)
    const detail = err.cause?.message || null
    res.status(err.status || 500).json({
        success: false,
        error  : err.message,
        detail,
    })
})

module.exports = router