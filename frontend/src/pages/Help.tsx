import React, { useState } from 'react';
import { Search, HelpCircle, MessageCircle, Book, Mail, Phone, ExternalLink } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

const Help: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const faqCategories = [
    { id: 'all', name: 'All Topics' },
    { id: 'trading', name: 'Trading' },
    { id: 'wallet', name: 'Wallet & USDS' },
    { id: 'security', name: 'Security' },
    { id: 'account', name: 'Account' },
  ];

  const faqs = [
    {
      id: 1,
      category: 'trading',
      question: 'How do I place my first trade?',
      answer: 'To place your first trade, navigate to the Trading page, select your desired asset, choose between market or limit order, enter the amount, and click Buy or Sell.',
    },
    {
      id: 2,
      category: 'wallet',
      question: 'What is USDS and how does it work?',
      answer: 'USDS is Seamount\'s stablecoin, pegged to the US Dollar. It provides stability for your marketData and can be used for trading, transfers, and as a safe haven during market volatility.',
    },
    {
      id: 3,
      category: 'security',
      question: 'How do I enable two-factor authentication?',
      answer: 'Go to Settings > Security, and toggle on Two-Factor Authentication. Follow the setup process to link your authenticator app or phone number.',
    },
    {
      id: 4,
      category: 'trading',
      question: 'What\'s the difference between market and limit orders?',
      answer: 'Market orders execute immediately at the current market price. Limit orders only execute when the price reaches your specified level.',
    },
    {
      id: 5,
      category: 'wallet',
      question: 'How do I send USDS to another user?',
      answer: 'In the Wallet section, click Send, enter the recipient\'s address or select from your contacts, specify the amount, and confirm the transaction.',
    },
    {
      id: 6,
      category: 'account',
      question: 'How do I verify my account?',
      answer: 'Account verification requires uploading government-issued ID and proof of address. Navigate to Settings > Profile to complete verification.',
    },
  ];

  const filteredFaqs = faqs.filter(faq => 
    (selectedCategory === 'all' || faq.category === selectedCategory) &&
    (searchQuery === '' || faq.question.toLowerCase().includes(searchQuery.toLowerCase()) || faq.answer.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3 mb-6">
        <HelpCircle className="h-8 w-8 text-blue-500" />
        <h1 className="text-2xl font-bold text-white">Help & Support</h1>
      </div>

      {/* Search and Categories */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search for help topics..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="block w-full pl-10 pr-3 py-3 border border-gray-600 rounded-lg bg-gray-700 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <div className="flex flex-wrap gap-2">
            {faqCategories.map((category) => (
              <Button
                key={category.id}
                size="sm"
                variant={selectedCategory === category.id ? 'default' : 'ghost'}
                onClick={() => setSelectedCategory(category.id)}
              >
                {category.name}
              </Button>
            ))}
          </div>
        </div>
      </Card>

      {/* Contact Options */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="text-center hover:shadow-lg transition-shadow">
          <MessageCircle className="h-12 w-12 text-blue-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Live Chat</h3>
          <p className="text-gray-400 text-sm mb-4">
            Get instant help from our support team
          </p>
          <Button className="w-full">Start Chat</Button>
        </Card>

        <Card className="text-center hover:shadow-lg transition-shadow">
          <Mail className="h-12 w-12 text-green-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Email Support</h3>
          <p className="text-gray-400 text-sm mb-4">
            Send us an email and we'll respond within 24 hours
          </p>
          <Button variant="secondary" className="w-full">Send Email</Button>
        </Card>

        <Card className="text-center hover:shadow-lg transition-shadow">
          <Book className="h-12 w-12 text-purple-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Documentation</h3>
          <p className="text-gray-400 text-sm mb-4">
            Comprehensive guides and API documentation
          </p>
          <Button variant="ghost" className="w-full">
            View Docs
          </Button>
        </Card>
      </div>

      {/* FAQ Section */}
      <Card>
        <h3 className="text-lg font-semibold text-white mb-6">Frequently Asked Questions</h3>
        
        <div className="space-y-4">
          {filteredFaqs.map((faq) => (
            <details key={faq.id} className="group">
              <summary className="flex items-center justify-between p-4 bg-gray-700/50 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors">
                <span className="font-medium text-white">{faq.question}</span>
                <HelpCircle className="h-5 w-5 text-gray-400 group-open:rotate-180 transition-transform" />
              </summary>
              <div className="p-4 text-gray-300 text-sm leading-relaxed">
                {faq.answer}
              </div>
            </details>
          ))}
        </div>

        {filteredFaqs.length === 0 && (
          <div className="text-center py-12">
            <HelpCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No results found</h3>
            <p className="text-gray-400">
              Try adjusting your search or browse by category
            </p>
          </div>
        )}
      </Card>

      {/* Additional Resources */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <h3 className="text-lg font-semibold text-white mb-4">Getting Started</h3>
          <div className="space-y-3">
            <a href="#" className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors">
              <span className="text-gray-300">Account Setup Guide</span>
              <ExternalLink className="h-4 w-4 text-gray-400" />
            </a>
            <a href="#" className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors">
              <span className="text-gray-300">First Trade Tutorial</span>
              <ExternalLink className="h-4 w-4 text-gray-400" />
            </a>
            <a href="#" className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors">
              <span className="text-gray-300">Security Best Practices</span>
              <ExternalLink className="h-4 w-4 text-gray-400" />
            </a>
          </div>
        </Card>

        <Card>
          <h3 className="text-lg font-semibold text-white mb-4">Contact Information</h3>
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <Mail className="h-5 w-5 text-blue-500" />
              <div>
                <div className="text-white font-medium">Email</div>
                <div className="text-gray-400 text-sm">support@seamount.io</div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <Phone className="h-5 w-5 text-green-500" />
              <div>
                <div className="text-white font-medium">Phone</div>
                <div className="text-gray-400 text-sm">+1 (555) 123-HELP</div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <MessageCircle className="h-5 w-5 text-purple-500" />
              <div>
                <div className="text-white font-medium">Live Chat</div>
                <div className="text-gray-400 text-sm">Available 24/7</div>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Help;