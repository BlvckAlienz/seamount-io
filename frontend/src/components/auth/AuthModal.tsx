import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import LoginForm from './LoginForm';
import RegisterForm from './RegisterForm';
import ResetPassword from './ResetPassword';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialView?: 'login' | 'register' | 'reset';
  onAuthSuccess?: () => void;
}

const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  initialView = 'login',
  onAuthSuccess
}) => {
  const [currentView, setCurrentView] = useState(initialView);

  useEffect(() => {
    // Reset the view to the initial one every time the modal is opened
    if (isOpen) {
      setCurrentView(initialView);
    }
  }, [isOpen, initialView]);

  if (!isOpen) return null;

  const handleSuccess = () => {
    if (onAuthSuccess) onAuthSuccess();
    onClose();
  };

  return (
    <div 
      className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 transition-opacity duration-300" 
      onClick={onClose}
    >
      <div 
        className="relative bg-gray-900 rounded-xl max-w-md w-full p-6 sm:p-8 border border-gray-800 shadow-2xl" 
        onClick={(e) => e.stopPropagation()}
      >
        <button className="absolute top-4 right-4 p-1 text-gray-400 hover:text-white" onClick={onClose}>
          <X className="h-6 w-6" />
        </button>

        <div>
          {currentView === 'login' && (
            <LoginForm
              onSuccess={handleSuccess}
              onRegisterClick={() => setCurrentView('register')}
              onForgotPassword={() => setCurrentView('reset')}
            />
          )}

          {currentView === 'register' && (
            <RegisterForm
              onSuccess={() => {
                // After successful registration, provide clear instructions and switch to login view
                alert("Registration successful! Please check your email to verify your account, then sign in.");
                setCurrentView('login');
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