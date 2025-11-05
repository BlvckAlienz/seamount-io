import React, { useState } from 'react';
import { Mail, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface ResetPasswordProps {
  onCancel?: () => void;
  onSuccess?: () => void;
}

const ResetPassword: React.FC<ResetPasswordProps> = ({ onCancel, onSuccess }) => {
  const [email, setEmail] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  
  const { loading } = useAuth();
  // Placeholder for actual reset password function in AuthContext
  const resetPassword = async (email: string) => { return { success: true, error: null }; };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !/\S+@\S+\.\S+/.test(email)) {
      setFormError('Please enter a valid email address');
      return;
    }
    const { success, error } = await resetPassword(email);
    if (success) {
      setSuccessMessage('If an account exists for this email, password reset instructions have been sent.');
      if (onSuccess) setTimeout(() => onSuccess(), 4000);
    } else {
      setFormError(error || 'An unexpected error occurred.');
    }
  };

  return (
    <Card>
      <h2 className="text-2xl font-bold text-white mb-4 text-center">Reset Password</h2>
      {successMessage ? (
        <div className="text-center py-6">
          <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
          <p className="text-gray-300 mb-6">{successMessage}</p>
          <Button onClick={onCancel || (() => {})}>Back to Sign In</Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
            <p className="text-gray-400 text-sm text-center">Enter your email to get a reset link.</p>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full pl-10 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" placeholder="your@email.com" required/>
            {formError && <div className="p-3 bg-red-900/30 border border-red-500/50 rounded-lg"><p className="text-sm text-red-400">{formError}</p></div>}
            <div className="pt-2 flex gap-4">
              {onCancel && <Button type="button" variant="secondary" onClick={onCancel} className="w-full">Cancel</Button>}
              <Button type="submit" className="w-full">Send Instructions</Button>
            </div>
        </form>
      )}
    </Card>
  );
};

export default ResetPassword;