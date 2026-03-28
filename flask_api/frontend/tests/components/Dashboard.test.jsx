import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Dashboard from '../../src/components/Dashboard';
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

describe('Dashboard', () => {
  const mockOverview = {
    metrics: [
      { id: 'total_users', label: 'Total Users', value: 100, change: 5, change_direction: 'up' },
      { id: 'total_messages', label: 'Total Messages', value: 500, change: 10, change_direction: 'up' },
    ],
  };

  const mockCharts = {
    messagesPerDay: [{ label: '2024-01-01', value: 10 }],
    usersPerDay: [{ label: '2024-01-01', value: 5 }],
    conversationsPerDay: [{ label: '2024-01-01', value: 3 }],
    messagesByHour: [{ label: '00:00', value: 10 }],
    messageTypeDistribution: [{ label: 'Text', value: 80 }],
  };

  const defaultStoreState = {
    overview: mockOverview,
    charts: mockCharts,
    topUsers: [{ id: 1, username: 'user1', email: 'user1@test.com', message_count: 50, last_activity: '2024-01-15' }],
    topConversations: [{ id: 1, name: 'Conv 1', is_group: true, participant_count: 5, message_count: 100 }],
    hasData: () => true,
    filters: {
      period: 'daily',
      chartDays: {
        messages_per_day: 7,
        users_per_day: 7,
        conversations_per_day: 7,
        messages_by_hour: 7,
      },
    },
    updateChartDays: vi.fn(),
    isLoading: { charts: false },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    useAnalyticsStore.mockReturnValue(defaultStoreState);
  });

  describe('loading state', () => {
    it('should show loading overlay when isLoading is true', () => {
      render(<Dashboard isLoading={true} error={null} onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.getByTestId('loading-overlay')).toBeInTheDocument();
    });

    it('should show "Loading..." text on refresh button when loading', () => {
      render(<Dashboard isLoading={true} error={null} onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('should disable refresh button when loading', () => {
      render(<Dashboard isLoading={true} error={null} onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.getByText('Loading...')).toBeDisabled();
    });

    it('should not show loading overlay when isLoading is false', () => {
      render(<Dashboard isLoading={false} error={null} onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.queryByTestId('loading-overlay')).not.toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('should show error banner when error is present', () => {
      render(<Dashboard isLoading={false} error="Server error" onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.getByTestId('error-banner')).toBeInTheDocument();
    });

    it('should display error message in banner', () => {
      render(<Dashboard isLoading={false} error="Connection failed" onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.getByText('Connection failed')).toBeInTheDocument();
    });

    it('should show retry button in error banner', () => {
      render(<Dashboard isLoading={false} error="Error" onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    it('should call onRetry when retry button is clicked', async () => {
      const onRetry = vi.fn();
      const user = userEvent.setup();
      render(<Dashboard isLoading={false} error="Error" onRetry={onRetry} onDismissError={vi.fn()} />);

      await user.click(screen.getByText('Retry'));
      expect(onRetry).toHaveBeenCalled();
    });

    it('should show dismiss button in error banner', () => {
      render(<Dashboard isLoading={false} error="Error" onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.getByText('Dismiss')).toBeInTheDocument();
    });

    it('should call onDismissError when dismiss is clicked', async () => {
      const onDismissError = vi.fn();
      const user = userEvent.setup();
      render(<Dashboard isLoading={false} error="Error" onRetry={vi.fn()} onDismissError={onDismissError} />);

      await user.click(screen.getByText('Dismiss'));
      expect(onDismissError).toHaveBeenCalled();
    });
  });

  describe('empty state', () => {
    it('should show empty state when no data and not loading', () => {
      useAnalyticsStore.mockReturnValue({
        ...defaultStoreState,
        overview: null,
        charts: {},
        topUsers: [],
        topConversations: [],
        hasData: () => false,
      });

      render(<Dashboard isLoading={false} error={null} onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
      expect(screen.getByText('No Analytics Data')).toBeInTheDocument();
    });

    it('should show retry button in empty state', () => {
      useAnalyticsStore.mockReturnValue({
        ...defaultStoreState,
        overview: null,
        charts: {},
        topUsers: [],
        topConversations: [],
        hasData: () => false,
      });

      render(<Dashboard isLoading={false} error={null} onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.getByText('Start using the application to generate analytics data.')).toBeInTheDocument();
    });

    it('should not show empty state when loading', () => {
      useAnalyticsStore.mockReturnValue({
        ...defaultStoreState,
        overview: null,
        hasData: () => false,
      });

      render(<Dashboard isLoading={true} error={null} onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.queryByText('No Analytics Data')).not.toBeInTheDocument();
    });
  });

  describe('data display', () => {
    it('should render dashboard header when data is available', () => {
      render(<Dashboard isLoading={false} error={null} onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });

    it('should render refresh button when data is available', () => {
      render(<Dashboard isLoading={false} error={null} onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });

    it('should call onRetry when refresh button is clicked', async () => {
      const onRetry = vi.fn();
      const user = userEvent.setup();
      render(<Dashboard isLoading={false} error={null} onRetry={onRetry} onDismissError={vi.fn()} />);

      await user.click(screen.getByText('Refresh'));
      expect(onRetry).toHaveBeenCalled();
    });

    it('should not render data sections when no data and not loading', () => {
      useAnalyticsStore.mockReturnValue({
        ...defaultStoreState,
        overview: null,
        charts: {},
        topUsers: [],
        topConversations: [],
        hasData: () => false,
      });

      render(<Dashboard isLoading={false} error={null} onRetry={vi.fn()} onDismissError={vi.fn()} />);
      expect(screen.queryByText('Analytics Dashboard')).not.toBeInTheDocument();
    });
  });
});
