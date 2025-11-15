import React, { useState, useEffect } from 'react';
import { Mail, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/lib/supabase';
import { emailMonitor } from '@/utils/emailMonitor';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface ResetPasswordProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

const ResetPassword: React.FC<ResetPasswordProps> = ({ open, onOpenChange, onSuccess }) => {
  const [email, setEmail] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { resetPassword, loading, startPasswordReset, endPasswordReset } = useAuth();
  const state = useAuth(); // Add this to access full state
  
  // 🔐 Control auto-navigation while modal is open
  useEffect(() => {
    if (open) {
      console.log('[ResetPassword] Modal opened - blocking auto-navigation');
      startPasswordReset();
    } else {
      console.log('[ResetPassword] Modal closed - allowing auto-navigation');
      endPasswordReset();
    }
    
    // Cleanup on unmount
    return () => {
      endPasswordReset();
    };
  }, [open, startPasswordReset, endPasswordReset]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // 🔍 DIAGNOSTIC: What is the actual auth state?
    console.log('=== RESET PASSWORD DEBUG ===');
    console.log('1. Current session:', state.session);
    console.log('2. Current user:', state.user);
    console.log('3. Is resetting password flag:', state.isResettingPassword);
    console.log('4. Current pathname:', window.location.pathname);
    
    // Check Supabase directly
    const { data: { session: supabaseSession } } = await supabase.auth.getSession();
    console.log('5. Supabase session (direct):', supabaseSession);
    console.log('============================');

    setFormError(null);
    
    if (!email || !/\S+@\S+\.\S+/.test(email)) {
      setFormError('Please enter a valid email address');
      return;
    }

    // ⚠️ Check rate limiting (prevent spam)
    if (emailMonitor.isRateLimited(email)) {
      const remaining = emailMonitor.getRateLimitRemaining(email);
      const minutes = Math.ceil(remaining / 60);
      setFormError(
        `Too many attempts. Please wait ${minutes} minute${minutes !== 1 ? 's' : ''} before trying again.`
      );
      return;
    }

    setIsSubmitting(true);
    
    try {
      const { success, error } = await resetPassword(email);
      
      if (success) {
        setSuccessMessage('If an account exists for this email, password reset instructions have been sent.');
        setEmail('');
        
        // Auto-close after success or call onSuccess
        if (onSuccess) {
          setTimeout(() => {
            onSuccess();
            onOpenChange(false);
          }, 3000);
        }
      } else {
        setFormError(error || 'An unexpected error occurred. Please try again.');
      }
    } catch (error: any) {
      setFormError(error.message || 'Failed to send reset instructions. Please try again.');
    } finally {
      setIsSubmitting(false);
    }

    // ✅ Record successful attempt
    emailMonitor.recordAttempt(email, 'password_reset');

  };

  const handleClose = () => {
  setEmail('');
  setSuccessMessage('');
  setFormError(null);
  setIsSubmitting(false);
  
  // ⚠️ CRITICAL: Re-enable navigation before closing
  endPasswordReset();
  
  onOpenChange(false);
};

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px] bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-600">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold text-gray-900 dark:text-white text-center">
            Reset Password
          </DialogTitle>
          <DialogDescription className="text-gray-600 dark:text-gray-400 text-center text-base">
            {successMessage 
              ? "Check your email for reset instructions" 
              : "Enter your email to receive password reset instructions"
            }
          </DialogDescription>
        </DialogHeader>

        {successMessage ? (
          <div className="py-6 text-center">
            <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
            <p className="text-gray-700 dark:text-gray-300 mb-6 text-lg font-medium">
              {successMessage}
            </p>
            <Button 
              onClick={handleClose}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white"
            >
              Back to Sign In
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="reset-email" className="text-sm font-semibold text-gray-900 dark:text-white">
                Email Address
              </Label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
                <Input
                  id="reset-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  required
                  disabled={isSubmitting}
                  className="pl-10 bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white h-12"
                />
              </div>
            </div>

            {formError && (
              <Alert variant="destructive" className="border-2">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="font-medium">
                  {formError}
                </AlertDescription>
              </Alert>
            )}

            <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                disabled={isSubmitting}
                className="w-full sm:w-auto h-12 px-6 text-base font-semibold"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting || loading}
                className="w-full sm:w-auto h-12 px-8 text-base font-bold bg-blue-600 hover:bg-blue-700 text-white"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  'Send Instructions'
                )}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default ResetPassword;