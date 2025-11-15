import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Lock, CheckCircle, AlertCircle, Eye, EyeOff, Shield, KeyRound } from 'lucide-react';
import toast from 'react-hot-toast';

// Password validation component with horizontal layout (matches RegisterForm)
const PasswordRequirements: React.FC<{ requirements: Record<string, boolean> }> = ({ requirements }) => {
  const allMet = Object.values(requirements).every(Boolean);
  
  if (allMet) {
    return (
      <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded-md">
        <div className="flex items-center text-sm text-green-700">
          <CheckCircle className="h-4 w-4 mr-2" />
          <span className="font-medium">Password meets all requirements ✓</span>
        </div>
      </div>
    );
  }
  
  return (
    <div className="mt-2">
      <p className="text-xs font-medium text-gray-500 mb-1">Password must contain:</p>
      <div className="flex flex-wrap gap-2">
        <div className={`flex items-center text-xs ${requirements.length ? 'text-green-600' : 'text-gray-500'}`}>
          <div className={`w-2 h-2 rounded-full mr-1 ${requirements.length ? 'bg-green-500' : 'bg-gray-400'}`}></div>
          8+ chars
        </div>
        <div className={`flex items-center text-xs ${requirements.uppercase ? 'text-green-600' : 'text-gray-500'}`}>
          <div className={`w-2 h-2 rounded-full mr-1 ${requirements.uppercase ? 'bg-green-500' : 'bg-gray-400'}`}></div>
          A-Z
        </div>
        <div className={`flex items-center text-xs ${requirements.lowercase ? 'text-green-600' : 'text-gray-500'}`}>
          <div className={`w-2 h-2 rounded-full mr-1 ${requirements.lowercase ? 'bg-green-500' : 'bg-gray-400'}`}></div>
          a-z
        </div>
        <div className={`flex items-center text-xs ${requirements.number ? 'text-green-600' : 'text-gray-500'}`}>
          <div className={`w-2 h-2 rounded-full mr-1 ${requirements.number ? 'bg-green-500' : 'bg-gray-400'}`}></div>
          0-9
        </div>
        <div className={`flex items-center text-xs ${requirements.special ? 'text-green-600' : 'text-gray-500'}`}>
          <div className={`w-2 h-2 rounded-full mr-1 ${requirements.special ? 'bg-green-500' : 'bg-gray-400'}`}></div>
          !@#$%^&*
        </div>
      </div>
    </div>
  );
};

