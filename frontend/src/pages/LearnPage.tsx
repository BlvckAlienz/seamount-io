// FILE: frontend/src/pages/LearnPage.tsx
// Financial Literacy Hub — Loops A (Quest), C (Wellbeing), D (Signal Guild)

import React, { useState, useEffect, useCallback } from 'react'
import {
    BookOpen, Brain, TrendingUp, Star, Shield, ChevronRight,
    CheckCircle, XCircle, Zap, Award, AlertTriangle, RefreshCw,
    ThumbsUp, ThumbsDown, Flag, Lock, ArrowUpRight, ArrowDownRight
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { apiClient } from '@/config/api'
import toast from 'react-hot-toast'
import Sidebar from '@/components/layout/Sidebar'

// ── Types ─────────────────────────────────────────────────────────────────────
interface QuestTrack {
    id: string; slug: string; title: string; description: string
    difficulty: 'beginner' | 'intermediate' | 'advanced'
    xp_reward: number; order_index: number
    progress: { completed: number; total: number }
}

interface WellbeingScore {
    score: number
    breakdown: { savings_health: number; debt_management: number; investment_readiness: number; financial_resilience: number }
    summary: string; top_action: string; risk_flags: string[]
    created_at?: string
}

interface FinancialProfile {
    country_code: string; income_range: string; income_source: string
    savings_rate: number; crypto_exposure_pct: number
    susu_ajo_participation: boolean; chama_participation: boolean
    goals_json: Record<string, unknown>
}

interface GuildSignal {
    id: string; asset_symbol: string; direction: 'BUY' | 'SELL'; thesis: string
    timeframe: string; entry_price: number; target_price: number; stop_loss: number
    qvac_score: number; qvac_explanation: string; qvac_recommendation: string
    upvotes: number; downvotes: number; flag_count: number; created_at: string
    guild_reputation: { reputation_score: number; accuracy_rate: number }
}

interface XPData {
    total_xp: number
    unlocks: Record<string, boolean>
    recent_events: { event_type: string; xp_amount: number; created_at: string }[]
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const DIFFICULTY_COLORS = {
    beginner:     'text-green-400 bg-green-400/10',
    intermediate: 'text-yellow-400 bg-yellow-400/10',
    advanced:     'text-red-400 bg-red-400/10',
}

const RECOMMENDATION_COLORS: Record<string, string> = {
    STRONG_BUY:  'text-green-400 bg-green-400/10 border-green-400/30',
    BUY:         'text-emerald-400 bg-emerald-400/10 border-emerald-400/30',
    NEUTRAL:     'text-gray-400 bg-gray-400/10 border-gray-400/30',
    AVOID:       'text-orange-400 bg-orange-400/10 border-orange-400/30',
    SCAM_ALERT:  'text-red-400 bg-red-400/10 border-red-400/30',
}

function ScoreRing({ score, size = 80 }: { score: number; size?: number }) {
    const r   = (size - 8) / 2
    const circ = 2 * Math.PI * r
    const pct  = (score / 100) * circ
    const color = score >= 70 ? '#34d399' : score >= 40 ? '#fbbf24' : '#f87171'
    return (
        <svg width={size} height={size}>
            <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#374151" strokeWidth="8" />
            <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth="8"
                strokeDasharray={`${pct} ${circ}`} strokeLinecap="round"
                transform={`rotate(-90 ${size/2} ${size/2})`} />
            <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle"
                fill={color} fontSize={size * 0.22} fontWeight="bold">{score}</text>
        </svg>
    )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
const LearnPage: React.FC = () => {
    const { user } = useAuth()
    const [activeTab, setActiveTab] = useState<'quests' | 'wellbeing' | 'guild'>('quests')

    // Shared state
    const [xpData,   setXpData]   = useState<XPData | null>(null)
    const [loading,  setLoading]  = useState(false)

    // Quest state
    const [tracks,   setTracks]   = useState<QuestTrack[]>([])
    const [tutorMsg, setTutorMsg] = useState('')
    const [tutorResp,setTutorResp]= useState('')
    const [tutorLoad,setTutorLoad]= useState(false)

    // Wellbeing state
    const [profile,  setProfile]  = useState<Partial<FinancialProfile>>({ country_code: 'NG' })
    const [scores,   setScores]   = useState<WellbeingScore[]>([])
    const [coachMsg, setCoachMsg] = useState('')
    const [coachResp,setCoachResp]= useState('')
    const [coachLoad,setCoachLoad]= useState(false)
    const [scoreLoad,setScoreLoad]= useState(false)
    const [profileSaved, setProfileSaved] = useState(false)

    // Guild state
    const [signals,  setSignals]  = useState<GuildSignal[]>([])
    const [newSignal,setNewSignal]= useState({
        asset_symbol: '', direction: 'BUY', thesis: '',
        timeframe: '1d', entry_price: '', target_price: '', stop_loss: ''
    })
    const [submitLoad, setSubmitLoad] = useState(false)
    const [validationResult, setValidationResult] = useState<Record<string, unknown> | null>(null)

    // ── Data fetching ─────────────────────────────────────────────────────────
    const fetchXP = useCallback(async () => {
        try {
            const r = await apiClient.get('/api/v1/learn/xp')
            setXpData(r.data)
        } catch { /* silent */ }
    }, [])

    const fetchTracks = useCallback(async () => {
        setLoading(true)
        try {
            const r = await apiClient.get('/api/v1/learn/quests/tracks')
            setTracks(r.data.tracks || [])
        } catch (e: any) {
            toast.error('Failed to load quest tracks')
        } finally { setLoading(false) }
    }, [])

    const fetchScores = useCallback(async () => {
        try {
            const [scoreRes, profileRes] = await Promise.all([
                apiClient.get('/api/v1/learn/wellbeing/scores'),
                apiClient.get('/api/v1/learn/wellbeing/profile'),
            ])
            setScores(scoreRes.data.scores || [])
            if (profileRes.data.profile) {
                setProfile(profileRes.data.profile)
                setProfileSaved(true)
            }
        } catch { /* silent */ }
    }, [])

    const fetchSignals = useCallback(async () => {
        try {
            const r = await apiClient.get('/api/v1/learn/guild/signals')
            setSignals(r.data.signals || [])
        } catch (e: any) {
            if (e?.response?.status === 403) {
                // XP gate — expected, not an error
            } else {
                toast.error('Failed to load signals')
            }
        }
    }, [])

    useEffect(() => {
        if (!user) return
        fetchXP()
        if (activeTab === 'quests')    fetchTracks()
        if (activeTab === 'wellbeing') fetchScores()
        if (activeTab === 'guild')     fetchSignals()
    }, [user, activeTab, fetchXP, fetchTracks, fetchScores, fetchSignals])

    // ── Quest handlers ────────────────────────────────────────────────────────
    const askTutor = async () => {
        if (!tutorMsg.trim()) return
        setTutorLoad(true); setTutorResp('')
        try {
            const r = await apiClient.post('/api/v1/learn/quests/tutor/ask', {
                message:     tutorMsg,
                device_tier: window.innerWidth < 768 ? 'mobile' : 'desktop',
            })
            setTutorResp(r.data.response)
        } catch {
            toast.error('Tutor temporarily unavailable')
        } finally { setTutorLoad(false) }
    }

    // ── Wellbeing handlers ────────────────────────────────────────────────────
    const saveProfile = async () => {
        try {
            await apiClient.post('/api/v1/learn/wellbeing/profile', profile)
            setProfileSaved(true)
            toast.success('Profile saved!')
        } catch { toast.error('Failed to save profile') }
    }

    const generateScore = async () => {
        if (!profileSaved) { toast.error('Save your financial profile first'); return }
        setScoreLoad(true)
        try {
            const r = await apiClient.post('/api/v1/learn/wellbeing/score')
            setScores(prev => [r.data, ...prev])
            toast.success(`Wellbeing Score: ${r.data.score}/100`)
        } catch (e: any) {
            toast.error(e?.response?.data?.detail || 'Score generation failed')
        } finally { setScoreLoad(false) }
    }

    const askCoach = async () => {
        if (!coachMsg.trim()) return
        setCoachLoad(true); setCoachResp('')
        try {
            const r = await apiClient.post('/api/v1/learn/wellbeing/coach/ask', {
                message:     coachMsg,
                device_tier: window.innerWidth < 768 ? 'mobile' : 'desktop',
            })
            setCoachResp(r.data.response)
        } catch { toast.error('Coach temporarily unavailable') }
        finally { setCoachLoad(false) }
    }

    // ── Guild handlers ────────────────────────────────────────────────────────
    const submitSignal = async () => {
        if (!newSignal.thesis || newSignal.thesis.length < 50) {
            toast.error('Thesis must be at least 50 characters'); return
        }
        setSubmitLoad(true); setValidationResult(null)
        try {
            const r = await apiClient.post('/api/v1/learn/guild/signals', {
                ...newSignal,
                entry_price:  parseFloat(newSignal.entry_price)  || undefined,
                target_price: parseFloat(newSignal.target_price) || undefined,
                stop_loss:    parseFloat(newSignal.stop_loss)    || undefined,
            })
            setValidationResult(r.data)
            toast.success(r.data.message)
            fetchSignals()
            setNewSignal({ asset_symbol: '', direction: 'BUY', thesis: '', timeframe: '1d', entry_price: '', target_price: '', stop_loss: '' })
        } catch (e: any) {
            const msg = e?.response?.data?.detail || 'Signal rejected'
            toast.error(msg)
            if (e?.response?.status === 422) setValidationResult({ error: msg })
        } finally { setSubmitLoad(false) }
    }

    const vote = async (signalId: string, voteType: 'up' | 'down' | 'flag') => {
        try {
            await apiClient.post(`/api/v1/learn/guild/signals/${signalId}/vote`, { vote_type: voteType })
            toast.success(voteType === 'flag' ? 'Signal flagged for review' : 'Vote recorded')
            fetchSignals()
        } catch (e: any) {
            toast.error(e?.response?.data?.detail || 'Vote failed')
        }
    }

    // ── XP bar ────────────────────────────────────────────────────────────────
    const XPBar = () => (
        <div className="flex items-center gap-3 bg-gray-800/50 rounded-xl px-4 py-2 border border-gray-700/50">
            <Zap className="w-4 h-4 text-yellow-400" />
            <span className="text-yellow-400 font-bold text-sm">{xpData?.total_xp?.toLocaleString() || 0} XP</span>
            <div className="flex gap-2 text-xs text-gray-400">
                {Object.entries(xpData?.unlocks || {}).map(([action, unlocked]) => (
                    <span key={action} className={unlocked ? 'text-green-400' : 'text-gray-600'}>
                        {unlocked ? '✓' : '🔒'} {action.replace('_', ' ')}
                    </span>
                ))}
            </div>
        </div>
    )

    return (
        <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
            <Sidebar />
            <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
                <div className="max-w-5xl mx-auto">

                    {/* Header */}
                    <div className="mb-6">
                        <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-3 mb-2">
                            <Brain className="h-7 w-7 text-purple-400" />
                            SeaLearn — Financial Intelligence Hub
                        </h1>
                        <p className="text-gray-400 text-sm">Master personal finance. Protect your money. Build wealth.</p>
                        <div className="mt-3">
                            <XPBar />
                        </div>
                    </div>

                    {/* Tabs */}
                    <div className="flex gap-2 mb-6 border-b border-gray-700">
                        {[
                            { id: 'quests',    label: 'Quest Tracks',     icon: BookOpen  },
                            { id: 'wellbeing', label: 'Wellbeing Coach',  icon: Brain     },
                            { id: 'guild',     label: 'Signal Guild',     icon: TrendingUp},
                        ].map(tab => (
                            <button key={tab.id}
                                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                                    activeTab === tab.id
                                        ? 'text-white bg-gray-800 border-b-2 border-purple-500'
                                        : 'text-gray-400 hover:text-gray-200'
                                }`}>
                                <tab.icon className="w-4 h-4" />
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    {/* ── TAB: QUEST TRACKS ──────────────────────────────────── */}
                    {activeTab === 'quests' && (
                        <div className="space-y-6">
                            {/* Quest grid */}
                            {loading ? (
                                <div className="text-center text-gray-400 py-12">Loading quests...</div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {tracks.map(track => (
                                        <div key={track.id}
                                            className="bg-gray-800/50 border border-gray-700/50 rounded-2xl p-5 hover:border-purple-500/50 transition-all">
                                            <div className="flex items-start justify-between mb-3">
                                                <div>
                                                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${DIFFICULTY_COLORS[track.difficulty]}`}>
                                                        {track.difficulty}
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-1 text-yellow-400 text-sm">
                                                    <Zap className="w-3 h-3" />
                                                    {track.xp_reward} XP
                                                </div>
                                            </div>
                                            <h3 className="text-white font-semibold mb-2">{track.title}</h3>
                                            <p className="text-gray-400 text-sm mb-4">{track.description}</p>
                                            <div className="flex items-center justify-between">
                                                <div className="flex-1 bg-gray-700 rounded-full h-1.5 mr-3">
                                                    <div className="bg-purple-500 h-1.5 rounded-full"
                                                        style={{ width: track.progress.total > 0 ? `${(track.progress.completed / track.progress.total) * 100}%` : '0%' }} />
                                                </div>
                                                <span className="text-xs text-gray-400">
                                                    {track.progress.completed}/{track.progress.total}
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* AI Tutor */}
                            <div className="bg-gray-800/50 border border-gray-700/50 rounded-2xl p-5">
                                <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
                                    <Brain className="w-5 h-5 text-purple-400" />
                                    Ask SeaLearn AI Tutor
                                </h2>
                                <div className="flex gap-2 mb-3">
                                    <input
                                        value={tutorMsg}
                                        onChange={e => setTutorMsg(e.target.value)}
                                        onKeyDown={e => e.key === 'Enter' && askTutor()}
                                        placeholder="e.g. What is yield farming? How does it compare to Ajo savings?"
                                        className="flex-1 bg-gray-700 border border-gray-600 rounded-xl px-4 py-2 text-white text-sm placeholder-gray-400 focus:outline-none focus:border-purple-500"
                                    />
                                    <button onClick={askTutor} disabled={tutorLoad || !tutorMsg.trim()}
                                        className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl text-sm font-medium transition-colors">
                                        {tutorLoad ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Ask'}
                                    </button>
                                </div>
                                {tutorResp && (
                                    <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4 text-sm text-gray-200 whitespace-pre-wrap">
                                        {tutorResp}
                                    </div>
                                )}
                                <p className="text-xs text-gray-500 mt-2">
                                    🤖 Powered by local AI — your questions never leave this device
                                </p>
                            </div>
                        </div>
                    )}

                    {/* ── TAB: WELLBEING COACH ───────────────────────────────── */}
                    {activeTab === 'wellbeing' && (
                        <div className="space-y-6">
                            {/* Latest score */}
                            {scores.length > 0 && (
                                <div className="bg-gray-800/50 border border-gray-700/50 rounded-2xl p-6">
                                    <div className="flex items-start gap-6">
                                        <ScoreRing score={scores[0].score} size={100} />
                                        <div className="flex-1">
                                            <h2 className="text-white font-bold text-lg mb-1">Your Wellbeing Score</h2>
                                            <p className="text-gray-300 text-sm mb-3">{scores[0].summary}</p>
                                            <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-3">
                                                <p className="text-purple-300 text-sm font-medium">💡 Top Action</p>
                                                <p className="text-gray-200 text-sm mt-1">{scores[0].top_action}</p>
                                            </div>
                                            {scores[0].risk_flags?.length > 0 && (
                                                <div className="mt-3 flex flex-wrap gap-2">
                                                    {scores[0].risk_flags.map((flag, i) => (
                                                        <span key={i} className="text-xs bg-red-400/10 text-red-400 border border-red-400/20 rounded-full px-2 py-1">
                                                            ⚠️ {flag}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    {/* Breakdown bars */}
                                    <div className="grid grid-cols-2 gap-3 mt-5">
                                        {Object.entries(scores[0].breakdown || {}).map(([key, val]) => (
                                            <div key={key}>
                                                <div className="flex justify-between text-xs text-gray-400 mb-1">
                                                    <span>{key.replace(/_/g, ' ')}</span>
                                                    <span>{val}/25</span>
                                                </div>
                                                <div className="bg-gray-700 rounded-full h-1.5">
                                                    <div className="bg-green-400 h-1.5 rounded-full"
                                                        style={{ width: `${(val / 25) * 100}%` }} />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Profile form */}
                            <div className="bg-gray-800/50 border border-gray-700/50 rounded-2xl p-5">
                                <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
                                    <Shield className="w-5 h-5 text-green-400" />
                                    Your Financial Profile
                                    <span className="text-xs text-gray-500 ml-2">stays on your device</span>
                                </h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {/* Country */}
                                    <div>
                                        <label className="text-xs text-gray-400 mb-1 block">Country</label>
                                        <select value={profile.country_code || 'NG'}
                                            onChange={e => setProfile(p => ({ ...p, country_code: e.target.value }))}
                                            className="w-full bg-gray-700 border border-gray-600 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500">
                                            <option value="NG">🇳🇬 Nigeria</option>
                                            <option value="KE">🇰🇪 Kenya</option>
                                        </select>
                                    </div>
                                    {/* Income range */}
                                    <div>
                                        <label className="text-xs text-gray-400 mb-1 block">Monthly Income Range</label>
                                        <select value={profile.income_range || ''}
                                            onChange={e => setProfile(p => ({ ...p, income_range: e.target.value }))}
                                            className="w-full bg-gray-700 border border-gray-600 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500">
                                            <option value="">Select range</option>
                                            <option value="0-50k">{profile.country_code === 'KE' ? 'Under KES 50k' : 'Under ₦50k'}</option>
                                            <option value="50k-150k">{profile.country_code === 'KE' ? 'KES 50k–150k' : '₦50k–150k'}</option>
                                            <option value="150k-500k">{profile.country_code === 'KE' ? 'KES 150k–500k' : '₦150k–500k'}</option>
                                            <option value="500k+">{profile.country_code === 'KE' ? 'Over KES 500k' : 'Over ₦500k'}</option>
                                        </select>
                                    </div>
                                    {/* Savings rate */}
                                    <div>
                                        <label className="text-xs text-gray-400 mb-1 block">
                                            Savings Rate: {profile.savings_rate || 0}% of income
                                        </label>
                                        <input type="range" min="0" max="50" value={profile.savings_rate || 0}
                                            onChange={e => setProfile(p => ({ ...p, savings_rate: parseInt(e.target.value) }))}
                                            className="w-full accent-green-500" />
                                    </div>
                                    {/* Crypto exposure */}
                                    <div>
                                        <label className="text-xs text-gray-400 mb-1 block">
                                            Crypto Exposure: {profile.crypto_exposure_pct || 0}% of assets
                                        </label>
                                        <input type="range" min="0" max="100" value={profile.crypto_exposure_pct || 0}
                                            onChange={e => setProfile(p => ({ ...p, crypto_exposure_pct: parseInt(e.target.value) }))}
                                            className="w-full accent-yellow-500" />
                                    </div>
                                    {/* Community savings */}
                                    <div className="flex flex-col gap-2">
                                        <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                                            <input type="checkbox" checked={profile.susu_ajo_participation || false}
                                                onChange={e => setProfile(p => ({ ...p, susu_ajo_participation: e.target.checked }))}
                                                className="accent-green-500" />
                                            Participate in {profile.country_code === 'KE' ? 'Chama' : 'Ajo/Susu'}
                                        </label>
                                        <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                                            <input type="checkbox" checked={profile.chama_participation || false}
                                                onChange={e => setProfile(p => ({ ...p, chama_participation: e.target.checked }))}
                                                className="accent-green-500" />
                                            {profile.country_code === 'KE' ? 'Member of a Sacco' : 'Cooperative member'}
                                        </label>
                                    </div>
                                </div>
                                <div className="flex gap-3 mt-4">
                                    <button onClick={saveProfile}
                                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-xl text-sm font-medium transition-colors">
                                        Save Profile
                                    </button>
                                    <button onClick={generateScore} disabled={scoreLoad || !profileSaved}
                                        className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl text-sm font-medium transition-colors">
                                        {scoreLoad ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Star className="w-4 h-4" />}
                                        Generate Score
                                    </button>
                                </div>
                            </div>

                            {/* Coach chat */}
                            <div className="bg-gray-800/50 border border-gray-700/50 rounded-2xl p-5">
                                <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
                                    <Brain className="w-5 h-5 text-green-400" />
                                    Ask SeaCoach
                                </h2>
                                <div className="flex gap-2 mb-3">
                                    <input value={coachMsg}
                                        onChange={e => setCoachMsg(e.target.value)}
                                        onKeyDown={e => e.key === 'Enter' && askCoach()}
                                        placeholder={`e.g. How should I split my salary between ${profile.country_code === 'KE' ? 'M-Shwari and' : 'PiggyVest and'} crypto?`}
                                        className="flex-1 bg-gray-700 border border-gray-600 rounded-xl px-4 py-2 text-white text-sm placeholder-gray-400 focus:outline-none focus:border-green-500"
                                    />
                                    <button onClick={askCoach} disabled={coachLoad || !coachMsg.trim()}
                                        className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-xl text-sm font-medium transition-colors">
                                        {coachLoad ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Ask'}
                                    </button>
                                </div>
                                {coachResp && (
                                    <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4 text-sm text-gray-200 whitespace-pre-wrap">
                                        {coachResp}
                                        <p className="text-xs text-gray-500 mt-3 border-t border-gray-700 pt-2">
                                            This is coaching guidance, not regulated financial advice.
                                        </p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* ── TAB: SIGNAL GUILD ──────────────────────────────────── */}
                    {activeTab === 'guild' && (
                        <div className="space-y-6">
                            {/* XP gate warning */}
                            {!xpData?.unlocks?.view_signals && (
                                <div className="bg-orange-900/20 border border-orange-500/30 rounded-2xl p-4 flex items-start gap-3">
                                    <Lock className="w-5 h-5 text-orange-400 mt-0.5" />
                                    <div>
                                        <p className="text-orange-300 font-medium">Signal Guild locked</p>
                                        <p className="text-orange-400/70 text-sm mt-1">
                                            Earn 50 XP by completing at least 1 quest lesson to unlock community signals.
                                            This protects you from scammers who target crypto newcomers.
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Submit signal */}
                            {xpData?.unlocks?.submit_signal && (
                                <div className="bg-gray-800/50 border border-gray-700/50 rounded-2xl p-5">
                                    <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
                                        <TrendingUp className="w-5 h-5 text-blue-400" />
                                        Submit a Signal
                                    </h2>
                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
                                        <input value={newSignal.asset_symbol}
                                            onChange={e => setNewSignal(s => ({ ...s, asset_symbol: e.target.value.toUpperCase() }))}
                                            placeholder="BTC, ETH, SOL..."
                                            className="bg-gray-700 border border-gray-600 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
                                        <select value={newSignal.direction}
                                            onChange={e => setNewSignal(s => ({ ...s, direction: e.target.value }))}
                                            className="bg-gray-700 border border-gray-600 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500">
                                            <option value="BUY">BUY</option>
                                            <option value="SELL">SELL</option>
                                        </select>
                                        <select value={newSignal.timeframe}
                                            onChange={e => setNewSignal(s => ({ ...s, timeframe: e.target.value }))}
                                            className="bg-gray-700 border border-gray-600 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500">
                                            {['1h','4h','1d','1w'].map(t => <option key={t} value={t}>{t}</option>)}
                                        </select>
                                        <input value={newSignal.entry_price} type="number"
                                            onChange={e => setNewSignal(s => ({ ...s, entry_price: e.target.value }))}
                                            placeholder="Entry price"
                                            className="bg-gray-700 border border-gray-600 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
                                        <input value={newSignal.target_price} type="number"
                                            onChange={e => setNewSignal(s => ({ ...s, target_price: e.target.value }))}
                                            placeholder="Target price"
                                            className="bg-gray-700 border border-gray-600 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
                                        <input value={newSignal.stop_loss} type="number"
                                            onChange={e => setNewSignal(s => ({ ...s, stop_loss: e.target.value }))}
                                            placeholder="Stop loss ⚠️ required"
                                            className="bg-gray-700 border border-gray-600 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
                                    </div>
                                    <textarea value={newSignal.thesis}
                                        onChange={e => setNewSignal(s => ({ ...s, thesis: e.target.value }))}
                                        placeholder="Your thesis (min 50 chars): Explain WHY you think this trade makes sense. Include technical or fundamental reasoning."
                                        rows={3}
                                        className="w-full bg-gray-700 border border-gray-600 rounded-xl px-3 py-2 text-white text-sm placeholder-gray-400 focus:outline-none focus:border-blue-500 mb-3 resize-none" />
                                    <div className="flex items-center justify-between">
                                        <p className="text-xs text-gray-500">
                                            AI validates all signals before posting. Scam content = account ban.
                                        </p>
                                        <button onClick={submitSignal} disabled={submitLoad}
                                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl text-sm font-medium transition-colors">
                                            {submitLoad ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Submit for Review'}
                                        </button>
                                    </div>
                                    {/* Validation result */}
                                    {validationResult && !('error' in validationResult) && (
                                        <div className="mt-3 bg-blue-900/20 border border-blue-500/30 rounded-xl p-3 text-sm">
                                            <p className="text-blue-300 font-medium">AI Analysis: Score {String(validationResult.qvac_score)}/100</p>
                                            <p className="text-gray-300 mt-1">{String(validationResult.explanation)}</p>
                                            <p className="text-xs text-gray-500 mt-2">{String(validationResult.disclaimer)}</p>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Signal list */}
                            {xpData?.unlocks?.view_signals && (
                                <div className="space-y-3">
                                    <h2 className="text-white font-semibold flex items-center gap-2">
                                        <Award className="w-5 h-5 text-yellow-400" />
                                        Community Signals
                                    </h2>
                                    {signals.length === 0 ? (
                                        <div className="text-center text-gray-400 py-12 bg-gray-800/30 rounded-2xl">
                                            No signals yet. Be the first to contribute.
                                        </div>
                                    ) : signals.map(sig => (
                                        <div key={sig.id} className="bg-gray-800/50 border border-gray-700/50 rounded-2xl p-4">
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-white font-bold">{sig.asset_symbol}</span>
                                                    <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${sig.direction === 'BUY' ? 'text-green-400 bg-green-400/10' : 'text-red-400 bg-red-400/10'}`}>
                                                        {sig.direction === 'BUY' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                                                        {sig.direction}
                                                    </span>
                                                    <span className="text-xs text-gray-400">{sig.timeframe}</span>
                                                </div>
                                                <span className={`text-xs px-2 py-1 rounded-full border font-medium ${RECOMMENDATION_COLORS[sig.qvac_recommendation] || RECOMMENDATION_COLORS.NEUTRAL}`}>
                                                    {sig.qvac_recommendation?.replace('_', ' ')}
                                                </span>
                                            </div>

                                            {/* QVAC explanation */}
                                            {sig.qvac_explanation && (
                                                <div className="bg-gray-900/50 rounded-xl p-3 mb-3 text-sm text-gray-300">
                                                    <span className="text-purple-400 text-xs font-medium">🤖 AI Analysis: </span>
                                                    {sig.qvac_explanation}
                                                </div>
                                            )}

                                            <p className="text-gray-400 text-sm mb-3 line-clamp-2">{sig.thesis}</p>

                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-3 text-xs text-gray-500">
                                                    {sig.entry_price  && <span>Entry: ${sig.entry_price}</span>}
                                                    {sig.target_price && <span className="text-green-400">Target: ${sig.target_price}</span>}
                                                    {sig.stop_loss    && <span className="text-red-400">SL: ${sig.stop_loss}</span>}
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs text-gray-500">Score: {sig.qvac_score}/100</span>
                                                    {xpData?.unlocks?.vote && (
                                                        <>
                                                            <button onClick={() => vote(sig.id, 'up')}
                                                                className="flex items-center gap-1 text-xs text-green-400 hover:text-green-300 transition-colors">
                                                                <ThumbsUp className="w-3 h-3" />{sig.upvotes}
                                                            </button>
                                                            <button onClick={() => vote(sig.id, 'down')}
                                                                className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition-colors">
                                                                <ThumbsDown className="w-3 h-3" />{sig.downvotes}
                                                            </button>
                                                            <button onClick={() => vote(sig.id, 'flag')}
                                                                className="flex items-center gap-1 text-xs text-orange-400 hover:text-orange-300 transition-colors">
                                                                <Flag className="w-3 h-3" />{sig.flag_count}
                                                            </button>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                            <p className="text-xs text-gray-600 mt-2">
                                                ⚠️ Community educational content only — not financial advice. Always do your own research.
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default LearnPage