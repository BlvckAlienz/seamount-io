import React, { useState } from 'react';
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
  
// We're calling Supabase directly to avoid unnecessary abstraction
// const { loading } = useAuth(); // ← Don't need this anymore

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMessage('');
    
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
      // 🎯 CRITICAL: Don't trust Supabase's "success" - it always returns true
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });

      // ⚠️ Supabase returns success even if email doesn't exist (security feature)
      if (error) {
        // Only show error if Supabase had a technical failure
        console.error('[ResetPassword] Supabase error:', error);
        setFormError('Unable to send reset email. Please try again later.');
        return;
      }

      // ✅ Record successful attempt
      emailMonitor.recordAttempt(email, 'password_reset');

      // ✅ Show generic success message (don't reveal if email exists)
      setSuccessMessage(
        'If an account exists with this email, you will receive password reset instructions within 5 minutes. Check your spam folder if you don\'t see it.'
      );
      setEmail('');
      
      // ⚠️ DON'T auto-close - let user read the message and close manually
      // NO setTimeout, NO auto-redirect, NO onSuccess callback
      
    } catch (error: any) {
      console.error('[ResetPassword] Exception:', error);
      setFormError('Network error. Please check your connection and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setEmail('');
    setSuccessMessage('');
    setFormError(null);
    setIsSubmitting(false);
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
            <p className="text-gray-700 dark:text-gray-300 mb-4 text-lg font-medium">
              {successMessage}
            </p>
            
            {/* ✅ ADD HELPFUL NEXT STEPS */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6 text-left">
              <p className="text-sm text-gray-700 dark:text-gray-300 font-semibold mb-2">
                📧 Next Steps:
              </p>
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <li>• Check your inbox for reset instructions</li>
                <li>• Look in spam/junk folder if not in inbox</li>
                <li>• Email may take up to 5 minutes to arrive</li>
                <li>• Link expires in 1 hour for security</li>
              </ul>
            </div>
            
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