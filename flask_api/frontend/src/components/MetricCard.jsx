import { LoadingSpinner } from './LoadingSpinner';

export function MetricCard({ id, label, value, change, changeDirection, unit, icon }) {
  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num?.toLocaleString() ?? '-';
  };

  const getChangeClass = () => {
    if (!changeDirection) return '';
    return changeDirection === 'up' ? 'positive' : 'negative';
  };

  const renderChange = () => {
    if (change === undefined || change === null) return null;
    const sign = changeDirection === 'up' ? '+' : changeDirection === 'down' ? '-' : '';
    return (
      <span className={`metric-change ${getChangeClass()}`}>
        {sign}{Math.abs(change)}%
      </span>
    );
  };

  return (
    <div className="metric-card" data-testid={`metric-card-${id}`}>
      <div className="metric-icon">{icon}</div>
      <div className="metric-content">
        <h3 className="metric-label">{label}</h3>
        <p className="metric-value" data-testid={`metric-value-${id}`}>
          {value !== undefined ? formatNumber(value) : <LoadingSpinner size="small" />}
        </p>
        {renderChange()}
      </div>
    </div>
  );
}
