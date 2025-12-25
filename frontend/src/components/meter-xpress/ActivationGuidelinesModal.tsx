// File: frontend/src/components/meter-xpress/ActivationGuidelinesModal.tsx
import React, { useState } from 'react';
import { X, Info, CheckCircle, AlertTriangle, Zap } from 'lucide-react';

interface ActivationGuidelinesModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const ActivationGuidelinesModal: React.FC<ActivationGuidelinesModalProps> = ({
  open,
  onOpenChange
}) => {
  const [selectedMeterType, setSelectedMeterType] = useState<string>('04');

  if (!open) return null;

  const meterTypes = [
    { code: '04', name: '04********* Series' },
    { code: '43', name: '43********* Series' },
    { code: '95', name: '95********* Series' },
    { code: '45', name: '45********* Series' },
    { code: '0179', name: '0179******* Series' },
    { code: '0101', name: '0101******* Series' },
    { code: '62', name: '62********* Series' }
  ];

  const pairingCodes: { [key: string]: string } = {
    '04': '#036# then enter the 11-digit meter serial number',
    '43': '755204↩ then last 9 digits of meter number',
    '95': '900 + meter\'s 11-digit serial number',
    '45': '755204↩ then meter number',
    '0179': '888888 + meter\'s 13-digit serial number',
    '0101': '5258 + [ignore first 4 digits] + [ignore last digit]↩',
    '62': '9999 + Meter Number + Enter Key↩'
  };

  const checkBalanceCodes: { [key: string]: string } = {
    '04': '#009#',
    '43': '10↩',
    '95': '019↩',
    '45': '009↩',
    '0179': '07↩',
    '0101': '01↩',
    '62': '801↩'
  };

  const preloadedUnits: { [key: string]: number } = {
    '04': 100,
    '43': 100,
    '95': 20,
    '45': 200,
    '0179': 100,
    '0101': 300,
    '62': 100
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700 sticky top-0 bg-gray-900/95 backdrop-blur-sm">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <Zap className="h-6 w-6 text-yellow-400" />
              Meter Activation Guidelines
            </h2>
            <p className="text-gray-400 text-sm mt-1">Complete setup instructions for your prepaid meter</p>
          </div>
          <button
            onClick={() => onOpenChange(false)}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Important Notice */}
          <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-yellow-400 font-semibold mb-1">Important</h3>
                <p className="text-sm text-gray-300">
                  Your meter comes with preloaded units. The installation form will be emailed to you 
                  immediately after installation. Contact EKEDC customer care if you don't receive it within 24 hours.
                </p>
              </div>
            </div>
          </div>

          {/* Contact Info */}
          <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-4">
            <h3 className="text-blue-400 font-semibold mb-2 flex items-center gap-2">
              <Info className="h-5 w-5" />
              EKEDC Customer Care
            </h3>
            <div className="space-y-1 text-sm text-gray-300">
              <p>📞 Phone: 0708 067 1170 or 0700 123 5666</p>
              <p>✉️ Email: customercare@ekedp.com</p>
            </div>
          </div>

          {/* Meter Type Selector */}
          <div>
            <h3 className="text-white font-semibold mb-3">Select Your Meter Type</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {meterTypes.map((type) => (
                <button
                  key={type.code}
                  onClick={() => setSelectedMeterType(type.code)}
                  className={`p-3 rounded-lg border-2 transition-all text-sm font-medium ${
                    selectedMeterType === type.code
                      ? 'bg-blue-600 border-blue-500 text-white'
                      : 'bg-gray-800 border-gray-700 text-gray-300 hover:border-blue-500'
                  }`}
                >
                  {type.name}
                </button>
              ))}
            </div>
          </div>

          {/* Preloaded Units */}
          <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-4">
            <h3 className="text-green-400 font-semibold mb-2">Preloaded Units</h3>
            <p className="text-2xl font-bold text-white">
              {preloadedUnits[selectedMeterType]} kWh
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Your meter comes preloaded with these units. Money value will be deducted at first or subsequent vending.
            </p>
          </div>

          {/* Step-by-Step Guide */}
          <div className="space-y-4">
            <h3 className="text-xl font-bold text-white">Activation Steps</h3>

            {/* Step 1: Power Supply */}
            <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 text-white font-bold text-sm flex-shrink-0">
                  1
                </div>
                <div>
                  <h4 className="text-white font-semibold mb-2">Ensure Power Supply</h4>
                  <ul className="space-y-1 text-sm text-gray-300">
                    <li className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0 mt-0.5" />
                      <span>Meter must be connected to power supply (Power LED should be ON)</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Step 2: UIU Communication */}
            <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 text-white font-bold text-sm flex-shrink-0">
                  2
                </div>
                <div>
                  <h4 className="text-white font-semibold mb-2">Ensure UIU/CIU Communication</h4>
                  <ul className="space-y-1 text-sm text-gray-300">
                    <li className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0 mt-0.5" />
                      <span>CIU must be powered (battery or power supply)</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0 mt-0.5" />
                      <span>CIU must be within proximity to the meter</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0 mt-0.5" />
                      <span>CIU must be paired with the meter</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Step 3: Pairing */}
            <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 text-white font-bold text-sm flex-shrink-0">
                  3
                </div>
                <div className="flex-1">
                  <h4 className="text-white font-semibold mb-2">Pair UIU with Meter</h4>
                  <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-600">
                    <p className="text-xs text-gray-400 mb-2">Pairing Code for {selectedMeterType}*********:</p>
                    <code className="text-green-400 font-mono text-sm block bg-black/30 p-2 rounded">
                      {pairingCodes[selectedMeterType]}
                    </code>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">
                    {selectedMeterType === '04' && 'Meter displays "rF CON ✓" if successful'}
                    {selectedMeterType === '95' && 'CIU displays "WRITE OK" → "COM SETTING" → "SYN"'}
                  </p>
                </div>
              </div>
            </div>

            {/* Step 4: Check Balance */}
            <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 text-white font-bold text-sm flex-shrink-0">
                  4
                </div>
                <div className="flex-1">
                  <h4 className="text-white font-semibold mb-2">Check Available Balance</h4>
                  <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-600">
                    <p className="text-xs text-gray-400 mb-2">Balance Check Code for {selectedMeterType}*********:</p>
                    <code className="text-green-400 font-mono text-sm block bg-black/30 p-2 rounded">
                      {checkBalanceCodes[selectedMeterType]}
                    </code>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">
                    You should see your preloaded {preloadedUnits[selectedMeterType]} kWh displayed
                  </p>
                </div>
              </div>
            </div>

            {/* Step 5: Load Token */}
            <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 text-white font-bold text-sm flex-shrink-0">
                  5
                </div>
                <div>
                  <h4 className="text-white font-semibold mb-2">Load Purchased Token</h4>
                  <ul className="space-y-1 text-sm text-gray-300">
                    <li className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0 mt-0.5" />
                      <span>Ensure meter is connected to power supply</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0 mt-0.5" />
                      <span>Ensure CIU is paired and communicating with meter</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0 mt-0.5" />
                      <span>Enter the 20-digit token purchased from EKEDC</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Troubleshooting */}
          <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-4">
            <h3 className="text-red-400 font-semibold mb-2 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Troubleshooting
            </h3>
            <p className="text-sm text-gray-300 mb-2">
              If you've completed all steps and still can't check your balance:
            </p>
            <ul className="space-y-1 text-sm text-gray-400 ml-4">
              <li>• Faulty CIU box (keypad unit)</li>
              <li>• Faulty meter</li>
              <li>• No supply from distribution transformer</li>
            </ul>
            <p className="text-sm text-gray-300 mt-3">
              Contact EKEDC customer care: <span className="text-blue-400">+234 708 065 5555</span>
            </p>
          </div>

          {/* Where to Buy Tokens */}
          <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-4">
            <h3 className="text-blue-400 font-semibold mb-2">Where to Purchase Energy Tokens</h3>
            <ul className="space-y-1 text-sm text-gray-300">
              <li>• EKEDC nearest cash office</li>
              <li>• Third-party payment channels</li>
              <li>• Online at <a href="https://www.ekedp.com/payment" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">www.ekedp.com/payment</a></li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};