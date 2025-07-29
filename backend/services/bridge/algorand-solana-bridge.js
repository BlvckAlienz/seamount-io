// algorand-solana-bridge.js
// Location: /backend/services/bridge/algorand-solana-bridge.js

import algosdk from 'algosdk';
import {
    Connection,
    PublicKey,
    Transaction,
    TransactionInstruction,
    SystemProgram,
    SYSVAR_RENT_PUBKEY,
    sendAndConfirmTransaction,
    Keypair
} from '@solana/web3.js';
import {
    Token,
    TOKEN_PROGRAM_ID,
    ASSOCIATED_TOKEN_PROGRAM_ID,
    MintLayout,
    AccountLayout
} from '@solana/spl-token';
import { createLogger } from 'winston';
import FeeCalculator from './fee-calculator.js';
import GeoDetectionMiddleware from '../../middleware/geo-detection.js';

class AlgorandSolanaBridge {
    constructor() {
        this.logger = this.initializeLogger();
        this.feeCalculator = new FeeCalculator();
        this.geoDetector = new GeoDetectionMiddleware();
        this.initializeConnections();
        this.initializeConfig();
        this.bridgeState = {
            pendingTransfers: new Map(),
            completedTransfers: new Map(),
            failedTransfers: new Map()
        };
        this.validators = new Map(); // Multi-sig validators
        
        // Initialize fee tracking for analytics
        this.feeAnalytics = {
            totalFeesCollected: 0,
            feesByTier: new Map(),
            feesByRegion: new Map(),
            averageFeeRate: 0
        };
    }

    initializeLogger() {
        return createLogger({
            level: 'info',
            format: require('winston').format.combine(
                require('winston').format.timestamp(),
                require('winston').format.json()
            ),
            transports: [
                new require('winston').transports.File({ filename: 'logs/bridge.log' }),
                new require('winston').transports.Console()
            ]
        });
    }

    initializeConnections() {
        // Algorand connection
        this.algorandClient = new algosdk.Algodv2(
            process.env.ALGORAND_API_TOKEN,
            process.env.ALGORAND_API_URL,
            ''
        );

        // Solana connection
        this.solanaConnection = new Connection(
            process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com',
            'confirmed'
        );

        this.logger.info('Bridge connections initialized');
    }

    initializeConfig() {
        this.config = {
            // Algorand configuration
            algorand: {
                assetId: parseInt(process.env.USDS_ASSET_ID || '3092770202'),
                decimals: 6,
                bridgeAddress: process.env.ALGORAND_BRIDGE_ADDRESS,
                validatorAddress: process.env.ALGORAND_VALIDATOR_ADDRESS,
                minTransferAmount: 1000000, // 1 USDS (6 decimals)
                maxTransferAmount: 1000000000000, // 1M USDS (6 decimals)
                confirmations: 3,
                gasLimit: 200000
            },
            // Solana configuration
            solana: {
                mintAddress: new PublicKey(process.env.SOLANA_USDS_MINT || 'USDSaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'),
                decimals: 6,
                bridgeAddress: new PublicKey(process.env.SOLANA_BRIDGE_ADDRESS || '11111111111111111111111111111111'),
                validatorAddress: new PublicKey(process.env.SOLANA_VALIDATOR_ADDRESS || '11111111111111111111111111111111'),
                minTransferAmount: 1000000, // 1 USDS (6 decimals)
                maxTransferAmount: 1000000000000, // 1M USDS (6 decimals)
                confirmations: 32,
                priorityFee: 5000 // 0.000005 SOL
            },
            // Bridge configuration - Updated to use dynamic fees
            bridge: {
                validatorThreshold: 2, // 2-of-3 multi-sig
                timeoutMinutes: 30,
                retryAttempts: 3,
                retryDelayMs: 5000,
                feeCollectionAddress: {
                    algorand: process.env.ALGORAND_FEE_COLLECTION_ADDRESS,
                    solana: new PublicKey(process.env.SOLANA_FEE_COLLECTION_ADDRESS || '11111111111111111111111111111111')
                }
            }
        };

        this.logger.info('Bridge configuration loaded with dynamic fee system', this.config);
    }

    // ENHANCED ALGORAND-TO-SOLANA BRIDGE WITH TIERED FEES

