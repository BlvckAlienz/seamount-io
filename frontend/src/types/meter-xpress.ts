// File: frontend/src/types/meter-xpress.ts

export interface MeterApplication {
  id: string;
  user_id: string;
  application_type: 'new_service' | 'replacement' | 'conversion' | 'upgrade' | 'downgrade';
  status: 'draft' | 'pending_payment' | 'submitted' | 'processing' | 'approved' | 'rejected' | 'completed';
  form_data: Record<string, any>;
  questionnaire_answers: Record<string, any>;
  supply_type?: string;
  phase_type: '1phase' | '3phase';
  voltage_level: string;
  map_vendor: string;
  lecan_contractor_id?: string;
  map_base_price: number;
  service_fee: number;
  total_amount: number;
  vat_amount?: number;
  payment_reference?: string;
  documents: MeterDocument[];
  district?: string;
  address?: string;
  created_at: string;
  updated_at: string;
  submitted_at?: string;
  completed_at?: string;
  metadata?: Record<string, any>;
}

export interface MeterDocument {
  id: string;
  application_id: string;
  user_id: string;
  document_type: string;
  file_name: string;
  file_url: string;
  storage_path: string;
  file_size?: number;
  mime_type?: string;
  is_validated: boolean;
  validation_notes?: string;
  uploaded_at: string;
  metadata?: Record<string, any>;
}

export interface MAPPricing {
  id: string;
  vendor_name: string;
  vendor_code?: string;
  single_phase_price: number;
  three_phase_price: number;
  vat_inclusive: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_synced_at?: string;
}

export interface LECANContractor {
  id: string;
  business_name: string;
  business_type?: string;
  cert_number?: string;
  phone_number?: string;
  email?: string;
  location?: string;
  district?: string;
  experience_years?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface QuestionnaireAnswers {
  has_existing_account: boolean;
  has_working_meter?: boolean;
  desired_action?: 'convert' | 'upgrade' | 'downgrade';
}

export interface PricingCalculation {
  base_price: number;
  service_fee: number;
  total_amount: number;
  markup_percentage: number;
}