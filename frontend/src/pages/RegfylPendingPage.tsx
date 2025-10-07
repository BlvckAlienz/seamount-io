// COMPLETE IMPLEMENTATION - Status page for Regfyl verifications
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Clock, CheckCircle2, AlertCircle, RefreshCw, Home } from 'lucide-react';

const RegfylPendingPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'pending' | 'approved' | 'rejected' | 'checking'>('pending');
  const [loading, setLoading] = useState(false);
  const userId = searchParams.get('user_id');

  const checkStatus = async () => {
    if (!userId) return;
    
    setLoading(true);
    try {
      const token = localStorage.getItem('token') || sessionStorage.getItem('supabase.auth.token');
      const response = await fetch(`/api/kyc/status/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.kyc_status === 'approved' || data.kyc_status === 'verified') {
          setStatus('approved');
        } else if (data.kyc_status === 'rejected') {
          setStatus('rejected');
        } else {
          setStatus('pending');
        }
      }
    } catch (error) {
      console.error('Status check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, [userId]);

  if (status === 'approved') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center p-4">
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 max-w-md w-full border border-green-500/30">
          <div className="text-center">
            <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="h-12 w-12 text-green-400" />
            </div>
            <h1 className="text-3xl font-bold text-white mb-4">Verification Complete!</h1>
            <p className="text-gray-300 mb-6">
              Your identity has been verified successfully. You now have full access to all platform features.
            </p>
            <button
              onClick={() => navigate('/dashboard')}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (status === 'rejected') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-red-900 to-gray-900 flex items-center justify-center p-4">
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 max-w-md w-full border border-red-500/30">
          <div className="text-center">
            <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <AlertCircle className="h-12 w-12 text-red-400" />
            </div>
            <h1 className="text-3xl font-bold text-white mb-4">Verification Failed</h1>
            <p className="text-gray-300 mb-6">
              Unfortunately, we couldn't verify your identity. Please contact support for assistance or try again.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
              >
                Dashboard
              </button>
              <button
                onClick={() => window.location.href = 'mailto:support@seamount.io'}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
              >
                Contact Support
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center p-4">
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 max-w-md w-full border border-blue-500/30">
        <div className="text-center">
          <div className="w-20 h-20 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-6 relative">
            <Clock className="h-12 w-12 text-blue-400" />
            <div className="absolute inset-0 rounded-full border-4 border-blue-400/30 border-t-blue-400 animate-spin"></div>
          </div>
          
          <h1 className="text-3xl font-bold text-white mb-4">Verification In Progress</h1>
          
          <p className="text-gray-300 mb-6">
            We're verifying your identity with our compliance partner. This typically takes 1-5 minutes.
          </p>

          <div className="space-y-4 mb-6">
            <div className="bg-blue-900/30 rounded-lg p-4 text-left">
              <h3 className="text-blue-400 font-semibold mb-2">What's happening?</h3>
              <ul className="text-sm text-gray-300 space-y-2">
                <li>✓ Your information has been submitted</li>
                <li>⏳ Checking against official databases</li>
                <li>⏳ Performing compliance screening</li>
                <li>⏳ Generating verification report</li>
              </ul>
            </div>

            <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-4 text-left">
              <h3 className="text-yellow-400 font-semibold mb-2 text-sm">Meanwhile, you can:</h3>
              <ul className="text-xs text-gray-300 space-y-1">
                <li>• Explore the platform (limited features)</li>
                <li>• Connect your wallet</li>
                <li>• Review transaction fees</li>
              </ul>
            </div>
          </div>

          <button
            onClick={checkStatus}
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2 mb-3"
          >
            <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Checking...' : 'Check Status'}
          </button>

          <button
            onClick={() => navigate('/dashboard')}
            className="w-full border border-gray-700 text-gray-300 py-3 px-6 rounded-lg hover:bg-gray-800 transition-colors flex items-center justify-center gap-2"
          >
            <Home className="h-5 w-5" />
            Go to Dashboard
          </button>
        </div>

        <p className="text-center text-xs text-gray-500 mt-6">
          We'll notify you by email once verification is complete
        </p>
      </div>
    </div>
  );
};

export default RegfylPendingPage;