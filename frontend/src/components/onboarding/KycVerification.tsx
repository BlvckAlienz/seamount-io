import React, { useState, useRef } from 'react';
import { Shield, Upload, Camera, CheckCircle, AlertCircle, RefreshCw, FileText, FileImage } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Button from './Button';
import Card from './Card';

interface KycVerificationProps {
  onComplete?: () => void;
  onCancel?: () => void;
}

enum VerificationStep {
  INTRO = 'intro',
  DOCUMENT_TYPE = 'document_type',
  DOCUMENT_UPLOAD = 'document_upload',
  SELFIE = 'selfie',
  PROCESSING = 'processing',
  COMPLETE = 'complete',
  ERROR = 'error'
}

const KycVerification: React.FC<KycVerificationProps> = ({ onComplete, onCancel }) => {
  const [currentStep, setCurrentStep] = useState<VerificationStep>(VerificationStep.INTRO);
  const [documentType, setDocumentType] = useState<'passport' | 'id_card' | 'drivers_license'>('passport');
  const [idDocument, setIdDocument] = useState<File | null>(null);
  const [selfieImage, setSelfieImage] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const selfieInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [cameraActive, setCameraActive] = useState(false);
  
  const { user, refreshKycStatus } = useAuth();

  // Initialize KYC verification flow
  const startVerification = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const profile = await fetch('/api/kyc/start-verification', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          userId: user?.id,
          email: user?.email
        })
      });
      
      const response = await profile.json();
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to start verification');
      }
      
      setSessionId(response.session_id);
      setCurrentStep(VerificationStep.DOCUMENT_TYPE);
    } catch (error) {
      console.error('Failed to start KYC:', error);
      setError(error instanceof Error ? error.message : 'Failed to start verification process');
      setCurrentStep(VerificationStep.ERROR);
    } finally {
      setLoading(false);
    }
  };

  // Handle file selection for ID document
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        setError('File size too large. Maximum 5MB allowed.');
        return;
      }
      
      setIdDocument(file);
      setError(null);
    }
  };

  // Handle selfie capture from camera
  const startCamera = async () => {
    try {
      setCameraActive(true);
      
      if (!videoRef.current) return;
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'user' }
      });
      
      videoRef.current.srcObject = stream;
    } catch (error) {
      console.error('Error accessing camera:', error);
      setError('Could not access camera. Please check permissions and try again.');
    }
  };

  const captureSelfie = () => {
    if (!videoRef.current || !canvasRef.current) return;
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    // Set canvas size to match video dimensions
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw video frame to canvas
    const context = canvas.getContext('2d');
    if (!context) return;
    
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convert canvas to file
    canvas.toBlob(blob => {
      if (blob) {
        const file = new File([blob], 'selfie.jpg', { type: 'image/jpeg' });
        setSelfieImage(file);
        stopCamera();
      }
    }, 'image/jpeg', 0.9);
  };

  const stopCamera = () => {
    if (!videoRef.current) return;
    
    const stream = videoRef.current.srcObject as MediaStream;
    
    if (stream) {
      const tracks = stream.getTracks();
      tracks.forEach(track => track.stop());
    }
    
    videoRef.current.srcObject = null;
    setCameraActive(false);
  };

  // Upload selfie from file
  const handleSelfieUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        setError('File size too large. Maximum 5MB allowed.');
        return;
      }
      
      setSelfieImage(file);
      setError(null);
    }
  };

  // Submit documents for verification
  const submitVerification = async () => {
    try {
      if (!idDocument || !selfieImage) {
        setError('Both ID document and selfie are required');
        return;
      }
      
      setLoading(true);
      setError(null);
      setCurrentStep(VerificationStep.PROCESSING);
      
      const formData = new FormData();
      formData.append('document_type', documentType);
      formData.append('id_document', idDocument);
      formData.append('selfie', selfieImage);
      
      const response = await fetch('/api/kyc/verify-documents', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.error || 'Verification submission failed');
      }
      
      // Refresh KYC status
      await refreshKycStatus();
      
      setCurrentStep(VerificationStep.COMPLETE);
      if (onComplete) {
        setTimeout(() => {
          onComplete();
        }, 3000);
      }
      
    } catch (error) {
      console.error('Document verification failed:', error);
      setError(error instanceof Error ? error.message : 'Verification submission failed');
      setCurrentStep(VerificationStep.ERROR);
    } finally {
      setLoading(false);
    }
  };

  // Check verification status
  const checkStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/kyc/verification-status');
      const result = await response.json();
      
      if (result.success) {
        await refreshKycStatus();
        
        if (result.verified) {
          setCurrentStep(VerificationStep.COMPLETE);
          if (onComplete) {
            setTimeout(() => {
              onComplete();
            }, 1000);
          }
        } else if (result.status === 'pending') {
          setCurrentStep(VerificationStep.PROCESSING);
        }
      }
    } catch (error) {
      console.error('Failed to check verification status:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderStep = () => {
    switch (currentStep) {
      case VerificationStep.INTRO:
        return (
          <div className="text-center py-6">
            <Shield className="h-16 w-16 text-blue-500 mx-auto mb-6" />
            <h3 className="text-xl font-bold text-white mb-2">Identity Verification Required</h3>
            <p className="text-gray-300 mb-6 max-w-md mx-auto">
              To comply with regulations and protect your account, we need to verify your identity.
              This process typically takes less than 5 minutes.
            </p>
            <div className="space-y-4 mb-6">
              <div className="p-3 bg-gray-800/50 rounded-lg text-left">
                <p className="text-sm text-white font-medium">You'll need:</p>
                <ul className="mt-2 space-y-2 text-sm text-gray-300">
                  <li className="flex items-start">
                    <FileText className="h-5 w-5 text-blue-400 mr-2 mt-0.5" />
                    <span>A valid government-issued photo ID (passport, driver's license, or national ID)</span>
                  </li>
                  <li className="flex items-start">
                    <Camera className="h-5 w-5 text-blue-400 mr-2 mt-0.5" />
                    <span>A selfie (taken with your webcam or uploaded from your device)</span>
                  </li>
                </ul>
              </div>
            </div>
            <div className="flex space-x-4">
              {onCancel && (
                <Button
                  variant="secondary"
                  onClick={onCancel}
                  className="flex-1"
                >
                  Do This Later
                </Button>
              )}
              <Button
                onClick={startVerification}
                loading={loading}
                className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600"
              >
                Start Verification
              </Button>
            </div>
          </div>
        );
        
      case VerificationStep.DOCUMENT_TYPE:
        return (
          <div className="py-6">
            <h3 className="text-xl font-bold text-white mb-6 text-center">Select ID Document Type</h3>
            <div className="space-y-3 mb-8">
              <button
                type="button"
                onClick={() => setDocumentType('passport')}
                className={`w-full p-4 rounded-lg border ${
                  documentType === 'passport' 
                    ? 'border-blue-500 bg-blue-500/20' 
                    : 'border-gray-700 hover:border-gray-600'
                } flex items-center transition-colors`}
              >
                <FileText className="h-6 w-6 text-blue-400 mr-3" />
                <div className="text-left">
                  <p className="font-medium text-white">Passport</p>
                  <p className="text-xs text-gray-400">International travel document</p>
                </div>
              </button>
              
              <button
                type="button"
                onClick={() => setDocumentType('id_card')}
                className={`w-full p-4 rounded-lg border ${
                  documentType === 'id_card' 
                    ? 'border-blue-500 bg-blue-500/20' 
                    : 'border-gray-700 hover:border-gray-600'
                } flex items-center transition-colors`}
              >
                <FileText className="h-6 w-6 text-blue-400 mr-3" />
                <div className="text-left">
                  <p className="font-medium text-white">National ID Card</p>
                  <p className="text-xs text-gray-400">Government issued identity card</p>
                </div>
              </button>
              
              <button
                type="button"
                onClick={() => setDocumentType('drivers_license')}
                className={`w-full p-4 rounded-lg border ${
                  documentType === 'drivers_license' 
                    ? 'border-blue-500 bg-blue-500/20' 
                    : 'border-gray-700 hover:border-gray-600'
                } flex items-center transition-colors`}
              >
                <FileText className="h-6 w-6 text-blue-400 mr-3" />
                <div className="text-left">
                  <p className="font-medium text-white">Driver's License</p>
                  <p className="text-xs text-gray-400">Vehicle operator's permit</p>
                </div>
              </button>
            </div>
            
            <Button
              onClick={() => setCurrentStep(VerificationStep.DOCUMENT_UPLOAD)}
              className="w-full"
            >
              Continue
            </Button>
          </div>
        );
        
      case VerificationStep.DOCUMENT_UPLOAD:
        return (
          <div className="py-6">
            <h3 className="text-xl font-bold text-white mb-2 text-center">Upload ID Document</h3>
            <p className="text-gray-300 mb-6 text-center">
              Please upload a clear photo of your {documentType.replace('_', ' ')}
            </p>
            
            <div className="border-2 border-dashed border-gray-700 rounded-lg p-6 mb-6">
              {idDocument ? (
                <div className="text-center">
                  <div className="mb-4">
                    <FileImage className="h-12 w-12 mx-auto text-green-400" />
                  </div>
                  <p className="text-gray-300 mb-2">{idDocument.name}</p>
                  <p className="text-xs text-gray-400 mb-4">
                    {(idDocument.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setIdDocument(null)}
                  >
                    Remove File
                  </Button>
                </div>
              ) : (
                <div className="text-center">
                  <div className="mb-4">
                    <Upload className="h-12 w-12 mx-auto text-blue-400" />
                  </div>
                  <p className="text-gray-300 mb-2">Drag and drop your document or</p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,application/pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <Button
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Browse Files
                  </Button>
                  <p className="text-xs text-gray-400 mt-4">
                    Supported formats: JPG, PNG, PDF (max 5MB)
                  </p>
                </div>
              )}
            </div>
            
            {error && (
              <div className="p-3 bg-red-900/30 border border-red-500/50 rounded-lg mb-6">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}
            
            <div className="flex space-x-4">
              <Button
                variant="secondary"
                onClick={() => setCurrentStep(VerificationStep.DOCUMENT_TYPE)}
                className="flex-1"
              >
                Back
              </Button>
              <Button
                onClick={() => setCurrentStep(VerificationStep.SELFIE)}
                disabled={!idDocument}
                className="flex-1"
              >
                Continue
              </Button>
            </div>
          </div>
        );
        
      case VerificationStep.SELFIE:
        return (
          <div className="py-6">
            <h3 className="text-xl font-bold text-white mb-2 text-center">Take a Selfie</h3>
            <p className="text-gray-300 mb-6 text-center">
              Please take a clear photo of your face
            </p>
            
            <div className="border-2 border-dashed border-gray-700 rounded-lg p-6 mb-6">
              {selfieImage ? (
                <div className="text-center">
                  <div className="mb-4 relative w-48 h-48 mx-auto">
                    <img 
                      src={URL.createObjectURL(selfieImage)} 
                      alt="Selfie preview" 
                      className="w-full h-full object-cover rounded-lg"
                    />
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setSelfieImage(null)}
                    className="mt-2"
                  >
                    Retake Photo
                  </Button>
                </div>
              ) : cameraActive ? (
                <div className="text-center">
                  <div className="relative w-full max-w-sm mx-auto mb-4 bg-black rounded-lg overflow-hidden">
                    <video 
                      ref={videoRef} 
                      autoPlay 
                      playsInline 
                      className="w-full h-full"
                    />
                  </div>
                  <canvas ref={canvasRef} className="hidden" />
                  <div className="flex justify-center space-x-4">
                    <Button
                      variant="secondary"
                      onClick={stopCamera}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={captureSelfie}
                    >
                      Take Photo
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-center">
                  <div className="mb-4">
                    <Camera className="h-12 w-12 mx-auto text-blue-400" />
                  </div>
                  <p className="text-gray-300 mb-6">Use your camera or upload a photo</p>
                  <div className="flex justify-center space-x-4">
                    <Button
                      onClick={startCamera}
                    >
                      Use Camera
                    </Button>
                    
                    <input
                      ref={selfieInputRef}
                      type="file"
                      accept="image/jpeg,image/png"
                      onChange={handleSelfieUpload}
                      className="hidden"
                    />
                    <Button
                      variant="secondary"
                      onClick={() => selfieInputRef.current?.click()}
                    >
                      Upload Photo
                    </Button>
                  </div>
                </div>
              )}
            </div>
            
            {error && (
              <div className="p-3 bg-red-900/30 border border-red-500/50 rounded-lg mb-6">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}
            
            <div className="flex space-x-4">
              <Button
                variant="secondary"
                onClick={() => setCurrentStep(VerificationStep.DOCUMENT_UPLOAD)}
                className="flex-1"
              >
                Back
              </Button>
              <Button
                onClick={submitVerification}
                disabled={!idDocument || !selfieImage || loading}
                loading={loading}
                className="flex-1"
              >
                Submit Verification
              </Button>
            </div>
          </div>
        );
        
      case VerificationStep.PROCESSING:
        return (
          <div className="text-center py-8">
            <div className="relative w-16 h-16 mx-auto mb-6">
              <div className="absolute inset-0 rounded-full border-4 border-gray-700"></div>
              <div className="absolute inset-0 rounded-full border-4 border-t-blue-500 animate-spin"></div>
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Verification in Progress</h3>
            <p className="text-gray-300 mb-6 max-w-md mx-auto">
              We're verifying your identity. This usually takes 5-10 minutes, but may take longer during peak times.
            </p>
            <Button
              onClick={checkStatus}
              variant="secondary"
              icon={RefreshCw}
              loading={loading}
            >
              Check Status
            </Button>
          </div>
        );
        
      case VerificationStep.COMPLETE:
        return (
          <div className="text-center py-8">
            <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-6" />
            <h3 className="text-xl font-bold text-white mb-2">Verification Successful</h3>
            <p className="text-gray-300 mb-6">
              Your identity has been verified successfully. You now have full access to all features.
            </p>
            <Button
              onClick={onComplete}
              className="bg-gradient-to-r from-green-600 to-teal-600"
            >
              Continue to Platform
            </Button>
          </div>
        );
        
      case VerificationStep.ERROR:
        return (
          <div className="text-center py-8">
            <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-6" />
            <h3 className="text-xl font-bold text-white mb-2">Verification Failed</h3>
            <p className="text-red-400 mb-4">{error || 'There was a problem verifying your identity.'}</p>
            <p className="text-gray-300 mb-6">
              Please try again or contact our support team for assistance.
            </p>
            <div className="flex space-x-4">
              <Button
                variant="secondary"
                onClick={onCancel}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={() => setCurrentStep(VerificationStep.INTRO)}
                className="flex-1"
              >
                Try Again
              </Button>
            </div>
          </div>
        );
        
      default:
        return null;
    }
  };

  return (
    <Card>
      <div className="flex items-center space-x-3 mb-6">
        <Shield className="h-6 w-6 text-blue-500" />
        <h2 className="text-xl font-bold text-white">Identity Verification</h2>
      </div>
      
      {renderStep()}
    </Card>
  );
};

export default KycVerification;