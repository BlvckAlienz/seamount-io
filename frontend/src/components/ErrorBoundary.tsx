// components/ErrorBoundary.tsx
import React from 'react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: any): Partial<ErrorBoundaryState> {
    console.error('ErrorBoundary: Handling error:', error);
    return {
      hasError: true,
      error: error instanceof Error ? error : new Error(String(error)),
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error);
    console.error('Component stack:', errorInfo.componentStack);
    this.setState({ errorInfo });
    
    // Log to your error tracking service
    if (window.location.hostname !== 'localhost') {
      // Send to your error tracking
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      const isSliceError = this.state.error?.message.includes('slice');
      
      return (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          backgroundColor: '#0f172a',
          color: 'white',
          padding: '20px',
          textAlign: 'center',
        }}>
          <div style={{ maxWidth: '600px' }}>
            <h2 style={{ fontSize: '24px', marginBottom: '16px' }}>Something went wrong</h2>
            
            {isSliceError && (
              <div style={{
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '20px',
              }}>
                <p style={{ color: '#f87171', marginBottom: '8px' }}>
                  <strong>Wallet Address Error</strong>
                </p>
                <p style={{ fontSize: '14px', color: '#d1d5db' }}>
                  There was an issue displaying wallet addresses. This is usually a temporary issue.
                </p>
              </div>
            )}
            
            <div style={{ marginBottom: '20px' }}>
              <button
                onClick={this.handleReload}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  marginRight: '10px',
                  fontWeight: '600',
                }}
              >
                Refresh Page
              </button>
              
              <button
                onClick={this.handleReset}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: '600',
                }}
              >
                Try Again
              </button>
            </div>
            
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div style={{
                marginTop: '20px',
                padding: '12px',
                backgroundColor: 'rgba(0,0,0,0.2)',
                borderRadius: '6px',
                fontSize: '12px',
                fontFamily: 'monospace',
                textAlign: 'left',
                overflow: 'auto',
                maxHeight: '200px',
              }}>
                <p><strong>Error:</strong> {this.state.error.toString()}</p>
                {this.state.errorInfo && (
                  <p><strong>Stack:</strong> {this.state.errorInfo.componentStack}</p>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;