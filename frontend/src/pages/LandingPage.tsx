import React, { useState, useEffect, useCallback } from 'react';
import { ArrowRight, Globe, Shield, Zap, DollarSign, Users, Briefcase, Send, Mail, MapPin, Phone, ChevronDown, ChevronUp, TrendingUp, AlertTriangle, Info, Eye, Lock } from 'lucide-react';
import React, { useState, useEffect, useMemo } from 'react';

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
  
  const [calc, setCalc] = useState({
    amount: '10000',
    period: '365',
    btcPrice: 95000,
    btcVolatility: 65,
    fundingRate: 12.5,
    estimatedYield: 0.22,
    creditSpread: 200,
    riskScore: 35
  });

  // Client-side only initialization
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Move live data updates to client-side only
  useEffect(() => {
    if (!isClient) return;

    const interval = setInterval(() => {
      setCalc(prev => ({
        ...prev,
        btcPrice: prev.btcPrice + (Math.random() - 0.5) * 500,
        btcVolatility: Math.max(50, Math.min(80, prev.btcVolatility + (Math.random() - 0.5) * 1.5)),
        fundingRate: Math.max(5, Math.min(20, prev.fundingRate + (Math.random() - 0.5) * 1))
      }));
    }, 5000);
    return () => clearInterval(interval);
  }, [isClient]);

  const yieldData = useMemo(() => {
  if (!isClient) return { annualYield: 2200, periodYield: 2200, adjustedAPY: 0.22 };
  
  const amount = parseFloat(calc.amount) || 0;
  const period = parseInt(calc.period);
  
  let baseAPY = 0.18;
  if (period === 90) baseAPY = 0.20;
  else if (period === 180) baseAPY = 0.21;
  else if (period === 365) baseAPY = 0.22;
  
  const fundingAdjustment = (calc.fundingRate - 12.5) / 500;
  const volAdjustment = (calc.btcVolatility - 65) / 1000;
  const adjustedAPY = Math.max(0.16, Math.min(0.24, baseAPY + fundingAdjustment + volAdjustment));
  
  const annualYield = amount * adjustedAPY;
  const periodYield = annualYield * (period / 365);
  
  return { annualYield, periodYield, adjustedAPY };
}, [isClient, calc.amount, calc.period, calc.btcVolatility, calc.fundingRate]);

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
      question: "How does 18-22% APY work with BTC-gold backing?", 
      answer: "USDS is backed by 90% BTC + 10% gold using delta-neutral hedging. We buy BTC spot while shorting equal value in perpetual futures, eliminating price risk. Returns come from: (1) Funding rate arbitrage (10-15% historically), (2) Gold treasury premium (5%), (3) Service and risk premiums. Combined, this delivers 18-22% tiered by duration. 160% overcollateralization protects against volatility."
    },
    { 
      question: "What happens if BTC crashes or funding rates turn negative?", 
      answer: "Delta-neutral hedging protects principal—if BTC drops 30%, our short position gains 30%, netting to zero. However, yields depend on funding rates staying positive (they're positive 85% of the time historically). In bear markets, funding can drop to 2-5% or briefly go negative, reducing yields to 16-18% range. Our 160% overcollateralization and 20% stablecoin reserve ensure USDS remains redeemable even in black swan events."
    },
    { 
      question: "How is this different from Nigerian T-bills at 20%?", 
      answer: "T-bills lock funds for 3-12 months with government backing. We offer comparable yields (18-22%) with 1-month liquidity and cryptocurrency diversification. T-bills hedge naira inflation; USDS hedges via dollar peg + BTC/gold appreciation. Trade-off: T-bills have sovereign backing; we have transparent, audited crypto reserves with higher execution risk but better liquidity."
    },
    {
      question: "Is this regulated and safe?",
      answer: "Yes—compliant across NG (ISA 2025), KE (VASP Act), SA (FSCA), GH/TZ/ET/RW frameworks. Quarterly reserve audits, real-time collateralization dashboard, embedded KYC/AML. Not NDIC-insured but protected by 160% overcollateralization and independent custody. We publish all hedging positions monthly—full transparency vs traditional banks."
    }
  ];

  // Calculate yield only on client to avoid hydration mismatch
  const yieldData = isClient ? calculateAdvancedYield() : { 
    annualYield: 2200, 
    periodYield: 2200, 
    adjustedAPY: 0.22 
  };

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
      `}</style>

      <header className="fixed top-0 left-0 right-0 bg-gray-950/95 backdrop-blur-xl border-b border-gray-800/60 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center font-bold text-lg">S</div>
            <span className="text-xl font-bold">Seamount.io</span>
          </div>
          <nav className="hidden md:flex space-x-8 text-sm">
            <a href="#features" className="hover:text-blue-400 transition">Features</a>
            <a href="#calculator" className="hover:text-blue-400 transition">Calculator</a>
            <a href="#transparency" className="hover:text-blue-400 transition">Transparency</a>
            <a href="#contact" className="hover:text-blue-400 transition">Contact</a>
          </nav>
          <div className="flex items-center space-x-3">
            <button onClick={() => onOpenAuth('login')} className="px-4 py-2 text-sm font-medium hover:text-blue-400 transition">Sign In</button>
            <button onClick={() => onOpenAuth('register')} className="px-4 py-2 text-sm font-medium bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg hover:from-blue-700 hover:to-purple-700 transition">Get Started</button>
          </div>
        </div>
      </header>

      <main className="pt-20">
        <section className="min-h-screen flex items-center justify-center relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(59,130,246,0.15)_0%,transparent_50%)]"></div>
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
          
          <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center relative z-10">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-500/10 border border-green-500/30 rounded-full text-sm font-medium mb-6">
              <Shield className="h-4 w-4 text-green-400" />
              160% Overcollateralized • Audited Reserves
            </div>
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold mb-6 leading-tight">
              <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 text-transparent bg-clip-text">
                Earn 18-22% APY
              </span>
              <br />
              <span className="text-white">On Delta-Neutral BTC-Gold</span>
            </h1>
            <p className="text-xl md:text-2xl text-gray-300 mb-4 max-w-3xl mx-auto leading-relaxed">
              Pan-Africa cross-border platform. Fiat in → USDT/USDCa → P2P send → local off-ramp.
              <span className="text-green-400 font-semibold"> Conservative yields</span> from hedged BTC + gold backing.
            </p>
            <p className="text-sm text-gray-400 mb-8 max-w-2xl mx-auto">
              Yields depend on BTC funding rates (historical 10-15%, volatile) and hedging execution. Not guaranteed—past performance ≠ future returns.
            </p>
            
            <div className="flex flex-col sm:flex-row justify-center gap-4 mb-12">
              <button onClick={() => onOpenAuth('register')} className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg font-semibold text-lg hover:from-blue-700 hover:to-purple-700 transform hover:scale-105 transition flex items-center justify-center">
                Start Earning <ArrowRight className="ml-2 h-5 w-5" />
              </button>
              <button onClick={() => document.getElementById('calculator')?.scrollIntoView({ behavior: 'smooth' })} className="px-8 py-4 bg-gray-800/50 border border-gray-700 rounded-lg font-semibold text-lg hover:bg-gray-700/50 transition">
                See Live Calculator
              </button>
            </div>

            <div className="flex flex-wrap justify-center gap-6 text-sm text-gray-400">
              <div className="flex items-center gap-2">
                <Eye className="h-5 w-5 text-blue-400" />
                <span>Full Transparency</span>
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-green-400" />
                <span>90% BTC + 10% Gold</span>
              </div>
              <div className="flex items-center gap-2">
                <Globe className="h-5 w-5 text-purple-400" />
                <span>7+ African Markets</span>
              </div>
            </div>
          </div>
        </section>

        <section id="calculator" className="py-24 bg-gray-900/50 relative">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-16 fade-in">
              <h2 className="text-4xl md:text-5xl font-bold mb-4">Live Yield Calculator</h2>
              <p className="text-xl text-gray-400 max-w-3xl mx-auto">
                Real-time BTC data, funding rates, and risk scoring. Full transparency on how we generate returns.
              </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-8">
              <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-2xl p-8 border border-gray-700/50 fade-in">
                <h3 className="text-2xl font-bold mb-6 flex items-center">
                  <DollarSign className="h-6 w-6 text-green-400 mr-2" />
                  Your Investment
                </h3>
                
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Investment Amount (USD)</label>
                    <input 
                      type="number" 
                      value={calc.amount}
                      onChange={(e) => setCalc({...calc, amount: e.target.value})}
                      className="w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg text-white text-lg focus:border-blue-500 focus:outline-none transition"
                      placeholder="10000"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Lock-up Period</label>
                    <select 
                      value={calc.period}
                      onChange={(e) => setCalc({...calc, period: e.target.value})}
                      className="w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg text-white text-lg focus:border-blue-500 focus:outline-none transition"
                    >
                      <option value="30">30 Days (18% APY)</option>
                      <option value="90">90 Days (20% APY)</option>
                      <option value="180">180 Days (21% APY)</option>
                      <option value="365">365 Days (22% APY)</option>
                    </select>
                  </div>

                  <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700/30">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm text-gray-400 flex items-center">
                        Live Market Data
                        <button onClick={() => setShowFundingInfo(!showFundingInfo)} className="ml-1">
                          <Info className="h-4 w-4 text-gray-500 hover:text-gray-300" />
                        </button>
                      </span>
                      <span className="text-xs text-green-400 flex items-center">
                        <div className="w-2 h-2 bg-green-400 rounded-full mr-1 animate-pulse"></div>
                        Live
                      </span>
                    </div>
                    {showFundingInfo && (
                      <div className="mb-3 p-3 bg-blue-900/20 rounded text-xs text-gray-300 border border-blue-500/20">
                        <strong>Funding Rate:</strong> Fee paid every 8 hours between perpetual futures traders. When positive, we collect payments by shorting futures while holding BTC spot (delta-neutral). Historical range: 5-20% annually.
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <div className="text-gray-500 text-xs">BTC Price</div>
                        <div className="font-semibold text-white" suppressHydrationWarning>
                          ${calc.btcPrice.toLocaleString(undefined, {maximumFractionDigits: 0})}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-500 text-xs">Volatility</div>
                        <div className="font-semibold text-yellow-400" suppressHydrationWarning>
                          {calc.btcVolatility.toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-500 text-xs">Funding Rate</div>
                        <div className={`font-semibold ${calc.fundingRate > 10 ? 'text-green-400' : calc.fundingRate > 5 ? 'text-yellow-400' : 'text-red-400'}`} suppressHydrationWarning>
                          {calc.fundingRate.toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-500 text-xs">Gold Premium</div>
                        <div className="font-semibold text-purple-400">5%</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 backdrop-blur-sm rounded-2xl p-8 border border-blue-700/30 fade-in">
                <h3 className="text-2xl font-bold mb-6 flex items-center">
                  <TrendingUp className="h-6 w-6 text-green-400 mr-2" />
                  Estimated Returns
                </h3>

                <div className="bg-gradient-to-r from-green-600/20 to-emerald-600/20 rounded-xl p-6 mb-6 border border-green-500/30">
                  <div className="text-center">
                    <div className="text-sm text-gray-300 mb-2">Estimated Annual Yield</div>
                    <div className="text-5xl font-bold text-green-400 mb-2" suppressHydrationWarning>
                      ${yieldData.annualYield.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    <div className="text-lg text-gray-300" suppressHydrationWarning>
                      ({(yieldData.adjustedAPY * 100).toFixed(1)}% APY)
                    </div>
                    <div className="mt-3 pt-3 border-t border-green-500/20">
                      <div className="text-sm text-gray-400">Period Return ({calc.period} days)</div>
                      <div className="text-2xl font-semibold text-green-300" suppressHydrationWarning>
                        ${yieldData.periodYield.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400 text-sm">Spread vs T-Bills</span>
                    <span className="font-semibold text-blue-400" suppressHydrationWarning>
                      {calc.creditSpread > 0 ? '+' : ''}{calc.creditSpread} bps
                    </span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-gray-400 text-sm flex items-center">
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
                    <div className="p-3 bg-gray-900/50 rounded-lg border border-gray-700/30 text-xs text-gray-300">
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span>Funding Rate Risk:</span>
                          <span className={calc.fundingRate < 8 ? 'text-red-400' : 'text-green-400'}>
                            {calc.fundingRate < 8 ? 'High (15 pts)' : calc.fundingRate > 18 ? 'Low (10 pts)' : 'Medium (5 pts)'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Volatility Risk:</span>
                          <span className="text-yellow-400">{((calc.btcVolatility / 80) * 30).toFixed(0)} pts</span>
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

                  <div className="flex justify-between items-center">
                    <span className="text-gray-400 text-sm">Strategy</span>
                    <span className="font-semibold text-purple-400">Delta-Neutral</span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-gray-400 text-sm">Collateralization</span>
                    <span className="font-semibold text-green-400">160%</span>
                  </div>
                </div>

                <div className="mt-6 p-4 bg-yellow-900/20 rounded-lg border border-yellow-500/30">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-gray-300">
                      <strong className="text-yellow-400">Risk Disclosure:</strong> Yields depend on BTC funding rates (currently {calc.fundingRate.toFixed(1)}%, historical 10-15%, volatile) and hedging execution. Bear markets can reduce yields to 16-18%. Not NDIC-insured. 160% overcollateralization protects principal.
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-12 bg-gray-800/50 rounded-xl p-6 border border-gray-700/50 fade-in">
              <h4 className="text-xl font-bold mb-4">Performance Comparison</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left py-3 px-4 font-semibold text-gray-400">Product</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-400">Yield</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-400">Duration</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-400">Liquidity</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-400">Risk Profile</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-gray-700/50 bg-blue-900/20">
                      <td className="py-3 px-4 font-semibold text-blue-400">Seamount USDS</td>
                      <td className="text-right py-3 px-4 text-green-400 font-semibold">18-22%</td>
                      <td className="text-right py-3 px-4">1-12 months</td>
                      <td className="text-right py-3 px-4 text-green-400">Monthly</td>
                      <td className="text-right py-3 px-4 text-yellow-400">Medium</td>
                    </tr>
                    <tr className="border-b border-gray-700/50">
                      <td className="py-3 px-4 text-gray-300">Nigerian T-Bills</td>
                      <td className="text-right py-3 px-4">18-22%</td>
                      <td className="text-right py-3 px-4">3-12 months</td>
                      <td className="text-right py-3 px-4 text-red-400">Locked</td>
                      <td className="text-right py-3 px-4 text-green-400">Low</td>
                    </tr>
                    <tr className="border-b border-gray-700/50">
                      <td className="py-3 px-4 text-gray-300">MSTR Preferred</td>
                      <td className="text-right py-3 px-4">9-10%</td>
                      <td className="text-right py-3 px-4">Perpetual</td>
                      <td className="text-right py-3 px-4 text-yellow-400">Tradable</td>
                      <td className="text-right py-3 px-4 text-green-400">Low-Medium</td>
                    </tr>
                    <tr>
                      <td className="py-3 px-4 text-gray-300">Busha Earn</td>
                      <td className="text-right py-3 px-4">7.5%</td>
                      <td className="text-right py-3 px-4">Flexible</td>
                      <td className="text-right py-3 px-4 text-green-400">Daily</td>
                      <td className="text-right py-3 px-4 text-green-400">Low</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        {/* Rest of your sections remain the same */}
        {/* ... Features, Transparency, FAQ, Contact sections ... */}
        
      </main>

      <footer className="bg-gray-950 border-t border-gray-800/60 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center font-bold">S</div>
                <span className="text-xl font-bold">Seamount.io</span>
              </div>
              <p className="text-gray-400 text-sm">The future of cross-border payments for emerging markets</p>
            </div>
            <div>
              <h4 className="text-white font-medium mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="text-gray-400 hover:text-white">Features</a></li>
                <li><a href="#calculator" className="text-gray-400 hover:text-white">Yield Calculator</a></li>
                <li><a href="#transparency" className="text-gray-400 hover:text-white">Transparency</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-4">Company</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="text-gray-400 hover:text-white">About Us</a></li>
                <li><a href="#contact" className="text-gray-400 hover:text-white">Contact</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="/legal/privacy-policy.html" className="text-gray-400 hover:text-white">Privacy Policy</a></li>
                <li><a href="/legal/terms-of-service.html" className="text-gray-400 hover:text-white">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8 text-center text-sm text-gray-500">
            <div className="flex flex-col sm:flex-row justify-between items-center">
              <p>© {new Date().getFullYear()} Seamount Technologies Ltd. All rights reserved.</p>
              <div className="flex space-x-4 mt-4 sm:mt-0">
                <div className="flex items-center"><Shield className="h-4 w-4 mr-1 text-green-500" /><span>GDPR Compliant</span></div>
                <div className="flex items-center"><Shield className="h-4 w-4 mr-1 text-blue-500" /><span>160% Backed</span></div>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;