// File Location: frontend/src/components/auth/RegisterForm.tsx
import React, { useState, useEffect } from 'react';
import { User, Mail, Lock, Eye, EyeOff, CheckCircle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';

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
    if (!validatePassword(formData.password)) {
      setFormErrors({ password: "Password does not meet all requirements." });
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setFormErrors({ confirmPassword: "Passwords do not match." });
      return;
    }
    const { success, error } = await signUp(formData.email, formData.password, formData.countryCode);
    if (success) {
      if (onSuccess) onSuccess();
    } else if (error) {
      setFormErrors({ form: error });
    }
  };

  return (
    <Card>
      <h2 className="text-2xl font-bold text-white mb-6 text-center">Create Your Account</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* All your form JSX from the previous file goes here */}
        <div className="pt-2">
            <Button type="submit" className="w-full bg-gradient-to-r from-blue-600 to-purple-600" loading={loading}>Create Account</Button>
        </div>
        {onLoginClick && <div className="text-center pt-4"><p className="text-sm text-gray-400">Already have an account?{' '}<button type="button" onClick={onLoginClick} className="font-semibold text-blue-400 hover:underline">Sign in</button></p></div>}
      </form>
    </Card>
  );
};
export default RegisterForm;