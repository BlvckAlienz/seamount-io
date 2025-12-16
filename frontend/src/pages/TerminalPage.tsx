// File: frontend/src/pages/TerminalPage.tsx
import React from 'react';
import Sidebar from '@/components/layout/Sidebar';
import MarketTerminal from '@/components/market/MarketTerminal'; // 🚨 FIX: Change to full page component

const TerminalPage: React.FC = () => {
  return (
    <div className="flex h-screen bg-gray-900">
      <Sidebar />
      <div className="flex-1 overflow-auto">
        <MarketTerminal />
      </div>
    </div>
  );
};

export default TerminalPage;