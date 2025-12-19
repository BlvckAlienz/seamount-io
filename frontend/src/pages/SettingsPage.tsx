// File: frontend/src/pages/SettingsPage.tsx
import React, { useState, useEffect } from 'react';
import { User, Shield, Key, ArrowLeft, Save, Phone, Globe, CheckCircle, X, Calendar, Briefcase, Building, Target, Clock } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { supabase } from '../lib/supabase';
import { useNavigate } from 'react-router-dom';
import ResetPassword from '@/components/auth/ResetPassword';

// Country data with calling codes
const COUNTRIES = [
  { code: 'NG', name: 'Nigeria', dialCode: '+234' },
  { code: 'US', name: 'United States', dialCode: '+1' },
  { code: 'GB', name: 'United Kingdom', dialCode: '+44' },
  { code: 'CA', name: 'Canada', dialCode: '+1' },
  { code: 'AU', name: 'Australia', dialCode: '+61' },
  { code: 'DE', name: 'Germany', dialCode: '+49' },
  { code: 'FR', name: 'France', dialCode: '+33' },
  { code: 'IT', name: 'Italy', dialCode: '+39' },
  { code: 'ES', name: 'Spain', dialCode: '+34' },
  { code: 'BR', name: 'Brazil', dialCode: '+55' },
  { code: 'IN', name: 'India', dialCode: '+91' },
  { code: 'CN', name: 'China', dialCode: '+86' },
  { code: 'JP', name: 'Japan', dialCode: '+81' },
  { code: 'ZA', name: 'South Africa', dialCode: '+27' },
  { code: 'KE', name: 'Kenya', dialCode: '+254' },
  { code: 'GH', name: 'Ghana', dialCode: '+233' },
  { code: 'AE', name: 'UAE', dialCode: '+971' },
  { code: 'SA', name: 'Saudi Arabia', dialCode: '+966' },
  { code: 'RU', name: 'Russia', dialCode: '+7' },
  { code: 'KR', name: 'South Korea', dialCode: '+82' }
];

interface UserProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  country_code: string;
  country: string;
  kyc_status: string;
  kyc_level: number;
  account_type?: string;
  role: string;
  created_at: string;
  updated_at: string;
  date_of_birth?: string;
  occupation?: string;
  source_of_funds?: string;
  risk_tolerance?: string;
  cumulative_volume_30d?: number;
  wallet_addresses?: any;
  algorand_address?: string;
}

