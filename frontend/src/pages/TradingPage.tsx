// File: frontend/src/pages/TradingPage.tsx
import React, { useState } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import MarketOffersModal from '@/components/modals/MarketOffersModal';

const TradingPage = () => {
  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      <div className="flex-1">
        <MarketOffersModal open={true} onOpenChange={() => {}} />
      </div>
    </div>
  );
};

export default TradingPage;