    async initiateAlgorandToSolana(params) {
        const { fromAddress, toAddress, amount, userPrivateKey, userIpAddress, userAgent } = params;
        
        try {
            // Input validation
            this.validateBridgeTransfer(amount, 'algorand');
            
            // Detect user location for fee calculation
            const userLocation = await this.geoDetector.detectLocation(userIpAddress, userAgent);
            
            // Calculate dynamic fees based on user location and amount
            const feeDetails = await this.feeCalculator.calculateBridgeFee({
                amount,
                sourceChain: 'algorand',
                destChain: 'solana',
                userLocation,
                transferType: 'cross_chain'
            });

            // Generate unique bridge transaction ID
            const bridgeId = this.generateBridgeId();
            
            // Create algorand lock transaction with fee deduction
            const lockTxnGroup = await this.createAlgorandLockTransactionWithFees({
                fromAddress,
                amount,
                feeDetails,
                bridgeId,
                destinationChain: 'solana',
                destinationAddress: toAddress
            });

            // Sign and submit lock transaction group
            const signedTxnGroup = lockTxnGroup.map(txn => 
                txn.signTxn(algosdk.mnemonicToSecretKey(userPrivateKey).sk)
            );
            
            const txResult = await this.algorandClient.sendRawTransaction(signedTxnGroup).do();
            
            // Store pending transfer with fee information
            this.bridgeState.pendingTransfers.set(bridgeId, {
                bridgeId,
                sourceChain: 'algorand',
                destChain: 'solana',
                sourceAddress: fromAddress,
                destAddress: toAddress,
                amount,
                netAmount: amount - feeDetails.totalFee, // Amount after fees
                feeDetails,
                userLocation,
                algorandTxId: txResult.txId,
                status: 'pending_lock',
                timestamp: Date.now(),
                confirmations: 0
            });

            // Update fee analytics
            this.updateFeeAnalytics(feeDetails, userLocation);

            this.logger.info(`Algorand-to-Solana bridge initiated with tiered fees`, {
                bridgeId,
                algorandTxId: txResult.txId,
                amount,
                netAmount: amount - feeDetails.totalFee,
                feeDetails,
                userLocation: userLocation.country,
                fromAddress,
                toAddress
            });

            // Start monitoring for confirmations
            this.monitorAlgorandTransaction(bridgeId, txResult.txId);

            return {
                bridgeId,
                algorandTxId: txResult.txId,
                status: 'pending_lock',
                feeDetails,
                netAmount: amount - feeDetails.totalFee,
                estimatedCompletionTime: Date.now() + (this.config.bridge.timeoutMinutes * 60000)
            };

        } catch (error) {
            this.logger.error('Failed to initiate Algorand-to-Solana bridge', { error: error.message });
            throw new Error(`Bridge initiation failed: ${error.message}`);
        }
    }

    async createAlgorandLockTransactionWithFees(params) {
        const { fromAddress, amount, feeDetails, bridgeId, destinationChain, destinationAddress } = params;
        
        try {
            // Get network parameters
            const suggestedParams = await this.algorandClient.getTransactionParams().do();
            const txnGroup = [];

            // Transaction 1: Transfer net amount to bridge contract
            const lockTxn = algosdk.makeAssetTransferTxnWithSuggestedParamsFromObject({
                from: fromAddress,
                to: this.config.algorand.bridgeAddress,
                amount: amount - feeDetails.totalFee, // Net amount after fees
                assetIndex: this.config.algorand.assetId,
                suggestedParams: suggestedParams,
                note: algosdk.encodeObj({
                    bridgeId,
                    destinationChain,
                    destinationAddress,
                    timestamp: Date.now(),
                    feeDetails: {
                        totalFee: feeDetails.totalFee,
                        feeRate: feeDetails.effectiveRate,
                        tier: feeDetails.tier
                    }
                })
            });

            // Transaction 2: Transfer fees to fee collection address
            const feeTxn = algosdk.makeAssetTransferTxnWithSuggestedParamsFromObject({
                from: fromAddress,
                to: this.config.bridge.feeCollectionAddress.algorand,
                amount: feeDetails.totalFee,
                assetIndex: this.config.algorand.assetId,
                suggestedParams: suggestedParams,
                note: algosdk.encodeObj({
                    bridgeId,
                    feeType: 'bridge_fee',
                    tier: feeDetails.tier,
                    timestamp: Date.now()
                })
            });

            // Group transactions atomically
            const groupId = algosdk.computeGroupID([lockTxn, feeTxn]);
            lockTxn.group = groupId;
            feeTxn.group = groupId;

            txnGroup.push(lockTxn, feeTxn);

            return txnGroup;

        } catch (error) {
            this.logger.error('Failed to create Algorand lock transaction with fees', { error: error.message });
            throw error;
        }
    }

    // ENHANCED SOLANA-TO-ALGORAND BRIDGE WITH TIERED FEES

