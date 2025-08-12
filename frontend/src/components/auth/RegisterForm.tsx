// File Location: frontend/src/components/auth/RegisterForm.tsx
import React, { useState } from 'react';
import { User, Mail, Lock, Eye, EyeOff, CheckCircle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import { useEffect, useRef } from 'react';

const RegisterForm: React.FC<RegisterFormProps> = ({ onSuccess, onLoginClick }) => {
  const [captchaToken, setCaptchaToken] = useState('');
  const captchaRef = useRef(null);

  useEffect(() => {
    // Load hCaptcha script dynamically
    const script = document.createElement('script');
    script.src = 'https://js.hcaptcha.com/1/api.js';
    script.async = true;
    document.body.appendChild(script);
    return () => document.body.removeChild(script);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormErrors({});
    console.log('Sign Up submitted:', formData);
    if (!validatePassword(formData.password)) {
      setFormErrors({ password: 'Password does not meet all requirements.' });
      console.error('Password validation failed');
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setFormErrors({ confirmPassword: 'Passwords do not match.' });
      console.error('Password mismatch');
      return;
    }
    if (!captchaToken) {
      setFormErrors({ form: 'Please complete CAPTCHA.' });
      console.error('CAPTCHA not completed');
      return;
    }
    try {
      const { success, error } = await signUp(formData.email, formData.password, formData.countryCode, { captchaToken });
      if (success) {
        console.log('Sign Up successful');
        if (onSuccess) onSuccess();
      } else {
        setFormErrors({ form: error || 'Registration failed.' });
        console.error('Sign Up error:', error);
      }
    } catch (err) {
      setFormErrors({ form: 'Unexpected error during registration.' });
      console.error('Sign Up exception:', err);
    }
  };

  return (
    <Card>
      {/* ... other form elements */}
      <div className="mt-4">
        <div className="h-captcha" data-sitekey="YOUR_HCAPTCHA_SITE_KEY" ref={captchaRef} onVerify={(token) => setCaptchaToken(token)}></div>
      </div>
      {/* ... rest of form */}
    </Card>
  );
};

const PASSWORD_REQUIREMENTS = [
  { id: 'length', text: 'At least 8 characters', regex: /^.{8,}$/ },
  { id: 'uppercase', text: 'At least one uppercase letter', regex: /[A-Z]/ },
  { id: 'lowercase', text: 'At least one lowercase letter', regex: /[a-z]/ },
  { id: 'number', text: 'At least one number', regex: /[0-9]/ },
];

interface RegisterFormProps { onSuccess?: () => void; onLoginClick?: () => void; }

const RegisterForm: React.FC<RegisterFormProps> = ({ onSuccess, onLoginClick }) => {
  const [formData, setFormData] = useState({ email: '', password: '', confirmPassword: '', firstName: '', lastName: '', countryCode: 'US' });
  const [validRequirements, setValidRequirements] = useState<Record<string, boolean>>({});
  const [showPassword, setShowPassword] = useState(false);
  const [formErrors, setFormErrors] = useState<{ [key: string]: string }>({});
  const { signUp, loading, error: authError } = useAuth();

  const validatePassword = (password: string) => {
    const newValidRequirements: Record<string, boolean> = {};
    PASSWORD_REQUIREMENTS.forEach(req => { newValidRequirements[req.id] = req.regex.test(password); });
    setValidRequirements(newValidRequirements);
    return Object.values(newValidRequirements).every(Boolean);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (name === 'password') validatePassword(value);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormErrors({});
    console.log('Sign Up submitted:', formData); // Debug log
    if (!validatePassword(formData.password)) {
      setFormErrors({ password: 'Password does not meet all requirements.' });
      console.error('Password validation failed');
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setFormErrors({ confirmPassword: 'Passwords do not match.' });
      console.error('Password mismatch');
      return;
    }
    try {
      const { success, error } = await signUp(formData.email, formData.password, formData.countryCode);
      if (success) {
        console.log('Sign Up successful');
        if (onSuccess) onSuccess();
      } else {
        setFormErrors({ form: error || 'Registration failed.' });
        console.error('Sign Up error:', error);
      }
    } catch (err) {
      setFormErrors({ form: 'Unexpected error during registration.' });
      console.error('Sign Up exception:', err);
    }
  };

  return (
    <Card>
      <h2 className="text-2xl font-bold text-white mb-6 text-center">Create Your Account</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input 
              id="email" 
              name="email" 
              autocomplete="email"
              type="email" 
              value={formData.email} 
              onChange={handleInputChange} 
              className="w-full pl-10 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg" 
              placeholder="your@email.com" 
              required
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Password</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input 
              id="password" 
              name="password" 
              autocomplete="new-password"
              type={showPassword ? 'text' : 'password'} 
              value={formData.password} 
              onChange={handleInputChange} 
              className="w-full pl-10 pr-10 py-2 bg-gray-800 border border-gray-700 rounded-lg" 
              placeholder="••••••••" 
              required
            />
            <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
              {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>
          <ul className="mt-2 text-sm text-gray-400">
            {PASSWORD_REQUIREMENTS.map(req => (
              <li key={req.id} className={validRequirements[req.id] ? 'text-green-500' : 'text-red-500'}>
                {validRequirements[req.id] ? <CheckCircle className="inline h-4 w-4 mr-1" /> : '•'} {req.text}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Confirm Password</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input 
              id="confirmPassword" 
              name="confirmPassword" 
              autocomplete="new-password"
              type={showPassword ? 'text' : 'password'} 
              value={formData.confirmPassword} 
              onChange={handleInputChange} 
              className="w-full pl-10 pr-10 py-2 bg-gray-800 border border-gray-700 rounded-lg" 
              placeholder="••••••••" 
              required
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">First Name</label>
          <input
            id="firstName"
            name="firstName"
            type="text"
            value={formData.firstName}
            onChange={handleInputChange}
            className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg"
            placeholder="First name"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Last Name</label>
          <input
            id="lastName"
            name="lastName"
            type="text"
            value={formData.lastName}
            onChange={handleInputChange}
            className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg"
            placeholder="Last name"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Country</label>
          <select
            id="countryCode"
            name="countryCode"
            value={formData.countryCode}
            onChange={handleInputChange}
            className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg"
          >
            <option value="US">United States</option>
            {/* Add more countries as needed */}
          </select>
        </div>
        {(authError || formErrors.form || formErrors.password || formErrors.confirmPassword) && (
          <div className="p-3 bg-red-900/30 border border-red-500/50 rounded-lg text-center">
            <p className="text-sm text-red-400">{authError || formErrors.form || formErrors.password || formErrors.confirmPassword}</p>
          </div>
        )}
        <div className="pt-2">
          <Button type="submit" className="w-full bg-gradient-to-r from-blue-600 to-purple-600" loading={loading}>Create Account</Button>
        </div>
        {onLoginClick && <div className="text-center pt-4"><p className="text-sm text-gray-400">Already have an account?{' '}<button type="button" onClick={onLoginClick} className="font-semibold text-blue-400 hover:underline">Sign in</button></p></div>}
      </form>
    </Card>
  );
};

export default RegisterForm;