import React, { useState, useEffect } from 'react';
import { TrendingUp, DollarSign, Globe, Shield, Clock, ArrowRight, Calculator, MessageCircle } from 'lucide-react';

// FILE: tools/src/components/SavingsCalculator.tsx
// This replaces your existing SavingsCalculator.tsx completely

// Enhanced UI Components
const Card = ({ children, className = '', variant = 'default' }) => {
  const variants = {
    default: 'bg-white/95 backdrop-blur-sm border border-gray-100',
    glass: 'bg-white/80 backdrop-blur-md border border-white/20',
    success: 'bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200',
    info: 'bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200'
  };
  
  return (
    <div className={`rounded-xl shadow-lg p-6 ${variants[variant]} ${className}`}>
      {children}
    </div>
  );
};

const Button = ({ children, onClick, loading = false, variant = 'primary', size = 'md', className = '', icon: Icon }) => {
  const variants = {
    primary: 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 shadow-lg hover:shadow-xl',
    secondary: 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 hover:border-gray-400',
    outline: 'border-2 border-blue-600 text-blue-600 hover:bg-blue-600 hover:text-white',
    ghost: 'text-blue-600 hover:bg-blue-50'
  };
  
  const sizes = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg'
  };

  return (
    <button
      className={`${variants[variant]} ${sizes[size]} rounded-lg font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 ${className}`}
      onClick={onClick}
      disabled={loading}
    >
      {loading ? (
        <div className="animate-spin w-5 h-5 border-2 border-current border-t-transparent rounded-full" />
      ) : (
        <>
          {Icon && <Icon size={size === 'sm' ? 16 : size === 'lg' ? 24 : 20} />}
          {children}
        </>
      )}
    </button>
  );
};

