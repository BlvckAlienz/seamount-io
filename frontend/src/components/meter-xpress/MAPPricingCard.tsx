// File: frontend/src/components/meter-xpress/MAPPricingCard.tsx
import React, { useState, useEffect } from 'react';
import { DollarSign, TrendingDown, Info } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface MAPPricingCardProps {
  selectedPhase: '1phase' | '3phase';
  selectedVendor: string | null;
  onVendorSelect: (vendor: string, pricing: any) => void;
}

interface PricingData {
  vendor_name: string;
  phase: string;
  base_price: number;
  service_fee: number;
  total_price: number;
  markup_percentage: number;
}

export const MAPPricingCard: React.FC<MAPPricingCardProps> = ({
  selectedPhase,
  selectedVendor,
  onVendorSelect
}) => {
  const [pricing, setPricing] = useState<PricingData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPricing();
  }, [selectedPhase]);

  const fetchPricing = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/api/v1/meter-xpress/map-pricing?phase=${selectedPhase}`);
      
      if (response.data.success) {
        setPricing(response.data.pricing);
      }
    } catch (error) {
      toast.error('Failed to load pricing');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-4 border-blue-500"></div>
        </div>
      </div>
    );
  }

  const cheapestPrice = pricing.length > 0 ? Math.min(...pricing.map(p => p.total_price)) : 0;

  return (
    <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <DollarSign className="h-5 w-5 text-green-400" />
          MAP Vendor Pricing ({selectedPhase === '1phase' ? 'Single Phase' : 'Three Phase'})
        </h3>
        <div className="text-xs text-gray-400 flex items-center gap-1">
          <Info className="h-3 w-3" />
          Includes VAT
        </div>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {pricing.map((item) => {
          const isCheapest = item.total_price === cheapestPrice;
          const isSelected = selectedVendor === item.vendor_name;
          
          return (
            <button
              key={`${item.vendor_name}-${item.phase}`}
              onClick={() => onVendorSelect(item.vendor_name, item)}
              className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                isSelected
                  ? 'bg-blue-600 border-blue-500'
                  : 'bg-gray-800/50 border-gray-700 hover:border-blue-500'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={`font-semibold ${isSelected ? 'text-white' : 'text-gray-200'}`}>
                    {item.vendor_name}
                  </span>
                  {isCheapest && (
                    <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full flex items-center gap-1">
                      <TrendingDown className="h-3 w-3" />
                      CHEAPEST
                    </span>
                  )}
                </div>
                {isSelected && (
                  <span className="text-white text-sm">✓ Selected</span>
                )}
              </div>

              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className={isSelected ? 'text-blue-100' : 'text-gray-400'}>Base Price:</span>
                  <span className={isSelected ? 'text-white' : 'text-gray-300'}>
                    {formatCurrency(item.base_price)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className={isSelected ? 'text-blue-100' : 'text-gray-400'}>
                    Service Fee ({item.markup_percentage}%):
                  </span>
                  <span className={isSelected ? 'text-white' : 'text-gray-300'}>
                    {formatCurrency(item.service_fee)}
                  </span>
                </div>
                <div className="flex justify-between pt-2 border-t border-gray-600">
                  <span className={`font-semibold ${isSelected ? 'text-white' : 'text-gray-200'}`}>
                    Total Price:
                  </span>
                  <span className={`font-bold text-lg ${isSelected ? 'text-white' : 'text-green-400'}`}>
                    {formatCurrency(item.total_price)}
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-4 p-3 bg-yellow-900/20 border border-yellow-500/30 rounded-lg">
        <p className="text-xs text-yellow-200 flex items-start gap-2">
          <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <span>
            Service fee covers form processing, contractor coordination, document verification, 
            and post-installation support. Meter comes with warranty.
          </span>
        </p>
      </div>
    </div>
  );
};