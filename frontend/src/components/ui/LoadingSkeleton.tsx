// File Location: frontend/src/components/ui/LoadingSkeleton.tsx
// Description: The definitive, corrected, and production-ready Loading Skeleton component.

import React from 'react';

// --- CORRECTED IMPORT PATH ---
// Using a robust, absolute path with the '@' alias from vite.config.ts
import { cn } from '@/utils/cn';

interface SkeletonProps {
  className?: string;
  width?: string;
  height?: string;
  variant?: 'default' | 'circular';
}

export const Skeleton: React.FC<SkeletonProps> = ({ 
  className, 
  width, 
  height, 
  variant = 'default' 
}) => {
  return (
    <div
      className={cn(
        'animate-pulse bg-gray-700/50',
        variant === 'circular' ? 'rounded-full' : 'rounded-md',
        className
      )}
      style={{ width, height }}
    />
  );
};

interface ChartSkeletonProps {
  height?: number;
  className?: string;
}

export const ChartSkeleton: React.FC<ChartSkeletonProps> = ({ 
  height = 200, 
  className 
}) => {
  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex justify-between items-center">
        <Skeleton width="120px" height="20px" />
        <div className="flex space-x-2">
          <Skeleton width="60px" height="32px" />
          <Skeleton width="60px" height="32px" />
          <Skeleton width="60px" height="32px" />
        </div>
      </div>
      <Skeleton width="100%" height={`${height}px`} />
    </div>
  );
};

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
  className?: string;
}

export const TableSkeleton: React.FC<TableSkeletonProps> = ({ 
  rows = 5, 
  columns = 6,
  className 
}) => {
  return (
    <div className={cn('space-y-4', className)}>
      <div className={`grid grid-cols-${columns} gap-4 pb-3 border-b border-gray-700/50`}>
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} width="80%" height="16px" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className={`grid grid-cols-${columns} gap-4 py-3`}>
          {Array.from({ length: columns }).map((_, colIndex) => (
            <div key={colIndex} className="flex items-center space-x-2">
              {colIndex === 0 && <Skeleton variant="circular" width="32px" height="32px" />}
              <Skeleton width="60%" height="16px" />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

interface CardSkeletonProps {
  className?: string;
  count?: number; // Added count prop for multiple cards
  height?: number;
}

export const CardSkeleton: React.FC<CardSkeletonProps> = ({ className, count = 1, height = 120 }) => {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{ height: `${height}px` }} className={cn('bg-gray-800/50 backdrop-blur-sm border border-gray-700/30 rounded-xl p-6', className)}>
          <div className="animate-pulse flex space-x-4">
            <div className="flex-1 space-y-4 py-1">
              <div className="h-4 bg-gray-700/50 rounded w-3/4"></div>
              <div className="space-y-2">
                <div className="h-4 bg-gray-700/50 rounded"></div>
                <div className="h-4 bg-gray-700/50 rounded w-5/6"></div>
              </div>
            </div>
          </div>
        </div>
      ))}
    </>
  );
};