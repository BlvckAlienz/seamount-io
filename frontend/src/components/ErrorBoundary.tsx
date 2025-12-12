// components/ErrorBoundary.tsx - SIMPLIFIED VERSION
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
    console.log('ErrorBoundary: Handling error:', error);
    return {
      hasError: true,
      error: error instanceof Error ? error : new Error(String(error)),
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
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
          <div>
            <h2>Something went wrong</h2>
            <p>Please try refreshing the page</p>
            <button
              onClick={this.handleReload}
              style={{
                padding: '10px 20px',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                marginTop: '20px'
              }}
            >
              Refresh Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;