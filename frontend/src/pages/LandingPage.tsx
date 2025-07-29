import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Globe, Shield, Zap, DollarSign, TrendingUp, Check, Send, Twitter, Instagram, Mail, MapPin, Phone, ChevronDown, ChevronUp } from 'lucide-react';
import Button from '../components/Button';
import AuthButton from '../components/AuthButton';
import AuthModal from '../components/AuthModal';

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [expandedFaqs, setExpandedFaqs] = useState<number[]>([]);
  const [activeAuthView, setActiveAuthView] = useState<'login' | 'register'>('register');
  
  const toggleFaq = (index: number) => {
    setExpandedFaqs(prev => 
      prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]
    );
  };

  const handleCTAClick = () => {
    setActiveAuthView('register');
    setIsAuthModalOpen(true);
  };

  const faqs = [
    {
      question: "How fast are Seamount cross-border transfers?",
      answer: "Seamount transfers settle within seconds, not days. Our blockchain technology enables instant settlement across borders, dramatically faster than traditional banking which can take 3-5 business days."
    },
    {
      question: "What are the fees for using Seamount?",
      answer: "Our fees are typically just 0.1-0.5% per transaction, compared to 3-7% with traditional remittance providers. There are no hidden fees or exchange rate markups."
    },
    {
      question: "Is USDS stablecoin regulated and secure?",
      answer: "Yes, USDS is fully compliant with local regulations and maintains a 1:1 USD peg. All USDS tokens are fully backed by USD reserves, ensuring stability and security."
    },
    {
      question: "Which African countries are supported?",
      answer: "We currently support Kenya, Nigeria, South Africa, Ghana, and Uganda, with more countries being added regularly. Our platform integrates with local payment methods including M-Pesa and bank transfers."
    }
  ];

  const stakingTiers = [
    { amount: '1,000 USDS', period: '30 days', apy: '4%', lockup: 'None' },
    { amount: '10,000 USDS', period: '90 days', apy: '6%', lockup: '30 days' },
    { amount: '50,000+ USDS', period: '180 days', apy: '8%', lockup: '60 days' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-950 via-gray-900 to-gray-950 text-white">
      {/* Navigation */}
      <nav className="bg-black/60 backdrop-blur-lg sticky top-0 z-50 border-b border-gray-800/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <img 
                src="https://i.imgur.com/59eVKha.png" 
                alt="Seamount Logo" 
                className="w-10 h-10 object-contain filter drop-shadow-lg rounded-md"
              />
              <div>
                <span className="text-xl font-bold bg-gradient-to-r from-blue-400 via-white to-gray-300 bg-clip-text text-transparent">
                  Seamount.io
                </span>
              </div>
            </div>
            
            <div className="hidden md:flex items-center space-x-8">
              <a href="#features" className="text-gray-300 hover:text-white transition-colors">Features</a>
              <a href="#stablecoin" className="text-gray-300 hover:text-white transition-colors">USDS</a>
              <a href="#about" className="text-gray-300 hover:text-white transition-colors">About</a>
              <a href="#contact" className="text-gray-300 hover:text-white transition-colors">Contact</a>
            </div>
            
            <div>
              <AuthButton />
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative py-20 overflow-hidden">
        {/* Background Animation */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_center,rgba(29,78,216,0.15),transparent_50%)]"></div>
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/20 rounded-full blur-3xl"></div>
          <div className="absolute top-1/4 left-1/3 w-60 h-60 bg-purple-500/20 rounded-full blur-3xl"></div>
          <div className="absolute bottom-0 right-1/4 w-60 h-60 bg-blue-500/20 rounded-full blur-3xl"></div>
          
          {/* Grid pattern */}
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNNTkuNSA2MEgwVjBoNjBWNjBoLS41ek0xIDF2NThoNTguMDAxVjFIMXoiIGZpbGw9IiMyMDIwMjAiIG9wYWNpdHk9IjAuMiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PC9zdmc+')] bg-[length:30px_30px] opacity-20"></div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold mb-6 bg-gradient-to-r from-blue-400 via-white to-purple-300 bg-clip-text text-transparent">
              The Future of Cross-Border Payments is Here
            </h1>
            <p className="text-lg sm:text-xl text-gray-300 mb-10 leading-relaxed">
              Experience instant, low-cost P2P and B2B transfers powered by Web3 technology
            </p>
            
            <div className="flex flex-col sm:flex-row justify-center gap-4 mb-12">
              <Button 
                onClick={handleCTAClick}
                size="lg" 
                className="px-8 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                icon={ArrowRight}
                elevated
                animated
              >
                Get Started
              </Button>
              <Button 
                size="lg" 
                variant="ghost" 
                className="border border-gray-700"
                onClick={() => navigate('/login')}
                elevated
              >
                Learn More
              </Button>
            </div>
            
            <div className="flex flex-wrap justify-center gap-4 text-sm text-gray-400">
              <div className="flex items-center">
                <Shield className="h-4 w-4 mr-1 text-green-400" />
                <span>Bank-level security</span>
              </div>
              <div className="flex items-center">
                <Zap className="h-4 w-4 mr-1 text-yellow-400" />
                <span>Sub-second settlements</span>
              </div>
              <div className="flex items-center">
                <DollarSign className="h-4 w-4 mr-1 text-blue-400" />
                <span>87% lower fees</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Showcase */}
      <section id="features" className="py-20 bg-gradient-to-b from-gray-900/40 to-gray-950/40 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Revolutionizing Financial Access</h2>
            <p className="text-gray-400 max-w-2xl mx-auto">Our platform is designed to solve the challenges of cross-border payments for emerging markets.</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                icon: <Send className="h-8 w-8 text-blue-500" />,
                title: "Instant Transfers",
                description: "Send money globally in seconds, not days. Our blockchain technology enables immediate settlement across borders."
              },
              {
                icon: <DollarSign className="h-8 w-8 text-green-500" />,
                title: "Ultra-Low Fees",
                description: "Pay pennies, not percentages for international transfers. Save up to 87% compared to traditional banks and remittance services."
              },
              {
                icon: <Shield className="h-8 w-8 text-purple-500" />,
                title: "USDS Stablecoin",
                description: "Our USD-pegged stablecoin ensures stable value during transfers and offers staking rewards for holders."
              },
              {
                icon: <TrendingUp className="h-8 w-8 text-yellow-500" />,
                title: "AI-Powered Trading",
                description: "Let AI optimize your investment portfolio with advanced algorithmic trading and risk management."
              },
              {
                icon: <Zap className="h-8 w-8 text-red-500" />,
                title: "Staking Rewards",
                description: "Earn up to 8% APY by holding USDS tokens. The longer you stake, the higher your returns."
              },
              {
                icon: <Globe className="h-8 w-8 text-teal-500" />,
                title: "African-First Design",
                description: "Built for African markets with integration for M-Pesa, bank transfers, and mobile money across multiple countries."
              }
            ].map((feature, index) => (
              <div 
                key={index} 
                className="p-6 bg-gradient-to-br from-gray-900/50 to-gray-800/30 rounded-xl border border-gray-800/80 hover:border-gray-700/80 transition-all duration-300 shadow-xl backdrop-blur-sm hover:scale-[1.03]"
              >
                <div className="rounded-full w-14 h-14 flex items-center justify-center bg-gray-800/80 mb-5 border border-gray-700/50 shadow-inner">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-bold mb-3 text-white">{feature.title}</h3>
                <p className="text-gray-400">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* USDS Stablecoin */}
      <section id="stablecoin" className="py-20 relative">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl"></div>
          <div className="absolute bottom-1/3 left-1/3 w-72 h-72 bg-green-500/10 rounded-full blur-3xl"></div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Meet USDS - Your Gateway to Web3 Finance</h2>
            <p className="text-gray-400 max-w-2xl mx-auto">A stable digital currency that powers cross-border transactions with the security of blockchain technology.</p>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-16">
            <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/10 rounded-xl p-8 border border-blue-700/30 backdrop-blur-sm">
              <h3 className="text-2xl font-bold mb-6 text-blue-300">1:1 USD Peg</h3>
              <p className="text-gray-300 mb-4">USDS maintains a stable value pegged 1:1 to the US Dollar, ensuring your money retains its value during cross-border transfers.</p>
              <ul className="space-y-3">
                {[
                  "Fully backed by USD reserves",
                  "Regulated and compliant across jurisdictions",
                  "Regular public audits ensure transparency",
                  "Instant settlement on blockchain"
                ].map((feature, i) => (
                  <li key={i} className="flex items-start">
                    <Check className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
            
            <div className="bg-gradient-to-br from-green-900/30 to-green-800/10 rounded-xl p-8 border border-green-700/30 backdrop-blur-sm">
              <h3 className="text-2xl font-bold mb-6 text-green-300">Staking Benefits</h3>
              
              <div className="overflow-x-auto">
                <table className="w-full mb-6">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="py-3 text-left text-gray-400 font-medium">Amount</th>
                      <th className="py-3 text-left text-gray-400 font-medium">Period</th>
                      <th className="py-3 text-left text-gray-400 font-medium">APY</th>
                      <th className="py-3 text-left text-gray-400 font-medium">Lockup</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stakingTiers.map((tier, i) => (
                      <tr key={i} className="border-b border-gray-800">
                        <td className="py-3 text-white">{tier.amount}</td>
                        <td className="py-3 text-white">{tier.period}</td>
                        <td className="py-3 text-green-400 font-bold">{tier.apy}</td>
                        <td className="py-3 text-gray-300">{tier.lockup}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              <p className="text-gray-400 text-sm">
                Earn competitive yields by staking your USDS. The longer you stake, the higher your returns.
              </p>
            </div>
          </div>
          
          <div className="text-center">
            <Button
              size="lg"
              onClick={handleCTAClick}
              className="px-8 bg-gradient-to-r from-blue-600 to-teal-600 hover:from-blue-700 hover:to-teal-700"
              elevated
            >
              Start Staking USDS
            </Button>
          </div>
        </div>
      </section>

      {/* About Seamount */}
      <section id="about" className="py-20 bg-gradient-to-b from-gray-900/40 to-gray-950/40 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">About Seamount</h2>
            <p className="text-gray-400 max-w-2xl mx-auto">Building bridges between traditional finance and Web3 to democratize financial access for emerging markets.</p>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="mb-8">
                <h3 className="text-2xl font-bold mb-4 text-white">Our Mission</h3>
                <p className="text-gray-300 leading-relaxed">
                  Seamount is on a mission to revolutionize cross-border payments in emerging markets. 
                  We're building technology that enables instant, low-cost transfers between countries, 
                  making financial services accessible to everyone regardless of location.
                </p>
              </div>
              
              <div>
                <h3 className="text-2xl font-bold mb-4 text-white">Our Impact</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50">
                    <div className="text-3xl font-bold text-blue-400">5+</div>
                    <div className="text-gray-400">Countries Reached</div>
                  </div>
                  <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50">
                    <div className="text-3xl font-bold text-purple-400">$50M+</div>
                    <div className="text-gray-400">Transaction Volume</div>
                  </div>
                  <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50">
                    <div className="text-3xl font-bold text-green-400">87%</div>
                    <div className="text-gray-400">Cost Savings</div>
                  </div>
                  <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50">
                    <div className="text-3xl font-bold text-yellow-400">25K+</div>
                    <div className="text-gray-400">Happy Users</div>
                  </div>
                </div>
              </div>
            </div>
            
            <div>
              <div className="relative rounded-xl overflow-hidden border border-gray-800 shadow-2xl">
                <div className="aspect-w-16 aspect-h-9 bg-gray-800">
                  <div className="w-full h-full flex items-center justify-center p-6 bg-gradient-to-br from-blue-900/50 to-purple-900/50">
                    <div className="space-y-6 text-left">
                      <h3 className="text-2xl font-bold">Leadership Team</h3>
                      <div className="grid grid-cols-2 gap-4">
                        {[
                          { name: "Sarah Johnson", role: "CEO & Co-founder" },
                          { name: "Michael Oladipo", role: "CTO & Co-founder" },
                          { name: "David Wainaina", role: "Head of African Markets" },
                          { name: "Priya Sharma", role: "Chief Product Officer" }
                        ].map((person, i) => (
                          <div key={i} className="flex flex-col">
                            <div className="w-12 h-12 rounded-full bg-gray-700 mb-2"></div>
                            <div className="text-sm font-medium">{person.name}</div>
                            <div className="text-xs text-gray-400">{person.role}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQs */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Frequently Asked Questions</h2>
            <p className="text-gray-400">Answers to common questions about Seamount and USDS</p>
          </div>
          
          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <div 
                key={index}
                className="bg-gradient-to-r from-gray-900/50 to-gray-800/30 rounded-xl border border-gray-800/80 overflow-hidden transition-all duration-300"
              >
                <button
                  onClick={() => toggleFaq(index)}
                  className="w-full p-5 flex items-center justify-between text-left"
                >
                  <h3 className="text-lg font-medium text-white">{faq.question}</h3>
                  {expandedFaqs.includes(index) ? (
                    <ChevronUp className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-gray-400" />
                  )}
                </button>
                
                {expandedFaqs.includes(index) && (
                  <div className="px-5 pb-5">
                    <p className="text-gray-300">{faq.answer}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contact Information */}
      <section id="contact" className="py-20 bg-gradient-to-b from-gray-900/40 to-gray-950/40 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Get in Touch</h2>
            <p className="text-gray-400 max-w-2xl mx-auto">Have questions about Seamount or USDS? Our team is here to help.</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-6">
              <div className="flex items-start space-x-4">
                <MapPin className="h-6 w-6 text-blue-500 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-semibold text-lg text-white mb-1">Our Address</h3>
                  <p className="text-gray-300">Wood Avenue, Kilimani, Nairobi, Kenya</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-4">
                <Mail className="h-6 w-6 text-green-500 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-semibold text-lg text-white mb-1">Email Us</h3>
                  <p className="text-gray-300">support@seamount.io</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-4">
                <Phone className="h-6 w-6 text-purple-500 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-semibold text-lg text-white mb-1">Call Us</h3>
                  <p className="text-gray-300">+254 751 875 374</p>
                </div>
              </div>
              
              <div>
                <h3 className="font-semibold text-lg text-white mb-3">Social Media</h3>
                <div className="flex space-x-4">
                  <a href="https://twitter.com/seamountusd" target="_blank" rel="noopener noreferrer" className="p-3 bg-gray-800 rounded-full hover:bg-blue-900/30 transition-colors">
                    <Twitter className="h-5 w-5 text-blue-400" />
                  </a>
                  <a href="https://instagram.com/seamountusd" target="_blank" rel="noopener noreferrer" className="p-3 bg-gray-800 rounded-full hover:bg-purple-900/30 transition-colors">
                    <Instagram className="h-5 w-5 text-purple-400" />
                  </a>
                </div>
              </div>
            </div>
            
            <div>
              <form className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 rounded-xl border border-gray-800/80 p-6 backdrop-blur-sm">
                <h3 className="text-xl font-bold mb-4">Send Us a Message</h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Your Name</label>
                    <input 
                      type="text" 
                      className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Full Name"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Email Address</label>
                    <input 
                      type="email" 
                      className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Email"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Message</label>
                    <textarea 
                      className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                      rows={4}
                      placeholder="Your message"
                    ></textarea>
                  </div>
                  
                  <Button className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700">
                    Send Message
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </section>

      {/* Newsletter & CTA */}
      <section className="py-20 bg-gradient-to-r from-blue-900/20 to-purple-900/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <div className="max-w-3xl mx-auto mb-12">
            <h2 className="text-3xl md:text-4xl font-bold mb-6">Ready to Transform Your Cross-Border Payments?</h2>
            <p className="text-gray-300 mb-8">
              Join thousands of users sending money globally with minimal fees and instant settlement.
            </p>
            
            <Button 
              size="lg"
              onClick={handleCTAClick}
              className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-lg"
              elevated
              animated
            >
              Sign Up Free
            </Button>
            
            <p className="mt-4 text-sm text-gray-400">
              Already have an account? <button onClick={() => {
                setActiveAuthView('login');
                setIsAuthModalOpen(true);
              }} className="text-blue-400 hover:underline">Sign In</button>
            </p>
          </div>
          
          <div className="border-t border-gray-800 pt-10 max-w-xl mx-auto">
            <h3 className="text-xl font-bold mb-4">Subscribe to Our Newsletter</h3>
            <p className="text-gray-400 mb-6">Get the latest updates on Web3 finance and cross-border payments.</p>
            
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <Button>
                Subscribe
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-950 border-t border-gray-800/60 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center space-x-3 mb-4">
                <img 
                  src="https://i.imgur.com/59eVKha.png" 
                  alt="Seamount Logo" 
                  className="w-8 h-8 object-contain filter drop-shadow-lg rounded-md"
                />
                <span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-gray-300 bg-clip-text text-transparent">
                  Seamount.io
                </span>
              </div>
              <p className="text-gray-400 text-sm">
                The future of cross-border payments for emerging markets
              </p>
            </div>
            
            <div>
              <h4 className="text-white font-medium mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="text-gray-400 hover:text-white">Features</a></li>
                <li><a href="#stablecoin" className="text-gray-400 hover:text-white">USDS Stablecoin</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white">API Documentation</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white">Security</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="text-white font-medium mb-4">Company</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#about" className="text-gray-400 hover:text-white">About Us</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white">Careers</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white">Blog</a></li>
                <li><a href="#contact" className="text-gray-400 hover:text-white">Contact</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="text-white font-medium mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="text-gray-400 hover:text-white">Privacy Policy</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white">Terms of Service</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white">Compliance</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white">AML Policy</a></li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-gray-800 pt-8 text-center text-sm text-gray-500">
            <div className="flex flex-col sm:flex-row justify-between items-center">
              <p>&copy; {new Date().getFullYear()} Seamount Technologies Ltd. All rights reserved.</p>
              <div className="flex space-x-4 mt-4 sm:mt-0">
                <div className="flex items-center">
                  <Shield className="h-4 w-4 mr-1 text-green-500" />
                  <span>GDPR Compliant</span>
                </div>
                <div className="flex items-center">
                  <Shield className="h-4 w-4 mr-1 text-blue-500" />
                  <span>USDS-Powered Fees</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </footer>
      
      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        initialView={activeAuthView}
      />
    </div>
  );
};

export default LandingPage;