    async initiateSolanaToAlgorand(params) {
        const { fromAddress, toAddress, amount, userPrivateKey, userIpAddress, userAgent } = params;
        
        try {
            // Input validation
            this.validateBridgeTransfer(amount, 'solana');
            
            // Detect user location for fee calculation
            const userLocation = await this.geoDetector.detectLocation(userIpAddress, userAgent);
            
            // Calculate dynamic fees based on user location and amount
            const feeDetails = await this.feeCalculator.calculateBridgeFee({
                amount,
                sourceChain: 'solana',
                destChain: 'algorand',
                userLocation,
                transferType: 'cross_chain'
            });

            // Generate unique bridge transaction ID
            const bridgeId = this.generateBridgeId();
            
            // Create solana burn transaction with fee handling
            const burnTxnWithFees = await this.createSolanaBurnTransactionWithFees({
                fromAddress,
                amount,
                feeDetails,
                bridgeId,
                destinationChain: 'algorand',
                destinationAddress: toAddress
            });

            // Sign and submit burn transaction
            const userKeypair = Keypair.fromSecretKey(
                Buffer.from(userPrivateKey, 'hex')
            );
            
            const signature = await sendAndConfirmTransaction(
                this.solanaConnection,
                burnTxnWithFees,
                [userKeypair],
                {
                    commitment: 'confirmed',
                    preflightCommitment: 'confirmed'
                }
            );
            
            // Store pending transfer with fee information
            this.bridgeState.pendingTransfers.set(bridgeId, {
                bridgeId,
                sourceChain: 'solana',
                destChain: 'algorand',
                sourceAddress: fromAddress,
                destAddress: toAddress,
                amount,
                netAmount: amount - feeDetails.totalFee, // Amount after fees
                feeDetails,
                userLocation,
                solanaSignature: signature,
                status: 'pending_burn',
                timestamp: Date.now(),
                confirmations: 0
            });

            // Update fee analytics
            this.updateFeeAnalytics(feeDetails, userLocation);

            this.logger.info(`Solana-to-Algorand bridge initiated with tiered fees`, {
                bridgeId,
                solanaSignature: signature,
                amount,
                netAmount: amount - feeDetails.totalFee,
                feeDetails,
                userLocation: userLocation.country,
                fromAddress,
                toAddress
            });

            // Start monitoring for confirmations
            this.monitorSolanaTransaction(bridgeId, signature);

            return {
                bridgeId,
                solanaSignature: signature,
                status: 'pending_burn',
                feeDetails,
                netAmount: amount - feeDetails.totalFee,
                estimatedCompletionTime: Date.now() + (this.config.bridge.timeoutMinutes * 60000)
            };

        } catch (error) {
            this.logger.error('Failed to initiate Solana-to-Algorand bridge', { error: error.message });
            throw new Error(`Bridge initiation failed: ${error.message}`);
        }
    }

    async createSolanaBurnTransactionWithFees(params) {
        const { fromAddress, amount, feeDetails, bridgeId, destinationChain, destinationAddress } = params;
        
        try {
            const transaction = new Transaction();
            const fromPublicKey = new PublicKey(fromAddress);
            
            // Get associated token account
            const associatedTokenAddress = await Token.getAssociatedTokenAddress(
                ASSOCIATED_TOKEN_PROGRAM_ID,
                TOKEN_PROGRAM_ID,
                this.config.solana.mintAddress,
                fromPublicKey
            );

            // Instruction 1: Transfer fees to fee collection address
            const feeTransferInstruction = Token.createTransferInstruction(
                TOKEN_PROGRAM_ID,
                associatedTokenAddress,
                await Token.getAssociatedTokenAddress(
                    ASSOCIATED_TOKEN_PROGRAM_ID,
                    TOKEN_PROGRAM_ID,
                    this.config.solana.mintAddress,
                    this.config.bridge.feeCollectionAddress.solana
                ),
                fromPublicKey,
                [],
                feeDetails.totalFee
            );

            // Instruction 2: Burn net amount (after fees)
            const burnInstruction = Token.createBurnInstruction(
                TOKEN_PROGRAM_ID,
                this.config.solana.mintAddress,
                associatedTokenAddress,
                fromPublicKey,
                [],
                amount - feeDetails.totalFee
            );

            transaction.add(feeTransferInstruction);
            transaction.add(burnInstruction);

            // Add bridge memo with fee information
            const memoInstruction = new TransactionInstruction({
                keys: [],
                programId: new PublicKey('MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr'),
                data: Buffer.from(JSON.stringify({
                    bridgeId,
                    destinationChain,
                    destinationAddress,
                    action: 'burn',
                    amount: amount - feeDetails.totalFee,
                    feeDetails: {
                        totalFee: feeDetails.totalFee,
                        feeRate: feeDetails.effectiveRate,
                        tier: feeDetails.tier
                    },
                    timestamp: Date.now()
                }))
            });

            transaction.add(memoInstruction);

            // Set recent blockhash and fee payer
            const { blockhash } = await this.solanaConnection.getRecentBlockhash();
            transaction.recentBlockhash = blockhash;
            transaction.feePayer = fromPublicKey;

            return transaction;

        } catch (error) {
            this.logger.error('Failed to create Solana burn transaction with fees', { error: error.message });
            throw error;
        }
    }

