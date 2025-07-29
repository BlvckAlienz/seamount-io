// File Location: frontend/src/pages/SettingsPage.tsx
// Description: The definitive, corrected, and production-ready user settings page.

import React, { useState } from 'react';
import { User, Shield, Bell, Palette, Key, Smartphone, Mail } from 'lucide-react';

// --- CORRECTED IMPORT PATHS ---
// Using robust, absolute paths with the '@' alias from vite.config.ts
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { useAuth } from '@/contexts/AuthContext';

const SettingsPage: React.FC = () => {
  const { user } = useAuth(); // Use the auth context to get user data

  // State for form elements, pre-filled from auth context
  const [profileData, setProfileData] = useState({
    fullName: `${user?.first_name || ''} ${user?.last_name || ''}`.trim(),
    phone: '', // Assuming phone is not in current UserProfile, add if it is
  });

  const [notifications, setNotifications] = useState({
    email: true,
    push: true,
    trading: true,
    security: true,
  });

  const [theme, setTheme] = useState('dark');
  const [twoFA, setTwoFA] = useState(false);
  
  const handleProfileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setProfileData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      {/* Profile Settings */}
      <Card>
        <div className="flex items-center space-x-3 mb-6">
          <User className="h-5 w-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-white">Profile Settings</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Full Name</label>
            <input type="text" name="fullName" value={profileData.fullName} onChange={handleProfileChange} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg"/>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Email Address</label>
            <input type="email" value={user?.email || ''} disabled className="w-full px-3 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-400 cursor-not-allowed"/>
          </div>
        </div>
        <div className="mt-6">
          <Button>Update Profile</Button>
        </div>
      </Card>

      {/* Security Settings */}
      <Card>
        <div className="flex items-center space-x-3 mb-6">
          <Shield className="h-5 w-5 text-green-500" />
          <h3 className="text-lg font-semibold text-white">Security Settings</h3>
        </div>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium text-white">Two-Factor Authentication</h4>
              <p className="text-sm text-gray-400">Add an extra layer of security</p>
            </div>
            <button onClick={() => setTwoFA(!twoFA)} className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${twoFA ? 'bg-blue-600' : 'bg-gray-600'}`}>
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${twoFA ? 'translate-x-6' : 'translate-x-1'}`}/>
            </button>
          </div>
          <div className="border-t border-gray-700 pt-6">
            <h4 className="font-medium text-white mb-4">Change Password</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input type="password" placeholder="Current Password" className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg"/>
                <input type="password" placeholder="New Password" className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg"/>
            </div>
            <Button className="mt-4" icon={Key}>Update Password</Button>
          </div>
        </div>
      </Card>

      {/* Notification Settings */}
      <Card>
        <div className="flex items-center space-x-3 mb-6">
          <Bell className="h-5 w-5 text-yellow-500" />
          <h3 className="text-lg font-semibold text-white">Notification Preferences</h3>
        </div>
        <div className="space-y-4">
          {[
            { key: 'email', label: 'Email Notifications', icon: Mail },
            { key: 'push', label: 'Push Notifications', icon: Smartphone },
            { key: 'security', label: 'Security Alerts', icon: Shield },
          ].map((item) => (
            <div key={item.key} className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <item.icon className="h-5 w-5 text-gray-400" />
                <h4 className="font-medium text-white">{item.label}</h4>
              </div>
              <button onClick={() => setNotifications(prev => ({ ...prev, [item.key]: !prev[item.key as keyof typeof prev] }))} className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${notifications[item.key as keyof typeof notifications] ? 'bg-blue-600' : 'bg-gray-600'}`}>
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${notifications[item.key as keyof typeof notifications] ? 'translate-x-6' : 'translate-x-1'}`}/>
              </button>
            </div>
          ))}
        </div>
      </Card>

      {/* Appearance & Preferences */}
      <Card>
        <div className="flex items-center space-x-3 mb-6">
          <Palette className="h-5 w-5 text-purple-500" />
          <h3 className="text-lg font-semibold text-white">Appearance & Preferences</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-3">Theme</label>
            <div className="space-y-2">
              {['dark', 'light', 'auto'].map((option) => (
                <label key={option} className="flex items-center space-x-3 cursor-pointer">
                  <input type="radio" name="theme" value={option} checked={theme === option} onChange={(e) => setTheme(e.target.value)} className="text-blue-500"/>
                  <span className="text-white capitalize">{option}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default SettingsPage;