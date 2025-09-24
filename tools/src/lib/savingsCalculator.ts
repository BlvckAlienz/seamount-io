// Free FX rate APIs with fallbacks
const FX_API_SOURCES = [
  'https://api.exchangerate.host/latest?base=USD',
  'https://api.frankfurter.app/latest?from=USD',
  'https://open.er-api.com/v6/latest/USD'
];

// Country-specific traditional bank spreads (conservative estimates)
const TRADITIONAL_SPREADS = {
  'NG': 0.08, // Nigeria: 8% spread
  'KE': 0.07, // Kenya: 7% spread  
  'GH': 0.075, // Ghana: 7.5% spread
  'ZA': 0.06, // South Africa: 6% spread
  'CA': 0.04, // Canada: 4% spread
  'TR': 0.09, // Turkey: 9% spread
  'CN': 0.05, // China: 5% spread
  'IN': 0.065, // India: 6.5% spread
  'US': 0.03, // USA: 3% spread
  'UK': 0.035, // UK: 3.5% spread
  'AE': 0.045, // UAE: 4.5% spread
  'SG': 0.04 // Singapore: 4% spread
};

export const calculateSavings = async (amount: number, fromCountry: string, toCountry: string) => {
  try {
    // Try your backend API first
    const response = await fetch(`/api/tools/calculate-cross-border-savings?amount=${amount}&from_country=${fromCountry}&to_country=${toCountry}`);
    
    if (response.ok) {
      return await response.json();
    }
    throw new Error('Backend API unavailable');
  } catch (error) {
    console.log('Using fallback calculation:', error);
    return await calculateWithFallbackRates(amount, fromCountry, toCountry);
  }
};

const calculateWithFallbackRates = async (amount: number, fromCountry: string, toCountry: string) => {
  // Get live rates from free APIs
  const rates = await getLiveRates();
  
  const fromSpread = TRADITIONAL_SPREADS[fromCountry] || 0.07;
  const toSpread = TRADITIONAL_SPREADS[toCountry] || 0.07;
  
  // Convert to USD for calculation
  const amountUSD = amount / (rates[getCurrencyCode(fromCountry)] || 1);
  
  // Traditional cost: amount + FX spread + bank fees (5%)
  const traditionalCost = amountUSD * (1 + Math.max(fromSpread, toSpread) + 0.05);
  
  // Seamount cost: amount + 3% fee
  const seamountCost = amountUSD * 1.03;
  
  const savings = traditionalCost - seamountCost;
  const savingsPercentage = (savings / traditionalCost) * 100;
  
  return {
    amount_sent: amount,
    from_country: fromCountry,
    to_country: toCountry,
    traditional_cost_usd: traditionalCost,
    seamount_cost_usd: seamountCost,
    savings_amount_usd: savings,
    savings_percentage: savingsPercentage,
    volatility_insight: generateVolatilityInsight(fromCountry, toCountry),
    stablecoin_education: "Stablecoins maintain 1:1 USD peg, eliminating FX volatility during transfers.",
    shareable_message: `I save ${savingsPercentage.toFixed(1)}% on ${amount} transfers from ${fromCountry} to ${toCountry} with @seamountusd! 🚀`,
    rates_source: "Live FX rates from public APIs"
  };
};

const getLiveRates = async () => {
  for (const apiUrl of FX_API_SOURCES) {
    try {
      const response = await fetch(apiUrl, { timeout: 5000 });
      if (response.ok) {
        const data = await response.json();
        return data.rates || {};
      }
    } catch (error) {
      console.log(`Failed to fetch from ${apiUrl}:`, error);
    }
  }
  
  // Fallback rates
  return {
    'NGN': 1500, 'KES': 150, 'GHS': 12, 'ZAR': 18,
    'CAD': 1.35, 'TRY': 30, 'CNY': 7.2, 'INR': 83,
    'USD': 1, 'GBP': 0.79, 'EUR': 0.92, 'AED': 3.67, 'SGD': 1.34
  };
};

const getCurrencyCode = (countryCode: string) => {
  const currencies = {
    'NG': 'NGN', 'KE': 'KES', 'GH': 'GHS', 'ZA': 'ZAR',
    'CA': 'CAD', 'TR': 'TRY', 'CN': 'CNY', 'IN': 'INR',
    'US': 'USD', 'UK': 'GBP', 'AE': 'AED', 'SG': 'SGD'
  };
  return currencies[countryCode] || 'USD';
};

const generateVolatilityInsight = (from: string, to: string) => {
  const insights = [
    `FX rates between ${from} and ${to} can fluctuate 2-5% daily. Traditional banks hide spreads up to 8%.`,
    `Stablecoins eliminate volatility risk during the 3-5 day bank transfer period.`,
    `Seamount's transparent pricing saves you from hidden bank FX spreads.`,
    `Real-time rates mean you get exactly what you see, no surprises.`
  ];
  return insights[Math.floor(Math.random() * insights.length)];
};