import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';

// --- DEFINITIVE, CORRECTED IMPORT ---
// Using a robust, absolute path with the '@' alias from vite.config.ts
import { apiClient } from '@/config/api';
import { Skeleton } from '@/components/ui/LoadingSkeleton.tsx';

// Define a clear type for the alert data for better code quality and safety
interface Alert {
  id: string;
  user_id: string;
  pattern_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
}

export const AlertsTable: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAlerts = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.get<Alert[]>(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/compliance/alerts?status=pending`);
        setAlerts(response.data);
      } catch (err) {
        const errorMessage = 'Failed to fetch compliance alerts.';
        setError(errorMessage);
        toast.error(errorMessage);
        console.error('Failed to fetch alerts:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAlerts();
  }, []);

  if (loading) {
    // Provide a better loading state experience
    return (
      <div className="space-y-2">
        <Skeleton height="40px" className="w-full" />
        <Skeleton height="40px" className="w-full" />
        <Skeleton height="40px" className="w-full" />
      </div>
    );
  }

  if (error) {
    // Provide a clear error message in the UI
    return <p className="text-center py-8 text-red-400">{error}</p>;
  }
  
  if (alerts.length === 0) {
    return <p className="text-center py-8 text-gray-400">No pending alerts for review.</p>;
  }

  const getSeverityClass = (severity: Alert['severity']) => {
    switch (severity) {
      case 'critical': return 'text-red-400 bg-red-900/50';
      case 'high': return 'text-orange-400 bg-orange-900/50';
      case 'medium': return 'text-yellow-400 bg-yellow-900/50';
      case 'low':
      default:
        return 'text-gray-300 bg-gray-700/50';
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-white">
        <thead className="bg-gray-700/50">
          <tr>
            <th className="text-left py-3 px-4 text-sm font-semibold">User ID</th>
            <th className="text-left py-3 px-4 text-sm font-semibold">Pattern Type</th>
            <th className="text-left py-3 px-4 text-sm font-semibold">Severity</th>
            <th className="text-left py-3 px-4 text-sm font-semibold">Date</th>
            <th className="text-left py-3 px-4 text-sm font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {alerts.map((alert) => (
            <tr key={alert.id} className="hover:bg-gray-800/50">
              <td className="py-3 px-4 text-sm font-mono">{alert.user_id}</td>
              <td className="py-3 px-4 text-sm">{alert.pattern_type}</td>
              <td className="py-3 px-4 text-sm">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityClass(alert.severity)}`}>
                  {alert.severity.charAt(0).toUpperCase() + alert.severity.slice(1)}
                </span>
              </td>
              <td className="py-3 px-4 text-sm">{new Date(alert.created_at).toLocaleString()}</td>
              <td className="py-3 px-4">
                <button className="font-medium text-blue-400 hover:text-blue-300">Review</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};