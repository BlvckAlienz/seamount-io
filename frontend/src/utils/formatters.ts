// ============================================================================
// NUMBER FORMATTING UTILITIES
// ============================================================================

/**
 * Format number as currency with commas, no decimals
 * @example formatCurrency(1600000) => "1,600,000"
 */
export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

/**
 * Format number as currency with $ prefix, no decimals
 * @example formatCurrencyUSD(1600000) => "$1,600,000"
 */
export const formatCurrencyUSD = (value: number): string => {
  return `$${formatCurrency(value)}`;
};

/**
 * Format number as currency with decimals (for precision displays)
 * @example formatCurrencyWithDecimals(1600000.50) => "$1,600,000.50"
 */
export const formatCurrencyWithDecimals = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};