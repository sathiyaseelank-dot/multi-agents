import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MetricsGrid } from '../../src/components/MetricsGrid';

describe('MetricsGrid', () => {
  const mockMetrics = [
    { id: 'total_users', label: 'Total Users', value: 100, change: 5, change_direction: 'up' },
    { id: 'total_messages', label: 'Total Messages', value: 500, change: 10, change_direction: 'up' },
    { id: 'total_conversations', label: 'Total Conversations', value: 50, change: 2, change_direction: 'down' },
    { id: 'active_users_daily', label: 'Active Users', value: 25 },
  ];

  it('should render all metric cards', () => {
    render(<MetricsGrid metrics={mockMetrics} />);
    expect(screen.getByText('Total Users')).toBeInTheDocument();
    expect(screen.getByText('Total Messages')).toBeInTheDocument();
    expect(screen.getByText('Total Conversations')).toBeInTheDocument();
    expect(screen.getByText('Active Users')).toBeInTheDocument();
  });

  it('should render metric values', () => {
    render(<MetricsGrid metrics={mockMetrics} />);
    expect(screen.getByTestId('metric-value-total_users')).toHaveTextContent('100');
    expect(screen.getByTestId('metric-value-total_messages')).toHaveTextContent('500');
  });

  it('should return null when metrics is empty array', () => {
    const { container } = render(<MetricsGrid metrics={[]} />);
    expect(container.innerHTML).toBe('');
  });

  it('should return null when metrics is null', () => {
    const { container } = render(<MetricsGrid metrics={null} />);
    expect(container.innerHTML).toBe('');
  });

  it('should return null when metrics is undefined', () => {
    const { container } = render(<MetricsGrid metrics={undefined} />);
    expect(container.innerHTML).toBe('');
  });

  it('should render section with metrics-grid class', () => {
    const { container } = render(<MetricsGrid metrics={mockMetrics} />);
    expect(container.querySelector('.metrics-grid')).toBeInTheDocument();
  });

  it('should render default icon for unknown metric id', () => {
    const metrics = [
      { id: 'unknown_metric', label: 'Unknown', value: 42 },
    ];
    render(<MetricsGrid metrics={metrics} />);
    expect(screen.getByText('📊')).toBeInTheDocument();
  });

  it('should render specific icons for known metric ids', () => {
    render(<MetricsGrid metrics={mockMetrics} />);
    expect(screen.getByText('👥')).toBeInTheDocument();
    expect(screen.getByText('💬')).toBeInTheDocument();
    expect(screen.getByText('💭')).toBeInTheDocument();
    expect(screen.getByText('🔥')).toBeInTheDocument();
  });

  it('should render positive change indicator', () => {
    render(<MetricsGrid metrics={mockMetrics} />);
    expect(screen.getByText('+5%')).toBeInTheDocument();
    expect(screen.getByText('+10%')).toBeInTheDocument();
  });

  it('should render negative change indicator', () => {
    render(<MetricsGrid metrics={mockMetrics} />);
    expect(screen.getByText('-2%')).toBeInTheDocument();
  });

  it('should format large numbers with K suffix', () => {
    const metrics = [
      { id: 'total_users', label: 'Total Users', value: 1500 },
    ];
    render(<MetricsGrid metrics={metrics} />);
    expect(screen.getByTestId('metric-value-total_users')).toHaveTextContent('1.5K');
  });

  it('should format millions with M suffix', () => {
    const metrics = [
      { id: 'total_messages', label: 'Total Messages', value: 2500000 },
    ];
    render(<MetricsGrid metrics={metrics} />);
    expect(screen.getByTestId('metric-value-total_messages')).toHaveTextContent('2.5M');
  });
});
