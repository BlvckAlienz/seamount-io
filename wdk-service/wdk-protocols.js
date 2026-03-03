// FILE: wdk-service/wdk-protocols.js
// ─────────────────────────────────────────────────────────────────────────────
// WDK Protocol Extensions — Swap (Velora/ParaSwap), Lending (Aave V3),
//                           Fiat On-ramp (MoonPay primary, Onramper fallback)
//
// ✅ ZERO new npm packages — uses only ethers (already installed) + native fetch
// ✅ Swap:          https://api.paraswap.io       — free, NO API key required
// ✅ Fiat Primary:  MoonPay widget                — trial key from dashboard.moonpay.com
// ✅ Fiat Fallback: Onramper                      — trial key, 190+ countries incl. Africa
// ✅ Prices:        CoinGecko free public API     — no key required
// ─────────────────────────────────────────────────────────────────────────────

'use strict'

const express    = require('express')
const { ethers } = require('ethers')
const crypto = require('crypto')
const router     = express.Router()

// ── ENV ───────────────────────────────────────────────────────────────────────
const MOONPAY_API_KEY    = process.env.MOONPAY_API_KEY    || ''   // publishable key from MoonPay dashboard
const MOONPAY_SECRET_KEY = process.env.MOONPAY_SECRET_KEY || ''  // sk_live_... mandatory for URL signing
const MOONPAY_ENV        = process.env.MOONPAY_ENV        || 'sandbox'
const ONRAMPER_API_KEY   = process.env.ONRAMPER_API_KEY   || ''   // from onramper.com/get-started (fallback)

// Velora = ParaSwap — no API key required
const PARASWAP_API = 'https://api.paraswap.io'

// ── Chain IDs ─────────────────────────────────────────────────────────────────
const CHAIN_IDS = {
    ethereum: 1,
    polygon:  137,
    arbitrum: 42161,
    bsc:      56
}

// ── RPC providers ────────────────────────────────────────────────────────────
const EVM_PROVIDERS = {
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
    arbitrum: new ethers.JsonRpcProvider('https://arb1.arbitrum.io/rpc')
}

// ── Known token contracts ─────────────────────────────────────────────────────
const TOKEN_CONTRACTS = {
    ethereum: {
        USDT:  '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        USDC:  '0xA0b86991c6218b36c1d19D4a2e9eb0cE3606eB48',
        WETH:  '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
        DAI:   '0x6B175474E89094C44Da98b954EedeAC495271d0F',
        ETH:   '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'  // ParaSwap native token convention
    },
    polygon: {
        USDT:  '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
        USDC:  '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
        WETH:  '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619',
        WMATIC:'0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270',
        MATIC: '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
    },
    arbitrum: {
        USDT:  '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',
        USDC:  '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
        WETH:  '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
        ETH:   '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
    }
}

// ── ABIs ──────────────────────────────────────────────────────────────────────
const ERC20_ABI = [
    'function approve(address spender, uint256 amount) returns (bool)',
    'function balanceOf(address owner) view returns (uint256)',
    'function decimals() view returns (uint8)',
    'function allowance(address owner, address spender) view returns (uint256)'
]

const AAVE_POOL_ABI = [
    'function supply(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)',
    'function withdraw(address asset, uint256 amount, address to) returns (uint256)',
    'function borrow(address asset, uint256 amount, uint256 interestRateMode, uint16 referralCode, address onBehalfOf)',
    'function repay(address asset, uint256 amount, uint256 interestRateMode, address onBehalfOf) returns (uint256)'
]

