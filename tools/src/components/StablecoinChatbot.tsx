import React, { useState, useRef, useEffect } from 'react';

interface Message {
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

const StablecoinChatbot = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      text: "Hi! I'm here to help you understand how stablecoins work and how Seamount makes cross-border payments better. What would you like to know?",
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const botResponses: { [key: string]: string } = {
    'what is a stablecoin': 'Stablecoins are digital currencies pegged 1:1 to stable assets like USD. They combine the stability of traditional money with the benefits of blockchain: fast, cheap, and borderless transfers.',
    'how do stablecoins work': 'Stablecoins maintain their value through reserves. For every 1 USDS issued, Seamount holds $1 in cash or cash equivalents. Regular audits ensure transparency.',
    'why use stablecoins': 'Stablecoins eliminate FX volatility, reduce transfer costs by 60-80%, settle in minutes instead of days, and work 24/7 unlike banks.',
    'is it safe': 'Yes! Seamount uses regulated stablecoins with full reserve backing. Your funds are protected by bank-level security and regular audits.',
    'how to get started': 'Simply sign up, verify your identity, and you can start sending money instantly. You can fund your account via bank transfer, mobile money, or card.',
    'fees': 'Seamount charges just 1-3% compared to 8-15% for traditional methods. No hidden FX spreads or surprise fees.',
    'countries': 'We support 60+ countries including Nigeria, Kenya, Ghana, South Africa, US, UK, Canada, UAE, and more.',
    'business use': 'Businesses use Seamount for global payroll, supplier payments, treasury management, and to earn yield on idle funds. API available for automation.',
    'default': "I'm here to help you understand stablecoins and cross-border payments! Ask me about: what stablecoins are, how they work, safety, fees, or how to get started."
  };

  const handleSend = () => {
    if (!inputText.trim()) return;

    // Add user message
    const userMessage: Message = {
      text: inputText,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');

    // Bot response (simulated delay)
    setTimeout(() => {
      const lowerInput = inputText.toLowerCase();
      let response = botResponses['default'];

      // Find matching response
      for (const [key, value] of Object.entries(botResponses)) {
        if (lowerInput.includes(key)) {
          response = value;
          break;
        }
      }

      const botMessage: Message = {
        text: response,
        sender: 'bot',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
    }, 1000);
  };

  const quickQuestions = [
    "What is a stablecoin?",
    "How do stablecoins work?",
    "Why use stablecoins?",
    "Is it safe?",
    "What are the fees?"
  ];

  return (
    <>
      {/* Chatbot Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 rounded-full shadow-lg z-50 hover:from-blue-700 hover:to-purple-700 transition-all"
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {/* Chatbot Window */}
      {isOpen && (
        <div className="fixed bottom-20 right-6 w-80 h-96 bg-white rounded-lg shadow-xl z-50 flex flex-col border border-gray-200">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 rounded-t-lg">
            <h3 className="font-bold">Stablecoin Assistant</h3>
            <p className="text-sm opacity-90">Ask me about stablecoins & payments</p>
          </div>

          {/* Messages */}
          <div className="flex-1 p-4 overflow-y-auto bg-gray-50">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`mb-3 ${msg.sender === 'user' ? 'text-right' : 'text-left'}`}
              >
                <div
                  className={`inline-block p-3 rounded-lg max-w-[80%] ${
                    msg.sender === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-800'
                  }`}
                >
                  {msg.text}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Questions */}
          <div className="p-2 bg-gray-100 border-t">
            <div className="flex flex-wrap gap-1 mb-2">
              {quickQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => setInputText(q)}
                  className="text-xs bg-white border border-gray-300 rounded px-2 py-1 hover:bg-gray-50"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Input */}
          <div className="p-2 border-t">
            <div className="flex">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask about stablecoins..."
                className="flex-1 border border-gray-300 rounded-l-lg p-2 text-sm"
              />
              <button
                onClick={handleSend}
                className="bg-blue-600 text-white px-4 rounded-r-lg hover:bg-blue-700"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default StablecoinChatbot;