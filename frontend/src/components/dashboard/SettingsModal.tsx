// File: frontend/src/components/dashboard/SettingsModal.tsx
import React, { useState } from 'react';
import { X, Wallet, Shield, User, Bell, Globe, Key, LogOut, Eye, EyeOff, Check, Copy } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import toast from 'react-hot-toast';
import { apiClient } from '../../config/api';
import { toastInfo, toastWarning } from '@/lib/toast-helpers';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const { user, userProfile, signOut } = useAuth();
  const [activeTab, setActiveTab] = useState('wallet');
  const [showPrivateKey, setShowPrivateKey] = useState(false);
  const [exporting, setExporting] = useState(false);

  if (!isOpen) return null;

  const handleExportWallet = async () => {
    setExporting(true);
    try {
      const response = await apiClient.get('/api/v1/user/export-wallet');
      if (response.data.encryptedData) {
        // Download wallet backup
        const blob = new Blob([JSON.stringify(response.data.encryptedData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `seamount-wallet-backup-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        toast.success('Wallet backup downloaded securely');
      }
    } catch (error) {
      toast.error('Failed to export wallet');
    } finally {
      setExporting(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const tabs = [
    { id: 'wallet', label: 'Wallet', icon: Wallet },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ];

  return (
    <div 
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-gray-800 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden border border-gray-700 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-white">Settings</h2>
            <p className="text-gray-400 text-sm">Manage your account and wallet</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="h-6 w-6 text-gray-400" />
          </button>
        </div>

        <div className="flex h-[500px]">
          {/* Sidebar */}
          <div className="w-48 border-r border-gray-700 bg-gray-900/50">
            <nav className="p-4 space-y-2">
              {tabs.map(tab => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeTab === tab.id
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-400 hover:text-white hover:bg-gray-700'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 p-6 overflow-y-auto">
            {activeTab === 'wallet' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-white">Wallet Management</h3>
                
                {/* Wallet Address */}
                <div className="bg-gray-900/50 rounded-lg p-4">
                  <label className="block text-sm text-gray-400 mb-2">Your Wallet Address</label>
                  <div className="flex items-center gap-3">
                    <code className="flex-1 font-mono text-sm text-white bg-gray-800 px-3 py-2 rounded">
                      {userProfile?.algorand_address || 'No wallet address found'}
                    </code>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(userProfile?.algorand_address || '');
                        toast.success('Address copied!');
                      }}
                      className="p-2 hover:bg-gray-700 rounded transition-colors"
                    >
                      <Copy className="h-4 w-4 text-gray-400" />
                    </button>
                  </div>
                </div>

                {/* Wallet Actions */}
                <div className="grid grid-cols-1 gap-3">
                  <button
                    onClick={handleExportWallet}
                    disabled={exporting}
                    className="flex items-center gap-3 p-4 border border-gray-600 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
                  >
                    <Key className="h-5 w-5 text-yellow-400" />
                    <div className="text-left">
                      <div className="text-white font-medium">Export Wallet Backup</div>
                      <div className="text-gray-400 text-sm">Download encrypted wallet data</div>
                    </div>
                  </button>

                  <button
                    onClick={() => toastInfo('Multi-chain wallet connection coming soon')}
                    className="flex items-center gap-3 p-4 border border-gray-600 rounded-lg hover:bg-gray-700 transition-colors"
                  >
                    <Wallet className="h-5 w-5 text-blue-400" />
                    <div className="text-left">
                      <div className="text-white font-medium">Connect External Wallet</div>
                      <div className="text-gray-400 text-sm">Link MetaMask, Pera, or other wallets</div>
                    </div>
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-white">Security Settings</h3>
                
                <div className="space-y-4">
                  <div className="bg-gray-900/50 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-white font-medium">Two-Factor Authentication</div>
                        <div className="text-gray-400 text-sm">Add extra security to your account</div>
                      </div>
                      <button
                        onClick={() => toastInfo('2FA setup coming soon')}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm"
                      >
                        Enable
                      </button>
                    </div>
                  </div>

                  <div className="bg-gray-900/50 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-white font-medium">Session Management</div>
                        <div className="text-gray-400 text-sm">Manage active login sessions</div>
                      </div>
                      <button
                        onClick={() => toastInfo('Session management coming soon')}
                        className="px-4 py-2 border border-gray-600 hover:bg-gray-700 rounded-lg text-white text-sm"
                      >
                        View
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'profile' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-white">Profile Information</h3>
                
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-400 mb-2">First Name</label>
                      <div className="text-white bg-gray-900/50 px-3 py-2 rounded">
                        {userProfile?.first_name || 'Not set'}
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-2">Last Name</label>
                      <div className="text-white bg-gray-900/50 px-3 py-2 rounded">
                        {userProfile?.last_name || 'Not set'}
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm text-gray-400 mb-2">Email</label>
                    <div className="text-white bg-gray-900/50 px-3 py-2 rounded">
                      {user?.email}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm text-gray-400 mb-2">Country</label>
                    <div className="text-white bg-gray-900/50 px-3 py-2 rounded">
                      {userProfile?.country_code || 'Not set'}
                    </div>
                  </div>

                  <button
                    onClick={() => toastInfo('Profile editing coming soon')}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg transition-colors"
                  >
                    Edit Profile
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-white">Notification Preferences</h3>
                
                <div className="space-y-4">
                  {[
                    { label: 'Transaction Notifications', description: 'Get alerts for incoming and outgoing payments' },
                    { label: 'Security Alerts', description: 'Important security updates and login attempts' },
                    { label: 'Market Updates', description: 'Price movements and market news' },
                    { label: 'Product Updates', description: 'New features and platform improvements' },
                  ].map((item, index) => (
                    <div key={index} className="flex items-center justify-between p-4 bg-gray-900/50 rounded-lg">
                      <div>
                        <div className="text-white font-medium">{item.label}</div>
                        <div className="text-gray-400 text-sm">{item.description}</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" className="sr-only peer" defaultChecked />
                        <div className="w-11 h-6 bg-gray-700 peer-focus:ring-4 peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-700 p-4 bg-gray-900/50">
          <div className="flex justify-between items-center">
            <button
              onClick={signOut}
              className="flex items-center gap-2 text-red-400 hover:text-red-300 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;