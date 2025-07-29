// Location: /backend/services/bridge/fee-calculator.js

import { createLogger } from 'winston';
import { 
    BRIDGE_FEE_CONFIG, 
    getBaseFeeRate, 
    getVolumeDiscount, 
    getMinimumFee, 
    getMaximumFee, 
    roundFeeAmount,
    validateFeeConfig 
} from '../../config/bridge-fees.js';
import { getTierForCountry } from '../../utils/country-tier-mapping.js';

class FeeCalculator {
    constructor() {
        this.logger = this.initializeLogger();
        this.config = BRIDGE_FEE_CONFIG;
        this.cache = new Map(); // Cache for fee calculations
        this.cacheExpiry = 5 * 60 * 1000; // 5 minutes cache for fees
        
        // Validate configuration on startup
        try {
            validateFeeConfig();
            this.logger.info('Fee configuration validated successfully');
        } catch (error) {
            this.logger.error('Fee configuration validation failed', { error: error.message });
            throw error;
        }
    }

    initializeLogger() {
        return createLogger({
            level: 'info',
            format: require('winston').format.combine(
                require('winston').format.timestamp(),
                require('winston').format.json()
            ),
            transports: [
                new require('winston').transports.File({ filename: 'logs/fee-calculator.log' }),
                new require('winston').transports.Console()
            ]
        });
    }

    /**
     * Calculate bridge fee for a transaction
     * @param {Object} params - Fee calculation parameters
     * @param {string} params.countryCode - User's country code (ISO 3166-1 alpha-2)
     * @param {number} params.amount - Transaction amount in base units (6 decimals)
     * @param {string} params.sourceChain - Source blockchain ('algorand' or 'solana')
     * @param {string} params.destChain - Destination blockchain ('algorand' or 'solana')
     * @param {string} params.partnerId - Optional partner ID for special rates
     * @returns {Object} Fee calculation result
     */
    async calculateBridgeFee(params) {
        const { countryCode, amount, sourceChain, destChain, partnerId = null } = params;
        
        try {
            // Input validation
            this.validateCalculationParams(params);
            
            // Check cache first
            const cacheKey = this.generateCacheKey(params);
            const cached = this.cache.get(cacheKey);
            
            if (cached && (Date.now() - cached.timestamp) < this.cacheExpiry) {
                this.logger.debug('Returning cached fee calculation', { cacheKey });
                return cached.result;
            }

            // Determine user's tier based on country
            const tier = getTierForCountry(countryCode);
            
            // Get base fee rate for this tier
            const baseFeeRate = getBaseFeeRate(tier, amount, partnerId);
            
            // Calculate base fee amount
            let feeAmount = Math.floor(amount * baseFeeRate);
            
            // Apply volume discount if applicable
            const volumeDiscount = getVolumeDiscount(amount);
            if (volumeDiscount > 0) {
                feeAmount = Math.floor(feeAmount * (1 - volumeDiscount));
            }
            
            // Apply minimum and maximum fee limits
            const minFee = getMinimumFee(tier);
            const maxFee = getMaximumFee(tier);
            
            feeAmount = Math.max(feeAmount, minFee);
            feeAmount = Math.min(feeAmount, maxFee);
            
            // Round according to configuration
            feeAmount = roundFeeAmount(feeAmount);
            
            // Calculate net amount (amount user receives after fees)
            const netAmount = amount - feeAmount;
            
            // Build result object
            const result = {
                grossAmount: amount,
                feeAmount: feeAmount,
                netAmount: netAmount,
                feePercentage: (feeAmount / amount) * 100,
                tier: tier,
                baseFeeRate: baseFeeRate,
                volumeDiscount: volumeDiscount,
                volumeDiscountAmount: volumeDiscount > 0 ? Math.floor(amount * baseFeeRate * volumeDiscount) : 0,
                minFeeApplied: feeAmount === minFee,
                maxFeeApplied: feeAmount === maxFee,
                sourceChain: sourceChain,
                destChain: destChain,
                countryCode: countryCode,
                partnerId: partnerId,
                calculatedAt: Date.now()
            };
            
            // Cache the result
            this.cache.set(cacheKey, {
                result: result,
                timestamp: Date.now()
            });
            
            this.logger.info('Bridge fee calculated', {
                amount: amount,
                feeAmount: feeAmount,
                tier: tier,
                countryCode: countryCode,
                volumeDiscount: volumeDiscount
            });
            
            return result;
            
        } catch (error) {
            this.logger.error('Error calculating bridge fee', { 
                params, 
                error: error.message 
            });
            throw new Error(`Fee calculation failed: ${error.message}`);
        }
    }

    /**
     * Calculate multiple fee scenarios for comparison
     * Useful for showing users different pricing options
     * @param {Object} params - Base calculation parameters
     * @param {Array} amounts - Array of amounts to calculate fees for
     * @returns {Array} Array of fee calculation results
     */
    async calculateMultipleFeeScenarios(params, amounts) {
        try {
            const scenarios = [];
            
            for (const amount of amounts) {
                const scenarioParams = { ...params, amount };
                const result = await this.calculateBridgeFee(scenarioParams);
                scenarios.push(result);
            }
            
            return scenarios;
            
        } catch (error) {
            this.logger.error('Error calculating multiple fee scenarios', { 
                params, 
                amounts, 
                error: error.message 
            });
            throw error;
        }
    }

