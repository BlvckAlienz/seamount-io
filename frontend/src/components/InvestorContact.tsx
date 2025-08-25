import React from 'react';
import { useForm, SubmitHandler } from 'react-hook-form';
import toast from 'react-hot-toast';
import { apiClient, API_ENDPOINTS } from '../config/api';

interface IFormInput {
  name: string;
  email: string;
  company: string;
  checkSize: string;
  message: string;
}

const InvestorContact: React.FC = () => {
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<IFormInput>();

  const onSubmit: SubmitHandler<IFormInput> = async (data) => {
    const toastId = toast.loading('Submitting your request...');
    try {
      // Use the properly defined endpoint
      await apiClient.post(API_ENDPOINTS.INVESTOR.CONTACT, data);
      
      toast.success('Thank you! Your message has been sent.', { id: toastId });
      reset();
    } catch (err: any) {
      console.error('Investor contact submission error:', err);
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || 'Submission failed. Please try again.';
      toast.error(errorMessage, { id: toastId });
    }
  };

  return (
    // ... (keep the existing JSX structure)
  );
};

export default InvestorContact;