import React, { useState } from 'react';
import { Mail, Lock, Eye, EyeOff, LogIn } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import Button from '@/components/ui/Button';

interface LoginFormProps {
  onSuccess?: () => void;
  onRegisterClick?: () => void;
  onForgotPassword?: () => void;
}

const LoginForm: React.FC<LoginFormProps> = ({
  onSuccess,
  onRegisterClick,
  onForgotPassword
}) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  
  const { signIn, loading, error: authError } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!email || !password) {
      setFormError('Email and password are required');
      return;
    }
    const { success, error } = await signIn(email, password);
    if (success) {
      if (onSuccess) onSuccess();
    } else if (error) {
      setFormError(error);
    }
  };

  return (
    <div className="w-full max-w-sm p-6 bg-white rounded-lg shadow-md">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Sign In</h2>
        <p className="text-gray-600 mt-2">Welcome back to Seamount</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input 
              id="email" 
              name="email" 
              autoComplete="email"
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              className="w-full pl-10 pr-3 py-2 bg-white border border-gray-300 rounded-md text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" 
              placeholder="your@email.com" 
              required
            />
          </div>
        </div>
        
        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="block text-sm font-medium text-gray-700">Password</label>
            {onForgotPassword && (
              <button 
                type="button" 
                onClick={onForgotPassword} 
                className="text-xs text-blue-600 hover:text-blue-800 hover:underline"
              >
                Forgot password?
              </button>
            )}
          </div>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input 
              id="password" 
              name="password" 
              autoComplete="current-password"
              type={showPassword ? 'text' : 'password'} 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              className="w-full pl-10 pr-10 py-2 bg-white border border-gray-300 rounded-md text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" 
              placeholder="••••••••" 
              required
            />
            <button 
              type="button" 
              onClick={() => setShowPassword(!showPassword)} 
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>
        </div>
        
        {(authError || formError) && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{authError || formError}</p>
          </div>
        )}
        
        <Button 
          type="submit" 
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2" 
          loading={loading} 
          icon={LogIn}
        >
          Sign In
        </Button>
        
        {onRegisterClick && (
          <div className="text-center pt-4">
            <p className="text-sm text-gray-600">
              Don't have an account?{' '}
              <button 
                type="button" 
                onClick={onRegisterClick} 
                className="font-medium text-blue-600 hover:text-blue-800 hover:underline"
              >
                Sign up
              </button>
            </p>
          </div>
        )}
      </form>
    </div>
  );
};

export default LoginForm;