import React, { useState } from 'react';
import { Mail, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Button from './Button';
import Card from './Card';

interface ResetPasswordProps {
  onCancel?: () => void;
  onSuccess?: () => void;
}

const ResetPassword: React.FC<ResetPasswordProps> = ({ onCancel, onSuccess }) => {
  const [email, setEmail] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  
  const { resetPassword, loading } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email) {
      setFormError('Email is required');
      return;
    }
    
    if (!/\S+@\S+\.\S+/.test(email)) {
      setFormError('Please enter a valid email address');
      return;
    }
    
    const { success, error } = await resetPassword(email);
    
    if (success) {
      setSuccessMessage(
        'Password reset instructions have been sent to your email. Please check your inbox.'
      );
      if (onSuccess) {
        setTimeout(() => {
          onSuccess();
        }, 3000);
      }
    } else if (error) {
      setFormError(error);
    }
  };

  return (
    <Card>
      <h2 className="text-2xl font-bold text-white mb-6">Reset Password</h2>
      
      {successMessage ? (
        <div className="text-center py-6">
          <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
          <p className="text-gray-300 mb-6">{successMessage}</p>
          <Button onClick={onCancel || (() => {})}>
            Back to Login
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <p className="text-gray-300 mb-4">
            Enter your email address and we'll send you instructions to reset your password.
          </p>
          
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
          
          {formError && (
            <div className="p-3 bg-red-900/30 border border-red-500/50 rounded-lg flex items-center">
              <AlertCircle className="h-5 w-5 text-red-400 mr-2 flex-shrink-0" />
              <p className="text-sm text-red-400">{formError}</p>
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
                className="flex-1"
                loading={loading}
              >
                Send Reset Instructions
              </Button>
            </div>
          </div>
        </form>
      )}
    </Card>
  );
};

export default ResetPassword;