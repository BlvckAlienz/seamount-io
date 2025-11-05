import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Home, 
  TrendingUp,
  Wallet as WalletIcon,
  Send,
  BarChart2,
  HelpCircle,
  X,
  Activity,
} from 'lucide-react';

// ➕ ADD THIS INTERFACE
interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string | number;
}

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

// ➕ ADD TYPE ANNOTATION
const navigationItems: NavItem[] = [
  { name: 'Dashboard', href: '/app', icon: Home },
  { name: 'Wallet', href: '/app/wallet', icon: WalletIcon, badge: 'New' }, // ➕ EXAMPLE
  { name: 'Send Money', href: '/app/wallet', icon: Send },
  { name: 'Markets', href: '/app/trading', icon: TrendingUp, badge: 3 }, // ➕ EXAMPLE
  { name: 'Analytics', href: '/app/analytics', icon: BarChart2 },
];

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/80 backdrop-blur-md z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <div className={`
        fixed lg:static inset-y-0 left-0 z-50 w-72 
        bg-gradient-to-b from-gray-950/95 via-gray-900/95 to-gray-950/95
        border-r border-gray-800/50 backdrop-blur-xl shadow-2xl
        transform transition-all duration-300 ease-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="flex flex-col h-full">
          {/* Logo and close button */}
          <div className="flex items-center justify-between p-6 border-b border-gray-800/50 bg-gradient-to-r from-gray-900/70 to-gray-800/30">
            <div className="flex items-center space-x-3">
              <div className="relative">
                {/* Seamount Logo */}
                <img 
                  src="https://i.imgur.com/59eVKha.png" 
                  alt="Seamount Logo" 
                  className="w-10 h-10 object-contain filter drop-shadow-lg rounded-md"
                />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full animate-pulse shadow-lg shadow-emerald-500/40"></div>
              </div>
              <div>
                <span className="text-2xl font-bold bg-gradient-to-r from-blue-400 via-white to-gray-300 bg-clip-text text-transparent">
                  Seamount.io
                </span>
                <div className="text-xs text-emerald-400 font-medium tracking-wider">Cross-border payments for emerging markets</div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="lg:hidden p-1 rounded-md text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-1">
            {navigationItems.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={onClose}
                className={({ isActive }) => `
                  group flex items-center px-4 py-3.5 text-sm font-medium rounded-xl transition-all duration-200 relative overflow-hidden
                  ${isActive 
                    ? 'bg-gradient-to-r from-blue-600/90 to-teal-600/90 text-white shadow-lg shadow-blue-500/25 scale-[1.03] border border-blue-500/20' 
                    : 'text-gray-300 hover:bg-gradient-to-r hover:from-gray-800/80 hover:to-gray-700/80 hover:text-white hover:scale-[1.03] border border-transparent hover:border-gray-700/80'
                  }
                `}
              >
                <span className="absolute inset-0 bg-gradient-to-r from-blue-600/0 via-blue-600/5 to-transparent w-[200%] translate-x-[-100%] group-hover:animate-shine"></span>
                <item.icon className="mr-3 h-5 w-5 flex-shrink-0 transition-transform group-hover:scale-110" />
                {item.name}
                {item.name === 'Send Money' && (
                  <div className="ml-auto w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
                )}
                {item.badge && (
                  <div className="ml-auto text-xs bg-gradient-to-r from-blue-500/30 to-purple-500/30 text-blue-300 px-2.5 py-1 rounded-full border border-blue-500/30 shadow-inner">
                    {item.badge}
                  </div>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Bottom section */}
          <div className="p-4 border-t border-gray-800/50 space-y-1 bg-gradient-to-b from-transparent to-gray-900/50">
            <NavLink
              to="/help"
              onClick={onClose}
              className="group flex items-center px-4 py-3.5 text-sm font-medium text-gray-300 rounded-xl hover:bg-gradient-to-r hover:from-gray-800/80 hover:to-gray-700/80 hover:text-white hover:border-gray-700 border border-transparent transition-all duration-200"
            >
              <HelpCircle className="mr-3 h-5 w-5 flex-shrink-0 transition-transform group-hover:scale-110" />
              Help & Support
            </NavLink>
            
            {/* API Status indicator */}
            <div className="mt-4 p-4 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-xl shadow-inner">
              <div className="flex items-center space-x-2 mb-1">
                <div className="w-2.5 h-2.5 bg-green-400 rounded-full animate-pulse shadow shadow-green-400/40"></div>
                <span className="text-xs text-blue-300 font-medium tracking-wide">SYSTEM ONLINE</span>
              </div>
              <div className="text-xs text-gray-400 mt-1 ml-4.5">Flutterwave + Circle + M-Pesa</div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar;