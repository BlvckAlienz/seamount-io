import React, { useState, useEffect, useRef } from 'react';
import { Send, Target, Zap, ShieldAlert, X, BrainCircuit, Activity, BarChart3 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';
import Sidebar from '@/components/layout/Sidebar';

interface ChatMessage { role: 'user' | 'ai' | 'system'; text: string; time: string; isStreaming?: boolean; }

const OmniTerminal = () => {
  const { user, session } = useAuth();
  
  const [messages, setMessages] = useState<ChatMessage[]>([
    { 
      role: 'ai', 
      text: "👋 Welcome to SeaBrain. I'm your autonomous financial intelligence partner.\n\nI can help you analyze yield strategies, optimize your household budget, or validate market signals. What would you like to explore today?", 
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<'tutor' | 'coach'>('tutor');
  const chatBottom = useRef<HTMLDivElement>(null);

  // Modals
  const [showWellbeing, setShowWellbeing] = useState(false);
  const [showSignal, setShowSignal] = useState(false);
  const [profile, setProfile] = useState({ country_code: 'NG', income_range: '', savings_rate: 10, crypto_exposure_pct: 5 });
  const [signal, setSignal] = useState({ asset_symbol: '', direction: 'BUY', thesis: '', timeframe: '1d' });

  useEffect(() => {
    chatBottom.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendStream = async (textToAnalyse: string, endpoint: string) => {
    if (!textToAnalyse.trim() || loading) return;
    
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages(prev => [...prev, { role: 'user', text: textToAnalyse, time }]);
    setInput('');
    setLoading(true);

    // Create a placeholder for the streaming response
    setMessages(prev => [...prev, { role: 'ai', text: '', time, isStreaming: true }]);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}${endpoint}`, {
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

  const generateScore = async () => {
    setShowWellbeing(false);
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages(prev => [...prev, { role: 'system', text: "Analyzing financial profile...", time }]);
    
    try {
      await apiClient.post('/api/v1/learn/wellbeing/profile', profile);
      const r = await apiClient.post('/api/v1/learn/wellbeing/score');
      
      setMessages(prev => [...prev, { 
        role: 'ai', 
        text: `🎯 **Your Wellbeing Score is ${r.data.score}/100**\n\n${r.data.summary}\n\n💡 **Top Action:** ${r.data.top_action}\n\n${r.data.risk_flags?.length ? `⚠️ **Risks Detected:**\n- ${r.data.risk_flags.join('\n- ')}` : ''}`, 
        time 
      }]);
      setMode('coach'); // Switch to coach mode for follow ups
    } catch (e) {
      toast.error("Failed to generate score.");
    }
  };

  const submitSignal = async () => {
    setShowSignal(false);
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages(prev => [...prev, { role: 'system', text: `Validating ${signal.direction} signal for ${signal.asset_symbol}...`, time }]);
    
    try {
      const r = await apiClient.post('/api/v1/learn/guild/signals', signal);
      setMessages(prev => [...prev, { 
        role: 'ai', 
        text: `📡 **Signal Validated!** (Score: ${r.data.qvac_score}/100)\n\n**Analysis:** ${r.data.explanation}\n\n*${r.data.disclaimer}*`, 
        time 
      }]);
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'ai', text: `🚨 **Signal Rejected:** ${e?.response?.data?.detail || 'Validation failed.'}`, time }]);
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
          
          <div className="flex gap-2">
            <button onClick={() => setShowWellbeing(true)} className="flex items-center gap-2 bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-lg px-4 py-2 text-sm font-medium transition-all">
              <Activity className="w-4 h-4 text-emerald-400" /> Wellbeing
            </button>
            <button onClick={() => setShowSignal(true)} className="flex items-center gap-2 bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-lg px-4 py-2 text-sm font-medium transition-all">
              <BarChart3 className="w-4 h-4 text-purple-400" /> Signal
            </button>
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
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendStream(input, mode === 'tutor' ? '/api/v1/learn/quests/tutor/ask' : '/api/v1/learn/wellbeing/coach/ask'); }}}
              placeholder={`Ask SeaBrain anything about DeFi, yields, or budgets...`}
              className="w-full bg-gray-900/90 border border-gray-800 rounded-2xl pl-5 pr-14 py-4 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none shadow-2xl backdrop-blur-sm"
              rows={1}
            />
            <button 
              onClick={() => sendStream(input, mode === 'tutor' ? '/api/v1/learn/quests/tutor/ask' : '/api/v1/learn/wellbeing/coach/ask')}
              disabled={!input.trim() || loading}
              className="absolute right-3 top-2.5 w-10 h-10 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 text-white rounded-xl flex items-center justify-center transition-all shadow-lg"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Wellbeing Modal */}
        {showWellbeing && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md shadow-2xl">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-white flex items-center gap-2"><Activity className="text-emerald-400"/> Health Check</h2>
                <button onClick={() => setShowWellbeing(false)}><X className="text-gray-500 hover:text-white" /></button>
              </div>
              <div className="space-y-4">
                <select value={profile.country_code} onChange={e => setProfile({...profile, country_code: e.target.value})} className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-3 text-sm focus:border-emerald-500 outline-none">
                  <option value="NG">🇳🇬 Nigeria</option>
                  <option value="KE">🇰🇪 Kenya</option>
                </select>
                <select value={profile.income_range} onChange={e => setProfile({...profile, income_range: e.target.value})} className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-3 text-sm focus:border-emerald-500 outline-none">
                  <option value="">Select Monthly Income Range</option>
                  <option value="0-50k">Under 50k</option>
                  <option value="50k-150k">50k – 150k</option>
                  <option value="150k-500k">150k – 500k</option>
                  <option value="500k+">Over 500k</option>
                </select>
                <div>
                  <label className="text-xs text-gray-400 mb-2 block">Savings Rate: {profile.savings_rate}%</label>
                  <input type="range" min="0" max="50" value={profile.savings_rate} onChange={e => setProfile({...profile, savings_rate: parseInt(e.target.value)})} className="w-full accent-emerald-500" />
                </div>
                <button onClick={generateScore} className="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl py-3 font-semibold mt-4 transition-all">Analyze My Score</button>
              </div>
            </div>
          </div>
        )}

        {/* Signal Modal */}
        {showSignal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md shadow-2xl">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-white flex items-center gap-2"><BarChart3 className="text-purple-400"/> Validate Signal</h2>
                <button onClick={() => setShowSignal(false)}><X className="text-gray-500 hover:text-white" /></button>
              </div>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <input placeholder="Asset (e.g. BTC)" value={signal.asset_symbol} onChange={e => setSignal({...signal, asset_symbol: e.target.value.toUpperCase()})} className="bg-gray-950 border border-gray-800 rounded-xl px-4 py-3 text-sm focus:border-purple-500 outline-none uppercase" />
                  <select value={signal.direction} onChange={e => setSignal({...signal, direction: e.target.value})} className="bg-gray-950 border border-gray-800 rounded-xl px-4 py-3 text-sm focus:border-purple-500 outline-none">
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                </div>
                <textarea placeholder="Explain your thesis. Why take this trade?" rows={3} value={signal.thesis} onChange={e => setSignal({...signal, thesis: e.target.value})} className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-3 text-sm focus:border-purple-500 outline-none resize-none" />
                <button onClick={submitSignal} className="w-full bg-purple-600 hover:bg-purple-500 text-white rounded-xl py-3 font-semibold mt-2 transition-all">Validate with AI</button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default OmniTerminal;