import React, { useState, useEffect } from 'react';

interface FXRate {
  currency: string;
  code: string;
  buyRate: number;
  sellRate: number;
  spread: number;
  lastUpdated: Date;
}

const LiveFXRates = () => {
  const [rates, setRates] = useState<FXRate[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  useEffect(() => {
    const fetchRates = async () => {
      // Simulate bank-style rate board with spreads
      const sampleRates: FXRate[] = [
        { currency: 'US Dollar', code: 'USD', buyRate: 1.00, sellRate: 1.03, spread: 3.0, lastUpdated: new Date() },
        { currency: 'British Pound', code: 'GBP', buyRate: 0.78, sellRate: 0.82, spread: 4.1, lastUpdated: new Date() },
        { currency: 'Euro', code: 'EUR', buyRate: 0.91, sellRate: 0.95, spread: 4.2, lastUpdated: new Date() },
        { currency: 'Nigerian Naira', code: 'NGN', buyRate: 1450, sellRate: 1550, spread: 6.5, lastUpdated: new Date() },
        { currency: 'Kenyan Shilling', code: 'KES', buyRate: 145, sellRate: 155, spread: 6.4, lastUpdated: new Date() },
        { currency: 'Ghanaian Cedi', code: 'GHS', buyRate: 11.5, sellRate: 12.5, spread: 8.0, lastUpdated: new Date() },
        { currency: 'South African Rand', code: 'ZAR', buyRate: 17.5, sellRate: 18.5, spread: 5.4, lastUpdated: new Date() },
      ];

      setRates(sampleRates);
      setLastUpdated(new Date());
    };

    fetchRates();
    const interval = setInterval(fetchRates, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-bold text-gray-800">🏦 Live FX Rates Board</h3>
        <div className="text-sm text-gray-600">
          Last updated: {lastUpdated.toLocaleTimeString()}
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="font-semibold text-gray-700 mb-2">Traditional Bank Spreads</h4>
          <div className="space-y-2">
            {rates.map((rate, index) => (
              <div key={index} className="flex justify-between items-center p-2 bg-red-50 rounded">
                <span className="font-medium">{rate.code}</span>
                <span className="text-red-600">{rate.spread}% spread</span>
              </div>
            ))}
          </div>
        </div>
        
        <div className="bg-green-50 p-4 rounded-lg">
          <h4 className="font-semibold text-green-800 mb-2">Seamount Advantage</h4>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Fixed Spread:</span>
              <span className="text-green-600 font-bold">1.0%</span>
            </div>
            <div className="flex justify-between">
              <span>Transfer Time:</span>
              <span className="text-green-600 font-bold">2-5 minutes</span>
            </div>
            <div className="flex justify-between">
              <span>Transparency:</span>
              <span className="text-green-600 font-bold">Real-time rates</span>
            </div>
          </div>
        </div>
      </div>
      
      <div className="mt-4 text-sm text-gray-600">
        <p>💡 <strong>Bank spreads typically include 3-8% hidden fees.</strong> Seamount shows you the real cost upfront with no surprises.</p>
      </div>
    </div>
  );
};

export default LiveFXRates;