const AAVE_V3_POOL = {
    ethereum: '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2',
    polygon:  '0x794a61358D6845594F94dc1DB02A252b5b4814aD',
    arbitrum: '0x794a61358D6845594F94dc1DB02A252b5b4814aD'
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function getEvmWallet(plaintext_seed, chain, account_index = 0) {
    const provider = EVM_PROVIDERS[chain]
    if (!provider) throw new Error(`No provider configured for chain: ${chain}`)
    if (account_index === 0) return ethers.Wallet.fromPhrase(plaintext_seed).connect(provider)
    const child = ethers.HDNodeWallet.fromPhrase(plaintext_seed).derivePath(`m/44'/60'/0'/0/${account_index}`)
    return new ethers.Wallet(child.privateKey, provider)
}

function resolveToken(symbolOrAddress, chain) {
    if (symbolOrAddress.startsWith('0x') && symbolOrAddress.length === 42) return symbolOrAddress
    const addr = TOKEN_CONTRACTS[chain]?.[symbolOrAddress.toUpperCase()]
    if (!addr) throw new Error(
        `Unknown token "${symbolOrAddress}" on ${chain}. ` +
        `Known: ${Object.keys(TOKEN_CONTRACTS[chain] || {}).join(', ')}. ` +
        `Or pass the full contract address.`
    )
    return addr
}

function explorerUrl(chain, txHash) {
    const bases = { ethereum: 'etherscan.io', polygon: 'polygonscan.com', arbitrum: 'arbiscan.io' }
    return `https://${bases[chain] || 'etherscan.io'}/tx/${txHash}`
}

const isNativeToken = addr =>
    addr.toLowerCase() === '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'

const asyncRoute = fn => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next)


// ─────────────────────────────────────────────────────────────────────────────
// POST /wdk/swap/quote
// Get a swap price quote via Velora (ParaSwap) — NO API KEY NEEDED
//
// Body:    { token_in, token_out, amount_in, chain? }
// Returns: { amount_out, gas_cost_usd, best_route, price_route }
//
// ⚠️ IMPORTANT: Save the returned `price_route` object and pass it to
//    /wdk/swap/execute — it must not be modified.
// ─────────────────────────────────────────────────────────────────────────────
router.post('/swap/quote', asyncRoute(async (req, res) => {
    const { token_in, token_out, amount_in, chain = 'ethereum' } = req.body

    if (!token_in || !token_out || amount_in == null)
        return res.status(400).json({ success: false, error: 'token_in, token_out, amount_in required' })

    const chainId = CHAIN_IDS[chain]
    if (!chainId)
        return res.status(400).json({
            success: false,
            error: `Unsupported chain: ${chain}. Supported: ${Object.keys(CHAIN_IDS).join(', ')}`
        })

    const tokenInAddr  = resolveToken(token_in,  chain)
    const tokenOutAddr = resolveToken(token_out, chain)
    const provider     = EVM_PROVIDERS[chain]

    // Get source decimals (18 for native ETH/MATIC)
    let srcDecimals = 18
    if (!isNativeToken(tokenInAddr)) {
        srcDecimals = Number(await new ethers.Contract(tokenInAddr, ERC20_ABI, provider).decimals())
    }

    const amountWei = ethers.parseUnits(String(amount_in), srcDecimals).toString()

    console.log(`💱 Swap quote: ${amount_in} ${token_in} → ${token_out} on ${chain}`)

    const url = `${PARASWAP_API}/prices?` + new URLSearchParams({
        srcToken:    tokenInAddr,
        destToken:   tokenOutAddr,
        amount:      amountWei,
        srcDecimals: String(srcDecimals),
        side:        'SELL',
        network:     String(chainId),
        version:     '5'
    }).toString()

    const resp = await fetch(url, { headers: { 'Accept': 'application/json' } })

    if (!resp.ok) {
        const errText = await resp.text()
        console.error(`❌ ParaSwap /prices failed (${resp.status}):`, errText)
        return res.status(502).json({ success: false, error: `Swap quote failed: ${errText}` })
    }

    const data = await resp.json()
    if (!data.priceRoute)
        return res.status(502).json({ success: false, error: 'No price route returned', raw: data })

    const pr           = data.priceRoute
    const destDecimals = pr.destDecimals || 6
    const amount_out   = ethers.formatUnits(pr.destAmount, destDecimals)
    const bestExchange = pr.bestRoute?.[0]?.swaps?.[0]?.swapExchanges?.[0]?.exchange || 'aggregated'

    res.json({
        success:      true,
        token_in,     token_out,
        amount_in,    amount_out,
        gas_cost_usd: pr.gasCostUSD,
        best_route:   bestExchange,
        chain,
        price_route:  pr     // ← REQUIRED: pass this exactly to /wdk/swap/execute
    })
}))