    /**
     * Get fee estimate without full calculation
     * Faster method for quick estimates in UI
     * @param {string} countryCode - User's country code
     * @param {number} amount - Transaction amount
     * @returns {Object} Quick fee estimate
     */
    async getQuickFeeEstimate(countryCode, amount) {
        try {
            const tier = getTierForCountry(countryCode);
            const baseFeeRate = getBaseFeeRate(tier, amount);
            const estimatedFee = Math.floor(amount * baseFeeRate);
            const minFee = getMinimumFee(tier);
            const maxFee = getMaximumFee(tier);
            
            const finalFee = Math.max(Math.min(estimatedFee, maxFee), minFee);
            
            return {
                estimatedFee: finalFee,
                estimatedPercentage: (finalFee / amount) * 100,
                tier: tier,
                isEstimate: true
            };
            
        } catch (error) {
            this.logger.error('Error getting quick fee estimate', { 
                countryCode, 
                amount, 
                error: error.message 
            });
            throw error;
        }
    }

    /**
     * Get fee breakdown for transparency
     * Shows users exactly how their fee is calculated
     * @param {Object} feeResult - Result from calculateBridgeFee
     * @returns {Object} Detailed fee breakdown
     */
    getFeeBreakdown(feeResult) {
        const breakdown = {
            baseCalculation: {
                amount: feeResult.grossAmount,
                baseRate: feeResult.baseFeeRate,
                baseRatePercentage: feeResult.baseFeeRate * 100,
                baseFeeAmount: Math.floor(feeResult.grossAmount * feeResult.baseFeeRate)
            },
            volumeDiscount: {
                applied: feeResult.volumeDiscount > 0,
                discountPercentage: feeResult.volumeDiscount * 100,
                discountAmount: feeResult.volumeDiscountAmount
            },
            limits: {
                minFeeApplied: feeResult.minFeeApplied,
                maxFeeApplied: feeResult.maxFeeApplied,
                minFeeAmount: getMinimumFee(feeResult.tier),
                maxFeeAmount: getMaximumFee(feeResult.tier)
            },
            final: {
                totalFee: feeResult.feeAmount,
                effectiveRate: feeResult.feePercentage,
                netAmount: feeResult.netAmount
            }
        };
        
        return breakdown;
    }

    /**
     * Validate calculation parameters
     * @param {Object} params - Parameters to validate
     */
    validateCalculationParams(params) {
        const { countryCode, amount, sourceChain, destChain } = params;
        
        if (!countryCode || typeof countryCode !== 'string') {
            throw new Error('Valid country code is required');
        }
        
        if (!amount || typeof amount !== 'number' || amount <= 0) {
            throw new Error('Valid amount is required');
        }
        
        if (!sourceChain || !['algorand', 'solana'].includes(sourceChain)) {
            throw new Error('Valid source chain is required (algorand or solana)');
        }
        
        if (!destChain || !['algorand', 'solana'].includes(destChain)) {
            throw new Error('Valid destination chain is required (algorand or solana)');
        }
        
        if (sourceChain === destChain) {
            throw new Error('Source and destination chains cannot be the same');
        }
        
        // Validate amount is within reasonable bounds
        const maxAmount = 10000000000000; // 10M USDS
        if (amount > maxAmount) {
            throw new Error(`Amount exceeds maximum allowed: ${maxAmount / 1000000} USDS`);
        }
    }

    /**
     * Generate cache key for fee calculation
     * @param {Object} params - Calculation parameters
     * @returns {string} Cache key
     */
    generateCacheKey(params) {
        const { countryCode, amount, sourceChain, destChain, partnerId } = params;
        return `fee_${countryCode}_${amount}_${sourceChain}_${destChain}_${partnerId || 'none'}`;
    }

    /**
     * Clear expired cache entries
     */
    clearExpiredCache() {
        const now = Date.now();
        for (const [key, value] of this.cache.entries()) {
            if (now - value.timestamp > this.cacheExpiry) {
                this.cache.delete(key);
            }
        }
    }

    /**
     * Get fee statistics for monitoring
     * @returns {Object} Fee calculation statistics
     */
    getFeeStats() {
        return {
            cacheSize: this.cache.size,
            cacheExpiry: this.cacheExpiry,
            config: {
                baseFees: this.config.baseFees,
                volumeDiscounts: this.config.volumeDiscounts,
                limits: this.config.limits
            }
        };
    }

    /**
     * Clear all cached fee calculations
     */
    clearCache() {
        this.cache.clear();
        this.logger.info('Fee calculator cache cleared');
    }

    /**
     * Get current promotional rates status
     * @returns {Object} Promotional rates information
     */
    getPromotionalStatus() {
        const promoConfig = this.config.promotionalRates.launchPromo;
        const now = new Date();
        
        return {
            launchPromo: {
                active: promoConfig.active,
                isCurrentlyActive: promoConfig.active && 
                    now >= promoConfig.startDate && 
                    now <= promoConfig.endDate,
                discount: promoConfig.discount,
                startDate: promoConfig.startDate,
                endDate: promoConfig.endDate
            },
            partnerRates: Object.keys(this.config.promotionalRates.partnerRates)
        };
    }
}

export default FeeCalculator;