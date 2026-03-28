import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAnalyticsStore } from '../src/stores/analyticsStore';
import { analyticsApi } from '../src/api/analytics';

vi.mock('../src/api/analytics', () => ({
  analyticsApi: {
    getOverview: vi.fn(),
    getMetric: vi.fn(),
    getChart: vi.fn(),
    getTopUsers: vi.fn(),
    getTopConversations: vi.fn(),
    getEngagement: vi.fn(),
    getAll: vi.fn(),
  },
}));

describe('Analytics Store', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAnalyticsStore.setState({
      overview: null,
      metrics: {},
      charts: {},
      topUsers: [],
      topConversations: [],
      engagement: null,
      isLoading: {},
      error: null,
      lastUpdated: null,
      filters: {
        period: 'daily',
        chartDays: {
          messages_per_day: 7,
          users_per_day: 7,
          conversations_per_day: 7,
          messages_by_hour: 7,
        },
      },
    });
  });

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const state = useAnalyticsStore.getState();
      expect(state.overview).toBeNull();
      expect(state.topUsers).toEqual([]);
      expect(state.topConversations).toEqual([]);
      expect(state.error).toBeNull();
    });
  });

  describe('setLoading', () => {
    it('should update loading state for a specific key', () => {
      const { setLoading } = useAnalyticsStore.getState();
      setLoading('overview', true);
      
      const state = useAnalyticsStore.getState();
      expect(state.isLoading.overview).toBe(true);
    });
  });

  describe('setError', () => {
    it('should set error message', () => {
      const { setError } = useAnalyticsStore.getState();
      const error = new Error('Test error');
      setError(error);
      
      const state = useAnalyticsStore.getState();
      expect(state.error).toBe('Test error');
    });

    it('should clear error when null is passed', () => {
      const { setError, clearError } = useAnalyticsStore.getState();
      setError(new Error('Test error'));
      clearError();
      
      const state = useAnalyticsStore.getState();
      expect(state.error).toBeNull();
    });
  });

  describe('setOverview', () => {
    it('should update overview data', () => {
      const { setOverview } = useAnalyticsStore.getState();
      const data = { 
        metrics: [{ id: 'total_users', label: 'Total Users', value: 100 }],
        generated_at: new Date().toISOString()
      };
      setOverview(data);
      
      const state = useAnalyticsStore.getState();
      expect(state.overview).toEqual(data);
      expect(state.lastUpdated).not.toBeNull();
    });
  });

  describe('setMetric', () => {
    it('should update a specific metric', () => {
      const { setMetric } = useAnalyticsStore.getState();
      const metricData = { id: 'total_users', label: 'Total Users', value: 100 };
      setMetric('users', metricData);
      
      const state = useAnalyticsStore.getState();
      expect(state.metrics.users).toEqual(metricData);
    });
  });

  describe('setChart', () => {
    it('should update chart data', () => {
      const { setChart } = useAnalyticsStore.getState();
      const chartData = [
        { label: '2024-01-01', value: 10 },
        { label: '2024-01-02', value: 20 },
      ];
      setChart('messagesPerDay', chartData);
      
      const state = useAnalyticsStore.getState();
      expect(state.charts.messagesPerDay).toEqual(chartData);
    });
  });

  describe('setFilter', () => {
    it('should update period filter', () => {
      const { setFilter } = useAnalyticsStore.getState();
      setFilter('period', 'weekly');
      
      const state = useAnalyticsStore.getState();
      expect(state.filters.period).toBe('weekly');
    });
  });

  describe('setChartDaysFilter', () => {
    it('should update chart days filter', () => {
      const { setChartDaysFilter } = useAnalyticsStore.getState();
      setChartDaysFilter('messages_per_day', 30);
      
      const state = useAnalyticsStore.getState();
      expect(state.filters.chartDays.messages_per_day).toBe(30);
    });
  });

  describe('fetchOverview', () => {
    it('should fetch and set overview data', async () => {
      const mockData = { 
        metrics: [{ id: 'total_users', value: 100 }],
        generated_at: new Date().toISOString()
      };
      analyticsApi.getOverview.mockResolvedValue(mockData);
      
      const { fetchOverview } = useAnalyticsStore.getState();
      await fetchOverview();
      
      expect(analyticsApi.getOverview).toHaveBeenCalled();
      expect(useAnalyticsStore.getState().overview).toEqual(mockData);
    });

    it('should handle fetch error', async () => {
      const error = new Error('Network error');
      analyticsApi.getOverview.mockRejectedValue(error);
      
      const { fetchOverview } = useAnalyticsStore.getState();
      
      await expect(fetchOverview()).rejects.toThrow('Network error');
      expect(useAnalyticsStore.getState().error).toBe('Network error');
    });
  });

  describe('fetchTopUsers', () => {
    it('should fetch and set top users', async () => {
      const mockUsers = [
        { id: 1, username: 'user1', email: 'user1@test.com', message_count: 50 },
        { id: 2, username: 'user2', email: 'user2@test.com', message_count: 30 },
      ];
      analyticsApi.getTopUsers.mockResolvedValue({ users: mockUsers });
      
      const { fetchTopUsers } = useAnalyticsStore.getState();
      await fetchTopUsers(10);
      
      expect(analyticsApi.getTopUsers).toHaveBeenCalledWith(10);
      expect(useAnalyticsStore.getState().topUsers).toEqual(mockUsers);
    });

    it('should handle fetch error and set empty array', async () => {
      analyticsApi.getTopUsers.mockRejectedValue(new Error('Error'));
      
      const { fetchTopUsers } = useAnalyticsStore.getState();
      try {
        await fetchTopUsers();
      } catch (e) {
        // expected
      }
      
      expect(useAnalyticsStore.getState().topUsers).toEqual([]);
    });
  });

  describe('fetchTopConversations', () => {
    it('should fetch and set top conversations', async () => {
      const mockConversations = [
        { id: 1, name: 'Conv 1', message_count: 100 },
        { id: 2, name: 'Conv 2', message_count: 50 },
      ];
      analyticsApi.getTopConversations.mockResolvedValue({ conversations: mockConversations });
      
      const { fetchTopConversations } = useAnalyticsStore.getState();
      await fetchTopConversations(10);
      
      expect(analyticsApi.getTopConversations).toHaveBeenCalledWith(10);
      expect(useAnalyticsStore.getState().topConversations).toEqual(mockConversations);
    });
  });

  describe('fetchChart', () => {
    it('should fetch and set chart data', async () => {
      const mockData = [
        { label: '2024-01-01', value: 10 },
        { label: '2024-01-02', value: 20 },
      ];
      analyticsApi.getChart.mockResolvedValue({ data: mockData });
      
      const { fetchChart } = useAnalyticsStore.getState();
      await fetchChart('messagesPerDay', 'messages_per_day', 7);
      
      expect(analyticsApi.getChart).toHaveBeenCalledWith('messages_per_day', 7);
      expect(useAnalyticsStore.getState().charts.messagesPerDay).toEqual(mockData);
    });

    it('should handle chart fetch error', async () => {
      analyticsApi.getChart.mockRejectedValue(new Error('Chart error'));
      
      const { fetchChart } = useAnalyticsStore.getState();
      await expect(fetchChart('messagesPerDay', 'messages_per_day', 7)).rejects.toThrow();
      expect(useAnalyticsStore.getState().error).toBe('Chart error');
    });
  });

  describe('hasData', () => {
    it('should return false when no data', () => {
      const { hasData } = useAnalyticsStore.getState();
      expect(hasData()).toBe(false);
    });

    it('should return true when overview exists', () => {
      const { setOverview, hasData } = useAnalyticsStore.getState();
      setOverview({ metrics: [] });
      expect(hasData()).toBe(true);
    });

    it('should return true when topUsers has data', () => {
      const { setTopUsers, hasData } = useAnalyticsStore.getState();
      setTopUsers([{ id: 1 }]);
      expect(hasData()).toBe(true);
    });
  });

  describe('updateChartDays', () => {
    it('should update filter and refetch chart', async () => {
      const mockData = [{ label: 'test', value: 1 }];
      analyticsApi.getChart.mockResolvedValue({ data: mockData });
      
      const { updateChartDays } = useAnalyticsStore.getState();
      await updateChartDays('messages_per_day', 14);
      
      expect(useAnalyticsStore.getState().filters.chartDays.messages_per_day).toBe(14);
      expect(analyticsApi.getChart).toHaveBeenCalledWith('messages_per_day', 14);
    });
  });
});
