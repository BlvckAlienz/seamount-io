// File: frontend/src/App.tsx
// ✅ UNIFIED WALLET ARCHITECTURE - SINGLE PROVIDER SYSTEM

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/react';
import { api } from '@/lib/api';
import ResetPasswordPage from '@/pages/ResetPasswordPage';
import TerminalPage from './pages/TerminalPage';
import CompliancePage from './pages/CompliancePage';
import MeterXpressPage from '@/pages/MeterXpressPage';
import AuthCallbackPage from './pages/auth/AuthCallbackPage';

// ✅ ADD THESE IMPORTS
import { WagmiProvider } from 'wagmi';
import { QueryClientProvider } from '@tanstack/react-query';
import { config, queryClient } from '@/config/walletConnect';

// --- Core Components & Pages ---
import EnhancedErrorBoundary from './components/ErrorBoundary';
import ProtectedRoute from './components/auth/ProtectedRoute';
import AuthModal from './components/auth/AuthModal';
import InvestorContact from './components/InvestorContact';
import { CookieConsentBanner } from './components/CookieConsentBanner';

// --- Page Imports ---
import LandingPage from './pages/LandingPage';
import OnboardingPage from './pages/OnboardingPage';
import DashboardPage from './pages/DashboardPage';
import AdminDashboard from './pages/AdminDashboard';
import PortfolioPage from './pages/PortfolioPage';
import TradingPage from './pages/TradingPage';
import PaymentsPage from './pages/PaymentsPage';
import SettingsPage from './pages/SettingsPage';
import UserProfilePage from './pages/UserProfilePage';
import ComplianceDashboard from './pages/admin/ComplianceDashboard';
import AuthDebugPage from './pages/AuthDebugPage';
import WalletRecovery from './pages/wallet-recovery';
import WalletsPage from './pages/WalletsPage';
import TokenizationMarketPage from './pages/TokenizationMarketPage';
import CollateralPage from './pages/CollateralPage';
import PredictionMarketsPage from './pages/PredictionMarketsPage';
import MarketTerminal from './components/market/MarketTerminal';
import MyAssetsPage from '@/pages/MyAssetsPage';
import XRPPage from '@/pages/XRPPage';
import P2POrderPage from '@/pages/P2POrderPage';
import MerchantDashboardPage from '@/pages/MerchantDashboardPage';

// --- Context & Hooks ---
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { WalletOrchestratorProvider } from './contexts/WalletOrchestratorContext';
import { WalletProvider } from './contexts/WalletContext';
import { useAutoLogout } from './hooks/useAutoLogout';
import { DebugEnv } from './components/DebugEnv';

