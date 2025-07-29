import React from 'react';
import { cn } from '../utils/cn';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  glassy?: boolean;
  hover?: boolean;
  onClick?: () => void;
}

const Card: React.FC<CardProps> = ({ 
  children, 
  className, 
  glassy = false, 
  hover = false,
  onClick
}) => {
  return (
    <div
      className={cn(
        'rounded-xl p-6 transition-all duration-300',
        glassy 
          ? 'bg-gray-800/50 backdrop-blur-sm border border-gray-700/30' 
          : 'bg-gray-800 border border-gray-700',
        hover && 'hover:bg-gray-700/50 hover:border-gray-600/50 hover:scale-[1.02] cursor-pointer',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
    >
      {children}
    </div>
  );
};

export default Card;