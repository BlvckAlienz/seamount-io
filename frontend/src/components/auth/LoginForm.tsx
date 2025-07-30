import React, { useState } from 'react';
import { Mail, Lock, Eye, EyeOff, LogIn } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';

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
    <Card>
      <h2 className="text-2xl font-bold text-white mb-6 text-center">Sign In to Seamount</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full pl-10 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" placeholder="your@email.com" required/>
          </div>
        </div>
        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="block text-sm font-medium text-gray-300">Password</label>
            {onForgotPassword && <button type="button" onClick={onForgotPassword} className="text-xs text-blue-400 hover:underline">Forgot password?</button>}
          </div>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} className="w-full pl-10 pr-10 py-2 bg-gray-800 border border-gray-700 rounded-lg" placeholder="••••••••" required/>
            <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">{showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}</button>
          </div>
        </div>
        {(authError || formError) && <div className="p-3 bg-red-900/30 border border-red-500/50 rounded-lg text-center"><p className="text-sm text-red-400">{authError || formError}</p></div>}
        <div className="pt-2"><Button type="submit" className="w-full bg-gradient-to-r from-blue-600 to-purple-600" loading={loading} icon={LogIn}>Sign In</Button></div>
        {onRegisterClick && <div className="text-center pt-4"><p className="text-sm text-gray-400">Don't have an account?{' '}<button type="button" onClick={onRegisterClick} className="font-semibold text-blue-400 hover:underline">Sign up</button></p></div>}
      </form>
    </Card>
  );
};

export default LoginForm;