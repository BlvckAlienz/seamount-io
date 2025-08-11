// File Location: frontend/src/pages/admin/ComplianceDashboard.tsx
// Description: The definitive, corrected, and production-ready compliance dashboard page.

import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';

// --- CORRECTED IMPORT PATHS ---
// Using robust, absolute paths with the '@' alias from vite.config.ts
import { apiClient } from '@/config/api';
import { AlertsTable } from '@/components/admin/AlertsTable';
import { CardSkeleton } from '@/components/ui/LoadingSkeleton';

// --- StatCard Component Definition ---
// This component was missing. It's defined here for completeness.
// In a real app, this would live in its own file at '@/components/ui/StatCard.tsx'
const StatCard: React.FC<{ title: string; value: string | number }> = ({ title, value }) => (
  <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700/50">
    <h4 className="text-sm font-medium text-gray-400 mb-2">{title}</h4>
    <p className="text-3xl font-bold text-white">{value}</p>
  </div>
);

const ComplianceDashboard = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/compliance/dashboard`);
        setMetrics(response.data);
      } catch (error) {
        toast.error('Failed to load compliance dashboard data.');
        console.error("Compliance Dashboard Error:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold text-white mb-6">Compliance Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <CardSkeleton height={100} />
            <CardSkeleton height={100} />
            <CardSkeleton height={100} />
            <CardSkeleton height={100} />
        </div>
      </div>
    );
  }
  
  if (!metrics) {
    return <div className="p-6 text-red-400">Error loading compliance data. Please try again later.</div>;
  }

  return (
    <div className="p-6 text-white">
      <h1 className="text-3xl font-bold text-white mb-6">Compliance Dashboard</h1>
      
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard title="Overall Compliance Score" value={`${metrics.compliance_score}%`} />
        <StatCard title="Pending Alerts" value={metrics.alerts.pending_count} />
        <StatCard title="Verified Users" value={`${metrics.kyc.verified_count} / ${metrics.kyc.total}`} />
        <StatCard title="30-Day Volume (USD)" value={`$${Number(metrics.transactions.total_volume).toLocaleString()}`} />
      </div>

      {/* Alerts Table */}
      <div className="bg-gray-800/30 p-6 rounded-lg shadow-md border border-gray-700/50">
        <h2 className="text-xl font-semibold mb-4">Alerts for Review</h2>
        <AlertsTable />
      </div>
    </div>
  );
};

export default ComplianceDashboard;