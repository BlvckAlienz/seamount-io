// ErrorBoundary.jsx
import React from 'react';
import PropTypes from 'prop-types';

/**
 * Production-ready Error Boundary Component
 * Features:
 * - Graceful error recovery
 * - Error categorization (critical vs non-critical)
 * - Error reporting to external services
 * - Fallback UI with user-friendly messages
 * - Retry mechanisms
 * - Error context preservation
 */

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
      isNonCritical: false,
      retryCount: 0,
      componentStack: '',
      timestamp: null
    };
    
    // Bind methods
    this.handleRetry = this.handleRetry.bind(this);
    this.handleReset = this.handleReset.bind(this);
    this.handleReport = this.handleReport.bind(this);
  }

  static getDerivedStateFromError(error) {
    // Safe error handling with comprehensive checks
    const errorObj = ErrorBoundary.normalizeError(error);
    const errorId = ErrorBoundary.generateErrorId();
    const timestamp = new Date().toISOString();
    
    // Determine if error is non-critical
    const isNonCritical = ErrorBoundary.isNonCriticalError(errorObj);
    
    return {
      hasError: true,
      error: errorObj,
      errorId,
      timestamp,
      isNonCritical,
      retryCount: 0
    };
  }

  componentDidCatch(error, errorInfo) {
    // Normalize the error for safety
    const normalizedError = ErrorBoundary.normalizeError(error);
    
    // Update state with component stack trace
    this.setState({
      errorInfo,
      componentStack: errorInfo?.componentStack || ''
    });

    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.group('🚨 ErrorBoundary Caught Error');
      console.error('Error:', normalizedError);
      console.error('Error Info:', errorInfo);
      console.error('Error ID:', this.state.errorId);
      console.groupEnd();
    }

    // Report error to external service (Sentry, LogRocket, etc.)
    this.reportErrorToService(normalizedError, errorInfo);
    
    // Track error in localStorage for debugging (optional)
    this.trackErrorForDebugging(normalizedError);
  }

  // Normalize any error type to a proper Error object
  static normalizeError(error) {
    if (!error) {
      return new Error('Unknown error occurred');
    }
    
    if (typeof error === 'string') {
      return new Error(error);
    }
    
    if (typeof error === 'object') {
      // Preserve original error properties
      const normalized = new Error(error.message || 'Unknown error');
      Object.assign(normalized, error);
      return normalized;
    }
    
    return new Error(String(error));
  }

  // Generate unique error ID for tracking
  static generateErrorId() {
    return `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Determine if error is non-critical
  static isNonCriticalError(error) {
    if (!error || typeof error !== 'object') return false;
    
    // Check for known non-critical error types
    const nonCriticalPatterns = [
      'network',
      'connection',
      'timeout',
      'fetch',
      'wallet',
      'web3',
      'ethereum',
      'metamask',
      'walletconnect',
      'auth',
      'session',
      'noncritical'
    ];
    
    const errorString = JSON.stringify(error).toLowerCase();
    
    // Check if error has isNonCriticalError flag
    if (error.isNonCriticalError === true) {
      return true;
    }
    
    // Check error message for non-critical patterns
    if (error.message) {
      const message = error.message.toLowerCase();
      if (nonCriticalPatterns.some(pattern => message.includes(pattern))) {
        return true;
      }
    }
    
    // Check error name
    if (error.name) {
      const name = error.name.toLowerCase();
      if (nonCriticalPatterns.some(pattern => name.includes(pattern))) {
        return true;
      }
    }
    
    // Check the stringified error
    if (nonCriticalPatterns.some(pattern => errorString.includes(pattern))) {
      return true;
    }
    
    return false;
  }

  // Report error to external service (Sentry, LogRocket, etc.)
  reportErrorToService(error, errorInfo) {
    const { errorId, timestamp, isNonCritical } = this.state;
    
    // Example: Report to Sentry
    if (window.Sentry) {
      window.Sentry.withScope((scope) => {
        scope.setTag('error_boundary', 'true');
        scope.setTag('error_id', errorId);
        scope.setTag('is_non_critical', isNonCritical);
        scope.setExtra('timestamp', timestamp);
        scope.setExtra('component_stack', errorInfo?.componentStack || '');
        scope.setExtra('retry_count', this.state.retryCount);
        window.Sentry.captureException(error);
      });
    }
    
    // Example: Report to LogRocket
    if (window.LogRocket) {
      window.LogRocket.captureException(error, {
        tags: { errorId, isNonCritical },
        extra: { componentStack: errorInfo?.componentStack }
      });
    }
    
    // Custom error reporting endpoint
    if (process.env.REACT_APP_ERROR_REPORTING_URL) {
      const errorData = {
        errorId,
        timestamp,
        isNonCritical,
        url: window.location.href,
        userAgent: navigator.userAgent,
        error: {
          name: error.name,
          message: error.message,
          stack: error.stack
        },
        componentStack: errorInfo?.componentStack,
        retryCount: this.state.retryCount
      };
      
      // Use navigator.sendBeacon for reliable error reporting
      if (navigator.sendBeacon) {
        navigator.sendBeacon(
          process.env.REACT_APP_ERROR_REPORTING_URL,
          JSON.stringify(errorData)
        );
      }
    }
  }

  // Track errors in localStorage for debugging
  trackErrorForDebugging(error) {
    try {
      const errorLog = {
        id: this.state.errorId,
        timestamp: this.state.timestamp,
        message: error.message,
        type: this.state.isNonCritical ? 'non-critical' : 'critical',
        url: window.location.href,
        userAgent: navigator.userAgent.substring(0, 100)
      };
      
      // Store last 10 errors
      const existingErrors = JSON.parse(localStorage.getItem('error_debug_log') || '[]');
      existingErrors.unshift(errorLog);
      localStorage.setItem('error_debug_log', JSON.stringify(existingErrors.slice(0, 10)));
    } catch (e) {
      // Silently fail - localStorage might be disabled
    }
  }

  // Handle retry action
  handleRetry() {
    const { retryCount } = this.state;
    const { maxRetries = 3 } = this.props;
    
    if (retryCount < maxRetries) {
      this.setState({
        hasError: false,
        error: null,
        errorInfo: null,
        retryCount: retryCount + 1
      });
      
      // Log retry attempt
      if (window.Sentry) {
        window.Sentry.addBreadcrumb({
          category: 'error_boundary',
          message: `Retry attempt ${retryCount + 1} for error ${this.state.errorId}`,
          level: 'info'
        });
      }
    } else {
      // Too many retries, perform hard reset
      this.handleHardReset();
    }
  }

  // Reset error state
  handleReset() {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
      isNonCritical: false,
      componentStack: '',
      timestamp: null
    });
  }

  // Hard reset - clear localStorage and reload
  handleHardReset() {
    // Clear problematic states from localStorage
    const keysToClear = [
      'walletconnect',
      'wagmi.wallet',
      'wagmi.connected',
      'wagmi.store',
      'web3modal',
      'WEB3_CONNECT_CACHED_PROVIDER'
    ];
    
    keysToClear.forEach(key => {
      try {
        localStorage.removeItem(key);
        sessionStorage.removeItem(key);
      } catch (e) {
        // Ignore errors
      }
    });
    
    // Reload the page
    window.location.reload();
  }

  // Generate user-friendly error message
  getUserFriendlyMessage() {
    const { error, isNonCritical } = this.state;
    const { fallbackMessages } = this.props;
    
    if (fallbackMessages && fallbackMessages[error?.message]) {
      return fallbackMessages[error.message];
    }
    
    if (isNonCritical) {
      return fallbackMessages?.nonCritical || 
        "We're experiencing temporary connection issues. Please check your network connection and try again.";
    }
    
    // Default critical error messages based on common patterns
    const message = error?.message?.toLowerCase() || '';
    
    if (message.includes('wallet') || message.includes('web3') || message.includes('ethereum')) {
      return "There's an issue with your wallet connection. Please try reconnecting your wallet.";
    }
    
    if (message.includes('network') || message.includes('fetch')) {
      return "Network error detected. Please check your internet connection and try again.";
    }
    
    if (message.includes('auth') || message.includes('session')) {
      return "Session error. Please refresh the page or try logging in again.";
    }
    
    return fallbackMessages?.default || 
      "Something went wrong. Our team has been notified. Please try refreshing the page.";
  }

  // Render fallback UI for non-critical errors
  renderNonCriticalFallback() {
    const { retryCount, errorId } = this.state;
    const { renderNonCritical } = this.props;
    
    if (renderNonCritical) {
      return renderNonCritical({
        error: this.state.error,
        errorId,
        retryCount,
        onRetry: this.handleRetry,
        onReset: this.handleReset
      });
    }
    
    return (
      <div className="error-boundary non-critical" style={styles.nonCriticalContainer}>
        <div style={styles.content}>
          <div style={styles.icon}>⚠️</div>
          <h3 style={styles.title}>Temporary Issue</h3>
          <p style={styles.message}>{this.getUserFriendlyMessage()}</p>
          
          <div style={styles.actions}>
            <button
              onClick={this.handleRetry}
              style={styles.primaryButton}
              aria-label="Retry connection"
            >
              {retryCount > 0 ? 'Try Again' : 'Retry Connection'}
            </button>
            <button
              onClick={this.handleReset}
              style={styles.secondaryButton}
              aria-label="Dismiss"
            >
              Dismiss
            </button>
          </div>
          
          {process.env.NODE_ENV === 'development' && (
            <details style={styles.details}>
              <summary style={styles.summary}>Debug Information</summary>
              <pre style={styles.pre}>
                Error ID: {errorId}
                {this.state.error && `\nError: ${this.state.error.toString()}`}
                {this.state.componentStack && `\n\nComponent Stack:\n${this.state.componentStack}`}
              </pre>
            </details>
          )}
        </div>
      </div>
    );
  }

  // Render fallback UI for critical errors
  renderCriticalFallback() {
    const { errorId, timestamp } = this.state;
    const { renderCritical } = this.props;
    
    if (renderCritical) {
      return renderCritical({
        error: this.state.error,
        errorId,
        timestamp,
        onRetry: this.handleRetry,
        onHardReset: this.handleHardReset
      });
    }
    
    return (
      <div className="error-boundary critical" style={styles.criticalContainer}>
        <div style={styles.content}>
          <div style={styles.icon}>🚨</div>
          <h2 style={styles.title}>Something Went Wrong</h2>
          <p style={styles.message}>{this.getUserFriendlyMessage()}</p>
          
          <div style={styles.actions}>
            <button
              onClick={this.handleRetry}
              style={styles.primaryButton}
              aria-label="Try again"
            >
              Try Again
            </button>
            <button
              onClick={this.handleHardReset}
              style={styles.secondaryButton}
              aria-label="Reset application"
            >
              Reset App
            </button>
            {this.props.showReportButton && (
              <button
                onClick={this.handleReport}
                style={styles.tertiaryButton}
                aria-label="Report error"
              >
                Report Issue
              </button>
            )}
          </div>
          
          {process.env.NODE_ENV === 'development' && (
            <details style={styles.details}>
              <summary style={styles.summary}>Error Details</summary>
              <div style={styles.errorDetails}>
                <p><strong>Error ID:</strong> {errorId}</p>
                <p><strong>Time:</strong> {new Date(timestamp).toLocaleString()}</p>
                {this.state.error && (
                  <pre style={styles.pre}>
                    {this.state.error.toString()}
                    {this.state.error.stack && `\n\nStack Trace:\n${this.state.error.stack}`}
                  </pre>
                )}
                {this.state.componentStack && (
                  <div>
                    <strong>Component Stack:</strong>
                    <pre style={styles.pre}>{this.state.componentStack}</pre>
                  </div>
                )}
              </div>
            </details>
          )}
          
          <div style={styles.footer}>
            <p style={styles.footerText}>
              If the problem persists, please contact support with Error ID: <code>{errorId}</code>
            </p>
          </div>
        </div>
      </div>
    );
  }

  handleReport() {
    // Implement error reporting to support
    const { errorId, error } = this.state;
    const subject = encodeURIComponent(`Error Report: ${errorId}`);
    const body = encodeURIComponent(
      `Error ID: ${errorId}\nURL: ${window.location.href}\nError: ${error?.message}\n\nPlease describe what you were doing when the error occurred:`
    );
    
    window.open(`mailto:support@example.com?subject=${subject}&body=${body}`, '_blank');
  }

  render() {
    const { hasError, isNonCritical } = this.state;
    const { children, disableBoundary } = this.props;

    // Allow disabling the boundary for testing
    if (disableBoundary) {
      return children;
    }

    if (hasError) {
      return isNonCritical 
        ? this.renderNonCriticalFallback()
        : this.renderCriticalFallback();
    }

    return children;
  }
}

// PropTypes for better development experience
ErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
  fallbackMessages: PropTypes.shape({
    default: PropTypes.string,
    nonCritical: PropTypes.string,
    critical: PropTypes.string,
  }),
  renderCritical: PropTypes.func,
  renderNonCritical: PropTypes.func,
  maxRetries: PropTypes.number,
  showReportButton: PropTypes.bool,
  disableBoundary: PropTypes.bool,
  onError: PropTypes.func, // Callback when error occurs
};

ErrorBoundary.defaultProps = {
  maxRetries: 3,
  showReportButton: true,
  disableBoundary: false,
  fallbackMessages: {
    default: "Something went wrong. Our team has been notified. Please try refreshing the page.",
    nonCritical: "We're experiencing temporary connection issues. Please check your network connection and try again.",
    critical: "A critical error occurred. Our team has been notified. Please try refreshing the page or contact support if the problem persists."
  }
};

// Inline styles for the component
const styles = {
  criticalContainer: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#fef2f2',
    padding: '20px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  nonCriticalContainer: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '300px',
    backgroundColor: '#fffbeb',
    padding: '40px 20px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    borderRadius: '8px',
    border: '1px solid #fcd34d',
    margin: '20px'
  },
  content: {
    maxWidth: '600px',
    textAlign: 'center',
    width: '100%'
  },
  icon: {
    fontSize: '48px',
    marginBottom: '20px'
  },
  title: {
    fontSize: '24px',
    fontWeight: '600',
    color: '#dc2626',
    marginBottom: '16px'
  },
  message: {
    fontSize: '16px',
    lineHeight: '1.5',
    color: '#4b5563',
    marginBottom: '32px'
  },
  actions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
    flexWrap: 'wrap',
    marginBottom: '32px'
  },
  primaryButton: {
    backgroundColor: '#2563eb',
    color: 'white',
    border: 'none',
    padding: '12px 24px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    minWidth: '140px'
  },
  secondaryButton: {
    backgroundColor: 'transparent',
    color: '#4b5563',
    border: '1px solid #d1d5db',
    padding: '12px 24px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.2s',
    minWidth: '140px'
  },
  tertiaryButton: {
    backgroundColor: 'transparent',
    color: '#2563eb',
    border: 'none',
    padding: '12px 24px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    textDecoration: 'underline'
  },
  details: {
    backgroundColor: 'white',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    padding: '16px',
    marginTop: '20px',
    textAlign: 'left'
  },
  summary: {
    cursor: 'pointer',
    fontWeight: '500',
    color: '#374151',
    outline: 'none',
    marginBottom: '8px'
  },
  pre: {
    backgroundColor: '#f9fafb',
    padding: '12px',
    borderRadius: '4px',
    overflowX: 'auto',
    fontSize: '12px',
    color: '#6b7280',
    whiteSpace: 'pre-wrap',
    marginTop: '8px'
  },
  errorDetails: {
    fontSize: '14px',
    lineHeight: '1.6'
  },
  footer: {
    marginTop: '32px',
    paddingTop: '16px',
    borderTop: '1px solid #e5e7eb'
  },
  footerText: {
    fontSize: '14px',
    color: '#6b7280',
    lineHeight: '1.5'
  }
};

// Higher Order Component for easier usage
export const withErrorBoundary = (WrappedComponent, errorBoundaryProps = {}) => {
  return function WithErrorBoundaryWrapper(props) {
    return (
      <ErrorBoundary {...errorBoundaryProps}>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    );
  };
};

// Utility function to create non-critical errors
export const createNonCriticalError = (message, originalError = null) => {
  const error = new Error(message);
  error.isNonCriticalError = true;
  if (originalError) {
    error.originalError = originalError;
  }
  return error;
};

export default ErrorBoundary;