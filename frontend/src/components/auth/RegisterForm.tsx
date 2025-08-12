import React, { useState } from 'react';
import { User, Mail, Lock, Eye, EyeOff, CheckCircle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';

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
}

interface FormErrors {
  email?: string;
  password?: string;
  confirmPassword?: string;
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
  });
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [validRequirements, setValidRequirements] = useState<Record<string, boolean>>({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false,
  });
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const { signUp } = useAuth();
  const navigate = useNavigate();

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
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (name === 'password') validatePassword(value);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormErrors({});
    setAuthError(null);
    console.log('Sign Up submitted:', formData);

    if (!validatePassword(formData.password)) {
      setFormErrors({ password: 'Password does not meet all requirements.' });
      console.error('Password validation failed:', validRequirements);
      toast.error('Password does not meet requirements');
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setFormErrors({ confirmPassword: 'Passwords do not match.' });
      console.error('Password mismatch');
      toast.error('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await signUp(formData.email, formData.password, {
        firstName: formData.firstName,
        lastName: formData.lastName,
        countryCode: formData.countryCode,
      });
      console.log('Sign Up successful:', formData.email);
      toast.success('Registration successful! Check your email to verify.');
      if (onSuccess) onSuccess();
      navigate('/onboarding');
    } catch (error: any) {
      const errorMessage = error.message || 'Registration failed.';
      setAuthError(errorMessage);
      console.error('Sign Up error:', errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md p-6 bg-gray-900 text-gray-100">
      <form onSubmit={handleSubmit} className="space-y-4">
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
              className="w-full pl-10 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100"
              placeholder="First name"
              required
            />
          </div>
        </div>
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
              className="w-full pl-10 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100"
              placeholder="Last name"
              required
            />
          </div>
        </div>
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
              className="w-full pl-10 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100"
              placeholder="Email address"
              required
            />
          </div>
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1">
            Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleInputChange}
              className="w-full pl-10 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100"
              placeholder="Password"
              required
            />
          </div>
          <ul className="text-sm text-gray-400 mt-2">
            <li className={validRequirements.length ? 'text-green-500' : 'text-red-500'}>
              {validRequirements.length ? <CheckCircle size={16} className="inline mr-1" /> : '•'} At least 8 characters
            </li>
            <li className={validRequirements.uppercase ? 'text-green-500' : 'text-red-500'}>
              {validRequirements.uppercase ? <CheckCircle size={16} className="inline mr-1" /> : '•'} Contains uppercase
            </li>
            <li className={validRequirements.lowercase ? 'text-green-500' : 'text-red-500'}>
              {validRequirements.lowercase ? <CheckCircle size={16} className="inline mr-1" /> : '•'} Contains lowercase
            </li>
            <li className={validRequirements.number ? 'text-green-500' : 'text-red-500'}>
              {validRequirements.number ? <CheckCircle size=16} className="inline mr-1" /> : '•'} Contains number
            </li>
            <li className={validRequirements.special ? 'text-green-500' : 'text-red-500'}>
              {validRequirements.special ? <CheckCircle size={16} className="inline mr-1" /> : '•'} Contains special character
            </li>
          </ul>
        </div>
        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-1">
            Confirm Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              value={formData.confirmPassword}
              onChange={handleInputChange}
              className="w-full pl-10 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100"
              placeholder="Confirm password"
              required
            />
          </div>
        </div>
        <div>
          <label htmlFor="countryCode" className="block text-sm font-medium text-gray-300 mb-1">
            Country
          </label>
          <select
            id="countryCode"
            name="countryCode"
            value={formData.countryCode}
            onChange={handleInputChange}
            className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100"
          >
            <option value="US">United States</option>
            <option value="KE">Kenya</option>
            {/* Add more countries as needed */}
          </select>
        </div>
        {(authError || formErrors.form || formErrors.password || formErrors.confirmPassword) && (
          <div className="p-3 bg-red-900/30 border border-red-500/50 rounded-lg text-center">
            <p className="text-sm text-red-400">
              {authError || formErrors.form || formErrors.password || formErrors.confirmPassword}
            </p>
          </div>
        )}
        <div className="pt-2">
          <Button
            type="submit"
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600"
            loading={loading}
          >
            Create Account
          </Button>
        </div>
        {onLoginClick && (
          <div className="text-center pt-4">
            <p className="text-sm text-gray-400">
              Already have an account?{' '}
              <button type="button" onClick={onLoginClick} className="font-semibold text-blue-400 hover:underline">
                Sign in
              </button>
            </p>
          </div>
        )}
      </form>
    </Card>
  );
};

export default RegisterForm;