// File: frontend/src/components/meter-xpress/QuestionnaireStep.tsx
import React, { useState } from 'react';
import { HelpCircle, ArrowRight } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface QuestionnaireStepProps {
  onComplete: (applicationType: string) => void;
}

export const QuestionnaireStep: React.FC<QuestionnaireStepProps> = ({ onComplete }) => {
  const [step, setStep] = useState(1);
  const [answers, setAnswers] = useState({
    has_existing_account: false,
    has_working_meter: false,
    desired_action: ''
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      
      const response = await apiClient.post('/api/v1/meter-xpress/classify', answers);
      
      if (response.data.success) {
        toast.success(response.data.message);
        
        if (response.data.next_step === 'form_details') {
          onComplete(response.data.application_type);
        } else {
          // Special case: upgrade/downgrade
          toast.error('Please contact support@seamount.io for this request', { duration: 5000 });
        }
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Classification failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <HelpCircle className="h-16 w-16 text-blue-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-white mb-2">Let's Find Your Application Type</h2>
        <p className="text-gray-400">Answer a few quick questions to get started</p>
      </div>

      {/* Question 1 */}
      {step === 1 && (
        <div className="space-y-6">
          <div className="text-center">
            <h3 className="text-xl font-semibold text-white mb-6">
              Do you have an existing EKEDC account number?
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => {
                  setAnswers({ ...answers, has_existing_account: true });
                  setStep(2);
                }}
                className="p-6 bg-gray-700/50 hover:bg-blue-600 border-2 border-gray-600 hover:border-blue-500 rounded-xl transition-all text-white font-semibold"
              >
                ✅ Yes, I have an account
              </button>
              <button
                onClick={() => {
                  setAnswers({ ...answers, has_existing_account: false });
                  handleSubmit();
                }}
                className="p-6 bg-gray-700/50 hover:bg-blue-600 border-2 border-gray-600 hover:border-blue-500 rounded-xl transition-all text-white font-semibold"
              >
                ❌ No, this is my first time
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Question 2 */}
      {step === 2 && (
        <div className="space-y-6">
          <button
            onClick={() => setStep(1)}
            className="text-blue-400 hover:text-blue-300 mb-4"
          >
            ← Back
          </button>
          <div className="text-center">
            <h3 className="text-xl font-semibold text-white mb-6">
              Do you currently have a working meter?
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => {
                  setAnswers({ ...answers, has_working_meter: true });
                  setStep(3);
                }}
                className="p-6 bg-gray-700/50 hover:bg-blue-600 border-2 border-gray-600 hover:border-blue-500 rounded-xl transition-all text-white font-semibold"
              >
                ✅ Yes, meter is working
              </button>
              <button
                onClick={() => {
                  setAnswers({ ...answers, has_working_meter: false });
                  handleSubmit();
                }}
                className="p-6 bg-gray-700/50 hover:bg-blue-600 border-2 border-gray-600 hover:border-blue-500 rounded-xl transition-all text-white font-semibold"
              >
                ❌ No, meter is faulty
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Question 3 */}
      {step === 3 && (
        <div className="space-y-6">
          <button
            onClick={() => setStep(2)}
            className="text-blue-400 hover:text-blue-300 mb-4"
          >
            ← Back
          </button>
          <div className="text-center">
            <h3 className="text-xl font-semibold text-white mb-6">
              What would you like to do?
            </h3>
            <div className="space-y-3">
              <button
                onClick={() => {
                  setAnswers({ ...answers, desired_action: 'convert' });
                  handleSubmit();
                }}
                className="w-full p-4 bg-gray-700/50 hover:bg-blue-600 border-2 border-gray-600 hover:border-blue-500 rounded-xl transition-all text-white font-semibold text-left"
              >
                🔄 Convert meter type (prepaid ↔ postpaid)
              </button>
              <button
                onClick={() => {
                  setAnswers({ ...answers, desired_action: 'upgrade' });
                  handleSubmit();
                }}
                className="w-full p-4 bg-gray-700/50 hover:bg-blue-600 border-2 border-gray-600 hover:border-blue-500 rounded-xl transition-all text-white font-semibold text-left"
              >
                ⬆️ Upgrade meter capacity
              </button>
              <button
                onClick={() => {
                  setAnswers({ ...answers, desired_action: 'downgrade' });
                  handleSubmit();
                }}
                className="w-full p-4 bg-gray-700/50 hover:bg-blue-600 border-2 border-gray-600 hover:border-blue-500 rounded-xl transition-all text-white font-semibold text-left"
              >
                ⬇️ Downgrade meter capacity
              </button>
            </div>
          </div>
        </div>
      )}

      {loading && (
        <div className="flex justify-center mt-6">
          <div className="animate-spin rounded-full h-8 w-8 border-b-4 border-blue-500"></div>
        </div>
      )}
    </div>
  );
};