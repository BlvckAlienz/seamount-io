// File Location: frontend/src/components/admin/AlertsTable.tsx
import React, { useState, useEffect } from 'react';
import { apiClient } from '../../config/api';

export const AlertsTable = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get('/api/v1/compliance/alerts?status=pending');
        setAlerts(response.data);
      } catch (error) {
        console.error('Failed to fetch alerts:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchAlerts();
  }, []);

  if (loading) return <p>Loading alerts...</p>;
  if (alerts.length === 0) return <p>No pending alerts for review.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white">
        <thead className="bg-gray-200">
          <tr>
            <th className="py-2 px-4">User ID</th>
            <th className="py-2 px-4">Pattern Type</th>
            <th className="py-2 px-4">Severity</th>
            <th className="py-2 px-4">Date</th>
            <th className="py-2 px-4">Actions</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert: any) => (
            <tr key={alert.id} className="border-b">
              <td className="py-2 px-4">{alert.user_id}</td>
              <td className="py-2 px-4">{alert.pattern_type}</td>
              <td className="py-2 px-4">{alert.severity}</td>
              <td className="py-2 px-4">{new Date(alert.created_at).toLocaleString()}</td>
              <td className="py-2 px-4">
                <button className="text-blue-600 hover:underline">Review</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};