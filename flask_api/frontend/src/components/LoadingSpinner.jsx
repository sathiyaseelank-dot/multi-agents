export function LoadingSpinner({ size = 'medium' }) {
  const sizeClass = size === 'small' ? 'spinner-small' : '';
  
  return (
    <div className={`spinner-container ${sizeClass}`} data-testid="loading-spinner">
      <div className="spinner"></div>
    </div>
  );
}
