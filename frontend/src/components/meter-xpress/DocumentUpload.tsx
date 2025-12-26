// File: frontend/src/components/meter-xpress/DocumentUpload.tsx
import React, { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle, Trash2, AlertCircle } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface DocumentUploadProps {
  applicationId: string;
  applicationType?: 'new_service' | 'replacement' | 'conversion';
  onComplete: () => void;
}

interface UploadedDocument {
  id: string;
  document_type: string;
  file_name: string;
  file_url: string;
  uploaded_at: string;
}

// ✅ UPDATED: Uniform document requirements with strict validation
const getRequiredDocs = (appType?: string) => {
  if (!appType) {
    return [
      { 
        type: 'id_card', 
        label: 'Means of Identification', 
        format: 'PDF Only', 
        allowedTypes: ['application/pdf'],
        maxSizeMB: 1 
      }
    ];
  }
  
  if (appType === 'new_service') {
    return [
      { 
        type: 'passport_photo', 
        label: 'Passport Photograph', 
        format: 'JPG/JPEG Only', 
        allowedTypes: ['image/jpeg', 'image/jpg'],
        maxSizeMB: 1 
      },
      { 
        type: 'id_card', 
        label: 'Means of Identification', 
        format: 'PDF Only', 
        allowedTypes: ['application/pdf'],
        maxSizeMB: 1 
      }
    ];
  } else if (appType === 'replacement') {
    return [
      { 
        type: 'id_card', 
        label: 'Means of Identification', 
        format: 'PDF Only', 
        allowedTypes: ['application/pdf'],
        maxSizeMB: 1 
      },
      { 
        type: 'meter_photo', 
        label: 'Photo of Faulty Meter', 
        format: 'JPG/JPEG Only', 
        allowedTypes: ['image/jpeg', 'image/jpg'],
        maxSizeMB: 1 
      }
    ];
  } else if (appType === 'conversion') {
    return [
      { 
        type: 'id_card', 
        label: 'Means of Identification', 
        format: 'PDF Only', 
        allowedTypes: ['application/pdf'],
        maxSizeMB: 1 
      }
    ];
  }
  return [];
};