const Input = ({ label, type = 'text', value, onChange, placeholder, prefix, suffix, error }) => (
  <div className="space-y-2">
    {label && <label className="block text-sm font-semibold text-gray-700">{label}</label>}
    <div className="relative">
      {prefix && <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-medium">{prefix}</span>}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all ${prefix ? 'pl-8' : ''} ${suffix ? 'pr-16' : ''} ${error ? 'border-red-500' : ''}`}
      />
      {suffix && <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">{suffix}</span>}
    </div>
    {error && <p className="text-red-500 text-sm">{error}</p>}
  </div>
);

// Live FX Rates Component
const LiveFXRates = () => {
  const [rates, setRates] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [loading, setLoading] = useState(true);

  const mockRates = [
    { currency: 'Nigerian Naira', code: 'NGN', bankSpread: 8.2, seamountSpread: 1.0, rate: 1547 },
    { currency: 'Kenyan Shilling', code: 'KES', bankSpread: 7.1, seamountSpread: 1.0, rate: 149 },
    { currency: 'Ghanaian Cedi', code: 'GHS', bankSpread: 7.8, seamountSpread: 1.0, rate: 11.8 },
    { currency: 'British Pound', code: 'GBP', bankSpread: 4.2, seamountSpread: 1.0, rate: 0.79 },
    { currency: 'Canadian Dollar', code: 'CAD', bankSpread: 4.5, seamountSpread: 1.0, rate: 1.35 },
    { currency: 'Euro', code: 'EUR', bankSpread: 3.8, seamountSpread: 1.0, rate: 0.92 }
  ];

  useEffect(() => {
    const fetchRates = async () => {
      setLoading(true);
      
      // Simulate API call with retry logic
      try {
        await new Promise(resolve => setTimeout(resolve, 1000));
        setRates(mockRates);
        setLastUpdated(new Date());
      } catch (error) {
        console.error('Rate fetch failed:', error);
        // Fallback to cached rates
        setRates(mockRates);
      } finally {
        setLoading(false);
      }
    };

    fetchRates();
    const interval = setInterval(fetchRates, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded mb-4"></div>
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-4 bg-gray-200 rounded"></div>
          ))}
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
          <TrendingUp className="text-blue-600" size={24} />
          Live FX Rate Comparison
        </h3>
        <div className="text-sm text-gray-500">
          Updated: {lastUpdated.toLocaleTimeString()}
        </div>
      </div>

      <div className="grid gap-4">
        <div className="grid grid-cols-4 gap-2 text-sm font-semibold text-gray-600 pb-2 border-b">
          <span>Currency</span>
          <span className="text-center">Bank Spread</span>
          <span className="text-center">Seamount</span>
          <span className="text-center">Savings</span>
        </div>
        
        {rates.map((rate, i) => (
          <div key={i} className="grid grid-cols-4 gap-2 items-center py-2 hover:bg-gray-50 rounded-lg px-2 transition-colors">
            <div>
              <div className="font-medium text-gray-800">{rate.code}</div>
              <div className="text-xs text-gray-500">{rate.currency}</div>
            </div>
            <div className="text-center text-red-600 font-semibold">
              {rate.bankSpread}%
            </div>
            <div className="text-center text-green-600 font-semibold">
              {rate.seamountSpread}%
            </div>
            <div className="text-center">
              <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-sm font-semibold">
                {(rate.bankSpread - rate.seamountSpread).toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>Pro Tip:</strong> Traditional banks hide 3-8% in FX spreads. Seamount shows real-time rates with transparent 1% spread.
        </p>
      </div>
    </Card>
  );
};

// Enhanced Chatbot Component
const StablecoinChatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      text: "👋 Hi! I'm your stablecoin expert. Ask me how Seamount saves you money on cross-border payments!",
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputText, setInputText] = useState('');

  const responses = {
    'stablecoin': 'Stablecoins are digital currencies pegged 1:1 to USD. They eliminate FX volatility and enable 24/7 instant transfers at a fraction of traditional banking costs.',
    'save': 'You save 60-80% compared to banks! No hidden FX spreads, no 3-5 day delays, no surprise fees. Just transparent, instant transfers.',
    'safe': 'Absolutely! Seamount uses regulated stablecoins with full reserve backing. Bank-level security + blockchain efficiency.',
    'fees': 'Just 1-3% total cost vs banks charging 8-15%. No hidden FX markups, no correspondent banking fees.',
    'countries': 'We support 60+ countries including Nigeria, Kenya, Ghana, South Africa, US, UK, Canada, UAE, and growing fast!',
    'business': 'Perfect for global payroll, supplier payments, treasury management. API available for seamless integration.',
    'default': "I can help you understand stablecoins, fees, safety, supported countries, or business use cases. What interests you most?"
  };

  const handleSend = () => {
    if (!inputText.trim()) return;

    const userMessage = { text: inputText, sender: 'user', timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setInputText('');

    setTimeout(() => {
      const lowerInput = inputText.toLowerCase();
      let response = responses.default;
      
      for (const [key, value] of Object.entries(responses)) {
        if (lowerInput.includes(key)) {
          response = value;
          break;
        }
      }

      const botMessage = { text: response, sender: 'bot', timestamp: new Date() };
      setMessages(prev => [...prev, botMessage]);
    }, 800);
  };

  const quickQuestions = [
    "What's a stablecoin?",
    "How much do I save?",
    "Is it safe?",
    "What are the fees?",
    "Which countries?"
  ];

  return (
    <>
      <Button
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-6 right-6 z-50 shadow-2xl ${isOpen ? 'bg-red-500 hover:bg-red-600' : ''}`}
        icon={isOpen ? null : MessageCircle}
      >
        {isOpen ? '✕' : 'Ask Expert'}
      </Button>

      {isOpen && (
        <div className="fixed bottom-20 right-6 w-80 h-96 bg-white rounded-xl shadow-2xl z-50 flex flex-col border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-4">
            <h3 className="font-bold">Stablecoin Expert</h3>
            <p className="text-sm opacity-90">Get instant answers about cross-border payments</p>
          </div>

          <div className="flex-1 p-4 overflow-y-auto bg-gray-50 space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] p-3 rounded-lg ${
                  msg.sender === 'user' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-white text-gray-800 shadow-sm'
                }`}>
                  {msg.text}
                </div>
              </div>
            ))}
          </div>

          <div className="p-2 bg-gray-100 border-t">
            <div className="flex flex-wrap gap-1 mb-2">
              {quickQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => setInputText(q)}
                  className="text-xs bg-white border rounded px-2 py-1 hover:bg-blue-50 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask anything..."
                className="flex-1 px-3 py-2 border rounded-lg text-sm"
              />
              <Button onClick={handleSend} size="sm">Send</Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

// Enhanced Calculator Logic
const calculateSavings = async (amount, fromCountry, toCountry) => {
  const spreads = {
    'NG': 0.082, 'KE': 0.071, 'GH': 0.078, 'ZA': 0.065,
    'CA': 0.045, 'TR': 0.095, 'CN': 0.055, 'IN': 0.068,
    'US': 0.032, 'UK': 0.038, 'AE': 0.048, 'SG': 0.042
  };

  const currencies = {
    'NG': 'NGN', 'KE': 'KES', 'GH': 'GHS', 'ZA': 'ZAR',
    'CA': 'CAD', 'TR': 'TRY', 'CN': 'CNY', 'IN': 'INR',
    'US': 'USD', 'UK': 'GBP', 'AE': 'AED', 'SG': 'SGD'
  };

  // Simulate API call with retry mechanism
  const rates = { NGN: 1547, KES: 149, GHS: 11.8, ZAR: 18.2, CAD: 1.35, GBP: 0.79 };
  const amountUSD = amount / (rates[currencies[fromCountry]] || 1);
  
  const bankSpread = spreads[fromCountry] || 0.07;
  const traditionalCost = amountUSD * (1 + bankSpread + 0.05); // Bank spread + fees
  const seamountCost = amountUSD * 1.025; // 2.5% total cost
  
  const savings = traditionalCost - seamountCost;
  const savingsPercentage = (savings / traditionalCost) * 100;

  return {
    traditional_cost_usd: traditionalCost,
    seamount_cost_usd: seamountCost,
    savings_amount_usd: savings,
    savings_percentage: savingsPercentage,
    volatility_insight: `FX rates can fluctuate 3-7% daily. Banks hide spreads up to ${(bankSpread * 100).toFixed(1)}%.`,
    country_insight: getCountryInsight(fromCountry, toCountry)
  };
};

const getCountryInsight = (from, to) => {
  const insights = {
    'NG': 'Nigerian remittances exceed $25B annually. Save thousands with transparent stablecoin transfers.',
    'KE': 'Kenya leads Africa in mobile money. Seamount adds global reach with stablecoin efficiency.',
    'GH': 'Ghana receives $4B+ in remittances. Seamount cuts transfer costs by 70%.',
    'default': 'Cross-border payments shouldn\'t cost 8-15%. Experience the stablecoin advantage.'
  };
  return insights[from] || insights.default;
};

// Main Savings Calculator Component
const SavingsCalculator = () => {
  const [amount, setAmount] = useState('1000');
  const [fromCountry, setFromCountry] = useState('NG');
  const [toCountry, setToCountry] = useState('US');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const countries = [
    { code: 'NG', name: 'Nigeria', currency: 'NGN', flag: '🇳🇬' },
    { code: 'KE', name: 'Kenya', currency: 'KES', flag: '🇰🇪' },
    { code: 'GH', name: 'Ghana', currency: 'GHS', flag: '🇬🇭' },
    { code: 'ZA', name: 'South Africa', currency: 'ZAR', flag: '🇿🇦' },
    { code: 'CA', name: 'Canada', currency: 'CAD', flag: '🇨🇦' },
    { code: 'US', name: 'United States', currency: 'USD', flag: '🇺🇸' },
    { code: 'UK', name: 'United Kingdom', currency: 'GBP', flag: '🇬🇧' },
  ];

  const handleCalculate = async () => {
    if (!amount || isNaN(parseFloat(amount))) return;
    
    setLoading(true);
    try {
      const savings = await calculateSavings(parseFloat(amount), fromCountry, toCountry);
      setResults(savings);
    } catch (error) {
      console.error('Calculation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const shareResults = () => {
    if (!results) return;
    
    const fromCountryName = countries.find(c => c.code === fromCountry)?.name || fromCountry;
    const toCountryName = countries.find(c => c.code === toCountry)?.name || toCountry;
    const text = `I save ${results.savings_percentage.toFixed(1)}% on ${amount} transfers from ${fromCountryName} to ${toCountryName} with @seamountusd! 💰 Enterprise stablecoin infrastructure vs traditional banking. No hidden FX spreads, instant settlement.`;
    const url = 'https://tools.seamount.io';
    
    // Try native sharing first (mobile)
    if (navigator.share && navigator.canShare && navigator.canShare({ title: 'Seamount Savings Calculator', text, url })) {
      navigator.share({ 
        title: 'Seamount Cross-Border Savings', 
        text: text, 
        url: url 
      }).catch(err => {
        console.log('Share failed:', err);
        fallbackShare(text, url);
      });
    } else {
      fallbackShare(text, url);
    }
  };

  const fallbackShare = (text, url) => {
    // Create shareable URLs for different platforms
    const linkedinUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}&title=${encodeURIComponent('Seamount Cross-Border Savings Calculator')}&summary=${encodeURIComponent(text)}`;
    const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
    const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(text + ' ' + url)}`;
    
    // Create a modal with sharing options
    const shareModal = document.createElement('div');
    shareModal.innerHTML = `
      <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;">
        <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 400px; width: 90%;">
          <h3 style="margin: 0 0 1rem 0; color: #1f2937;">Share Your Savings</h3>
          <div style="display: flex; flex-direction: column; gap: 0.75rem;">
            <button onclick="window.open('${twitterUrl}', '_blank')" style="padding: 0.75rem 1rem; background: #1da1f2; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">Share on Twitter</button>
            <button onclick="window.open('${linkedinUrl}', '_blank')" style="padding: 0.75rem 1rem; background: #0077b5; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">Share on LinkedIn</button>
            <button onclick="window.open('${whatsappUrl}', '_blank')" style="padding: 0.75rem 1rem; background: #25d366; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">Share on WhatsApp</button>
            <button onclick="navigator.clipboard.writeText('${text.replace(/'/g, "\\'")} ${url}').then(() => alert('Copied to clipboard!')); document.body.removeChild(this.parentElement.parentElement)" style="padding: 0.75rem 1rem; background: #6b7280; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">Copy Link</button>
          </div>
          <button onclick="document.body.removeChild(this.parentElement.parentElement)" style="position: absolute; top: 0.5rem; right: 0.5rem; background: none; border: none; font-size: 1.5rem; cursor: pointer;">×</button>
        </div>
      </div>
    `;
    document.body.appendChild(shareModal);
    
    // Auto-close after 30 seconds
    setTimeout(() => {
      if (document.body.contains(shareModal)) {
        document.body.removeChild(shareModal);
      }
    }, 30000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white">
        <div className="max-w-6xl mx-auto px-4 py-12">
          <div className="text-center">
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              💰 Cross-Border Savings Calculator
            </h1>
            <p className="text-xl text-blue-100 mb-6">
              Discover how stablecoins save you 60-80% on international transfers
            </p>
            <div className="flex flex-wrap justify-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <Clock size={16} />
                <span>2-5 minute settlement</span>
              </div>
              <div className="flex items-center gap-2">
                <Shield size={16} />
                <span>Bank-level security</span>
              </div>
              <div className="flex items-center gap-2">
                <Globe size={16} />
                <span>60+ countries supported</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Calculator Section */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <h2 className="text-2xl font-bold mb-6 text-gray-800 flex items-center gap-3">
                <Calculator className="text-blue-600" size={28} />
                Calculate Your Savings
              </h2>
              
              <div className="grid md:grid-cols-3 gap-6 mb-6">
                <Input
                  label="Amount to Send"
                  type="number"
                  value={amount}
                  onChange={setAmount}
                  placeholder="Enter amount"
                  prefix="$"
                />
                
                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-gray-700">From Country</label>
                  <select
                    value={fromCountry}
                    onChange={(e) => setFromCountry(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    {countries.map(country => (
                      <option key={country.code} value={country.code}>
                        {country.flag} {country.name} ({country.currency})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-gray-700">To Country</label>
                  <select
                    value={toCountry}
                    onChange={(e) => setToCountry(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    {countries.map(country => (
                      <option key={country.code} value={country.code}>
                        {country.flag} {country.name} ({country.currency})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <Button 
                onClick={handleCalculate} 
                loading={loading}
                icon={DollarSign}
                size="lg"
                className="w-full md:w-auto"
              >
                Calculate Savings
              </Button>

              {results && (
                <div className="mt-8 space-y-6">
                  <Card variant="success">
                    <div className="text-center">
                      <h3 className="text-2xl font-bold text-green-800 mb-2">
                        You Save {results.savings_percentage.toFixed(1)}%
                      </h3>
                      <div className="text-lg text-green-700 mb-4">
                        <span className="line-through">${results.traditional_cost_usd.toFixed(2)}</span>
                        {' → '}
                        <span className="font-bold">${results.seamount_cost_usd.toFixed(2)}</span>
                      </div>
                      <p className="text-green-800 font-semibold">
                        Savings: ${results.savings_amount_usd.toFixed(2)}
                      </p>
                    </div>
                  </Card>

                  <Card variant="info">
                    <h4 className="font-bold text-blue-800 mb-2">📊 Market Insight</h4>
                    <p className="text-blue-700 text-sm mb-3">{results.volatility_insight}</p>
                    <p className="text-blue-700 text-sm">{results.country_insight}</p>
                  </Card>

                  <div className="flex flex-wrap gap-3">
                    <Button onClick={shareResults} variant="outline" icon={ArrowRight}>
                      Share Results
                    </Button>
                    <Button 
                      onClick={() => window.open('https://seamount.io/signup', '_blank')} 
                      variant="primary"
                    >
                      Start Saving Now
                    </Button>
                  </div>
                </div>
              )}
            </Card>

            <LiveFXRates />
          </div>

          {/* Educational Sidebar */}
          <div className="space-y-6">
            <Card>
              <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                <Shield className="text-blue-600" size={20} />
                Why Stablecoins Work
              </h3>
              <div className="space-y-3 text-sm text-gray-700">
                <p>✅ <strong>Price Stability:</strong> Pegged 1:1 to USD</p>
                <p>⚡ <strong>Speed:</strong> 2-5 minutes vs 3-5 days</p>
                <p>💰 <strong>Cost:</strong> 1-3% vs bank's 8-15%</p>
                <p>🌍 <strong>24/7 Global:</strong> No banking hours</p>
                <p>🔍 <strong>Transparent:</strong> No hidden FX spreads</p>
              </div>
            </Card>

            <Card>
              <h3 className="font-bold text-lg mb-4">🚀 Seamount Advantage</h3>
              <div className="space-y-4">
                <div className="bg-blue-50 p-3 rounded-lg">
                  <div className="font-semibold text-blue-800">Regulated & Audited</div>
                  <div className="text-blue-700 text-sm">Full reserves, monthly audits</div>
                </div>
                <div className="bg-green-50 p-3 rounded-lg">
                  <div className="font-semibold text-green-800">Enterprise Ready</div>
                  <div className="text-green-700 text-sm">API, bulk payments, treasury</div>
                </div>
                <div className="bg-purple-50 p-3 rounded-lg">
                  <div className="font-semibold text-purple-800">Yield Farming</div>
                  <div className="text-purple-700 text-sm">Earn while you hold USDS</div>
                </div>
              </div>
            </Card>

            <Card>
              <h3 className="font-bold text-lg mb-4">🌍 Why This Matters</h3>
              <p className="text-gray-700 text-sm leading-relaxed">
                Cross-border payments are broken. Banks charge 8-15% in hidden fees, 
                take 3-5 days, and only work business hours. Stablecoins solve this 
                with transparent pricing, instant settlement, and global accessibility.
              </p>
              <Button 
                className="w-full mt-4" 
                variant="outline"
                onClick={() => window.open('https://seamount.io/learn', '_blank')}
              >
                Learn More
              </Button>
            </Card>
          </div>
        </div>
      </div>

      <StablecoinChatbot />
    </div>
  );
};

export default SavingsCalculator;