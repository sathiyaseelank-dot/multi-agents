import { useEffect, useState } from 'react';
import Dashboard from '../components/Dashboard';
import { useAnalyticsStore } from '../stores/analyticsStore';

function DashboardPage() {
  const [localLoading, setLocalLoading] = useState(true);
  const { fetchAllAnalytics, error, clearError, isLoading } = useAnalyticsStore();

  const handleRetry = async () => {
    setLocalLoading(true);
    try {
      await fetchAllAnalytics();
    } finally {
      setLocalLoading(false);
    }
  };

  const handleDismissError = () => {
    clearError();
  };

  useEffect(() => {
    handleRetry();
  }, []);

  const loading = localLoading || isLoading.overview || isLoading.charts;

  return (
    <Dashboard
      isLoading={loading}
      error={error}
      onRetry={handleRetry}
      onDismissError={handleDismissError}
    />
  );
}

export default DashboardPage;
