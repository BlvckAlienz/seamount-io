// File: frontend/src/pages/TerminalPage.tsx
import React from 'react';
import Sidebar from '@/components/layout/Sidebar';
import MarketTerminalModal from '@/components/market/MarketTerminalModal';

const TerminalPage = () => {
  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      <div className="flex-1 overflow-hidden relative">
        <div className="absolute inset-0">
          <MarketTerminalModal isOpen={true} onClose={() => {}} />
        </div>
      </div>
    </div>
  );
};

export default TerminalPage;