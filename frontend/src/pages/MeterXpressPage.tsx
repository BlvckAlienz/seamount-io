// File: frontend/src/pages/MeterXpressPage.tsx
import React, { useState, useEffect } from 'react';
import { Zap, CheckCircle, ArrowRight, Info, DollarSign, FileText, Upload } from 'lucide-react';
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

type Step = 'questionnaire' | 'form' | 'documents' | 'payment' | 'complete';
type ApplicationType = 'new_service' | 'replacement' | 'conversion' | 'upgrade' | 'downgrade';

const MeterXpressPage = () => {
  const [currentStep, setCurrentStep] = useState<Step>('questionnaire');
  const [applicationType, setApplicationType] = useState<ApplicationType | null>(null);
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [formData, setFormData] = useState<any>(null);
  const [showActivationModal, setShowActivationModal] = useState(false);

  const steps = [
    { id: 'questionnaire', label: 'Classify', icon: FileText },
    { id: 'form', label: 'Details', icon: FileText },
    { id: 'documents', label: 'Documents', icon: Upload },
    { id: 'payment', label: 'Payment', icon: DollarSign },
  ];

  const currentStepIndex = steps.findIndex(s => s.id === currentStep);

  useEffect(() => {
    // ✅ FIX: Fetch application type if we have applicationId but no applicationType
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
    
    // ✅ ALWAYS go to documents step for all application types
    // Backend will handle which documents are required
    setCurrentStep('documents');
  };

  const handleDocumentsComplete = () => {
    setCurrentStep('payment');
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      
      <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-3">
                <Zap className="h-8 w-8 text-yellow-400" />
                <span>Meter Xpress</span>
              </h1>
              <p className="text-gray-400 mt-1">Simplified meter application & installation</p>
            </div>
            <button
              onClick={() => setShowActivationModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              <Info className="h-4 w-4" />
              <span className="hidden md:inline">Activation Guide</span>
            </button>
          </div>

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
                <DocumentUpload applicationId={applicationId} applicationType={applicationType!} onComplete={handleDocumentsComplete} />
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