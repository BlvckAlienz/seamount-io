// File Location: frontend/src/components/ErrorBoundary.tsx
// CRITICAL: Enhanced error boundary with retry mechanisms and user-friendly recovery
// 🎯 UPDATED: Added WalletConnect error suppression

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, WifiOff, Shield } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackComponent?: React.ComponentType<{
    error: Error;
    retry: () => void;
    errorId: string;
  }>;
  onError?: (error: Error, errorInfo: ErrorInfo, errorId: string) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string | null;
  retryCount: number;
  lastErrorTime: number;
  suppressedErrors: string[]; // Track suppressed non-critical errors
}

class EnhancedErrorBoundary extends Component<Props, State> {
  private maxRetries = 3;
  private retryTimeWindow = 60000; // 1 minute
  private retryTimeout: NodeJS.Timeout | null = null;
  
  // 🎯 NON-CRITICAL ERROR PATTERNS (WalletConnect, network, etc.)
  private nonCriticalPatterns = [
    /pulse\.walletconnect\.org/,
    /403.*walletconnect/,
    /Failed to fetch/,
    /NetworkError/,
    /Network request failed/,
    /Loading chunk.*failed/,
    /Cannot read property.*of null/,
    /Cannot read property.*of undefined/,
    /walletconnect/,
    /metamask/,
    /web3/,
    /ethereum/,
  ];
  
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
      retryCount: 0,
      lastErrorTime: 0,
      suppressedErrors: []
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // 🎯 CHECK IF ERROR IS NON-CRITICAL (WalletConnect, network issues)
    const isNonCritical = this.isNonCriticalError(error);
    
    if (isNonCritical) {
      console.warn('⚠️ Non-critical error suppressed by boundary:', error.message);
      
      // Don't trigger error UI for non-critical errors
      return {
        hasError: false,
        suppressedErrors: [error.message]
      };
    }
    