const ResetPasswordPage: React.FC = () => {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validating, setValidating] = useState(true);
  const [validRequirements, setValidRequirements] = useState<Record<string, boolean>>({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false,
  });
  const [passwordsMatch, setPasswordsMatch] = useState(true);
  const navigate = useNavigate();

  // Validate that user came from reset link
  useEffect(() => {
    const checkResetToken = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      
      // User should have a recovery session from email link
      if (!session) {
        toast.error('Invalid or expired reset link');
        navigate('/');
        return;
      }
      
      console.log('✅ [ResetPasswordPage] Valid recovery session detected');
      setValidating(false);
    };
    
    checkResetToken();
  }, [navigate]);

  // Validate password requirements
  const validatePassword = (password: string) => {
    const requirements = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
      special: /[!@#$%^&*]/.test(password),
    };
    setValidRequirements(requirements);
    return Object.values(requirements).every(Boolean);
  };

  // Handle password change
  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setNewPassword(value);
    validatePassword(value);
    
    // Check if passwords match
    if (confirmPassword) {
      setPasswordsMatch(value === confirmPassword);
    }
  };

  // Handle confirm password change
  const handleConfirmPasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setConfirmPassword(value);
    setPasswordsMatch(newPassword === value);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!validatePassword(newPassword)) {
      setError('Password does not meet requirements');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      setPasswordsMatch(false);
      return;
    }

    setLoading(true);

    try {
      console.log('🔐 [ResetPasswordPage] Updating password...');
      
      // Update password using Supabase
      const { error } = await supabase.auth.updateUser({
        password: newPassword
      });

      if (error) throw error;

      console.log('✅ [ResetPasswordPage] Password updated successfully');
      toast.success('Password updated successfully!', {
        icon: '🔒',
        duration: 3000,
      });
      
      // Redirect to dashboard after 1.5 seconds
      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);

    } catch (err: any) {
      console.error('❌ [ResetPasswordPage] Password update failed:', err);
      setError(err.message || 'Failed to update password');
      toast.error('Password update failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Loading state while validating session
  if (validating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <Card className="w-full max-w-md mx-4 shadow-xl border-2 border-blue-100">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center py-8">
              <div className="relative">
                <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600"></div>
                <Shield className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 h-8 w-8 text-blue-600" />
              </div>
              <p className="text-gray-600 mt-4 font-medium">Verifying security link...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 px-4 py-12">
      <Card className="w-full max-w-md shadow-2xl border-2 border-blue-100">
        <CardHeader className="space-y-4 pb-6 border-b bg-gradient-to-r from-blue-50 to-purple-50">
          <div className="flex justify-center">
            <div className="relative">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
                <KeyRound className="h-10 w-10 text-white" />
              </div>
              <div className="absolute -bottom-1 -right-1 w-8 h-8 bg-green-500 rounded-full flex items-center justify-center border-4 border-white shadow-md">
                <Shield className="h-4 w-4 text-white" />
              </div>
            </div>
          </div>
          
          <div className="text-center space-y-2">
            <CardTitle className="text-2xl font-bold text-gray-900">
              Create New Password
            </CardTitle>
            <CardDescription className="text-base text-gray-600">
              Choose a strong password to secure your account
            </CardDescription>
          </div>

          {/* Security Badge */}
          <div className="flex items-center justify-center gap-2 bg-blue-100 border border-blue-200 rounded-lg px-4 py-2">
            <Shield className="h-4 w-4 text-blue-600" />
            <span className="text-xs font-semibold text-blue-700">Secure Password Reset</span>
          </div>
        </CardHeader>

        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* New Password Field */}
            <div className="space-y-2">
              <Label htmlFor="new-password" className="text-sm font-semibold text-gray-900">
                New Password
              </Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <Input
                  id="new-password"
                  type={showNewPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={handlePasswordChange}
                  placeholder="Enter new password"
                  required
                  disabled={loading}
                  className="pl-10 pr-10 h-12 text-base bg-white border-2 border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                  disabled={loading}
                >
                  {showNewPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
              
              {/* Password Requirements */}
              {newPassword && <PasswordRequirements requirements={validRequirements} />}
            </div>

            {/* Confirm Password Field */}
            <div className="space-y-2">
              <Label htmlFor="confirm-password" className="text-sm font-semibold text-gray-900">
                Confirm New Password
              </Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <Input
                  id="confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={handleConfirmPasswordChange}
                  placeholder="Confirm new password"
                  required
                  disabled={loading}
                  className={`pl-10 pr-10 h-12 text-base bg-white border-2 transition-all ${
                    confirmPassword && !passwordsMatch
                      ? 'border-red-400 focus:border-red-500 focus:ring-red-200'
                      : 'border-gray-300 focus:border-blue-500 focus:ring-blue-200'
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                  disabled={loading}
                >
                  {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
              
              {/* Password Match Indicator */}
              {confirmPassword && (
                <div className={`flex items-center text-sm ${passwordsMatch ? 'text-green-600' : 'text-red-600'}`}>
                  {passwordsMatch ? (
                    <>
                      <CheckCircle className="h-4 w-4 mr-1" />
                      <span className="font-medium">Passwords match</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-4 w-4 mr-1" />
                      <span className="font-medium">Passwords do not match</span>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Error Alert */}
            {error && (
              <Alert variant="destructive" className="border-2">
                <AlertCircle className="h-5 w-5" />
                <AlertDescription className="font-medium text-base">
                  {error}
                </AlertDescription>
              </Alert>
            )}

            {/* Security Notice */}
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <Shield className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-amber-800 space-y-1">
                  <p className="font-semibold">Security Tips:</p>
                  <ul className="list-disc list-inside space-y-0.5 ml-1">
                    <li>Use a unique password you don't use elsewhere</li>
                    <li>Avoid personal information like birthdays</li>
                    <li>Consider using a password manager</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={loading || !passwordsMatch || !Object.values(validRequirements).every(Boolean)}
              className="w-full h-12 text-base font-bold bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg hover:shadow-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-lg"
            >
              {loading ? (
                <div className="flex items-center justify-center gap-2">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  <span>Updating Password...</span>
                </div>
              ) : (
                <div className="flex items-center justify-center gap-2">
                  <Lock className="h-5 w-5" />
                  <span>Update Password</span>
                </div>
              )}
            </Button>

            {/* Help Text */}
            <p className="text-center text-xs text-gray-500 pt-2">
              After updating, you'll be signed in with your new password
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default ResetPasswordPage;