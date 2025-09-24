import React from 'react';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  loading?: boolean;
  variant?: 'primary' | 'outline';
  size?: 'sm' | 'md';
}

const Button: React.FC<ButtonProps> = ({ 
  children, 
  onClick, 
  loading = false,
  variant = 'primary',
  size = 'md'
}) => {
  const baseStyle = 'rounded font-medium transition-colors focus:outline-none focus:ring-2';
  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    outline: 'border border-gray-300 text-gray-700 hover:bg-gray-50 focus:ring-blue-500'
  };
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2'
  };

  return (
    <button
      className={`${baseStyle} ${variants[variant]} ${sizes[size]} ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
      onClick={onClick}
      disabled={loading}
    >
      {loading ? 'Loading...' : children}
    </button>
  );
};

export default Button;