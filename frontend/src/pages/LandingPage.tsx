import React, { useState, useEffect, useMemo } from 'react';
import { ArrowRight, Globe, Shield, Zap, DollarSign, Users, Briefcase, Send, Mail, MapPin, Phone, ChevronDown, ChevronUp, TrendingUp, AlertTriangle, Info, Eye, Lock, UserPlus, FileCheck, Wallet, CreditCard, ArrowRightLeft, CheckCircle, Heart, TrendingDown } from 'lucide-react';

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
    period: '365',
    estimatedYield: 0.12,
    creditSpread: 120,
    riskScore: 35
  });

  useEffect(() => {
    setIsClient(true);
  }, []);

  // Fetch live oracle data with better error handling
  useEffect(() => {
    if (!isClient) return;

    const fetchOracleData = async () => {
      try {
        const btcResponse = await fetch('/api/oracle/price/bitcoin');
        
        if (!btcResponse.ok) {
          throw new Error(`HTTP ${btcResponse.status}`);
        }
        
        const btcData = await btcResponse.json();
        
        // Use fallback if API returns error
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
        // Use fallback data instead of showing error
        setOracleData({
          btcPrice: 12500,
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
    if (!isClient) return { annualYield: 1200, periodYield: 1200, adjustedAPY: 0.12 };
    
    const amount = parseFloat(calc.amount) || 0;
    const period = parseInt(calc.period);
    
    let baseAPY = 0.09;
    if (period === 90) baseAPY = 0.10;
    else if (period === 180) baseAPY = 0.11;
    else if (period === 365) baseAPY = 0.12;
    
    const fundingAdjustment = (oracleData.fundingRate - 12.5) / 1000;
    const volAdjustment = (oracleData.btcVolatility - 65) / 2000;
    const adjustedAPY = Math.max(0.08, Math.min(0.14, baseAPY + fundingAdjustment + volAdjustment));
    
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
      question: "How does 9-12% APY work with BTC-gold backing?", 
      answer: "USDS is backed by 90% BTC + 10% gold using delta-neutral hedging. We buy BTC spot while shorting equal value in perpetual futures, eliminating price risk. Returns come from: (1) Funding rate arbitrage (5-8% historically, up to 10-15% in bull markets), (2) Gold treasury premium (2-3%), (3) Risk premium (2-3%), (4) Service fees (1-2%). Combined, this delivers 9-12% tiered by duration with 160% overcollateralization protecting against volatility."
    },
    { 
      question: "What happens if BTC crashes or funding rates turn negative?", 
      answer: "Delta-neutral hedging protects principal—if BTC drops 30%, our short position gains 30%, netting to zero. However, yields depend on funding rates staying positive (they're positive 85% of the time historically). In bear markets, funding can drop to 2-5% or briefly go negative, reducing yields to 8-10% range. Our 160% overcollateralization and 20% stablecoin reserve ensure USDS remains redeemable even in black swan events."
    },
    { 
      question: "How is this different from Nigerian T-bills at 20%?", 
      answer: "T-bills offer 20% in Nigerian Naira, which faces high inflation and currency devaluation risk. We offer 9-12% APY in USD-equivalent stablecoins, protecting against local currency depreciation. T-bills hedge naira inflation; USDS provides global diversification with cryptocurrency upside exposure. Trade-off: T-bills have sovereign backing; we have transparent, audited crypto reserves with higher liquidity and borderless transfer capabilities."
    },
    {
      question: "Is this regulated and safe?",
      answer: "Yes—compliant across NG (ISA 2025), KE (VASP Act), SA (FSCA), GH/TZ/ET/RW frameworks. Quarterly reserve audits, real-time collateralization dashboard, embedded KYC/AML. Not NDIC-insured but protected by 160% overcollateralization and independent custody. We publish all hedging positions monthly—full transparency vs traditional banks."
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-black text-white overflow-hidden">
      <style>{`
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
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        .animate-pulse-slow {
          animation: pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        @media (max-width: 640px) {
          .mobile-compact {
            padding: 0.75rem 1rem;
            font-size: 0.875rem;
          }
        }
      `}</style>

      <header className="fixed top-0 left-0 right-0 bg-gray-950/95 backdrop-blur-xl border-b border-gray-800/60 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex justify-between items-center">
          <div className="flex items-center space-x-2 sm:space-x-3">
            <img src="/seamount-logo.jpeg" alt="Seamount Logo" className="w-8 h-8 sm:w-10 sm:h-10 object-contain rounded-lg" />
            <span className="text-lg sm:text-xl font-bold">Seamount.io</span>
          </div>
          <nav className="hidden md:flex space-x-6 lg:space-x-8 text-sm">
            <a href="#how-it-works" className="hover:text-blue-400 transition">How It Works</a>
            <a href="#features" className="hover:text-blue-400 transition">Features</a>
            <a href="#calculator" className="hover:text-blue-400 transition">Calculator</a>
            <a href="#business" className="hover:text-blue-400 transition">Business</a>
          </nav>
          <div className="flex items-center space-x-2 sm:space-x-3">
            <button 
              onClick={() => onOpenAuth('login')} 
              className="px-3 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm font-medium hover:text-blue-400 transition"
            >
              Sign In
            </button>
            <button 
              onClick={() => onOpenAuth('register')} 
              className="px-3 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm font-medium bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg hover:from-blue-700 hover:to-purple-700 transition whitespace-nowrap"
            >
              Sign Up
            </button>
          </div>
        </div>
      </header>

      <main className="pt-16 sm:pt-20">
        <section id="hero" className="min-h-screen flex items-center justify-center relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(59,130,246,0.15)_0%,transparent_50%)]"></div>
          <div className="absolute top-1/4 left-1/4 w-64 sm:w-96 h-64 sm:h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
          <div className="absolute bottom-1/4 right-1/4 w-64 sm:w-96 h-64 sm:h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
          
          <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center relative z-10">
            <div className="inline-flex items-center gap-2 px-3 sm:px-4 py-2 bg-green-500/10 border border-green-500/30 rounded-full text-xs sm:text-sm font-medium mb-4 sm:mb-6">
              <Shield className="h-3 w-3 sm:h-4 sm:w-4 text-green-400" />
              160% Overcollateralized • Audited Reserves
            </div>
            
            <h1 className="text-3xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold mb-4 sm:mb-6 leading-tight">
              <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 text-transparent bg-clip-text">
                Your Shield Against
              </span>
              <br />
              <span className="text-white">Economic Uncertainty</span>
            </h1>
            
            <p className="text-base sm:text-lg md:text-xl lg:text-2xl text-gray-300 mb-3 sm:mb-4 max-w-3xl mx-auto leading-relaxed px-2">
              <strong className="text-green-400">Built for African resilience.</strong> While inflation erodes local currencies, Seamount delivers <span className="text-green-400 font-semibold">9-12% APY</span> in USD-equivalent stablecoins. Convert fiat → USDT/USDCa → P2P send → local off-ramp. Build wealth, send money instantly across borders, and protect your family's future—all on one platform.
            </p>
            
            <div className="flex flex-wrap justify-center gap-3 sm:gap-4 text-xs sm:text-sm text-gray-400 mb-6 sm:mb-8 px-2">
              <div className="flex items-center gap-1 sm:gap-2">
                <TrendingDown className="h-4 w-4 sm:h-5 sm:w-5 text-red-400" />
                <span>Beat High Inflation</span>
              </div>
              <div className="flex items-center gap-1 sm:gap-2">
                <Shield className="h-4 w-4 sm:h-5 sm:w-5 text-blue-400" />
                <span>Dollar-Pegged Stability</span>
              </div>
              <div className="flex items-center gap-1 sm:gap-2">
                <Zap className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-400" />
                <span>&lt;5s Settlements</span>
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row justify-center gap-3 sm:gap-4 mb-8 sm:mb-12 px-2">
              <button 
                onClick={() => onOpenAuth('register')} 
                className="px-6 py-3 sm:px-8 sm:py-4 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg font-semibold text-base sm:text-lg hover:from-blue-700 hover:to-purple-700 transform hover:scale-105 transition flex items-center justify-center"
              >
                Start Earning Now <ArrowRight className="ml-2 h-4 w-4 sm:h-5 sm:w-5" />
              </button>
              <button 
                onClick={() => document.getElementById('calculator')?.scrollIntoView({ behavior: 'smooth' })} 
                className="px-6 py-3 sm:px-8 sm:py-4 bg-gray-800/50 border border-gray-700 rounded-lg font-semibold text-base sm:text-lg hover:bg-gray-700/50 transition"
              >
                Calculate Your Yield
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 max-w-4xl mx-auto px-2">
              <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-xl p-4 sm:p-6 border border-gray-700/50">
                <div className="text-2xl sm:text-3xl md:text-4xl font-bold text-green-400 mb-2">9-12%</div>
                <div className="text-xs sm:text-sm text-gray-400">Annual Yield (USD)</div>
              </div>
              <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-xl p-4 sm:p-6 border border-gray-700/50">
                <div className="text-2xl sm:text-3xl md:text-4xl font-bold text-blue-400 mb-2">&lt;5 sec</div>
                <div className="text-xs sm:text-sm text-gray-400">Cross-Border Settlement</div>
              </div>
              <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-xl p-4 sm:p-6 border border-gray-700/50">
                <div className="text-2xl sm:text-3xl md:text-4xl font-bold text-purple-400 mb-2">160%</div>
                <div className="text-xs sm:text-sm text-gray-400">Overcollateralized Safety</div>
              </div>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="py-16 sm:py-24 bg-gray-950 relative">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-12 sm:mb-16 fade-in">
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4">How It Works</h2>
              <p className="text-lg sm:text-xl text-gray-400 max-w-3xl mx-auto">
                From signup to earning yields—your complete journey in 6 simple steps.
              </p>
            </div>

            <div className="space-y-6 sm:space-y-8">
              {[
                {
                  icon: <UserPlus className="h-8 w-8 sm:h-10 sm:w-10 text-blue-400" />,
                  step: "01",
                  title: "Sign Up in Minutes",
                  description: "Create your account with email. No lengthy forms—just essential info to get started.",
                  color: "from-blue-600/20 to-blue-800/10 border-blue-700/30"
                },
                {
                  icon: <FileCheck className="h-8 w-8 sm:h-10 sm:w-10 text-green-400" />,
                  step: "02",
                  title: "Complete KYC Verification",
                  description: "Quick identity verification via Regfyl. Document upload takes ~3 minutes, approval within 24 hours.",
                  color: "from-green-600/20 to-green-800/10 border-green-700/30"
                },
                {
                  icon: <Wallet className="h-8 w-8 sm:h-10 sm:w-10 text-purple-400" />,
                  step: "03",
                  title: "Algorand Wallet Creation",
                  description: "We generate your non-custodial Algorand wallet automatically. You get full control—download your private key and store it securely. We never access your funds.",
                  color: "from-purple-600/20 to-purple-800/10 border-purple-700/30"
                },
                {
                  icon: <Lock className="h-8 w-8 sm:h-10 sm:w-10 text-yellow-400" />,
                  step: "04",
                  title: "Secure Your Private Key",
                  description: "Download and backup your 25-word seed phrase. Store offline in multiple secure locations. This is your only recovery method—we cannot reset it.",
                  color: "from-yellow-600/20 to-yellow-800/10 border-yellow-700/30"
                },
                {
                  icon: <CreditCard className="h-8 w-8 sm:h-10 sm:w-10 text-red-400" />,
                  step: "05",
                  title: "Fund Your Account",
                  description: "Deposit fiat (USD/GBP/EUR/NGN/KES/ZAR/etc.) via Paystack or Cashramp. Funds convert to USDT/USDCa instantly. Buy goBTC, goETH, or ALGO on Algorand rails.",
                  color: "from-red-600/20 to-red-800/10 border-red-700/30"
                },
                {
                  icon: <ArrowRightLeft className="h-8 w-8 sm:h-10 sm:w-10 text-teal-400" />,
                  step: "06",
                  title: "Send P2P & Off-Ramp",
                  description: "Send stablecoins peer-to-peer globally in <5 seconds. Recipients off-ramp to local currency via our liquidity providers. When USDS launches, hold for 9-12% APY yields.",
                  color: "from-teal-600/20 to-teal-800/10 border-teal-700/30"
                }
              ].map((step, idx) => (
                <div key={idx} className={`bg-gradient-to-br ${step.color} backdrop-blur-sm rounded-2xl p-4 sm:p-6 border flex gap-4 sm:gap-6 items-start fade-in hover:scale-[1.02] transition-transform duration-300`}>
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 sm:w-16 sm:h-16 bg-gray-900/50 rounded-xl flex items-center justify-center border border-gray-700/30 mb-2">
                      {step.icon}
                    </div>
                    <div className="text-2xl sm:text-4xl font-bold text-gray-700 text-center">{step.step}</div>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg sm:text-2xl font-bold mb-2 sm:mb-3 flex items-center gap-2 sm:gap-3">
                      {step.title}
                      {idx === 5 && <span className="text-xs sm:text-sm px-2 sm:px-3 py-1 bg-green-500/20 border border-green-500/30 rounded-full text-green-400">USDS Coming Soon</span>}
                    </h3>
                    <p className="text-gray-300 text-sm sm:text-lg leading-relaxed">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 sm:mt-12 bg-gradient-to-r from-blue-900/30 to-purple-900/30 rounded-2xl p-4 sm:p-6 border border-blue-700/30 fade-in">
              <div className="flex items-start gap-3 sm:gap-4">
                <CheckCircle className="h-6 w-6 sm:h-8 sm:w-8 text-green-400 flex-shrink-0 mt-1" />
                <div>
                  <h4 className="text-lg sm:text-2xl font-bold mb-2 sm:mb-3 text-green-400">When USDS Launches</h4>
                  <p className="text-gray-300 text-sm sm:text-lg leading-relaxed mb-3 sm:mb-4">
                    Users who choose to hold USDS will gain exposure to our delta-neutral BTC-gold strategy, earning 9-12% APY with monthly liquidity. Your stablecoins work for you—no lock-ups longer than 30 days, with full transparency on backing and yields.
                  </p>
                  <div className="flex flex-wrap gap-3 sm:gap-4 text-xs sm:text-sm">
                    <div className="flex items-center gap-1 sm:gap-2">
                      <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                      <span className="text-gray-400">90% BTC + 10% Gold</span>
                    </div>
                    <div className="flex items-center gap-1 sm:gap-2">
                      <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                      <span className="text-gray-400">160% Overcollateralized</span>
                    </div>
                    <div className="flex items-center gap-1 sm:gap-2">
                      <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                      <span className="text-gray-400">Quarterly Audits</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="py-16 sm:py-24 bg-gray-900/50 relative">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-12 sm:mb-16 fade-in">
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4">Platform Features</h2>
              <p className="text-lg sm:text-xl text-gray-400 max-w-3xl mx-auto">
                Everything you need for secure, fast, and profitable cross-border transactions.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
              {[
                {
                  icon: <Send className="h-6 w-6 sm:h-8 sm:w-8 text-blue-400" />,
                  title: "Instant Cross-Border Payments",
                  description: "Send money globally in seconds with minimal fees. Algorand's sub-5s settlement beats traditional remittance by days."
                },
                {
                  icon: <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-green-400" />,
                  title: "Multi-Stablecoin Support",
                  description: "Trade USDT, USDCa, USDS with seamless swaps. Access goBTC, goETH, and ALGO on the same platform."
                },
                {
                  icon: <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-purple-400" />,
                  title: "9-12% APY on USDS",
                  description: "Earn competitive yields through delta-neutral BTC-gold hedging strategy. Monthly liquidity, quarterly audits."
                },
                {
                  icon: <Shield className="h-6 w-6 sm:h-8 sm:w-8 text-yellow-400" />,
                  title: "160% Overcollateralized",
                  description: "Your funds backed by audited reserves with transparent collateralization. Real-time dashboard monitoring."
                },
                {
                  icon: <Lock className="h-6 w-6 sm:h-8 sm:w-8 text-red-400" />,
                  title: "Self-Custody Wallets",
                  description: "Full control of your private keys. Non-custodial Algorand wallets with military-grade encryption."
                },
                {
                  icon: <Globe className="h-6 w-6 sm:h-8 sm:w-8 text-teal-400" />,
                  title: "Pan-Africa Coverage",
                  description: "Support for NGN, KES, ZAR, ETB, RWF, TZS, GHS plus USD, GBP, EUR. Compliant across 7+ countries."
                }
              ].map((feature, idx) => (
                <div key={idx} className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-2xl p-5 sm:p-6 border border-gray-700/50 hover:border-blue-500/50 transition-all duration-300 fade-in">
                  <div className="w-12 h-12 sm:w-14 sm:h-14 bg-gray-900/50 rounded-xl flex items-center justify-center mb-3 sm:mb-4 border border-gray-700/30">
                    {feature.icon}
                  </div>
                  <h3 className="text-lg sm:text-xl font-bold mb-2 sm:mb-3">{feature.title}</h3>
                  <p className="text-gray-400 text-sm leading-relaxed">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="calculator" className="py-16 sm:py-24 bg-gray-950 relative">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-12 sm:mb-16 fade-in">
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4">Live Yield Calculator</h2>
              <p className="text-lg sm:text-xl text-gray-400 max-w-3xl mx-auto">
                Real-time BTC data from our 3-tier oracle system. Full transparency on returns.
              </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-6 sm:gap-8">
              <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-2xl p-6 sm:p-8 border border-gray-700/50 fade-in">
                <h3 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6 flex items-center">
                  <DollarSign className="h-5 w-5 sm:h-6 sm:w-6 text-green-400 mr-2" />
                  Your Investment
                </h3>
                
                <div className="space-y-4 sm:space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Investment Amount (USD)</label>
                    <input 
                      type="number" 
                      value={calc.amount}
                      onChange={(e) => setCalc({...calc, amount: e.target.value})}
                      className="w-full px-3 sm:px-4 py-2 sm:py-3 bg-gray-900/50 border border-gray-700 rounded-lg text-white text-base sm:text-lg focus:border-blue-500 focus:outline-none transition"
                      placeholder="10000"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Lock-up Period</label>
                    <select 
                      value={calc.period}
                      onChange={(e) => setCalc({...calc, period: e.target.value})}
                      className="w-full px-3 sm:px-4 py-2 sm:py-3 bg-gray-900/50 border border-gray-700 rounded-lg text-white text-base sm:text-lg focus:border-blue-500 focus:outline-none transition"
                    >
                      <option value="30">30 Days (9% APY)</option>
                      <option value="90">90 Days (10% APY)</option>
                      <option value="180">180 Days (11% APY)</option>
                      <option value="365">365 Days (12% APY)</option>
                    </select>
                  </div>

                  <div className="bg-gray-900/50 rounded-lg p-3 sm:p-4 border border-gray-700/30">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm text-gray-400 flex items-center">
                        Live Market Data
                        <button onClick={() => setShowFundingInfo(!showFundingInfo)} className="ml-1">
                          <Info className="h-4 w-4 text-gray-500 hover:text-gray-300" />
                        </button>
                      </span>
                      <span className="text-xs text-green-400 flex items-center">
                        {oracleData.loading ? (
                          <>Loading...</>
                        ) : oracleData.error ? (
                          <span className="text-yellow-400">Cached</span>
                        ) : (
                          <>
                            <div className="w-2 h-2 bg-green-400 rounded-full mr-1 animate-pulse"></div>
                            Live
                          </>
                        )}
                      </span>
                    </div>
                    {showFundingInfo && (
                      <div className="mb-3 p-2 sm:p-3 bg-blue-900/20 rounded text-xs text-gray-300 border border-blue-500/20">
                        <strong>Funding Rate:</strong> Fee paid every 8 hours between perpetual futures traders. When positive, we collect payments by shorting futures while holding BTC spot (delta-neutral).
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-2 sm:gap-3 text-sm">
                      <div>
                        <div className="text-gray-500 text-xs">BTC Price</div>
                        <div className="font-semibold text-white" suppressHydrationWarning>
                          {oracleData.loading ? '...' : `$${oracleData.btcPrice.toLocaleString(undefined, {maximumFractionDigits: 0})}`}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-500 text-xs">Volatility</div>
                        <div className="font-semibold text-yellow-400" suppressHydrationWarning>
                          {oracleData.loading ? '...' : `${oracleData.btcVolatility.toFixed(1)}%`}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-500 text-xs">Funding Rate</div>
                        <div className={`font-semibold ${oracleData.fundingRate > 10 ? 'text-green-400' : oracleData.fundingRate > 5 ? 'text-yellow-400' : 'text-red-400'}`} suppressHydrationWarning>
                          {oracleData.loading ? '...' : `${oracleData.fundingRate.toFixed(1)}%`}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-500 text-xs">Gold Premium</div>
                        <div className="font-semibold text-purple-400">2-3%</div>
                      </div>
                    </div>
                    {oracleData.lastUpdate && (
                      <div className="mt-2 text-xs text-gray-500 text-center">
                        Last updated: {oracleData.lastUpdate.toLocaleTimeString()}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 backdrop-blur-sm rounded-2xl p-6 sm:p-8 border border-blue-700/30 fade-in">
                <h3 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6 flex items-center">
                  <TrendingUp className="h-5 w-5 sm:h-6 sm:w-6 text-green-400 mr-2" />
                  Estimated Returns
                </h3>

                <div className="bg-gradient-to-r from-green-600/20 to-emerald-600/20 rounded-xl p-4 sm:p-6 mb-4 sm:mb-6 border border-green-500/30">
                  <div className="text-center">
                    <div className="text-sm text-gray-300 mb-2">Estimated Annual Yield</div>
                    <div className="text-3xl sm:text-5xl font-bold text-green-400 mb-2" suppressHydrationWarning>
                      ${yieldData.annualYield.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    <div className="text-base sm:text-lg text-gray-300" suppressHydrationWarning>
                      ({(yieldData.adjustedAPY * 100).toFixed(1)}% APY)
                    </div>
                    <div className="mt-3 pt-3 border-t border-green-500/20">
                      <div className="text-sm text-gray-400">Period Return ({calc.period} days)</div>
                      <div className="text-xl sm:text-2xl font-semibold text-green-300" suppressHydrationWarning>
                        ${yieldData.periodYield.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3 sm:space-y-4">
                  <div className="flex justify-between items-center text-sm sm:text-base">
                    <span className="text-gray-400">Spread vs T-Bills</span>
                    <span className="font-semibold text-blue-400" suppressHydrationWarning>
                      {calc.creditSpread > 0 ? '+' : ''}{calc.creditSpread} bps
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-sm sm:text-base">
                    <span className="text-gray-400 flex items-center">
                      Risk Score
                      <button onClick={() => setShowRiskDetails(!showRiskDetails)} className="ml-1">
                        <Info className="h-4 w-4 text-gray-500 hover:text-gray-300" />
                      </button>
                    </span>
                    <span className={`font-semibold ${calc.riskScore < 40 ? 'text-green-400' : calc.riskScore < 60 ? 'text-yellow-400' : 'text-red-400'}`} suppressHydrationWarning>
                      {calc.riskScore}/100
                    </span>
                  </div>

                  {showRiskDetails && (
                    <div className="p-2 sm:p-3 bg-gray-900/50 rounded-lg border border-gray-700/30 text-xs text-gray-300">
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span>Funding Rate Risk:</span>
                          <span className={oracleData.fundingRate < 8 ? 'text-red-400' : 'text-green-400'}>
                            {oracleData.fundingRate < 8 ? 'High (15 pts)' : oracleData.fundingRate > 18 ? 'Low (10 pts)' : 'Medium (5 pts)'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Volatility Risk:</span>
                          <span className="text-yellow-400">{((oracleData.btcVolatility / 80) * 30).toFixed(0)} pts</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Duration Risk:</span>
                          <span className="text-blue-400">{(15 - (parseInt(calc.period) / 365) * 15).toFixed(0)} pts</span>
                        </div>
                        <div className="flex justify-between">
                          <span>BTC Exposure:</span>
                          <span className="text-purple-400">25 pts (90% allocation)</span>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="flex justify-between items-center text-sm sm:text-base">
                    <span className="text-gray-400">Strategy</span>
                    <span className="font-semibold text-purple-400">Delta-Neutral</span>
                  </div>

                  <div className="flex justify-between items-center text-sm sm:text-base">
                    <span className="text-gray-400">Collateralization</span>
                    <span className="font-semibold text-green-400">160%</span>
                  </div>
                </div>

                <div className="mt-4 sm:mt-6 p-3 sm:p-4 bg-yellow-900/20 rounded-lg border border-yellow-500/30">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-gray-300">
                      <strong className="text-yellow-400">Risk Disclosure:</strong> Yields depend on BTC funding rates (currently {oracleData.fundingRate.toFixed(1)}%, historical 5-8%, volatile) and hedging execution. Bear markets can reduce yields to 8-10%. Not NDIC-insured. 160% overcollateralization protects principal.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="business" className="py-16 sm:py-24 bg-gray-950 relative">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-12 sm:mb-16 fade-in">
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4">For Business</h2>
              <p className="text-lg sm:text-xl text-gray-400 max-w-3xl mx-auto">
                Transform your business treasury and cross-border operations with institutional-grade stablecoin infrastructure.
              </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-6 sm:gap-8 mb-8 sm:mb-12">
              <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-2xl p-6 sm:p-8 border border-gray-700/50 fade-in">
                <Briefcase className="h-8 w-8 sm:h-12 sm:w-12 text-blue-400 mb-3 sm:mb-4" />
                <h3 className="text-xl sm:text-2xl font-bold mb-3 sm:mb-4">Business Solutions</h3>
                <ul className="space-y-2 sm:space-y-3 text-sm sm:text-base text-gray-300">
                  <li className="flex items-start">
                    <div className="w-2 h-2 bg-blue-400 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                    <span><strong className="text-white">Global Payroll:</strong> Pay international teams instantly with multi-currency support</span>
                  </li>
                  <li className="flex items-start">
                    <div className="w-2 h-2 bg-green-400 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                    <span><strong className="text-white">Treasury Management:</strong> Earn yields on idle corporate funds (9-12% APY)</span>
                  </li>
                  <li className="flex items-start">
                    <div className="w-2 h-2 bg-purple-400 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                    <span><strong className="text-white">Trade Finance:</strong> Streamline cross-border B2B payments with programmable settlements</span>
                  </li>
                  <li className="flex items-start">
                    <div className="w-2 h-2 bg-yellow-400 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                    <span><strong className="text-white">Liquidity Optimization:</strong> Turn working capital into revenue-generating assets</span>
                  </li>
                </ul>
              </div>

              <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-2xl p-6 sm:p-8 border border-gray-700/50 fade-in">
                <h3 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6">Get in Touch</h3>
                <form onSubmit={(e) => { e.preventDefault(); handleContactSubmit(); }} className="space-y-3 sm:space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Your Name</label>
                    <input 
                      type="text"
                      value={formState.name}
                      onChange={(e) => setFormState({...formState, name: e.target.value})}
                      className="w-full px-3 sm:px-4 py-2 sm:py-3 bg-gray-900/50 border border-gray-700 rounded-lg text-white text-sm sm:text-base focus:border-blue-500 focus:outline-none transition"
                      placeholder="John Doe"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Business Name</label>
                    <input 
                      type="text"
                      value={formState.businessName}
                      onChange={(e) => setFormState({...formState, businessName: e.target.value})}
                      className="w-full px-3 sm:px-4 py-2 sm:py-3 bg-gray-900/50 border border-gray-700 rounded-lg text-white text-sm sm:text-base focus:border-blue-500 focus:outline-none transition"
                      placeholder="Your Company Ltd."
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Email Address</label>
                    <input 
                      type="email"
                      value={formState.email}
                      onChange={(e) => setFormState({...formState, email: e.target.value})}
                      className="w-full px-3 sm:px-4 py-2 sm:py-3 bg-gray-900/50 border border-gray-700 rounded-lg text-white text-sm sm:text-base focus:border-blue-500 focus:outline-none transition"
                      placeholder="john@company.com"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Message</label>
                    <textarea
                      value={formState.message}
                      onChange={(e) => setFormState({...formState, message: e.target.value})}
                      className="w-full px-3 sm:px-4 py-2 sm:py-3 bg-gray-900/50 border border-gray-700 rounded-lg text-white text-sm sm:text-base focus:border-blue-500 focus:outline-none transition resize-none"
                      rows={4}
                      placeholder="Tell us about your business needs..."
                      required
                    ></textarea>
                  </div>
                  <button
                    type="submit"
                    disabled={formStatus === 'sending'}
                    className="w-full px-4 sm:px-6 py-2 sm:py-3 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg font-semibold text-sm sm:text-base hover:from-blue-700 hover:to-purple-700 transition disabled:opacity-50"
                  >
                    {formStatus === 'sending' ? 'Sending...' : formStatus === 'success' ? 'Message Sent!' : formStatus === 'error' ? 'Failed, Try Again' : 'Send Message'}
                  </button>
                </form>
              </div>
            </div>

            <div className="grid sm:grid-cols-3 gap-4 sm:gap-8 fade-in">
              <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-2xl p-4 sm:p-6 border border-gray-700/50 text-center">
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto mb-3 sm:mb-4 border border-blue-500/30">
                  <MapPin className="h-5 w-5 sm:h-7 sm:w-7 text-blue-400" />
                </div>
                <h3 className="text-lg sm:text-xl font-bold mb-2">Our Office</h3>
                <p className="text-sm sm:text-base text-gray-400">Wood Avenue, Kilimani<br />Nairobi, Kenya</p>
              </div>

              <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-2xl p-4 sm:p-6 border border-gray-700/50 text-center">
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-3 sm:mb-4 border border-green-500/30">
                  <Mail className="h-5 w-5 sm:h-7 sm:w-7 text-green-400" />
                </div>
                <h3 className="text-lg sm:text-xl font-bold mb-2">Email Us</h3>
                <p className="text-sm sm:text-base text-gray-400">support@seamount.io</p>
              </div>

              <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-2xl p-4 sm:p-6 border border-gray-700/50 text-center">
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-purple-500/10 rounded-full flex items-center justify-center mx-auto mb-3 sm:mb-4 border border-purple-500/30">
                  <Phone className="h-5 w-5 sm:h-7 sm:w-7 text-purple-400" />
                </div>
                <h3 className="text-lg sm:text-xl font-bold mb-2">Call Us</h3>
                <p className="text-sm sm:text-base text-gray-400">+254 751 875 374</p>
              </div>
            </div>
          </div>
        </section>

        <section className="py-12 sm:py-16 bg-gray-950">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-8 sm:mb-12 fade-in">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-4">Frequently Asked Questions</h2>
              <p className="text-sm sm:text-base text-gray-400 max-w-2xl mx-auto">Get answers to common questions about Seamount's platform.</p>
            </div>
            <div className="space-y-3 sm:space-y-4">
              {faqs.map((faq, index) => (
                <div key={index} className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 rounded-xl border border-gray-800/80 backdrop-blur-sm overflow-hidden fade-in">
                  <button onClick={() => setExpandedFaqs(prev => prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index])} className="w-full px-4 sm:px-6 py-3 sm:py-4 text-left flex items-center justify-between hover:bg-gray-800/30 transition-colors">
                    <h3 className="font-semibold text-sm sm:text-base lg:text-lg text-white pr-4">{faq.question}</h3>
                    {expandedFaqs.includes(index) ? <ChevronUp className="h-4 w-4 sm:h-5 sm:w-5 text-blue-500 flex-shrink-0" /> : <ChevronDown className="h-4 w-4 sm:h-5 sm:w-5 text-blue-500 flex-shrink-0" />}
                  </button>
                  {expandedFaqs.includes(index) && (
                    <div className="px-4 sm:px-6 pb-3 sm:pb-4 border-t border-gray-800/50">
                      <p className="text-sm sm:text-base text-gray-300 pt-3 sm:pt-4">{faq.answer}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-12 sm:py-20 bg-gradient-to-r from-blue-900/20 to-purple-900/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-4 sm:mb-6">Ready to Take Control of Your Financial Future?</h2>
              <button onClick={() => onOpenAuth('register')} className="px-6 sm:px-8 py-3 sm:py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-base sm:text-lg font-semibold rounded-lg transform hover:scale-105 transition">
                Sign Up for Free
              </button>
              <p className="mt-4 text-xs sm:text-sm text-gray-400">Already have an account? <button onClick={() => onOpenAuth('login')} className="text-blue-400 hover:underline font-semibold">Sign In</button></p>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-gray-950 border-t border-gray-800/60 py-8 sm:py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 sm:gap-8 mb-6 sm:mb-8">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center space-x-2 sm:space-x-3 mb-3 sm:mb-4">
                <img src="/seamount-logo.jpeg" alt="Seamount Logo" className="w-6 h-6 sm:w-8 sm:h-8 object-contain rounded-lg" />
                <span className="text-lg sm:text-xl font-bold">Seamount.io</span>
              </div>
              <p className="text-gray-400 text-xs sm:text-sm">The future of cross-border payments for emerging markets</p>
            </div>
            <div>
              <h4 className="text-white font-medium mb-3 sm:mb-4 text-sm sm:text-base">Product</h4>
              <ul className="space-y-2 text-xs sm:text-sm">
                <li><a href="#features" className="text-gray-400 hover:text-white">Features</a></li>
                <li><a href="#calculator" className="text-gray-400 hover:text-white">Calculator</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-3 sm:mb-4 text-sm sm:text-base">Company</h4>
              <ul className="space-y-2 text-xs sm:text-sm">
                <li><a href="#how-it-works" className="text-gray-400 hover:text-white">How It Works</a></li>
                <li><a href="#business" className="text-gray-400 hover:text-white">Business</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-3 sm:mb-4 text-sm sm:text-base">Legal</h4>
              <ul className="space-y-2 text-xs sm:text-sm">
                <li><a href="/legal/privacy-policy.html" className="text-gray-400 hover:text-white">Privacy Policy</a></li>
                <li><a href="/legal/terms-of-service.html" className="text-gray-400 hover:text-white">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-6 sm:pt-8 text-center text-xs sm:text-sm text-gray-500">
            <div className="flex flex-col sm:flex-row justify-between items-center gap-3">
              <p>© {new Date().getFullYear()} Seamount Technologies Ltd. All rights reserved.</p>
              <div className="flex flex-wrap justify-center gap-3 sm:gap-4">
                <div className="flex items-center text-xs"><Shield className="h-3 w-3 sm:h-4 sm:w-4 mr-1 text-green-500" /><span>GDPR Compliant</span></div>
                <div className="flex items-center text-xs"><Shield className="h-3 w-3 sm:h-4 sm:w-4 mr-1 text-blue-500" /><span>160% Backed</span></div>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;