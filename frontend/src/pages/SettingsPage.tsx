import React, { useState } from 'react';
import { User, Shield, Bell, Palette, Globe, Key, Smartphone, Mail } from 'lucide-react';
import Card from '../components/Card';
import Button from '../components/Button';

const Settings: React.FC = () => {
  const [notifications, setNotifications] = useState({
    email: true,
    push: true,
    trading: true,
    security: true,
  });

  const [theme, setTheme] = useState('dark');
  const [language, setLanguage] = useState('en');
  const [twoFA, setTwoFA] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3 mb-6">
        <h1 className="text-2xl font-bold text-white">Settings</h1>
      </div>

      {/* Profile Settings */}
      <Card>
        <div className="flex items-center space-x-3 mb-6">
          <User className="h-5 w-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-white">Profile Settings</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Full Name</label>
            <input
              type="text"
              defaultValue="John Doe"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Email Address</label>
            <input
              type="email"
              defaultValue="john.doe@example.com"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Phone Number</label>
            <input
              type="tel"
              defaultValue="+1 (555) 123-4567"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Time Zone</label>
            <select className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option>UTC-5 (Eastern Time)</option>
              <option>UTC-8 (Pacific Time)</option>
              <option>UTC+0 (GMT)</option>
            </select>
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
              <p className="text-sm text-gray-400">Add an extra layer of security to your account</p>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setTwoFA(!twoFA)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                  twoFA ? 'bg-blue-600' : 'bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                    twoFA ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
              <Smartphone className="h-5 w-5 text-gray-400" />
            </div>
          </div>
          
          <div className="border-t border-gray-700 pt-6">
            <h4 className="font-medium text-white mb-4">Change Password</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Current Password</label>
                <input
                  type="password"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">New Password</label>
                <input
                  type="password"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <Button className="mt-4" icon={Key}>
              Update Password
            </Button>
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
            { key: 'email', label: 'Email Notifications', description: 'Receive notifications via email', icon: Mail },
            { key: 'push', label: 'Push Notifications', description: 'Receive push notifications on your device', icon: Smartphone },
            { key: 'trading', label: 'Trading Alerts', description: 'Get notified about trading opportunities', icon: Bell },
            { key: 'security', label: 'Security Alerts', description: 'Important security and account updates', icon: Shield },
          ].map((item) => (
            <div key={item.key} className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <item.icon className="h-5 w-5 text-gray-400" />
                <div>
                  <h4 className="font-medium text-white">{item.label}</h4>
                  <p className="text-sm text-gray-400">{item.description}</p>
                </div>
              </div>
              <button
                onClick={() => setNotifications(prev => ({ ...prev, [item.key]: !prev[item.key as keyof typeof prev] }))}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                  notifications[item.key as keyof typeof notifications] ? 'bg-blue-600' : 'bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                    notifications[item.key as keyof typeof notifications] ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
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
              {[
                { value: 'dark', label: 'Dark Mode', description: 'Dark theme for better visibility' },
                { value: 'light', label: 'Light Mode', description: 'Light theme for day usage' },
                { value: 'auto', label: 'Auto', description: 'Follow system preference' },
              ].map((option) => (
                <label key={option.value} className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="radio"
                    name="theme"
                    value={option.value}
                    checked={theme === option.value}
                    onChange={(e) => setTheme(e.target.value)}
                    className="text-blue-500"
                  />
                  <div>
                    <div className="text-white">{option.label}</div>
                    <div className="text-sm text-gray-400">{option.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Language</label>
            <select 
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="en">English</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
              <option value="de">Deutsch</option>
              <option value="zh">中文</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Danger Zone */}
      <Card className="border-red-500/20">
        <div className="flex items-center space-x-3 mb-6">
          <Shield className="h-5 w-5 text-red-500" />
          <h3 className="text-lg font-semibold text-white">Danger Zone</h3>
        </div>
        
        <div className="space-y-4">
          <div className="p-4 border border-red-500/20 rounded-lg bg-red-500/5">
            <h4 className="font-medium text-white mb-2">Close Account</h4>
            <p className="text-sm text-gray-400 mb-4">
              Permanently delete your account and all associated data. This action cannot be undone.
            </p>
            <Button variant="danger" size="sm">
              Close Account
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Settings;