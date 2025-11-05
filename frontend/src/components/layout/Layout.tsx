import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import ErrorBoundary from '@/components/ErrorBoundary.tsx';
import ErrorTracking from '@/components/ErrorTracking.tsx';
import QuickAccessButton from '@/components/QuickAccessButton.tsx';
import Sidebar from './Sidebar';
import Header from './Header';

const Layout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate initial app loading
    const timer = setTimeout(() => setIsLoading(false), 1000);
    return () => clearTimeout(timer);
  }, []);

  if (isLoading) {
    return (
      <div className="h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full border-4 border-gray-800"></div>
            <div className="absolute inset-0 rounded-full border-4 border-t-blue-500 animate-spin"></div>
          </div>
          <div className="text-xl font-semibold text-white mb-2">Seamount.io</div>
          <div className="text-gray-400">Initializing trading terminal...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-black overflow-hidden">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header onMenuClick={() => setSidebarOpen(true)} />
        
        <main className="flex-1 overflow-auto bg-black">
          <div className="h-full p-4 lg:p-6 space-y-6">
            <ErrorBoundary>
              <Outlet />
            </ErrorBoundary>
          </div>
        </main>
      </div>
      
      {/* Quick access to help */}
      <QuickAccessButton />
    </div>
  );
};

export default Layout;