    // FEE ANALYTICS AND MONITORING

    updateFeeAnalytics(feeDetails, userLocation) {
        try {
            // Update total fees collected
            this.feeAnalytics.totalFeesCollected += feeDetails.totalFee;

            // Update fees by tier
            const currentTierFees = this.feeAnalytics.feesByTier.get(feeDetails.tier) || 0;
            this.feeAnalytics.feesByTier.set(feeDetails.tier, currentTierFees + feeDetails.totalFee);

            // Update fees by region
            const currentRegionFees = this.feeAnalytics.feesByRegion.get(userLocation.country) || 0;
            this.feeAnalytics.feesByRegion.set(userLocation.country, currentRegionFees + feeDetails.totalFee);

            // Recalculate average fee rate
            const totalTransfers = this.bridgeState.completedTransfers.size + this.bridgeState.pendingTransfers.size;
            if (totalTransfers > 0) {
                this.feeAnalytics.averageFeeRate = this.feeAnalytics.totalFeesCollected / totalTransfers;
            }

            this.logger.info('Fee analytics updated', {
                totalFeesCollected: this.feeAnalytics.totalFeesCollected,
                tier: feeDetails.tier,
                region: userLocation.country,
                feeAmount: feeDetails.totalFee
            });

        } catch (error) {
            this.logger.error('Error updating fee analytics', { error: error.message });
        }
    }

    async getFeeAnalytics() {
        return {
            totalFeesCollected: this.feeAnalytics.totalFeesCollected,
            feesByTier: Object.fromEntries(this.feeAnalytics.feesByTier),
            feesByRegion: Object.fromEntries(this.feeAnalytics.feesByRegion),
            averageFeeRate: this.feeAnalytics.averageFeeRate,
            totalTransfers: this.bridgeState.completedTransfers.size + this.bridgeState.pendingTransfers.size,
            timestamp: Date.now()
        };
    }

    // ENHANCED QUOTE SYSTEM

    async getTransferQuote(params) {
        const { amount, sourceChain, destChain, userIpAddress, userAgent } = params;
        
        try {
            // Detect user location
            const userLocation = await this.geoDetector.detectLocation(userIpAddress, userAgent);
            
            // Calculate fees
            const feeDetails = await this.feeCalculator.calculateBridgeFee({
                amount,
                sourceChain,
                destChain,
                userLocation,
                transferType: 'cross_chain'
            });

            // Calculate network costs
            const networkCosts = await this.calculateNetworkCosts(sourceChain, destChain);

            return {
                amount,
                netAmount: amount - feeDetails.totalFee,
                feeDetails,
                networkCosts,
                estimatedTime: this.getEstimatedTransferTime(sourceChain, destChain),
                userLocation: {
                    country: userLocation.country,
                    tier: feeDetails.tier
                },
                quote: {
                    totalCost: feeDetails.totalFee + networkCosts.total,
                    bridgeFee: feeDetails.totalFee,
                    networkFee: networkCosts.total,
                    savings: this.calculateSavings(feeDetails.totalFee, amount)
                },
                timestamp: Date.now(),
                validUntil: Date.now() + (5 * 60 * 1000) // 5 minutes
            };

        } catch (error) {
            this.logger.error('Error generating transfer quote', { error: error.message });
            throw error;
        }
    }

    async calculateNetworkCosts(sourceChain, destChain) {
        try {
            const costs = {
                source: 0,
                destination: 0,
                total: 0
            };

            if (sourceChain === 'algorand') {
                costs.source = 1000; // 0.001 ALGO in microALGOs
            } else if (sourceChain === 'solana') {
                costs.source = 5000; // 0.000005 SOL in lamports
            }

            if (destChain === 'algorand') {
                costs.destination = 1000; // 0.001 ALGO in microALGOs
            } else if (destChain === 'solana') {
                costs.destination = 5000; // 0.000005 SOL in lamports
            }

            costs.total = costs.source + costs.destination;

            return costs;

        } catch (error) {
            this.logger.error('Error calculating network costs', { error: error.message });
            throw error;
        }
    }

