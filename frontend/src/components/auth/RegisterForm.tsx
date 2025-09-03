// File Location: frontend/src/components/auth/RegisterForm.tsx
// CRITICAL FIX: Corrected country code mapping and form submission flow

import React, { useState, useMemo, useRef } from 'react';
import { User, Mail, Lock, CheckCircle, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';
import HCaptcha from '@hcaptcha/react-hcaptcha';
import countryList from 'react-select-country-list';

interface IRegisterFormProps {
  onSuccess?: () => void;
  onLoginClick?: () => void;
}

interface FormData {
  email: string;
  password: string;
  confirmPassword: string;
  firstName: string;
  lastName: string;
  countryCode: string;
  captchaToken: string | null;
}

interface FormErrors {
  email?: string;
  password?: string;
  confirmPassword?: string;
  captcha?: string;
  form?: string;
}

const RegisterForm: React.FC<IRegisterFormProps> = ({ onSuccess, onLoginClick }) => {
  const [formData, setFormData] = useState<FormData>({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    countryCode: 'US',
    captchaToken: null,
  });
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [validRequirements, setValidRequirements] = useState<Record<string, boolean>>({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const captchaRef = useRef<HCaptcha>(null);
  const { signUp } = useAuth();
  const navigate = useNavigate();

  // FIXED: Create proper country options with correct mapping
  const countryOptions = useMemo(() => {
    const options = countryList().getData();
    // Add some common mappings that might be missing
    const additionalCountries = [
      { value: 'AE', label: 'United Arab Emirates' },
      { value: 'NG', label: 'Nigeria' },
      { value: 'KE', label: 'Kenya' },
      { value: 'GH', label: 'Ghana' },
    ];
    
    // Merge and deduplicate
    const allCountries = [...options];
    additionalCountries.forEach(country => {
      if (!allCountries.find(c => c.value === country.value)) {
        allCountries.push(country);
      }
    });
    
    // Sort alphabetically by label
    return allCountries.sort((a, b) => a.label.localeCompare(b.label));
  }, []);

  // Check if hCaptcha is properly configured
  const hcaptchaSiteKey = import.meta.env.VITE_HCAPTCHA_SITE_KEY;
  const isHcaptchaEnabled = hcaptchaSiteKey && hcaptchaSiteKey !== 'your-site-key-here';

  const validatePassword = (password: string) => {
    const requirements = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
      special: /[!@#$%^&*]/.test(password),
    };
    setValidRequirements(requirements);
    return Object.values(requirements).every(Boolean);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    
    // FIXED: Ensure country code is properly set
    if (name === 'countryCode') {
      console.log('[Form] Country changed to:', value);
      setFormData((prev) => ({ ...prev, [name]: value }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
    
    if (name === 'password') validatePassword(value);
    
    // Clear errors when user starts typing
    if (formErrors[name as keyof FormErrors]) {
      setFormErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const handleCaptchaVerify = (token: string) => {
    setFormData((prev) => ({ ...prev, captchaToken: token }));
    setFormErrors((prev) => ({ ...prev, captcha: undefined }));
  };

  const handleCaptchaError = () => {
    setFormErrors({ captcha: 'CAPTCHA verification failed. Please try again.' });
    setFormData((prev) => ({ ...prev, captchaToken: null }));
  };

  const handleCaptchaExpire = () => {
    setFormData((prev) => ({ ...prev, captchaToken: null }));
    setFormErrors({ captcha: 'CAPTCHA expired. Please verify again.' });
  };

  const resetCaptcha = () => {
    if (captchaRef.current) {
      captchaRef.current.resetCaptcha();
    }
    setFormData((prev) => ({ ...prev, captchaToken: null }));
  };

  const validateForm = () => {
    const errors: FormErrors = {};
    
    // Email validation
    if (!formData.email) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email address';
    }
    
    // Name validation
    if (!formData.firstName.trim()) {
      errors.form = 'First name is required';
    }
    if (!formData.lastName.trim()) {
      errors.form = 'Last name is required';
    }
    
    // Password validation
    if (!validatePassword(formData.password)) {
      errors.password = 'Password does not meet requirements';
    }
    
    if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }
    
    // CAPTCHA validation (only if enabled)
    if (isHcaptchaEnabled && !formData.captchaToken) {
      errors.captcha = 'Please complete the CAPTCHA';
    }
    
    return errors;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormErrors({});
    setAuthError(null);

    // Validate form
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setFormErrors(validationErrors);
      toast.error('Please fix the form errors before submitting');
      return;
    }

    console.log('[Form] Registration attempt with data:', {
      email: formData.email,
      firstName: formData.firstName,
      lastName: formData.lastName,
      countryCode: formData.countryCode,
      passwordLength: formData.password.length,
      captchaProvided: !!formData.captchaToken
    });

    setLoading(true);
    
    try {
      // FIXED: Prepare clean signup data with proper structure
      const signUpData = {
        firstName: formData.firstName.trim(),
        lastName: formData.lastName.trim(),
        countryCode: formData.countryCode.toUpperCase(), // This should be 2-letter ISO code like 'AE' for UAE
        ...(isHcaptchaEnabled && { captchaToken: formData.captchaToken }),
      };

      console.log('[Form] Calling signUp with data:', signUpData);
      
      await signUp(formData.email.trim(), formData.password, signUpData);
      
      console.log('[Form] Registration successful');
      
      // Show success message and redirect
      toast.success('Registration successful! Please check your email to verify your account.');
      
      if (onSuccess) {
        onSuccess();
      }
      
      // Navigate to onboarding after a brief delay
      setTimeout(() => {
        navigate('/onboarding');
      }, 1000);
      
    } catch (error: any) {
      const errorMessage = error.message || 'Registration failed. Please try again.';
      setAuthError(errorMessage);
      console.error('[Form] Registration error:', error);
      toast.error(errorMessage);
      
      // Reset CAPTCHA on error
      if (isHcaptchaEnabled) {
        resetCaptcha();
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-sm p-4 bg-gray-900 text-gray-100">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-white">Create Account</h2>
        <p className="text-gray-400 text-sm mt-2">Join Seamount and start your journey</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        {/* First Name */}
        <div>
          <label htmlFor="firstName" className="block text-sm font-medium text-gray-300 mb-1">
            First Name
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              id="firstName"
              name="firstName"
              type="text"
              value={formData.firstName}
              onChange={handleInputChange}
              className="w-full pl-10 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="First name"
              required
            />
          </div>
        </div>

        {/* Last Name */}
        <div>
          <label htmlFor="lastName" className="block text-sm font-medium text-gray-300 mb-1">
            Last Name
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              id="lastName"
              name="lastName"
              type="text"
              value={formData.lastName}
              onChange={handleInputChange}
              className="w-full pl-10 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="Last name"
              required
            />
          </div>
        </div>

        {/* Email */}
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1">
            Email
          </label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleInputChange}
              className="w-full pl-10 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="Email address"
              required
            />
          </div>
          {formErrors.email && (
            <p className="text-sm text-red-400 mt-1">{formErrors.email}</p>
          )}
        </div>

        {/* Password */}
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1">
            Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              value={formData.password}
              onChange={handleInputChange}
              className="w-full pl-10 pr-10 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="Password"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300"
            >
              {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
            </button>
          </div>
          
          {/* Password Requirements */}
          {formData.password && (
            <div className="mt-2 text-xs space-y-1">
              <div className={`flex items-center ${validRequirements.length ? 'text-green-400' : 'text-gray-400'}`}>
                <CheckCircle size={12} className="mr-1" />
                At least 8 characters
              </div>
              <div className={`flex items-center ${validRequirements.uppercase ? 'text-green-400' : 'text-gray-400'}`}>
                <CheckCircle size={12} className="mr-1" />
                One uppercase letter
              </div>
              <div className={`flex items-center ${validRequirements.lowercase ? 'text-green-400' : 'text-gray-400'}`}>
                <CheckCircle size={12} className="mr-1" />
                One lowercase letter
              </div>
              <div className={`flex items-center ${validRequirements.number ? 'text-green-400' : 'text-gray-400'}`}>
                <CheckCircle size={12} className="mr-1" />
                One number
              </div>
              <div className={`flex items-center ${validRequirements.special ? 'text-green-400' : 'text-gray-400'}`}>
                <CheckCircle size={12} className="mr-1" />
                One special character (!@#$%^&*)
              </div>
            </div>
          )}
          
          {formErrors.password && (
            <p className="text-sm text-red-400 mt-1">{formErrors.password}</p>
          )}
        </div>

        {/* Confirm Password */}
        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-1">
            Confirm Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              id="confirmPassword"
              name="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              value={formData.confirmPassword}
              onChange={handleInputChange}
              className="w-full pl-10 pr-10 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="Confirm password"
              required
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300"
            >
              {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
            </button>
          </div>
          {formErrors.confirmPassword && (
            <p className="text-sm text-red-400 mt-1">{formErrors.confirmPassword}</p>
          )}
        </div>

        {/* Country Selection - FIXED */}
        <div>
          <label htmlFor="countryCode" className="block text-sm font-medium text-gray-300 mb-1">
            Country
          </label>
          <select
            id="countryCode"
            name="countryCode"
            value={formData.countryCode}
            onChange={handleInputChange}
            className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            required
          >
            {countryOptions.map((country: { value: string; label: string }) => (
              <option key={country.value} value={country.value}>
                {country.label}
              </option>
            ))}
          </select>
        </div>
        
        {/* CAPTCHA - Only if enabled */}
        {isHcaptchaEnabled && (
          <div className="flex justify-center">
            <HCaptcha
              ref={captchaRef}
              sitekey={hcaptchaSiteKey}
              onVerify={handleCaptchaVerify}
              onError={handleCaptchaError}
              onExpire={handleCaptchaExpire}
              theme="dark"
            />
            {formErrors.captcha && (
              <p className="text-sm text-red-400 mt-1">{formErrors.captcha}</p>
            )}
          </div>
        )}

        {/* Error Messages */}
        {(authError || formErrors.form) && (
          <div className="p-3 bg-red-900/30 border border-red-500/30 border border-red-500 rounded-lg">
            <p className="text-sm text-red-400">
              {authError || formErrors.form}
            </p>
          </div>
        )}

        {/* Submit Button */}
        <Button
          type="submit"
          disabled={loading || (isHcaptchaEnabled && !formData.captchaToken)}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Creating Account...
            </div>
          ) : (
            'Create Account'
          )}
        </Button>
      </form>

      {/* Login Link */}
      <div className="text-center mt-4">
        <p className="text-gray-400 text-sm">
          Already have an account?{' '}
          <button
            onClick={onLoginClick}
            className="text-blue-400 hover:text-blue-300 font-medium"
          >
            Sign In
          </button>
        </p>
      </div>
    </Card>
  );
};

export default RegisterForm;