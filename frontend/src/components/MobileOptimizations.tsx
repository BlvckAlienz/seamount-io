import React, { useState, useEffect } from 'react';
import { Smartphone, Tablet, Monitor, Wifi, WifiOff } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface MobileOptimizationsProps {
  children: React.ReactNode;
}

const MobileOptimizations: React.FC<MobileOptimizationsProps> = ({ children }) => {
  const [deviceType, setDeviceType] = useState<'mobile' | 'tablet' | 'desktop'>('desktop');
  const { user, kycStatus } = useAuth();
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [touchSupport, setTouchSupport] = useState(false);

  useEffect(() => {
    // Detect device type
    const checkDevice = () => {
      const width = window.innerWidth;
      if (width < 768) {
        setDeviceType('mobile');
      } else if (width < 1024) {
        setDeviceType('tablet');
      } else {
        setDeviceType('desktop');
      }
    };

    // Detect touch support
    setTouchSupport('ontouchstart' in window || navigator.maxTouchPoints > 0);

    // Set up listeners
    checkDevice();
    window.addEventListener('resize', checkDevice);
    
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('resize', checkDevice);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Mobile-specific styles
  const mobileClasses = deviceType === 'mobile' ? 'touch-optimization' : '';

  return (
    <div className={`${mobileClasses} ${touchSupport ? 'touch-device' : 'no-touch'}`}>
      {/* Mobile Status Bar */}
      {deviceType === 'mobile' && (
        <div className="fixed top-0 left-0 right-0 bg-gray-950/95 backdrop-blur-xl border-b border-gray-800 px-4 py-2 z-50 flex items-center justify-between">
          <div className="flex items-center space-x-1">
            <Smartphone className="h-4 w-4 text-blue-400" />
            <span className="text-xs text-gray-400 truncate">{user?.email?.split('@')[0] || 'Guest'}</span>
          </div>
          <div className="flex items-center space-x-2">
            {isOnline ? (
              <Wifi className="h-4 w-4 text-green-400" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-400" />
            )}
            <span className="text-xs text-gray-400 truncate">
              {isOnline ? (kycStatus === 'approved' ? 'Verified' : 'Unverified') : 'Offline'}
            </span>
          </div>
        </div>
      )}

      {/* Offline Banner */}
      {!isOnline && (
        <div className="fixed top-0 left-0 right-0 bg-red-600 text-white text-center py-2 z-50">
          <span className="text-sm">Connection lost. Some features may be limited.</span>
        </div>
      )}

      {/* Main Content with Mobile Padding */}
      <div className={deviceType === 'mobile' ? 'pt-12' : ''}>
        {children}
      </div>

      <style>{`
        .touch-optimization {
          /* Larger touch targets for mobile */
        }
        
        .touch-optimization button,
        .touch-optimization a,
        .touch-optimization input {
          min-height: 44px;
          min-width: 44px;
        }
        
        .touch-device {
          /* Remove hover effects on touch devices */
        }
        
        @media (max-width: 768px) {
          .touch-optimization {
            /* Mobile-specific optimizations */
          }
          
          /* Improve scroll performance */
          * {
            -webkit-overflow-scrolling: touch;
          }
          
          /* Prevent zoom on input focus */
          input, select, textarea {
            font-size: 16px !important;
          }
        }
      `}</style>
    </div>
  );
};

export default MobileOptimizations;