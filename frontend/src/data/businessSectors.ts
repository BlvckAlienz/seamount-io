// ============================================================================
// BUSINESS SECTORS - Comprehensive Industry Classification
// ============================================================================

export const BUSINESS_SECTORS = [
  // Primary Industries
  { value: 'agriculture', label: 'Agriculture & Farming' },
  { value: 'mining', label: 'Mining & Extraction' },
  { value: 'oil_gas', label: 'Oil & Gas' },
  { value: 'renewable_energy', label: 'Renewable Energy' },
  
  // Manufacturing
  { value: 'manufacturing', label: 'Manufacturing (General)' },
  { value: 'construction', label: 'Construction & Infrastructure' },
  { value: 'automotive', label: 'Automotive' },
  { value: 'aerospace', label: 'Aerospace & Defense' },
  
  // Technology
  { value: 'fintech', label: 'Financial Technology (FinTech)' },
  { value: 'software', label: 'Software & SaaS' },
  { value: 'blockchain', label: 'Blockchain & Web3' },
  { value: 'ai_ml', label: 'AI & Machine Learning' },
  { value: 'telecom', label: 'Telecommunications' },
  
  // Financial Services
  { value: 'banking', label: 'Banking & Financial Services' },
  { value: 'insurance', label: 'Insurance' },
  { value: 'investment', label: 'Investment & Asset Management' },
  { value: 'payments', label: 'Payments & Remittance' },
  
  // Real Estate & Property
  { value: 'real_estate', label: 'Real Estate Development' },
  { value: 'property_management', label: 'Property Management' },
  { value: 'hospitality', label: 'Hospitality & Hotels' },
  
  // Healthcare
  { value: 'healthcare', label: 'Healthcare Services' },
  { value: 'pharmaceuticals', label: 'Pharmaceuticals' },
  { value: 'medical_devices', label: 'Medical Devices & Equipment' },
  { value: 'biotech', label: 'Biotechnology' },
  
  // Consumer Goods & Services
  { value: 'retail', label: 'Retail & E-commerce' },
  { value: 'fmcg', label: 'FMCG (Consumer Goods)' },
  { value: 'fashion', label: 'Fashion & Apparel' },
  { value: 'food_beverage', label: 'Food & Beverage' },
  
  // Media & Entertainment
  { value: 'media', label: 'Media & Publishing' },
  { value: 'entertainment', label: 'Entertainment & Gaming' },
  { value: 'sports', label: 'Sports & Recreation' },
  
  // Transportation & Logistics
  { value: 'logistics', label: 'Logistics & Supply Chain' },
  { value: 'transportation', label: 'Transportation' },
  { value: 'aviation', label: 'Aviation' },
  { value: 'maritime', label: 'Maritime & Shipping' },
  
  // Professional Services
  { value: 'consulting', label: 'Consulting' },
  { value: 'legal', label: 'Legal Services' },
  { value: 'accounting', label: 'Accounting & Auditing' },
  
  // Education & Training
  { value: 'education', label: 'Education & EdTech' },
  { value: 'training', label: 'Training & Development' },
  
  // Other
  { value: 'ngo_nonprofit', label: 'NGO & Non-Profit' },
  { value: 'government', label: 'Government & Public Sector' },
  { value: 'other', label: 'Other' },
] as const;

export type BusinessSector = typeof BUSINESS_SECTORS[number]['value'];