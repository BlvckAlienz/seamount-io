// File Location: frontend/src/components/layout/EnvSetup.tsx
// Description: The definitive, corrected, and production-ready environment setup component.

import React from 'react';

// --- CORRECTED IMPORT PATH ---
// We now use the '@' alias defined in vite.config.ts for a robust, absolute path.
// This is no longer fragile and will not break if the file is moved again.
import { type EnvironmentStatus } from '@/config/env';

interface EnvSetupProps {
  envStatus: EnvironmentStatus;
}

const generateEnvContent = () => {
  return `# Seamount.io Environment Configuration
# Add these to your Vercel Project Settings for the 'seamount-io' project.
# Do NOT prefix backend secrets with VITE_.

# --- FRONTEND (PUBLIC) ---
# These MUST start with VITE_
VITE_SUPABASE_URL=your_supabase_url_here
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key_here
VITE_API_URL=/api

# --- BACKEND (PRIVATE) ---
# These must NOT start with VITE_
DATABASE_URL=your_full_postgresql_connection_string
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
# ... and all other backend secrets ...
`;
};

const copyEnvToClipboard = () => {
  navigator.clipboard.writeText(generateEnvContent());
  alert('Environment variable template copied to clipboard!');
};

const EnvSetup: React.FC<EnvSetupProps> = ({ envStatus }) => {
  return (
    <div className="flex items-center justify-center min-h-screen bg-black p-4 text-white">
      <div className="max-w-3xl w-full bg-gray-900/90 backdrop-blur-lg rounded-xl p-8 shadow-2xl border border-red-800/80">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-12 h-12 flex-shrink-0 bg-red-900/50 rounded-lg flex items-center justify-center border border-red-700">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Environment Configuration Error</h1>
            <p className="text-red-300">Your application cannot start because critical services are not configured.</p>
          </div>
        </div>
        
        <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700/50 mb-6">
          <h3 className="font-semibold text-white mb-2">Detected Issues:</h3>
          <ul className="text-sm space-y-1">
            {envStatus.errors.map((error, index) => (
              <li key={index} className="flex items-start">
                <span className="text-red-400 mr-2">❌</span>
                <span className="text-gray-300">{error}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="mb-6">
          <h3 className="font-semibold text-white mb-2">How to Fix:</h3>
          <p className="text-gray-400 text-sm mb-4">
            This is a one-time setup. You need to add the required environment variables to your Vercel project settings.
            Click the button below to copy a template, then paste the values into the "Environment Variables" section of your `seamount-io` project on Vercel.
          </p>
          <button 
            onClick={copyEnvToClipboard}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            Copy .env Template for Vercel
          </button>
        </div>
        
        <div className="text-center">
          <p className="text-gray-500 text-xs">
            After adding the variables to Vercel, a new deployment will be automatically triggered.
          </p>
        </div>
      </div>
    </div>
  );
};

export default EnvSetup;