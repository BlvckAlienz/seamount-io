import React, { useEffect, useState } from 'react';
import { AlertTriangle, X, TrendingDown } from 'lucide-react';
import { Card } from '@/components/ui/card.tsx';
import { Button } from '@/components/ui/button.tsx';

interface ErrorLog {
  timestamp: number;
  error: string;
  component: string;
}

const ErrorTracking: React.FC = () => {
  const [errors, setErrors] = useState<ErrorLog[]>([]);
  const [showErrors, setShowErrors] = useState(false);

  useEffect(() => {
    // Load errors from localStorage (development mode)
    const storedErrors = localStorage.getItem('seamount-errors');
    if (storedErrors) {
      setErrors(JSON.parse(storedErrors));
    }

    // Listen for new errors
    const handleError = (event: ErrorEvent) => {
      const newError: ErrorLog = {
        timestamp: Date.now(),
        error: event.message,
        component: 'Global',
      };

      setErrors(prev => {
        const updated = [...prev, newError].slice(-50); // Keep last 50 errors
        localStorage.setItem('seamount-errors', JSON.stringify(updated));
        return updated;
      });
    };

    window.addEventListener('error', handleError);
    return () => window.removeEventListener('error', handleError);
  }, []);

  if (process.env.NODE_ENV === 'production') {
    return null; // Hide in production
  }

  const recentErrors = errors.slice(-5);

  return (
    <>
      {/* Error indicator */}
      {errors.length > 0 && (
        <button
          onClick={() => setShowErrors(true)}
          className="fixed bottom-4 right-4 bg-red-600 hover:bg-red-700 text-white p-3 rounded-full shadow-lg z-50 transition-all duration-200"
        >
          <AlertTriangle className="h-5 w-5" />
          {errors.length > 0 && (
            <span className="absolute -top-1 -right-1 bg-yellow-500 text-black text-xs rounded-full h-5 w-5 flex items-center justify-center font-bold">
              {errors.length}
            </span>
          )}
        </button>
      )}

      {/* Error tracking modal */}
      {showErrors && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-2xl max-h-[80vh] overflow-hidden p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <AlertTriangle className="h-6 w-6 text-red-500" />
                <h3 className="text-lg font-semibold text-white">Error Tracking Dashboard</h3>
              </div>
              <button
                onClick={() => setShowErrors(false)}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className="h-5 w-5 text-gray-400" />
              </button>
            </div>

            <div className="space-y-4 max-h-96 overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <TrendingDown className="h-5 w-5 text-red-400" />
                    <span className="text-sm text-gray-300">Total Errors</span>
                  </div>
                  <div className="text-2xl font-bold text-red-400 mt-2">{errors.length}</div>
                </div>
                
                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <AlertTriangle className="h-5 w-5 text-yellow-400" />
                    <span className="text-sm text-gray-300">Recent (24h)</span>
                  </div>
                  <div className="text-2xl font-bold text-yellow-400 mt-2">
                    {errors.filter(e => Date.now() - e.timestamp < 24 * 60 * 60 * 1000).length}
                  </div>
                </div>
                
                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <AlertTriangle className="h-5 w-5 text-blue-400" />
                    <span className="text-sm text-gray-300">Environment</span>
                  </div>
                  <div className="text-sm font-bold text-blue-400 mt-2">Development</div>
                </div>
              </div>

              <h4 className="font-semibold text-white mb-3">Recent Errors</h4>
              <div className="space-y-2">
                {recentErrors.length > 0 ? (
                  recentErrors.reverse().map((error, index) => (
                    <div key={index} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-red-400 font-medium">{error.component}</span>
                        <span className="text-xs text-gray-400">
                          {new Date(error.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-300 font-mono">{error.error}</p>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No errors tracked yet</p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex space-x-3 mt-6 pt-6 border-t border-gray-700">
              <Button 
                variant="destructive" 
                size="sm"
                onClick={() => {
                  localStorage.removeItem('seamount-errors');
                  setErrors([]);
                }}
              >
                Clear Errors
              </Button>
              <Button 
                variant="secondary" 
                size="sm"
                onClick={() => {
                  const errorData = JSON.stringify(errors, null, 2);
                  const blob = new Blob([errorData], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'seamount-errors.json';
                  a.click();
                }}
              >
                Export Logs
              </Button>
            </div>
          </Card>
        </div>
      )}
    </>
  );
};

export default ErrorTracking;