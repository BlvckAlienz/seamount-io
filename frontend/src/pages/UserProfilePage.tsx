import React, { useState, useEffect } from 'react';
import { User, Mail, Phone, Globe, CheckCircle, Shield, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Button from './Button';
import Card from './Card';

interface UserProfileProps {
  onUpdateComplete?: () => void;
}

const UserProfile: React.FC<UserProfileProps> = ({ onUpdateComplete }) => {
  const [profile, setProfile] = useState<any>({
    first_name: '',
    last_name: '',
    country_code: '',
    phone: '',
    kyc_level: 0,
    kyc_verified: false,
    algorand_address: ''
  });
  
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  
  const { getProfile, updateProfile, user, kycStatus, kycLevel } = useAuth();

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setLoading(true);
        const userProfile = await getProfile();
        
        if (userProfile) {
          setProfile(userProfile);
        }
      } catch (error) {
        console.error('Failed to fetch profile:', error);
      } finally {
        setLoading(false);
      }
    };
    
    if (user) {
      fetchProfile();
    }
  }, [user, getProfile]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setProfile(prev => ({ ...prev, [name]: value }));
    setFormError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setUpdating(true);
      setFormError(null);
      
      // Only update the fields that can be changed
      const updatedProfile = {
        first_name: profile.first_name,
        last_name: profile.last_name,
        phone: profile.phone,
        country_code: profile.country_code
      };
      
      const { success, error } = await updateProfile(updatedProfile);
      
      if (success) {
        setSuccess(true);
        setTimeout(() => setSuccess(false), 3000);
        if (onUpdateComplete) {
          onUpdateComplete();
        }
      } else if (error) {
        setFormError(error);
      }
      
    } catch (error) {
      setFormError('Failed to update profile');
      console.error('Profile update error:', error);
    } finally {
      setUpdating(false);
    }
  };

  // Country list for profile form
  const countries = [
    { code: 'US', name: 'United States' },
    { code: 'KE', name: 'Kenya' },
    { code: 'NG', name: 'Nigeria' },
    { code: 'ZA', name: 'South Africa' },
    { code: 'GH', name: 'Ghana' },
    { code: 'UG', name: 'Uganda' },
    // Add more countries as needed
  ];

  if (loading) {
    return (
      <Card>
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-700 rounded w-1/3"></div>
          <div className="h-6 bg-gray-700 rounded w-1/2"></div>
          <div className="h-10 bg-gray-700 rounded"></div>
          <div className="h-10 bg-gray-700 rounded"></div>
          <div className="h-10 bg-gray-700 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center space-x-3 mb-6">
        <User className="h-6 w-6 text-blue-500" />
        <h2 className="text-xl font-bold text-white">Your Profile</h2>
      </div>
      
      {success && (
        <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg mb-6 flex items-center">
          <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
          <p className="text-green-400">Profile updated successfully!</p>
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* KYC Status */}
        <div className="p-4 bg-gray-800/50 rounded-lg mb-6">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <Shield className="h-5 w-5 text-blue-400" />
              <div>
                <h3 className="font-medium text-white">Identity Verification</h3>
                <p className="text-xs text-gray-400">KYC Level: {kycLevel}</p>
              </div>
            </div>
            
            <div>
              {kycStatus === 'approved' ? (
                <div className="flex items-center bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-sm">
                  <CheckCircle className="h-4 w-4 mr-1" />
                  Verified
                </div>
              ) : kycStatus === 'pending' ? (
                <div className="flex items-center bg-yellow-500/20 text-yellow-400 px-3 py-1 rounded-full text-sm">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  Pending
                </div>
              ) : (
                <div className="flex items-center bg-red-500/20 text-red-400 px-3 py-1 rounded-full text-sm">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  Not Verified
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Personal Information */}
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">First Name</label>
              <div className="relative">
                <User className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  name="first_name"
                  value={profile.first_name || ''}
                  onChange={handleInputChange}
                  className="w-full pl-10 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="First Name"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Last Name</label>
              <input
                type="text"
                name="last_name"
                value={profile.last_name || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Last Name"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
              <input
                type="email"
                value={user?.email || ''}
                disabled
                className="w-full pl-10 pr-3 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-400 cursor-not-allowed"
                placeholder="Your email address"
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">Email cannot be changed</p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Phone Number</label>
            <div className="relative">
              <Phone className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
              <input
                type="tel"
                name="phone"
                value={profile.phone || ''}
                onChange={handleInputChange}
                className="w-full pl-10 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Your phone number"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Country</label>
            <div className="relative">
              <Globe className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
              <select
                name="country_code"
                value={profile.country_code || ''}
                onChange={handleInputChange}
                className="w-full pl-10 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="" disabled>Select your country</option>
                {countries.map(country => (
                  <option key={country.code} value={country.code}>
                    {country.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
        
        {/* Wallet Address (Read-only) */}
        {profile.algorand_address && (
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Wallet Address</label>
            <input
              type="text"
              value={profile.algorand_address}
              disabled
              className="w-full px-3 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-400 cursor-not-allowed"
            />
            <p className="text-xs text-gray-500 mt-1">Your USDS wallet address</p>
          </div>
        )}
        
        {/* Form errors */}
        {formError && (
          <div className="p-3 bg-red-900/30 border border-red-500/50 rounded-lg">
            <p className="text-sm text-red-400">{formError}</p>
          </div>
        )}
        
        <Button
          type="submit"
          loading={updating}
          className="bg-gradient-to-r from-blue-600 to-purple-600"
        >
          Update Profile
        </Button>
      </form>
    </Card>
  );
};

export default UserProfile;