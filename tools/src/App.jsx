// FILE: tools/src/App.jsx
// Professional Financial Platform Application Entry Point

import React from 'react'
import SavingsCalculator from './components/SavingsCalculator'

// Enhanced Error Boundary Component for Professional UX
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Seamount Platform Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full text-center">
            <div className="mb-4">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-gray-800 mb-2">Platform Temporarily Unavailable</h2>
              <p className="text-gray-600 mb-6">Our financial platform encountered an issue. Please refresh the page or try again shortly.</p>
            </div>
            <div className="space-y-3">
              <button
                onClick={() => window.location.reload()}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
              >
                Refresh Platform
              </button>
              <a
                href="https://seamount.io"
                className="block w-full border border-gray-300 text-gray-700 py-2 px-4 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
              >
                Visit Main Site
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Professional Loading Component
const LoadingFallback = () => (
  <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <h2 className="text-xl font-semibold text-gray-800 mb-2">Loading Seamount Platform</h2>
      <p className="text-gray-600">Preparing your cross-border savings calculator...</p>
    </div>
  </div>
);

// Main Application Component
function App() {
  return (
    <ErrorBoundary>
      <React.Suspense fallback={<LoadingFallback />}>
        <div className="seamount-financial-platform">
          <SavingsCalculator />
        </div>
      </React.Suspense>
    </ErrorBoundary>
  );
}

export default App;