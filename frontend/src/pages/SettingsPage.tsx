// File: frontend/src/pages/SettingsPage.tsx
import React, { useState, useEffect } from 'react';
import { User, Shield, Bell, Palette, Key, Smartphone, Mail, ArrowLeft, Save } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { apiClient } from '../config/api';

const SettingsPage: React.FC = () => {
  const { user, refreshProfile } = useAuth();
  const [saving, setSaving] = useState(false);

  const [profileData, setProfileData] = useState({
    firstName: user?.first_name || '',
    lastName: user?.last_name || '',
    phone: user?.phone_number || '',
  });

  const [notifications, setNotifications] = useState({
    email: user?.notification_preferences?.email ?? true,
    push: user?.notification_preferences?.push ?? true,
    sms: user?.notification_preferences?.sms ?? true,
  });

  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: ''
  });

  const [theme, setTheme] = useState('dark');
  const [twoFA, setTwoFA] = useState(false);

  useEffect(() => {
    if (user) {
      setProfileData({
        firstName: user.first_name || '',
        lastName: user.last_name || '',
        phone: user.phone_number || '',
      });
      setNotifications({
        email: user.notification_preferences?.email ?? true,
        push: user.notification_preferences?.push ?? true,
        sms: user.notification_preferences?.sms ?? true,
      });
    }
  }, [user]);

  const handleProfileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setProfileData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPasswords(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleUpdateProfile = async () => {
    try {
      setSaving(true);
      await apiClient.put('/api/v1/user/profile', {
        first_name: profileData.firstName,
        last_name: profileData.lastName,
        phone_number: profileData.phone,
      });
      await refreshProfile();
      toast.success('Profile updated successfully');
    } catch (error) {
      console.error('Profile update error:', error);
      toast.error('Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateNotifications = async () => {
    try {
      setSaving(true);
      await apiClient.put('/api/v1/user/profile', {
        notification_preferences: notifications
      });
      await refreshProfile();
      toast.success('Notification preferences updated');
    } catch (error) {
      console.error('Notification update error:', error);
      toast.error('Failed to update preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleUpdatePassword = async () => {
    if (passwords.new !== passwords.confirm) {
      toast.error('New passwords do not match');
      return;
    }
    if (passwords.new.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    try {
      setSaving(true);
      await apiClient.post('/api/v1/user/change-password', {
        current_password: passwords.current,
        new_password: passwords.new,
      });
      setPasswords({ current: '', new: '', confirm: '' });
      toast.success('Password updated successfully');
    } catch (error: any) {
      console.error('Password update error:', error);
      toast.error(error.response?.data?.detail || 'Failed to update password');
    } finally {
      setSaving(false);
    }
  };

  const handleBack = () => {
    window.location.href = '/dashboard';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6 flex items-center gap-4">
          <button
            onClick={handleBack}
            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white">Settings</h1>
            <p className="text-gray-400 text-sm">Manage your account preferences</p>
          </div>
        </div>

        <div className="space-y-6">
          {/* Profile Settings */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-blue-600/20">
                <User className="h-5 w-5 text-blue-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">Profile Settings</h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">First Name</label>
                <input 
                  type="text" 
                  name="firstName" 
                  value={profileData.firstName} 
                  onChange={handleProfileChange} 
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Last Name</label>
                <input 
                  type="text" 
                  name="lastName" 
                  value={profileData.lastName} 
                  onChange={handleProfileChange} 
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Email Address</label>
                <input 
                  type="email" 
                  value={user?.email || ''} 
                  disabled 
                  className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-400 cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Phone Number</label>
                <input 
                  type="tel" 
                  name="phone" 
                  value={profileData.phone} 
                  onChange={handleProfileChange} 
                  placeholder="+234..."
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>
            
            <button
              onClick={handleUpdateProfile}
              disabled={saving}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {saving ? 'Saving...' : 'Update Profile'}
            </button>
          </div>

          {/* Security Settings */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-green-600/20">
                <Shield className="h-5 w-5 text-green-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">Security Settings</h3>
            </div>
            
            <div className="space-y-6">
              <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                <div>
                  <h4 className="font-medium text-white">Two-Factor Authentication</h4>
                  <p className="text-sm text-gray-400">Add an extra layer of security (Coming Soon)</p>
                </div>
                <button 
                  onClick={() => setTwoFA(!twoFA)} 
                  disabled
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition opacity-50 cursor-not-allowed ${twoFA ? 'bg-blue-600' : 'bg-gray-600'}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${twoFA ? 'translate-x-6' : 'translate-x-1'}`}/>
                </button>
              </div>

              <div className="border-t border-gray-700 pt-6">
                <h4 className="font-medium text-white mb-4">Change Password</h4>
                <div className="space-y-4 mb-4">
                  <input 
                    type="password" 
                    name="current"
                    value={passwords.current}
                    onChange={handlePasswordChange}
                    placeholder="Current Password" 
                    className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                  />
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <input 
                      type="password" 
                      name="new"
                      value={passwords.new}
                      onChange={handlePasswordChange}
                      placeholder="New Password" 
                      className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                    />
                    <input 
                      type="password" 
                      name="confirm"
                      value={passwords.confirm}
                      onChange={handlePasswordChange}
                      placeholder="Confirm New Password" 
                      className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                </div>
                <button
                  onClick={handleUpdatePassword}
                  disabled={saving || !passwords.current || !passwords.new}
                  className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  <Key className="h-4 w-4" />
                  {saving ? 'Updating...' : 'Update Password'}
                </button>
              </div>
            </div>
          </div>

          {/* Notification Settings */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-yellow-600/20">
                <Bell className="h-5 w-5 text-yellow-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">Notification Preferences</h3>
            </div>
            
            <div className="space-y-4 mb-6">
              {[
                { key: 'email', label: 'Email Notifications', icon: Mail, desc: 'Receive updates via email' },
                { key: 'push', label: 'Push Notifications', icon: Smartphone, desc: 'Browser notifications' },
                { key: 'sms', label: 'SMS Alerts', icon: Smartphone, desc: 'Text message notifications' },
              ].map((item) => (
                <div key={item.key} className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                  <div className="flex items-center gap-3">
                    <item.icon className="h-5 w-5 text-gray-400" />
                    <div>
                      <h4 className="font-medium text-white">{item.label}</h4>
                      <p className="text-xs text-gray-400">{item.desc}</p>
                    </div>
                  </div>
                  <button 
                    onClick={() => setNotifications(prev => ({ ...prev, [item.key]: !prev[item.key as keyof typeof prev] }))} 
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${notifications[item.key as keyof typeof notifications] ? 'bg-blue-600' : 'bg-gray-600'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${notifications[item.key as keyof typeof notifications] ? 'translate-x-6' : 'translate-x-1'}`}/>
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={handleUpdateNotifications}
              disabled={saving}
              className="flex items-center gap-2 bg-yellow-600 hover:bg-yellow-700 text-white px-6 py-3 rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {saving ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>

          {/* Appearance */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-purple-600/20">
                <Palette className="h-5 w-5 text-purple-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">Appearance</h3>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">Theme</label>
              <div className="space-y-2">
                {[
                  { value: 'dark', label: 'Dark Mode', desc: 'Easier on the eyes' },
                  { value: 'light', label: 'Light Mode', desc: 'Coming soon' },
                  { value: 'auto', label: 'Auto', desc: 'Match system settings' }
                ].map((option) => (
                  <label 
                    key={option.value} 
                    className={`flex items-center justify-between p-4 rounded-lg border cursor-pointer transition ${
                      theme === option.value 
                        ? 'bg-blue-600/20 border-blue-500' 
                        : 'bg-gray-800/50 border-gray-700 hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input 
                        type="radio" 
                        name="theme" 
                        value={option.value} 
                        checked={theme === option.value} 
                        onChange={(e) => setTheme(e.target.value)}
                        disabled={option.value !== 'dark'}
                        className="text-blue-500"
                      />
                      <div>
                        <span className="text-white font-medium">{option.label}</span>
                        <p className="text-xs text-gray-400">{option.desc}</p>
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Account Info */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-gray-600/20">
                <Shield className="h-5 w-5 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">Account Information</h3>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-400">Account Status</p>
                  <p className="text-white font-medium capitalize">{user?.kyc_status?.replace('_', ' ') || 'Not Started'}</p>
                </div>
                <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                  user?.kyc_status === 'verified' || user?.kyc_status === 'approved'
                    ? 'bg-green-600/20 text-green-400'
                    : user?.kyc_status === 'pending' || user?.kyc_status === 'in_progress'
                    ? 'bg-yellow-600/20 text-yellow-400'
                    : 'bg-gray-600/20 text-gray-400'
                }`}>
                  {user?.role === 'tribe' ? 'Verified' : 'Alien'}
                </div>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-400">KYC Level</p>
                  <p className="text-white font-medium">{user?.kyc_level || 0} / 3</p>
                </div>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-400">Account Created</p>
                  <p className="text-white font-medium">
                    {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;