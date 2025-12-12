// components/ErrorBoundary.tsx
import React from 'react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: any): Partial<ErrorBoundaryState> {
    // CRITICAL FIX: Safely handle undefined/null errors
    if (!error) {
      console.warn('ErrorBoundary: Received undefined error');
      return {
        hasError: true,
        error: new Error('An unknown error occurred'),
      };
    }
    
    // Handle any type of error (string, object, Error instance)
    const normalizedError = error instanceof Error ? error : new Error(String(error));
    
    return {
      hasError: true,
      error: normalizedError,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error);
    console.error('Error info:', errorInfo);
    
    // You can add error reporting here if needed
    // if (window.Sentry) window.Sentry.captureException(error);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={styles.container}>
          <div style={styles.content}>
            <h2 style={styles.title}>Something went wrong</h2>
            <p style={styles.message}>
              {this.state.error?.message || 'An unexpected error occurred.'}
            </p>
            <div style={styles.actions}>
              <button onClick={this.handleReset} style={styles.primaryButton}>
                Try Again
              </button>
              <button onClick={this.handleReload} style={styles.secondaryButton}>
                Reload Page
              </button>
            </div>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details style={styles.details}>
                <summary style={styles.summary}>Error Details</summary>
                <pre style={styles.pre}>
                  {this.state.error.toString()}
                  {this.state.error.stack && `\n\nStack Trace:\n${this.state.error.stack}`}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#0f172a',
    padding: '20px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  content: {
    maxWidth: '500px',
    width: '100%',
    textAlign: 'center' as const,
  },
  title: {
    fontSize: '24px',
    fontWeight: 600,
    color: '#f8fafc',
    marginBottom: '16px',
  },
  message: {
    fontSize: '16px',
    lineHeight: 1.5,
    color: '#cbd5e1',
    marginBottom: '32px',
  },
  actions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
    flexWrap: 'wrap' as const,
  },
  primaryButton: {
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    padding: '12px 24px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    minWidth: '140px',
  },
  secondaryButton: {
    backgroundColor: 'transparent',
    color: '#cbd5e1',
    border: '1px solid #475569',
    padding: '12px 24px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    minWidth: '140px',
  },
  details: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '6px',
    padding: '16px',
    marginTop: '32px',
    textAlign: 'left' as const,
  },
  summary: {
    cursor: 'pointer',
    fontWeight: 500,
    color: '#94a3b8',
    outline: 'none' as const,
    marginBottom: '8px',
  },
  pre: {
    backgroundColor: '#0f172a',
    padding: '12px',
    borderRadius: '4px',
    overflowX: 'auto' as const,
    fontSize: '12px',
    color: '#94a3b8',
    whiteSpace: 'pre-wrap' as const,
    marginTop: '8px',
  },
} as const;

export default ErrorBoundary;