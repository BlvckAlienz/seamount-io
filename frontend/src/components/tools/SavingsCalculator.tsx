import React, { useState } from 'react';
import { Card, Button, Input, Select, Alert } from '../ui';
import { calculateSavings } from '../../lib/tools/savingsCalculator';
import SocialShare from '../shared/SocialShare';

const SavingsCalculator = () => {
  const [amount, setAmount] = useState('');
  const [fromCountry, setFromCountry] = useState('NG');
  const [toCountry, setToCountry] = useState('US');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const countries = [
    { value: 'NG', label: 'Nigeria', flag: '🇳🇬' },
	{ value: 'SA', label: 'South Africa', flag: 'SA' },
    { value: 'KE', label: 'Kenya', flag: '🇰🇪' },
    { value: 'GH', label: 'Ghana', flag: '🇬🇭' },
    { value: 'US', label: 'United States', flag: '🇺🇸' },
    { value: 'UK', label: 'United Kingdom', flag: '🇬🇧' },
	{ value: 'CA', label: 'Canada', flag: 'CA' },
  ];

  const handleCalculate = async () => {
    setLoading(true);
    const savings = await calculateSavings(parseFloat(amount), fromCountry, toCountry);
    setResults(savings);
    setLoading(false);
  };

  return (
    <div className="max-w-md mx-auto p-6">
      <Card>
        <h2 className="text-2xl font-bold mb-4">💰 Cross-Border Savings Calculator</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Amount to Send</label>
            <Input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="Enter amount"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">From Country</label>
              <Select
                value={fromCountry}
                onChange={setFromCountry}
                options={countries}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">To Country</label>
              <Select
                value={toCountry}
                onChange={setToCountry}
                options={countries}
              />
            </div>
          </div>

          <Button onClick={handleCalculate} loading={loading}>
            Calculate Savings
          </Button>
        </div>

        {results && (
          <div className="mt-6">
            <Alert type="success">
              <h3 className="font-bold">You Save {results.savingsPercentage}% with Seamount!</h3>
              <p>Traditional methods: ${results.traditionalFee}</p>
              <p>Seamount fee: ${results.seamountFee}</p>
              <p className="text-green-600 font-bold">Savings: ${results.savings}</p>
            </Alert>

            <SocialShare 
              amount={amount}
              savings={results.savings}
              fromCountry={fromCountry}
              toCountry={toCountry}
            />
          </div>
        )}
      </Card>
    </div>
  );
};

export default SavingsCalculator;