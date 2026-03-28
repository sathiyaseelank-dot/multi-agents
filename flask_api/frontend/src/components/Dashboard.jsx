import { MetricsGrid } from './MetricsGrid';
import { ChartsGrid } from './ChartsGrid';
import { TopLists } from './TopLists';
import { LoadingOverlay } from './LoadingOverlay';
import { ErrorBanner } from './ErrorBanner';
import { EmptyState } from './EmptyState';
import { useAnalyticsStore } from '../stores/analyticsStore';

function Dashboard({ isLoading, error, onRetry, onDismissError }) {
  const { overview, charts, topUsers, topConversations, hasData } = useAnalyticsStore();
  const hasAnalyticsData = hasData() || overview !== null;

  return (
    <>
      <LoadingOverlay isLoading={isLoading} />
      
      <ErrorBanner 
        error={error} 
        onRetry={onRetry} 
        onDismiss={onDismissError} 
      />

      {!isLoading && !hasAnalyticsData && (
        <EmptyState 
          title="No Analytics Data"
          message="Start using the application to generate analytics data."
          onRetry={onRetry}
        />
      )}

      {hasAnalyticsData && (
        <>
          <header className="dashboard-header">
            <h1>Analytics Dashboard</h1>
            <div className="header-actions">
              <button 
                className="btn btn-primary" 
                onClick={onRetry}
                disabled={isLoading}
              >
                {isLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>
          </header>

          <MetricsGrid metrics={overview?.metrics || []} />

          <ChartsGrid charts={charts} />

          <TopLists 
            topUsers={topUsers} 
            topConversations={topConversations} 
          />
        </>
      )}
    </>
  );
}

export default Dashboard;
