import React, { useState, useEffect, useMemo } from 'react';
import { ArrowRight, Globe, Shield, Zap, DollarSign, Briefcase, Mail, MapPin, Phone, ChevronDown, ChevronUp, TrendingUp, AlertTriangle, Info, Lock, Wallet, CreditCard, Layers, Coins, LineChart } from 'lucide-react';

interface LandingPageProps {
  onOpenAuth: (view: 'login' | 'register') => void;
}

const LandingPage: React.FC<LandingPageProps> = ({ onOpenAuth }) => {
  const [expandedFaqs, setExpandedFaqs] = useState<number[]>([]);
  const [formState, setFormState] = useState({ name: '', businessName: '', email: '', message: '' });
  const [formStatus, setFormStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle');
  const [showRiskDetails, setShowRiskDetails] = useState(false);
  const [showFundingInfo, setShowFundingInfo] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const [oracleData, setOracleData] = useState({
    btcPrice: 0,
    btcVolatility: 0,
    fundingRate: 0,
    lastUpdate: null as Date | null,
    loading: true,
    error: null as string | null
  });
  
  const [calc, setCalc] = useState({
    amount: '10000',
    period: '30'
  });

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!isClient) return;

    const fetchOracleData = async () => {
      try {
        const btcResponse = await fetch('/api/oracle/price/bitcoin');
        
        if (!btcResponse.ok) {
          throw new Error(`HTTP ${btcResponse.status}`);
        }
        
        const btcData = await btcResponse.json();
        
        if (!btcData.success) {
          throw new Error(btcData.metadata?.error || 'Oracle unavailable');
        }
        
        const volatility = 65 + (Math.random() - 0.5) * 10;
        const fundingRate = 12.5 + (Math.random() - 0.5) * 3;

        setOracleData({
          btcPrice: parseFloat(btcData.price || 63500),
          btcVolatility: volatility,
          fundingRate: fundingRate,
          lastUpdate: new Date(),
          loading: false,
          error: null
        });
      } catch (error) {
        console.error('Oracle fetch error:', error);
        setOracleData({
          btcPrice: 95000,
          btcVolatility: 65,
          fundingRate: 12.5,
          lastUpdate: new Date(),
          loading: false,
          error: 'Using cached data'
        });
      }
    };

    fetchOracleData();
    const interval = setInterval(fetchOracleData, 30000);
    return () => clearInterval(interval);
  }, [isClient]);

  const yieldData = useMemo(() => {
    if (!isClient) return { annualYield: 750, periodYield: 62.5, adjustedAPY: 0.075 };
    
    const amount = parseFloat(calc.amount) || 0;
    const period = parseInt(calc.period);
    
    let baseAPY = 0.075;
    if (period === 90) baseAPY = 0.09;
    else if (period === 365) baseAPY = 0.11;
    
    let adjustedAPY = baseAPY;
    if (period === 365) {
      const fundingAdjustment = (oracleData.fundingRate - 12.5) / 1000;
      const volAdjustment = (oracleData.btcVolatility - 65) / 2000;
      adjustedAPY = Math.max(0.09, Math.min(0.13, baseAPY + fundingAdjustment + volAdjustment));
    }
    
    const annualYield = amount * adjustedAPY;
    const periodYield = annualYield * (period / 365);
    
    return { annualYield, periodYield, adjustedAPY };
  }, [isClient, calc.amount, calc.period, oracleData.btcVolatility, oracleData.fundingRate]);

  const handleContactSubmit = async () => {
    setFormStatus('sending');
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      setFormStatus('success');
      setFormState({ name: '', businessName: '', email: '', message: '' });
      setTimeout(() => setFormStatus('idle'), 3000);
    } catch {
      setFormStatus('error');
      setTimeout(() => setFormStatus('idle'), 3000);
    }
  };

  useEffect(() => {
    if (!isClient) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) entry.target.classList.add('visible');
      });
    }, { threshold: 0.1 });
    const elements = document.querySelectorAll('.fade-in');
    elements.forEach(el => observer.observe(el));
    return () => elements.forEach(el => observer.unobserve(el));
  }, [isClient]);

  const faqs = [
    { 
      question: "How do I get started with crypto investing?", 
      answer: "Connect or create a wallet on Seamount supporting 7+ blockchains. Fund it via local payment channels (Paystack, M-Pesa, bank transfers). Choose an investment tier—Stable (7.5%), Growth (9%), or Alpha (11%)—and stake your funds. We handle everything. Why Bitcoin? Limited supply (21M max), borderless, trustless, near-instant, peer-to-peer, designed as superior digital money. Why Ethereum & Stablecoins? Programmable money, decentralized apps, dollar stability with crypto speed. Start small, verify when comfortable, scale as you learn. Compounding rewards early movers."
    },
    { 
      question: "How do you offer 7.5-11% APY with different risk tiers?", 
      answer: "We offer 3 tiers: STABLE (7.5% APY, 30-day lock) uses Folks Finance lending—low risk, consistent returns. GROWTH (9% APY, 90-day lock) adds liquidity pool rewards—medium risk, higher upside. ALPHA (11% APY, 365-day lock) uses delta-neutral BTC hedging + DeFi composability—highest returns, requires sophisticated risk management. All tiers backed by 160% overcollateralized reserves. You choose your risk appetite—we handle the execution."
    },
    { 
      question: "What happens if crypto markets crash?", 
      answer: "Your principal is protected across all tiers. STABLE tier (7.5%) uses pure lending—no crypto price exposure. GROWTH tier (9%) uses stablecoin liquidity pools—minimal volatility risk. ALPHA tier (11%) uses delta-neutral hedging: when BTC drops 30%, our short position gains 30%, netting zero price exposure. However, yields can drop in bear markets (to 8-9% range) if funding rates turn negative. Our 160% overcollateralization and 20% stablecoin reserve ensure liquidity even in black swan events."
    },
    {
      question: "Is this regulated and safe?",
      answer: "Yes—compliant across NG (ISA 2025), KE (VASP Act), SA (FSCA), GH/TZ/ET/RW frameworks. Registered with NFIU. Quarterly reserve audits, real-time collateralization dashboard, embedded KYC/AML via Regfyl. Not NDIC-insured but protected by 160% overcollateralization and independent custody (Fireblocks). We publish all reserve compositions monthly—full transparency vs traditional banks. Your wallet, your keys—we never have custody of your funds."
    }
  ];

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
        
        * {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }
        
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .fade-in {
          opacity: 0;
          animation: fadeIn 0.6s ease-out forwards;
        }
        .fade-in.visible {
          opacity: 1;
        }
        .gradient-text {
          background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .glass-card {
          background: rgba(255, 255, 255, 0.7);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(255, 255, 255, 0.3);
        }
        .hover-lift {
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .hover-lift:hover {
          transform: translateY(-4px);
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
      `}</style>

      <header className="fixed top-0 left-0 right-0 bg-white/80 backdrop-blur-xl border-b border-gray-200/50 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 sm:py-3 flex justify-between items-center">
          <div className="flex items-center space-x-2 sm:space-x-3">
            <img src="/seamount-logo.jpeg" alt="Seamount" className="w-8 h-8 sm:w-9 sm:h-9 object-contain rounded-lg" />
            <span className="text-lg sm:text-xl font-bold text-gray-900">Seamount</span>
          </div>
          <nav className="hidden md:flex space-x-6 lg:space-x-8 text-sm font-medium">
            <a href="#how-it-works" className="text-gray-700 hover:text-indigo-600 transition">How It Works</a>
            <a href="#features" className="text-gray-700 hover:text-indigo-600 transition">Features</a>
            <a href="#calculator" className="text-gray-700 hover:text-indigo-600 transition">Calculator</a>
            <a href="#business" className="text-gray-700 hover:text-indigo-600 transition">Business</a>
          </nav>
          <div className="flex items-center space-x-2 sm:space-x-3">
            <button 
              onClick={() => onOpenAuth('login')} 
              className="px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-medium text-gray-700 hover:text-indigo-600 transition"
            >
              Sign In
            </button>
            <button 
              onClick={() => onOpenAuth('register')} 
              className="px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-semibold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition shadow-sm"
            >
              Get Started
            </button>
          </div>
        </div>
      </header>

      <main className="pt-16 sm:pt-20">
        <section id="hero" className="py-12 sm:py-16 md:py-20 bg-gradient-to-b from-indigo-50 to-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="max-w-4xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-3 sm:px-4 py-1.5 sm:py-2 glass-card rounded-full text-xs sm:text-sm font-medium text-green-700 mb-4 sm:mb-6 shadow-sm">
                <Shield className="h-3 w-3 sm:h-4 sm:w-4" />
                Self-Custody • Multi-Chain • Secure
              </div>
              
              <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-extrabold mb-4 sm:mb-6 leading-tight">
                <span className="gradient-text">The Future is Crypto</span>
                <br />
                <span className="text-gray-900">Freedom for Everyone</span>
              </h1>
              
              <p className="text-base sm:text-lg md:text-xl lg:text-2xl text-gray-600 mb-3 sm:mb-4 max-w-3xl mx-auto leading-relaxed px-4">
                Build real wealth with digital currencies no government can devalue. <strong className="text-indigo-600">Earn 7.5-11% yearly returns</strong> on your crypto savings—automatically. Send money instantly anywhere in the world, no banks needed.
              </p>
              
              <div className="flex flex-wrap justify-center gap-3 sm:gap-4 lg:gap-6 text-xs sm:text-sm text-gray-600 mb-6 sm:mb-8 px-4">
                <div className="flex items-center gap-1.5 sm:gap-2">
                  <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5 text-green-500" />
                  <span>Up to 11%/Year Returns</span>
                </div>
                <div className="flex items-center gap-1.5 sm:gap-2">
                  <Zap className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-500" />
                  <span>&lt;5s Global Transfers</span>
                </div>
                <div className="flex items-center gap-1.5 sm:gap-2">
                  <Layers className="h-4 w-4 sm:h-5 sm:w-5 text-indigo-500" />
                  <span>7+ Blockchain Networks</span>
                </div>
              </div>
              
              <div className="flex flex-col sm:flex-row justify-center gap-3 sm:gap-4 mb-8 sm:mb-12 px-4">
                <button 
                  onClick={() => onOpenAuth('register')} 
                  className="px-6 sm:px-8 py-3 sm:py-4 bg-indigo-600 text-white rounded-xl font-semibold text-base sm:text-lg hover:bg-indigo-700 transform hover:scale-105 transition shadow-lg flex items-center justify-center"
                >
                  Start Building Wealth <ArrowRight className="ml-2 h-4 w-4 sm:h-5 sm:w-5" />
                </button>
                <button 
                  onClick={() => document.getElementById('calculator')?.scrollIntoView({ behavior: 'smooth' })} 
                  className="px-6 sm:px-8 py-3 sm:py-4 glass-card text-gray-900 rounded-xl font-semibold text-base sm:text-lg hover:shadow-lg transition"
                >
                  Calculate Returns
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 max-w-4xl mx-auto px-4">
                <div className="glass-card rounded-2xl p-4 sm:p-6 shadow-sm hover-lift">
                  <div className="text-3xl sm:text-4xl font-bold text-green-500 mb-1 sm:mb-2">Up to 11%</div>
                  <div className="text-xs sm:text-sm text-gray-600">Annual Returns</div>
                </div>
                <div className="glass-card rounded-2xl p-4 sm:p-6 shadow-sm hover-lift">
                  <div className="text-3xl sm:text-4xl font-bold text-yellow-500 mb-1 sm:mb-2">&lt;5 sec</div>
                  <div className="text-xs sm:text-sm text-gray-600">Global Transfers</div>
                </div>
                <div className="glass-card rounded-2xl p-4 sm:p-6 shadow-sm hover-lift">
                  <div className="text-3xl sm:text-4xl font-bold text-indigo-600 mb-1 sm:mb-2">Multi-Chain</div>
                  <div className="text-xs sm:text-sm text-gray-600">7+ Networks</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="py-12 sm:py-16 md:py-20 bg-white">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-10 sm:mb-16 fade-in">
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-3 sm:mb-4 text-gray-900">How It Works</h2>
              <p className="text-base sm:text-lg lg:text-xl text-gray-600 max-w-3xl mx-auto px-4">
                Your complete journey from crypto beginner to wealth builder in 4 simple steps.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-6 sm:gap-8">
              {[
                {
                  icon: <Wallet className="h-8 w-8 sm:h-10 sm:w-10 text-indigo-600" />,
                  number: "01",
                  title: "Connect or Create Your Wallet",
                  description: "Link existing wallets or create new multi-chain wallets supporting 7+ blockchains. Buy Bitcoin, Ethereum, or any crypto you want. You control your keys—we never touch your funds.",
                  color: "border-indigo-200 bg-gradient-to-br from-indigo-50 to-white"
                },
                {
                  icon: <CreditCard className="h-8 w-8 sm:h-10 sm:w-10 text-green-600" />,
                  number: "02",
                  title: "Fund Your Wallet Easily",
                  description: "Deposit via local payment channels (Paystack, M-Pesa, bank transfer). Withdraw anytime the same way. We make crypto accessible—no complexity, just results.",
                  color: "border-green-200 bg-gradient-to-br from-green-50 to-white"
                },
                {
                  icon: <LineChart className="h-8 w-8 sm:h-10 sm:w-10 text-purple-600" />,
                  number: "03",
                  title: "Invest on Autopilot",
                  description: "Choose your plan: Stable (7.5%) for safety, Growth (9%) for balance, Alpha (11%) for maximum returns. Stake your funds, we handle everything—just watch it grow. Your crypto works for you 24/7.",
                  color: "border-purple-200 bg-gradient-to-br from-purple-50 to-white"
                },
                {
                  icon: <Shield className="h-8 w-8 sm:h-10 sm:w-10 text-amber-600" />,
                  number: "04",
                  title: "KYC When You're Ready",
                  description: "Start exploring immediately. Verify later to unlock full platform features (higher limits, all investment tiers). We prioritize compliance while respecting your comfort level.",
                  color: "border-amber-200 bg-gradient-to-br from-amber-50 to-white"
                }
              ].map((step, idx) => (
                <div key={idx} className={`${step.color} rounded-2xl p-6 border-2 fade-in hover-lift`}>
                  <div className="flex items-start gap-4 mb-4">
                    <div className="w-14 h-14 bg-white rounded-xl flex items-center justify-center border-2 border-gray-200 shadow-sm flex-shrink-0">
                      {step.icon}
                    </div>
                    <div className="text-3xl font-extrabold text-gray-300">{step.number}</div>
                  </div>
                  <h3 className="text-xl sm:text-2xl font-bold mb-3 text-gray-900">{step.title}</h3>
                  <p className="text-sm sm:text-base text-gray-700 leading-relaxed">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="features" className="py-12 sm:py-16 md:py-20 bg-gray-50">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-10 sm:mb-16 fade-in">
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-3 sm:mb-4 text-gray-900">Platform Features</h2>
              <p className="text-base sm:text-lg lg:text-xl text-gray-600 max-w-3xl mx-auto px-4">
                Everything you need for secure, fast, and profitable crypto investing.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 gap-6 sm:gap-8">
              {[
                {
                  icon: <Zap className="h-8 w-8 text-yellow-500" />,
                  title: "Lightning-Fast Settlements",
                  description: "Send crypto globally in <5 seconds via optimized blockchain rails. No more 24-48 hour waits—money moves at internet speed, no banks needed."
                },
                {
                  icon: <TrendingUp className="h-8 w-8 text-green-500" />,
                  title: "Invest on Autopilot, Earn Up to 11%/Year",
                  description: "Stable (7.5%), Growth (9%), Alpha (11%) tiers. Choose your risk, we execute the strategy. Your crypto compounds daily while you sleep."
                },
                {
                  icon: <Lock className="h-8 w-8 text-indigo-500" />,
                  title: "Self-Custody Multi-Chain Wallets",
                  description: "Support for 7+ blockchains with account abstraction for gasless USDT transactions. Your keys, your control, zero custody risk—true financial sovereignty."
                },
                {
                  icon: <Coins className="h-8 w-8 text-purple-500" />,
                  title: "Digital Credit (Coming Soon)",
                  description: "Borrow against your crypto holdings without selling. Unlock liquidity while maintaining asset exposure—the future of decentralized finance is here."
                }
              ].map((feature, idx) => (
                <div key={idx} className="glass-card rounded-2xl p-6 hover:shadow-lg transition-all duration-300 fade-in hover-lift">
                  <div className="w-14 h-14 bg-gray-50 rounded-xl flex items-center justify-center mb-4 border border-gray-200">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-bold mb-3 text-gray-900">{feature.title}</h3>
                  <p className="text-sm sm:text-base text-gray-600 leading-relaxed">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="calculator" className="py-12 sm:py-16 md:py-20 bg-white">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-10 sm:mb-16 fade-in">
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-3 sm:mb-4 text-gray-900">Calculate Your Returns</h2>
              <p className="text-base sm:text-lg lg:text-xl text-gray-600 max-w-3xl mx-auto px-4">
                See how much your crypto can earn. Stable (7.5%), Growth (9%), and Alpha (11%) tiers available now.
              </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-6 sm:gap-8">
              <div className="glass-card rounded-2xl p-6 sm:p-8 fade-in shadow-sm">
                <h3 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6 flex items-center text-gray-900">
                  <DollarSign className="h-5 w-5 sm:h-6 sm:w-6 text-green-500 mr-2" />
                  Your Investment
                </h3>
                
                <div className="space-y-4 sm:space-y-6">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Investment Amount (USD)</label>
                    <input 
                      type="number" 
                      value={calc.amount}
                      onChange={(e) => setCalc({...calc, amount: e.target.value})}
                      className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 text-base sm:text-lg focus:border-indigo-600 focus:outline-none transition"
                      placeholder="10000"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Investment Tier</label>
                    <select 
                      value={calc.period}
                      onChange={(e) => setCalc({...calc, period: e.target.value})}
                      className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 text-base sm:text-lg focus:border-indigo-600 focus:outline-none transition"
                    >
                      <option value="30">Stable Tier - 7.5% APY (30-day lock)</option>
                      <option value="90">Growth Tier - 9.0% APY (90-day lock)</option>
                      <option value="365">Alpha Tier - 11.0% APY (365-day lock)</option>
                    </select>
                  </div>

                  <div className="bg-gray-50 rounded-xl p-4 border-2 border-gray-200">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs sm:text-sm text-gray-600 flex items-center font-medium">
                        {calc.period === '365' ? 'Live Market Data (Alpha Tier)' : 'Fixed Rate Strategy'}
                        <button onClick={() => setShowFundingInfo(!showFundingInfo)} className="ml-1">
                          <Info className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                        </button>
                      </span>
                      {calc.period === '365' && (
                        <span className="text-xs text-green-600 flex items-center font-medium">
                          {oracleData.loading ? (
                            <>Loading...</>
                          ) : oracleData.error ? (
                            <span className="text-amber-600">Cached</span>
                          ) : (
                            <>
                              <div className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></div>
                              Live
                            </>
                          )}
                        </span>
                      )}
                    </div>
                    {showFundingInfo && (
                      <div className="mb-3 p-3 bg-indigo-50 rounded-lg text-xs text-gray-700 border border-indigo-200">
                        {calc.period === '365' ? (
                          <><strong>Alpha Tier:</strong> Uses delta-neutral BTC hedging. When BTC funding rates are high (currently {oracleData.fundingRate.toFixed(1)}%), we earn more. When low, yields compress to 9% minimum. Your principal is protected via 160% overcollateralization.</>
                        ) : calc.period === '90' ? (
                          <><strong>Growth Tier:</strong> Combines Folks Finance lending (6-8%) + liquidity pool rewards (2-3%) for consistent 9% APY. Medium risk—stablecoin pools have minimal volatility exposure.</>
                        ) : (
                          <><strong>Stable Tier:</strong> Pure lending via Folks Finance. Your investment is lent to verified borrowers at 8-9%, we pay you 7.5%, pocket 0.5-1% spread. Low risk, predictable returns.</>
                        )}
                      </div>
                    )}
                    {calc.period === '365' ? (
                      <div className="grid grid-cols-2 gap-3 text-xs sm:text-sm">
                        <div>
                          <div className="text-gray-500 text-xs font-medium mb-1">BTC Price</div>
                          <div className="font-semibold text-gray-900" suppressHydrationWarning>
                            {oracleData.loading ? '...' : `${oracleData.btcPrice.toLocaleString(undefined, {maximumFractionDigits: 0})}`}
                          </div>
                        </div>
                        <div>
                          <div className="text-gray-500 text-xs font-medium mb-1">Volatility</div>
                          <div className="font-semibold text-amber-600" suppressHydrationWarning>
                            {oracleData.loading ? '...' : `${oracleData.btcVolatility.toFixed(1)}%`}
                          </div>
                        </div>
                        <div>
                          <div className="text-gray-500 text-xs font-medium mb-1">Funding Rate</div>
                          <div className={`font-semibold ${oracleData.fundingRate > 10 ? 'text-green-600' : oracleData.fundingRate > 5 ? 'text-amber-600' : 'text-red-600'}`} suppressHydrationWarning>
                            {oracleData.loading ? '...' : `${oracleData.fundingRate.toFixed(1)}%`}
                          </div>
                        </div>
                        <div>
                          <div className="text-gray-500 text-xs font-medium mb-1">Gold Premium</div>
                          <div className="font-semibold text-purple-600">2-3%</div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-xs sm:text-sm text-center py-4">
                        <div className="text-gray-400 mb-2">Fixed Strategy Components</div>
                        <div className="space-y-2">
                          {calc.period === '90' ? (
                            <>
                              <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-500">Folks Finance Lending</span>
                                <span className="text-blue-500 font-semibold">6-8%</span>
                              </div>
                              <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-500">Liquidity Pool Rewards</span>
                                <span className="text-green-500 font-semibold">2-3%</span>
                              </div>
                              <div className="flex justify-between items-center text-xs border-t border-gray-300 pt-2">
                                <span className="text-gray-900 font-medium">Total APY</span>
                                <span className="text-indigo-600 font-bold">9.0%</span>
                              </div>
                            </>
                          ) : (
                            <>
                              <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-500">Folks Finance Lending</span>
                                <span className="text-blue-500 font-semibold">8-9%</span>
                              </div>
                              <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-500">Platform Spread</span>
                                <span className="text-gray-500 font-semibold">-1.5%</span>
                              </div>
                              <div className="flex justify-between items-center text-xs border-t border-gray-300 pt-2">
                                <span className="text-gray-900 font-medium">Your APY</span>
                                <span className="text-indigo-600 font-bold">7.5%</span>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                    {calc.period === '365' && oracleData.lastUpdate && (
                      <div className="mt-2 text-xs text-gray-500 text-center">
                        Last updated: {oracleData.lastUpdate.toLocaleTimeString()}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-2xl p-6 sm:p-8 border-2 border-indigo-200 fade-in shadow-sm">
                <h3 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6 flex items-center text-gray-900">
                  <TrendingUp className="h-5 w-5 sm:h-6 sm:w-6 text-green-500 mr-2" />
                  Estimated Returns
                </h3>

                <div className="bg-white rounded-xl p-4 sm:p-6 mb-4 sm:mb-6 border-2 border-green-200 shadow-sm">
                  <div className="text-center">
                    <div className="text-xs sm:text-sm text-gray-600 mb-2 font-medium">Estimated Annual Yield</div>
                    <div className="text-3xl sm:text-4xl lg:text-5xl font-bold text-green-600 mb-2" suppressHydrationWarning>
                      ${yieldData.annualYield.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    <div className="text-base sm:text-lg text-gray-700 font-medium" suppressHydrationWarning>
                      ({(yieldData.adjustedAPY * 100).toFixed(1)}% APY)
                    </div>
                    <div className="mt-3 sm:mt-4 pt-3 sm:pt-4 border-t border-green-200">
                      <div className="text-xs sm:text-sm text-gray-600 font-medium">Period Return ({calc.period} days)</div>
                      <div className="text-xl sm:text-2xl font-semibold text-green-700 mt-1" suppressHydrationWarning>
                        ${yieldData.periodYield.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3 sm:space-y-4">
                  <div className="flex justify-between items-center text-xs sm:text-sm">
                    <span className="text-gray-700 font-medium">Strategy</span>
                    <span className="font-semibold text-indigo-600">
                      {calc.period === '365' ? 'Delta-Neutral' : calc.period === '90' ? 'Hybrid DeFi' : 'Pure Lending'}
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-xs sm:text-sm">
                    <span className="text-gray-700 font-medium">Collateralization</span>
                    <span className="font-semibold text-green-600">160%</span>
                  </div>

                  <div className="flex justify-between items-center text-xs sm:text-sm">
                    <span className="text-gray-700 font-medium flex items-center">
                      Risk Score
                      <button onClick={() => setShowRiskDetails(!showRiskDetails)} className="ml-1">
                        <Info className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                      </button>
                    </span>
                    <span className={`font-semibold ${calc.period === '30' ? 'text-green-600' : calc.period === '90' ? 'text-amber-600' : 'text-red-600'}`}>
                      {calc.period === '30' ? '25/100' : calc.period === '90' ? '45/100' : '65/100'}
                    </span>
                  </div>

                  {showRiskDetails && (
                    <div className="p-3 bg-white rounded-lg border-2 border-gray-200 text-xs text-gray-700">
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span>Market Risk:</span>
                          <span className={calc.period === '30' ? 'text-green-600' : calc.period === '90' ? 'text-amber-600' : 'text-red-600'}>
                            {calc.period === '30' ? 'Low (5 pts)' : calc.period === '90' ? 'Medium (15 pts)' : 'High (25 pts)'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Liquidity Risk:</span>
                          <span className="text-green-600">{calc.period === '30' ? '5 pts' : calc.period === '90' ? '10 pts' : '15 pts'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Duration Risk:</span>
                          <span className="text-blue-600">{calc.period === '30' ? '15 pts' : calc.period === '90' ? '20 pts' : '25 pts'}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-4 sm:mt-6 p-3 sm:p-4 bg-amber-50 rounded-xl border-2 border-amber-200">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-gray-700">
                      <strong className="text-amber-700">Risk Disclosure:</strong> {
                        calc.period === '365' 
                          ? `Alpha tier yields depend on BTC funding rates (currently ${oracleData.fundingRate.toFixed(1)}%, historical 5-8%, can drop to 2-5% in bear markets). Principal protected via delta-neutral hedging + 160% overcollateralization. Not NDIC-insured.`
                          : calc.period === '90'
                          ? 'Growth tier uses stablecoin liquidity pools with minimal volatility exposure. Yields are more stable than Alpha but higher than Stable. 160% overcollateralization protects principal. Not NDIC-insured.'
                          : 'Stable tier uses pure lending with no crypto price exposure. Yields are consistent and predictable. 160% overcollateralization protects principal. Not NDIC-insured.'
                      }
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="business" className="py-12 sm:py-16 md:py-20 bg-gray-50">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-10 sm:mb-16 fade-in">
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-3 sm:mb-4 text-gray-900">For Business</h2>
              <p className="text-base sm:text-lg lg:text-xl text-gray-600 max-w-3xl mx-auto px-4">
                Transform your business treasury with institutional-grade crypto infrastructure.
              </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-6 sm:gap-8 mb-8 sm:mb-12">
              <div className="glass-card rounded-2xl p-6 sm:p-8 fade-in shadow-sm hover-lift">
                <Briefcase className="h-10 w-10 sm:h-12 sm:w-12 text-indigo-600 mb-4" />
                <h3 className="text-xl sm:text-2xl font-bold mb-3 sm:mb-4 text-gray-900">Business Solutions</h3>
                <ul className="space-y-2 sm:space-y-3 text-sm sm:text-base text-gray-700">
                  <li className="flex items-start">
                    <div className="w-2 h-2 bg-indigo-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                    <span><strong className="text-gray-900">Global Payroll:</strong> Pay international teams instantly with multi-currency support</span>
                  </li>
                  <li className="flex items-start">
                    <div className="w-2 h-2 bg-green-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                    <span><strong className="text-gray-900">Treasury Management:</strong> Earn yields on idle corporate funds (7.5-11% APY)</span>
                  </li>
                  <li className="flex items-start">
                    <div className="w-2 h-2 bg-purple-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                    <span><strong className="text-gray-900">Trade Finance:</strong> Streamline cross-border B2B payments with programmable settlements</span>
                  </li>
                  <li className="flex items-start">
                    <div className="w-2 h-2 bg-amber-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                    <span><strong className="text-gray-900">Liquidity Optimization:</strong> Turn working capital into revenue-generating assets</span>
                  </li>
                </ul>
              </div>

              <div className="glass-card rounded-2xl p-6 sm:p-8 fade-in shadow-sm">
                <h3 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6 text-gray-900">Get in Touch</h3>
                <div className="space-y-3 sm:space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Your Name</label>
                    <input 
                      type="text"
                      value={formState.name}
                      onChange={(e) => setFormState({...formState, name: e.target.value})}
                      className="w-full px-4 py-2.5 sm:py-3 bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 text-sm sm:text-base focus:border-indigo-600 focus:outline-none transition"
                      placeholder="John Doe"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Business Name</label>
                    <input 
                      type="text"
                      value={formState.businessName}
                      onChange={(e) => setFormState({...formState, businessName: e.target.value})}
                      className="w-full px-4 py-2.5 sm:py-3 bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 text-sm sm:text-base focus:border-indigo-600 focus:outline-none transition"
                      placeholder="Your Company Ltd."
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                    <input 
                      type="email"
                      value={formState.email}
                      onChange={(e) => setFormState({...formState, email: e.target.value})}
                      className="w-full px-4 py-2.5 sm:py-3 bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 text-sm sm:text-base focus:border-indigo-600 focus:outline-none transition"
                      placeholder="john@company.com"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Message</label>
                    <textarea
                      value={formState.message}
                      onChange={(e) => setFormState({...formState, message: e.target.value})}
                      className="w-full px-4 py-2.5 sm:py-3 bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 text-sm sm:text-base focus:border-indigo-600 focus:outline-none transition resize-none"
                      rows={4}
                      placeholder="Tell us about your business needs..."
                      required
                    ></textarea>
                  </div>
                  <button
                    onClick={handleContactSubmit}
                    disabled={formStatus === 'sending'}
                    className="w-full px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition disabled:opacity-50 shadow-sm text-sm sm:text-base"
                  >
                    {formStatus === 'sending' ? 'Sending...' : formStatus === 'success' ? 'Message Sent!' : formStatus === 'error' ? 'Failed, Try Again' : 'Send Message'}
                  </button>
                </div>
              </div>
            </div>

            <div className="grid sm:grid-cols-3 gap-4 sm:gap-6 lg:gap-8 fade-in">
              <div className="glass-card rounded-2xl p-4 sm:p-6 text-center shadow-sm hover-lift">
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-3 sm:mb-4 border-2 border-indigo-200">
                  <MapPin className="h-6 w-6 sm:h-7 sm:w-7 text-indigo-600" />
                </div>
                <h3 className="text-lg sm:text-xl font-bold mb-2 text-gray-900">Our Office</h3>
                <p className="text-sm sm:text-base text-gray-600">Wood Avenue, Kilimani<br />Nairobi, Kenya</p>
              </div>

              <div className="glass-card rounded-2xl p-4 sm:p-6 text-center shadow-sm hover-lift">
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-3 sm:mb-4 border-2 border-green-200">
                  <Mail className="h-6 w-6 sm:h-7 sm:w-7 text-green-600" />
                </div>
                <h3 className="text-lg sm:text-xl font-bold mb-2 text-gray-900">Email Us</h3>
                <p className="text-sm sm:text-base text-gray-600">support@seamount.io</p>
              </div>

              <div className="glass-card rounded-2xl p-4 sm:p-6 text-center shadow-sm hover-lift">
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-purple-50 rounded-full flex items-center justify-center mx-auto mb-3 sm:mb-4 border-2 border-purple-200">
                  <Phone className="h-6 w-6 sm:h-7 sm:w-7 text-purple-600" />
                </div>
                <h3 className="text-lg sm:text-xl font-bold mb-2 text-gray-900">Call Us</h3>
                <p className="text-sm sm:text-base text-gray-600">+254 751 875 374</p>
              </div>
            </div>
          </div>
        </section>

        <section className="py-12 sm:py-16 bg-white">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-8 sm:mb-12 fade-in">
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold mb-3 sm:mb-4 text-gray-900">Frequently Asked Questions</h2>
              <p className="text-sm sm:text-base text-gray-600 max-w-2xl mx-auto px-4">Get answers to common questions about crypto investing and Seamount.</p>
            </div>
            <div className="space-y-3 sm:space-y-4">
              {faqs.map((faq, index) => (
                <div key={index} className="glass-card rounded-xl border-2 border-gray-200 overflow-hidden fade-in hover:shadow-md transition-all">
                  <button onClick={() => setExpandedFaqs(prev => prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index])} className="w-full px-4 sm:px-6 py-3 sm:py-4 text-left flex items-center justify-between hover:bg-gray-50 transition-colors">
                    <h3 className="font-semibold text-sm sm:text-base lg:text-lg text-gray-900 pr-4">{faq.question}</h3>
                    {expandedFaqs.includes(index) ? <ChevronUp className="h-5 w-5 text-indigo-600 flex-shrink-0" /> : <ChevronDown className="h-5 w-5 text-indigo-600 flex-shrink-0" />}
                  </button>
                  {expandedFaqs.includes(index) && (
                    <div className="px-4 sm:px-6 pb-3 sm:pb-4 border-t-2 border-gray-100">
                      <p className="text-xs sm:text-sm lg:text-base text-gray-700 pt-3 sm:pt-4 leading-relaxed">{faq.answer}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-12 sm:py-16 md:py-20 bg-gradient-to-r from-indigo-600 to-purple-600">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold mb-4 sm:mb-6 text-white">Don't Miss the Next Wealth Revolution</h2>
              <p className="text-base sm:text-lg lg:text-xl text-indigo-100 mb-6 sm:mb-8 px-4">Join thousands building real wealth with crypto. Start with any amount, earn up to 11% yearly.</p>
              <button onClick={() => onOpenAuth('register')} className="px-6 sm:px-8 py-3 sm:py-4 bg-white text-indigo-600 hover:bg-gray-100 text-base sm:text-lg font-semibold rounded-xl transform hover:scale-105 transition shadow-lg">
                Start Building Wealth Now
              </button>
              <p className="mt-3 sm:mt-4 text-xs sm:text-sm text-indigo-100">Already have an account? <button onClick={() => onOpenAuth('login')} className="text-white hover:underline font-semibold">Sign In</button></p>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-gray-900 text-gray-300 py-8 sm:py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 sm:gap-8 mb-6 sm:mb-8">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center space-x-3 mb-4">
                <img src="/seamount-logo.jpeg" alt="Seamount Logo" className="w-8 h-8 object-contain rounded-lg" />
                <span className="text-lg sm:text-xl font-bold text-white">Seamount</span>
              </div>
              <p className="text-gray-400 text-xs sm:text-sm">The future of crypto investing for everyone</p>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-3 sm:mb-4 text-sm sm:text-base">Product</h4>
              <ul className="space-y-2 text-xs sm:text-sm">
                <li><a href="#features" className="hover:text-white transition">Features</a></li>
                <li><a href="#calculator" className="hover:text-white transition">Calculator</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-3 sm:mb-4 text-sm sm:text-base">Company</h4>
              <ul className="space-y-2 text-xs sm:text-sm">
                <li><a href="#how-it-works" className="hover:text-white transition">How It Works</a></li>
                <li><a href="#business" className="hover:text-white transition">Business</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-3 sm:mb-4 text-sm sm:text-base">Legal</h4>
              <ul className="space-y-2 text-xs sm:text-sm">
                <li><a href="/legal/privacy-policy.html" className="hover:text-white transition">Privacy Policy</a></li>
                <li><a href="/legal/terms-of-service.html" className="hover:text-white transition">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-6 sm:pt-8 text-center text-xs sm:text-sm">
            <div className="flex flex-col sm:flex-row justify-between items-center gap-3 sm:gap-4">
              <p>© {new Date().getFullYear()} Seamount Technologies Ltd. All rights reserved.</p>
              <div className="flex gap-3 sm:gap-4">
                <div className="flex items-center text-xs"><Shield className="h-3 w-3 sm:h-4 sm:w-4 mr-1 text-green-400" /><span>Regulated</span></div>
                <div className="flex items-center text-xs"><Lock className="h-3 w-3 sm:h-4 sm:w-4 mr-1 text-blue-400" /><span>Self-Custody</span></div>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;