    const errorId = `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const now = Date.now();
    
    return {
      hasError: true,
      error,
      errorId,
      lastErrorTime: now,
      suppressedErrors: []
    };
  }

  // 🎯 HELPER: Check if error is non-critical
  private static isNonCriticalError(error: Error): boolean {
    const errorMessage = error.message || '';
    const errorStack = error.stack || '';
    
    // Check against non-critical patterns
    const patterns = [
      /pulse\.walletconnect\.org/,
      /403.*walletconnect/,
      /Failed to fetch/,
      /NetworkError/,
      /Network request failed/,
      /Loading chunk.*failed/,
      /Cannot read property.*of null/,
      /Cannot read property.*of undefined/,
      /walletconnect/,
      /metamask/,
      /web3/,
      /ethereum/,
    ];
    
    return patterns.some(pattern => 
      pattern.test(errorMessage) || pattern.test(errorStack)
    );
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const { errorId } = this.state;
    
    // 🎯 SKIP LOGGING FOR NON-CRITICAL ERRORS
    if (EnhancedErrorBoundary.isNonCriticalError(error)) {
      console.warn('⚠️ Non-critical error caught (not logged):', error.message);
      
      // Track suppressed errors for debugging
      this.setState(prev => ({
        suppressedErrors: [...prev.suppressedErrors, error.message]
      }));
      
      return; // Don't log or process non-critical errors
    }
    
    console.error('🚨 Seamount Error Boundary caught an error:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
      hasError: true
    });

    // Enhanced error logging with retry context
    this.logError(error, errorInfo, errorId || 'unknown');

    // Call custom error handler if provided
    if (this.props.onError && errorId) {
      this.props.onError(error, errorInfo, errorId);
    }
  }

  private logError = (error: Error, errorInfo: ErrorInfo, errorId: string) => {
    try {
      // 🎯 SKIP LOGGING WALLET CONNECT ERRORS TO BACKEND
      if (EnhancedErrorBoundary.isNonCriticalError(error)) {
        return;
      }
      
      // Enhanced error logging for Seamount.io
      const errorData = {
        errorId,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
        error: {
          name: error.name,
          message: error.message,
          stack: error.stack
        },
        componentStack: errorInfo.componentStack,
        retryCount: this.state.retryCount,
        lastErrorTime: this.state.lastErrorTime,
        suppressedErrors: this.state.suppressedErrors, // Include suppressed errors
        sessionInfo: {
          viewport: {
            width: window.innerWidth,
            height: window.innerHeight
          },
          connection: (navigator as any).connection?.effectiveType || 'unknown',
          online: navigator.onLine
        }
      };

      // Send to your backend error tracking
      console.error('Seamount Error Report:', errorData);
      
      // Optional: Send to your backend with retry mechanism
      fetch('/api/errors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(errorData)
      }).catch(loggingError => {
        console.error('Failed to log error to backend:', loggingError);
      });

    } catch (loggingError) {
      console.error('Failed to log error:', loggingError);
    }
  };

  private handleRetry = () => {
    const now = Date.now();
    const timeSinceLastError = now - this.state.lastErrorTime;
    
    // Reset retry count if enough time has passed
    if (timeSinceLastError > this.retryTimeWindow) {
      this.setState({ retryCount: 0 });
    }
    
    if (this.state.retryCount < this.maxRetries) {
      this.setState(prevState => ({
        hasError: false,
        error: null,
        errorInfo: null,
        errorId: null,
        retryCount: prevState.retryCount + 1,
        lastErrorTime: now
      }));

      // Auto-retry with exponential backoff
      const backoffTime = Math.pow(2, this.state.retryCount) * 1000;
      this.retryTimeout = setTimeout(() => {
        // Force re-render by updating a dummy state
        this.forceUpdate();
      }, backoffTime);
    }
  };

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
      retryCount: 0,
      lastErrorTime: 0,
      suppressedErrors: []
    });
  };

  private handleGoHome = () => {
    // Clear any retry timeouts before navigation
    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout);
    }
    window.location.href = '/';
  };

  componentWillUnmount() {
    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout);
    }
  }

  render() {
    if (this.state.hasError) {
      // Use custom fallback component if provided
      if (this.props.fallbackComponent) {
        const FallbackComponent = this.props.fallbackComponent;
        return (
          <FallbackComponent
            error={this.state.error!}
            retry={this.handleRetry}
            errorId={this.state.errorId || 'unknown'}
          />
        );
      }

      // 🎯 DETERMINE ERROR TYPE FOR BETTER UI
      const isNetworkError = 
        this.state.error?.message?.includes('Network') ||
        this.state.error?.message?.includes('fetch') ||
        this.state.error?.message?.includes('offline');
      
      const isWalletError = 
        this.state.error?.message?.includes('wallet') ||
        this.state.error?.message?.includes('metamask') ||
        this.state.error?.message?.includes('ethereum');

      // Default fallback UI
      const canRetry = this.state.retryCount < this.maxRetries;
      const retryText = `Retry (${this.maxRetries - this.state.retryCount} attempts left)`;

      return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white rounded-lg shadow-xl p-6 text-center">
            <div className="mb-4">
              {isNetworkError ? (
                <WifiOff className="h-16 w-16 text-orange-500 mx-auto mb-4" />
              ) : isWalletError ? (
                <Shield className="h-16 w-16 text-purple-500 mx-auto mb-4" />
              ) : (
                <AlertTriangle className="h-16 w-16 text-red-500 mx-auto mb-4" />
              )}
              
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                {isNetworkError ? 'Network Connection Issue' : 
                 isWalletError ? 'Wallet Connection Error' : 
                 'Oops! Something went wrong'}
              </h1>
              
              <p className="text-gray-600 mb-4">
                {isNetworkError ? 
                  'Unable to connect to the network. Please check your internet connection.' :
                 isWalletError ?
                  'There was an issue with wallet connection. Please try reconnecting.' :
                  'Seamount.io encountered an unexpected error. Our team has been notified.'}
              </p>
            </div>

            {/* 🎯 SHOW SUPPRESSED ERRORS FOR DEBUGGING */}
            {process.env.NODE_ENV === 'development' && this.state.suppressedErrors.length > 0 && (
              <div className="mb-4 p-3 bg-yellow-50 rounded-lg text-left">
                <details className="text-sm">
                  <summary className="font-medium text-yellow-700 cursor-pointer mb-2">
                    Recent Suppressed Errors ({this.state.suppressedErrors.length})
                  </summary>
                  <div className="text-yellow-600 text-xs overflow-auto max-h-32">
                    {this.state.suppressedErrors.slice(-5).map((err, idx) => (
                      <div key={idx} className="mb-1 p-1 bg-yellow-100 rounded">
                        {err}
                      </div>
                    ))}
                  </div>
                </details>
              </div>
            )}

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div className="mb-4 p-3 bg-red-50 rounded-lg text-left">
                <details className="text-sm">
                  <summary className="font-medium text-red-700 cursor-pointer mb-2">
                    Error Details
                  </summary>
                  <pre className="text-red-600 text-xs overflow-auto max-h-32">
                    {this.state.error.message}
                    {'\n\n'}
                    {this.state.error.stack}
                  </pre>
                </details>
              </div>
            )}

            <div className="space-y-3">
              {canRetry && (
                <button
                  onClick={this.handleRetry}
                  className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  <RefreshCw className="h-4 w-4" />
                  {retryText}
                </button>
              )}
              
              <button
                onClick={this.handleReset}
                className="w-full bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Reset Component
              </button>
              
              <button
                onClick={this.handleGoHome}
                className="w-full flex items-center justify-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
              >
                <Home className="h-4 w-4" />
                Go to Dashboard
              </button>
            </div>

            <div className="mt-6 pt-4 border-t border-gray-200">
              <p className="text-xs text-gray-500">
                Error ID: {this.state.errorId || Date.now().toString(36)}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Retry count: {this.state.retryCount}/{this.maxRetries}
              </p>
              {this.state.suppressedErrors.length > 0 && (
                <p className="text-xs text-yellow-500 mt-1">
                  Suppressed errors: {this.state.suppressedErrors.length}
                </p>
              )}
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default EnhancedErrorBoundary;