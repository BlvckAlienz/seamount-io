import React from 'react';
import { useForm, SubmitHandler } from 'react-hook-form';
import toast from 'react-hot-toast';
import { apiClient } from '../config/api'; // Adjust path if needed
import Button from './ui/Button'; // Assuming you have these UI components
import Card from './ui/Card';   // Assuming you have these UI components

// Define the shape of our form data
interface IFormInput {
  name: string;
  email: string;
  company: string;
  checkSize: string;
  message: string;
}

const InvestorContact: React.FC = () => {
  // useForm provides superior state management (loading, errors, etc.)
  const { 
    register, 
    handleSubmit, 
    reset,
    formState: { errors, isSubmitting } 
  } = useForm<IFormInput>();

  const onSubmit: SubmitHandler<IFormInput> = async (data) => {
    const toastId = toast.loading('Submitting your request...');
    try {
      // apiClient is already configured with the correct base URL from your env vars
      await apiClient.post('/api/v1/investor-contact', data);
      
      toast.success('Thank you! Your message has been sent.', { id: toastId });
      reset(); // Clear the form on success
    } catch (err: any) {
      console.error('Investor contact submission error:', err);
      toast.error(err.response?.data?.detail || 'Submission failed. Please try again.', { id: toastId });
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
            className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="Your name"
          />
          {errors.name && <p className="text-red-400 text-sm mt-1">{errors.name.message}</p>}
        </div>

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1">Email</label>
          <input
            id="email"
            type="email"
            {...register("email", { required: "A valid email is required" })}
            className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-blue-500 focus:border-blue-500"
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
            className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="Your company"
          />
        </div>

        <div>
          <label htmlFor="checkSize" className="block text-sm font-medium text-gray-300 mb-1">Check Size</label>
          <input
            id="checkSize"
            type="text"
            {...register("checkSize")}
            className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., $100k-$500k"
          />
        </div>

        <div>
          <label htmlFor="message" className="block text-sm font-medium text-gray-300 mb-1">Message</label>
          <textarea
            id="message"
            rows={4}
            {...register("message", { required: "A message is required" })}
            className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="Your message"
          />
          {errors.message && <p className="text-red-400 text-sm mt-1">{errors.message.message}</p>}
        </div>
        
        <Button type="submit" loading={isSubmitting} className="w-full bg-gradient-to-r from-blue-600 to-purple-600">
          {isSubmitting ? 'Submitting...' : 'Submit'}
        </Button>
      </form>
    </Card>
  );
};

export default InvestorContact;