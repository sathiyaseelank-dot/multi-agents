export function ErrorBanner({ error, onRetry, onDismiss }) {
  if (!error) return null;

  const errorMessage = typeof error === 'string' ? error : error?.message || 'An unexpected error occurred';

  return (
    <div className="error-message" role="alert" data-testid="error-banner">
      <div className="error-content">
        <span className="error-text">
          {errorMessage}
        </span>
        <div className="error-actions">
          {onRetry && (
            <button className="btn btn-retry" onClick={onRetry}>
              Retry
            </button>
          )}
          {onDismiss && (
            <button className="btn btn-dismiss" onClick={onDismiss}>
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
