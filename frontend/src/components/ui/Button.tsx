// File Location: frontend/src/components/ui/Button.tsx
// Description: The definitive, corrected, and production-ready Button component.

import React from 'react';
import { Loader2 } from 'lucide-react';

// --- CORRECTED IMPORT PATH ---
// Using a robust, absolute path with the '@' alias from vite.config.ts
import { cn } from '@/utils/cn';

// --- ENHANCED PROPS FOR FLEXIBILITY ---
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ComponentType<{ className?: string }>;
  elevated?: boolean;
  animated?: boolean;
}

const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  icon: Icon,
  elevated = false,
  animated = false,
  ...props // Pass down other button attributes like type, onClick etc.
}) => {
  const baseClasses = 'inline-flex items-center justify-center font-semibold rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed';
  
  const variantClasses = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-gray-700 hover:bg-gray-600 text-white',
    ghost: 'bg-transparent hover:bg-gray-800/50 text-gray-300 hover:text-white',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
    outline: 'bg-transparent border border-gray-700 hover:bg-gray-800/50 text-gray-300 hover:text-white',
  };

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  };
  
  const elevatedClasses = elevated ? 'shadow-lg hover:shadow-xl hover:-translate-y-0.5' : '';
  const animatedClasses = animated ? 'transform-gpu' : '';

  return (
    <button
      className={cn(
        baseClasses,
        variantClasses[variant],
        sizeClasses[size],
        elevatedClasses,
        animatedClasses,
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <>
          {Icon && <Icon className="h-4 w-4 mr-2" />}
          {children}
        </>
      )}
    </button>
  );
};

export default Button;