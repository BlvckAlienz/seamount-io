import React, { useState, useEffect, useRef } from 'react';
import { Send, BrainCircuit } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Sidebar from '@/components/layout/Sidebar';

interface ChatMessage { role: 'user' | 'ai' | 'system'; text: string; time: string; isStreaming?: boolean; }

const OmniTerminal = () => {
  const { user, session } = useAuth();
  
  const [messages, setMessages] = useState<ChatMessage[]>([
    { 
      role: 'ai', 
      text: "👋 Welcome to SeaBrain. I'm your autonomous financial intelligence partner.\n\nI can help you analyze yield strategies and understand DeFi. What would you like to explore today?", 
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatBottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatBottom.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendStream = async (textToAnalyse: string) => {
    if (!textToAnalyse.trim() || loading) return;
    
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages(prev => [...prev, { role: 'user', text: textToAnalyse, time }]);
    setInput('');
    setLoading(true);

    // Create a placeholder for the streaming response
    setMessages(prev => [...prev, { role: 'ai', text: '', time, isStreaming: true }]);

    try {
      let baseUrl = import.meta.env.VITE_API_URL || 'https://seamount-api.onrender.com';
      if (baseUrl.includes('main3')) {
          baseUrl = 'https://seamount-api.onrender.com';
      }

      const response = await fetch(`${baseUrl}/api/v1/learn/quests/tutor/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token}`
        },
        body: JSON.stringify({
          message: textToAnalyse,
          device_tier: window.innerWidth < 768 ? 'mobile' : 'desktop'
        })
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        aiText += decoder.decode(value, { stream: true });
        
        setMessages(prev => {
          const newMsg = [...prev];
          newMsg[newMsg.length - 1].text = aiText;
          return newMsg;
        });
      }

      // Mark stream as complete
      setMessages(prev => {
        const newMsg = [...prev];
        newMsg[newMsg.length - 1].isStreaming = false;
        return newMsg;
      });

    } catch (err) {
      setMessages(prev => {
        const newMsg = [...prev];
        newMsg[newMsg.length - 1].text = "⚠️ Connection interrupted. Please check your network and try again.";
        newMsg[newMsg.length - 1].isStreaming = false;
        return newMsg;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-950 font-sans text-gray-200">
      <Sidebar />
      
      <div className="flex-1 flex flex-col items-center justify-center pt-16 lg:pt-0 relative">
        
        {/* Top Header */}
        <div className="absolute top-0 left-0 right-0 p-4 border-b border-gray-900 bg-gray-950/80 backdrop-blur-md z-10 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center shadow-lg">
              <BrainCircuit className="text-white w-5 h-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-wide">SeaBrain Terminal</h1>
              <p className="text-xs text-blue-400 font-medium tracking-widest uppercase">Autonomous Intelligence</p>
            </div>
          </div>
        </div>

        {/* Chat Area */}
        <div className="w-full max-w-4xl flex-1 overflow-y-auto p-4 md:p-8 pt-24 pb-32">
          <div className="space-y-6">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'system' ? (
                  <div className="w-full text-center text-xs text-gray-500 font-mono my-2 tracking-widest uppercase">
                    — {msg.text} —
                  </div>
                ) : (
                  <div className={`max-w-[85%] md:max-w-[75%] p-5 rounded-2xl ${
                    msg.role === 'user' 
                      ? 'bg-gradient-to-br from-blue-600 to-purple-600 text-white rounded-br-sm shadow-lg' 
                      : 'bg-gray-900 border border-gray-800 text-gray-300 rounded-bl-sm'
                  }`}>
                    <div className="whitespace-pre-wrap leading-relaxed">{msg.text}</div>
                    {msg.isStreaming && <span className="inline-block w-2 h-4 ml-1 bg-purple-400 animate-pulse" />}
                  </div>
                )}
              </div>
            ))}
            <div ref={chatBottom} />
          </div>
        </div>

        {/* Input Area */}
        <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-gray-950 via-gray-950 to-transparent">
          <div className="max-w-4xl mx-auto flex gap-3 relative">
            <textarea 
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendStream(input); }}}
              placeholder="Ask SeaBrain anything about DeFi, yields, or protocols..."
              className="w-full bg-gray-900/90 border border-gray-800 rounded-2xl pl-5 pr-14 py-4 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none shadow-2xl backdrop-blur-sm"
              rows={1}
            />
            <button 
              onClick={() => sendStream(input)}
              disabled={!input.trim() || loading}
              className="absolute right-3 top-2.5 w-10 h-10 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 text-white rounded-xl flex items-center justify-center transition-all shadow-lg"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};

export default OmniTerminal;