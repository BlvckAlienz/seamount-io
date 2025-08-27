import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Globe, Shield, Zap, DollarSign, Users, Briefcase, Check, Send, Mail, MapPin, Phone, ChevronDown, ChevronUp } from 'lucide-react';
import Button from '@/components/ui/Button';
import { apiClient } from '@/config/api';

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
  const [rewards, setRewards] = useState('$390.00');
  const [formState, setFormState] = useState({ name: '', email: '', message: '' });
  const [formStatus, setFormStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle');

  // --- COOKIE CONSENT STATE ---
  const [showConsentBanner, setShowConsentBanner] = useState(false);
  const [showOptionsModal, setShowOptionsModal] = useState(false);
  const [cookiePreferences, setCookiePreferences] = useState<CookiePreferences>({
    functional: true,
    analytics: true,
    advertising: true,
  });

  // --- COOKIE HELPER FUNCTIONS ---
  const getCookie = (name: string): string | null => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        const popped = parts.pop();
        return popped ? popped.split(';').shift() || null : null;
    }
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
      await apiClient.post(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/consent/cookies`, { preferences });
      console.log("Cookie consent saved to server.", preferences);
    } catch (error) {
      console.error("Failed to save cookie consent to server:", error);
    }
  };

  useEffect(() => {
    const consent = getCookie('seamount_cookie_consent');
    if (!consent) {
      setTimeout(() => setShowConsentBanner(true), 1500);
    }
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
  };
  
  const handleSavePreferences = () => {
    setCookie('seamount_cookie_consent', JSON.stringify(cookiePreferences), 365);
    sendConsentToServer(cookiePreferences);
    setShowOptionsModal(false);
  };

  const toggleFaq = (index: number) => {
    setExpandedFaqs(prev => prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]);
  };

  const calculateYield = useCallback(() => {
    const amount = parseFloat(stakeAmount) || 0;
    let apy = 0.039;
    if (stakePeriod === '30') apy = 0.030;
    else if (stakePeriod === '90') apy = 0.033;
    else if (stakePeriod === '180') apy = 0.036;
    const annualYield = amount * apy;
    setRewards(`$${annualYield.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
  }, [stakeAmount, stakePeriod]);

  useEffect(() => {
    calculateYield();
  }, [calculateYield]);

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormStatus('sending');
    try {
      const response = await apiClient.post(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/investor-contact`, formState);
      if (response.status !== 200) throw new Error('Network response was not ok.');
      setFormStatus('success');
      setFormState({ name: '', email: '', message: '' });
      setTimeout(() => setFormStatus('idle'), 3000);
    } catch (error) {
      console.error('Contact form submission error:', error);
      setFormStatus('error');
      setTimeout(() => setFormStatus('idle'), 3000);
    }
  };

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) entry.target.classList.add('visible');
      });
    }, { threshold: 0.1 });
    const elements = document.querySelectorAll('.fade-in');
    elements.forEach(el => observer.observe(el));
    return () => elements.forEach(el => observer.unobserve(el));
  }, []);

  const faqs = [
    { question: "How much faster and cheaper is sending money with Seamount compared to traditional methods?", answer: "Seamount transfers settle in under 10 minutes for a fraction of the cost. A doctor in the UK sending money to his wife in Nigeria would save significantly on fees and the funds would be available almost instantly, compared to the 3-5 business days and high costs of legacy remittance services." },
    { question: "How can my business benefit from Seamount beyond simple B2B payments?", answer: "Seamount is a complete financial operating system. You can manage multi-currency treasury, automate global payroll, and streamline trade finance with programmable payments. Our platform helps you optimize working capital and earn yield on idle assets, turning your treasury into a strategic advantage." },
    { question: "Is the USDS stablecoin regulated and a secure way to hold money?", answer: "Absolutely. USDS is a fully-reserved stablecoin, backed 1:1 by cash and cash equivalents held in regulated financial institutions. We provide regular, transparent attestations and operate in full compliance with local SEC & CBN regulatory frameworks to ensure institutional-grade trust and security for both individual and business users." },
    { question: "How easy is it to convert USDS back to local currency like the Nigerian Naira?", answer: "It's seamless. Our platform is built with deep 'on-ramp' and 'off-ramp' integrations for African markets. Users can easily convert USDS to local currency and withdraw via bank transfer, mobile money, or through partners like Flutterwave and Paystack, ensuring liquidity when you need it." }
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white selection:bg-blue-500/30">
      <nav className="bg-black/60 backdrop-blur-lg sticky top-0 z-50 border-b border-gray-800/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3">
          <div className="flex items-center justify-between">
            <a href="/" className="flex items-center space-x-3"><img src="/seamount-logo.jpeg" alt="Seamount Logo" className="w-10 h-10 object-contain" /><span className="text-xl font-bold">Seamount.io</span></a>
            <div className="hidden md:flex items-center space-x-8"><a href="#features" className="text-gray-300 hover:text-white">Features</a><a href="#stablecoin" className="text-gray-300 hover:text-white">USDS</a><a href="#about" className="text-gray-300 hover:text-white">About</a><a href="#contact" className="text-gray-300 hover:text-white">Contact</a></div>
            <div className="flex items-center space-x-2"><Button variant="ghost" onClick={() => onOpenAuth('login')}>Sign In</Button><Button onClick={() => onOpenAuth('register')} elevated>Sign Up</Button></div>
          </div>
        </div>
      </nav>

      <main>
        <section className="relative py-20 md:py-32 overflow-hidden">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNNTkuNSA2MEgwVjBoNjBWNjBoLS41ek0xIDF2NThoNTguMDAxVjFIMXoiIGZpbGw9IiMyMDIwMjAiIG9wYWNpdHk9IjAuMiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PC9zdmc+')] bg-[length:30px_30px] opacity-20"></div>
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute top-1/4 left-1/3 w-60 h-60 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
            <div className="text-center max-w-4xl mx-auto">
              <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold mb-6 bg-gradient-to-r from-blue-400 via-white to-purple-300 bg-clip-text text-transparent tracking-tighter">Regulated Borderless Money Built for Trust</h1>
              <p className="text-lg sm:text-xl text-gray-300 mb-10 leading-relaxed">Experience instant global transfers with USDS stablecoin. Low remittance fees (2.6% per transaction), 24/7 decentralized settlement, seamless swapping to USDT, USDC, and more...</p>
              <div className="flex flex-col sm:flex-row justify-center gap-4 mb-12"><Button onClick={() => onOpenAuth('register')} size="lg" className="px-8 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700" icon={ArrowRight} elevated animated>Get Started for Free</Button><Button size="lg" variant="outline" onClick={() => document.getElementById('features')?.scrollIntoView()} elevated>Learn More</Button></div>
              <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-gray-400"><div className="flex items-center"><Shield className="h-4 w-4 mr-1.5 text-green-400" /><span>Bank-level security</span></div><div className="flex items-center"><Zap className="h-4 w-4 mr-1.5 text-yellow-400" /><span>Sub-second settlements</span></div><div className="flex items-center"><DollarSign className="h-4 w-4 mr-1.5 text-blue-400" /><span>Up to 87% lower fees</span></div></div>
            </div>
          </div>
        </section>

        <section id="features" className="py-20 bg-gray-950/40 backdrop-blur-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-16 fade-in"><h2 className="text-3xl md:text-4xl font-bold mb-4">One Platform, Limitless Possibilities</h2><p className="text-gray-400 max-w-2xl mx-auto">From personal remittances to corporate treasury, our solutions are engineered to solve the real-world challenges of moving money in and out of Africa.</p></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {[ { icon: <Send className="h-8 w-8 text-blue-500" />, title: "Instant Global Transfers", description: "Send money to family or settle business invoices in minutes, not days. Our blockchain rails bypass slow, expensive legacy systems." }, { icon: <DollarSign className="h-8 w-8 text-green-500" />, title: "Drastically Lower Fees", description: "Keep more of your money. Save up to 87% on fees for personal remittances and business payments compared to traditional banks." }, { icon: <Briefcase className="h-8 w-8 text-purple-500" />, title: "Personal Savings & Corporate Treasury", description: "For individuals, a stable way to save and earn. For businesses, a powerful tool to manage liquidity, automate payments, and optimize capital 24/7." }, { icon: <Users className="h-8 w-8 text-yellow-500" />, title: "Global Payroll & Creator Payouts", description: "Pay your international team or global creator base instantly and affordably. Perfect for remote workforces and the gig economy." }, { icon: <Zap className="h-8 w-8 text-red-500" />, title: "Earn Yield on USDS", description: "Whether holding personal savings or corporate funds, our USDS stablecoin allows you to earn competitive returns on your digital dollars." }, { icon: <Globe className="h-8 w-8 text-teal-500" />, title: "Seamless Local Integration", description: "Designed for Africa. Easily move funds with deep integrations for Flutterwave, Paystack, bank transfers, and mobile money." } ].map((feature, index) => (<div key={index} className="p-6 bg-gradient-to-br from-gray-900/50 to-gray-800/30 rounded-xl border border-gray-800/80 hover:border-blue-700/50 transition-all duration-300 shadow-xl backdrop-blur-sm hover:-translate-y-2 fade-in"><div className="rounded-full w-14 h-14 flex items-center justify-center bg-gray-800/80 mb-5 border border-gray-700/50 shadow-inner">{feature.icon}</div><h3 className="text-xl font-bold mb-3 text-white">{feature.title}</h3><p className="text-gray-400">{feature.description}</p></div>))}
            </div>
          </div>
        </section>
        
        <section id="about" className="py-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-16 fade-in"><h2 className="text-3xl md:text-4xl font-bold mb-4">About Seamount</h2><p className="text-gray-400 max-w-2xl mx-auto">A stablecoin network that bridges traditional finance and Web3, democratizing global commerce for emerging African markets.</p></div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div className="fade-in"><div className="mb-8"><h3 className="text-2xl font-bold mb-4 text-white">Our Mission</h3><p className="text-gray-300 leading-relaxed">Seamount is building the next generation of global financial infrastructure to transform the movement and custody of money. By combining the stability of regulated digital dollars with the efficiency of modern payment rails, we empower households and businesses to operate without borders, unlocking new opportunities in emerging African markets and beyond.</p></div></div>
              <div className="fade-in"><div className="grid grid-cols-2 gap-4"><div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50"><div className="text-3xl font-bold text-blue-400">60+</div><div className="text-gray-400">Countries Reached</div></div><div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50"><div className="text-3xl font-bold text-purple-400">500K USDS</div><div className="text-gray-400">Total Token Supply</div></div><div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50"><div className="text-3xl font-bold text-green-400">87%</div><div className="text-gray-400">Cost Savings</div></div><div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50"><div className="text-3xl font-bold text-yellow-400">6K+</div><div className="text-gray-400">Projected Users (12 months)</div></div></div></div>
            </div>
          </div>
        </section>

        <section id="stablecoin" className="py-20 relative overflow-hidden bg-gray-950/40 backdrop-blur-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
                <div className="text-center mb-16 fade-in"><h2 className="text-3xl md:text-4xl font-bold mb-4">USDS: The Institutional-Grade Digital Dollar For Africa</h2><p className="text-gray-400 max-w-2xl mx-auto">A stable, programmable, digital currency that powers 24/7 global commerce, cross-border payments, and treasury management with the security of blockchain technology.</p></div>
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-center">
                    <div className="lg:col-span-3 bg-gradient-to-br from-blue-900/30 to-blue-800/10 rounded-xl p-8 border border-blue-700/30 backdrop-blur-sm fade-in">
                        <h3 className="text-2xl font-bold mb-6 text-blue-300">1:1 USD Peg & Transparency</h3><p className="text-gray-300 mb-4">More than a payment token, USDS is a programmable financial asset. It provides the core building block for everything from cross-border settlement to tokenized real-world assets, offering stability, transparency, and yield-bearing potential for households and corporate treasuries.</p><ul className="space-y-3 text-gray-300">{[ "Fully backed by audited USD reserves", "Regulated and compliant across jurisdictions", "Regular public attestations ensure transparency", "Instant settlement on the Algorand network" ].map((feature, i) => (<li key={i} className="flex items-start"><Check className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" /><span>{feature}</span></li>))}</ul>
                    </div>
                    <div className="lg:col-span-2 bg-gradient-to-br from-gray-900/50 to-gray-800/30 rounded-xl p-8 border border-gray-800/80 backdrop-blur-sm fade-in">
                        <h3 className="text-xl font-bold mb-4 text-center">Yield Calculator</h3><div className="space-y-4"><div><label htmlFor="stake-amount" className="text-sm text-gray-400">Investment Amount</label><input id="stake-amount" name="stake-amount" type="number" value={stakeAmount} onChange={(e) => setStakeAmount(e.target.value)} className="w-full mt-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" /></div><div><label htmlFor="stake-period" className="text-sm text-gray-400">Period</label><select id="stake-period" name="stake-period" value={stakePeriod} onChange={(e) => setStakePeriod(e.target.value)} className="w-full mt-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"><option value="30">1 Month (3.0% APY)</option><option value="90">3 Months (3.3% APY)</option><option value="180">6 Months (3.6% APY)</option><option value="365">1 Year (3.9% APY)</option></select></div><div className="bg-gradient-to-r from-green-600 to-teal-600 rounded-lg p-4 text-center"><div className="text-2xl font-bold">{rewards}</div><div className="text-sm opacity-80">Estimated Annual Yield</div></div></div>
                    </div>
                </div>
            </div>
        </section>

        <section id="contact" className="py-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-16 fade-in"><h2 className="text-3xl md:text-4xl font-bold mb-4">Get in Touch</h2><p className="text-gray-400 max-w-2xl mx-auto">Have questions or interested in our solutions? Our team is here to help.</p></div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-6 fade-in">{[ { icon: <MapPin className="h-6 w-6 text-blue-500 flex-shrink-0 mt-1" />, title: "Our Address", detail: "Wood Avenue, Kilimani, Nairobi, Kenya" }, { icon: <Mail className="h-6 w-6 text-green-500 flex-shrink-0 mt-1" />, title: "Email Us", detail: "support@seamount.io" }, { icon: <Phone className="h-6 w-6 text-purple-500 flex-shrink-0 mt-1" />, title: "Call Us", detail: "+254 751 875 374" } ].map((item, i) => (<div key={i} className="flex items-start space-x-4"><div className="p-3 bg-gray-800/50 rounded-full">{item.icon}</div><div><h3 className="font-semibold text-lg text-white mb-1">{item.title}</h3><p className="text-gray-300">{item.detail}</p></div></div>))}</div>
              <div className="fade-in"><form onSubmit={handleContactSubmit} className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 rounded-xl border border-gray-800/80 p-6 backdrop-blur-sm"><h3 className="text-xl font-bold mb-4">Send Us a Message</h3><div className="space-y-4"><div><label htmlFor="contact-name" className="block text-sm font-medium text-gray-300 mb-1">Your Name</label><input id="contact-name" name="name" type="text" value={formState.name} onChange={(e) => setFormState({...formState, name: e.target.value})} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg" placeholder="Full Name" required /></div><div><label htmlFor="contact-email" className="block text-sm font-medium text-gray-300 mb-1">Email Address</label><input id="contact-email" name="email" type="email" value={formState.email} onChange={(e) => setFormState({...formState, email: e.target.value})} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg" placeholder="Email" required /></div><div><label htmlFor="contact-message" className="block text-sm font-medium text-gray-300 mb-1">Message</label><textarea id="contact-message" name="message" value={formState.message} onChange={(e) => setFormState({...formState, message: e.target.value})} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg resize-none" rows={4} placeholder="Your message" required></textarea></div><Button type="submit" loading={formStatus === 'sending'} className="w-full bg-gradient-to-r from-blue-600 to-purple-600">{formStatus === 'success' ? 'Message Sent!' : formStatus === 'error' ? 'Failed, Try Again' : 'Send Message'}</Button></div></form></div>
            </div>
          </div>
        </section>

        <section className="py-20 bg-gradient-to-r from-blue-900/20 to-purple-900/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
            <div className="max-w-3xl mx-auto"><h2 className="text-3xl md:text-4xl font-bold mb-6">Ready to Transform How You Move Money?</h2><Button size="lg" onClick={() => onOpenAuth('register')} className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-lg" elevated animated>Sign Up for Free</Button><p className="mt-4 text-sm text-gray-400">Already have an account? <button onClick={() => onOpenAuth('login')} className="text-blue-400 hover:underline font-semibold">Sign In</button></p></div>
          </div>
        </section>
      </main>

      <footer className="bg-gray-950 border-t border-gray-800/60 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center space-x-3 mb-4"><img src="/seamount-logo.jpeg" alt="Seamount Logo" className="w-8 h-8 object-contain" /><span className="text-xl font-bold">Seamount.io</span></div><p className="text-gray-400 text-sm">The future of cross-border payments for emerging markets</p>
            </div>
            <div>
              <h4 className="text-white font-medium mb-4">Product</h4>
              <ul className="space-y-2 text-sm"><li><a href="#features" className="text-gray-400 hover:text-white">Features</a></li><li><a href="#stablecoin" className="text-gray-400 hover:text-white">USDS Stablecoin</a></li><li><a href="#" className="text-gray-400 hover:text-white">API Documentation</a></li><li><a href="#" className="text-gray-400 hover:text-white">Security</a></li></ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-4">Company</h4>
              <ul className="space-y-2 text-sm"><li><a href="#about" className="text-gray-400 hover:text-white">About Us</a></li><li><a href="#" className="text-gray-400 hover:text-white">Careers</a></li><li><a href="#" className="text-gray-400 hover:text-white">Blog</a></li><li><a href="#contact" className="text-gray-400 hover:text-white">Contact</a></li></ul>
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
              <div className="flex space-x-4 mt-4 sm:mt-0"><div className="flex items-center"><Shield className="h-4 w-4 mr-1 text-green-500" /><span>GDPR Compliant</span></div><div className="flex items-center"><Shield className="h-4 w-4 mr-1 text-blue-500" /><span>USDS-Powered Fees</span></div></div>
            </div>
          </div>
        </div>
      </footer>

      {showOptionsModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 rounded-xl max-w-lg w-full p-6 border border-gray-800 shadow-2xl">
            <h3 className="text-xl font-bold mb-4">Cookie Preferences</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <div><h4 className="font-medium text-white">Functional Cookies</h4><p className="text-xs text-gray-400">Essential for the site to function.</p></div>
                <input type="checkbox" checked disabled className="h-4 w-4 rounded text-blue-600 bg-gray-700 border-gray-600" />
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <div><h4 className="font-medium text-white">Analytics Cookies</h4><p className="text-xs text-gray-400">Help us improve our services.</p></div>
                <input type="checkbox" checked={cookiePreferences.analytics} onChange={(e) => setCookiePreferences({...cookiePreferences, analytics: e.target.checked})} className="h-4 w-4 rounded text-blue-600 bg-gray-700 border-gray-600" />
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <div><h4 className="font-medium text-white">Advertising Cookies</h4><p className="text-xs text-gray-400">Used for targeted advertising.</p></div>
                <input type="checkbox" checked={cookiePreferences.advertising} onChange={(e) => setCookiePreferences({...cookiePreferences, advertising: e.target.checked})} className="h-4 w-4 rounded text-blue-600 bg-gray-700 border-gray-600" />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <Button onClick={handleSavePreferences} className="flex-1">Save Preferences</Button>
              <Button onClick={() => setShowOptionsModal(false)} variant="secondary" className="flex-1">Cancel</Button>
            </div>
          </div>
        </div>
      )}

      <section className="py-16 bg-gray-950/60">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12 fade-in">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Frequently Asked Questions</h2>
            <p className="text-gray-400 max-w-2xl mx-auto">Get answers to common questions about Seamount's cross-border payment platform.</p>
          </div>
          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <div key={index} className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 rounded-xl border border-gray-800/80 backdrop-blur-sm overflow-hidden fade-in">
                <button onClick={() => toggleFaq(index)} className="w-full px-6 py-4 text-left flex items-center justify-between hover:bg-gray-800/30 transition-colors">
                  <h3 className="font-semibold text-lg text-white pr-4">{faq.question}</h3>
                  {expandedFaqs.includes(index) ? <ChevronUp className="h-5 w-5 text-blue-500 flex-shrink-0" /> : <ChevronDown className="h-5 w-5 text-blue-500 flex-shrink-0" />}
                </button>
                {expandedFaqs.includes(index) && (
                  <div className="px-6 pb-4 border-t border-gray-800/50">
                    <p className="text-gray-300 pt-4">{faq.answer}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;