// ─────────────────────────────────────────────────────────────────────────────
// POST /wdk/swap/execute
// Execute a previously quoted swap
//
// Body: { plaintext_seed, price_route, slippage?, account_index?, chain? }
// slippage: percent, default 1 (max recommended: 3)
// ─────────────────────────────────────────────────────────────────────────────
router.post('/swap/execute', asyncRoute(async (req, res) => {
    const {
        plaintext_seed,
        price_route,
        slippage      = 1,
        account_index = 0,
        chain         = 'ethereum'
    } = req.body

    if (!plaintext_seed || !price_route)
        return res.status(400).json({ success: false, error: 'plaintext_seed and price_route required' })

    const chainId = CHAIN_IDS[chain]
    if (!chainId)
        return res.status(400).json({ success: false, error: `Unsupported chain: ${chain}` })

    const wallet = getEvmWallet(plaintext_seed, chain, account_index)
    console.log(`🔄 Executing swap on ${chain} | ${wallet.address.slice(0,10)}...`)

    // Build calldata from ParaSwap
    const buildBody = {
        srcToken:    price_route.srcToken,
        destToken:   price_route.destToken,
        srcAmount:   price_route.srcAmount,
        destAmount:  price_route.destAmount,
        priceRoute:  price_route,
        userAddress: wallet.address,
        slippage:    slippage * 100   // ParaSwap: 1% = 100 basis points
    }

    const buildResp = await fetch(`${PARASWAP_API}/transactions/${chainId}`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body:    JSON.stringify(buildBody)
    })

    if (!buildResp.ok) {
        const errText = await buildResp.text()
        console.error(`❌ ParaSwap /transactions failed (${buildResp.status}):`, errText)
        return res.status(502).json({ success: false, error: `Swap build failed: ${errText}` })
    }

    const txData = await buildResp.json()

    // Approve ParaSwap's tokenTransferProxy if ERC-20 (not native)
    if (!isNativeToken(price_route.srcToken)) {
        const spender       = price_route.tokenTransferProxy
        const srcAmount     = BigInt(price_route.srcAmount)
        const tokenContract = new ethers.Contract(price_route.srcToken, ERC20_ABI, wallet)
        const allowance     = await tokenContract.allowance(wallet.address, spender)

        if (allowance < srcAmount) {
            console.log(`⚙️ Approving ParaSwap tokenTransferProxy...`)
            await (await tokenContract.approve(spender, srcAmount)).wait(1)
            console.log(`✅ Approval confirmed`)
        }
    }

    // Send transaction
    console.log(`⚙️ Submitting swap tx...`)
    const swapTx = await wallet.sendTransaction({
        to:       txData.to,
        data:     txData.data,
        value:    BigInt(txData.value   || '0'),
        gasLimit: txData.gas      ? BigInt(Math.ceil(Number(txData.gas)      * 1.2)) : undefined,
        gasPrice: txData.gasPrice ? BigInt(txData.gasPrice) : undefined
    })

    console.log(`⏳ Submitted: ${swapTx.hash}`)
    const receipt = await swapTx.wait(1)
    console.log(`✅ Swap confirmed block ${receipt.blockNumber}`)

    res.json({
        success:      true,
        tx_hash:      receipt.hash,
        chain,
        token_in:     price_route.srcToken,
        token_out:    price_route.destToken,
        amount_in:    ethers.formatUnits(price_route.srcAmount,  price_route.srcDecimals  || 18),
        amount_out:   ethers.formatUnits(price_route.destAmount, price_route.destDecimals || 6),
        gas_used:     receipt.gasUsed.toString(),
        explorer_url: explorerUrl(chain, receipt.hash)
    })
}))


