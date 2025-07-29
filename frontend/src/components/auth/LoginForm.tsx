// Location: /frontend/src/components/LoginForm.tsx

import React, { useState } from 'react';
import { Mail, Lock, Eye, EyeOff, LogIn } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Button from './Button';
import Card from './Card';

interface LoginFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
  onRegisterClick?: () => void;
  onForgotPassword?: () => void;
}

const LoginForm: React.FC<LoginFormProps> = ({
  onSuccess,
  onCancel,
  onRegisterClick,
  onForgotPassword
}) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  
  const { signIn, loading, error } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !password) {
      setFormError('Email and password are required');
      return;
    }
    
    const { success, error } = await signIn(email, password);
    
    if (success && onSuccess) {
      onSuccess();
    } else if (error) {
      setFormError(error);
    }
  };

  return (
    <Card>
      <h2 className="text-2xl font-bold text-white mb-6">Sign In</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full pl-10 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Your email address"
            />
          </div>
        </div>
        
        <div>
          <div className="flex justify-between mb-1">
            <label className="block text-sm font-medium text-gray-300">Password</label>
            {onForgotPassword && (
              <button
                type="button"
                onClick={onForgotPassword}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                Forgot password?
              </button>
            )}
          </div>
          <div className="relative">
            <Lock className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full pl-10 pr-10 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Your password"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-2.5 text-gray-400"
            >
              {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>
        </div>
        
        {(error || formError) && (
          <div className="p-3 bg-red-900/30 border border-red-500/50 rounded-lg">
            <p className="text-sm text-red-400">{error || formError}</p>
          </div>
        )}
        
        <div className="pt-2">
          <div className="flex space-x-4">
            {onCancel && (
              <Button
                type="button"
                variant="secondary"
                onClick={onCancel}
                className="flex-1"
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600"
              loading={loading}
              icon={LogIn}
            >
              Sign In
            </Button>
          </div>
        </div>
        
        {onRegisterClick && (
          <div className="text-center mt-4">
            <button 
              type="button"
              onClick={onRegisterClick}
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              Don't have an account? Sign up
            </button>
          </div>
        )}
      </form>
    </Card>
  );
};

export default LoginForm;