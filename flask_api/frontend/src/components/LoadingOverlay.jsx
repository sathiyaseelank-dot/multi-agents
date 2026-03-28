import { LoadingSpinner } from './LoadingSpinner';

export function LoadingOverlay({ isLoading }) {
  if (!isLoading) return null;

  return (
    <div className="loading-overlay" data-testid="loading-overlay">
      <LoadingSpinner />
      <p>Loading analytics...</p>
    </div>
  );
}