const SettingsPage: React.FC = () => {
  const { user, refreshProfile } = useAuth();
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [resetPasswordOpen, setResetPasswordOpen] = useState(false);

  // Profile data - only phone_number is editable
  const [profileData, setProfileData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phoneNumber: '',
    countryCode: 'NG',
    country: 'Nigeria'
  });

  const [currentCountry, setCurrentCountry] = useState({
    code: 'NG',
    name: 'Nigeria',
    dialCode: '+234'
  });

  // KYC additional data
  const [kycData, setKycData] = useState({
    date_of_birth: '',
    occupation: '',
    source_of_funds: '',
    risk_tolerance: 'medium'
  });

  // Fetch user profile data
  useEffect(() => {
    fetchUserProfile();
  }, [user]);

  const fetchUserProfile = async () => {
    try {
      if (!user?.id) return;

      const { data, error } = await supabase
        .from('user_profiles')
        .select('*')
        .eq('id', user.id)
        .single();

      if (error) throw error;

      if (data) {
        console.log('Profile data:', data);
        
        // Parse phone number
        let phoneNumber = data.phone_number || '';
        let countryCode = data.country_code || 'NG';
        let country = data.country || 'Nigeria';
        
        // If phone is stored with country code, extract it
        if (phoneNumber && phoneNumber.startsWith('+')) {
          const countryMatch = COUNTRIES.find(c => phoneNumber.startsWith(c.dialCode));
          if (countryMatch) {
            countryCode = countryMatch.code;
            country = countryMatch.name;
            phoneNumber = phoneNumber.replace(countryMatch.dialCode, '').trim();
          }
        }

        const countryObj = COUNTRIES.find(c => c.code === countryCode) || COUNTRIES[0];
        
        setProfileData({
          firstName: data.first_name || '',
          lastName: data.last_name || '',
          email: data.email || user.email || '',
          phoneNumber,
          countryCode,
          country
        });
        
        setCurrentCountry(countryObj);
        
        // Set KYC data
        setKycData({
          date_of_birth: data.date_of_birth || '',
          occupation: data.occupation || '',
          source_of_funds: data.source_of_funds || '',
          risk_tolerance: data.risk_tolerance || 'medium'
        });
      }
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
      toast.error('Failed to load profile data');
    }
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, ''); // Only numbers
    setProfileData(prev => ({ ...prev, phoneNumber: value }));
  };

  const handleCountryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const countryCode = e.target.value;
    const country = COUNTRIES.find(c => c.code === countryCode) || COUNTRIES[0];
    setCurrentCountry(country);
    setProfileData(prev => ({ 
      ...prev, 
      countryCode,
      country: country.name 
    }));
  };

  const validatePhoneNumber = (phone: string, country: typeof currentCountry) => {
    const fullNumber = country.dialCode + phone;
    
    // Basic validation - adjust based on country
    switch (country.code) {
      case 'NG': // Nigeria: +234 followed by 10 digits
        return phone.length === 10 && /^[0-9]{10}$/.test(phone);
      case 'US': // US: +1 followed by 10 digits
      case 'CA':
        return phone.length === 10 && /^[0-9]{10}$/.test(phone);
      case 'GB': // UK: +44 followed by 10-11 digits
        return phone.length >= 10 && phone.length <= 11 && /^[0-9]+$/.test(phone);
      default:
        return phone.length >= 8 && phone.length <= 15 && /^[0-9]+$/.test(phone);
    }
  };

  const handleUpdateProfile = async () => {
    if (!validatePhoneNumber(profileData.phoneNumber, currentCountry)) {
      toast.error(`Please enter a valid phone number for ${currentCountry.name}`);
      return;
    }

    setSaving(true);
    try {
      const fullPhone = currentCountry.dialCode + profileData.phoneNumber;

      const { error } = await supabase
        .from('user_profiles')
        .update({
          phone_number: fullPhone,
          country_code: currentCountry.code,
          country: currentCountry.name,
          updated_at: new Date().toISOString()
        })
        .eq('id', user?.id);

      if (error) throw error;

      toast.success('Phone number updated successfully');
      await refreshProfile();
    } catch (error: any) {
      console.error('Profile update error:', error);
      toast.error('Failed to update phone number');
    } finally {
      setSaving(false);
    }
  };

  const handleResetPasswordSuccess = () => {
    setResetPasswordOpen(false);
    toast.success('Password reset email sent. Please check your inbox.');
  };

  const handleBack = () => {
    navigate('/dashboard');
  };

  // Format date nicely
  const formatDate = (dateString: string) => {
    if (!dateString) return 'Not set';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  // Get KYC status color
  const getKycStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'verified':
      case 'approved':
        return 'text-green-400';
      case 'pending':
      case 'in_progress':
        return 'text-yellow-400';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 md:p-8">
      {/* Close Button */}
      <button
        onClick={handleBack}
        className="absolute top-6 left-6 p-3 rounded-full bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 text-gray-400 hover:text-white transition-colors z-10"
        title="Close"
      >
        <X className="h-6 w-6" />
      </button>

      <div className="max-w-4xl mx-auto">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-3 mb-4 px-6 py-3 bg-gradient-to-r from-blue-500/20 to-blue-500/20 rounded-full border border-blue-500/30">
            <User className="h-5 w-5 text-blue-400" />
            <span className="text-blue-400 font-semibold text-sm">ACCOUNT SETTINGS</span>
          </div>

          <h1 className="text-4xl md:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white via-blue-100 to-blue-300 mb-3">
            Account Settings
          </h1>

          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Manage your account information and preferences
          </p>
        </div>

        <div className="space-y-6">
          {/* Profile Settings */}
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50 hover:border-slate-600/50 transition-all">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-gradient-to-r from-blue-600 to-blue-700">
                <User className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-white">Profile Information</h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              {/* First Name - Read Only */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">First Name</label>
                <div className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-lg text-gray-400 cursor-not-allowed">
                  {profileData.firstName || 'Not set'}
                </div>
              </div>
              
              {/* Last Name - Read Only */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Last Name</label>
                <div className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-lg text-gray-400 cursor-not-allowed">
                  {profileData.lastName || 'Not set'}
                </div>
              </div>
              
              {/* Email - Read Only */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-400 mb-2">Email Address</label>
                <div className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-lg text-gray-400 cursor-not-allowed">
                  {profileData.email || user?.email || 'Not set'}
                </div>
              </div>

              {/* Phone Number - Editable */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-400 mb-2">Phone Number</label>
                <div className="flex gap-2">
                  {/* Country Code Dropdown */}
                  <div className="relative flex-1 max-w-[200px]">
                    <Globe className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 h-4 w-4" />
                    <select
                      value={currentCountry.code}
                      onChange={handleCountryChange}
                      className="w-full pl-10 pr-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-blue-500 focus:outline-none appearance-none cursor-pointer"
                    >
                      {COUNTRIES.map(country => (
                        <option key={country.code} value={country.code}>
                          {country.name} ({country.dialCode})
                        </option>
                      ))}
                    </select>
                    <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none">
                      ▼
                    </div>
                  </div>

                  {/* Phone Number Input */}
                  <div className="flex-1 relative">
                    <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 h-4 w-4" />
                    <input
                      type="tel"
                      value={profileData.phoneNumber}
                      onChange={handlePhoneChange}
                      placeholder={`Enter phone number`}
                      className="w-full pl-10 pr-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                    />
                    {profileData.phoneNumber && validatePhoneNumber(profileData.phoneNumber, currentCountry) && (
                      <CheckCircle className="absolute right-3 top-1/2 transform -translate-y-1/2 text-green-500 h-4 w-4" />
                    )}
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Format: {currentCountry.dialCode} XXX XXX XXXX
                </p>
              </div>
            </div>
            
            <button
              onClick={handleUpdateProfile}
              disabled={saving || !validatePhoneNumber(profileData.phoneNumber, currentCountry)}
              className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-bold rounded-lg hover:shadow-lg hover:shadow-blue-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="h-4 w-4" />
              {saving ? 'Saving...' : 'Update Phone Number'}
            </button>
          </div>

          {/* Security Settings */}
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50 hover:border-slate-600/50 transition-all">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-gradient-to-r from-green-600 to-green-700">
                <Shield className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-white">Security Settings</h3>
            </div>
            
            <div className="space-y-6">
              {/* Two-Factor Authentication - Coming Soon */}
              <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-lg border border-slate-700/50">
                <div>
                  <h4 className="font-medium text-white">Two-Factor Authentication</h4>
                  <p className="text-sm text-gray-400">Add an extra layer of security (Coming Soon)</p>
                </div>
                <button 
                  disabled
                  className="px-4 py-2 bg-slate-700 text-gray-400 rounded-lg text-sm font-medium cursor-not-allowed"
                >
                  Enable
                </button>
              </div>

              {/* Change Password */}
              <div className="border-t border-slate-700/50 pt-6">
                <h4 className="font-medium text-white mb-4">Change Password</h4>
                <p className="text-gray-400 mb-4">Secure your account with a new password</p>
                <button
                  onClick={() => setResetPasswordOpen(true)}
                  className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-green-600 to-green-700 text-white font-bold rounded-lg hover:shadow-lg hover:shadow-green-500/30 transition-all"
                >
                  <Key className="h-4 w-4" />
                  Reset Password via Email
                </button>
              </div>
            </div>
          </div>

          {/* Account Information */}
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50 hover:border-slate-600/50 transition-all">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-gradient-to-r from-purple-600 to-purple-700">
                <User className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-white">Account Information</h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* KYC Level */}
              <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/50">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="h-4 w-4 text-blue-400" />
                  <div className="text-sm text-gray-400">KYC Level</div>
                </div>
                <div className="text-2xl font-black text-white mb-2">
                  {user?.kyc_level || 0} / 3
                </div>
                <div className="flex gap-1">
                  {[1, 2, 3].map(level => (
                    <div 
                      key={level}
                      className={`h-2 flex-1 rounded-full ${level <= (user?.kyc_level || 0) ? 'bg-green-500' : 'bg-slate-700'}`}
                    />
                  ))}
                </div>
                <div className={`text-xs mt-2 ${getKycStatusColor(user?.kyc_status || '')}`}>
                  {user?.kyc_status?.replace('_', ' ') || 'Not started'}
                </div>
              </div>

              {/* Account Created */}
              <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/50">
                <div className="flex items-center gap-2 mb-2">
                  <Calendar className="h-4 w-4 text-blue-400" />
                  <div className="text-sm text-gray-400">Account Created</div>
                </div>
                <div className="text-xl font-bold text-white">
                  {user?.created_at ? formatDate(user.created_at) : 'N/A'}
                </div>
                <div className="text-xs text-gray-500 mt-1">Member since</div>
              </div>

              {/* Account Type */}
              <div className={`rounded-xl p-5 border ${user?.account_type === 'business' ? 'bg-purple-900/20 border-purple-700/50' : 'bg-blue-900/20 border-blue-700/50'}`}>
                <div className="flex items-center gap-2 mb-2">
                  <Building className="h-4 w-4 text-blue-400" />
                  <div className="text-sm text-gray-400">Account Type</div>
                </div>
                <div className={`text-xl font-bold ${user?.account_type === 'business' ? 'text-purple-400' : 'text-blue-400'}`}>
                  {user?.account_type === 'business' ? 'Business' : 'Individual'}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {user?.account_type === 'business' ? 'Corporate account' : 'Personal account'}
                </div>
              </div>

              {/* Trading Volume */}
              <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/50">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="h-4 w-4 text-blue-400" />
                  <div className="text-sm text-gray-400">30-Day Volume</div>
                </div>
                <div className="text-xl font-bold text-white">
                  {formatCurrency(user?.cumulative_volume_30d || 0)}
                </div>
                <div className="text-xs text-gray-400 mt-1">Total trading</div>
              </div>

              {/* KYC Additional Info */}
              {kycData.occupation && (
                <div className="md:col-span-2 bg-slate-800/30 rounded-xl p-5 border border-slate-700/50">
                  <div className="flex items-center gap-2 mb-2">
                    <Briefcase className="h-4 w-4 text-blue-400" />
                    <div className="text-sm text-gray-400">Occupation</div>
                  </div>
                  <div className="text-lg font-medium text-white">
                    {kycData.occupation}
                  </div>
                </div>
              )}

              {/* Source of Funds */}
              {kycData.source_of_funds && (
                <div className="md:col-span-2 bg-slate-800/30 rounded-xl p-5 border border-slate-700/50">
                  <div className="flex items-center gap-2 mb-2">
                    <Building className="h-4 w-4 text-blue-400" />
                    <div className="text-sm text-gray-400">Source of Funds</div>
                  </div>
                  <div className="text-lg font-medium text-white">
                    {kycData.source_of_funds}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Reset Password Dialog */}
      <ResetPassword
        open={resetPasswordOpen}
        onOpenChange={setResetPasswordOpen}
        onSuccess={handleResetPasswordSuccess}
      />
    </div>
  );
};

export default SettingsPage;