import React, { useState } from 'react';
import { Search, Bell, Menu, User, ChevronDown, Wifi, WifiOff } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Search, Bell, Menu, User, ChevronDown, Wifi, WifiOff, Settings, LogOut, Key } from 'lucide-react';

interface HeaderProps {
  onMenuClick: () => void;
}

const Header: React.FC<HeaderProps> = ({ onMenuClick }) => {
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const { user, signOut, kycStatus } = useAuth();
  const navigate = useNavigate();
  const [connectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('connected');
  const [notificationsCount] = useState<number>(3);

  return (
    <header className="bg-gradient-to-r from-gray-950/80 via-gray-900/80 to-gray-950/80 border-b border-gray-800/50 backdrop-blur-xl sticky top-0 z-40 px-4 lg:px-6 py-4 shadow-lg">
      <div className="flex items-center justify-between">
        {/* Left section */}
        <div className="flex items-center space-x-4">
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 rounded-xl text-gray-400 hover:text-white hover:bg-gray-800/60 transition-all duration-200"
          >
            <Menu className="h-5 w-5" />
          </button>
          
          {/* Search */}
          <div className="relative hidden md:block">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search assets, transactions..."
              className="block w-80 pl-10 pr-3 py-2.5 border border-gray-700/60 rounded-xl bg-gradient-to-r from-gray-800/40 to-gray-700/30 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200 shadow-inner"
            />
          </div>

          {/* Connection Status */}
          <div className="hidden lg:flex items-center space-x-2 px-3 py-1.5 bg-gradient-to-r from-gray-800/40 to-gray-700/40 rounded-lg border border-gray-700/50 shadow-inner">
            {connectionStatus === 'connected' ? (
              <Wifi className="h-4 w-4 text-emerald-400 animate-pulse" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-400" />
            )}
            <span className={`text-xs font-medium ${
              connectionStatus === 'connected' ? 'text-emerald-400' : 'text-red-400'
            }`}>
              {connectionStatus === 'connected' ? 'Live Data' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* Right section */}
        <div className="flex items-center space-x-4">
          {/* Mobile search */}
          <button className="md:hidden p-2 rounded-xl text-gray-400 hover:text-white hover:bg-gray-800/60 transition-all duration-200">
            <Search className="h-5 w-5" />
          </button>

          {/* Notifications */}
          <button className="relative p-2 rounded-xl text-gray-400 hover:text-white hover:bg-gray-800/60 transition-all duration-200 group">
            <Bell className="h-5 w-5" />
            {notificationsCount > 0 && (
              <>
                <span className="absolute -top-1 -right-1 flex items-center justify-center h-4 w-4 rounded-full bg-gradient-to-r from-red-500 to-pink-500 text-white text-xs font-bold animate-pulse">
                  {notificationsCount}
                </span>
                <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-pink-500/20 animate-ping"></span>
              </>
            )}
            <div className="absolute top-full right-0 mt-1 w-60 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-300 transform origin-top-right scale-95 group-hover:scale-100">
              <div className="bg-gray-800 border border-gray-700 rounded-lg shadow-xl p-2">
                <div className="text-xs text-gray-400 p-2">Recent Notifications</div>
                <div className="text-white text-sm p-2 hover:bg-gray-700 rounded">New trading alert: BTC</div>
              </div>
            </div>
          </button>

          {/* Profile dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className="flex items-center space-x-3 p-2 rounded-xl text-gray-300 hover:text-white hover:bg-gradient-to-r hover:from-gray-800/60 hover:to-gray-700/60 transition-all duration-200 group"
            >
              <div className="relative">
                <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 via-teal-500 to-emerald-500 flex items-center justify-center shadow-lg">
                  {user?.email ? (
                    <span className="text-xs font-bold text-white">
                      {user.email.charAt(0).toUpperCase()}
                    </span>
                  ) : (
                    <User className="h-4 w-4 text-white" />
                  )}
                </div>
                <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-emerald-400 border-2 border-gray-900 rounded-full animate-pulse shadow-emerald-500/50"></div>
              </div>
              <div className="hidden md:block text-left">
                <div className="text-sm font-medium bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                  {user?.email ? user.email.split('@')[0] : 'Guest'}
                </div>
                <div className="text-xs text-blue-400">
                  {kycStatus === 'approved' ? 'Verified User' : kycStatus === 'pending' ? 'Pending Verification' : 'Unverified User'}
                </div>
              </div>
              <ChevronDown className="h-4 w-4 transition-transform group-hover:rotate-180" />
            </button>

            {showProfileMenu && (
              <>
                <div 
                  className="fixed inset-0 z-40" 
                  onClick={() => setShowProfileMenu(false)}
                />
                <div className="absolute right-0 mt-2 w-56 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 backdrop-blur-xl">
                  <button
                    onClick={() => {
                      setShowProfileMenu(false);
                      navigate('/settings');  // âœ… Navigate, don't logout
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-gray-300 transition-colors rounded-t-lg text-left"
                  >
                    <Settings className="h-4 w-4" />
                    <span>Settings</span>
                  </button>
                  {/* 🔒 ADD THIS EXACTLY HERE - Backup Wallet Seeds */}
                  <button
                    onClick={() => {
                      setShowProfileMenu(false);
                      navigate('/wallet-recovery');
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-yellow-400 transition-colors text-left"
                  >
                    <Key className="h-4 w-4" />
                    <span>Backup Wallet Seeds</span>
                  </button>
                  <button
                    onClick={() => {
                      setShowProfileMenu(false);
                      signOut();  // âœ… THIS should trigger logout
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-red-400 transition-colors rounded-b-lg text-left"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Logout</span>
                  </button>
                  <button
                    onClick={() => {
                      setShowProfileMenu(false);
                      navigate('/wallet-recovery');
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-yellow-400 transition-colors text-left"
                  >
                    <Key className="h-4 w-4" />
                    <span>Backup Wallet Seeds</span>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;