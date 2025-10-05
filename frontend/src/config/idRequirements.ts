export interface IDRequirement {
  field: string;
  label: string;
  type: 'text' | 'date' | 'select' | 'tel';
  placeholder?: string;
  validation?: (value: string) => boolean;
  errorMessage?: string;
  options?: { value: string; label: string }[];
}

export interface CountryIDConfig {
  countryCode: string;
  countryName: string;
  supportedIDTypes: { value: string; label: string }[];
  requiredFields: Record<string, IDRequirement[]>;
}

export const ID_REQUIREMENTS: Record<string, CountryIDConfig> = {
  NG: {
    countryCode: 'NG',
    countryName: 'Nigeria',
    supportedIDTypes: [
      { value: 'BVN', label: 'Bank Verification Number (BVN)' },
      { value: 'NIN', label: 'National Identity Number (NIN)' },
      { value: 'PASSPORT', label: 'International Passport' }
    ],
    requiredFields: {
      BVN: [
        {
          field: 'bvn',
          label: 'Bank Verification Number (BVN)',
          type: 'text',
          placeholder: 'Enter 11-digit BVN',
          validation: (val) => /^\d{11}$/.test(val),
          errorMessage: 'BVN must be exactly 11 digits'
        },
        {
          field: 'date_of_birth',
          label: 'Date of Birth',
          type: 'date',
          validation: (val) => {
            const age = new Date().getFullYear() - new Date(val).getFullYear();
            return age >= 18;
          },
          errorMessage: 'You must be at least 18 years old'
        },
        {
          field: 'gender',
          label: 'Gender',
          type: 'select',
          options: [
            { value: 'M', label: 'Male' },
            { value: 'F', label: 'Female' },
            { value: 'Other', label: 'Other' }
          ]
        }
      ],
      NIN: [
        {
          field: 'nin',
          label: 'National Identity Number (NIN)',
          type: 'text',
          placeholder: 'Enter 11-digit NIN',
          validation: (val) => /^\d{11}$/.test(val),
          errorMessage: 'NIN must be exactly 11 digits'
        },
        {
          field: 'date_of_birth',
          label: 'Date of Birth',
          type: 'date'
        }
      ]
    }
  },
  KE: {
    countryCode: 'KE',
    countryName: 'Kenya',
    supportedIDTypes: [
      { value: 'NATIONAL_ID', label: 'National ID' },
      { value: 'PASSPORT', label: 'Passport' }
    ],
    requiredFields: {
      NATIONAL_ID: [
        {
          field: 'id_number',
          label: 'National ID Number',
          type: 'text',
          placeholder: 'Enter ID number',
          validation: (val) => val.length >= 7,
          errorMessage: 'Invalid ID number'
        },
        {
          field: 'date_of_birth',
          label: 'Date of Birth',
          type: 'date'
        }
      ]
    }
  },
  US: {
    countryCode: 'US',
    countryName: 'United States',
    supportedIDTypes: [
      { value: 'PASSPORT', label: 'Passport' },
      { value: 'DRIVERS_LICENSE', label: 'Driver\'s License' },
      { value: 'STATE_ID', label: 'State ID' }
    ],
    requiredFields: {
      PASSPORT: [
        {
          field: 'passport_number',
          label: 'Passport Number',
          type: 'text',
          placeholder: 'Enter passport number'
        },
        {
          field: 'date_of_birth',
          label: 'Date of Birth',
          type: 'date'
        }
      ],
      DRIVERS_LICENSE: [
        {
          field: 'license_number',
          label: 'License Number',
          type: 'text',
          placeholder: 'Enter license number'
        },
        {
          field: 'state',
          label: 'State',
          type: 'text',
          placeholder: 'State of issuance'
        },
        {
          field: 'date_of_birth',
          label: 'Date of Birth',
          type: 'date'
        }
      ]
    }
  }
};

export const getCountryConfig = (countryCode: string): CountryIDConfig | null => {
  return ID_REQUIREMENTS[countryCode] || null;
};

export const getDefaultCountry = (): CountryIDConfig => {
  return ID_REQUIREMENTS.US;
};