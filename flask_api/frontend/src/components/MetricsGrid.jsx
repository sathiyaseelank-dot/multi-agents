import { MetricCard } from './MetricCard';

export function MetricsGrid({ metrics }) {
  if (!metrics || metrics.length === 0) {
    return null;
  }

  const metricIcons = {
    total_users: '👥',
    total_messages: '💬',
    total_conversations: '💭',
    active_users_daily: '🔥',
  };

  return (
    <section className="metrics-grid">
      {metrics.map((metric) => (
        <MetricCard
          key={metric.id}
          id={metric.id}
          label={metric.label}
          value={metric.value}
          change={metric.change}
          changeDirection={metric.change_direction}
          unit={metric.unit}
          icon={metricIcons[metric.id] || '📊'}
        />
      ))}
    </section>
  );
}
