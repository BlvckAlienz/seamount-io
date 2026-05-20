# Seamount API Platform: Architectural & Security Posture Review

This report provides an in-depth analysis of the **Seamount API Platform** (referred to as Semalt in your query). Seamount is designed as a high-performance "financial operating system for Africa," orchestrating fiat on-ramps, multi-chain web3 wallets, prediction markets, compliance screening, and local AI-driven financial tutoring/coaching.

---

## 🏛️ Architectural Overview

Seamount uses a **dual-backend architectural pattern** combined with a React-based Progressive Web App (PWA) client. It decouples high-throughput, transactional financial logic from locally-hosted AI analytics.

```mermaid
graph TD
    Client[React PWA Client] -->|HTTPS / WSS| API[FastAPI Core Backend]
    
    subgraph Core Platform
        API -->|ORM / SQL| DB[(Supabase PostgreSQL + RLS)]
        API -->|Local HTTP API| QVAC[QVAC Node.js AI Sidecar]
    end
    
    subgraph AI Infrastructure (Local Node)
        QVAC -->|REST| Ollama[Ollama Local Engine]
        Ollama -->|Inference| Model[Llama 3.2 1B / Qwen 3B]
    end
    
    subgraph Blockchain Layers
        API -->|Algorand SDK| ALGO[Algorand Mainnet/Testnet]
        API -->|Tether WDK| WDK[Multi-Chain: BTC, ETH, TON, Polygon]
        API -->|Ripple API| XRP[Ripple Ledger Integration]
    end
    
    subgraph Banking & Custody Integrations
        API -->|Paystack / Flutterwave| NIBSS[NIBSS Nigerian Banking Rails]
        API -->|CSCS Custodian API| CSCS[Central Securities Clearing System]
        API -->|Regfyl API| Regfyl[Compliance & KYC Screening]
    end
```

### 1. The Core Backend (`seamount-io`)
*   **Technology Stack**: Built on **FastAPI (Python)** for asynchronous, high-concurrency request handling, utilizing `asyncio` for non-blocking I/O.
*   **Database Layer**: Leverages **Supabase (PostgreSQL)**. Data security is enforced directly at the SQL level using **Row-Level Security (RLS)**, ensuring strict multi-tenant isolation.
*   **Service-Driven Architecture**: The API router acts as a controller, delegating complex operations to specialized service modules (e.g., `WDKService`, `LegislativeTaxEngine`, `EnhancedOracleService`, `SeamountProtocol`).

### 2. The Local AI Sidecar (`seamount-qvac`)
*   **Technology Stack**: A **Node.js/Express** microservice running locally alongside the main backend (typically on `localhost:11434` / `localhost:3000`).
*   **AI Engine**: Integrates directly with **Ollama** using lightweight models (such as `llama3.2:1b` or `qwen2.5:3b/0.5b`) to handle sensitive customer-facing logic without exposing data to external LLM providers.
*   **The AI Loops**:
    *   **Loop A (Tutor)**: Provides conversational financial literacy instruction using local vector search/retrieval.
    *   **Loop C (Coach)**: Acts as a financial wellbeing coach, checking user sentiment, providing spending advice, and evaluating budget compliance.
    *   **Loop D (Signal Validator)**: Real-time validation of trade setups and prediction signals.
    *   **AML Engine**: Ingests suspicious transactional patterns and automatically drafts Suspicious Transaction Reports (STRs) based on FinCEN and GIABA guidelines.

---

## 🔒 Security Posture Review

Seamount operates in a heavily regulated financial domain (payments, securities tokenization, and digital assets). As such, it implements a multi-layered security strategy:

### 1. Data Isolation via Supabase Row-Level Security (RLS)
The platform enforces security policies directly inside PostgreSQL using Supabase auth claims.
*   **User Isolation**: Table policies require `auth.uid() = user_id` for reads and writes, protecting personal wallets, transaction records, and chat logs.
*   **Merchant Isolation**: Distinct RLS roles separate merchant configurations, customer ledger balances, and fee-splits from retail users.

### 2. Multi-Chain Cryptographic Key Management (WDK-based)
To achieve "WhatsApp-level simplicity" for non-technical users, Seamount abstracts cryptographic operations entirely:
*   **Key Custody**: Multi-chain wallets (Bitcoin, Ethereum, Polygon, TON, and Lightning Network) are provisioned through Tether's **Wallet Development Kit (WDK)**.
*   **Server-Side Signing**: Private keys are encrypted and stored inside the database. When a user requests a transfer, the server fetches the encrypted key, decrypts it in memory, signs the transaction via the local WDK instance, and broadcasts it.
*   **Zero Jargon**: The user never sees mnemonic phrases, gas fees, or native tokens (like MATIC or native ETH). All gas fees are pre-calculated, bundled, and shown as a unified USD or fiat fee.