// ─────────────────────────────────────────────────────────────────────────────
// POST /wdk/lend
// Aave V3: supply / withdraw / borrow / repay
//
// Body: { plaintext_seed, action, token, amount, chain?, account_index? }
// action: 'supply' | 'withdraw' | 'borrow' | 'repay'
// amount: human-readable decimal, e.g. "100". Pass "max" to withdraw everything.
// ─────────────────────────────────────────────────────────────────────────────
router.post('/lend', asyncRoute(async (req, res) => {
    const {
        plaintext_seed, action, token, amount,
        chain = 'ethereum', account_index = 0
    } = req.body

    const VALID = ['supply', 'withdraw', 'borrow', 'repay']
    if (!plaintext_seed || !action || !token || amount == null)
        return res.status(400).json({ success: false, error: 'plaintext_seed, action, token, amount required' })
    if (!VALID.includes(action))
        return res.status(400).json({ success: false, error: `action must be: ${VALID.join(', ')}` })

    const poolAddress = AAVE_V3_POOL[chain]
    if (!poolAddress)
        return res.status(400).json({
            success: false,
            error: `Aave V3 not available on ${chain}. Use: ${Object.keys(AAVE_V3_POOL).join(', ')}`
        })

    const tokenAddr = resolveToken(token, chain)
    const wallet    = getEvmWallet(plaintext_seed, chain, account_index)
    const provider  = EVM_PROVIDERS[chain]
    const decimals  = Number(await new ethers.Contract(tokenAddr, ERC20_ABI, provider).decimals())
    const amountWei = ethers.parseUnits(String(amount), decimals)
    const pool      = new ethers.Contract(poolAddress, AAVE_POOL_ABI, wallet)

    console.log(`🏦 Aave ${action}: ${amount} ${token} on ${chain} | ${wallet.address.slice(0,10)}...`)

    let tx

    if (action === 'supply') {
        const tok = new ethers.Contract(tokenAddr, ERC20_ABI, wallet)
        if (await tok.allowance(wallet.address, poolAddress) < amountWei) {
            console.log(`⚙️ Approving Aave V3 pool...`)
            await (await tok.approve(poolAddress, amountWei)).wait(1)
        }
        tx = await pool.supply(tokenAddr, amountWei, wallet.address, 0)

    } else if (action === 'withdraw') {
        tx = await pool.withdraw(tokenAddr, amount === 'max' ? ethers.MaxUint256 : amountWei, wallet.address)

    } else if (action === 'borrow') {
        // interestRateMode 2 = variable (standard)
        tx = await pool.borrow(tokenAddr, amountWei, 2, 0, wallet.address)

    } else if (action === 'repay') {
        const tok = new ethers.Contract(tokenAddr, ERC20_ABI, wallet)
        if (await tok.allowance(wallet.address, poolAddress) < amountWei) {
            await (await tok.approve(poolAddress, amountWei)).wait(1)
        }
        tx = await pool.repay(tokenAddr, amountWei, 2, wallet.address)
    }

    const receipt = await tx.wait(1)
    console.log(`✅ Aave ${action} confirmed block ${receipt.blockNumber}`)

    res.json({
        success:      true,
        action, chain, token, amount,
        tx_hash:      receipt.hash,
        gas_used:     receipt.gasUsed.toString(),
        explorer_url: explorerUrl(chain, receipt.hash)
    })
}))


