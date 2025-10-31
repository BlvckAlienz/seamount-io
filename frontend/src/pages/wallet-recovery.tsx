// File: frontend/src/pages/wallet-recovery.tsx
// ✅ STANDALONE WALLET RECOVERY PAGE

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import WalletRecoveryModal from '../components/wallet/WalletRecoveryModal';

const WalletRecoveryPage = () => {
  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(true);

  const handleClose = () => {
    setShowModal(false);
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <WalletRecoveryModal isOpen={showModal} onClose={handleClose} />
    </div>
  );
};

export default WalletRecoveryPage;