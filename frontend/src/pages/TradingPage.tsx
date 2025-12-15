// File: frontend/src/pages/TradingPage.tsx
import React, { useState } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import MarketOffersModal from '@/components/modals/MarketOffersModal';

const TradingPage = () => {
  const [showModal, setShowModal] = useState(true);

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      <div className="flex-1 flex items-center justify-center">
        {showModal ? (
          <MarketOffersModal open={showModal} onOpenChange={setShowModal} />
        ) : (
          <div className="text-center text-gray-400">
            <p className="text-xl mb-4">Market Closed</p>
            <button
              onClick={() => setShowModal(true)}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
            >
              Reopen Market
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default TradingPage;