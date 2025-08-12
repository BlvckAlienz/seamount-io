// File Location: frontend/src/components/InvestorContact.tsx
import React, { useState } from 'react';
import { apiClient } from '../config/api';
import Button from './ui/Button';
import Card from './ui/Card';

const InvestorContact: React.FC = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    checkSize: '',
    message: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await apiClient.post('/api/v1/investor-contact', formData);
      setSuccess(true);
    } catch (err: any) {
      setError('Submission failed: ' + (err.message || 'Unknown error'));
      console.error('Investor contact error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <h2 className="text-2xl font-bold text-white mb-6 text-center">Investor Contact</h2>
      {success ? (
        <p className="text-green-500 text-center">Message sent successfully!</p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
            <input
              id="name"
              name="name"
              type="text"
              value={formData.name}
              onChange={handleChange}
              className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg"
              placeholder="Your name"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg"
              placeholder="your@email.com"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Company</label>
            <input
              id="company"
              name="company"
              type="text"
              value={formData.company}
              onChange={handleChange}
              className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg"
              placeholder="Your company"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Check Size</label>
            <input
              id="checkSize"
              name="checkSize"
              type="text"
              value={formData.checkSize}
              onChange={handleChange}
              className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg"
              placeholder="e.g., $100k-$500k"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Message</label>
            <textarea
              id="message"
              name="message"
              value={formData.message}
              onChange={handleChange}
              className="w-full pl-3 py-2 bg-gray-800 border border-gray-700 rounded-lg"
              placeholder="Your message"
            />
          </div>
          {error && <p className="text-red-400">{error}</p>}
          <Button type="submit" loading={loading} className="w-full bg-gradient-to-r from-blue-600 to-purple-600">Submit</Button>
        </form>
      )}
    </Card>
  );
};

export default InvestorContact;