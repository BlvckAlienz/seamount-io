// File Location: frontend/src/pages/admin/ComplianceDashboard.tsx
import React, { useState, useEffect } from 'react';
import { apiClient } from '../../config/api';
import { StatCard } from '../../components/ui/StatCard';
import { AlertsTable } from '../../components/admin/AlertsTable';
import { toast } from 'react-hot-toast';

const ComplianceDashboard = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get('/api/v1/compliance/dashboard');
        setMetrics(response.data);
      } catch (error) {
        toast.error('Failed to load compliance dashboard data.');
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
  }, []);

  if (loading) {
    return <div>Loading Compliance Dashboard...</div>;
  }
  
  if (!metrics) {
    return <div>Error loading data.</div>;
  }

  return (
    <div className="p-6 bg-gray-100 min-h-screen">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Compliance Dashboard</h1>
      
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard title="Overall Compliance Score" value={`${metrics.compliance_score}%`} />
        <StatCard title="Pending Alerts" value={metrics.alerts.pending_count} />
        <StatCard title="Verified Users" value={`${metrics.kyc.verified_count} / ${metrics.kyc.total}`} />
        <StatCard title="30-Day Volume (USD)" value={`$${Number(metrics.transactions.total_volume).toLocaleString()}`} />
      </div>

      {/* Alerts Table */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4">Alerts for Review</h2>
        <AlertsTable />
      </div>
    </div>
  );
};

export default ComplianceDashboard;