// File Location: frontend/src/components/layout/NigerianUserBanner.tsx
// HYBRID APPROACH: Proactive BVN education banner for Nigerian users

import React, { useState, useEffect } from 'react';
import { X, AlertCircle, Shield } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

const NigerianUserBanner: React.FC = () => {
  const { userProfile } = useAuth();
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // Check if banner was previously dismissed
    const wasDismissed = localStorage.getItem('ng_bvn_banner_dismissed');
    if (wasDismissed) {
      setDismissed(true);
    }
  }, []);

  const handleDismiss = () => {
    setDismissed(true);
    localStorage.setItem('ng_bvn_banner_dismissed', 'true');
  };

  // Don't show if:
  // - Banner dismissed
  // - Not Nigerian user
  // - BVN already provided
  // - Already verified
  if (
    dismissed ||
    (userProfile?.country_code !== 'NG' && userProfile?.country !== 'NG') ||
    userProfile?.bvn ||
    userProfile?.kyc_status === 'verified' ||
    userProfile?.kyc_status === 'approved'
  ) {
    return null;
  }

  return (
    <div className="bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg p-4 mb-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 flex-1">
          <div className="flex-shrink-0 mt-0.5">
            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
              <Shield className="h-4 w-4 text-green-600" />
            </div>
          </div>
          
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">🇳🇬</span>
              <h3 className="font-semibold text-gray-900">Nigerian User - Fast Verification</h3>
            </div>
            
            <p className="text-sm text-gray-700 mb-2">
              Have your BVN ready for instant identity verification powered by Regfyl.
            </p>
            
            <div className="flex items-start gap-2 text-xs text-gray-600">
              <AlertCircle className="h-3 w-3 flex-shrink-0 mt-0.5" />
              <span>You'll need: BVN, Date of Birth, and Gender when starting verification</span>
            </div>
          </div>
        </div>

        <button
          onClick={handleDismiss}
          className="flex-shrink-0 p-1 hover:bg-gray-200 rounded-full transition-colors"
          aria-label="Dismiss banner"
        >
          <X className="h-5 w-5 text-gray-500" />
        </button>
      </div>
    </div>
  );
};

export default NigerianUserBanner;