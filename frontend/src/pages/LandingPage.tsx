import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Globe, Shield, Zap, DollarSign, TrendingUp, Check, Send, Twitter, Instagram, Mail, MapPin, Phone, ChevronDown, ChevronUp, Linkedin } from 'lucide-react';
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
  const [rewards, setRewards] = useState('$450.00');
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
    let apy = 0.045;
    if (stakePeriod === '30') apy = 0.035;
    else if (stakePeriod === '90') apy = 0.040;
    else if (stakePeriod === '180') apy = 0.042;
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
      console.error("Contact form submission error:", error);
      setFormStatus('error');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black text-white">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center px-4 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(0,0,255,0.1),transparent_70%)] opacity-50"></div>
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-blue-400 to-purple-500 text-transparent bg-clip-text">
            Revolutionize Cross-Border Payments
          </h1>
          <p className="text-xl md:text-2xl text-gray-300 mb-12">
            Instant, low-cost transfers powered by USDS stablecoin. Yield farming meets seamless global finance.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" onClick={() => onOpenAuth('register')} className="bg-gradient-to-r from-blue-600 to-purple-600">
              Get Started <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button size="lg" variant="outline" onClick={() => navigate('/demo')}>Try Demo</Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-16">Why Choose Seamount?</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-gray-800/50 p-8 rounded-xl border border-gray-700/50 backdrop-blur-sm">
              <Globe className="h-12 w-12 text-blue-400 mb-4" />
              <h3 className="text-2xl font-bold mb-4">Global Reach</h3>
              <p className="text-gray-300">Send and receive payments across borders instantly with minimal fees.</p>
            </div>
            <div className="bg-gray-800/50 p-8 rounded-xl border border-gray-700/50 backdrop-blur-sm">
              <Shield className="h-12 w-12 text-green-400 mb-4" />
              <h3 className="text-2xl font-bold mb-4">Bank-Grade Security</h3>
              <p className="text-gray-300">Enterprise-level encryption and compliance for peace of mind.</p>
            </div>
            <div className="bg-gray-800/50 p-8 rounded-xl border border-gray-700/50 backdrop-blur-sm">
              <Zap className="h-12 w-12 text-yellow-400 mb-4" />
              <h3 className="text-2xl font-bold mb-4">Lightning Fast</h3>
              <p className="text-gray-300">Transactions confirmed in seconds, not days.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Yield Farming Section */}
      <section id="yield" className="py-24 px-4 bg-gray-900/50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-16">Earn Yield on Your Stablecoins</h2>
          <div className="bg-gray-800/50 p-8 rounded-xl border border-gray-700/50">
            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Stake Amount (USDS)</label>
                <input 
                  type="number" 
                  value={stakeAmount} 
                  onChange={(e) => setStakeAmount(e.target.value)} 
                  className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Stake Period</label>
                <select 
                  value={stakePeriod} 
                  onChange={(e) => setStakePeriod(e.target.value)}
                  className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500"
                >
                  <option value="30">30 Days (3.5% APY)</option>
                  <option value="90">90 Days (4.0% APY)</option>
                  <option value="180">180 Days (4.2% APY)</option>
                  <option value="365">365 Days (4.5% APY)</option>
                </select>
              </div>
            </div>
            <div className="mt-8 p-6 bg-blue-900/20 rounded-lg border border-blue-800/50">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Estimated Annual Rewards</span>
                <span className="text-3xl font-bold text-green-400">{rewards}</span>
              </div>
            </div>
            <Button size="lg" className="w-full mt-8 bg-gradient-to-r from-green-600 to-blue-600">
              Start Earning <TrendingUp className="ml-2 h-5 w-5" />
            </Button>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-24 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-16">How It Works</h2>
          <div className="space-y-8">
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">1</div>
              <div>
                <h3 className="text-xl font-bold mb-2">Sign Up & Verify</h3>
                <p className="text-gray-300">Create your account and complete quick KYC verification.</p>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">2</div>
              <div>
                <h3 className="text-xl font-bold mb-2">Fund Your Wallet</h3>
                <p className="text-gray-300">Deposit fiat or crypto and convert to USDS stablecoin.</p>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">3</div>
              <div>
                <h3 className="text-xl font-bold mb-2">Send & Earn</h3>
                <p className="text-gray-300">Make payments or stake your USDS to earn competitive yields.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-24 px-4 bg-gray-900/50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-16">Frequently Asked Questions</h2>
          <div className="space-y-4">
            {[
              {
                q: "What is USDS?",
                a: "USDS is our USD-pegged stablecoin, backed 1:1 by cash reserves and short-term treasuries."
              },
              {
                q: "How secure is Seamount?",
                a: "We use bank-grade security with multi-signature wallets, regular audits, and full compliance with regulations."
              },
              {
                q: "What fees do you charge?",
                a: "Network fees are minimal on Solana/Ethereum. We charge 0.1% for cross-border transfers, paid in USDS."
              },
              {
                q: "Can I earn yield on my holdings?",
                a: "Yes! Stake your USDS for up to 4.5% APY through our yield farming program."
              }
            ].map((faq, index) => (
              <div key={index} className="bg-gray-800/50 rounded-lg border border-gray-700/50">
                <button 
                  onClick={() => toggleFaq(index)}
                  className="w-full px-6 py-4 flex justify-between items-center text-left"
                >
                  <span className="font-medium">{faq.q}</span>
                  {expandedFaqs.includes(index) ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </button>
                {expandedFaqs.includes(index) && (
                  <p className="px-6 py-4 text-gray-300 border-t border-gray-700/50">{faq.a}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section id="contact" className="py-24 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-16">Get in Touch</h2>
          <div className="grid md:grid-cols-2 gap-12">
            <div>
              <h3 className="text-2xl font-bold mb-6">Contact Information</h3>
              <div className="space-y-4 text-gray-300">
                <div className="flex items-center space-x-3">
                  <Mail className="h-5 w-5 text-blue-400" />
                  <span>support@seamount.io</span>
                </div>
                <div className="flex items-center space-x-3">
                  <Phone className="h-5 w-5 text-blue-400" />
                  <span>+1 (555) 123-4567</span>
                </div>
                <div className="flex items-center space-x-3">
                  <MapPin className="h-5 w-5 text-blue-400" />
                  <span>123 FinTech Street, San Francisco, CA 94105</span>
                </div>
              </div>
              <div className="mt-8 flex space-x-4">
                <a href="#" className="p-2 bg-gray-800 rounded-full hover:bg-gray-700"><Twitter className="h-5 w-5" /></a>
                <a href="#" className="p-2 bg-gray-800 rounded-full hover:bg-gray-700"><Linkedin className="h-5 w-5" /></a>
                <a href="#" className="p-2 bg-gray-800 rounded-full hover:bg-gray-700"><Instagram className="h-5 w-5" /></a>
              </div>
            </div>
            <form onSubmit={handleContactSubmit} className="space-y-6">
              <input 
                type="text" 
                placeholder="Your Name" 
                value={formState.name}
                onChange={(e) => setFormState({...formState, name: e.target.value})}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500"
                required
              />
              <input 
                type="email" 
                placeholder="Your Email" 
                value={formState.email}
                onChange={(e) => setFormState({...formState, email: e.target.value})}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500"
                required
              />
              <textarea 
                placeholder="Your Message" 
                value={formState.message}
                onChange={(e) => setFormState({...formState, message: e.target.value})}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500 h-32"
                required
              />
              <Button 
                type="submit" 
                size="lg" 
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600"
                disabled={formStatus === 'sending'}
              >
                {formStatus === 'sending' ? 'Sending...' : 'Send Message'} <Send className="ml-2 h-5 w-5" />
              </Button>
              {formStatus === 'success' && <p className="text-green-400 text-center">Message sent successfully!</p>}
              {formStatus === 'error' && <p className="text-red-400 text-center">Failed to send message. Please try again.</p>}
            </form>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900/50 py-12 px-4 border-t border-gray-800">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <h4 className="text-white font-medium mb-4">Seamount</h4>
              <p className="text-sm text-gray-400">Empowering global finance with stablecoins and DeFi.</p>
            </div>
            <div>
              <h4 className="text-white font-medium mb-4">Products</h4>
              <ul className="space-y-2 text-sm"><li><a href="#features" className="text-gray-400 hover:text-white">Payments</a></li><li><a href="#yield" className="text-gray-400 hover:text-white">Yield Farming</a></li><li><a href="#" className="text-gray-400 hover:text-white">API Documentation</a></li><li><a href="#" className="text-gray-400 hover:text-white">Security</a></li></ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-4">Company</h4>
              <ul className="space-y-2 text-sm"><li><a href="#about" className="text-gray-400 hover:text-white">About Us</a></li><li><a href="#" className="text-gray-400 hover:text-white">Careers</a></li><li><a href="#" className="text-gray-400 hover:text-white">Blog</a></li><li><a href="#contact" className="text-gray-400 hover:text-white">Contact</a></li></ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="/legal/privacy-policy" className="text-gray-400 hover:text-white">Privacy Policy</a></li>
                <li><a href="/legal/terms-of-service" className="text-gray-400 hover:text-white">Terms of Service</a></li>
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
      
      {showConsentBanner && (
        <div className="fixed bottom-4 right-4 bg-gray-800/80 backdrop-blur-lg border border-gray-700/50 p-4 rounded-lg shadow-2xl max-w-sm z-50">
          <p className="text-sm text-gray-300 mb-3">We use cookies to enhance your experience. Please select your preferences.</p>
          <div className="flex gap-2">
            <Button onClick={handleApproveAll} size="sm" className="flex-1">Approve All</Button>
            <Button onClick={handleOpenOptions} size="sm" variant="secondary" className="flex-1">Customize</Button>
          </div>
        </div>
      )}

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
                <input type="checkbox" checked={cookiePreferences.analytics} onChange={(e) => setCookiePreferences(prev => ({...prev, analytics: e.target.checked}))} className="h-4 w-4 rounded text-blue-600 bg-gray-700 border-gray-600" />
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <div><h4 className="font-medium text-white">Advertising Cookies</h4><p className="text-xs text-gray-400">Help us show relevant ads.</p></div>
                <input type="checkbox" checked={cookiePreferences.advertising} onChange={(e) => setCookiePreferences(prev => ({...prev, advertising: e.target.checked}))} className="h-4 w-4 rounded text-blue-600 bg-gray-700 border-gray-600" />
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

export default LandingPage;