### 3. Automated AML / OFAC Compliance (The Compliance Engine)
The system guards against money laundering and sanction evasion using a dual programmatic/AI approach (`aml_scoring_service.py`):
*   **OFAC/Sanction Screening**: High-efficiency fuzzy name-matching against active OFAC SDN and PEP lists.
*   **5-Factor Risk Weighting**: Programmatic scoring based on:
    1.  *Identity Verification* (KYC tier level, PEP status).
    2.  *Transaction Amount* (relative to historical averages and local reporting thresholds).
    3.  *Geographical Risk* (IP address vs. registered country, FATF high-risk jurisdictions).
    4.  *Velocity Risk* (transactions within brief windows).
    5.  *Asset Class Risk* (privacy-centric cryptos vs. stablecoins).
*   **Automated STR Drafting**: If the risk score crosses the critical threshold (>75/100), the backend flags the transaction and calls the local QVAC AI engine to compile a legal-grade Suspicious Transaction Report (STR).

---

## 💸 Core Financial Integration Modules

Seamount integrates deeply with national fiat rails and blockchain settlement protocols.

| Service Module | Purpose & Integration | Technical Mechanism |
| :--- | :--- | :--- |
| **`seamount_protocol.py`** | Algorand-native escrow and settlement | Uses atomic swaps (DVP - Delivery vs. Payment) to guarantee that cross-border trade occurs atomically without counterparty risk. |
| **`cscs_connector.py`** | Nigeria Securities Clearing (CSCS) | Connects to authorized CSCS custodians (e.g., Stanbic IBTC) to lock physical equities and issue digital twin tokens on Algorand. |
| **`nibss_connector.py`** | NUBAN Bank & NIBSS Transfers | Wraps Paystack/Flutterwave APIs to execute bank account lookups and instant NIBSS fiat transfers in Nigeria. |
| **`wdk_service.py`** | Tether Wallet Development Kit | Automatically routes transactions to the cheapest chain (e.g., small BTC transfers to Lightning, USD stablecoins to Polygon, large BTC to Mainnet). |
| **`legislative_tax_engine.py`**| Tax Act 2025 Compliance | Calculates Corporate Income Tax (CIT), Personal Income Tax (PIT), VAT, Tertiary Education Tax (TET), and Capital Gains Tax (CGT) on digital assets. |
| **`oracle_service.py`** | 3-Tier Quota-Aware Price Feeds | Resolves real-time crypto prices (Binance $\rightarrow$ CoinGecko $\rightarrow$ DIA), precious/industrial metals (Metals.dev & Yahoo Finance), and forex rates (ExchangeRate-API). |

---

## 🛠️ Key Architectural & Security Recommendations

While the platform is highly sophisticated, several enhancements should be prioritized to move from sandbox to institutional-grade production:

### 1. Transition Key Custody to a Secure HSM/MPC Environment
*   **Current Vulnerability**: The backend acts as a single point of failure by storing encrypted private keys in Supabase and decrypting them in application memory.
*   **Mitigation**: Transition to a Multi-Party Computation (MPC) custody solution (e.g., Fireblocks or Coinbase WaaS) or load key-signing logic into a dedicated Hardware Security Module (HSM).

### 2. Harden the Node.js QVAC API Sidecar Connection
*   **Current Vulnerability**: The `qvac_service.py` client communicates with the Express sidecar over standard unauthenticated HTTP (`http://localhost:3000`).
*   **Mitigation**: 
    *   Bind the Node.js server strictly to `127.0.0.1` to prevent external network access.
    *   Implement an internal API token (e.g., shared secret HMAC header) to verify that all sidecar requests originate solely from the FastAPI backend.

### 3. Establish Circuit Breakers on the Oracle System
*   **Current Vulnerability**: In extreme market events, APIs (like Binance or Yahoo Finance) can experience outages or return stale prices, potentially leading to arbitrage exploits on prediction markets.
*   **Mitigation**: Implement a circuit breaker that halts predictive market trading if all three oracle tiers return pricing discrepancies greater than 5% or if the cache is stale for over 30 minutes.

### 4. Implement Decentralized Escalation for the CSCS Custody Lock
*   **Current Vulnerability**: Locking and unlocking physical securities at CSCS is triggered by backend API calls. If the backend is compromised, tokens could be minted without locked collateral, or physical collateral could be unlocked prematurely.
*   **Mitigation**: Implement a multi-sig authorization flow where unlocking requires cryptographic signatures from both Seamount's automated service and the custodian bank.
