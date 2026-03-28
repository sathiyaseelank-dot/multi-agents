import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MetricCard } from '../../src/components/MetricCard';

describe('MetricCard', () => {
  it('should render metric label', () => {
    render(<MetricCard id="test-metric" label="Test Metric" value={100} />);
    expect(screen.getByText('Test Metric')).toBeInTheDocument();
  });

  it('should render metric value', () => {
    render(<MetricCard id="test-metric" label="Test Metric" value={100} />);
    expect(screen.getByTestId('metric-value-test-metric')).toHaveTextContent('100');
  });

  it('should format large numbers with K suffix', () => {
    render(<MetricCard id="test-metric" label="Test Metric" value={1500} />);
    expect(screen.getByTestId('metric-value-test-metric')).toHaveTextContent('1.5K');
  });

  it('should format large numbers with M suffix', () => {
    render(<MetricCard id="test-metric" label="Test Metric" value={1500000} />);
    expect(screen.getByTestId('metric-value-test-metric')).toHaveTextContent('1.5M');
  });

  it('should render positive change with green color', () => {
    render(
      <MetricCard
        id="test-metric"
        label="Test Metric"
        value={100}
        change={10}
        changeDirection="up"
      />
    );
    const changeEl = screen.getByText('+10%');
    expect(changeEl).toHaveClass('positive');
  });

  it('should render negative change with red color', () => {
    render(
      <MetricCard
        id="test-metric"
        label="Test Metric"
        value={100}
        change={5}
        changeDirection="down"
      />
    );
    const changeEl = screen.getByText('-5%');
    expect(changeEl).toHaveClass('negative');
  });

  it('should not render change when null', () => {
    render(
      <MetricCard
        id="test-metric"
        label="Test Metric"
        value={100}
        change={null}
        changeDirection={null}
      />
    );
    expect(screen.queryByText(/^\+/)).not.toBeInTheDocument();
  });

  it('should render icon', () => {
    render(
      <MetricCard
        id="test-metric"
        label="Test Metric"
        value={100}
        icon="👥"
      />
    );
    expect(screen.getByText('👥')).toBeInTheDocument();
  });
});
