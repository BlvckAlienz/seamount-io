import React, { useEffect, useState, useCallback } from 'react';
import { 
  SUPABASE_URL, 
  SUPABASE_ANON_KEY, 
  ALPHA_VANTAGE_API_KEY, 
  CIRCLE_API_KEY, 
  COMPLYCUBE_API_KEY,
  isAlphaVantageConfigured, 
  isCircleConfigured, 
  isSupabaseConfigured, 
  isSentryConfigured, 
  MOCK_MODE 
} from '../config/env';

interface EnvSetupProps {
  children: React.ReactNode;
}

interface ServiceHealth {
  supabase: boolean;
  alphaVantage: boolean;
  circle: boolean;
  complycube: boolean;
  sentry: boolean;
}

interface ApiTestResult {
  service: string;
  status: 'testing' | 'success' | 'error';
  message?: string;
}

const EnvSetup: React.FC<EnvSetupProps> = ({ children }) => {
  const [loading, setLoading] = useState(true);
  const [showSetup, setShowSetup] = useState(false);
  const [testResults, setTestResults] = useState<ApiTestResult[]>([]);
  const [envStatus, setEnvStatus] = useState<ServiceHealth>({
    supabase: isSupabaseConfigured,
    alphaVantage: isAlphaVantageConfigured,
    circle: isCircleConfigured,
    complycube: !!COMPLYCUBE_API_KEY,
    sentry: isSentryConfigured,
  });

  // Test API connections with retry mechanism
  const testApiConnection = useCallback(async (service: string, testFn: () => Promise<boolean>) => {
    const maxRetries = 3;
    let retries = 0;
    
    setTestResults(prev => [...prev.filter(r => r.service !== service), 
      { service, status: 'testing' }]);

    while (retries < maxRetries) {
      try {
        const success = await testFn();
        setTestResults(prev => [...prev.filter(r => r.service !== service), 
          { service, status: success ? 'success' : 'error', 
            message: success ? 'Connected' : 'Connection failed' }]);
        return success;
      } catch (error) {
        retries++;
        if (retries === maxRetries) {
          setTestResults(prev => [...prev.filter(r => r.service !== service), 
            { service, status: 'error', 
              message: `Failed after ${maxRetries} attempts: ${error.message}` }]);
        }
        await new Promise(resolve => setTimeout(resolve, 1000 * retries));
      }
    }
    return false;
  }, []);

  // Test critical services
  const testCriticalServices = useCallback(async () => {
    const tests = [];
    
    if (envStatus.supabase) {
      tests.push(testApiConnection('supabase', async () => {
        const response = await fetch(`${SUPABASE_URL}/rest/v1/`, {
          headers: { 'apikey': SUPABASE_ANON_KEY }
        });
        return response.status < 500;
      }));
    }

    if (envStatus.alphaVantage) {
      tests.push(testApiConnection('alphaVantage', async () => {
        const response = await fetch(
          `https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=${ALPHA_VANTAGE_API_KEY}`
        );
        const data = await response.json();
        return !data['Error Message'] && !data['Note'];
      }));
    }

    await Promise.allSettled(tests);
  }, [envStatus, testApiConnection]);

  useEffect(() => {
    const initializeEnv = async () => {
      // Update status
      const newStatus = {
        supabase: isSupabaseConfigured,
        alphaVantage: isAlphaVantageConfigured,
        circle: isCircleConfigured,
        complycube: !!COMPLYCUBE_API_KEY,
        sentry: isSentryConfigured,
      };
      setEnvStatus(newStatus);

      // Check if critical services missing (and not in mock mode)
      const criticalMissing = !newStatus.supabase && !MOCK_MODE;
      
      if (criticalMissing) {
        setShowSetup(true);
        setLoading(false);
        return;
      }

      // Test configured services
      await testCriticalServices();
      
      setTimeout(() => setLoading(false), 1200);
    };

    initializeEnv();
  }, [testCriticalServices]);

  const generateEnvContent = () => {
    return `# Seamount.io Environment Configuration
# Copy this to your .env file

# Database (Required for production)
VITE_SUPABASE_URL=your_supabase_url_here
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key_here

# Market Data APIs (Optional - free alternatives available)
VITE_ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here

# Payment Processing (Optional)
VITE_CIRCLE_API_KEY=your_circle_api_key_here

# KYC/Compliance (Optional)
VITE_COMPLYCUBE_API_KEY=your_complycube_key_here

# Error Tracking (Optional)
VITE_SENTRY_DSN=your_sentry_dsn_here

# Development Mode
VITE_MOCK_MODE=true`;
  };

  const copyEnvToClipboard = () => {
    navigator.clipboard.writeText(generateEnvContent());
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full border-4 border-gray-800"></div>
            <div className="absolute inset-0 rounded-full border-4 border-t-blue-500 animate-spin"></div>
          </div>
          <div className="text-xl font-semibold text-white mb-2">Seamount.io</div>
          <div className="text-gray-400">Initializing services...</div>
          {testResults.length > 0 && (
            <div className="mt-4 space-y-1">
              {testResults.map(result => (
                <div key={result.service} className="text-xs text-gray-500">
                  {result.service}: {result.status === 'testing' ? '🔄' : 
                   result.status === 'success' ? '✅' : '❌'}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (showSetup) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black p-4">
        <div className="max-w-2xl w-full bg-gray-900/90 backdrop-blur-lg rounded-xl p-6 shadow-2xl border border-gray-800">
          <h1 className="text-2xl font-bold text-white mb-4">🚀 Seamount.io Setup</h1>
          
          <div className="mb-6">
            <p className="text-gray-300 mb-4">
              Your AI-powered trading platform needs configuration. Choose your path:
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-4 mb-6">
            {/* Quick Start */}
            <div className="bg-green-900/20 border border-green-700/50 rounded-lg p-4">
              <h3 className="text-green-400 font-semibold mb-2">⚡ Quick Start</h3>
              <p className="text-sm text-gray-300 mb-3">
                Start trading immediately with free services
              </p>
              <button 
                onClick={() => {
                  localStorage.setItem('SEAMOUNT_MOCK_MODE', 'true');
                  window.location.reload();
                }}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors"
              >
                Launch with Mock Data
              </button>
            </div>

            {/* Premium Setup */}
            <div className="bg-blue-900/20 border border-blue-700/50 rounded-lg p-4">
              <h3 className="text-blue-400 font-semibold mb-2">💎 Premium Setup</h3>
              <p className="text-sm text-gray-300 mb-3">
                Configure real APIs for live trading
              </p>
              <button 
                onClick={copyEnvToClipboard}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors"
              >
                Copy .env Template
              </button>
            </div>
          </div>

          {/* Service Status */}
          <div className="space-y-2 mb-6">
            <h4 className="text-white font-medium">Service Status:</h4>
            
            {[
              { key: 'supabase', name: 'Database', critical: true },
              { key: 'alphaVantage', name: 'Market Data', critical: false },
              { key: 'circle', name: 'Payments', critical: false },
              { key: 'complycube', name: 'KYC', critical: false },
              { key: 'sentry', name: 'Monitoring', critical: false },
            ].map(({ key, name, critical }) => {
              const testResult = testResults.find(r => r.service === key);
              const configured = envStatus[key as keyof ServiceHealth];
              
              return (
                <div key={key} className="flex items-center justify-between p-2 bg-gray-800/50 rounded">
                  <div className="flex items-center gap-2">
                    <div className="w-6">
                      {testResult?.status === 'testing' ? '🔄' :
                       testResult?.status === 'success' ? '✅' :
                       testResult?.status === 'error' ? '❌' :
                       configured ? '🟡' : '⚪'}
                    </div>
                    <span className="text-gray-300">{name}</span>
                    {critical && <span className="text-xs bg-red-600 px-1 rounded">Required</span>}
                  </div>
                  <span className="text-xs text-gray-500">
                    {testResult?.message || (configured ? 'Configured' : 'Not set')}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="text-center">
            <p className="text-gray-400 text-sm">
              After setting up .env, refresh the page or restart your dev server
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Environment ready - render app
  return (
    <>
      {MOCK_MODE && (
        <div className="fixed bottom-0 left-0 right-0 bg-amber-900/80 backdrop-blur-sm text-white text-xs py-1 px-3 text-center z-50">
          🧪 Mock Mode Active - Simulated data for demonstration
        </div>
      )}
      {children}
    </>
  );
};

export default EnvSetup;