// ─────────────────────────────────────────────────────────────────────────────
// POST /wdk/fiat/buy
// Returns a widget URL for fiat → crypto purchase
//
// PROVIDER LOGIC (automatic fallback):
//   Primary:  MoonPay  — use MOONPAY_ENV=sandbox for testing, production when approved
//   Fallback: Onramper — 190+ countries incl. Africa; used if MOONPAY_API_KEY missing
//                        OR if request body contains provider: "onramper"
//
// Body: { plaintext_seed, fiat_amount, fiat_currency?, crypto_currency?,
//         account_index?, chain?, provider? }
// provider: 'moonpay' (default) | 'onramper'
// ─────────────────────────────────────────────────────────────────────────────
router.post('/fiat/buy', asyncRoute(async (req, res) => {
    const {
        plaintext_seed,
        fiat_amount,
        fiat_currency   = 'USD',
        crypto_currency = 'USDT',
        account_index   = 0,
        chain           = 'ethereum',
        provider        = 'moonpay'
    } = req.body

    if (!plaintext_seed || !fiat_amount)
        return res.status(400).json({ success: false, error: 'plaintext_seed and fiat_amount required' })

    // Derive wallet address — crypto goes directly to user's own wallet
    const wallet        = getEvmWallet(plaintext_seed, chain, account_index)
    const walletAddress = wallet.address
    console.log(`💰 Fiat buy: ${fiat_amount} ${fiat_currency} → ${crypto_currency} to ${walletAddress.slice(0,10)}...`)

    // Auto-fallback to Onramper if MoonPay keys not configured
    const moonpayReady     = !!(MOONPAY_API_KEY && MOONPAY_SECRET_KEY)
    const resolvedProvider = (provider === 'moonpay' && moonpayReady) ? 'moonpay' : 'onramper'
    let url

    if (resolvedProvider === 'moonpay') {
        // MoonPay — URL signing is MANDATORY when walletAddress is passed
        // Without signature the widget silently refuses to load
        const widgetBase = MOONPAY_ENV === 'production'
            ? 'https://buy.moonpay.com'
            : 'https://buy-sandbox.moonpay.com'

        const params = new URLSearchParams({
            apiKey:               MOONPAY_API_KEY,
            currencyCode:         crypto_currency.toLowerCase(),
            baseCurrencyCode:     fiat_currency.toLowerCase(),
            baseCurrencyAmount:   String(fiat_amount),
            walletAddress:        walletAddress,
            lockAmount:           'false',
            showWalletAddressForm:'false',
            redirectURL:          process.env.APP_REDIRECT_URL || 'https://seamount.io/wallet'
        })

        // Sign the query string with HMAC-SHA256 using secret key
        const queryString = `?${params.toString()}`
        const signature   = crypto
            .createHmac('sha256', MOONPAY_SECRET_KEY)
            .update(queryString)
            .digest('base64')

        params.append('signature', signature)
        url = `${widgetBase}?${params.toString()}`
        console.log(`✅ MoonPay URL signed (${MOONPAY_ENV})`)

    } else {
        // Onramper fallback
        url = `https://buy.onramper.com?` + new URLSearchParams({
            apiKey:           ONRAMPER_API_KEY,
            onlyGiants:       'false',
            defaultCrypto:    crypto_currency.toUpperCase(),
            defaultFiat:      fiat_currency.toUpperCase(),
            defaultFiatAmount: String(fiat_amount),
            walletAddress:    walletAddress,
            redirectURL:      process.env.APP_REDIRECT_URL || 'https://seamount.io/wallet'
        }).toString()
        console.log(`✅ Onramper URL generated`)
    }

    res.json({
        success:         true,
        url,
        wallet_address:  walletAddress,
        fiat_currency,
        crypto_currency,
        fiat_amount,
        provider:        resolvedProvider,
        note:            'Open this URL in a new browser tab for the user to complete purchase'
    })
}))


// ─────────────────────────────────────────────────────────────────────────────
// GET /wdk/price-rates?tokens=USDT,ETH,BTC
// Live USD prices — CoinGecko free public API (no key required)
// ─────────────────────────────────────────────────────────────────────────────
router.get('/price-rates', asyncRoute(async (req, res) => {
    const tokenFilter = req.query.tokens
        ? req.query.tokens.split(',').map(t => t.trim().toUpperCase())
        : null

    const COINGECKO_IDS = {
        BTC:   'bitcoin',
        ETH:   'ethereum',
        MATIC: 'matic-network',
        SOL:   'solana',
        TRX:   'tron',
        USDT:  'tether',
        USDC:  'usd-coin',
        DAI:   'dai',
        XAUT:  'tether-gold',
        ALGO:  'algorand',
        ARB:   'arbitrum'
    }

    const symbols = tokenFilter || Object.keys(COINGECKO_IDS)
    const ids     = symbols.map(s => COINGECKO_IDS[s]).filter(Boolean).join(',')

    if (!ids)
        return res.status(400).json({
            success: false,
            error: `Unknown tokens. Known symbols: ${Object.keys(COINGECKO_IDS).join(', ')}`
        })

    console.log(`💹 Price rates for: ${symbols.join(', ')}`)

    const resp = await fetch(
        `https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd&include_24hr_change=true`,
        { headers: { 'Accept': 'application/json' } }
    )

    if (!resp.ok)
        return res.status(502).json({ success: false, error: `CoinGecko failed: HTTP ${resp.status}` })

    const data  = await resp.json()
    const rates = {}

    for (const [symbol, geckoId] of Object.entries(COINGECKO_IDS)) {
        if (!tokenFilter || tokenFilter.includes(symbol)) {
            rates[symbol] = {
                usd:        data[geckoId]?.usd            ?? null,
                change_24h: data[geckoId]?.usd_24h_change ?? null
            }
        }
    }

    res.json({ success: true, rates, source: 'coingecko', timestamp: Date.now() })
}))


// ── Error handler ─────────────────────────────────────────────────────────────
router.use((err, req, res, _next) => {
    console.error(`❌ [wdk-protocols] ${req.method} ${req.path} — ${err.message}`)
    res.status(500).json({ success: false, error: err.message || 'Internal protocol error' })
})

module.exports = router