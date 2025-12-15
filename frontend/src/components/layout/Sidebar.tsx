// File: frontend/src/components/layout/Sidebar.tsx
// 🆕 DTCC-Inspired Sidebar Navigation

import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Coins,
  TrendingUp,
  RefreshCw,
  CreditCard,
  Settings,
  Link2,
  LogOut,
  Shield,
  Plus,
  Activity,
  Target,
  AlertTriangle,
  FileText,
  Clock,
  Wallet,
  ArrowDownToLine,
  ArrowUpRight,
  ShoppingCart,
  Menu,
  X,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

interface NavItem {
  label: string;
  icon: React.ElementType;
  path: string;
  badge?: string;
}

const Sidebar: React.FC = () => {
  const location = useLocation();
  const { userProfile, signOut } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  const navItems: NavItem[] = [
    { label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
    { label: 'Wallets', icon: Wallet, path: '/wallets' },
    { label: 'Tokenization', icon: Coins, path: '/tokenization', badge: 'NEW' },
    { label: 'Collateral', icon: Shield, path: '/collateral', badge: 'NEW' },
    { label: 'Trading', icon: TrendingUp, path: '/trading' },
    { label: 'Payments', icon: CreditCard, path: '/payments' },
    { label: 'Settings', icon: Settings, path: '/settings' },
  ];

  const isActive = (path: string) => location.pathname === path;

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
                <div className="text-gray-400 text-xs">Digital Securities</div>
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

          {/* 👤 USER PROFILE */}
          <div className="p-4 border-t border-gray-800">
            <div className="flex items-center gap-3 mb-3 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity duration-300">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold">
                  {userProfile?.first_name?.[0] || 'U'}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-white text-sm font-medium truncate">
                  {userProfile?.first_name || 'User'}
                </div>
                <div className="text-gray-400 text-xs truncate">{userProfile?.email}</div>
              </div>
            </div>
            <div className="space-y-2">
              <Link
                to="/settings"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-2 text-gray-400 hover:text-white text-sm transition-colors"
              >
                <Settings className="w-4 h-4 flex-shrink-0" />
                <span className="opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity duration-300">
                  Settings
                </span>
              </Link>
              <button
                onClick={() => {
                  setIsOpen(false);
                  signOut();
                }}
                className="flex items-center gap-2 text-red-400 hover:text-red-300 text-sm transition-colors w-full"
              >
                <LogOut className="w-4 h-4 flex-shrink-0" />
                <span className="opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity duration-300">
                  Logout
                </span>
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;