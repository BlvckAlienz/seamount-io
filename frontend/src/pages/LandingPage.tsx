import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Globe, Shield, Zap, DollarSign, TrendingUp, Check, Send, Twitter, Instagram, Mail, MapPin, Phone, ChevronDown, ChevronUp } from 'lucide-react';
import Button from '@/components/ui/Button';

// --- PROPS DEFINITION ---
interface LandingPageProps {
  onOpenAuth: (view: 'login' | 'register') => void;
}

// --- COOKIE PREFERENCES TYPE ---
interface CookiePreferences {
  functional: boolean; // Always true
  analytics: boolean;
  advertising: boolean;
}

const LandingPage: React.FC<LandingPageProps> = ({ onOpenAuth }) => {
  const navigate = useNavigate();
  const [expandedFaqs, setExpandedFaqs] = useState<number[]>([]);
  const [stakeAmount, setStakeAmount] = useState('10000');
  const [stakePeriod, setStakePeriod] = useState('365');
  const [rewards, setRewards] = useState('$450.00');
  const [formState, setFormState] = useState({ name: '', email: '', message: '' });
  const [formStatus, setFormStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle');

  // --- COOKIE CONSENT STATE ---
  const [showConsentBanner, setShowConsentBanner] = useState(false);
  const [showOptionsModal, setShowOptionsModal] = useState(false);
  const [cookieUnderPreferences, setCookiePreferences] = useState<CookiePreferences>({
    functional: true,
    analytics: true,
    advertising: true,
  });

    // --- COOKIE HELPER FUNCTIONS (CORRECTED) ---
  const getCookie = (name: string): string | null => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
    return null;
  };

  const setCookie = (name: string, value: string, days: number) => {
    let expires = "";
    if (days) {
      const date = new Date();
      date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
      expires = "; expires=" + date.toUTCString();
    }
    document.cookie = `${name}=${value || ""}${expires}; path=/; SameSite=Lax; Secure`;
  };

  const sendConsentToServer = async (preferences: CookiePreferences) => {
    try {
      // apiClient.post('/api/v1/consent/cookies', { preferences });
      console.log("Cookie consent recorded, ChevronDown } from 'lucide-react';
import Button from '@/components/ui/Button';

// ---.", preferences);
    } catch (error) {
      console.error("Failed to save cookie consent to server:", error PROPS DEFINITION ---
interface LandingPageProps {
  onOpenAuth: (view: 'login' | 'register') => void;
}

// --- COOKIE PREFERENCES TYPE ---
interface CookiePreferences {
  functional: boolean; //);
    }
  };

  useEffect(() => {
    const consent = getCookie('seamount_cookie Always true
  analytics: boolean;
  advertising: boolean;
}

const LandingPage: React.FC<LandingPageProps> = ({ onOpenAuth }) => {
  const navigate = useNavigate();
  const [_consent');
    if (!consent) {
      setTimeout(() => setShowConsentBanner(true), 1500);
    }expandedFaqs, setExpandedFaqs] = useState<number[]>([]);
  const [stakeAmount, setStakeAmount] = useState('10000');
  const [stakePeriod, setStakePeriod] = useState('365');
  const [rewards, setRewards] = useState('$450.00');
  const [form
  }, []);

  const handleApproveAll = () => {
    const allPrefs = { functional: true, analytics: true, advertising: true };
    setCookie('seamount_cookie_consent', JSON.stringify(allPrefs), 365);
    sendConsentToServer(allPrefs);
    setShowConsentBanner(false);
  };

  const handleOpenOptions = () => {
    setShowConsentBanner(false);
    setShowOptionsModal(true);
  };State, setFormState] = useState({ name: '', email: '', message: '' });
  const [formStatus, setFormStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('
  
  const handleSavePreferences = () => {
    setCookie('seamount_cookie_consent', JSON.stringify(cookiePreferences), 365);
    sendConsentToServer(cookiePreferences);
    setShowOptionsModal(false);
  };


  const toggleFaq = (index: number) => {
    setExpandedFaqs(prev => prev.includesidle');

  // --- COOKIE CONSENT STATE ---
  const [showConsentBanner, setShowConsentBanner] = useState(false);
  const [showOptionsModal, setShowOptionsModal] = useState(false);
  const [cookiePreferences, setCookiePreferences] = useState<CookiePreferences>({
    functional: true,
    analytics: true,
    advertising: true,
  });

  // --- COOKIE HELPER FUNCTIONS (CORRECTED) ---
  const getCookie = (name: string): string | null => {
    const value = `; ${document.cookie}`;
    const parts = value.split((index) ? prev.filter(i => i !== index) : [...prev, index]);
  };

  const calculateYield = useCallback(() => {
    const amount = parseFloat(stakeAmount) || 0;
    let apy = 0.045;
    if (stakePeriod === '30') apy = 0.035;
    else if (stakePeriod === '90') apy = 0.040;
    else if`; ${name}=`);
    if (parts.length === 2) return parts.pop()?.split(' (stakePeriod === '180') apy = 0.042;
    const annualYield;').shift() || null;
    return null;
  };

  const setCookie = (name: string, value: string, days: number) => {
    let expires = "";
    if (days) {
      const date = amount * apy;
    setRewards(`$${annualYield.toLocaleString(undefined, { minimumFractionDigits = new Date();
      date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
      expires = "; expires=" + date.toUTCString();
    : 2, maximumFractionDigits: 2 })}`);
  }, [stakeAmount, stakePeriod]);

  useEffect}
    document.cookie = `${name}=${value || ""}${expires}; path=/; SameSite=Lax; Secure(() => {
    calculateYield();
  }, [calculateYield]);

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormStatus('sending');
    try {
      const response = await fetch('/api/v1/investor-contact', {
        method: 'POST',
        headers`;
  };

  const sendConsentToServer = async (preferences: CookiePreferences) => {
    try {
      // apiClient.post('/api/v1/consent/cookies', { preferences });
      console.log("Cookie consent recorded: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formState)
      });
      if (!response.ok) throw new Error(`Network response was not ok: ${response.statusText}`);
      setFormStatus('success');
      setFormState({ name: '', email: '', message: '' });
      setTimeout.", preferences);
    } catch (error) {
      console.error("Failed to save cookie consent to server:", error);
    }
  };

  useEffect(() => {
    const consent = getCookie('seamount(() => setFormStatus('idle'), 3000);
    } catch (error) {
      console._cookie_consent');
    if (!consent) {
      setTimeout(() => setShowConsentBanner(true), 1500);
    }
  }, []);

  const handleApproveAll = () => {
    consterror('Contact form submission error:', error);
      setFormStatus('error');
      setTimeout(() => setFormStatus('idle'), 3000);
    }
  };

  useEffect(() => {
    const observer = new allPrefs = { functional: true, analytics: true, advertising: true };
    setCookie('seamount_cookie_consent', JSON.stringify(allPrefs), 365);
    sendConsentToServer(allPrefs);
    setShowConsentBanner(false IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) entry.target.classList.add('visible');
      });
    }, { threshold: 0.1);
  };

  const handleOpenOptions = () => {
    setShowConsentBanner(false);
    setShowOptionsModal(true);
  };
  
  const handleSavePreferences = () => {
    setCookie('seamount_cookie_consent', JSON.stringify(cookiePreferences), 365);
    sendConsentToServer(cookiePreferences);
    setShowOptionsModal( });
    const elements = document.querySelectorAll('.fade-in');
    elements.forEach(el => observer.observe(el));
    return () => elements.forEach(el => observer.unobserve(el));
  },false);
  };


  const toggleFaq = (index: number) => {
    setExpandedFaqs( []);

  const faqs = [
    { question: "How fast are Seamount cross-border transfers?", answerprev => prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]);
  };

  const calculateYield = useCallback(() => {
    const amount = parseFloat(stakeAmount) || 0;
: "Seamount transfers settle within seconds, not days. Our blockchain technology, powered by Algorand, enables instant    let apy = 0.045;
    if (stakePeriod === '30') apy = 0.035;
    else if (stakePeriod === '90') apy = 0.040;
    else if (stakePeriod === '180') apy = 0.042;
    const annualYield = amount settlement across borders, dramatically faster than traditional banking which can take 3-5 business days." },
    { question: "What * apy;
    setRewards(`$${annualYield.toLocaleString(undefined, { minimumFractionDigits:  are the fees for using Seamount?", answer: "Our fees are typically just 2.6-3.8%2, maximumFractionDigits: 2 })}`);
  }, [stakeAmount, stakePeriod]);

  useEffect(() => {
    calculateYield();
  }, [calculateYield]);

  const handleContactSubmit = async (e: React.FormEvent per transaction, compared to 12-15% with traditional banks. There are no hidden fees or exchange rate) => {
    e.preventDefault();
    setFormStatus('sending');
    try {
      const response = await fetch('/api/v1/investor-contact', {
        method: 'POST',
         markups." },
    { question: "Is USDS stablecoin regulated and secure?", answer: "Yes, USDS is fully compliant with local regulations and maintains a 1:1 USD peg. All USDS tokens are fully backedheaders: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formState)
      }); by USD reserves, ensuring stability and security." },
    { question: "Which African countries are supported?", answer: "We
      if (!response.ok) throw new Error(`Network response was not ok: ${response.statusText}`);
      setFormStatus('success');
      setFormState({ name: '', email: '', message: '' });
      setTimeout(() => setFormStatus('idle'), 3000);
    } catch (error) {
      console. currently support 60+ countries including US, Nigeria, South Africa, Kenya, Ghana, Uganda, with more countrieserror('Contact form submission error:', error);
      setFormStatus('error');
      setTimeout(() => setFormStatus('idle'), 3000);
    }
  };

  useEffect(() => {
    const observer = new being added regularly. Our platform integrates with local payment methods including Flutterwave, Paystack, and bank transfers." }
  ];

  return IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) entry.target.classList.add('visible');
      });
    }, { threshold: 0.1 (
    <div className="min-h-screen bg-gray-950 text-white selection: });
    const elements = document.querySelectorAll('.fade-in');
    elements.forEach(el => observer.observe(el));
    return () => elements.forEach(el => observer.unobserve(el));
  },bg-blue-500/30">
      <nav className="bg-black/60 backdrop []);

  const faqs = [
    { question: "How fast are Seamount cross-border transfers?", answer-blur-lg sticky top-0 z-50 border-b border-gray-800/6: "Seamount transfers settle within seconds, not days. Our blockchain technology, powered by Algorand, enables instant0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3">
          <div className="flex items-center justify-between">
            <a href="/" className="flex settlement across borders, dramatically faster than traditional banking which can take 3-5 business days." },
    { question: "What items-center space-x-3"><img src="/seamount-logo.png" alt="Seamount Logo are the fees for using Seamount?", answer: "Our fees are typically just 2.6-3.8%" className="w-10 h-10 object-contain filter drop-shadow-lg rounded-md" />< per transaction, compared to 12-15% with traditional banks. There are no hidden fees or exchange rate markups." },
    { question: "Is USDS stablecoin regulated and secure?", answer: "Yes,span className="text-xl font-bold bg-gradient-to-r from-blue-400 via USDS is fully compliant with local regulations and maintains a 1:1 USD peg. All USDS tokens are fully backed-white to-gray-300 bg-clip-text text-transparent">Seamount.io</span></a>
            <div className="hidden by USD reserves, ensuring stability and security." },
    { question: "Which African countries are supported?", answer: "We md:flex items-center space-x-8"><a href="#features" className="text-gray-300 hover:text-white transition-colors">Features</a><a href="#stablecoin" className="text-gray-30 currently support 60+ countries including US, Nigeria, South Africa, Kenya, Ghana, Uganda, with more countries0 hover:text-white transition-colors">USDS</a><a href="#about" className="text-gray-300 hover:text-white transition-colors">About</a><a href="#contact" className="text-gray-300 hover:text-white transition-colors">Contact</a></div>
            <div className="flex items being added regularly. Our platform integrates with local payment methods including Flutterwave, Paystack, and bank transfers." }
  ];

  return-center space-x-2"><Button variant="ghost" onClick={() => onOpenAuth('login')}>Sign In</Button><Button onClick={() => onOpenAuth('register')} className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 (
    <div className="min-h-screen bg-gray-950 text-white selection:" elevated>Sign Up</Button></div>
          </div>
        </div>
      </nav>

      <mainbg-blue-500/30">
      <nav className="bg-black/60 backdrop>
        <section className="relative py-20 md:py-32 overflow-hidden">
          <div-blur-lg sticky top-0 z-50 border-b border-gray-800/6 className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2Zy0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3">
          <div className="flex items-center justify-between">
            <a href="/" className="flexB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZX items-center space-x-3">
              <img src="/seamount-logo.png" alt="Seamount Logo" className="w-10 h-10 object-contain filter drop-shadow-lg rounded-md" />
              <span className="text-xl font-bold bg-gradient-to-r fromdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA-blue-400 via-white to-gray-300 bg-clip-text text-transparent6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0">Seamount.io</span>
            </a>
            <div className="hidden md:flex items-center space-x-8"><a href="#features" className="text-gray-300 hover:text-white transition-colors">Features</a><a href="#stablecoin" className="text-gray-300 hover:text-white transition-aCBkPSJNNTkuNSA2MEgwVjBoNjBWNjBoLS41ek0colors">USDS</a><a href="#about" className="text-gray-300 hover:text-white transition-colors">About</a><a href="#contact" className="text-gray-300 hover:text-white transition-colors">Contact</a></div>
            <div className="flex items-center space-x-2"><Button variant="ghost" onClick={() => onOpenAuth('login')}>Sign In</Button><Button onClick={() => onOpenAuth('registerxIDF2NThoNTguMDAxVjFIMXoiIGZpbGw9IiMyM')} className="bg-gradient-to-r from-blue-600 to-purple-600 hoverDIwMjAiIG9wYWNpdHk9IjAuMiIgZmlsbC1ydW:from-blue-700 hover:to-purple-700" elevated>Sign Up</Button></div>
          </div>
        </div>
      </nav>

      <main>
        <section className="relative py-20 md:py-32 overflow-hidden">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWRxlPSJldmVub2RkIi8+PC9zdmc+')] bg-[length:30px_30px] opacity-20"></div>
          <div className="absolute -top-40 -right0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g-40 w-80 h-80 bg-blue-500/10 rounded-full9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly9 blur-3xl animate-pulse"></div>
          <div className="absolute top-1/4 left-1/3 w-60 h-60 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
            <div className="text-center max-w-43d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBxl mx-auto">
              <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold mb-6 bg-gradient-to-r from-blue-400 via-white to-purple-300 bg-clip-text text-transparent tracking-tighter">The Future of Cross-Border Payments is Here</h1>
              <p className="text-lg sm:text-xl text-gray-300 mbkPSJNNTkuNSA2MEgwVjBoNjBWNjBoLS41ek0xIDF-10 leading-relaxed">Experience instant, low-cost P2P and B2B transfers powered by Stablecoin tech. Built for the financial realities of emerging African markets.</p>
              <div className="flex flex-col2NThoNTguMDAxVjFIMXoiIGZpbGw9IiMyMDIw sm:flex-row justify-center gap-4 mb-12"><Button onClick={() => onOpenAuth('register')} size="lg" className="px-8 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700" icon={ArrowRight} elevated animated>Get Started for Free</Button><Button size="lg" variant="outline" onClick={() => documentMjAiIG9wYWNpdHk9IjAuMiIgZmlsbC1ydWxlPS.getElementById('features')?.scrollIntoView()} elevated>Learn More</Button></div>
              <div className="flex flex-wrapJldmVub2RkIi8+PC9zdmc+')] bg-[length:30px_ justify-center gap-x-6 gap-y-2 text-sm text-gray-400"><div className="flex items-center"><Shield className="h-4 w-4 mr-1.5 text-green30px] opacity-20"></div>
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full-400" /><span>Bank-level security</span></div><div className="flex items-center"><Zap className="h-4 w-4 mr-1.5 text-yellow-400" /><span>Sub-second settlements</span></div><div className="flex items-center"><DollarSign className="h-4 w-4 mr-1.5 text-blue-400" /><span> blur-3xl animate-pulse"></div>
          <div className="absolute top-1/4 left-1/3 w-60 h-60 bg-purple-500/10 rounded-full blur-3xlUp to 87% lower fees</span></div></div>
            </div>
          </div>
        </section>

        <section id="features" className="py-20 bg-gray-950/40 backdrop-blur-sm animate-pulse delay-1000"></div>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
            <div className="text-center max-w-4">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-16 fade-in"><h2 className="text-3xl mx-auto">
              <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold mb-6 bg-gradient-to-r from-blue-400 via-whitexl md:text-4xl font-bold mb-4">Revolutionizing Financial Access</h2><p className="text-gray-400 max-w-2xl mx-auto">Our platform is designed to solve real-world challenges of cross to-purple-300 bg-clip-text text-transparent tracking-tighter">The Future of Cross-Border Payments is Here</h1>
              <p className="text-lg sm:text-xl text-gray-300 mb-border payments for emerging African markets.</p></div>
            <div className="grid grid-cols-1 md:grid-10 leading-relaxed">Experience instant, low-cost P2P and B2B transfers powered by Stable-cols-2 lg:grid-cols-3 gap-8">
              {[ { icon: <Send className="h-8 w-8 text-blue-500" />, title: "Instant Transfers", description: "Sendcoin tech. Built for the financial realities of emerging African markets.</p>
              <div className="flex flex-col sm:flex-row justify-center gap-4 mb-12"><Button onClick={() => onOpenAuth('register money globally in minutes, not days. Our blockchain technology, powered by Algorand, enables immediate settlement across borders." }, { icon: <DollarSign className="h-8 w-8 text-green-500" />, title: "Ultra-')} size="lg" className="px-8 bg-gradient-to-r from-blue-600 to-purpleLow Fees", description: "Pay pennies, not percentages. Save up to 87% compared to traditional banks and remittance services." }, { icon: <Shield className="h-8 w-8 text-purple-500" />, title:-600 hover:from-blue-700 hover:to-purple-700" icon={ArrowRight} elevated animated>Get Started for Free</Button><Button size="lg" variant="outline" onClick={() => document "USDS Stablecoin", description: "Our fully-reserved, USD-pegged stablecoin ensures stable value and offers staking rewards." }, { icon: <TrendingUp className="h-8 w-8 text-yellow-5.getElementById('features')?.scrollIntoView()} elevated>Learn More</Button></div>
              <div className="flex flex-wrap00" />, title: "AI-Powered Trading", description: "Let AI optimize your investment portfolio with advanced algorithmic justify-center gap-x-6 gap-y-2 text-sm text-gray-400"><div className="flex items-center"><Shield className="h-4 w-4 mr-1.5 text-green trading and risk management." }, { icon: <Zap className="h-8 w-8 text-red-500" />,-400" /><span>Bank-level security</span></div><div className="flex items-center"><Zap className="h-4 w-4 mr-1.5 text-yellow-400" /><span>Sub-second settlements</span></div><div className="flex items-center"><DollarSign className="h-4 w-4 mr-1.5 text-blue-400" /><span> title: "Staking Rewards", description: "Earn competitive yields by holding USDS tokens. The longer you stake, the higher your returns." }, { icon: <Globe className="h-8 w-8 text-teal-500" />, title: "African-First Design", description: "Built for African markets with integration for Flutterwave, Paystack, bank transfers, and mobileUp to 87% lower fees</span></div></div>
            </div>
          </div>
        </section>

        <section id="features" className="py-20 bg-gray-950/40 backdrop-blur-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6"> money." } ].map((feature, index) => (<div key={index} className="p-6 bg-gradient-to-br from-gray-900/50 to-gray-800/30 rounded-xl border
            <div className="text-center mb-16 fade-in"><h2 className="text-3xl md:text-4xl font-bold mb-4">Revolutionizing Financial Access</h2><p className="text-gray-4 border-gray-800/80 hover:border-blue-700/50 transition-all duration-300 shadow-xl backdrop-blur-sm hover:-translate-y-2 fade-in"><div className="rounded-full w-14 h-14 flex items-center justify-center bg-gray-800/800 max-w-2xl mx-auto">Our platform is designed to solve real-world challenges of cross-border payments for emerging African markets.</p></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {[ { icon: <Send className0 mb-5 border border-gray-700/50 shadow-inner">{feature.icon}</div><h3 className="text-xl font-bold mb-3 text-white">{feature.title}</h3><p className="text-="h-8 w-8 text-blue-500" />, title: "Instant Transfers", description: "Send money globally in minutes, not days. Our blockchain technology, powered by Algorand, enables immediate settlement across borders." }, { icon:gray-400">{feature.description}</p></div>))}
            </div>
          </div>
        </section>
        
        <section id="about" className="py-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-16 fade-in"><h2 className="text-3xl md:text-4xl font-bold mb-4">About <DollarSign className="h-8 w-8 text-green-500" />, title: "Ultra-Low Fees", description: "Pay pennies, not percentages. Save up to 87% compared to traditional banks and Seamount</h2><p className="text-gray-400 max-w-2xl mx-auto">A stablecoin network that bridges traditional finance and Web3 to democratize financial access for emerging African markets.</p></div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center"> remittance services." }, { icon: <Shield className="h-8 w-8 text-purple-500" />, title: "USDS Stablecoin", description: "Our fully-reserved, USD-pegged stablecoin ensures stable value and offers staking rewards." }, { icon: <TrendingUp className="h-8 w-8 text-yellow-500" />, title: "
              <div className="fade-in"><div className="mb-8"><h3 className="text-2xl font-bold mb-4 text-white">Our Mission</h3><p className="text-gray-300 leading-relaxed">Seamount is on a mission to transform cross-border payments in emerging African markets. We're buildingAI-Powered Trading", description: "Let AI optimize your investment portfolio with advanced algorithmic trading and risk management." }, { icon: <Zap className="h-8 w-8 text-red-500" />, title: "Staking Rewards", description: " a stablecoin infrastructure that enables instant, low-cost transfers between countries, making financial services accessible to everyone regardless of location.</p></div></div>Earn competitive yields by holding USDS tokens. The longer you stake, the higher your returns." }, { icon: <Globe className="h-8 w-8 text-teal-500" />, title: "African-First Design", description: "Built for African markets with integration for Flutterwave, Paystack, bank transfers, and mobile money." } ].
              <div className="fade-in"><div className="grid grid-cols-2 gap-4"><div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50"><div className="text-3xl font-bold text-blue-400">6map((feature, index) => (<div key={index} className="p-6 bg-gradient-to-br from-gray-900/50 to-gray-800/30 rounded-xl border0+</div><div className="text-gray-400">Countries Reached</div></div><div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50"><div className="text-3xl font-bold text-purple-400">500K border-gray-800/80 hover:border-blue-700/50 transition-all USDS</div><div className="text-gray-400">Total Token Supply</div></div><div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/ duration-300 shadow-xl backdrop-blur-sm hover:-translate-y-2 fade-in"><div className="rounded-full w-14 h-14 flex items-center justify-center bg-gray-800/850"><div className="text-3xl font-bold text-green-400">87%</div><div className="text0 mb-5 border border-gray-700/50 shadow-inner">{feature.icon}</div><h-gray-400">Cost Savings</div></div><div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50"><div className="text-3xl font-bold text-yellow-400">1.5K+</div><div className="text-gray-4003 className="text-xl font-bold mb-3 text-white">{feature.title}</h3><p className="text-gray">Projected Users (3-6 months)</div></div></div></div>
            </div>
          </div>
        </section>

        <section id="stablecoin" className="py-20 relative overflow-hidden bg-gray-950/40 backdrop-blur-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z--400">{feature.description}</p></div>))}
            </div>
          </div>
        </section>
        
        <section id="about" className="py-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-16 fade-in"><h2 className="text-3xl md:text-4xl font-bold mb-4">About10">
                <div className="text-center mb-16 fade-in"><h2 className="text-3xl md Seamount</h2><p className="text-gray-400 max-w-2xl mx-auto">A stablecoin network that bridges traditional finance and Web3 to democratize financial access for emerging African markets.</p></div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">:text-4xl font-bold mb-4">Meet USDS - Your Gateway to Stablecoins Network</h2><p className="text-gray-400 max-w-2xl mx-auto">A stable digital currency that powers cross-border transactions
              <div className="fade-in"><div className="mb-8"><h3 className="text-2 with the security of blockchain technology.</p></div>
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-center">
                    <div className="lg:col-span-3 bg-gradient-to-brxl font-bold mb-4 text-white">Our Mission</h3><p className="text-gray-300 leading-relaxed from-blue-900/30 to-blue-800/10 rounded-xl p-8 border border-blue-700/30 backdrop-blur-sm fade-in">
                        <h3">Seamount is on a mission to transform cross-border payments in emerging African markets. We're building a stablecoin infrastructure that enables instant, low-cost transfers between countries, making financial services accessible to everyone regardless of location.</p></div></div>
              <div className="fade-in"><div className="grid grid-cols-2 gap-4"><div className="text-2xl font-bold mb-6 text-blue-300">1:1 USD Peg & Transparency</h3><p className="text-gray-300 mb-4">USDS maintains a stable value pegged className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50"><div className="text-3xl font-bold text-blue-400">60+</div><div 1:1 to the US Dollar, ensuring your money retains its value during cross-border transfers.</p><ul className="space className="text-gray-400">Countries Reached</div></div><div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50"><div className="text-3xl font-bold text-purple-400">500K USDS</div><div className="text-gray--y-3 text-gray-300">{[ "Fully backed by audited USD reserves", "Regulated and400">Total Token Supply</div></div><div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50"><div className="text-3xl font-bold text-green-400">87%</div><div className="text-gray-400">Cost Savings</div></div><div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/ compliant across jurisdictions", "Regular public attestations ensure transparency", "Instant settlement on the Algorand network" ].map((feature, i50"><div className="text-3xl font-bold text-yellow-400">1.5K+</div><div className) => (<li key={i} className="flex items-start"><Check className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" /><span>{="text-gray-400">Projected Users (3-6 months)</div></div></div></div>
            </div>
          </div>
        </section>

        <section id="stablecoin" className="py-20 relative overflow-hidden bg-gray-950/40 backdrop-blur-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
                <div className="text-center mb-16 fade-in"><h2 className="text-3xl md:text-4xl font-bold mb-4">Meet USDS -feature}</span></li>))}</ul>
                    </div>
                    <div className="lg:col-span-2 bg-gradient-to-br from-gray-900/50 to-gray-800/30 rounded-xl p-8 border border-gray-800/80 backdrop-blur-sm fade-in">
                        <h3 className="text-xl Your Gateway to Stablecoins Network</h2><p className="text-gray-400 max-w-2xl mx-auto"> font-bold mb-4 text-center">Yield Calculator</h3><div className="space-y-4"><div><labelA stable digital currency that powers cross-border transactions with the security of blockchain technology.</p></div>
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-center">
                    <div className="lg:col htmlFor="stake-amount" className="text-sm text-gray-400">Investment Amount</label><input-span-3 bg-gradient-to-br from-blue-900/30 to-blue-8 id="stake-amount" name="stake-amount" type="number" value={stakeAmount} onChange={(e) => setStakeAmount(e.target.value)} className="w-full mt-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" /></div><div><label htmlFor="stake-period00/10 rounded-xl p-8 border border-blue-700/30 backdrop-blur-sm fade-in">
                        <h3 className="text-2xl font-bold mb-6 text-blue-300">1:1 USD Peg & Transparency</h3><p className="text-gray-300 mb-4" className="text-sm text-gray-400">Period</label><select id="stake-period" name="stake-period" value={stakePeriod} onChange={(e) => setStakePeriod(e.target.value)} className="w-full mt-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded">USDS maintains a stable value pegged 1:1 to the US Dollar, ensuring your money retains its value during cross-border transfers.</p><ul className="space-y-3 text-gray-300">{[-lg text-white"><option value="30">1 Month (3.5% APY)</option><option value="90">3 Months (4.0% APY)</option><option value="180">6 Months (4.2% APY)</option><option value="365">1 Year (4.5% APY)</option></select></div><div className="bg-gradient-to-r from-green-600 to-teal "Fully backed by audited USD reserves", "Regulated and compliant across jurisdictions", "Regular public attestations ensure transparency", "Instant-600 rounded-lg p-4 text-center"><div className="text-2xl font-bold">{rewards}</div><div className="text-sm opacity-80">Estimated Annual Yield</div></div></div>
                    </div>
                </div>
            </div>
        </section>

        <section id="contact" className="py-20"> settlement on the Algorand network" ].map((feature, i) => (<li key={i} className="flex items-start
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-16 fade-in"><h2 className="text-3"><Check className="h-5 w-5 text-green-500 mr-2 mt-0.5 flexxl md:text-4xl font-bold mb-4">Get in Touch</h2><p className="text-gray-400 max-w-2xl mx-auto">Have questions or interested in investing? Our team is here to help.</p></div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8-shrink-0" /><span>{feature}</span></li>))}</ul>
                    </div>
                    <div className="lg:col-span-2 bg-gradient-to-br from-gray-900/50 to-gray">
              <div className="space-y-6 fade-in">{[ { icon: <MapPin className="h-6 w-6 text-blue-500 flex-shrink-0 mt-1" />, title: "Our-800/30 rounded-xl p-8 border border-gray-800/80 backdrop-blur-sm fade-in">
                        <h3 className="text-xl font-bold mb-4 text-center">Yield Address", detail: "Wood Avenue, Kilimani, Nairobi, Kenya" }, { icon: <Mail className="h-6 w-6 text-green-500 flex-shrink-0 mt-1" />, title: "Email Us", detail: "support@seamount.io" }, { icon: <Phone className="h-6 w-6 text-purple-500 flex-shrink- Calculator</h3><div className="space-y-4"><div><label htmlFor="stake-amount" className="text-sm0 mt-1" />, title: "Call Us", detail: "+254 751 8 text-gray-400">Investment Amount</label><input id="stake-amount" name="stake-amount" type="number" value={stakeAmount} onChange={(e) => setStakeAmount(e.target.value)} className="w-full mt-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded75 374" } ].map((item, i) => (<div key={i} className="flex items-start space-x-4"><div className="p-3 bg-gray-800/50 rounded-full">{item.icon}</div><div><h3 className="font-semibold text-lg text-white mb-lg text-white" /></div><div><label htmlFor="stake-period" className="text-sm text-gray-400">Period</label><select id="stake-period" name="stake-period" value={stakePeriod} onChange={(e) => setStakePeriod(e.target.value)} className="w-full mt-1 px-4 py-2 bg-gray-800 border-1">{item.title}</h3><p className="text-gray-300">{item.detail}</p></div></div> border-gray-700 rounded-lg text-white"><option value="30">1 Month (3.))}</div>
              <div className="fade-in"><form onSubmit={handleContactSubmit} className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 rounded-xl border border-gray-800/80 p-6 backdrop-blur-sm"><h3 className="text-xl font-bold mb5% APY)</option><option value="90">3 Months (4.0% APY)</option><option value="180">6 Months (4.2% APY)</option><option value="365">1-4">Send Us a Message</h3><div className="space-y-4"><div><label htmlFor="contact-name" className="block text-sm font-medium text-gray-300 mb-1">Your Year (4.5% APY)</option></select></div><div className="bg-gradient-to-r from-green-600 to-teal-600 rounded-lg p-4 text-center"><div className="text-2xl font-bold">{rewards}</div><div className="text-sm opacity-80">Estimated Annual Yield</div></div></div>
                    </div>
                </div>
            </div>
        </section>

        <section id="contact" className="py-20">
          <div className="max-w-7xl mx-auto px-4 sm:px- Name</label><input id="contact-name" name="name" type="text" value={formState.name} onChange={(e) => setFormState({...formState, name: e.target.value})} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg"6">
            <div className="text-center mb-16 fade-in"><h2 className="text-3xl md:text-4xl font-bold mb-4">Get in Touch</h2><p className="text-gray-400 max-w placeholder="Full Name" required /></div><div><label htmlFor="contact-email" className="block text-sm font-medium text-gray-300 mb-1">Email Address</label><input id="contact-email" name="email" type="email" value={formState.email} onChange={(e) => setFormState({...formState,-2xl mx-auto">Have questions or interested in investing? Our team is here to help.</p></div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-6 fade-in">{[ { icon: <MapPin className="h-6 w-6 text-blue email: e.target.value})} className="w-full px-4 py-2 bg-gray-8-500 flex-shrink-0 mt-1" />, title: "Our Address", detail: "Wood00 border border-gray-700 rounded-lg" placeholder="Email" required /></div><div><label htmlFor="contact-message" className="block text-sm font-medium text-gray-300 mb-1">Message</label Avenue, Kilimani, Nairobi, Kenya" }, { icon: <Mail className="h-6 w-6 text-green-500 flex-shrink-0 mt-1" />, title: "Email Us", detail: "support@seamount.io" }, { icon: <Phone><textarea id="contact-message" name="message" value={formState.message} onChange={(e) => set className="h-6 w-6 text-purple-500 flex-shrink-0 mt-1"FormState({...formState, message: e.target.value})} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg resize-none" rows={4} placeholder="Your message" required></textarea></div><Button type="submit" loading={formStatus === 'sending'} className="w-full bg-gradient-to- />, title: "Call Us", detail: "+254 751 875 374" } ].map((item, i) => (<div key={i} className="flex items-start space-x-4"><div className="p-3 bg-gray-800/50 rounded-full">{item.icon}</div><div>r from-blue-600 to-purple-600">{formStatus === 'success' ? 'Message Sent!' : formStatus === 'error' ? 'Failed, Try Again' : 'Send Message'}</Button></div></<h3 className="font-semibold text-lg text-white mb-1">{item.title}</h3><p className="text-gray-300">{item.detail}</p></div></div>))}</div>
              <div className="fadeform></div>
            </div>
          </div>
        </section>

        <section className="py-20 bg-in"><form onSubmit={handleContactSubmit} className="bg-gradient-to-br from-gray-900/50 to-gradient-to-r from-blue-900/20 to-purple-900/20">-gray-800/30 rounded-xl border border-gray-800/80 p-6
          <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
            <div className="max-w-3xl mx-auto"><h2 className="text-3xl md:text backdrop-blur-sm"><h3 className="text-xl font-bold mb-4">Send Us a Message</h3><div className="space-y-4"><div><label htmlFor="contact-name" className="block text-sm font-medium text-gray-300 mb-1">Your Name</label><input id="contact-name" name="name-4xl font-bold mb-6">Ready to Transform Your Cross-Border Payments?</h2><Button size="lg" onClick={() => onOpenAuth('register')} className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-70" type="text" value={formState.name} onChange={(e) => setFormState({...formState, name: e.target.value})} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg" placeholder="Full Name" required /></div><div><label htmlFor="contact-email" className="block text-sm font-medium text-gray-300 mb-1">Email0 text-lg" elevated animated>Sign Up for Free</Button><p className="mt-4 text-sm text-gray-40 Address</label><input id="contact-email" name="email" type="email" value={formState.email}0">Already have an account? <button onClick={() => onOpenAuth('login')} className="text-blue-400 hover onChange={(e) => setFormState({...formState, email: e.target.value})} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg" placeholder="Email" required /></div><div><label htmlFor="contact-message" className="block text-sm font-medium text-gray-3:underline font-semibold">Sign In</button></p></div>
          </div>
        </section>
      </main>

      <footer00 mb-1">Message</label><textarea id="contact-message" name="message" value={formState. className="bg-gray-950 border-t border-gray-800/60 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <message} onChange={(e) => setFormState({...formState, message: e.target.value})} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg resize-none"div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div> rows={4} placeholder="Your message" required></textarea></div><Button type="submit" loading={formStatus === 'sending'} className="w-full bg-gradient-to-r from-blue-600 to-purple-600">{
              <div className="flex items-center space-x-3 mb-4"><img src="/seamount-logo.png" alt="Seamount Logo" className="w-8 h-8 object-contain filter drop-shadow-lg rounded-md" /><span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-grayformStatus === 'success' ? 'Message Sent!' : formStatus === 'error' ? 'Failed, Try Again' : 'Send Message'}</Button></div></form></div>
            </div>
          </div>
        </section>

        <section className-300 bg-clip-text text-transparent">Seamount.io</span></div><p className="text-gray-400 text-sm">The future of cross-border payments for emerging markets</p>
            </div>
            <div>="py-20 bg-gradient-to-r from-blue-900/20 to-purple-900/20">
          <div className="max-w-7xl mx-auto px
              <h4 className="text-white font-medium mb-4">Product</h4>
              <ul className="space-y-4 sm:px-6 text-center">
            <div className="max-w-3xl mx-auto"><h2 className-2 text-sm"><li><a href="#features" className="text-gray-400 hover:text-white">Features</a></li><li><a href="#stablecoin" className="text-gray-400 hover:text-white">USDS Stablecoin</a></li><li><a href="#" className="text-gray-400 hover:text-white">API="text-3xl md:text-4xl font-bold mb-6">Ready to Transform Your Cross-Border Payments? Documentation</a></li><li><a href="#" className="text-gray-400 hover:text-white">Security</a></li></ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-4">Company</h4>
              <ul className="space-y-2 text-sm"><li><a href="#about" className="text</h2><Button size="lg" onClick={() => onOpenAuth('register')} className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-lg" elevated animated>Sign Up for Free</Button><p className="mt-4 text-sm text-gray-400">Already have an account? <button onClick-gray-400 hover:text-white">About Us</a></li><li><a href="#" className="text-gray-400 hover:text-white">Careers</a></li><li><a href="#" className="text-gray-400 hover:text-white">Blog</a></li><li><a href="#contact" className="text-gray-400 hover:text-white">Contact</a></li></ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-4">={() => onOpenAuth('login')} className="text-blue-400 hover:underline font-semibold">Sign In</button></p></div>
          </div>
        </section>
      </main>

      <footer className="bgLegal</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="/legal/privacy-policy" className="text-gray-400 hover:text-white">Privacy Policy</a></li>-gray-950 border-t border-gray-800/60 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div
                <li><a href="/legal/terms-of-service" className="text-gray-400 hover:text- className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center space-x-3 mb-4"><img src="/seamount-logo.png" alt="Seamount Logo" className="w-8 h-8 object-contain filter drop-shadow-lg rounded-md" /><span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-graywhite">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8 text-center text-sm text-gray-500">
            <div className="flex-300 bg-clip-text text-transparent">Seamount.io</span></div><p className="text-gray-4 flex-col sm:flex-row justify-between items-center">
              <p>© {new Date().getFullYear()} Se00 text-sm">The future of cross-border payments for emerging markets</p>
            </div>
            <div>amount Technologies Ltd. All rights reserved.</p>
              <div className="flex space-x-4 mt-4 sm:mt-0"><div className="flex items-center"><Shield className="h-4 w-4 mr-1 text-green-500" /><span>GDPR Compliant</span></div><div className="flex items-center"><Shield
              <h4 className="text-white font-medium mb-4">Product</h4>
              <ul className="space-y-2 text-sm"><li><a href="#features" className="text-gray-400 hover:text-white">Features</a></li><li><a href="#stablecoin" className="text-gray-400 hover:text-white">USDS Stablecoin</a></li><li><a href="#" className="text-gray-400 hover:text-white">API Documentation</a></li><li><a href="#" className="text-gray-400 hover:text-white">Security className="h-4 w-4 mr-1 text-blue-500" /><span>USDS-Powered Fees</span></div></div>
            </div>
          </div>
        </div>
      </footer>
      
      {showConsentBanner && (
        <div className="fixed bottom-4 right-4 bg-gray-800/80 backdrop-blur-lg border</a></li></ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-4">Company</h4>
              <ul className="space-y-2 text-sm"><li><a href="#about" className="text-gray-4 border-gray-700/50 p-4 rounded-lg shadow-2xl max-w-sm z-50">
          <p className="text-sm text-gray-300 mb-3">We use cookies to enhance your experience and for analytics. Please select your preferences.</p>
          <div className="flex gap00 hover:text-white">About Us</a></li><li><a href="#" className="text-gray-400 hover:text-white">Careers</a></li><li><a href="#" className="text-gray-400 hover:text-white">Blog</a></li><li><a href="#contact" className="text-gray-400 hover:text-white">Contact</a></li></ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="/legal-2">
            <Button onClick={handleApproveAll} size="sm" className="flex-1">App/privacy-policy" className="text-gray-400 hover:text-white">Privacy Policy</a></li>
rove All</Button>
            <Button onClick={handleOpenOptions} size="sm" variant="secondary" className="flex-1">Customize</Button>
          </div>
        </div>
      )}

      {showOptionsModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p                <li><a href="/legal/terms-of-service" className="text-gray-400 hover:text-white">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8 text-center text-sm text-gray-500">
            <div className="flex flex-col sm:flex-row justify-between items-center">
              <p>© {new Date().getFullYear()}-4">
          <div className="bg-gray-900 rounded-xl max-w-lg Seamount Technologies Ltd. All rights reserved.</p>
              <div className="flex space-x-4 mt-4 sm:mt-0"><div className="flex items-center"><Shield className="h-4 w-4 mr-1 text-green-500" /><span>GDPR Compliant</span></div><div className="flex items-center"><Shield w-full p-6 border border-gray-800 shadow-2xl">
            <h3 className="text-xl font-bold mb-4">Cookie Preferences</h3>
            <p className="text-gray-400 mb className="h-4 w-4 mr-1 text-blue-500" /><span>USDS--6 text-sm">We use cookies to operate our site and for marketing purposes. You can choose to opt out of non-essential cookies.</p>
            <div className="space-y-4">
              <div className="flex itemsPowered Fees</span></div></div>
            </div>
          </div>
        </div>
      </footer>
      
      {showConsentBanner && (
        <div className="fixed bottom-4 right-4 bg-gray-800/80 backdrop-blur-lg border-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <div> border-gray-700/50 p-4 rounded-lg shadow-2xl max-w-sm z-50">
          <p className="text-sm text-gray-300 mb-3<h4 className="font-medium text-white">Functional Cookies</h4><p className="text-xs text-gray-400">These cookies are essential for the website to function and cannot be switched off.</p></div>
                <input type="checkbox" checked disabled className="h-4 w-4 rounded text-blue-600 bg-gray-700 border">We use cookies to enhance your experience and for analytics. Please select your preferences.</p>
          <div className="flex gap-2">
            <Button onClick={handleApproveAll} size="sm" className="flex-1">App-gray-600 cursor-not-allowed" />
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <div><h4 className="font-medium text-white">rove All</Button>
            <Button onClick={handleOpenOptions} size="sm" variant="secondary" className="flex-1">Customize</Button>
          </div>
        </div>
      )}

      {showOptionsModal && (
        <div classNameAnalytics & Performance</h4><p className="text-xs text-gray-400">These cookies (including IP address="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 rounded-xl max-w-lg, location, etc.) help us improve our services and develop new cybersecurity products.</p></div>
                <input type="checkbox" checked={cookiePreferences.analytics} onChange={(e) => setCookiePreferences(prev => ({...prev, analytics: e.target.checked}))} className="h-4 w-4 rounded text-blue-600 bg-gray-700 border w-full p-6 border border-gray-800 shadow-2xl">
            <h3 className="text-xl font-bold mb-4">Cookie Preferences</h3>
            <p className="text-gray-400 mb-gray-600" />
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <div><h4 className="font-medium text-white">Advertising & Marketing</h4><p className="text-xs text-gray-400">These cookies help us show-6 text-sm">We use cookies to operate our site and for marketing purposes. You can choose to opt out of non-essential cookies.</p>
            <div className="space-y-4">
              <div className="flex you more relevant ads and marketing communications.</p></div>
                <input type="checkbox" checked={cookiePreferences.advertising} onChange={(e) => setCookiePreferences(prev => ({...prev, advertising: e.target.checked})) items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <div><h} className="h-4 w-4 rounded text-blue-600 bg-gray-7004 className="font-medium text-white">Functional Cookies</h4><p className="text-xs text-gray-400">These cookies are essential for the website to function and cannot be switched off.</p></div>
                <input type="checkbox" checked disabled className="h-4 w-4 rounded text-blue-600 bg-gray-700 border- border-gray-600" />
              </div>
            </div>
            <div className="mt-6 flex gap-4">
              <Button onClick={handleSavePreferences} className="flex-1">Save Preferences</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LandingPage;```gray-600 cursor-not-allowed" />
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <div><h4 className="font