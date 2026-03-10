// File: frontend/src/components/layout/Sidebar.tsx
// 🆕 DTCC-Inspired Sidebar Navigation - REDESIGNED

import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Briefcase,
  Coins,
  TrendingUp,
  Shield,
  Settings,
  Target,
  Activity,
  Key,
  LogOut,
  Menu,
  X,
  Lock,
  Receipt,
  BookOpen,
  Wallet,
  Waves,
  Zap,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

interface NavItem {
  label: string;
  icon: React.ElementType;
  path: string;
  badge?: string;
  businessOnly?: boolean;
  individualOnly?: boolean;
  adminOnly?: boolean;
}

const Sidebar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, userProfile, signOut } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);

  // 🚨 ALL NAV ITEMS (includes business-only features)
  const allNavItems: NavItem[] = [
    { label: 'Wallets', icon: Wallet, path: '/dashboard' },
    { label: 'XRP Ledger', icon: Waves, path: '/xrp' },
    { label: 'My Assets', icon: Briefcase, path: '/my-assets', adminOnly: true },
    { label: 'Tokenization', icon: Coins, path: '/tokenization', badge: 'NEW', adminOnly: true },
    { label: 'Market', icon: TrendingUp, path: '/trading', adminOnly: true },
    { label: 'Audit & Tax', icon: Receipt, path: '/compliance', badge: 'NG', businessOnly: true },
    { label: 'Terminal', icon: Activity, path: '/terminal' },
    { label: 'Settings', icon: Settings, path: '/settings' },
  ];

  // 🔒 FILTER: Hide business-only tabs from individual users
  const navItems = allNavItems.filter(item => {
    if (item.adminOnly) {
      return userProfile?.is_admin === true;
    }
    if (item.businessOnly) {
      return userProfile?.account_type === 'business';
    }
    if (item.individualOnly) {
      return userProfile?.account_type !== 'business';
    }
    return true;
  });

  const isActive = (path: string) => location.pathname === path;

  const handleLogout = async () => {
    try {
      await signOut();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <>
      {/* 📱 MOBILE: Hamburger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-50 lg:hidden bg-gray-800 hover:bg-gray-700 p-3 rounded-xl border border-gray-700 transition-colors shadow-lg"
        aria-label="Toggle menu"
      >
        {isOpen ? (
          <X className="h-6 w-6 text-white" />
        ) : (
          <Menu className="h-6 w-6 text-white" />
        )}
      </button>

      {/* 📱 MOBILE: Backdrop Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* 🖥️ SIDEBAR */}
      <aside
        className={`
          fixed lg:sticky top-0 left-0 h-screen
          bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900
          border-r border-gray-700/50
          transition-all duration-300 ease-in-out
          z-40
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          w-64 lg:w-20 lg:hover:w-64
          group
        `}
      >
        <div className="flex flex-col h-full">
          {/* 🏢 LOGO */}
          <div className="p-6 border-b border-gray-800">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold text-xl">S</span>
              </div>
              <div className="opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity duration-300">
                <div className="text-white font-bold text-lg">Seamount</div>
                <div className="text-gray-400 text-xs">Private Markets</div>
              </div>
            </div>
          </div>

          {/* 🧭 NAVIGATION */}
          <nav className="flex-1 p-4 overflow-y-auto">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsOpen(false)}
                  className={`
                    flex items-center gap-3 px-4 py-3 rounded-lg mb-2
                    transition-all duration-200
                    ${active
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/50'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                    }
                  `}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  <span className="font-medium whitespace-nowrap opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity duration-300">
                    {item.label}
                  </span>
                  {item.badge && (
                    <span className="ml-auto px-2 py-1 text-xs bg-green-500 text-white rounded-full opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity duration-300">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* 👤 USER PROFILE - ENHANCED VERSION FROM DASHBOARD */}
          <div className="p-4 border-t border-gray-800 relative">
            <button
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className="w-full flex items-center gap-3 hover:bg-gray-800 p-2 rounded-lg transition-colors"
            >
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold text-sm">
                  {userProfile?.first_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
                </span>
              </div>
              <div className="flex-1 text-left opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity duration-300 min-w-0">
                <div className="text-white text-sm font-medium truncate">
                  {userProfile?.first_name || user?.email?.split('@')[0] || 'User'}
                </div>
                <div className="text-gray-400 text-xs truncate">{user?.email}</div>
              </div>
            </button>

            {/* 📋 DROPDOWN MENU */}
            {showProfileMenu && (
              <>
                {/* Backdrop */}
                <div className="fixed inset-0 z-40" onClick={() => setShowProfileMenu(false)} />
                
                {/* Menu */}
                <div className="absolute bottom-full left-4 right-4 mb-2 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl z-50 overflow-hidden">
                  {/* User Info Header */}
                  <div className="px-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 border-b border-gray-700">
                    <div className="text-white font-semibold">
                      {userProfile?.first_name || 'User'}
                    </div>
                    <div className="text-blue-100 text-xs">
                      {user?.email}
                    </div>
                  </div>

                  {/* Menu Items */}
                  <div className="py-2">
                    {/* Recovery Phrases */}
                    <button 
                      onClick={() => {
                        setShowProfileMenu(false);
                        setIsOpen(false);
                        navigate('/wallet-recovery');
                      }} 
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-gray-300 transition-colors text-left"
                    >
                      <Key className="h-4 w-4 text-orange-400" />
                      <div>
                        <div className="text-sm font-medium">Recovery Phrases</div>
                        <div className="text-xs text-gray-500">View your seed phrases</div>
                      </div>
                    </button>

                    {/* Verify KYC */}
                    <button 
                      onClick={() => {
                        setShowProfileMenu(false);
                        setIsOpen(false);
                        navigate('/onboarding');
                      }} 
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-gray-300 transition-colors text-left"
                    >
                      <Shield className="h-4 w-4 text-green-400" />
                      <div>
                        <div className="text-sm font-medium">Verify Identity</div>
                        <div className="text-xs text-gray-500">Complete KYC verification</div>
                      </div>
                    </button>

                    {/* Admin Dashboard (only if admin) */}
                    {userProfile?.is_admin && (
                      <button 
                        onClick={() => {
                          setShowProfileMenu(false);
                          setIsOpen(false);
                          navigate('/admin');
                        }} 
                        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-yellow-400 transition-colors text-left border-t border-gray-700"
                      >
                        <Shield className="h-4 w-4" />
                        <div>
                          <div className="text-sm font-medium">Admin Dashboard</div>
                          <div className="text-xs text-yellow-500">Platform management</div>
                        </div>
                      </button>
                    )}

                    {/* Logout */}
                    <button 
                      onClick={() => {
                        setShowProfileMenu(false);
                        setIsOpen(false);
                        handleLogout();
                      }} 
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-red-400 transition-colors text-left border-t border-gray-700"
                    >
                      <LogOut className="h-4 w-4" />
                      <div>
                        <div className="text-sm font-medium">Logout</div>
                        <div className="text-xs text-red-500">Sign out of your account</div>
                      </div>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;