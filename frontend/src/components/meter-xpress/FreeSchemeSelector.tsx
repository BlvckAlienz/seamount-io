// File: frontend/src/components/meter-xpress/FreeSchemeSelector.tsx
import React from 'react';
import { Gift, Award, CreditCard } from 'lucide-react';

interface FreeSchemeSelectorProps {
  selectedScheme: 'MAP' | 'DISREP' | 'MAF' | null;
  onSelectScheme: (scheme: 'MAP' | 'DISREP' | 'MAF') => void;
}

export const FreeSchemeSelector: React.FC<FreeSchemeSelectorProps> = ({
  selectedScheme,
  onSelectScheme
}) => {
  return (
    <div className="mb-6">
      <label className="block text-sm text-gray-400 mb-3">
        Select Metering Scheme *
        <span className="ml-2 text-xs text-green-400">
          (DISREP & MAF are free, sponsored by World Bank & Federal Government)
        </span>
      </label>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* MAP Scheme (Paid) */}
        <button
          type="button"
          onClick={() => onSelectScheme('MAP')}
          className={`p-4 rounded-xl border-2 transition-all text-left ${
            selectedScheme === 'MAP'
              ? 'bg-blue-900/30 border-blue-500 shadow-lg shadow-blue-500/20'
              : 'bg-gray-800/50 border-gray-700 hover:border-blue-500'
          }`}
        >
          <div className="flex items-center gap-3 mb-2">
            <div className={`p-2 rounded-lg ${selectedScheme === 'MAP' ? 'bg-blue-600' : 'bg-gray-700'}`}>
              <CreditCard className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="font-semibold text-white">MAP</div>
              <div className="text-xs text-gray-400">Meter Asset Provider</div>
            </div>
          </div>
          <div className="text-sm text-gray-300">
            • Choose from certified vendors<br/>
            • Standard service fees apply<br/>
            • Complete payment required
          </div>
          <div className={`mt-3 text-sm font-semibold ${selectedScheme === 'MAP' ? 'text-blue-300' : 'text-gray-500'}`}>
            Paid Service
          </div>
        </button>

        {/* DISREP Scheme (Free) */}
        <button
          type="button"
          onClick={() => onSelectScheme('DISREP')}
          className={`p-4 rounded-xl border-2 transition-all text-left ${
            selectedScheme === 'DISREP'
              ? 'bg-green-900/30 border-green-500 shadow-lg shadow-green-500/20'
              : 'bg-gray-800/50 border-gray-700 hover:border-green-500'
          }`}
        >
          <div className="flex items-center gap-3 mb-2">
            <div className={`p-2 rounded-lg ${selectedScheme === 'DISREP' ? 'bg-green-600' : 'bg-gray-700'}`}>
              <Gift className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="font-semibold text-white">DISREP</div>
              <div className="text-xs text-gray-400">Distribution Rehabilitation</div>
            </div>
          </div>
          <div className="text-sm text-gray-300">
            • Government sponsored<br/>
            • No payment required<br/>
            • Eligibility criteria apply
          </div>
          <div className="mt-3 text-sm font-semibold text-green-400">
            Free Service ✓
          </div>
        </button>

        {/* MAF Scheme (Free) */}
        <button
          type="button"
          onClick={() => onSelectScheme('MAF')}
          className={`p-4 rounded-xl border-2 transition-all text-left ${
            selectedScheme === 'MAF'
              ? 'bg-purple-900/30 border-purple-500 shadow-lg shadow-purple-500/20'
              : 'bg-gray-800/50 border-gray-700 hover:border-purple-500'
          }`}
        >
          <div className="flex items-center gap-3 mb-2">
            <div className={`p-2 rounded-lg ${selectedScheme === 'MAF' ? 'bg-purple-600' : 'bg-gray-700'}`}>
              <Award className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="font-semibold text-white">MAF</div>
              <div className="text-xs text-gray-400">Meter Acquisition Fund</div>
            </div>
          </div>
          <div className="text-sm text-gray-300">
            • World Bank funded<br/>
            • No cost to customer<br/>
            • Limited availability
          </div>
          <div className="mt-3 text-sm font-semibold text-green-400">
            Free Service ✓
          </div>
        </button>
      </div>

      {/* Info Banner */}
      {selectedScheme && selectedScheme !== 'MAP' && (
        <div className="mt-4 p-4 bg-green-900/20 border border-green-500/30 rounded-xl">
          <div className="flex items-start gap-3">
            <Gift className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-green-400 font-semibold">Free Metering Scheme Selected</h4>
              <p className="text-sm text-gray-300 mt-1">
                Your application will be processed under the {selectedScheme} scheme sponsored by 
                the World Bank and Federal Government of Nigeria. No payment is required.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};