const AppContent: React.FC = () => {
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authView, setAuthView] = useState<'login' | 'register'>('register');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [consentGiven, setConsentGiven] = useState<boolean>(false);

  useAutoLogout();
  const auth = useAuth();
  const authSession = auth?.session || null;

  useEffect(() => {
    try {
      const stored = localStorage.getItem('seamount_consent_given');
      if (stored === 'true') {
        setConsentGiven(true);
      }
    } catch (error) {
      console.error('Failed to read consent:', error);
    }
  }, []);

  // ─── ADD THIS: Reset consent + session state on logout ───────────
  // Hard reload in signOut() handles most cases, but this is belt+suspenders
  // for any path that clears localStorage without a full reload
  useEffect(() => {
    if (!authSession) {
      // Delay 300ms — localStorage.clear() in signOut() runs async after
      // supabase.auth.signOut() which triggers this effect via SIGNED_OUT
      const timer = window.setTimeout(() => {
        const stored = localStorage.getItem('seamount_consent_given');
        const hasConsent = stored === 'true';
        setConsentGiven(hasConsent);
        if (!hasConsent) {
          setSessionId(null); // triggers initializeAnonymousSession re-run
        }
      }, 300);
      return () => window.clearTimeout(timer);
    }
  }, [authSession]);

  useEffect(() => {
    const initializeAnonymousSession = async () => {
      try {
        const response = await api.post('/api/v1/session/initialize');
        console.log('🔄 Session initialize response:', response);
        
        if (response && response.data) {
          setSessionId(response.data.session_id || response.data.id);
        } else if (response && response.session_id) {
          setSessionId(response.session_id);
        } else {
          console.warn('⚠️ Unexpected session response structure:', response);
          setSessionId(`anon_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
        }
      } catch (error) {
        console.error("Failed to initialize anonymous session:", error);
        setSessionId(`anon_error_${Date.now()}`);
      }
    };
    
    if (!authSession && !consentGiven) {
      initializeAnonymousSession();
    }
  }, [authSession, consentGiven]);

  const handleConsentGiven = () => {
    try {
      localStorage.setItem('seamount_consent_given', 'true');
      setConsentGiven(true);
    } catch (error) {
      console.error('Failed to save consent:', error);
    }
  };

  const handleOpenAuth = (view: 'login' | 'register') => {
    setAuthView(view);
    setShowAuthModal(true);
  };

  return (
    <>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<LandingPage onOpenAuth={handleOpenAuth} />} />
        <Route path="/contact" element={<InvestorContact />} />
        <Route path="/debug-auth" element={<AuthDebugPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        {/* OAuth callback handler */}
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        
        {/* Protected Routes */}
        <Route 
          path="/onboarding" 
          element={
            <ProtectedRoute>
              <OnboardingPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/my-assets" 
          element={
            <ProtectedRoute>
              <MyAssetsPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/profile" 
          element={
            <ProtectedRoute>
              <UserProfilePage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/settings" 
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/trading" 
          element={
            <ProtectedRoute>
              <TradingPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/payments" 
          element={
            <ProtectedRoute>
              <PaymentsPage />
            </ProtectedRoute>
          } 
        />
        <Route
          path="/p2p"
          element={<ProtectedRoute><PaymentsPage /></ProtectedRoute>}
        />
        <Route 
          path="/meter-xpress" 
          element={
            <ProtectedRoute>
              <MeterXpressPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/portfolio" 
          element={
            <ProtectedRoute>
              <PortfolioPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/wallet-recovery" 
          element={
            <ProtectedRoute>
              <WalletRecovery />
            </ProtectedRoute>
          } 
        />

        {/* 🆕 Multi-Chain Wallets Routes */}
        <Route 
          path="/wallets" 
          element={
            <ProtectedRoute>
              <WalletsPage />
            </ProtectedRoute>
          } 
        />
        {/* 🌊 XRP Ledger — Payments + Yield Farming */}
        <Route 
          path="/xrp" 
          element={
            <ProtectedRoute>
              <XRPPage />
            </ProtectedRoute>
          } 
        />
        <Route
          path="/p2p/orders/:id"
          element={
            <ProtectedRoute>
              <P2POrderPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/merchant"
          element={
            <ProtectedRoute>
              <MerchantDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route 
          path="/wallets/all" 
          element={
            <ProtectedRoute>
              <WalletsPage />
            </ProtectedRoute>
          } 
        />

        {/* 🆕 Tokenization & Secondary Market Routes - BUSINESS ONLY */}
        <Route 
          path="/tokenization" 
          element={
            <ProtectedRoute businessRequired={true}>
              <TokenizationMarketPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/tokenization/convert" 
          element={
            <ProtectedRoute businessRequired={true}>
              <TokenizationMarketPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/tokenization/tokens" 
          element={
            <ProtectedRoute businessRequired={true}>
              <TokenizationMarketPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/tokenization/market" 
          element={
            <ProtectedRoute businessRequired={true}>
              <TokenizationMarketPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/tokenization/publish" 
          element={
            <ProtectedRoute businessRequired={true}>
              <TokenizationMarketPage />
            </ProtectedRoute>
          } 
        />

        {/* 🆕 Collateral Management & Repo Trades Routes - BUSINESS ONLY */}
        <Route 
          path="/collateral" 
          element={
            <ProtectedRoute businessRequired={true}>
              <CollateralPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/collateral/create-repo" 
          element={
            <ProtectedRoute businessRequired={true}>
              <CollateralPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/collateral/repos" 
          element={
            <ProtectedRoute businessRequired={true}>
              <CollateralPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/collateral/manage" 
          element={
            <ProtectedRoute businessRequired={true}>
              <CollateralPage />
            </ProtectedRoute>
          } 
        />

        {/* 📊 Compliance & Audit Routes - BUSINESS ONLY */}
        <Route 
          path="/compliance" 
          element={
            <ProtectedRoute businessRequired={true}>
              <CompliancePage />
            </ProtectedRoute>
          } 
        />

        {/* 🆕 Market Terminal Route */}
        <Route 
          path="/terminal" 
          element={
            <ProtectedRoute>
              <TerminalPage />
            </ProtectedRoute>
          } 
        />
        
        {/* 🆕 Prediction Markets Route */}
        <Route 
          path="/predictions" 
          element={
            <ProtectedRoute>
              <PredictionMarketsPage />
            </ProtectedRoute>
          } 
        />
        
        {/* Admin Routes */}
        <Route 
          path="/admin" 
          element={
            <ProtectedRoute adminRequired={true}>
              <AdminDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/admin/compliance" 
          element={
            <ProtectedRoute adminRequired={true}>
              <ComplianceDashboard />
            </ProtectedRoute>
          } 
        />

        {/* Fallback Route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <AuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)} 
        initialView={authView}
      />

      {!authSession && !consentGiven && sessionId && (
        <CookieConsentBanner 
          sessionId={sessionId} 
          onConsentGiven={handleConsentGiven} 
        />
      )}
    </>
  );
};

function App() {
  return (
    <EnhancedErrorBoundary>
      <Router>
        {/* 🚨 CRITICAL: Provider Order Matters */}
        <WagmiProvider config={config}>
          <QueryClientProvider client={queryClient}>
            <AuthProvider>
              {/* 🌊 WalletProvider: Auto-created wallets (Algo, BTC, ETH, MATIC, TRX) */}
              <WalletProvider>
                {/* ✨ WalletOrchestratorProvider: External wallets (Base, Celo, BaseCAMP) */}
                <WalletOrchestratorProvider>
                  <DebugEnv />
                  <Toaster position="top-right" />
                  <AppContent />
                  <Analytics />
                  <SpeedInsights />
                </WalletOrchestratorProvider>
              </WalletProvider>
            </AuthProvider>
          </QueryClientProvider>
        </WagmiProvider>
      </Router>
    </EnhancedErrorBoundary>
  );
}

export default App;