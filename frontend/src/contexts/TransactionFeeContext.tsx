import React, { createContext, useContext, ReactNode } from 'react';

interface TransactionFeeContextType {
  currentFeeRate: number;
  minRequiredUsds: number;
  calculateFee: (amount: number) => number;
  recommendedUsdsBalance: (transactionAmount: number) => number;
}

const TransactionFeeContext = createContext<TransactionFeeContextType | undefined>(undefined);

export function useTransactionFees() {
  const context = useContext(TransactionFeeContext);
  if (!context) {
    throw new Error('useTransactionFees must be used within a TransactionFeeProvider');
  }
  return context;
}

export const TransactionFeeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Fee configuration
  const feeConfig = {
    standard: 0.0015, // 0.15% for standard transfers
    crossBorder: 0.0045, // 0.45% for cross-border
    swap: 0.003, // 0.3% for swaps
    minFee: 0.05, // $0.05 minimum
    maxFee: 10, // $10 maximum 
    bufferMultiplier: 1.5 // Recommended to keep 1.5x fees worth of USDS
  };

  // Current network fee rate
  const currentFeeRate = feeConfig.standard;
  
  // Minimum required USDS for a basic transaction
  const minRequiredUsds = feeConfig.minFee;

  // Calculate fee for a given amount
  const calculateFee = (amount: number): number => {
    const calculatedFee = amount * currentFeeRate;
    return Math.max(feeConfig.minFee, Math.min(calculatedFee, feeConfig.maxFee));
  };

  // Calculate recommended USDS balance for transaction processing
  const recommendedUsdsBalance = (transactionAmount: number): number => {
    const fee = calculateFee(transactionAmount);
    return fee * feeConfig.bufferMultiplier;
  };

  const value: TransactionFeeContextType = {
    currentFeeRate,
    minRequiredUsds,
    calculateFee,
    recommendedUsdsBalance
  };

  return (
    <TransactionFeeContext.Provider value={value}>
      {children}
    </TransactionFeeContext.Provider>
  );
};