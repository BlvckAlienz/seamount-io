// File: frontend/src/pages/PredictionsPage.tsx
import React from 'react';
import Sidebar from '@/components/layout/Sidebar';
import PredictionMarketsPage from './PredictionMarketsPage';

const PredictionsPage = () => {
  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      <div className="flex-1 overflow-y-auto">
        <PredictionMarketsPage />
      </div>
    </div>
  );
};

export default PredictionsPage;