export const DocumentUpload: React.FC<DocumentUploadProps> = ({ 
  applicationId, 
  applicationType,
  onComplete 
}) => {
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [selectedType, setSelectedType] = useState('passport_photo');
  const [loading, setLoading] = useState(true);

  const requiredDocs = getRequiredDocs(applicationType);
  
  // ✅ Set initial selectedType based on first available document type
  useEffect(() => {
    if (requiredDocs.length > 0 && !requiredDocs.find(d => d.type === selectedType)) {
      setSelectedType(requiredDocs[0].type);
    }
  }, [requiredDocs]);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/api/v1/meter-xpress/applications/${applicationId}`);
      
      if (response.data.success) {
        setDocuments(response.data.documents);
      }
    } catch (error) {
      toast.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setUploading(true);
      
      const selectedDoc = requiredDocs.find(d => d.type === selectedType);
      if (!selectedDoc) {
        toast.error('Invalid document type selected');
        return;
      }

      // ✅ Validate file size
      if (file.size > selectedDoc.maxSizeMB * 1024 * 1024) {
        toast.error(`File size exceeds ${selectedDoc.maxSizeMB}MB limit`);
        return;
      }

      // ✅ Validate file type
      if (!selectedDoc.allowedTypes.includes(file.type)) {
        const allowedFormats = selectedDoc.allowedTypes.includes('application/pdf') 
          ? 'PDF' 
          : 'JPG/JPEG';
        toast.error(`Invalid file type. Please upload ${allowedFormats} format`);
        return;
      }

      // ✅ Validate file extension
      const fileExtension = file.name.split('.').pop()?.toLowerCase();
      const allowedExtensions = selectedDoc.allowedTypes.includes('application/pdf') 
        ? ['pdf'] 
        : ['jpg', 'jpeg', 'jfif'];
      
      if (!fileExtension || !allowedExtensions.includes(fileExtension)) {
        toast.error(`Invalid file extension. Allowed: ${allowedExtensions.join(', ').toUpperCase()}`);
        return;
      }

      const formData = new FormData();
      formData.append('file', file);
      formData.append('document_type', selectedType);

      const response = await apiClient.post(
        `/api/v1/meter-xpress/applications/${applicationId}/documents/upload`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );

      if (response.data.success) {
        toast.success('Document uploaded successfully!');
        fetchDocuments();
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
      if (e.target) e.target.value = '';
    }
  };

  const handleDelete = async (documentId: string) => {
    if (!confirm('Delete this document?')) return;

    try {
      await apiClient.delete(`/api/v1/meter-xpress/applications/${applicationId}/documents/${documentId}`);
      toast.success('Document deleted');
      fetchDocuments();
    } catch (error) {
      toast.error('Failed to delete document');
    }
  };

  const isRequiredDocUploaded = (docType: string) => {
    return documents.some(d => d.document_type === docType);
  };

  const allRequiredDocsUploaded = requiredDocs.every(doc => isRequiredDocUploaded(doc.type));

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-bold text-white mb-2">Upload Required Documents</h3>
        <p className="text-gray-400">
          {applicationType === 'conversion' 
            ? 'Upload your identification document to proceed' 
            : 'All documents are required to proceed with your application'}
        </p>
      </div>

      {/* Required Documents Checklist */}
      <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-4">
        <h4 className="text-sm font-semibold text-blue-400 mb-3 uppercase">Required Documents</h4>
        <div className="space-y-2">
          {requiredDocs.map((doc) => {
            const uploaded = isRequiredDocUploaded(doc.type);
            return (
              <div
                key={doc.type}
                className={`flex items-center justify-between p-3 rounded-lg ${
                  uploaded ? 'bg-green-900/20' : 'bg-gray-800/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  {uploaded ? (
                    <CheckCircle className="h-5 w-5 text-green-400" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-yellow-400" />
                  )}
                  <div>
                    <div className={`font-medium ${uploaded ? 'text-green-400' : 'text-white'}`}>
                      {doc.label}
                    </div>
                    <div className="text-xs text-gray-400">{doc.format} • Max {doc.maxSizeMB}MB</div>
                  </div>
                </div>
                {uploaded && (
                  <span className="text-xs text-green-400 font-semibold">✓ Uploaded</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Upload Section */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
        <h4 className="text-lg font-semibold text-white mb-4">Upload Document</h4>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Document Type</label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {requiredDocs.map(doc => (
                <option key={doc.type} value={doc.type}>
                  {doc.label} {isRequiredDocUploaded(doc.type) ? '(Uploaded ✓)' : ''}
                </option>
              ))}
            </select>
          </div>

          <label className="flex flex-col items-center justify-center gap-3 px-6 py-8 bg-gray-900/50 border-2 border-dashed border-gray-600 hover:border-blue-500 rounded-lg cursor-pointer transition-all">
            <Upload className="h-12 w-12 text-gray-400" />
            <div className="text-center">
              <span className="text-white font-medium">
                {uploading ? 'Uploading...' : 'Click to choose file'}
              </span>
              <p className="text-sm text-gray-400 mt-1">
                {requiredDocs.find(d => d.type === selectedType)?.format} • Max {requiredDocs.find(d => d.type === selectedType)?.maxSizeMB}MB
              </p>
            </div>
            <input
              type="file"
              onChange={handleUpload}
              disabled={uploading}
              className="hidden"
              accept={requiredDocs.find(d => d.type === selectedType)?.allowedTypes.includes('application/pdf') 
                ? '.pdf' 
                : '.jpg,.jpeg,.jfif'
              }
            />
          </label>
          
          {/* ✅ Format Guidelines */}
          <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-3">
            <p className="text-xs text-yellow-200">
              📋 <strong>Format Guidelines:</strong><br/>
              • <strong>Identification Documents:</strong> PDF format only (Max 1MB)<br/>
              • <strong>Passport/Meter Photos:</strong> JPG/JPEG format only (Max 1MB)<br/>
              • Ensure documents are clear and readable
            </p>
          </div>
        </div>
      </div>

      {/* Uploaded Documents List */}
      {documents.length > 0 && (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
          <h4 className="text-lg font-semibold text-white mb-4">Uploaded Documents ({documents.length})</h4>
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-4 bg-gray-900/50 rounded-lg"
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <FileText className="h-5 w-5 text-blue-400 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-white font-medium truncate">{doc.file_name}</p>
                    <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
                      <span className="bg-gray-800 px-2 py-0.5 rounded">
                        {requiredDocs.find(d => d.type === doc.document_type)?.label}
                      </span>
                      <span>•</span>
                      <span>Uploaded: {new Date(doc.uploaded_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors flex-shrink-0 ml-4"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Continue Button */}
      <button
        onClick={onComplete}
        disabled={!allRequiredDocsUploaded}
        className="w-full py-4 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
      >
        {allRequiredDocsUploaded ? (
          <>
            <CheckCircle className="h-5 w-5" />
            Continue to {applicationType === 'conversion' ? 'Submit Application' : 'Payment'}
          </>
        ) : (
          <>
            <AlertCircle className="h-5 w-5" />
            Upload all required documents to continue
          </>
        )}
      </button>
    </div>
  );
};