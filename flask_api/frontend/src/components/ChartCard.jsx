import { EmptyState } from './EmptyState';

export function ChartCard({ 
  title, 
  children, 
  isWide = false, 
  showDaysFilter = false,
  daysOptions = [],
  selectedDays = 7,
  onDaysChange 
}) {
  const hasContent = children && 
    (Array.isArray(children) ? children.length > 0 : true);

  return (
    <div className={`chart-card ${isWide ? 'chart-wide' : ''}`}>
      <div className="chart-header">
        <h2>{title}</h2>
        {showDaysFilter && (
          <select 
            className="days-filter"
            value={selectedDays}
            onChange={(e) => onDaysChange?.(parseInt(e.target.value))}
          >
            {daysOptions.map((days) => (
              <option key={days} value={days}>
                {days} days
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="chart-container">
        {hasContent ? children : (
          <EmptyState message="No chart data available" />
        )}
      </div>
    </div>
  );
}
