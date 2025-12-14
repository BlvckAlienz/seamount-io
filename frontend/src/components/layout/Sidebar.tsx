// File: frontend/src/components/layout/Sidebar.tsx
// 🆕 DTCC-Inspired Sidebar Navigation

import React from 'react';
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
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

interface NavItem {
  label: string;
  icon: React.ElementType;
  path: string;
  badge?: string;
  children?: NavItem[];
}

const Sidebar: React.FC = () => {
  const location = useLocation();
  const { userProfile, signOut } = useAuth();

  const navItems: NavItem[] = [
    {
      label: 'Portfolio',
      icon: LayoutDashboard,
      path: '/dashboard',
    },
    {
      label: 'Wallets',
      icon: Wallet,
      path: '/wallets',
      children: [
        { label: 'All Wallets', icon: Coins, path: '/wallets/all' },
        { label: 'Fund', icon: ArrowDownToLine, path: '/wallets/fund' },
        { label: 'Withdraw', icon: ArrowUpRight, path: '/wallets/withdraw' },
      ],
    },
    {
      label: 'Tokenization',
      icon: Coins,
      path: '/tokenization',
      badge: 'NEW',
      children: [
        { label: 'Convert Asset', icon: RefreshCw, path: '/tokenization/convert' },
        { label: 'My Tokens', icon: Shield, path: '/tokenization/tokens' },
        { label: 'Market', icon: TrendingUp, path: '/tokenization/market' },
        { label: 'Publish Offer', icon: Plus, path: '/tokenization/publish' },
      ],
    },
    {
      label: 'Collateral',
      icon: Shield,
      path: '/collateral',
      badge: 'NEW',
      children: [
        { label: 'Create Repo', icon: Plus, path: '/collateral/create-repo' },
        { label: 'Active Repos', icon: Activity, path: '/collateral/repos' },
        { label: 'Manage', icon: Target, path: '/collateral/manage' },
        { label: 'Margin Calls', icon: AlertTriangle, path: '/collateral/margin-calls' },
      ],
    },
    {
      label: 'Trading',
      icon: TrendingUp,
      path: '/trading',
      children: [
        { label: 'Execute Trade', icon: ShoppingCart, path: '/trading/execute' },
        { label: 'My Orders', icon: FileText, path: '/trading/orders' },
        { label: 'History', icon: Clock, path: '/trading/history' },
      ],
    },
    {
      label: 'Payments',
      icon: CreditCard,
      path: '/payments',
      children: [
        { label: 'Send', icon: ArrowUpRight, path: '/payments/send' },
        { label: 'Swap', icon: RefreshCw, path: '/payments/swap' },
        { label: 'Earn', icon: TrendingUp, path: '/payments/earn' },
      ],
    },
    {
      label: 'Market Terminal',
      icon: Activity,
      path: '/market-terminal',
    },
    {
      label: 'Predictions',
      icon: Target,
      path: '/predictions',
    },
  ];

  const [expandedItems, setExpandedItems] = React.useState<string[]>([]);

  const toggleExpanded = (path: string) => {
    setExpandedItems((prev) =>
      prev.includes(path) ? prev.filter((p) => p !== path) : [...prev, path]
    );
  };

  const isActive = (path: string) => location.pathname === path;
  const isParentActive = (item: NavItem) =>
    item.children?.some((child) => location.pathname === child.path);

  return (
    <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col h-screen">
      {/* Logo */}
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-xl">S</span>
          </div>
          <div>
            <div className="text-white font-bold text-lg">Seamount</div>
            <div className="text-gray-400 text-xs">Digital Securities</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 overflow-y-auto">
        {navItems.map((item) => (
          <div key={item.path} className="mb-2">
            {/* Parent Item */}
            <Link
              to={item.children ? '#' : item.path}
              onClick={(e) => {
                if (item.children) {
                  e.preventDefault();
                  toggleExpanded(item.path);
                }
              }}
              className={`
                flex items-center justify-between px-4 py-3 rounded-lg transition-all
                ${
                  isActive(item.path) || isParentActive(item)
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/50'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }
              `}
            >
              <div className="flex items-center gap-3">
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </div>
              {item.badge && (
                <span className="px-2 py-1 text-xs bg-green-500 text-white rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>

            {/* Child Items */}
            {item.children && expandedItems.includes(item.path) && (
              <div className="ml-4 mt-2 space-y-1">
                {item.children.map((child) => (
                  <Link
                    key={child.path}
                    to={child.path}
                    className={`
                      flex items-center gap-3 px-4 py-2 rounded-lg transition-all text-sm
                      ${
                        isActive(child.path)
                          ? 'bg-blue-600/20 text-blue-400 border-l-2 border-blue-500'
                          : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50'
                      }
                    `}
                  >
                    <child.icon className="w-4 h-4" />
                    <span>{child.label}</span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        ))}
      </nav>

      {/* External Wallet Connection (Merged) */}
      <div className="p-4 border-t border-gray-800">
        <Link
          to="/wallet-connect"
          className="flex items-center gap-3 px-4 py-3 rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white transition-all"
        >
          <Link2 className="w-5 h-5" />
          <span className="font-medium">Connect External Wallet</span>
        </Link>
      </div>

      {/* User Profile */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center">
            <span className="text-white font-bold">
              {userProfile?.first_name?.[0] || 'U'}
            </span>
          </div>
          <div className="flex-1">
            <div className="text-white text-sm font-medium">
              {userProfile?.first_name || 'User'}
            </div>
            <div className="text-gray-400 text-xs">{userProfile?.email}</div>
          </div>
        </div>
        <div className="space-y-2">
          <Link
            to="/settings"
            className="flex items-center gap-2 text-gray-400 hover:text-white text-sm transition-colors"
          >
            <Settings className="w-4 h-4" />
            <span>Settings</span>
          </Link>
          <button
            onClick={signOut}
            className="flex items-center gap-2 text-red-400 hover:text-red-300 text-sm transition-colors w-full"
          >
            <LogOut className="w-4 h-4" />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;