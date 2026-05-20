// FILE: frontend/src/pages/LearnPage.tsx
// SeaLearn — Financial Literacy Hub — Full Redesign
// Fun, gamified, chat-first UI for Quest + Wellbeing + Signal Guild

import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  BookOpen, Brain, TrendingUp, Zap, Star, Shield, Lock,
  Send, RefreshCw, ChevronRight, Award, ThumbsUp, ThumbsDown,
  Flag, ArrowUpRight, ArrowDownRight, CheckCircle, Trophy,
  Flame, Target, MessageCircle, User, Bot, Plus, X
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { apiClient } from '@/config/api'
import toast from 'react-hot-toast'
import Sidebar from '@/components/layout/Sidebar'

// ── Types ─────────────────────────────────────────────────────────────────────
interface ChatMessage { role: 'user' | 'ai'; text: string; time: string }
interface QuestTrack {
  id: string; slug: string; title: string; description: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  xp_reward: number; order_index: number
  progress: { completed: number; total: number }
}
interface WellbeingScore {
  score: number
  breakdown: Record<string, number>
  summary: string; top_action: string; risk_flags: string[]
}
interface GuildSignal {
  id: string; asset_symbol: string; direction: 'BUY' | 'SELL'
  thesis: string; timeframe: string; entry_price: number
  target_price: number; stop_loss: number; qvac_score: number
  qvac_explanation: string; qvac_recommendation: string
  upvotes: number; downvotes: number; flag_count: number
  created_at: string
}
interface XPData {
  total_xp: number
  unlocks: Record<string, boolean>
  recent_events: { event_type: string; xp_amount: number }[]
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

const DIFF_CONFIG = {
  beginner:     { color: 'text-emerald-400', bg: 'bg-emerald-400/10', emoji: '🌱' },
  intermediate: { color: 'text-amber-400',   bg: 'bg-amber-400/10',   emoji: '🔥' },
  advanced:     { color: 'text-red-400',      bg: 'bg-red-400/10',     emoji: '⚡' },
}

const REC_CONFIG: Record<string, { color: string; label: string }> = {
  STRONG_BUY:  { color: 'text-emerald-400 border-emerald-400/40 bg-emerald-400/10', label: '🚀 Strong Buy' },
  BUY:         { color: 'text-green-400 border-green-400/40 bg-green-400/10',       label: '✅ Buy' },
  NEUTRAL:     { color: 'text-gray-400 border-gray-400/40 bg-gray-400/10',          label: '⚖️ Neutral' },
  AVOID:       { color: 'text-orange-400 border-orange-400/40 bg-orange-400/10',    label: '⚠️ Avoid' },
  SCAM_ALERT:  { color: 'text-red-400 border-red-400/40 bg-red-400/10',             label: '🚨 Scam Alert' },
}

const XP_LEVEL = (xp: number) => {
  if (xp < 200)  return { level: 1, title: 'Rookie',       next: 200,  color: 'text-gray-400' }
  if (xp < 500)  return { level: 2, title: 'Learner',      next: 500,  color: 'text-emerald-400' }
  if (xp < 1000) return { level: 3, title: 'Trader',       next: 1000, color: 'text-blue-400' }
  if (xp < 2000) return { level: 4, title: 'Analyst',      next: 2000, color: 'text-purple-400' }
  return               { level: 5, title: 'Guild Master',  next: 5000, color: 'text-yellow-400' }
}

// ── Chat bubble ───────────────────────────────────────────────────────────────
const ChatBubble = ({ msg }: { msg: ChatMessage }) => (
  <div className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
      msg.role === 'ai' ? 'bg-gradient-to-br from-purple-500 to-blue-600' : 'bg-gradient-to-br from-gray-600 to-gray-700'
    }`}>
      {msg.role === 'ai' ? <Bot className="w-4 h-4 text-white" /> : <User className="w-4 h-4 text-white" />}
    </div>
    <div className={`max-w-[80%] ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
      <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
        msg.role === 'ai'
          ? 'bg-gray-800/80 border border-gray-700/60 text-gray-100 rounded-tl-sm'
          : 'bg-gradient-to-br from-blue-600 to-purple-600 text-white rounded-tr-sm'
      }`}>
        {msg.text}
      </div>
      <span className="text-xs text-gray-600 px-1">{msg.time}</span>
    </div>
  </div>
)

// ── Typing indicator ──────────────────────────────────────────────────────────
const TypingIndicator = () => (
  <div className="flex gap-3">
    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center flex-shrink-0">
      <Bot className="w-4 h-4 text-white" />
    </div>
    <div className="bg-gray-800/80 border border-gray-700/60 rounded-2xl rounded-tl-sm px-4 py-3">
      <div className="flex gap-1 items-center h-4">
        {[0,1,2].map(i => (
          <div key={i} className="w-2 h-2 rounded-full bg-gray-400"
            style={{ animation: 'bounce 1.2s infinite', animationDelay: `${i * 0.2}s` }} />
        ))}
      </div>
    </div>
  </div>
)

// ── XP Badge ──────────────────────────────────────────────────────────────────
const XPBadge = ({ xp }: { xp: number }) => {
  const lvl = XP_LEVEL(xp)
  const pct  = Math.min(100, ((xp - (lvl.level === 1 ? 0 : [0,200,500,1000,2000][lvl.level-1])) /
               (lvl.next - (lvl.level === 1 ? 0 : [0,200,500,1000,2000][lvl.level-1]))) * 100)
  return (
    <div className="flex items-center gap-3 bg-gray-800/60 border border-gray-700/50 rounded-2xl px-4 py-2.5">
      <div className="flex items-center gap-1.5">
        <Trophy className={`w-4 h-4 ${lvl.color}`} />
        <span className={`font-bold text-sm ${lvl.color}`}>Lv.{lvl.level}</span>
        <span className="text-gray-400 text-xs">{lvl.title}</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-20 h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-yellow-400 to-orange-400 rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }} />
        </div>
        <span className="text-yellow-400 font-bold text-xs flex items-center gap-0.5">
          <Zap className="w-3 h-3" />{xp.toLocaleString()}
        </span>
      </div>
    </div>
  )
}

// ── Score Ring ────────────────────────────────────────────────────────────────
const ScoreRing = ({ score }: { score: number }) => {
  const size = 120; const r = 46; const circ = 2 * Math.PI * r
  const color = score >= 70 ? '#34d399' : score >= 40 ? '#fbbf24' : '#f87171'
  const label = score >= 70 ? 'Healthy 💪' : score >= 40 ? 'Growing 🌱' : 'Needs Work ⚠️'
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1f2937" strokeWidth="10"/>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth="10"
          strokeDasharray={`${(score/100)*circ} ${circ}`} strokeLinecap="round"
          transform={`rotate(-90 ${size/2} ${size/2})`}
          style={{ transition: 'stroke-dasharray 1s ease' }}/>
        <text x="50%" y="46%" dominantBaseline="middle" textAnchor="middle"
          fill={color} fontSize="24" fontWeight="800">{score}</text>
        <text x="50%" y="66%" dominantBaseline="middle" textAnchor="middle"
          fill="#6b7280" fontSize="10">/100</text>
      </svg>
      <span className="text-xs font-medium" style={{ color }}>{label}</span>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ══════════════════════════════════════════════════════════════════════════════
const LearnPage: React.FC = () => {
  const { user } = useAuth()
  const [tab, setTab] = useState<'quests' | 'wellbeing' | 'guild'>('quests')

  // Shared
  const [xpData, setXpData]   = useState<XPData | null>(null)

  // Quest
  const [tracks,  setTracks]  = useState<QuestTrack[]>([])
  const [tutorHistory, setTutorHistory] = useState<ChatMessage[]>([
    { role: 'ai', text: "👋 Hey! I'm SeaLearn, your AI tutor.\n\nAsk me anything about crypto, investing, or personal finance — I'll explain it in plain language with real African examples.\n\nTry: \"What is yield farming?\" or \"How do I start investing with ₦10,000?\"", time: now() }
  ])
  const [tutorInput, setTutorInput] = useState('')
  const [tutorLoading, setTutorLoading] = useState(false)
  const tutorBottom = useRef<HTMLDivElement>(null)

  // Wellbeing
  const [coachHistory, setCoachHistory] = useState<ChatMessage[]>([
    { role: 'ai', text: "👋 I'm SeaCoach — your personal finance wellness coach.\n\nFirst, let's set up your profile so I can give you personalised advice. Hit 'Update Profile' below, fill in your details, then come back and ask me anything!\n\nOr just ask directly: \"How much should I save each month?\"", time: now() }
  ])
  const [coachInput, setCoachInput]     = useState('')
  const [coachLoading, setCoachLoading] = useState(false)
  const [scores, setScores]             = useState<WellbeingScore[]>([])
  const [showProfile, setShowProfile]   = useState(false)
  const [scoreLoading, setScoreLoading] = useState(false)
  const [profile, setProfile]           = useState({
    country_code: 'NG', income_range: '', income_source: '',
    savings_rate: 10, crypto_exposure_pct: 5,
    susu_ajo_participation: false, chama_participation: false,
    goals_json: {}
  })
  const [profileSaved, setProfileSaved] = useState(false)
  const coachBottom = useRef<HTMLDivElement>(null)

  // Guild
  const [signals,     setSignals]     = useState<GuildSignal[]>([])
  const [showSubmit,  setShowSubmit]  = useState(false)
  const [submitLoad,  setSubmitLoad]  = useState(false)
  const [newSig, setNewSig] = useState({
    asset_symbol: '', direction: 'BUY', thesis: '',
    timeframe: '1d', entry_price: '', target_price: '', stop_loss: ''
  })

  // ── Fetch ─────────────────────────────────────────────────────────────────
  const fetchXP = useCallback(async () => {
    try { const r = await apiClient.get('/api/v1/learn/xp'); setXpData(r.data) } catch {}
  }, [])

  const fetchTracks = useCallback(async () => {
    try {
      const r = await apiClient.get('/api/v1/learn/quests/tracks')
      setTracks(r.data.tracks || [])
    } catch { toast.error('Could not load quests') }
  }, [])

  const fetchScores = useCallback(async () => {
    try {
      const [sr, pr] = await Promise.all([
        apiClient.get('/api/v1/learn/wellbeing/scores'),
        apiClient.get('/api/v1/learn/wellbeing/profile'),
      ])
      setScores(sr.data.scores || [])
      if (pr.data.profile) { setProfile(pr.data.profile); setProfileSaved(true) }
    } catch {}
  }, [])

  const fetchSignals = useCallback(async () => {
    try { const r = await apiClient.get('/api/v1/learn/guild/signals'); setSignals(r.data.signals || []) }
    catch {}
  }, [])

  useEffect(() => {
    if (!user) return
    fetchXP()
    if (tab === 'quests')    fetchTracks()
    if (tab === 'wellbeing') fetchScores()
    if (tab === 'guild')     fetchSignals()
  }, [user, tab])

  // Auto-scroll chat
  useEffect(() => { tutorBottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [tutorHistory, tutorLoading])
  useEffect(() => { coachBottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [coachHistory, coachLoading])

  // ── Tutor chat ────────────────────────────────────────────────────────────
  const sendTutor = async () => {
    const msg = tutorInput.trim()
    if (!msg || tutorLoading) return
    setTutorInput('')
    setTutorHistory(h => [...h, { role: 'user', text: msg, time: now() }])
    setTutorLoading(true)
    try {
      const r = await apiClient.post('/api/v1/learn/quests/tutor/ask', {
        message: msg,
        device_tier: window.innerWidth < 768 ? 'mobile' : 'desktop'
      })
      setTutorHistory(h => [...h, { role: 'ai', text: r.data.response, time: now() }])
    } catch {
      setTutorHistory(h => [...h, { role: 'ai', text: '⚠️ Tutor is warming up. Try again in a moment!', time: now() }])
    }
    setTutorLoading(false)
  }

  // ── Coach chat ────────────────────────────────────────────────────────────
  const sendCoach = async () => {
    const msg = coachInput.trim()
    if (!msg || coachLoading) return
    setCoachInput('')
    setCoachHistory(h => [...h, { role: 'user', text: msg, time: now() }])
    setCoachLoading(true)
    try {
      const r = await apiClient.post('/api/v1/learn/wellbeing/coach/ask', {
        message: msg,
        device_tier: window.innerWidth < 768 ? 'mobile' : 'desktop'
      })
      setCoachHistory(h => [...h, { role: 'ai', text: r.data.response, time: now() }])
    } catch {
      setCoachHistory(h => [...h, { role: 'ai', text: '⚠️ Coach is warming up. Try again in a moment!', time: now() }])
    }
    setCoachLoading(false)
  }

  // ── Save profile + generate score ─────────────────────────────────────────
  const saveProfile = async () => {
    try {
      await apiClient.post('/api/v1/learn/wellbeing/profile', profile)
      setProfileSaved(true)
      setShowProfile(false)
      toast.success('Profile saved! 🎉')
      setCoachHistory(h => [...h, {
        role: 'ai',
        text: `Profile saved! ✅\n\nNow I know your situation better. Ask me anything, or tap "Get My Score" to see your Financial Wellbeing Score (0–100).`,
        time: now()
      }])
    } catch { toast.error('Save failed') }
  }

  const generateScore = async () => {
    if (!profileSaved) { toast.error('Save your profile first'); return }
    setScoreLoading(true)
    setCoachHistory(h => [...h, { role: 'user', text: 'Generate my Wellbeing Score', time: now() }])
    try {
      const r = await apiClient.post('/api/v1/learn/wellbeing/score')
      setScores(p => [r.data, ...p])
      fetchXP()
      setCoachHistory(h => [...h, {
        role: 'ai',
        text: `🎯 Your Wellbeing Score: ${r.data.score}/100\n\n${r.data.summary}\n\n💡 Top action: ${r.data.top_action}\n\n${r.data.risk_flags?.length ? `⚠️ Watch out: ${r.data.risk_flags.join(', ')}` : '✅ No major risk flags!'}`,
        time: now()
      }])
    } catch (e: any) {
      setCoachHistory(h => [...h, { role: 'ai', text: '⚠️ Score generation failed. Make sure your profile is filled in and try again.', time: now() }])
    }
    setScoreLoading(false)
  }

  // ── Signal submit ─────────────────────────────────────────────────────────
  const submitSignal = async () => {
    if (newSig.thesis.length < 50) { toast.error('Thesis needs 50+ characters'); return }
    setSubmitLoad(true)
    try {
      const r = await apiClient.post('/api/v1/learn/guild/signals', {
        ...newSig,
        entry_price:  parseFloat(newSig.entry_price)  || undefined,
        target_price: parseFloat(newSig.target_price) || undefined,
        stop_loss:    parseFloat(newSig.stop_loss)    || undefined,
      })
      toast.success(`Signal submitted! Score: ${r.data.qvac_score}/100 🎯`)
      setShowSubmit(false)
      setNewSig({ asset_symbol: '', direction: 'BUY', thesis: '', timeframe: '1d', entry_price: '', target_price: '', stop_loss: '' })
      fetchSignals(); fetchXP()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Signal rejected')
    }
    setSubmitLoad(false)
  }

  const vote = async (id: string, type: 'up'|'down'|'flag') => {
    try {
      await apiClient.post(`/api/v1/learn/guild/signals/${id}/vote`, { vote_type: type })
      fetchSignals()
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Vote failed') }
  }

  // ── Quick prompts ─────────────────────────────────────────────────────────
  const TUTOR_PROMPTS = ['What is yield farming?', 'How does crypto work?', 'What is a good savings rate?', 'Explain DeFi simply']
  const COACH_PROMPTS = ['Am I saving enough?', 'How should I invest ₦50,000?', 'Is my crypto exposure too high?', 'How do I start a Sacco?']

  const inp = 'w-full bg-gray-900/50 border border-gray-700/60 rounded-2xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:bg-gray-900 transition-all'

  return (
    <div className="flex h-screen bg-gray-950">
      <style>{`
        @keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-6px)} }
        .chat-scroll::-webkit-scrollbar{width:4px}
        .chat-scroll::-webkit-scrollbar-track{background:transparent}
        .chat-scroll::-webkit-scrollbar-thumb{background:#374151;border-radius:4px}
      `}</style>
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden pt-16 lg:pt-0">
        {/* Header */}
        <div className="flex-shrink-0 px-4 md:px-6 py-4 border-b border-gray-800/60 bg-gray-950">
          <div className="max-w-5xl mx-auto flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <span className="text-2xl">🎓</span> Financial Literacy
              </h1>
              <p className="text-gray-500 text-xs mt-0.5">Learn. Earn XP. Protect your money.</p>
            </div>
            {xpData && <XPBadge xp={xpData.total_xp} />}
          </div>

          {/* Tabs */}
          <div className="max-w-5xl mx-auto mt-4 flex gap-1 bg-gray-900/60 rounded-2xl p-1 w-fit">
            {[
              { id: 'quests',    emoji: '📚', label: 'Quest Tracks' },
              { id: 'wellbeing', emoji: '💚', label: 'Wellbeing' },
              { id: 'guild',     emoji: '📡', label: 'Signal Guild' },
            ].map(t => (
              <button key={t.id} onClick={() => setTab(t.id as typeof tab)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                  tab === t.id
                    ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg'
                    : 'text-gray-400 hover:text-gray-200'
                }`}>
                <span>{t.emoji}</span>
                <span className="hidden sm:inline">{t.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* ── QUESTS TAB ─────────────────────────────────────────────────── */}
        {tab === 'quests' && (
          <div className="flex-1 overflow-hidden flex flex-col md:flex-row gap-0 max-w-5xl mx-auto w-full px-4 md:px-6 py-4">

            {/* Left: track cards */}
            <div className="md:w-72 flex-shrink-0 overflow-y-auto chat-scroll pr-0 md:pr-4 mb-4 md:mb-0">
              <p className="text-xs text-gray-500 font-medium mb-3 uppercase tracking-wider">Choose a track</p>
              <div className="space-y-2">
                {tracks.map(t => {
                  const d = DIFF_CONFIG[t.difficulty]
                  const pct = t.progress.total > 0 ? (t.progress.completed / t.progress.total) * 100 : 0
                  return (
                    <button key={t.id}
                      onClick={() => setTutorInput(`Tell me about the "${t.title}" track`)}
                      className="w-full text-left bg-gray-900/60 border border-gray-800 hover:border-gray-600 rounded-2xl p-4 transition-all group">
                      <div className="flex items-start justify-between mb-2">
                        <span className={`text-lg`}>{d.emoji}</span>
                        <div className="flex items-center gap-1 text-yellow-400 text-xs">
                          <Zap className="w-3 h-3" />{t.xp_reward}
                        </div>
                      </div>
                      <p className="text-white text-sm font-semibold leading-snug mb-1 group-hover:text-purple-300 transition-colors">{t.title}</p>
                      <p className="text-gray-500 text-xs mb-3 line-clamp-2">{t.description}</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-800 rounded-full h-1">
                          <div className="bg-gradient-to-r from-purple-500 to-blue-500 h-1 rounded-full transition-all"
                            style={{ width: `${pct}%` }} />
                        </div>
                        <span className="text-xs text-gray-600">{t.progress.completed}/{t.progress.total}</span>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Right: tutor chat */}
            <div className="flex-1 flex flex-col bg-gray-900/40 border border-gray-800/60 rounded-2xl overflow-hidden">
              <div className="flex-shrink-0 px-4 py-3 border-b border-gray-800/60 flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div>
                  <p className="text-white text-sm font-semibold">SeaLearn AI Tutor</p>
                  <p className="text-emerald-400 text-xs flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block"></span> Online
                  </p>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto chat-scroll p-4 space-y-4">
                {tutorHistory.map((m, i) => <ChatBubble key={i} msg={m} />)}
                {tutorLoading && <TypingIndicator />}
                <div ref={tutorBottom} />
              </div>

              {/* Quick prompts */}
              <div className="flex-shrink-0 px-4 pt-2 flex gap-2 flex-wrap">
                {TUTOR_PROMPTS.map(p => (
                  <button key={p} onClick={() => { setTutorInput(p); }}
                    className="text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 rounded-full px-3 py-1.5 transition-colors">
                    {p}
                  </button>
                ))}
              </div>

              <div className="flex-shrink-0 p-4 flex gap-2">
                <input value={tutorInput} onChange={e => setTutorInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendTutor()}
                  placeholder="Ask anything about finance..."
                  className={inp} />
                <button onClick={sendTutor} disabled={tutorLoading || !tutorInput.trim()}
                  className="flex-shrink-0 w-11 h-11 bg-gradient-to-br from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 disabled:opacity-40 rounded-2xl flex items-center justify-center transition-all">
                  <Send className="w-4 h-4 text-white" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── WELLBEING TAB ──────────────────────────────────────────────── */}
        {tab === 'wellbeing' && (
          <div className="flex-1 overflow-hidden flex flex-col md:flex-row gap-0 max-w-5xl mx-auto w-full px-4 md:px-6 py-4">

            {/* Left: score + controls */}
            <div className="md:w-72 flex-shrink-0 overflow-y-auto chat-scroll pr-0 md:pr-4 mb-4 md:mb-0 space-y-3">

              {/* Score card */}
              {scores.length > 0 ? (
                <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-4">
                  <p className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-3">Your Score</p>
                  <div className="flex justify-center mb-3">
                    <ScoreRing score={scores[0].score} />
                  </div>
                  <div className="space-y-2">
                    {Object.entries(scores[0].breakdown || {}).map(([k, v]) => (
                      <div key={k}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-400 capitalize">{k.replace(/_/g,' ')}</span>
                          <span className="text-gray-300">{v}/25</span>
                        </div>
                        <div className="bg-gray-800 rounded-full h-1">
                          <div className="bg-gradient-to-r from-emerald-500 to-teal-400 h-1 rounded-full"
                            style={{ width: `${(v/25)*100}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                  {scores[0].risk_flags?.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {scores[0].risk_flags.map((f, i) => (
                        <div key={i} className="text-xs bg-red-400/10 text-red-400 border border-red-400/20 rounded-xl px-3 py-1.5">
                          ⚠️ {f}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-4 text-center">
                  <div className="text-4xl mb-2">🎯</div>
                  <p className="text-white text-sm font-semibold mb-1">No Score Yet</p>
                  <p className="text-gray-500 text-xs">Set up your profile and generate your score below</p>
                </div>
              )}

              {/* Action buttons */}
              <button onClick={() => setShowProfile(!showProfile)}
                className="w-full bg-gray-900/60 hover:bg-gray-800/60 border border-gray-700 rounded-2xl px-4 py-3 text-sm text-gray-200 font-medium transition-colors flex items-center justify-between">
                <span>📋 {showProfile ? 'Hide Profile' : 'Update Profile'}</span>
                <ChevronRight className={`w-4 h-4 transition-transform ${showProfile ? 'rotate-90' : ''}`} />
              </button>

              {showProfile && (
                <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-4 space-y-3">
                  <select value={profile.country_code} onChange={e => setProfile(p => ({ ...p, country_code: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500">
                    <option value="NG">🇳🇬 Nigeria</option>
                    <option value="KE">🇰🇪 Kenya</option>
                  </select>
                  <select value={profile.income_range} onChange={e => setProfile(p => ({ ...p, income_range: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500">
                    <option value="">Monthly income range</option>
                    <option value="0-50k">{profile.country_code==='KE'?'Under KES 50k':'Under ₦50k'}</option>
                    <option value="50k-150k">{profile.country_code==='KE'?'KES 50k–150k':'₦50k–150k'}</option>
                    <option value="150k-500k">{profile.country_code==='KE'?'KES 150k–500k':'₦150k–500k'}</option>
                    <option value="500k+">{profile.country_code==='KE'?'Over KES 500k':'Over ₦500k'}</option>
                  </select>
                  <div>
                    <p className="text-xs text-gray-400 mb-1">Savings rate: <span className="text-white">{profile.savings_rate}%</span></p>
                    <input type="range" min={0} max={50} value={profile.savings_rate}
                      onChange={e => setProfile(p => ({ ...p, savings_rate: +e.target.value }))}
                      className="w-full accent-emerald-500" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 mb-1">Crypto exposure: <span className="text-white">{profile.crypto_exposure_pct}%</span></p>
                    <input type="range" min={0} max={100} value={profile.crypto_exposure_pct}
                      onChange={e => setProfile(p => ({ ...p, crypto_exposure_pct: +e.target.value }))}
                      className="w-full accent-yellow-500" />
                  </div>
                  <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                    <input type="checkbox" checked={profile.susu_ajo_participation}
                      onChange={e => setProfile(p => ({ ...p, susu_ajo_participation: e.target.checked }))}
                      className="accent-emerald-500 w-4 h-4" />
                    {profile.country_code==='KE' ? 'In a Chama/Sacco' : 'In an Ajo/Susu group'}
                  </label>
                  <button onClick={saveProfile}
                    className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl py-2.5 text-sm font-semibold transition-all">
                    Save Profile ✅
                  </button>
                </div>
              )}

              <button onClick={generateScore} disabled={scoreLoading || !profileSaved}
                className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 disabled:opacity-40 text-white rounded-2xl px-4 py-3 text-sm font-semibold transition-all flex items-center justify-center gap-2">
                {scoreLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Star className="w-4 h-4" />}
                Get My Score
              </button>

              {!profileSaved && (
                <p className="text-xs text-center text-gray-600">Set up your profile first ↑</p>
              )}
            </div>

            {/* Right: coach chat */}
            <div className="flex-1 flex flex-col bg-gray-900/40 border border-gray-800/60 rounded-2xl overflow-hidden">
              <div className="flex-shrink-0 px-4 py-3 border-b border-gray-800/60 flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                  <Brain className="w-4 h-4 text-white" />
                </div>
                <div>
                  <p className="text-white text-sm font-semibold">SeaCoach</p>
                  <p className="text-emerald-400 text-xs flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block"></span> Personal Finance Coach
                  </p>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto chat-scroll p-4 space-y-4">
                {coachHistory.map((m, i) => <ChatBubble key={i} msg={m} />)}
                {coachLoading && <TypingIndicator />}
                <div ref={coachBottom} />
              </div>

              <div className="flex-shrink-0 px-4 pt-2 flex gap-2 flex-wrap">
                {COACH_PROMPTS.map(p => (
                  <button key={p} onClick={() => setCoachInput(p)}
                    className="text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 rounded-full px-3 py-1.5 transition-colors">
                    {p}
                  </button>
                ))}
              </div>

              <div className="flex-shrink-0 p-4 flex gap-2">
                <input value={coachInput} onChange={e => setCoachInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendCoach()}
                  placeholder="Ask your coach anything..."
                  className={inp} />
                <button onClick={sendCoach} disabled={coachLoading || !coachInput.trim()}
                  className="flex-shrink-0 w-11 h-11 bg-gradient-to-br from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-40 rounded-2xl flex items-center justify-center transition-all">
                  <Send className="w-4 h-4 text-white" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── GUILD TAB ──────────────────────────────────────────────────── */}
        {tab === 'guild' && (
          <div className="flex-1 overflow-y-auto chat-scroll p-4 md:p-6">
            <div className="max-w-3xl mx-auto space-y-4">

              {!xpData?.unlocks?.view_signals ? (
                <div className="bg-gray-900/60 border border-amber-500/30 rounded-2xl p-8 text-center">
                  <div className="text-5xl mb-4">🔒</div>
                  <h2 className="text-white font-bold text-lg mb-2">Signal Guild Locked</h2>
                  <p className="text-gray-400 text-sm mb-4">
                    Complete a quest lesson to earn <span className="text-yellow-400 font-bold">50 XP</span> and unlock community signals.
                  </p>
                  <button onClick={() => setTab('quests')}
                    className="bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl px-6 py-3 text-sm font-semibold">
                    Start Learning →
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-white font-bold">📡 Signal Guild</h2>
                      <p className="text-gray-500 text-xs mt-0.5">Community signals — educational only, not financial advice</p>
                    </div>
                    {xpData?.unlocks?.submit_signal && (
                      <button onClick={() => setShowSubmit(!showSubmit)}
                        className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white rounded-xl px-4 py-2 text-sm font-semibold transition-all">
                        <Plus className="w-4 h-4" /> Submit
                      </button>
                    )}
                  </div>

                  {/* Submit form */}
                  {showSubmit && (
                    <div className="bg-gray-900/60 border border-blue-500/30 rounded-2xl p-5 space-y-3">
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-white font-semibold text-sm">New Signal</p>
                        <button onClick={() => setShowSubmit(false)}><X className="w-4 h-4 text-gray-500" /></button>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {[
                          { placeholder: 'Asset (BTC, ETH...)', key: 'asset_symbol', transform: (v:string) => v.toUpperCase() },
                          { placeholder: 'Entry price', key: 'entry_price', type: 'number' },
                          { placeholder: 'Target price', key: 'target_price', type: 'number' },
                          { placeholder: 'Stop loss ⚠️', key: 'stop_loss', type: 'number' },
                        ].map(f => (
                          <input key={f.key} placeholder={f.placeholder} type={f.type || 'text'}
                            value={(newSig as any)[f.key]}
                            onChange={e => setNewSig(s => ({ ...s, [f.key]: f.transform ? f.transform(e.target.value) : e.target.value }))}
                            className="bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500" />
                        ))}
                        <select value={newSig.direction} onChange={e => setNewSig(s => ({ ...s, direction: e.target.value }))}
                          className="bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500">
                          <option value="BUY">BUY</option>
                          <option value="SELL">SELL</option>
                        </select>
                        <select value={newSig.timeframe} onChange={e => setNewSig(s => ({ ...s, timeframe: e.target.value }))}
                          className="bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500">
                          {['1h','4h','1d','1w'].map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                      </div>
                      <textarea value={newSig.thesis} onChange={e => setNewSig(s => ({ ...s, thesis: e.target.value }))}
                        placeholder="Your thesis — explain WHY (min 50 chars). What's your reasoning? Technical pattern? News catalyst?"
                        rows={3}
                        className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500 resize-none" />
                      <div className="flex items-center justify-between">
                        <p className="text-xs text-gray-600">AI validates all signals. Spam = ban. 🚨</p>
                        <button onClick={submitSignal} disabled={submitLoad}
                          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded-xl px-5 py-2 text-sm font-semibold transition-all flex items-center gap-2">
                          {submitLoad ? <RefreshCw className="w-3 h-3 animate-spin" /> : null} Submit
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Signal cards */}
                  {signals.length === 0 ? (
                    <div className="text-center py-16 text-gray-600">
                      <div className="text-4xl mb-3">📡</div>
                      <p>No signals yet. Be the first to contribute.</p>
                    </div>
                  ) : signals.map(sig => {
                    const rec = REC_CONFIG[sig.qvac_recommendation] || REC_CONFIG.NEUTRAL
                    return (
                      <div key={sig.id} className="bg-gray-900/60 border border-gray-800 hover:border-gray-700 rounded-2xl p-5 transition-all">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-white font-bold text-lg">{sig.asset_symbol}</span>
                            <span className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-semibold ${
                              sig.direction === 'BUY' ? 'bg-emerald-400/10 text-emerald-400' : 'bg-red-400/10 text-red-400'
                            }`}>
                              {sig.direction === 'BUY' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                              {sig.direction}
                            </span>
                            <span className="text-xs text-gray-500 bg-gray-800 rounded-full px-2 py-0.5">{sig.timeframe}</span>
                            <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${rec.color}`}>{rec.label}</span>
                          </div>
                          <span className="text-xs text-gray-600 flex-shrink-0">Score: {sig.qvac_score}/100</span>
                        </div>

                        {sig.qvac_explanation && (
                          <div className="bg-purple-500/5 border border-purple-500/20 rounded-xl p-3 mb-3">
                            <p className="text-xs text-purple-400 font-medium mb-1">🤖 AI Analysis</p>
                            <p className="text-gray-300 text-sm">{sig.qvac_explanation}</p>
                          </div>
                        )}

                        <p className="text-gray-400 text-sm mb-3 line-clamp-2">{sig.thesis}</p>

                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="flex items-center gap-3 text-xs text-gray-500">
                            {sig.entry_price  && <span>Entry <span className="text-gray-300">${sig.entry_price}</span></span>}
                            {sig.target_price && <span>Target <span className="text-emerald-400">${sig.target_price}</span></span>}
                            {sig.stop_loss    && <span>SL <span className="text-red-400">${sig.stop_loss}</span></span>}
                          </div>
                          {xpData?.unlocks?.vote && (
                            <div className="flex items-center gap-1">
                              <button onClick={() => vote(sig.id,'up')}
                                className="flex items-center gap-1 text-xs text-gray-400 hover:text-emerald-400 bg-gray-800 hover:bg-gray-700 rounded-lg px-2.5 py-1.5 transition-colors">
                                <ThumbsUp className="w-3 h-3" />{sig.upvotes}
                              </button>
                              <button onClick={() => vote(sig.id,'down')}
                                className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-400 bg-gray-800 hover:bg-gray-700 rounded-lg px-2.5 py-1.5 transition-colors">
                                <ThumbsDown className="w-3 h-3" />{sig.downvotes}
                              </button>
                              <button onClick={() => vote(sig.id,'flag')}
                                className="flex items-center gap-1 text-xs text-gray-400 hover:text-orange-400 bg-gray-800 hover:bg-gray-700 rounded-lg px-2.5 py-1.5 transition-colors">
                                <Flag className="w-3 h-3" />{sig.flag_count}
                              </button>
                            </div>
                          )}
                        </div>
                        <p className="text-xs text-gray-700 mt-2">Community educational content only — not financial advice.</p>
                      </div>
                    )
                  })}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default LearnPage