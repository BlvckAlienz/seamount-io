import React, { useState } from 'react';
import { X } from 'lucide-react';
import LoginForm from './LoginForm';
import RegisterForm from './RegisterForm';
import ResetPassword from './ResetPassword';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialView?: 'login' | 'register' | 'reset';
  onSuccess?: () => void;
}

const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  initialView = 'login',
  onSuccess
}) => {
  const [currentView, setCurrentView] = useState(initialView);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="relative bg-gray-900 rounded-xl max-w-md w-full p-6 border border-gray-800 shadow-2xl">
        <button
          className="absolute top-4 right-4 p-1 text-gray-400 hover:text-white"
          onClick={onClose}
        >
          <X className="h-6 w-6" />
        </button>

        <div className="mb-6">
          {currentView === 'login' && (
            <LoginForm
              onSuccess={() => {
                onSuccess?.();
                onClose();
              }}
              onRegisterClick={() => setCurrentView('register')}
              onForgotPassword={() => setCurrentView('reset')}
            />
          )}

          {currentView === 'register' && (
            <RegisterForm
              onSuccess={() => {
                onSuccess?.();
                onClose();
              }}
              onLoginClick={() => setCurrentView('login')}
            />
          )}

          {currentView === 'reset' && (
            <ResetPassword
              onCancel={() => setCurrentView('login')}
              onSuccess={() => setCurrentView('login')}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default AuthModal;