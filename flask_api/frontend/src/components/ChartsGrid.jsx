import { LineChart } from './LineChart';
import { BarChart } from './BarChart';
import { DoughnutChart } from './DoughnutChart';
import { ChartCard } from './ChartCard';
import { useAnalyticsStore } from '../stores/analyticsStore';

const chartConfig = [
  { 
    key: 'messagesPerDay', 
    title: 'Messages Over Time', 
    type: 'line',
    dataKey: 'messages_per_day',
  },
  { 
    key: 'usersPerDay', 
    title: 'Users Over Time', 
    type: 'line',
    dataKey: 'users_per_day',
  },
  { 
    key: 'conversationsPerDay', 
    title: 'Conversations Over Time', 
    type: 'line',
    dataKey: 'conversations_per_day',
  },
  { 
    key: 'messagesByHour', 
    title: 'Messages by Hour', 
    type: 'bar',
    dataKey: 'messages_by_hour',
  },
  { 
    key: 'messageTypeDistribution', 
    title: 'Message Types', 
    type: 'doughnut',
    dataKey: 'message_type_distribution',
  },
];

export function ChartsGrid({ charts }) {
  const { updateChartDays, filters, isLoading } = useAnalyticsStore();
  const daysOptions = [7, 14, 30];

  const handleDaysChange = async (chartType, days) => {
    await updateChartDays(chartType, days);
  };

  const renderChart = (config, data) => {
    const chartProps = {
      data,
      isLoading: isLoading.charts,
    };

    switch (config.type) {
      case 'line':
        return <LineChart {...chartProps} />;
      case 'bar':
        return <BarChart {...chartProps} />;
      case 'doughnut':
        return <DoughnutChart {...chartProps} />;
      default:
        return null;
    }
  };

  return (
    <section className="charts-grid">
      {chartConfig.map((config) => (
        <ChartCard
          key={config.key}
          title={config.title}
          isWide={config.type === 'doughnut'}
          showDaysFilter={config.type !== 'doughnut'}
          daysOptions={daysOptions}
          selectedDays={filters.chartDays[config.dataKey]}
          onDaysChange={(days) => handleDaysChange(config.dataKey, days)}
        >
          {renderChart(config, charts[config.key] || [])}
        </ChartCard>
      ))}
    </section>
  );
}
