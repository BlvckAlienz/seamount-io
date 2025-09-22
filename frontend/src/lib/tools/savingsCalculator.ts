import { apiClient } from '../../config/api';

export const calculateSavings = async (amount: number, fromCountry: string, toCountry: string) => {
  try {
    const response = await apiClient.get('/tools/calculate-savings', {
      params: { amount, from_country: fromCountry, to_country: toCountry }
    });
    return response.data;
  } catch (error) {
    console.error('Failed to calculate savings:', error);
    throw new Error('Could not calculate savings');
  }
};

export const generateShareImage = async (data: {
  amount: number;
  savings: number;
  fromCountry: string;
  toCountry: string;
}) => {
  try {
    const response = await apiClient.post('/tools/generate-share-image', data);
    return response.data.image_url;
  } catch (error) {
    console.error('Failed to generate share image:', error);
    return null;
  }
};

// New function to get supported countries
export const getSupportedCountries = async () => {
  try {
    const response = await apiClient.get('/tools/supported-countries');
    return response.data;
  } catch (error) {
    console.error('Failed to get supported countries:', error);
    return [];
  }
};