import React from 'react';
import { useForm, SubmitHandler } from 'react-hook-form';
import toast from 'react-hot-toast';
import { apiClient } from '../config/api';
import Button from './ui/Button';
import Card from './ui/Card';

interface IFormInput {
  name: string;
  email: string;
  company: string;
  checkSize: string;
  message: string;
}

const InvestorContact: React.FC = () => {
  const { 
    register, 
    handleSubmit, 
    reset,
    formState: { errors, isSubmitting } 
  } = useForm<IFormInput>();

  const onSubmit: SubmitHandler<IFormInput> = async (data) => {
    const toastId = toast.loading('Submitting your request...');
    try {
      console.log('Submitting investor contact form:', data);
      
      // Use the correct endpoint
      await apiClient.post('/api/v1/investor-contact', data);
      
      toast.success('Thank you! Your message has been sent.', { id: toastId });
      reset();
    } catch (err: any) {
      console.error('Investor contact submission error:', err);
      const errorMessage = err.response?.data?.detail || 
                          err.response?.data?.message || 
                          'Submission failed. Please try again.';
      toast.error(errorMessage, { id: toastId });
    }
  };

  return (
    <Card>
      <h2 className="text-2xl font-bold text-white mb-6 text-center">Investor Contact</h2>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-300 mb-1">Name</label>
          <input
            id="name"
            type="text"
            {...register("name", { required: "Name is required" })}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="Your name"
          />
          {errors.name && <p className="text-red-400 text-sm mt-1">{errors.name.message}</p>}
        </div>

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1">Email</label>
          <input
            id="email"
            type="email"
            {...register("email", { 
              required: "Email is required",
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: "Invalid email address"
              }
            })}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="your@email.com"
          />
          {errors.email && <p className="text-red-400 text-sm mt-1">{errors.email.message}</p>}
        </div>

        <div>
          <label htmlFor="company" className="block text-sm font-medium text-gray-300 mb-1">Company</label>
          <input
            id="company"
            type="text"
            {...register("company")}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="Your company"
          />
        </div>

        <div>
          <label htmlFor="checkSize" className="block text-sm font-medium text-gray-300 mb-1">Check Size</label>
          <input
            id="checkSize"
            type="text"
            {...register("checkSize")}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., $100k-$500k"
          />
        </div>

        <div>
          <label htmlFor="message" className="block text-sm font-medium text-gray-300 mb-1">Message</label>
          <textarea
            id="message"
            rows={4}
            {...register("message", { required: "A message is required" })}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="Your message"
          />
          {errors.message && <p className="text-red-400 text-sm mt-1">{errors.message.message}</p>}
        </div>
        
        <Button 
          type="submit" 
          loading={isSubmitting} 
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600"
        >
          {isSubmitting ? 'Submitting...' : 'Submit'}
        </Button>
      </form>
    </Card>
  );
};

export default InvestorContact;