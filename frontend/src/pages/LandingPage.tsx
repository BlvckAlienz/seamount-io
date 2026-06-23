import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  ArrowRight, Globe, Shield, Zap, Briefcase, Mail, MapPin, Phone, 
  ChevronDown, ChevronUp, TrendingUp, AlertTriangle, Server, ShieldCheck, Info, Lock, 
  Wallet, CreditCard, Layers, Coins, LineChart, Users, Building, 
  Target, PieChart, Database, Smartphone, Cpu, BarChart3,
  CheckCircle, Award, Globe2, Clock, Eye, Sparkles, Key, DollarSign
} from 'lucide-react';
import { motion, useInView, useAnimation } from 'framer-motion';

interface LandingPageProps {
  onOpenAuth: (view: 'login' | 'register') => void;
}

const LandingPage: React.FC<LandingPageProps> = ({ onOpenAuth }) => {
  const [expandedFaqs, setExpandedFaqs] = useState<number[]>([]);
  const [formState, setFormState] = useState({ name: '', businessName: '', email: '', message: '' });
  const [formStatus, setFormStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle');
  const [activeService, setActiveService] = useState<'payments' | 'tokenization' | 'prediction' | 'audit'>('payments');
  const [showRiskDetails, setShowRiskDetails] = useState(false);
  const [showFundingInfo, setShowFundingInfo] = useState(false);
  const [isClient, setIsClient] = useState(false);
  
  const [calc, setCalc] = useState({
    amount: '10000',
    period: '90'
  });
  
  const [oracleData, setOracleData] = useState({
    btcPrice: 0,
    btcVolatility: 0,
    fundingRate: 0,
    lastUpdate: null as Date | null,
    loading: true,
    error: null as string | null
  });
  
  const heroRef = useRef(null);
  const servicesRef = useRef(null);
  const isHeroInView = useInView(heroRef, { once: true });
  const isServicesInView = useInView(servicesRef, { once: true });
  
  const controls = useAnimation();

  useEffect(() => {
    setIsClient(true);
    if (isHeroInView) {
      controls.start("visible");
    }
  }, [controls, isHeroInView, isClient]);

  useEffect(() => {
    if (!isClient) return;

    const fetchOracleData = async () => {
      try {
        const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://seamount-api.onrender.com';
        const btcResponse = await fetch(`${API_BASE}/api/oracle/price/bitcoin`);
        
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
    if (!isClient) return { annualYield: 525, periodYield: 131.25, adjustedAPY: 0.0525, grossAPY: 0.0657, seamountFee: 0.0132 };
    
    const amount = parseFloat(calc.amount) || 0;
    const period = parseInt(calc.period);
    
    let grossAPY = period === 0 ? 0.0657 : 0.109;
    
    const basePlatformFee = 0.005;
    const performanceFeeRate = 0.20;
    
    const performanceFee = grossAPY * performanceFeeRate;
    const totalSeamountFee = basePlatformFee + performanceFee;
    
    let netAPY = grossAPY - totalSeamountFee;
    
    if (period === 90) {
      const fundingAdjustment = (oracleData.fundingRate - 12.5) / 1000;
      const volAdjustment = (oracleData.btcVolatility - 65) / 2000;
      grossAPY = Math.max(0.095, Math.min(0.125, grossAPY + fundingAdjustment + volAdjustment));
      
      const adjustedPerformanceFee = grossAPY * performanceFeeRate;
      const adjustedTotalFee = basePlatformFee + adjustedPerformanceFee;
      netAPY = grossAPY - adjustedTotalFee;
    }
    
    const annualYield = amount * netAPY;
    const periodYield = period === 0 ? annualYield : annualYield * (period / 365);
    
    return { 
      annualYield, 
      periodYield, 
      adjustedAPY: netAPY,
      grossAPY: grossAPY,
      seamountFee: totalSeamountFee
    };
  }, [isClient, calc.amount, calc.period, oracleData.btcVolatility, oracleData.fundingRate]);

  const handleContactSubmit = async () => {
    if (!formState.name || !formState.email) {
      alert('Please fill in your name and email');
      return;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formState.email)) {
      alert('Please enter a valid email address');
      return;
    }
    
    setFormStatus('sending');
    
    try {
      const response = await fetch('/api/v1/leads/business-contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formState.name,
          business_name: formState.businessName,
          email: formState.email,
          message: formState.message
        })
      });
      
      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.detail || 'Failed to submit inquiry');
      }
      
      setFormStatus('success');
      alert(result.message || 'Thank you! We\'ll be in touch within 24 hours.');
      
      setFormState({ 
        name: '', 
        businessName: '', 
        email: '', 
        message: '' 
      });
      
      setTimeout(() => setFormStatus('idle'), 3000);
      
    } catch (error: any) {
      console.error('[Business Contact] Error:', error);
      setFormStatus('error');
      alert(error.message || 'Failed to submit. Please try again.');
      setTimeout(() => setFormStatus('idle'), 3000);
    }
  };

  const services = {
    payments: {
      title: "🌐 Digital Payments & Yield",
      description: "Global settlement with multi-chain smart wallets",
      features: [
        "Multi-chain wallets (Algorand, Bitcoin, Ethereum, Polygon, Tron, Solana)",
        "24/7 settlements plus earn yields (up to 8.2% APY)",
        "Local payment rails integration (Flutterwave, Paystack)",
        "Enterprise treasury management"
      ],
      icon: <Globe2 className="h-12 w-12" />,
      color: "from-blue-500 to-cyan-500",
      gradient: "bg-gradient-to-br from-blue-500/20 to-cyan-500/20",
      imageKey: 'wallets'
    },
    tokenization: {
      title: "🗝️ Asset Tokenization",
      description: "Transform assets into digital securities and raise capital from private markets",
      features: [
        "Raise capital through fractional ownership",
        "Bypass traditional gatekeepers with direct access to investors",
        "Women-led businesses gain equal visibility and opportunity",
        "Transparent, merit-based capital allocation"
      ],
      icon: <PieChart className="h-12 w-12" />,
      color: "from-purple-500 to-pink-500",
      gradient: "bg-gradient-to-br from-purple-500/20 to-pink-500/20",
      imageKey: 'tokenization'
    },
    prediction: {
      title: "🔄 P2P Trading",
      description: "Peer-to-peer crypto trading with secure escrow and dispute resolution",
      features: [
        "Buy and sell crypto directly with other users",
        "Escrow-protected trades with automatic settlement",
        "Multi-currency support (USD, NGN, KES, ZAR, GHS)",
        "Dispute resolution system for safe trading"
      ],
      icon: <ArrowRight className="h-12 w-12" />,
      color: "from-orange-500 to-yellow-500",
      gradient: "bg-gradient-to-br from-orange-500/20 to-yellow-500/20",
      imageKey: 'p2p'
    },
    audit: {
      title: "🛡️ Real-Time AML Intelligence",
      description: "On-premise AI fraud detection for every transaction",
      features: [
        "45K+ fraud signatures: EFCC, CBN, Kenya DCI, curated typologies",
        "Real-time embedding & cosine similarity matching",
        "5-factor scoring: pattern, structuring, velocity, counterparty, time",
        "Instant Suspicious Transaction Reports — anti-hallucination AI",
        "100% on-premise: zero transaction data leaves your servers"
      ],
      icon: <Shield className="h-12 w-12" />,
      color: "from-green-500 to-emerald-500",
      gradient: "bg-gradient-to-br from-green-500/20 to-emerald-500/20",
      imageKey: 'aml'
    }
  };

  const faqs = [
    { 
      question: "What assets can be tokenized on Seamount?", 
      answer: "We support tokenization of public and private company shares, real estate, infrastructure (data centers, power grids, etc.), commodities, industrial machinery/equipment, art, and intellectual property. Each asset issuer undergoes rigorous due diligence including incorporation docs, tax certificates, audited accounts, and regulatory compliance checks before listing." 

    },
    { 
      question: "How does your investment service work?", 
      answer: "Seamount operates investment services through licensed fund managers and partners. All investment products are managed by third-party licensed entities. Past performance does not guarantee future results." 
    },
    {
      question: "Is Seamount regulated?",
      answer: "Seamount operates in Nigeria via partnership with a licensed VASP under regulatory oversight of the SEC's ISA 2025. We are also registered with the NFIU. Globally, we are pursuing licenses under frameworks such as Kenya (VASP Act) and South Africa (FSCA)."
    },
    {
      question: "What markets do you currently operate in?",
      answer: "Our infrastructure is live in Nigeria (via Quidax partnership). We're expanding to Kenya, Rwanda, and South Africa soon."
    }
  ];

  const FloatingCrypto = ({ count = 15, section = 'default' }: { count?: number; section?: string }) => {
    const cryptoSymbols = ['₿', '💎', '🪙', 'Ξ', '₮', '💰', '⚡'];
    
    return (
      <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-20 z-0">
        {[...Array(count)].map((_, i) => {
          const symbol = cryptoSymbols[i % cryptoSymbols.length];
          const startX = Math.random() * 100;
          const endX = startX + (Math.random() - 0.5) * 30;
          const duration = 8 + Math.random() * 12;
          const delay = Math.random() * 5;
          
          return (
            <motion.div
              key={`${section}-${i}`}
              className="absolute text-2xl sm:text-3xl md:text-4xl"
              style={{ 
                left: `${startX}%`,
                top: '100%',
                textShadow: '0 0 10px currentColor'
              }}
              initial={{ 
                y: 0,
                x: 0,
                opacity: 0,
                rotate: 0,
                scale: 0.5
              }}
              animate={{
                y: typeof window !== 'undefined' ? -window.innerHeight - 100 : -800,
                x: `${(endX - startX)}vw`,
                opacity: [0, 0.3, 0.6, 0.3, 0],
                rotate: 360,
                scale: [0.5, 1, 0.8, 1, 0.5]
              }}
              transition={{
                duration,
                delay,
                repeat: Infinity,
                ease: "linear"
              }}
            >
              {symbol}
            </motion.div>
          );
        })}
      </div>
    );
  };

  const ServiceImage = ({ serviceKey }: { serviceKey: string }) => {
    const renderServiceVisual = () => {
      switch(serviceKey) {
        case 'wallets':
          return (
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500 to-cyan-600 p-6 overflow-hidden">
              <div className="absolute inset-0">
                {[...Array(15)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="absolute w-1 h-1 bg-white/30 rounded-full"
                    initial={{ x: Math.random() * 256, y: Math.random() * 256 }}
                    animate={{
                      y: [Math.random() * 256, Math.random() * 256],
                      x: [Math.random() * 256, Math.random() * 256],
                      opacity: [0.3, 0.8, 0.3]
                    }}
                    transition={{
                      duration: 3 + Math.random() * 2,
                      repeat: Infinity,
                      ease: "easeInOut"
                    }}
                  />
                ))}
              </div>
              
              <div className="h-full flex flex-col justify-between text-white relative z-10">
                <motion.div 
                  className="flex justify-between items-center"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <div className="flex items-center gap-2">
                    <motion.div 
                      className="w-2 h-2 bg-green-400 rounded-full"
                      animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    />
                    <span className="text-xs font-medium">5 Networks</span>
                  </div>
                  <motion.div
                    animate={{ rotate: [0, 360] }}
                    transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                  >
                    <Wallet className="h-6 w-6 opacity-80" />
                  </motion.div>
                </motion.div>
                
                <motion.div 
                  className="bg-white/10 backdrop-blur rounded-xl p-4 border border-white/20"
                  whileHover={{ scale: 1.02 }}
                >
                  <div className="text-xs opacity-70 mb-1">Total Balance</div>
                  <motion.div 
                    className="text-3xl font-bold mb-3"
                    initial={{ scale: 0.9 }}
                    animate={{ scale: 1 }}
                  >
                    $12,487
                  </motion.div>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { token: 'ALGO', value: '$4,250', color: 'from-blue-400 to-blue-600' },
                      { token: 'BTC', value: '$5,892', color: 'from-orange-400 to-orange-600' },
                      { token: 'ETH', value: '$2,345', color: 'from-purple-400 to-purple-600' }
                    ].map((item, idx) => (
                      <motion.div 
                        key={item.token} 
                        className={`bg-gradient-to-br ${item.color} rounded-lg p-2 text-center`}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        whileHover={{ scale: 1.1, rotate: 5 }}
                      >
                        <div className="text-xs opacity-90">{item.token}</div>
                        <div className="text-sm font-semibold">{item.value}</div>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
                
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { icon: '↓', label: 'Fund', color: 'hover:bg-green-500/30' }, 
                    { icon: '↑', label: 'Send', color: 'hover:bg-blue-500/30' }, 
                    { icon: '⇄', label: 'Swap', color: 'hover:bg-purple-500/30' }, 
                    { icon: '📈', label: 'Earn', color: 'hover:bg-yellow-500/30' }
                  ].map((action, idx) => (
                    <motion.div 
                      key={action.label} 
                      className={`bg-white/10 backdrop-blur rounded-lg p-2 text-center border border-white/20 cursor-pointer ${action.color}`}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.5 + idx * 0.1 }}
                      whileHover={{ scale: 1.15, y: -5 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <div className="text-lg mb-1">{action.icon}</div>
                      <div className="text-xs">{action.label}</div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          );
          
        case 'tokenization':
          return (
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500 to-pink-600 p-6 overflow-hidden">
              <div className="absolute inset-0">
                {[...Array(8)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="absolute text-2xl"
                    initial={{ x: Math.random() * 256, y: Math.random() * 256 }}
                    animate={{
                      y: [null, Math.random() * 256],
                      x: [null, Math.random() * 256],
                      rotate: 360,
                      opacity: [0.2, 0.5, 0.2]
                    }}
                    transition={{
                      duration: 4 + Math.random() * 3,
                      repeat: Infinity
                    }}
                  >
                    🪙
                  </motion.div>
                ))}
              </div>
              
              <div className="h-full flex flex-col justify-between text-white relative z-10">
                <motion.div 
                  className="flex justify-between items-center"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <span className="text-xs font-medium">Asset Conversion</span>
                  <motion.div
                    animate={{ rotate: [0, 360] }}
                    transition={{ duration: 15, repeat: Infinity }}
                  >
                    <Coins className="h-6 w-6 opacity-80" />
                  </motion.div>
                </motion.div>
                
                <div className="space-y-3">
                  <motion.div 
                    className="bg-white/10 backdrop-blur rounded-xl p-3 border border-white/20"
                    whileHover={{ scale: 1.05 }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs opacity-70">Traditional Asset</span>
                      <motion.span 
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      >
                        🏢
                      </motion.span>
                    </div>
                    <div className="h-2 bg-white/20 rounded-full overflow-hidden">
                      <motion.div 
                        className="h-full bg-white/40"
                        initial={{ width: "0%" }}
                        animate={{ width: "100%" }}
                        transition={{ duration: 2, repeat: Infinity }}
                      />
                    </div>
                  </motion.div>
                  
                  <div className="flex justify-center">
                    <motion.div 
                      className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center backdrop-blur"
                      animate={{ scale: [1, 1.2, 1], rotate: [0, 180, 360] }}
                      transition={{ duration: 3, repeat: Infinity }}
                    >
                      <span className="text-xl">⇣</span>
                    </motion.div>
                  </div>
                  
                  <motion.div 
                    className="bg-white/10 backdrop-blur rounded-xl p-3 border border-white/20"
                    whileHover={{ scale: 1.05 }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs opacity-70">Digital Securities</span>
                      <span className="text-xs font-semibold">🪙</span>
                    </div>
                    <div className="grid grid-cols-4 gap-1">
                      {[1,2,3,4].map(i => (
                        <motion.div 
                          key={i} 
                          className="h-6 bg-gradient-to-br from-yellow-400/40 to-orange-400/40 rounded"
                          initial={{ opacity: 0, scale: 0 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: i * 0.2, repeat: Infinity, repeatDelay: 2 }}
                        />
                      ))}
                    </div>
                  </motion.div>
                </div>
                
                <motion.div 
                  className="bg-white/10 backdrop-blur rounded-xl p-3 border border-white/20"
                  whileHover={{ boxShadow: "0 0 20px rgba(255,255,255,0.3)" }}
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="text-xs opacity-70">Tokenized</div>
                      <motion.div 
                        className="text-2xl font-bold"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                      >
                        3
                      </motion.div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs opacity-70">Status</div>
                      <motion.div 
                        className="text-sm font-semibold text-green-300"
                        animate={{ opacity: [0.5, 1, 0.5] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      >
                        Live
                      </motion.div>
                    </div>
                  </div>
                </motion.div>
              </div>
            </div>
          );
          
        case 'secondary':
          return (
            <div className="absolute inset-0 bg-gradient-to-br from-orange-500 to-yellow-600 p-6 overflow-hidden">
              <div className="absolute inset-0">
                {[...Array(12)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="absolute w-2 h-2 bg-white/40 rounded-full"
                    initial={{ x: Math.random() * 256, y: 256 }}
                    animate={{ y: -50, opacity: [0, 1, 0] }}
                    transition={{
                      duration: 2 + Math.random() * 2,
                      repeat: Infinity,
                      delay: Math.random() * 2
                    }}
                  />
                ))}
              </div>
              
              <div className="h-full flex flex-col justify-between text-white relative z-10">
                <motion.div 
                  className="flex justify-between items-center"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <span className="text-xs font-medium">Active Offers</span>
                  <motion.div
                    animate={{ y: [0, -5, 0], rotate: [0, 5, -5, 0] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <TrendingUp className="h-6 w-6 opacity-80" />
                  </motion.div>
                </motion.div>
                
                <div className="space-y-3">
                  <motion.div 
                    className="bg-white/10 backdrop-blur rounded-xl p-3 border border-white/20"
                    whileHover={{ scale: 1.05 }}
                  >
                    <div className="text-xs opacity-70 mb-1">Market Value</div>
                    <motion.div 
                      className="text-2xl font-bold mb-2"
                      initial={{ scale: 0.8 }}
                      animate={{ scale: 1 }}
                    >
                      $25M
                    </motion.div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1 bg-white/20 rounded-full overflow-hidden">
                        <motion.div 
                          className="h-full bg-gradient-to-r from-green-400 to-emerald-400"
                          initial={{ width: "0%" }}
                          animate={{ width: "75%" }}
                          transition={{ duration: 1.5 }}
                        />
                      </div>
                      <span className="text-xs">75%</span>
                    </div>
                  </motion.div>
                  
                  <div className="grid grid-cols-2 gap-2">
                    <motion.div 
                      className="bg-white/10 backdrop-blur rounded-lg p-3 border border-white/20"
                      initial={{ x: -20, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      whileHover={{ scale: 1.1, rotate: 3 }}
                    >
                      <div className="text-xs opacity-70 mb-1">Active</div>
                      <motion.div 
                        className="text-xl font-bold"
                        animate={{ scale: [1, 1.1, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      >
                        5
                      </motion.div>
                    </motion.div>
                    <motion.div 
                      className="bg-white/10 backdrop-blur rounded-lg p-3 border border-white/20"
                      initial={{ x: 20, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      whileHover={{ scale: 1.1, rotate: -3 }}
                    >
                      <div className="text-xs opacity-70 mb-1">Settlement</div>
                      <div className="text-xl font-bold">2-4m</div>
                    </motion.div>
                  </div>
                </div>
                
                <div className="space-y-2">
                  {[1,2,3].map(i => (
                    <motion.div 
                      key={i} 
                      className="bg-white/10 backdrop-blur rounded-lg p-2 flex items-center justify-between border border-white/20"
                      initial={{ x: -50, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      transition={{ delay: 0.6 + i * 0.1 }}
                      whileHover={{ x: 5, scale: 1.02 }}
                    >
                      <div className="flex items-center gap-2">
                        <motion.div 
                          className="w-6 h-6 bg-gradient-to-br from-orange-300 to-yellow-300 rounded"
                          animate={{ rotate: 360 }}
                          transition={{ duration: 10, repeat: Infinity }}
                        />
                        <div className="text-xs">Asset #{i}</div>
                      </div>
                      <div className="text-xs font-semibold">$213</div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          );

        case 'p2p':
          return (
            <div className="absolute inset-0 bg-gradient-to-br from-orange-500 to-yellow-600 p-6 overflow-hidden">
              <div className="absolute inset-0">
                {[...Array(12)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="absolute w-2 h-2 bg-white/40 rounded-full"
                    initial={{ x: Math.random() * 256, y: Math.random() * 256 }}
                    animate={{
                      y: [null, Math.random() * 256],
                      x: [null, Math.random() * 256],
                      opacity: [0.2, 0.8, 0.2]
                    }}
                    transition={{
                      duration: 3 + Math.random() * 2,
                      repeat: Infinity
                    }}
                  />
                ))}
              </div>

              <div className="h-full flex flex-col justify-between text-white relative z-10">
                <motion.div 
                  className="flex justify-between items-center"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <span className="text-xs font-medium">P2P Marketplace</span>
                  <motion.div
                    animate={{ rotate: [0, 360] }}
                    transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                  >
                    <ArrowRight className="h-6 w-6 opacity-80" />
                  </motion.div>
                </motion.div>

                <div className="space-y-3">
                  <motion.div 
                    className="bg-white/10 backdrop-blur rounded-xl p-3 border border-white/20"
                    whileHover={{ scale: 1.05 }}
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-xs opacity-70">Active Offers</span>
                      <motion.span
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      >
                        💱
                      </motion.span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { action: 'Buy BTC', price: '$67,458', color: 'bg-green-400/20' },
                        { action: 'Sell ETH', price: '$2,054', color: 'bg-blue-400/20' }
                      ].map((item, idx) => (
                        <div key={idx} className={`${item.color} rounded-lg p-2 text-center`}>
                          <div className="text-xs">{item.action}</div>
                          <div className="text-sm font-semibold">{item.price}</div>
                        </div>
                      ))}
                    </div>
                  </motion.div>

                  <div className="flex justify-center">
                    <motion.div 
                      className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center backdrop-blur"
                      animate={{ 
                        scale: [1, 1.1, 1],
                        rotate: [0, 5, -5, 0]
                      }}
                      transition={{ duration: 2, repeat: Infinity }}
                    >
                      <span className="text-xl">↺</span>
                    </motion.div>
                  </div>

                  <motion.div 
                    className="bg-white/10 backdrop-blur rounded-xl p-3 border border-white/20"
                    whileHover={{ scale: 1.05 }}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="text-xs opacity-70">Escrow Balance</div>
                        <motion.div 
                          className="text-2xl font-bold"
                          initial={{ scale: 0.8 }}
                          animate={{ scale: 1 }}
                        >
                          $245,890
                        </motion.div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs opacity-70">Trades Today</div>
                        <div className="text-sm font-semibold text-green-300">127</div>
                      </div>
                    </div>
                    <div className="mt-2 h-1 bg-white/20 rounded-full overflow-hidden">
                      <motion.div 
                        className="h-full bg-green-400"
                        initial={{ width: "0%" }}
                        animate={{ width: "100%" }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                      />
                    </div>
                  </motion.div>
                </div>

                <div className="grid grid-cols-2 gap-2 mt-2">
                  {[
                    { emoji: '🛡️', label: 'Escrow' },
                    { emoji: '⚖️', label: 'Dispute' }
                  ].map((item, idx) => (
                    <motion.div 
                      key={item.label}
                      className="bg-white/10 backdrop-blur rounded-lg p-2 text-center border border-white/20 cursor-pointer"
                      initial={{ y: 20, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      transition={{ delay: 0.8 + idx * 0.1 }}
                      whileHover={{ scale: 1.1, y: -5 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <div className="text-2xl mb-1">{item.emoji}</div>
                      <div className="text-xs">{item.label}</div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          );

        case 'aml':
          return (
            <div className="absolute inset-0 bg-gradient-to-br from-green-500 to-emerald-600 p-6 overflow-hidden">
              <div className="absolute inset-0">
                {/* Animated transaction lines */}
                {[...Array(8)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="absolute h-0.5 w-16 bg-white/30"
                    style={{ top: `${15 + i * 10}%`, left: '10%' }}
                    initial={{ x: -50, opacity: 0 }}
                    animate={{ x: 300, opacity: [0.2, 0.6, 0.2] }}
                    transition={{ duration: 2 + i * 0.3, repeat: Infinity, delay: i * 0.4 }}
                  />
                ))}
                {/* Scanning shield */}
                <motion.div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                  <Shield className="h-24 w-24 text-white/20" />
                  <motion.div
                    className="absolute inset-0 flex items-center justify-center"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
                  >
                    <div className="w-16 h-16 border-2 border-white/40 rounded-full" />
                  </motion.div>
                  <motion.div
                    className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 bg-red-400 rounded-full"
                    animate={{ scale: [1, 1.5, 1], opacity: [1, 0.6, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                </motion.div>
              </div>
              
              <div className="h-full flex flex-col justify-between text-white relative z-10">
                <motion.div 
                  className="flex justify-between items-center"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <span className="text-xs font-medium">Transaction Scanner</span>
                  <motion.div
                    animate={{ rotate: [0, 360] }}
                    transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                  >
                    <Shield className="h-6 w-6 opacity-80" />
                  </motion.div>
                </motion.div>
                
                <div className="space-y-3">
                  <motion.div 
                    className="bg-white/10 backdrop-blur rounded-xl p-3 border border-white/20"
                    whileHover={{ scale: 1.02 }}
                  >
                    <div className="text-xs opacity-70 mb-1">Pattern Library</div>
                    <motion.div className="text-xl font-bold">45,389</motion.div>
                    <div className="flex gap-1 mt-1">
                      {['EFCC','CBN','DCI','Typologies'].map((s,i) => (
                        <span key={i} className="text-xs bg-white/20 px-1.5 py-0.5 rounded">{s}</span>
                      ))}
                    </div>
                  </motion.div>
                  
                  <motion.div 
                    className="bg-white/10 backdrop-blur rounded-xl p-3 border border-white/20"
                    whileHover={{ scale: 1.02 }}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs opacity-70">Scanning tx...</span>
                      <motion.span 
                        className="text-xs font-semibold text-red-300"
                        animate={{ opacity: [0.5, 1, 0.5] }}
                        transition={{ duration: 1, repeat: Infinity }}
                      >
                        LIVE
                      </motion.span>
                    </div>
                    <div className="flex justify-between mt-2">
                      <span className="text-xs">Factor</span>
                      <span className="text-xs">Score</span>
                    </div>
                    {[
                      { name: 'Pattern', val: '1.00', color: 'bg-red-400' },
                      { name: 'Structuring', val: '1.00', color: 'bg-red-400' },
                      { name: 'Velocity', val: '0.00', color: 'bg-emerald-400' },
                    ].map((f, i) => (
                      <div key={i} className="flex justify-between items-center mt-1">
                        <span className="text-xs">{f.name}</span>
                        <div className="flex items-center gap-1">
                          <div className="w-12 h-1.5 bg-white/20 rounded-full overflow-hidden">
                            <motion.div 
                              className={`h-full ${f.color} rounded-full`}
                              initial={{ width: 0 }}
                              animate={{ width: `${parseFloat(f.val)*100}%` }}
                              transition={{ duration: 0.8, delay: i * 0.2 }}
                            />
                          </div>
                          <span className="text-xs font-mono">{f.val}</span>
                        </div>
                      </div>
                    ))}
                  </motion.div>
                </div>
                
                <motion.div 
                  className="bg-white/10 backdrop-blur rounded-xl p-3 border border-white/20"
                  whileHover={{ boxShadow: "0 0 20px rgba(255,255,255,0.3)" }}
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="text-xs opacity-70">Alert</div>
                      <motion.div 
                        className="text-lg font-bold text-red-300"
                        animate={{ opacity: [0.7, 1, 0.7] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      >
                        AMBER
                      </motion.div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs opacity-70">STR Generated</div>
                      <div className="text-xs font-semibold text-green-300">3.2s</div>
                    </div>
                  </div>
                </motion.div>
              </div>
            </div>
          );

        default:
          return null;
      }
    };

    return (
      <div className="relative w-64 h-64 rounded-2xl overflow-hidden shadow-lg">
        {renderServiceVisual()}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 via-white to-gray-50">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
        
        * {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }
        
        .glass-card {
          background: rgba(255, 255, 255, 0.7);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        .gradient-text {
          background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 25%, #ec4899 50%, #f59e0b 75%, #10b981 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          background-size: 200% auto;
          animation: gradient 8s ease infinite;
        }
        
        @keyframes gradient {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        
        .glider-float {
          animation: float 6s ease-in-out infinite;
        }
        
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          33% { transform: translateY(-20px) rotate(5deg); }
          66% { transform: translateY(-10px) rotate(-5deg); }
        }
        
        .cyber-cube {
          transform-style: preserve-3d;
          animation: cube-rotate 8s linear infinite;
        }
        
        @keyframes cube-rotate {
          0% { transform: rotateY(0deg) rotateX(0deg); }
          100% { transform: rotateY(360deg) rotateX(360deg); }
        }
        
        .cyber-face {
          animation: face-pulse 2s ease-in-out infinite alternate;
        }
        
        @keyframes face-pulse {
          0% { box-shadow: 0 0 20px rgba(139, 92, 246, 0.5); }
          100% { box-shadow: 0 0 40px rgba(139, 92, 246, 0.8), 0 0 60px rgba(59, 130, 246, 0.4); }
        }
        
        .cyber-block {
          animation: block-glow 1.5s ease-in-out infinite;
        }
        
        @keyframes block-glow {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.8; background: rgba(255, 255, 255, 0.4); }
        }
        
        .orbit {
          animation: orbit 3s linear infinite;
        }
        
        @keyframes orbit {
          0% { transform: rotate(0deg) translateX(50px) rotate(0deg); }
          100% { transform: rotate(360deg) translateX(50px) rotate(-360deg); }
        }
        
        .particle {
          animation: particle-rise 4s ease-in infinite;
        }
        
        @keyframes particle-rise {
          0% { transform: translateY(200px) scale(0); opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 0.5; }
          100% { transform: translateY(-100px) scale(1); opacity: 0; }
        }
        
        .scroll-indicator {
          animation: indicator-bounce 2s ease-in-out infinite;
        }
        
        @keyframes indicator-bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(8px); }
        }
        
        .scroll-dot {
          animation: dot-scroll 2s ease-in-out infinite;
        }
        
        @keyframes dot-scroll {
          0%, 100% { transform: translateY(0); opacity: 0.3; }
          50% { transform: translateY(12px); opacity: 1; }
        }
      `}</style>

      {/* Navigation Header */}
      <header className="fixed top-0 left-0 right-0 glass-card z-50 shadow-lg">
        <div className="max-w-7xl mx-auto px-2 sm:px-6 py-2 sm:py-4 flex justify-between items-center gap-2">
          <div className="flex items-center space-x-1.5 sm:space-x-3">
            <div className="relative">
              <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg blur opacity-30"></div>
              <img src="/seamount-logo.jpeg" alt="Seamount" className="relative w-8 h-8 sm:w-10 sm:h-10 object-contain rounded-lg" />
            </div>
            <span className="text-base sm:text-xl font-bold bg-gradient-to-r from-green-600 to-purple-600 bg-clip-text text-transparent">Seamount</span>
          </div>
          
          <nav className="hidden md:flex space-x-8 text-sm font-medium">
            <a href="#services" className="text-gray-700 hover:text-blue-600 transition-all hover:scale-105">Services</a>
            <a href="#how-it-works" className="text-gray-700 hover:text-blue-600 transition-all hover:scale-105">How It Works</a>
            <a href="#calculator" className="text-gray-700 hover:text-blue-600 transition-all hover:scale-105">Calculator</a>
            <a href="#business" className="text-gray-700 hover:text-blue-600 transition-all hover:scale-105">Business</a>
          </nav>
          
          <div className="flex items-center space-x-1.5 sm:space-x-3">
            <button 
              onClick={() => onOpenAuth('login')} 
              className="px-2 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-medium text-gray-700 hover:text-blue-600 transition-all"
            >
              Sign In
            </button>
            <button 
              onClick={() => onOpenAuth('register')} 
              className="px-3 sm:px-6 py-1.5 sm:py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white text-xs sm:text-base font-semibold rounded-lg hover:shadow-xl hover:scale-105 transition-all whitespace-nowrap"
            >
              Get Started
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section ref={heroRef} className="pt-20 sm:pt-24 pb-12 sm:pb-20 px-3 sm:px-6 relative overflow-hidden">
        <FloatingCrypto count={12} section="hero" />
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 opacity-50"></div>
        <div className="max-w-7xl mx-auto relative z-10">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={controls}
            variants={{
              visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
            }}
            className="text-center max-w-5xl mx-auto"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 glass-card rounded-full text-sm font-medium mb-6 shadow-sm">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-gray-700">Powered by Tether WDK + Circle Arc + XRP Ledger</span>
              </div>
            </div>
            
            <h1 className="text-3xl sm:text-5xl md:text-6xl lg:text-7xl font-bold mb-4 sm:mb-6 leading-tight">
              <span className="block">Seamount</span>
              <span className="gradient-text">Digital Money Market</span>
            </h1>
            
            <div className="text-base sm:text-xl md:text-2xl text-gray-600 mb-6 sm:mb-8 max-w-3xl mx-auto leading-relaxed px-2">
              <p className="mb-2">Stablecoins. 24/7 Payments & Yield. Asset tokenization.</p>
              <p className="font-semibold text-gray-900">
                Unlocking growth for communities.
              </p>
            </div>
            
            <div className="flex flex-col sm:flex-row justify-center gap-3 sm:gap-4 mb-6 sm:mb-8 px-4">
              <motion.button 
                onClick={() => onOpenAuth('register')} 
                className="group px-6 sm:px-8 py-3 sm:py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white text-sm sm:text-base font-semibold rounded-xl transition-all duration-300"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                animate={{ 
                  boxShadow: [
                    "0 0 0 0 rgba(59, 130, 246, 0)",
                    "0 0 0 10px rgba(59, 130, 246, 0.1)",
                    "0 0 0 0 rgba(59, 130, 246, 0)"
                  ]
                }}
                transition={{ 
                  boxShadow: { duration: 2, repeat: Infinity }
                }}
              >
                <span className="flex items-center justify-center gap-3">
                  Get Started <ArrowRight className="h-5 w-5 group-hover:translate-x-2 transition-transform" />
                </span>
              </motion.button>
              
              <motion.button 
                onClick={() => document.getElementById('services')?.scrollIntoView({ behavior: 'smooth' })} 
                className="px-6 sm:px-8 py-3 sm:py-4 glass-card text-gray-900 text-sm sm:text-base font-semibold rounded-xl transition-all"
                whileHover={{ scale: 1.05, backgroundColor: "rgba(255, 255, 255, 0.9)" }}
                whileTap={{ scale: 0.95 }}
              >
                Explore Our Services
              </motion.button>
            </div>
            
            {/* 🎨 CYBERPUNK WEB3 GLIDER */}
            <div className="relative h-48 flex items-center justify-center">
              {/* Particle Trail */}
              <div className="absolute inset-0 overflow-hidden">
                {[...Array(20)].map((_, i) => (
                  <div
                    key={i}
                    className="absolute w-1 h-1 bg-gradient-to-r from-blue-400 to-purple-400 rounded-full particle"
                    style={{
                      left: `${Math.random() * 100}%`,
                      animationDelay: `${Math.random() * 3}s`,
                      opacity: Math.random() * 0.7 + 0.3
                    }}
                  />
                ))}
              </div>
              
              {/* Main Glider Character */}
              <div className="relative z-10 glider-float">
                {/* Holographic Glow */}
                <div className="absolute -inset-8 bg-gradient-to-r from-blue-500/30 via-purple-500/30 to-pink-500/30 rounded-full blur-2xl animate-pulse"></div>
                
                {/* 3D Blockchain Cube */}
                <div className="relative w-24 h-24 cyber-cube">
                  {/* Front Face */}
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg transform rotate-12 cyber-face border-2 border-white/30">
                    <div className="absolute inset-2 border border-white/20 rounded">
                      <div className="absolute inset-0 grid grid-cols-3 grid-rows-3 gap-1 p-1">
                        {[...Array(9)].map((_, i) => (
                          <div key={i} className="bg-white/20 rounded-sm cyber-block" style={{animationDelay: `${i * 0.1}s`}}></div>
                        ))}
                      </div>
                    </div>
                  </div>
                  
                  {/* Side Face */}
                  <div className="absolute inset-0 bg-gradient-to-br from-purple-500 to-pink-600 rounded-lg transform -rotate-6 translate-x-2 translate-y-2 cyber-face border-2 border-white/20 opacity-60"></div>
                  
                  {/* Orbiting Coins */}
                  <div className="absolute inset-0 orbit">
                    <div className="absolute top-0 left-1/2 w-3 h-3 -ml-1.5 bg-yellow-400 rounded-full shadow-lg shadow-yellow-400/50"></div>
                  </div>
                  <div className="absolute inset-0 orbit" style={{animationDelay: '1s', animationDirection: 'reverse'}}>
                    <div className="absolute top-0 left-1/2 w-3 h-3 -ml-1.5 bg-green-400 rounded-full shadow-lg shadow-green-400/50"></div>
                  </div>
                </div>
              </div>
              
              {/* Scroll Prompt */}
              <button 
                onClick={() => document.getElementById('services')?.scrollIntoView({ behavior: 'smooth' })}
                className="absolute bottom-0 left-1/2 -translate-x-1/2 group cursor-pointer"
              >
                <div className="flex flex-col items-center gap-2 text-gray-600 hover:text-blue-600 transition-colors">
                  <span className="text-sm font-medium">Explore Services</span>
                  <div className="w-8 h-12 border-2 border-current rounded-full flex items-start justify-center p-2 scroll-indicator">
                    <div className="w-1.5 h-3 bg-current rounded-full scroll-dot"></div>
                  </div>
                </div>
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-16 px-3 sm:px-6 bg-gradient-to-r from-blue-50 via-purple-50 to-pink-50 relative overflow-hidden">
        <FloatingCrypto count={8} section="how-it-works" />
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="text-center mb-16">
            <h2 className="text-2xl sm:text-4xl md:text-5xl font-bold mb-3 sm:mb-4 text-gray-900 px-2">
              How It <span className="gradient-text">Works</span>
            </h2>
            <p className="text-lg text-gray-600 max-w-3xl mx-auto">
              Get started in minutes. From signup to your first transaction.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
            {/* Step 1: Sign Up & KYC */}
            <motion.div 
              className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg hover:shadow-2xl transition-all duration-300 border-2 border-transparent hover:border-blue-300"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center text-white font-bold text-xl">
                  1
                </div>
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <Users className="h-8 w-8 text-blue-500" />
                </motion.div>
              </div>
              <h3 className="text-xl font-bold mb-3 text-gray-900">Sign Up & Verify</h3>
              <p className="text-gray-600 text-sm mb-4">
                Create your account in 2 minutes. Complete KYC now or skip and verify later—your choice.
              </p>
              <div className="flex items-center gap-2 text-xs text-blue-600 font-medium">
                <CheckCircle className="h-4 w-4" />
                <span>Email verification required</span>
              </div>
            </motion.div>

            {/* Step 2: Multi-Chain Wallets */}
            <motion.div 
              className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg hover:shadow-2xl transition-all duration-300 border-2 border-transparent hover:border-purple-300"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-xl">
                  2
                </div>
                <motion.div
                  animate={{ rotate: [0, 360] }}
                  transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                >
                  <Wallet className="h-8 w-8 text-purple-500" />
                </motion.div>
              </div>
              <h3 className="text-xl font-bold mb-3 text-gray-900">6 Smart Wallets Created</h3>
              <p className="text-gray-600 text-sm mb-4">
                Instantly get wallets on Algorand, Bitcoin, Ethereum, Polygon, Tron, and Solana—ready to use.
              </p>
              <div className="grid grid-cols-3 gap-1 mt-3">
                {['ALGO', 'BTC', 'ETH', 'POL', 'TRX', 'SOL'].map((chain, idx) => (
                  <div 
                    key={chain} 
                    className="text-xs font-semibold text-center py-1 bg-purple-50 rounded text-purple-700"
                    style={{ animationDelay: `${idx * 0.1}s` }}
                  >
                    {chain}
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Step 3: Fund Your Wallets */}
            <motion.div 
              className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg hover:shadow-2xl transition-all duration-300 border-2 border-transparent hover:border-green-300"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3 }}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-full flex items-center justify-center text-white font-bold text-xl">
                  3
                </div>
                <motion.div
                  animate={{ y: [0, -5, 0] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                >
                  <CreditCard className="h-8 w-8 text-green-500" />
                </motion.div>
              </div>
              <h3 className="text-xl font-bold mb-3 text-gray-900">Receive Tokens or Fund Wallet</h3>
              <p className="text-gray-600 text-sm mb-4">
                Send tokens to your wallets or buy from P2P merchants—we support local currencies.
              </p>
              <div className="flex items-center gap-2 text-xs">
                <span className="px-2 py-1 bg-green-50 text-green-700 rounded font-medium">Paystack</span>
                <span className="px-2 py-1 bg-green-50 text-green-700 rounded font-medium">Flutterwave</span>
                <span className="px-2 py-1 bg-green-50 text-green-700 rounded font-medium">P2P Trading</span>
              </div>
            </motion.div>

            {/* Step 4: Trade & Withdraw */}
            <motion.div 
              className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg hover:shadow-2xl transition-all duration-300 border-2 border-transparent hover:border-orange-300"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.4 }}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-orange-600 rounded-full flex items-center justify-center text-white font-bold text-xl">
                  4
                </div>
                <motion.div
                  animate={{ rotate: [0, 10, -10, 0] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <TrendingUp className="h-8 w-8 text-orange-500" />
                </motion.div>
              </div>
              <h3 className="text-xl font-bold mb-3 text-gray-900">Send & Withdraw</h3>
              <p className="text-gray-600 text-sm mb-4">
                Make global payments, earn yields, swap tokens. Withdraw anytime back to local fiat—seamlessly.
              </p>
              <div className="flex items-center gap-2 text-xs text-orange-600 font-medium">
                <Sparkles className="h-4 w-4" />
                <span>Instant off-ramps available</span>
              </div>
            </motion.div>
          </div>

          {/* Call to Action */}
          <motion.div 
            className="text-center mt-12"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
          >
            <button 
              onClick={() => onOpenAuth('register')} 
              className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl hover:shadow-xl hover:scale-105 transition-all duration-300"
            >
              Get Started Now <ArrowRight className="inline h-5 w-5 ml-2" />
            </button>
            <p className="mt-4 text-sm text-gray-600">
              Join thousands using Seamount for borderless payments
            </p>
          </motion.div>
        </div>
      </section>

      {/* Services Section WITH IMAGES */}
      <section id="services" ref={servicesRef} className="py-12 sm:py-20 px-3 sm:px-6 bg-gray-50 relative overflow-hidden">
        <FloatingCrypto count={10} section="services" />
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="text-center mb-16">
            <h2 className="text-2xl sm:text-4xl md:text-5xl font-bold mb-3 sm:mb-4 text-gray-900 px-2">
              Complete <span className="gradient-text">Web3 Infrastructure</span>
            </h2>
            <p className="text-lg text-gray-600 max-w-3xl mx-auto">
              Four pillars of the future. One unified platform.
            </p>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 mb-12 max-w-4xl mx-auto px-2">
            {Object.entries(services).map(([key, service]) => (
              <motion.button
                key={key}
                onClick={() => setActiveService(activeService === key ? '' : key as any)}
                className={`p-3 sm:p-4 rounded-xl transition-all ${activeService === key ? 'glass-card shadow-lg scale-105' : 'hover:bg-white/50'}`}
                whileHover={{ scale: 1.05, y: -5 }}
                whileTap={{ scale: 0.95 }}
              >
                <motion.div 
                  className={`w-12 h-12 rounded-lg ${service.gradient} flex items-center justify-center mx-auto mb-3`}
                  animate={activeService === key ? { 
                    rotate: [0, 360],
                    scale: [1, 1.1, 1]
                  } : {}}
                  transition={{ 
                    duration: 2,
                    repeat: activeService === key ? Infinity : 0
                  }}
                >
                  {service.icon}
                </motion.div>
                <div className="text-sm font-medium text-gray-900">{service.title.split(' ')[0]}</div>
              </motion.button>
            ))}
          </div>
          
          {activeService && (
            <motion.div 
              key={activeService}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-5xl mx-auto px-2"
            >
              <div className="glass-card rounded-2xl p-4 sm:p-8 shadow-xl">
                <div className="flex flex-col md:flex-row items-start gap-6 sm:gap-8">
                  <div className="flex-1">
                    <h3 className="text-2xl font-bold mb-2 text-gray-900">{services[activeService].title}</h3>
                    <p className="text-gray-600 mb-6">{services[activeService].description}</p>
                    
                    <div className="space-y-3">
                      {services[activeService].features.map((feature, idx) => (
                        <div key={idx} className="flex items-start gap-3">
                          <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
                          <span className="text-gray-700">{feature}</span>
                        </div>
                      ))}
                    </div>
                    
                    <button 
                      onClick={() => onOpenAuth('register')} 
                      className="mt-8 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-lg hover:shadow-lg hover:scale-105 transition-all"
                    >
                      Get Started
                    </button>
                  </div>
                  
                  {/* 📍 SERVICE IMAGE DISPLAY */}
                  <div className="hidden sm:block">
                    <ServiceImage serviceKey={services[activeService].imageKey} />
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </section>

      {/* 📍 COMPLETE CALCULATOR SECTION (updated with fixed components for both tiers) */}
      <section id="calculator" className="py-12 sm:py-20 px-3 sm:px-6 bg-gray-50 relative overflow-hidden">
        <FloatingCrypto count={8} section="calculator" />
        <div className="max-w-6xl mx-auto relative z-10">
          <div className="text-center mb-16">
            <h2 className="text-2xl sm:text-4xl md:text-5xl font-bold mb-3 sm:mb-4 text-gray-900 px-2">Calculate Your Returns</h2>
            <p className="text-lg text-gray-600 max-w-3xl mx-auto">
              See how much you can earn. Prime (5.25% net, instant) and Alpha (8.20% net, quarterly) tiers available now via Seamount. All fees included.
            </p>
          </div>
          
          <div className="grid lg:grid-cols-2 gap-6 sm:gap-8">
            {/* Left Calculator Panel */}
            <div className="glass-card rounded-2xl p-4 sm:p-8 shadow-sm">
              <h3 className="text-2xl font-bold mb-6 flex items-center text-gray-900">
                <DollarSign className="h-6 w-6 text-green-500 mr-2" />
                Your Investment
              </h3>
              
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Investment Amount (USD)</label>
                  <input 
                    type="number" 
                    value={calc.amount}
                    onChange={(e) => setCalc({...calc, amount: e.target.value})}
                    className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 text-lg focus:border-blue-600 focus:outline-none transition"
                    placeholder="10000"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Investment Tier</label>
                  <select 
                    value={calc.period}
                    onChange={(e) => setCalc({...calc, period: e.target.value})}
                    className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 text-lg focus:border-blue-600 focus:outline-none transition"
                  >
                    <option value="0">Prime Tier - 5.25% Net APY (Instant Liquidity)</option>
                    <option value="90">Alpha Tier - 8.20% Net APY (Quarterly Liquidity)</option>
                  </select>
                </div>

                <div className="bg-gray-50 rounded-xl p-4 border-2 border-gray-200">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm text-gray-600 flex items-center font-medium">
                      Fixed Rate Strategy
                      <button onClick={() => setShowFundingInfo(!showFundingInfo)} className="ml-1">
                        <Info className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                      </button>
                    </span>
                  </div>
                  {showFundingInfo && (
                    <div className="mb-3 p-3 bg-blue-50 rounded-lg text-xs text-gray-700 border border-blue-200">
                      {calc.period === '90' ? (
                        <><strong>Alpha Tier (Securitize Apollo Fund):</strong> Diversified credit fund targeting 10.9% gross APY. Managed by Apollo Global Management. Seamount charges 0.5% annual + 20% performance fee (approx. 2.70% total). Your net: 8.20% APY. Quarterly liquidity allows redemptions every 90 days.</>
                      ) : (
                        <><strong>Prime Tier (Hamilton Lane Fund):</strong> 6.57% gross APY. Targets senior secured loans and credit instruments for stable, risk-adjusted returns. Managed by Hamilton Lane with $150B+ AUM. Seamount charges 0.5% annual + 20% performance fee (1.32% total). Your net: 5.25% APY. Instant liquidity—withdraw anytime.</>
                      )}
                    </div>
                  )}
                  <div className="text-sm text-center py-4">
                    <div className="text-gray-400 mb-2">Fixed Strategy Components</div>
                    <div className="space-y-2">
                      {calc.period === '90' ? (
                        <>
                          <div className="flex justify-between items-center text-xs">
                            <span className="text-gray-500">Diversified Credit Fund</span>
                            <span className="text-blue-500 font-semibold">10.5-11.5%</span>
                          </div>
                          <div className="flex justify-between items-center text-xs">
                            <span className="text-gray-500">Management Fee</span>
                            <span className="text-gray-500 font-semibold">-2.00%</span>
                          </div>
                          <div className="flex justify-between items-center text-xs">
                            <span className="text-gray-500">Seamount Fee</span>
                            <span className="text-indigo-500 font-semibold">-2.70%</span>
                          </div>
                          <div className="flex justify-between items-center text-xs border-t border-gray-300 pt-2">
                            <span className="text-gray-900 font-medium">Your Net APY</span>
                            <span className="text-green-600 font-bold">8.20%</span>
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="flex justify-between items-center text-xs">
                            <span className="text-gray-500">Senior Secured Loans</span>
                            <span className="text-blue-500 font-semibold">7.5-8.5%</span>
                          </div>
                          <div className="flex justify-between items-center text-xs">
                            <span className="text-gray-500">Management Fee</span>
                            <span className="text-gray-500 font-semibold">-1.75%</span>
                          </div>
                          <div className="flex justify-between items-center text-xs">
                            <span className="text-gray-500">Seamount Fee</span>
                            <span className="text-indigo-500 font-semibold">-1.32%</span>
                          </div>
                          <div className="flex justify-between items-center text-xs border-t border-gray-300 pt-2">
                            <span className="text-gray-900 font-medium">Your Net APY</span>
                            <span className="text-green-600 font-bold">5.25%</span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Right Results Panel */}
            <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-2xl p-4 sm:p-8 border-2 border-blue-200 shadow-sm">
              <h3 className="text-2xl font-bold mb-6 flex items-center text-gray-900">
                <TrendingUp className="h-6 w-6 text-green-500 mr-2" />
                Estimated Returns
              </h3>

              <div className="bg-white rounded-xl p-6 mb-6 border-2 border-green-200 shadow-sm">
                <div className="text-center">
                  <div className="text-sm text-gray-600 mb-2 font-medium">Estimated Annual Yield (Net)</div>
                  <div className="text-5xl font-bold text-green-600 mb-2" suppressHydrationWarning>
                    ${yieldData.annualYield.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div className="text-lg text-gray-700 font-medium" suppressHydrationWarning>
                    ({(yieldData.adjustedAPY * 100).toFixed(2)}% Net APY)
                  </div>
                  <div className="mt-4 pt-4 border-t border-green-200">
                    <div className="text-sm text-gray-600 font-medium">
                      {calc.period === '0' ? 'Instant Liquidity' : 'Quarterly Return (90 days)'}
                    </div>
                    <div className="text-2xl font-semibold text-green-700 mt-1" suppressHydrationWarning>
                      {calc.period === '0' ? 'Available Anytime' : `$${yieldData.periodYield.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                  <div className="text-xs text-blue-700 font-medium mb-2">Fee Breakdown</div>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Gross Fund APY:</span>
                      <span className="font-semibold text-gray-900" suppressHydrationWarning>
                        {(yieldData.grossAPY * 100).toFixed(2)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Seamount Platform Fee:</span>
                      <span className="font-semibold text-indigo-600">0.50%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Performance Fee (20%):</span>
                      <span className="font-semibold text-indigo-600" suppressHydrationWarning>
                        {((yieldData.grossAPY * 0.20) * 100).toFixed(2)}%
                      </span>
                    </div>
                    <div className="flex justify-between pt-1 border-t border-blue-300">
                      <span className="text-gray-900 font-semibold">Total Seamount Fee:</span>
                      <span className="font-bold text-indigo-600" suppressHydrationWarning>
                        {(yieldData.seamountFee * 100).toFixed(2)}%
                      </span>
                    </div>
                    <div className="flex justify-between pt-1 border-t-2 border-green-300">
                      <span className="text-gray-900 font-bold">Your Net APY:</span>
                      <span className="font-bold text-green-600" suppressHydrationWarning>
                        {(yieldData.adjustedAPY * 100).toFixed(2)}%
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-700 font-medium">Fund Manager</span>
                  <span className="font-semibold text-indigo-600">
                    {calc.period === '90' ? 'Apollo Global' : 'Hamilton Lane'}
                  </span>
                </div>

                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-700 font-medium">Platform Partner</span>
                  <span className="font-semibold text-purple-600">Securitize Capital</span>
                </div>

                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-700 font-medium">Liquidity</span>
                  <span className="font-semibold text-green-600">
                    {calc.period === '0' ? 'Instant' : 'Quarterly'}
                  </span>
                </div>

                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-700 font-medium flex items-center">
                    Risk Score
                    <button onClick={() => setShowRiskDetails(!showRiskDetails)} className="ml-1">
                      <Info className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                    </button>
                  </span>
                  <span className={`font-semibold ${calc.period === '0' ? 'text-green-600' : 'text-amber-600'}`}>
                    {calc.period === '0' ? '35/100' : '55/100'}
                  </span>
                </div>

                {showRiskDetails && (
                  <div className="p-3 bg-white rounded-lg border-2 border-gray-200 text-xs text-gray-700">
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span>Credit Risk:</span>
                        <span className={calc.period === '0' ? 'text-green-600' : 'text-amber-600'}>
                          {calc.period === '0' ? 'Low (10 pts)' : 'Medium (20 pts)'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Market Risk:</span>
                        <span className="text-green-600">{calc.period === '0' ? '10 pts' : '15 pts'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Liquidity Risk:</span>
                        <span className="text-blue-600">{calc.period === '0' ? '15 pts' : '20 pts'}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-6 p-4 bg-amber-50 rounded-xl border-2 border-amber-200">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div className="text-xs text-gray-700">
                    <strong className="text-amber-700">Risk Disclosure:</strong> {
                      calc.period === '90' 
                        ? `Net APY ${(yieldData.adjustedAPY * 100).toFixed(2)}% for Apollo Diversified Credit Fund, after Seamount's 0.5% platform + ${((yieldData.grossAPY * 0.20) * 100).toFixed(2)}% performance fees (${(yieldData.seamountFee * 100).toFixed(2)}% total). Returns may include return of capital and vary with credit market conditions. Not FDIC-insured.`
                        : `Net APY ${(yieldData.adjustedAPY * 100).toFixed(2)}% for Hamilton Lane Senior Credit Fund, after Seamount's 0.5% platform + ${((yieldData.grossAPY * 0.20) * 100).toFixed(2)}% performance fees (${(yieldData.seamountFee * 100).toFixed(2)}% total). Returns may fluctuate with credit spreads. Not FDIC-insured.`
                    }
                  </div>
                </div>
                <div className="mt-4 p-3 bg-amber-50 rounded-lg border border-amber-200 text-xs">
                    <p className="font-medium text-amber-800 mb-1">Investment Services Note:</p>
                    <p className="text-amber-700">
                      Seamount operates investment services through licensed fund managers and partners. 
                      All investment products are managed by third-party licensed entities. 
                      Past performance does not guarantee future results.
                    </p>
               </div>
              </div>
            </div>
          </div>
        </div>
      </section>

       {/* Business Section WITH FORM */}
      <section id="business" className="py-12 sm:py-20 px-3 sm:px-6 relative overflow-hidden">
        <FloatingCrypto count={10} section="business" />
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="text-center mb-16">
            <h2 className="text-2xl sm:text-4xl md:text-5xl font-bold mb-3 sm:mb-4 text-gray-900 px-2">
              Join the Move <span className="gradient-text">On-Chain</span>
            </h2>
            <p className="text-lg text-gray-600 max-w-3xl mx-auto">
              Unlock permissionless 24/7 access to decentralized finance.
            </p>
          </div>
          
          <div className="grid lg:grid-cols-2 gap-8 sm:gap-12">
            {/* Business Solutions */}
            <div>
              <div className="glass-card rounded-2xl p-4 sm:p-8 mb-6 sm:mb-8">
                <Briefcase className="h-12 w-12 text-blue-600 mb-6" />
                <h3 className="text-2xl font-bold mb-6 text-gray-900">Business Solutions</h3>
                
                <div className="space-y-6">
                  {[
                    {
                      icon: "🏢",
                      title: "Asset Tokenization",
                      description: "Convert public and private company shares into 24/7 tradeable digital securities"
                    },
                    {
                      icon: "💸",
                      title: "Digital Treasury",
                      description: "Working capital management with 24/7 global payments, FX support, and yield generation"
                    },
                    {
                      icon: "🎯",
                      title: "Market Intelligence",
                      description: "Market data, on-chain analytics, and actionable insights to optimize your DeFi strategy"
                    },
                    {
                      icon: "🛡️",
                      title: "Real-Time AML & Fraud Detection",
                      description: "AI-powered transaction monitoring, pattern matching, and automated STR generation running entirely on-premise."
                    }
                  ].map((item, idx) => (
                    <div key={idx} className="flex items-start gap-4 p-4 hover:bg-gray-50 rounded-xl transition-colors">
                      <div className="text-2xl">{item.icon}</div>
                      <div>
                        <h4 className="font-bold text-gray-900 mb-1">{item.title}</h4>
                        <p className="text-gray-600 text-sm">{item.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Contact Info */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
                <div className="glass-card rounded-xl p-4 text-center">
                  <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-3">
                    <MapPin className="h-6 w-6 text-blue-600" />
                  </div>
                  <div className="text-sm font-medium text-gray-900">Our Office</div>
                  <div className="text-xs text-gray-600">Wood Avenue, Kilimani</div>
                </div>
                
                <div className="glass-card rounded-xl p-4 text-center">
                  <div className="w-12 h-12 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-3">
                    <Mail className="h-6 w-6 text-green-600" />
                  </div>
                  <div className="text-sm font-medium text-gray-900">Email Us</div>
                  <div className="text-xs text-gray-600">business@seamount.io</div>
                </div>
                
                <div className="glass-card rounded-xl p-4 text-center">
                  <div className="w-12 h-12 bg-purple-50 rounded-full flex items-center justify-center mx-auto mb-3">
                    <Phone className="h-6 w-6 text-purple-600" />
                  </div>
                  <div className="text-sm font-medium text-gray-900">Call Us</div>
                  <div className="text-xs text-gray-600">+254 751 875 374</div>
                </div>
              </div>
            </div>
            
            {/* Contact Form */}
            <div className="glass-card rounded-2xl p-4 sm:p-8 shadow-sm">
              <h3 className="text-2xl font-bold mb-6 text-gray-900">Get in Touch</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Your Name</label>
                  <input 
                    type="text"
                    value={formState.name}
                    onChange={(e) => setFormState({...formState, name: e.target.value})}
                    className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 text-sm focus:border-blue-600 focus:outline-none transition"
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
                    className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 text-sm focus:border-blue-600 focus:outline-none transition"
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
                    className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 text-sm focus:border-blue-600 focus:outline-none transition"
                    placeholder="john@company.com"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Message</label>
                  <textarea
                    value={formState.message}
                    onChange={(e) => setFormState({...formState, message: e.target.value})}
                    className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-300 rounded-xl text-gray-900 text-sm focus:border-blue-600 focus:outline-none transition resize-none"
                    rows={4}
                    placeholder="Tell us about your business needs..."
                    required
                  ></textarea>
                </div>
                <button
                  onClick={handleContactSubmit}
                  disabled={formStatus === 'sending'}
                  className="w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl hover:shadow-lg transition disabled:opacity-50"
                >
                  {formStatus === 'sending' ? 'Sending...' : formStatus === 'success' ? 'Message Sent!' : formStatus === 'error' ? 'Failed, Try Again' : 'Send Message'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-12 sm:py-20 px-3 sm:px-6 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-2xl sm:text-4xl md:text-5xl font-bold mb-3 sm:mb-4 text-gray-900 px-2">
              Frequently Asked Questions
            </h2>
            <p className="text-lg text-gray-600">
              Everything you need to know about Seamount
            </p>
          </div>
          
          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <div key={index} className="glass-card rounded-xl overflow-hidden">
                <button 
                  onClick={() => setExpandedFaqs(prev => 
                    prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]
                  )} 
                  className="w-full px-6 py-4 text-left flex items-center justify-between hover:bg-gray-50 transition-colors"
                >
                  <h3 className="font-semibold text-gray-900">{faq.question}</h3>
                  {expandedFaqs.includes(index) ? 
                    <ChevronUp className="h-5 w-5 text-blue-600" /> : 
                    <ChevronDown className="h-5 w-5 text-blue-600" />
                  }
                </button>
                {expandedFaqs.includes(index) && (
                  <div className="px-6 pb-4 border-t border-gray-100">
                    <p className="text-gray-700 pt-4 leading-relaxed">{faq.answer}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-12 sm:py-20 px-3 sm:px-6 relative overflow-hidden">
        <FloatingCrypto count={15} section="cta" />
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <div className="relative">
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl blur opacity-30"></div>
            <div className="relative glass-card rounded-3xl p-6 sm:p-12">
              <h2 className="text-2xl sm:text-4xl md:text-5xl font-bold mb-4 sm:mb-6 text-gray-900 px-2">
                Building an <span className="gradient-text">Ownership Economy</span> for Everyone
              </h2>
              <p className="text-lg text-gray-600 mb-8 max-w-2xl mx-auto">
                Join the platform where creatives and SMEs are the default users, not an afterthought.
              </p>
              <button 
                onClick={() => onOpenAuth('register')} 
                className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl hover:shadow-2xl hover:scale-105 transition-all duration-300"
              >
                Start Your Journey Today
              </button>
              <p className="mt-6 text-sm text-gray-500">
                Already part of the tribe?{' '}
                <button onClick={() => onOpenAuth('login')} className="text-blue-600 hover:underline font-semibold">
                  Sign In
                </button>
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-300 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center space-x-3 mb-4">
                <img src="/seamount-logo.jpeg" alt="Seamount Logo" className="w-10 h-10 object-contain rounded-lg" />
                <span className="text-xl font-bold text-white">Seamount</span>
              </div>
              <p className="text-gray-400 text-sm">Where creatives and SMEs become the economy's engine</p>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#services" className="hover:text-white transition">Features</a></li>
                <li><a href="#calculator" className="hover:text-white transition">Calculator</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#services" className="hover:text-white transition">Services</a></li>
                <li><a href="#business" className="hover:text-white transition">Business</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="/legal/privacy-policy.html" className="hover:text-white transition">Privacy Policy</a></li>
                <li><a href="/legal/terms-of-service.html" className="hover:text-white transition">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8 text-center text-sm">
            <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
              <p>© {new Date().getFullYear()} Seamount Technologies Ltd. All rights reserved.</p>
              <div className="flex gap-4">
                <div className="flex items-center text-sm"><Shield className="h-4 w-4 mr-1 text-green-400" /><span>Regulated</span></div>
                <div className="flex items-center text-sm"><Lock className="h-4 w-4 mr-1 text-blue-400" /><span>Self-Custody</span></div>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;