// src/components/Payments.tsx
import React from 'react';
import PaymentFlow from './PaymentFlow';
import CrossBorderPayment from './CrossBorderPayment';
import P2PPayment from './P2PPayment';
import FlutterwavePayment from './FlutterwavePayment';

interface PaymentsProps {
  userId: string;
  mode?: 'flow' | 'p2p' | 'cross-border' | 'flutterwave';
  onComplete?: (result: any) => void;
}

const Payments: React.FC<PaymentsProps> = ({ 
  userId, 
  mode = 'flow', 
  onComplete = () => {} 
}) => {
  switch (mode) {
    case 'p2p':
      return <P2PPayment userId={userId} onComplete={onComplete} />;
    case 'cross-border':
      return <CrossBorderPayment userId={userId} onComplete={onComplete} />;
    case 'flutterwave':
      return <FlutterwavePayment userId={userId} onComplete={onComplete} />;
    case 'flow':
    default:
      return <PaymentFlow userId={userId} onComplete={onComplete} />;
  }
};

export default Payments;