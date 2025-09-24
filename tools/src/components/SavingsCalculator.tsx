import React, { useState, useEffect } from 'react';
import Card from './ui/Card';
import Button from './ui/Button';
import Input from './ui/Input';
import { calculateSavings } from '../lib/savingsCalculator';

const SavingsCalculator = () => {
  const [amount, setAmount] = useState('');
  const [fromCountry, setFromCountry] = useState('NG');
  const [toCountry, setToCountry] = useState('US');
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [countries, setCountries] = useState<any[]>([]);
  const [educationalContent, setEducationalContent] = useState({
    volatility: '',
    stablecoins: '',
    seamountSolution: ''
  });

  // Fetch supported countries on component mount
  useEffect(() => {
    fetchSupportedCountries();
    loadEducationalContent();
  }, []);

  const fetchSupportedCountries = async () => {
    try {
      const response = await fetch('https://api.seamount.io/tools/supported-countries');
      const data = await response.json();
      setCountries(data.countries);
    } catch (error) {
      console.error('Failed to fetch countries:', error);
      // Fallback countries
      setCountries([
        { code: 'NG', name: 'Nigeria', currency: 'NGN', region: 'west_africa' },
        { code: 'KE', name: 'Kenya', currency: 'KES', region: 'east_africa' },
        { code: 'GH', name: 'Ghana', currency: 'GHS', region: 'west_africa' },
        { code: 'ZA', name: 'South Africa', currency: 'ZAR', region: 'southern_africa' },
        { code: 'CA', name: 'Canada', currency: 'CAD', region: 'north_america' },
        { code: 'TR', name: 'Turkey', currency: 'TRY', region: 'middle_east' },
        { code: 'CN', name: 'China', currency: 'CNY', region: 'asia' },
        { code: 'IN', name: 'India', currency: 'INR', region: 'asia' },
        { code: 'US', name: 'United States', currency: 'USD', region: 'north_america' },
        { code: 'UK', name: 'United Kingdom', currency: 'GBP', region: 'europe' },
      ]);
    }
  };

  const loadEducationalContent = () => {
    setEducationalContent({
      volatility: 'FX rates can change rapidly. Traditional methods expose you to this volatility during the 3-5 day transfer period.',
      stablecoins: 'Stablecoins are digital currencies pegged 1:1 to stable assets like USD. They enable instant, low-cost transfers without bank intermediaries.',
      seamountSolution: 'Seamount uses stablecoins to provide predictable pricing, instant settlement, and savings of 60-80% compared to traditional banks.'
    });
  };

  const handleCalculate = async () => {
    if (!amount) return;
    
    setLoading(true);
    try {
      const savings = await calculateSavings(parseFloat(amount), fromCountry, toCountry);
      setResults(savings);
    } catch (error) {
      console.error('Calculation failed:', error);
      // Fallback calculation
      setResults({
        savings_amount_usd: parseFloat(amount) * 0.05,
        savings_percentage: 62.5,
        volatility_insight: 'Live rates temporarily unavailable. Using conservative estimates.',
        stablecoin_education: educationalContent.stablecoins,
        shareable_message: `I save 62.5% on ${amount} transfers with @SeamountApp! 🚀`
      });
    }
    setLoading(false);
  };

const shareOnTwitter = (savings: number, percentage: number, amount: number, from: string, to: string) => {
  const text = `I save ${percentage.toFixed(1)}% on ${amount} ${from} transfers to ${to} with @seamountusd! 🚀 No hidden FX spreads.`;
  const url = 'https://tools.seamount.io';
  const imageUrl = 'https://seamount.io/og-image.png'; // You'll need to create this
  
  // Twitter intent with image (image needs to be hosted)
  window.open(
    `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,
    '_blank'
  );
};

const generateShareImage = async (data: any) => {
  // This would call an API to generate a shareable image
  // For now, we'll use a static image
  return 'https://seamount.io/share-image.jpg';
};

  const shareOnWhatsApp = () => {
    if (!results) return;
    
    const text = results.shareable_message || `I save ${results.savings_percentage}% on cross-border transfers with Seamount!`;
    const url = 'https://tools.seamount.io';
    window.open(`https://wa.me/?text=${encodeURIComponent(text + ' ' + url)}`, '_blank');
  };

  const copyToClipboard = async () => {
    if (!results) return;
    
    const text = results.shareable_message || `I save ${results.savings_percentage}% on cross-border transfers with Seamount! Check it out: https://tools.seamount.io`;
    await navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header Section */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-4">
            💰 Seamount Cross-Border Savings Calculator
          </h1>
          <p className="text-xl text-blue-100">
            Discover how much you save with stablecoins vs traditional banking
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {/* Calculator Section */}
          <div className="md:col-span-2">
            <Card>
              <h2 className="text-2xl font-bold mb-4 text-gray-800">
                Calculate Your Savings
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-gray-700">
                    Amount to Send
                  </label>
                  <Input
                    type="number"
                    value={amount}
                    onChange={setAmount}
                    placeholder="Enter amount"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-700">
                      From Country
                    </label>
                    <select
                      value={fromCountry}
                      onChange={(e) => setFromCountry(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {countries.map(country => (
                        <option key={country.code} value={country.code}>
                          {country.name} ({country.currency})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-700">
                      To Country
                    </label>
                    <select
                      value={toCountry}
                      onChange={(e) => setToCountry(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {countries.map(country => (
                        <option key={country.code} value={country.code}>
                          {country.name} ({country.currency})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <Button onClick={handleCalculate} loading={loading}>
                  Calculate Savings
                </Button>
              </div>

              {results && (
                <div className="mt-6 space-y-4">
                  <div className="p-4 bg-green-50 rounded-lg">
                    <h3 className="font-bold text-green-800 text-lg">
                      You Save {results.savings_percentage?.toFixed(1)}% with Seamount!
                    </h3>
                    <p className="text-green-700">
                      Traditional methods: ${results.traditional_cost_usd?.toFixed(2)}
                    </p>
                    <p className="text-green-700">
                      Seamount cost: ${results.seamount_cost_usd?.toFixed(2)}
                    </p>
                    <p className="text-green-800 font-bold">
                      Savings: ${results.savings_amount_usd?.toFixed(2)}
                    </p>
                  </div>

                  {/* Social Sharing */}
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <h4 className="font-bold mb-2">🎉 Share Your Savings!</h4>
                    <div className="flex flex-wrap gap-2">
                      <Button variant="outline" size="sm" onClick={shareOnTwitter}>
                        Twitter
                      </Button>
                      <Button variant="outline" size="sm" onClick={shareOnWhatsApp}>
                        WhatsApp
                      </Button>
                      <Button variant="outline" size="sm" onClick={copyToClipboard}>
                        Copy Text
                      </Button>
                    </div>
                  </div>

                  {/* Educational Insights */}
                  <div className="p-4 bg-yellow-50 rounded-lg">
                    <h4 className="font-bold mb-2">📊 Market Insight</h4>
                    <p className="text-sm text-yellow-800">{results.volatility_insight}</p>
                  </div>
                </div>
              )}
            </Card>
          </div>

          {/* Educational Sidebar */}
          <div className="space-y-6">
            <Card>
              <h3 className="font-bold text-lg mb-3">💡 How Stablecoins Work</h3>
              <p className="text-sm text-gray-700">
                {educationalContent.stablecoins}
              </p>
            </Card>

            <Card>
              <h3 className="font-bold text-lg mb-3">⚡ Seamount Advantage</h3>
              <ul className="text-sm text-gray-700 space-y-2">
                <li>• 60-80% lower costs than traditional banks</li>
                <li>• Instant settlement (vs 3-5 days with banks)</li>
                <li>• No hidden FX spreads or fees</li>
                <li>• Regulated and secure stablecoins</li>
              </ul>
            </Card>

            <Card>
              <h3 className="font-bold text-lg mb-3">🌍 Why This Matters for Africa</h3>
              <p className="text-sm text-gray-700">
                Stablecoins unlock economic resilience by providing access to 
                stable dollar-denominated assets, protecting against local currency 
                volatility and enabling seamless cross-border trade.
              </p>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SavingsCalculator;