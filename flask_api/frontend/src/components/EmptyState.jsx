export function EmptyState({ 
  title = 'No Data', 
  message = 'No data available to display',
  onRetry 
}) {
  return (
    <div className="empty-state" data-testid="empty-state">
      <div className="empty-state-icon">📊</div>
      {title && <h3 className="empty-state-title">{title}</h3>}
      <p className="empty-state-message">{message}</p>
      {onRetry && (
        <button className="btn btn-primary" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
