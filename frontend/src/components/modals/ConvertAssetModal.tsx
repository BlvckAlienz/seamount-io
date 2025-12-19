// File: frontend/src/components/modals/ConvertAssetModal.tsx
import React, { useState } from 'react';
import { X, RefreshCw, AlertTriangle, Check } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface ConvertAssetModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const ConvertAssetModal: React.FC<ConvertAssetModalProps> = ({
  open,
  onOpenChange,
}) => {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [loading, setLoading] = useState(false);
  
  // Form state
  const [custodianId, setCustodianId] = useState('mock-custodian-stanbic');
  const [symbol, setSymbol] = useState('');
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState('');
  const [pricePerUnit, setPricePerUnit] = useState('');
  const [isin, setIsin] = useState('');

  // Result state
  const [conversionResult, setConversionResult] = useState<any>(null);

  const handleConvert = async () => {
    if (!symbol || !quantity || !pricePerUnit) {
      toast.error('Please fill all required fields');
      return;
    }

    try {
      setLoading(true);
      setStep(2); // Show loading step
      
      const response = await apiClient.post('/api/v1/tokenization/convert-asset', {
        custodian_id: custodianId,
        symbol: symbol.toUpperCase(),
        name: name || symbol,
        quantity: parseInt(quantity),
        price_per_unit: parseFloat(pricePerUnit),
        isin: isin || undefined,
      });

      if (response.data.success) {
        setConversionResult(response.data.data);
        setStep(3); // Show success step
        toast.success('Asset tokenized successfully!');
      } else {
        toast.error(response.data.message || 'Conversion failed');
        setStep(1);
      }
    } catch (error: any) {
      console.error('Conversion failed:', error);
      toast.error(error.response?.data?.detail || 'Failed to convert asset');
      setStep(1);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setStep(1);
    setConversionResult(null);
    setSymbol('');
    setName('');
    setQuantity('');
    setPricePerUnit('');
    setIsin('');
    onOpenChange(false);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-white">Convert Traditional Asset</h2>
            <p className="text-gray-400 text-sm mt-1">Create digital twin on blockchain</p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-2 p-4 bg-gray-800/50">
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${step >= 1 ? 'bg-green-600 text-white' : 'bg-gray-700 text-gray-400'}`}>
            <span className="font-semibold">1</span>
            <span className="text-sm">Asset Details</span>
          </div>
          <div className="w-12 h-0.5 bg-gray-700"></div>
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${step >= 2 ? 'bg-green-600 text-white' : 'bg-gray-700 text-gray-400'}`}>
            <span className="font-semibold">2</span>
            <span className="text-sm">Processing</span>
          </div>
          <div className="w-12 h-0.5 bg-gray-700"></div>
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${step >= 3 ? 'bg-green-600 text-white' : 'bg-gray-700 text-gray-400'}`}>
            <span className="font-semibold">3</span>
            <span className="text-sm">Complete</span>
          </div>
        </div>

        {/* Step 1: Asset Details */}
        {step === 1 && (
          <div className="p-6 space-y-6">
            {/* Custodian Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Custodian <span className="text-red-400">*</span>
              </label>
              <select
                value={custodianId}
                onChange={(e) => setCustodianId(e.target.value)}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-green-500 transition-colors"
              >
                <option value="mock-custodian-stanbic">Stanbic IBTC (Mock)</option>
                <option value="mock-custodian-cscs">CSCS Nigeria (Mock)</option>
                <option value="mock-custodian-nse">NSE Direct (Mock)</option>
                <option value="mock-custodian-broker">Broker-Dealer</option>
                <option value="mock-custodian-developer">Real-Estate Developer</option>
                <option value="mock-custodian-auctioner">Auction House</option>
                <option value="mock-custodian-company">Private Company</option>
                <option value="mock-custodian-others">Others</option>
              </select>
            </div>

            {/* Asset Symbol */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Asset Symbol <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="e.g., DANGCEM"
                maxLength={10}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-green-500 transition-colors"
              />
            </div>

            {/* Asset Name */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Asset Name (Optional)
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Dangote Cement Plc"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-green-500 transition-colors"
              />
            </div>

            {/* Quantity */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Quantity <span className="text-red-400">*</span>
              </label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="Number of shares/units"
                min="1"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-green-500 transition-colors"
              />
            </div>

            {/* Price Per Unit */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Price Per Unit (USD) <span className="text-red-400">*</span>
              </label>
              <input
                type="number"
                value={pricePerUnit}
                onChange={(e) => setPricePerUnit(e.target.value)}
                placeholder="0.00"
                step="0.01"
                min="0"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-green-500 transition-colors"
              />
            </div>

            {/* ISIN (Optional) */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                ISIN Code (Optional)
              </label>
              <input
                type="text"
                value={isin}
                onChange={(e) => setIsin(e.target.value.toUpperCase())}
                placeholder="e.g., NGDANGCEM001"
                maxLength={12}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-green-500 transition-colors"
              />
            </div>

            {/* Total Value Preview */}
            {quantity && pricePerUnit && (
              <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4">
                <div className="text-sm text-gray-400 mb-2">Total Value</div>
                <div className="text-3xl font-bold text-white">
                  ${(parseFloat(quantity) * parseFloat(pricePerUnit)).toFixed(2)}
                </div>
              </div>
            )}

            {/* Warning */}
            <div className="flex items-start gap-2 p-4 bg-yellow-900/20 border border-yellow-500/30 rounded-lg">
              <AlertTriangle className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-yellow-300">
                This will lock your physical assets with the custodian and mint equivalent digital tokens on Algorand blockchain.
              </div>
            </div>

            {/* Convert Button */}
            <button
              onClick={handleConvert}
              disabled={!symbol || !quantity || !pricePerUnit}
              className="w-full py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw className="h-5 w-5" />
              Convert to Digital Asset
            </button>
          </div>
        )}

        {/* Step 2: Processing */}
        {step === 2 && (
          <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
            <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-green-500 mb-4"></div>
            <h3 className="text-xl font-bold text-white mb-2">Converting Asset...</h3>
            <p className="text-gray-400 text-center">
              Creating digital twin on Algorand blockchain
            </p>
          </div>
        )}

        {/* Step 3: Success */}
        {step === 3 && conversionResult && (
          <div className="p-6 space-y-6">
            <div className="flex flex-col items-center justify-center py-6">
              <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mb-4">
                <Check className="h-10 w-10 text-green-400" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">Conversion Successful!</h3>
              <p className="text-gray-400 text-center">
                Your asset has been tokenized on Algorand
              </p>
            </div>

            {/* Result Details */}
            <div className="space-y-4">
              <div className="bg-gray-800/50 rounded-xl p-4">
                <div className="text-sm text-gray-400 mb-1">Asset ID</div>
                <div className="text-white font-mono text-sm">{conversionResult.asset_id}</div>
              </div>

              <div className="bg-gray-800/50 rounded-xl p-4">
                <div className="text-sm text-gray-400 mb-1">Algorand ASA ID</div>
                <div className="text-white font-mono text-sm">{conversionResult.algorand_asa_id}</div>
              </div>

              <div className="bg-gray-800/50 rounded-xl p-4">
                <div className="text-sm text-gray-400 mb-1">Digital Twin Address</div>
                <div className="text-white font-mono text-xs break-all">{conversionResult.digital_twin_address}</div>
              </div>

              <div className="bg-gray-800/50 rounded-xl p-4">
                <div className="text-sm text-gray-400 mb-1">Custody Reference</div>
                <div className="text-white font-mono text-sm">{conversionResult.custody_reference}</div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleClose}
                className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => window.location.href = '/tokenization/tokens'}
                className="flex-1 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors"
              >
                View My Tokens
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConvertAssetModal;