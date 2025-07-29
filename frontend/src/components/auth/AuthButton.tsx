import React, { useState } from 'react';
import { LogIn, UserPlus, User, Shield } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Button from './Button';
import AuthModal from './AuthModal';

interface AuthButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost';
  className?: string;
}

const AuthButton: React.FC<AuthButtonProps> = ({ 
  variant = 'primary',
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
          icon={Shield}
          onClick={handleKycClick}
        >
          Verify Identity
        </Button>
      );
    }
    
    // User is logged in and verified
    return (
      <Button
        variant={variant}
        className={`bg-gradient-to-r from-green-600 to-teal-600 ${className}`}
        icon={User}
      >
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
          icon={LogIn}
          onClick={handleLoginClick}
        >
          Sign In
        </Button>
        <Button
          variant={variant}
          className={`bg-gradient-to-r from-blue-600 to-purple-600 ${className}`}
          icon={UserPlus}
          onClick={handleRegisterClick}
        >
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