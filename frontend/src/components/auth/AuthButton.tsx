import React, { useState } from 'react';
import { LogIn, UserPlus, User, Shield } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import AuthModal from './AuthModal';

interface AuthButtonProps {
  variant?: 'default' | 'secondary' | 'ghost';
  className?: string;
}

const AuthButton: React.FC<AuthButtonProps> = ({ 
  variant = 'default',
  className = ''
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalView, setModalView] = useState<'login' | 'register'>('login');
  const { user, kycStatus } = useAuth();

  const handleLoginClick = () => {
    setModalView('login');
    setIsModalOpen(true);
  };

  const handleRegisterClick = () => {
    setModalView('register');
    setIsModalOpen(true);
  };

  const handleKycClick = () => {
    window.location.href = '/kyc';
  };

  if (user) {
    // User is logged in
    if (kycStatus !== 'approved') {
      // KYC verification needed
      return (
        <Button 
          variant={variant}
          className={`bg-gradient-to-r from-yellow-600 to-amber-600 ${className}`}
          onClick={handleKycClick}
        >
          <Shield className="h-4 w-4 mr-2" />
          Verify Identity
        </Button>
      );
    }
    
    // User is logged in and verified
    return (
      <Button
        variant={variant}
        className={`bg-gradient-to-r from-green-600 to-teal-600 ${className}`}
      >
        <User className="h-4 w-4 mr-2" />
        <span className="hidden md:inline">Account</span>
        <span className="inline md:hidden">Profile</span>
      </Button>
    );
  }

  // User is not logged in
  return (
    <>
      <div className="flex space-x-2">
        <Button
          variant="secondary"
          className={className}
          onClick={handleLoginClick}
        >
          <LogIn className="h-4 w-4 mr-2" />
          Sign In
        </Button>
        <Button
          variant={variant}
          className={`bg-gradient-to-r from-blue-600 to-purple-600 ${className}`}
          onClick={handleRegisterClick}
        >
          <UserPlus className="h-4 w-4 mr-2" />
          <span className="hidden md:inline">Create Account</span>
          <span className="inline md:hidden">Sign Up</span>
        </Button>
      </div>

      <AuthModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        initialView={modalView}
      />
    </>
  );
};

export default AuthButton;