    calculateSavings(bridgeFee, amount) {
        // Compare with traditional remittance services (typically 6-8%)
        const traditionalFee = amount * 0.07; // 7% average
        const savings = traditionalFee - bridgeFee;
        const savingsPercentage = (savings / traditionalFee) * 100;

        return {
            absolute: savings,
            percentage: savingsPercentage,
            traditional: traditionalFee,
            seamount: bridgeFee
        };
    }

    getEstimatedTransferTime(sourceChain, destChain) {
        // Based on network characteristics and confirmations needed
        const algorandTime = 4 * this.config.algorand.confirmations; // 4 seconds per confirmation
        const solanaTime = 1 * this.config.solana.confirmations; // 1 second per confirmation
        
        return algorandTime + solanaTime + 10; // Add 10 seconds for processing
    }

    // EXISTING MONITORING FUNCTIONS (keeping the same logic)

    async monitorAlgorandTransaction(bridgeId, txId) {
        const transfer = this.bridgeState.pendingTransfers.get(bridgeId);
        if (!transfer) return;

        try {
            const txStatus = await this.algorandClient.pendingTransactionInformation(txId).do();
            
            if (txStatus['confirmed-round']) {
                transfer.confirmations++;
                transfer.confirmedRound = txStatus['confirmed-round'];
                
                this.logger.info(`Algorand transaction confirmed`, {
                    bridgeId,
                    txId,
                    confirmations: transfer.confirmations,
                    round: txStatus['confirmed-round']
                });

                if (transfer.confirmations >= this.config.algorand.confirmations) {
                    transfer.status = 'locked';
                    await this.initiateSolanaMint(bridgeId);
                } else {
                    setTimeout(() => this.monitorAlgorandTransaction(bridgeId, txId), 5000);
                }
            } else {
                setTimeout(() => this.monitorAlgorandTransaction(bridgeId, txId), 5000);
            }

        } catch (error) {
            this.logger.error('Error monitoring Algorand transaction', { 
                bridgeId, 
                txId, 
                error: error.message 
            });
            setTimeout(() => this.monitorAlgorandTransaction(bridgeId, txId), 10000);
        }
    }

    async initiateSolanaMint(bridgeId) {
        const transfer = this.bridgeState.pendingTransfers.get(bridgeId);
        if (!transfer || transfer.status !== 'locked') return;

        try {
            transfer.status = 'minting';
            
            // Use net amount (after fees) for minting
            const mintTxn = await this.createSolanaMintTransaction({
                toAddress: transfer.destAddress,
                amount: transfer.netAmount, // Net amount after fees
                bridgeId
            });

            const bridgeKeypair = Keypair.fromSecretKey(
                Buffer.from(process.env.SOLANA_BRIDGE_PRIVATE_KEY, 'hex')
            );
            
            const signature = await sendAndConfirmTransaction(
                this.solanaConnection,
                mintTxn,
                [bridgeKeypair],
                {
                    commitment: 'confirmed',
                    preflightCommitment: 'confirmed'
                }
            );

            transfer.solanaSignature = signature;
            transfer.status = 'completed';
            transfer.completedAt = Date.now();

            this.bridgeState.completedTransfers.set(bridgeId, transfer);
            this.bridgeState.pendingTransfers.delete(bridgeId);

            this.logger.info(`Solana mint completed`, {
                bridgeId,
                solanaSignature: signature,
                amount: transfer.netAmount,
                destAddress: transfer.destAddress
            });

            return signature;

        } catch (error) {
            this.logger.error('Failed to mint on Solana', { bridgeId, error: error.message });
            transfer.status = 'failed';
            transfer.errorMessage = error.message;
            
            this.bridgeState.failedTransfers.set(bridgeId, transfer);
            this.bridgeState.pendingTransfers.delete(bridgeId);
            
            throw error;
        }
    }

    // Keep all existing utility functions with minimal changes
    generateBridgeId() {
        return `bridge_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
    }

    validateBridgeTransfer(amount, sourceChain) {
        const config = this.config[sourceChain];
        
        if (amount < config.minTransferAmount) {
            throw new Error(`Amount below minimum transfer: ${config.minTransferAmount / Math.pow(10, config.decimals)} USDS`);
        }
        
        if (amount > config.maxTransferAmount) {
            throw new Error(`Amount exceeds maximum transfer: ${config.maxTransferAmount / Math.pow(10, config.decimals)} USDS`);
        }
    }

    // All other existing methods remain the same...
    // (keeping the rest of the original bridge functionality)
}

export default AlgorandSolanaBridge;