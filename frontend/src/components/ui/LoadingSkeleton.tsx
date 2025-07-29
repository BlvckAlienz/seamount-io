import React from 'react';
import { cn } from '../utils/cn';

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
      <div className="relative">
        <Skeleton width="100%" height={`${height}px`} />
        <div className="absolute inset-0 flex items-end justify-around p-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton
              key={i}
              width="12px"
              height={`${Math.random() * (height - 100) + 50}px`}
              className="rounded-t-sm"
            />
          ))}
        </div>
      </div>
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
      {/* Header */}
      <div className="grid grid-cols-6 gap-4 pb-3 border-b border-gray-700/50">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} width="80%" height="16px" />
        ))}
      </div>
      
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="grid grid-cols-6 gap-4 py-3">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <div key={colIndex} className="flex items-center space-x-2">
              {colIndex === 0 && (
                <Skeleton variant="circular" width="32px" height="32px" />
              )}
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
}

export const CardSkeleton: React.FC<CardSkeletonProps> = ({ className }) => {
  return (
    <div className={cn('bg-gray-800/50 backdrop-blur-sm border border-gray-700/30 rounded-xl p-6', className)}>
      <div className="flex items-center justify-between mb-4">
        <Skeleton width="100px" height="16px" />
        <Skeleton variant="circular" width="40px" height="40px" />
      </div>
      <Skeleton width="120px" height="32px" className="mb-2" />
      <div className="flex items-center space-x-2">
        <Skeleton width="16px" height="16px" />
        <Skeleton width="80px" height="16px" />
      </div>
    </div>
  );
};