// Location: /frontend/src/components/RegisterForm.tsx

import React, { useState } from 'react';
import { User, Mail, Lock, Eye, EyeOff, CheckCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Button from './Button';
import Card from './Card';

// Password validation requirements
const PASSWORD_MIN_LENGTH = 8;
const PASSWORD_REQUIREMENTS = [
  { id: 'length', text: `At least ${PASSWORD_MIN_LENGTH} characters`, regex: new RegExp(`^.{${PASSWORD_MIN_LENGTH},}$`) },
  { id: 'uppercase', text: 'At least one uppercase letter', regex: /[A-Z]/ },
  { id: 'lowercase', text: 'At least one lowercase letter', regex: /[a-z]/ },
  { id: 'number', text: 'At least one number', regex: /[0-9]/ },
  { id: 'special', text: 'At least one special character', regex: /[!@#$%^&*(),.?":{}|<>]/ }
];

interface RegisterFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
  onLoginClick?: () => void;
}

const RegisterForm: React.FC<RegisterFormProps> = ({ onSuccess, onCancel, onLoginClick }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    countryCode: 'US'
  });
  const [passwordStrength, setPasswordStrength] = useState(0);
  const [validRequirements, setValidRequirements] = useState<Record<string, boolean>>({});
  const [showPassword, setShowPassword] = useState(false);
  const [formErrors, setFormErrors] = useState<{[key: string]: string}>({});
  const [successMessage, setSuccessMessage] = useState('');
  
  const { signUp, loading, error } = useAuth();

  const validateForm = () => {
    const errors: {[key: string]: string} = {};
    
    if (!formData.email) {
      errors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      errors.email = 'Email is invalid';
    }
    
    // Enhanced password validation
    const metRequirements = PASSWORD_REQUIREMENTS.reduce((count, req) => {
      return count + (validRequirements[req.id] ? 1 : 0);
    }, 0);
    
    if (metRequirements < 3) {
      errors.password = 'Password doesn\'t meet minimum requirements';
    }
    
    if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }
    
    if (!formData.firstName) {
      errors.firstName = 'First name is required';
    }
    
    if (!formData.lastName) {
      errors.lastName = 'Last name is required';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Check password strength when password field changes
    if (name === 'password') {
      evaluatePasswordStrength(value);
    }
    
    // Clear error when field is edited
    if (formErrors[name]) {
      setFormErrors(prev => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }
  };

  // Evaluate password strength and requirements
  const evaluatePasswordStrength = (password: string) => {
    // Check each requirement
    const requirements: Record<string, boolean> = {};
    PASSWORD_REQUIREMENTS.forEach(req => {
      requirements[req.id] = req.regex.test(password);
    });
    
    // Count met requirements
    const metRequirements = Object.values(requirements).filter(Boolean).length;
    
    // Calculate strength percentage (0-100)
    const strengthPercentage = Math.min(100, (metRequirements / PASSWORD_REQUIREMENTS.length) * 100);
    
    setPasswordStrength(strengthPercentage);
    setValidRequirements(requirements);
  };

  // Get color based on password strength
  const getStrengthColor = () => {
    if (passwordStrength < 40) return 'bg-red-500';
    if (passwordStrength < 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  // Get strength label
  const getStrengthLabel = () => {
    if (passwordStrength < 40) return 'Weak';
    if (passwordStrength < 70) return 'Medium';
    return 'Strong';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    const { success, error } = await signUp(formData.email, formData.password);
    
    if (success) {
      setSuccessMessage('Registration successful! Please check your email to verify your account.');
      if (onSuccess) {
        setTimeout(() => {
          onSuccess();
        }, 2000);
      }
    } else if (error) {
      setFormErrors(prev => ({ ...prev, form: error }));
    }
  };

  // Country list for registration form
  const countries = [
    { code: 'US', name: 'United States' },
    { code: 'KE', name: 'Kenya' },
    { code: 'NG', name: 'Nigeria' },
    { code: 'ZA', name: 'South Africa' },
    { code: 'GH', name: 'Ghana' },
    { code: 'UG', name: 'Uganda' },
    // Add more countries as needed
  ];

  return (
    <Card>
      <h2 className="text-2xl font-bold text-white mb-6">Create Your Account</h2>
      
      {successMessage ? (
        <div className="text-center py-8">
          <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">Registration Successful</h3>
          <p className="text-gray-300 mb-6">{successMessage}</p>
          {onLoginClick && (
            <Button onClick={onLoginClick}>
              Proceed to Login
            </Button>
          )}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">First Name</label>
              <div className="relative">
                <User className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  name="firstName"
                  value={formData.firstName}
                  onChange={handleInputChange}
                  className={`w-full pl-10 pr-3 py-2 bg-gray-800 border ${formErrors.firstName ? 'border-red-500' : 'border-gray-700'} rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500`}
                  placeholder="First Name"
                />
              </div>
              {formErrors.firstName && (
                <p className="mt-1 text-xs text-red-500">{formErrors.firstName}</p>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Last Name</label>
              <input
                type="text"
                name="lastName"
                value={formData.lastName}
                onChange={handleInputChange}
                className={`w-full px-3 py-2 bg-gray-800 border ${formErrors.lastName ? 'border-red-500' : 'border-gray-700'} rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500`}
                placeholder="Last Name"
              />
              {formErrors.lastName && (
                <p className="mt-1 text-xs text-red-500">{formErrors.lastName}</p>
              )}
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                className={`w-full pl-10 pr-3 py-2 bg-gray-800 border ${formErrors.email ? 'border-red-500' : 'border-gray-700'} rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500`}
                placeholder="Your email address"
              />
            </div>
            {formErrors.email && (
              <p className="mt-1 text-xs text-red-500">{formErrors.email}</p>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Country</label>
            <select
              name="countryCode"
              value={formData.countryCode}
              onChange={handleInputChange}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {countries.map(country => (
                <option key={country.code} value={country.code}>
                  {country.name}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                className={`w-full pl-10 pr-10 py-2 bg-gray-800 border ${formErrors.password ? 'border-red-500' : 'border-gray-700'} rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500`}
                placeholder="Create a strong password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-2.5 text-gray-400"
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
            {formErrors.password && (
              <p className="mt-1 text-xs text-red-500">{formErrors.password}</p>
            )}

            {/* Password strength meter */}
            {formData.password && (
              <div className="mt-2">
                <div className="flex items-center justify-between mb-1">
                  <div className="h-2 w-full bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${getStrengthColor()} transition-all duration-300`}
                      style={{ width: `${passwordStrength}%` }}
                    ></div>
                  </div>
                  <span className={`text-xs ml-2 ${
                    passwordStrength < 40 ? 'text-red-400' : 
                    passwordStrength < 70 ? 'text-yellow-400' : 'text-green-400'
                  }`}>
                    {getStrengthLabel()}
                  </span>
                </div>

                {/* Password requirements */}
                <div className="mt-2 grid grid-cols-2 gap-y-1 gap-x-2">
                  {PASSWORD_REQUIREMENTS.map(req => (
                    <div key={req.id} className="flex items-center">
                      <div className={`w-2 h-2 rounded-full mr-2 ${
                        validRequirements[req.id] ? 'bg-green-400' : 'bg-gray-500'
                      }`}></div>
                      <span className={`text-xs ${
                        validRequirements[req.id] ? 'text-green-400' : 'text-gray-400'
                      }`}>
                        {req.text}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Confirm Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
              <input
                type={showPassword ? 'text' : 'password'}
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                className={`w-full pl-10 pr-3 py-2 bg-gray-800 border ${formErrors.confirmPassword ? 'border-red-500' : 'border-gray-700'} rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500`}
                placeholder="Confirm your password"
              />
            </div>
            {formErrors.confirmPassword && (
              <p className="mt-1 text-xs text-red-500">{formErrors.confirmPassword}</p>
            )}
          </div>
          
          {(error || formErrors.form) && (
            <div className="p-3 bg-red-900/30 border border-red-500/50 rounded-lg">
              <p className="text-sm text-red-400">{error || formErrors.form}</p>
            </div>
          )}
          
          <div className="pt-2">
            <p className="text-xs text-gray-400 mb-4">
              By creating an account, you agree to our Terms of Service and Privacy Policy. 
              You'll need to verify your identity to access all features.
            </p>
            
            <div className="flex space-x-4">
              {onCancel && (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={onCancel}
                  className="flex-1"
                >
                  Cancel
                </Button>
              )}
              <Button
                type="submit"
                className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600"
                loading={loading}
              >
                Create Account
              </Button>
            </div>
          </div>
          
          {onLoginClick && (
            <div className="text-center mt-4">
              <button 
                type="button"
                onClick={onLoginClick}
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                Already have an account? Sign in
              </button>
            </div>
          )}
        </form>
      )}
    </Card>
  );
};

export default RegisterForm;