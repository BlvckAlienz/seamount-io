import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import crash
    // There is NO import for AuthModal
    
    // ... later in the file ...
    return ( LoginForm from './LoginForm';
import RegisterForm from './RegisterForm';
import ResetPassword from './ResetPassword';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialView
        // ...
        <AuthModal isOpen={isAuthModalOpen} ... /> // <-- The crash happens here
?: 'login' | 'register' | 'reset';
  onAuthSuccess?: () => void;
}

    );
    ```
4.  **The Inescapable Conclusion:** The file `LandingPage.tsxconst AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  initial` is trying to render the `<AuthModal>` component, but it has **never imported it.** The component is unknown,View = 'login',
  onAuthSuccess
}) => {
  const [currentView, setCurrentView] = useState(initialView);

  useEffect(() => {
    setCurrentView(initialView);
  }, [ undefined, and the application crashes.

This is the final bug. We will fix it now. We will also fixinitialView, isOpen]);

  if (!isOpen) return null;

  return (
    <div className=" the incorrect `Button` import at the same time.

---

### **The Fortress Protocol: The Definitive, Finalfixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center Fix**

We will now perform the final, definitive code correction.

#### **The Definitive, Corrected `LandingPage p-4 transition-opacity duration-300" onClick={onClose}>
      <div className="relative bg.tsx`**

This is the final, complete, and syntactically correct version of your landing page component. I-gray-900 rounded-xl max-w-md w-full p-6 sm:p-8 border have added the missing `AuthModal` import and corrected the `Button` import path.

**DELETE the entire contents of your `frontend/src/pages/LandingPage.tsx`. Replace it with this definitive code.**

**File border-gray-800 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <button className Path:** `frontend/src/pages/LandingPage.tsx`
="absolute top-4 right-4 p-1 text-gray-400 hover:text-white" onClick={```typescript
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowonClose}>
          <X className="h-6 w-6" />
        </button>

        <div>
          {currentView === 'login' && (
            <LoginForm
              onSuccess={() => {
                onAuthSuccess?.();
                onClose();
              }}
              onRegisterClick={() => setCurrentView('register')}Right, Globe, Shield, Zap, DollarSign, TrendingUp, Check, Send, Twitter, Instagram, Mail, Map
              onForgotPassword={() => setCurrentView('reset')}
            />
          )}

          {currentView === 'registerPin, Phone, ChevronDown, ChevronUp } from 'lucide-react';

// --- DEFINITIVE, CORRECTED IMP' && (
            <RegisterForm
              onSuccess={() => {
                // After successful registration, prompt userORTS ---
import Button from '@/components/ui/Button';
import AuthModal from '@/components/auth/AuthModal'; to check email and switch to login view
                alert("Registration successful! Please check your email to verify your account,

// Define the component's props to accept the function from App.tsx
interface LandingPageProps {
   then sign in.");
                setCurrentView('login');
              }}
              onLoginClick={() => setCurrentView('login')}
            />
          )}

          {currentView === 'reset' && (
            <ResetPassword
              onOpenAuth: (view: 'login' | 'register') => void;
}

const LandingPage:onCancel={() => setCurrentView('login')}
              onSuccess={() => setCurrentView('login')}
            />
 React.FC<LandingPageProps> = ({ onOpenAuth }) => {
  const navigate = useNavigate();
            )}
        </div>
      </div>
    </div>
  );
};

export default AuthModal;