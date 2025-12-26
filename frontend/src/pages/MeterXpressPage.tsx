// File: frontend/src/pages/MeterXpressPage.tsx
import React, { useState, useEffect } from 'react';
import { Zap, CheckCircle, ArrowRight, Info, DollarSign, FileText, Upload, X, Home, AlertCircle } from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';
import { QuestionnaireStep } from '@/components/meter-xpress/QuestionnaireStep';
import { NewServiceForm } from '@/components/meter-xpress/NewServiceForm';
import { MAPPricingCard } from '@/components/meter-xpress/MAPPricingCard';
import { DocumentUpload } from '@/components/meter-xpress/DocumentUpload';
import { ActivationGuidelinesModal } from '@/components/meter-xpress/ActivationGuidelinesModal';
import { PaymentStep } from '@/components/meter-xpress/PaymentStep';
import { ReplacementForm } from '@/components/meter-xpress/ReplacementForm';
import { ConversionForm } from '@/components/meter-xpress/ConversionForm';
import { useNavigate } from 'react-router-dom';

type Step = 'questionnaire' | 'form' | 'documents' | 'payment' | 'complete';
type ApplicationType = 'new_service' | 'replacement' | 'conversion' | 'upgrade' | 'downgrade';

const MeterXpressPage = () => {
  const [currentStep, setCurrentStep] = useState<Step>('questionnaire');
  const [applicationType, setApplicationType] = useState<ApplicationType | null>(null);
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [formData, setFormData] = useState<any>(null);
  const [showActivationModal, setShowActivationModal] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const navigate = useNavigate();

  const steps = [
    { id: 'questionnaire', label: 'Classify', icon: FileText },
    { id: 'form', label: 'Details', icon: FileText },
    { id: 'documents', label: 'Documents', icon: Upload },
    { id: 'payment', label: 'Payment', icon: DollarSign },
  ];

  const currentStepIndex = steps.findIndex(s => s.id === currentStep);

  useEffect(() => {
    if (applicationId && !applicationType && currentStep === 'documents') {
      const fetchApplicationType = async () => {
        try {
          const response = await apiClient.get(`/api/v1/meter-xpress/applications/${applicationId}`);
          if (response.data.success && response.data.application) {
            setApplicationType(response.data.application.application_type);
          }
        } catch (error) {
          console.error('Failed to fetch application type:', error);
        }
      };
      fetchApplicationType();
    }
  }, [applicationId, applicationType, currentStep]);

  const handleQuestionnaireComplete = (type: ApplicationType) => {
    setApplicationType(type);
    
    if (type === 'upgrade' || type === 'downgrade') {
      toast.error('Please contact support@seamount.io for this request');
      return;
    }
    
    setCurrentStep('form');
  };

  const handleFormComplete = async (appId: string, data: any) => {
    setApplicationId(appId);
    setFormData(data);
    
    setCurrentStep('documents');
  };

  const handleDocumentsComplete = () => {
    setCurrentStep('payment');
  };

  const handleResetFlow = () => {
    if (currentStep !== 'questionnaire' && applicationId) {
      toast.loading('Cleaning up...', { id: 'reset' });
      
      // Optional: Call backend to clean up draft application
      apiClient.delete(`/api/v1/meter-xpress/applications/${applicationId}/cancel`)
        .catch(() => { /* Silent fail for draft cleanup */ })
        .finally(() => {
          resetState();
          toast.dismiss('reset');
          toast.success('Flow reset successfully');
        });
    } else {
      resetState();
    }
  };

  const resetState = () => {
    setCurrentStep('questionnaire');
    setApplicationType(null);
    setApplicationId(null);
    setFormData(null);
    setShowResetConfirm(false);
  };

  const handleExitToDashboard = () => {
    if (currentStep !== 'questionnaire') {
      if (confirm('Are you sure you want to exit? Your current progress will be lost.')) {
        navigate('/dashboard');
      }
    } else {
      navigate('/dashboard');
    }
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      
      <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <button
                  onClick={handleExitToDashboard}
                  className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
                  title="Exit to Dashboard"
                >
                  <Home className="h-5 w-5 text-gray-300" />
                </button>
                <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-3">
                  <Zap className="h-8 w-8 text-yellow-400" />
                  <span>Meter Xpress</span>
                </h1>
              </div>
              <p className="text-gray-400">Simplified meter application & installation</p>
            </div>
            
            <div className="flex items-center gap-3">
              {currentStep !== 'questionnaire' && (
                <button
                  onClick={() => setShowResetConfirm(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                >
                  <X className="h-4 w-4" />
                  <span className="hidden md:inline">Quit & Start Over</span>
                </button>
              )}
              <button
                onClick={() => setShowActivationModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <Info className="h-4 w-4" />
                <span className="hidden md:inline">Activation Guide</span>
              </button>
            </div>
          </div>

          {/* Reset Confirmation Modal */}
          {showResetConfirm && (
            <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
              <div className="bg-gray-800 rounded-xl p-6 max-w-md w-full border border-red-500/30">
                <div className="flex items-center gap-3 mb-4">
                  <AlertCircle className="h-8 w-8 text-red-400" />
                  <h3 className="text-xl font-bold text-white">Quit Application?</h3>
                </div>
                <p className="text-gray-300 mb-6">
                  Are you sure you want to quit and start over? All your current progress will be lost.
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => setShowResetConfirm(false)}
                    className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleResetFlow}
                    className="flex-1 py-3 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg transition-colors"
                  >
                    Yes, Quit Now
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Progress Stepper */}
          <div className="mb-8">
            <div className="flex items-center justify-between">
              {steps.map((step, index) => {
                const Icon = step.icon;
                const isActive = index === currentStepIndex;
                const isCompleted = index < currentStepIndex;
                
                return (
                  <React.Fragment key={step.id}>
                    <div className="flex flex-col items-center">
                      <div className={`
                        w-12 h-12 rounded-full flex items-center justify-center mb-2 transition-all
                        ${isCompleted ? 'bg-green-600' : isActive ? 'bg-blue-600' : 'bg-gray-700'}
                      `}>
                        {isCompleted ? (
                          <CheckCircle className="h-6 w-6 text-white" />
                        ) : (
                          <Icon className="h-6 w-6 text-white" />
                        )}
                      </div>
                      <span className={`text-sm font-medium ${isActive ? 'text-white' : 'text-gray-400'}`}>
                        {step.label}
                      </span>
                    </div>
                    
                    {index < steps.length - 1 && (
                      <div className={`flex-1 h-1 mx-4 rounded ${
                        index < currentStepIndex ? 'bg-green-600' : 'bg-gray-700'
                      }`} />
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>

          {/* Step Content */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-2xl p-6">
            {currentStep === 'questionnaire' && (
              <QuestionnaireStep onComplete={handleQuestionnaireComplete} />
            )}
            
            {currentStep === 'form' && applicationType === 'new_service' && (
              <NewServiceForm onComplete={handleFormComplete} />
            )}
            
            {currentStep === 'form' && applicationType === 'replacement' && (
              <ReplacementForm onComplete={handleFormComplete} />
            )}
            
            {currentStep === 'form' && applicationType === 'conversion' && (
              <ConversionForm onComplete={handleFormComplete} />
            )}
            
            {currentStep === 'documents' && applicationId && (
              <DocumentUpload 
                applicationId={applicationId} 
                applicationType={applicationType!} 
                onComplete={handleDocumentsComplete} 
              />
            )}
            
            {currentStep === 'payment' && applicationId && (
              <PaymentStep applicationId={applicationId} />
            )}
          </div>
        </div>
      </div>

      {/* Activation Guidelines Modal */}
      <ActivationGuidelinesModal
        open={showActivationModal}
        onOpenChange={setShowActivationModal}
      />
    </div>
  );
};

export default MeterXpressPage;