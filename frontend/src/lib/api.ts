// frontend/src/lib/api.ts
// ── BRIDGE: delegates ALL calls to the resilient pool in config/api.ts ──
// This file exists for backward compatibility with imports using '@/lib/api'
// DO NOT add direct axios calls here — use config/api.ts pool exclusively

import { apiClient } from '../config/api';

// Match the original ApiClient method signatures exactly so no callers break
class ApiClientBridge {
  async get<T>(url: string, params?: any): Promise<T> {
    const res = await apiClient.get<T>(url, params ? { params } : undefined);
    return res.data;
  }

  async post<T>(url: string, data?: any): Promise<T> {
    const res = await apiClient.post<T>(url, data);
    return res.data;
  }

  async put<T>(url: string, data?: any): Promise<T> {
    const res = await apiClient.put<T>(url, data);
    return res.data;
  }

  async patch<T>(url: string, data?: any): Promise<T> {
    const res = await apiClient.patch<T>(url, data);
    return res.data;
  }

  async delete<T>(url: string): Promise<T> {
    const res = await apiClient.delete<T>(url);
    return res.data;
  }
}

export const api = new ApiClientBridge();
export default api;