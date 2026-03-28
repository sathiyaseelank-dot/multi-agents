import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChartsGrid } from '../../src/components/ChartsGrid';
import { useAnalyticsStore } from '../../src/stores/analyticsStore';

vi.mock('../../src/stores/analyticsStore', () => ({
  useAnalyticsStore: vi.fn(),
}));

vi.mock('chart.js', () => {
  const mockInstance = { destroy: vi.fn() };
  const registerables = [];
  return {
    Chart: Object.assign(vi.fn(() => mockInstance), { register: vi.fn() }),
    registerables,
  };
});

describe('ChartsGrid', () => {
  const mockCharts = {
    messagesPerDay: [
      { label: '2024-01-01', value: 10 },
      { label: '2024-01-02', value: 20 },
    ],
    usersPerDay: [
      { label: '2024-01-01', value: 5 },
    ],
    conversationsPerDay: [
      { label: '2024-01-01', value: 3 },
    ],
    messagesByHour: [
      { label: '00:00', value: 10 },
    ],
    messageTypeDistribution: [
      { label: 'Text', value: 80 },
      { label: 'Image', value: 20 },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    useAnalyticsStore.mockReturnValue({
      updateChartDays: vi.fn(),
      filters: {
        chartDays: {
          messages_per_day: 7,
          users_per_day: 7,
          conversations_per_day: 7,
          messages_by_hour: 7,
        },
      },
      isLoading: { charts: false },
    });
  });

  it('should render all chart cards', () => {
    render(<ChartsGrid charts={mockCharts} />);
    expect(screen.getByText('Messages Over Time')).toBeInTheDocument();
    expect(screen.getByText('Users Over Time')).toBeInTheDocument();
    expect(screen.getByText('Conversations Over Time')).toBeInTheDocument();
    expect(screen.getByText('Messages by Hour')).toBeInTheDocument();
    expect(screen.getByText('Message Types')).toBeInTheDocument();
  });

  it('should render chart cards with days filter for non-doughnut charts', () => {
    render(<ChartsGrid charts={mockCharts} />);
    const selects = screen.getAllByRole('combobox');
    expect(selects).toHaveLength(4);
  });

  it('should render doughnut chart card without days filter', () => {
    render(<ChartsGrid charts={mockCharts} />);
    const doughnutCard = screen.getByText('Message Types').closest('.chart-card');
    expect(doughnutCard.querySelector('.days-filter')).not.toBeInTheDocument();
  });

  it('should use store filter values for selected days', () => {
    useAnalyticsStore.mockReturnValue({
      updateChartDays: vi.fn(),
      filters: {
        chartDays: {
          messages_per_day: 14,
          users_per_day: 30,
          conversations_per_day: 7,
          messages_by_hour: 7,
        },
      },
      isLoading: { charts: false },
    });

    render(<ChartsGrid charts={mockCharts} />);
    const selects = screen.getAllByRole('combobox');
    expect(selects[0]).toHaveValue('14');
  });

  it('should call updateChartDays when days filter changes', async () => {
    const mockUpdateChartDays = vi.fn();
    useAnalyticsStore.mockReturnValue({
      updateChartDays: mockUpdateChartDays,
      filters: {
        chartDays: {
          messages_per_day: 7,
          users_per_day: 7,
          conversations_per_day: 7,
          messages_by_hour: 7,
        },
      },
      isLoading: { charts: false },
    });

    const { container } = render(<ChartsGrid charts={mockCharts} />);
    const firstSelect = container.querySelector('.days-filter');
    firstSelect.value = '30';
    firstSelect.dispatchEvent(new Event('change', { bubbles: true }));
  });

  it('should handle empty charts data gracefully', () => {
    render(<ChartsGrid charts={{}} />);
    expect(screen.getByText('Messages Over Time')).toBeInTheDocument();
  });

  it('should render section with charts-grid class', () => {
    const { container } = render(<ChartsGrid charts={mockCharts} />);
    expect(container.querySelector('.charts-grid')).toBeInTheDocument();
  });
});
