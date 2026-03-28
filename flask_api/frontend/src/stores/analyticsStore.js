import { create } from 'zustand';
import { analyticsApi, ApiError } from '../api/analytics';

const initialState = {
  overview: null,
  metrics: {
    users: null,
    messages: null,
    conversations: null,
    activeUsers: null,
  },
  charts: {
    messagesPerDay: [],
    usersPerDay: [],
    conversationsPerDay: [],
    messagesByHour: [],
    messageTypeDistribution: [],
  },
  topUsers: [],
  topConversations: [],
  engagement: null,
  isLoading: {
    overview: false,
    charts: false,
    topUsers: false,
    topConversations: false,
    engagement: false,
  },
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
};

export const useAnalyticsStore = create((set, get) => ({
  ...initialState,

  setLoading: (key, value) =>
    set((state) => ({
      isLoading: { ...state.isLoading, [key]: value },
    })),

  setError: (error) => set({ error: error ? error.message : null }),

  clearError: () => set({ error: null }),

  setOverview: (overview) => set({ overview, lastUpdated: new Date().toISOString() }),

  setMetric: (key, data) =>
    set((state) => ({
      metrics: { ...state.metrics, [key]: data },
    })),

  setChart: (key, data) =>
    set((state) => ({
      charts: { ...state.charts, [key]: data },
    })),

  setTopUsers: (users) => set({ topUsers: users }),

  setTopConversations: (conversations) => set({ topConversations: conversations }),

  setEngagement: (engagement) => set({ engagement }),

  setFilter: (key, value) =>
    set((state) => ({
      filters: {
        ...state.filters,
        [key]: value,
      },
    })),

  setChartDaysFilter: (chartType, days) =>
    set((state) => ({
      filters: {
        ...state.filters,
        chartDays: {
          ...state.filters.chartDays,
          [chartType]: days,
        },
      },
    })),

  fetchOverview: async () => {
    const { setLoading, setOverview, setError } = get();
    setLoading('overview', true);
    setError(null);
    try {
      const data = await analyticsApi.getOverview();
      setOverview(data);
    } catch (error) {
      setError(error);
      throw error;
    } finally {
      setLoading('overview', false);
    }
  },

  fetchMetric: async (metricName, endpoint) => {
    const { setLoading, setMetric, setError } = get();
    setLoading(metricName, true);
    setError(null);
    try {
      const data = await analyticsApi.getMetric(endpoint);
      setMetric(metricName, data);
    } catch (error) {
      setError(error);
      throw error;
    } finally {
      setLoading(metricName, false);
    }
  },

  fetchChart: async (chartKey, chartType, days = 7) => {
    const { setLoading, setChart, setError } = get();
    setLoading('charts', true);
    setError(null);
    try {
      const data = await analyticsApi.getChart(chartType, days);
      setChart(chartKey, data.data);
    } catch (error) {
      setError(error);
      throw error;
    } finally {
      setLoading('charts', false);
    }
  },

  fetchTopUsers: async (limit = 10) => {
    const { setLoading, setTopUsers, setError } = get();
    setLoading('topUsers', true);
    setError(null);
    try {
      const data = await analyticsApi.getTopUsers(limit);
      setTopUsers(data.users);
    } catch (error) {
      setError(error);
      setTopUsers([]);
      throw error;
    } finally {
      setLoading('topUsers', false);
    }
  },

  fetchTopConversations: async (limit = 10) => {
    const { setLoading, setTopConversations, setError } = get();
    setLoading('topConversations', true);
    setError(null);
    try {
      const data = await analyticsApi.getTopConversations(limit);
      setTopConversations(data.conversations);
    } catch (error) {
      setError(error);
      setTopConversations([]);
      throw error;
    } finally {
      setLoading('topConversations', false);
    }
  },

  fetchEngagement: async () => {
    const { setLoading, setEngagement, setError } = get();
    setLoading('engagement', true);
    setError(null);
    try {
      const data = await analyticsApi.getEngagement();
      setEngagement(data);
    } catch (error) {
      setError(error);
      throw error;
    } finally {
      setLoading('engagement', false);
    }
  },

  fetchAllAnalytics: async () => {
    const { setError } = get();
    setError(null);

    try {
      await Promise.all([
        get().fetchOverview(),
        get().fetchChart('messagesPerDay', 'messages_per_day', 7),
        get().fetchChart('usersPerDay', 'users_per_day', 7),
        get().fetchChart('conversationsPerDay', 'conversations_per_day', 7),
        get().fetchChart('messagesByHour', 'messages_by_hour', 7),
        get().fetchChart('messageTypeDistribution', 'message_type_distribution', 7),
        get().fetchTopUsers(10),
        get().fetchTopConversations(10),
        get().fetchEngagement(),
      ]);
    } catch (error) {
      setError(error);
    }
  },

  updateChartDays: async (chartType, days) => {
    const { setChartDaysFilter, fetchChart } = get();
    const chartKeyMap = {
      messages_per_day: 'messagesPerDay',
      users_per_day: 'usersPerDay',
      conversations_per_day: 'conversationsPerDay',
      messages_by_hour: 'messagesByHour',
    };
    const chartKey = chartKeyMap[chartType];
    if (chartKey) {
      setChartDaysFilter(chartType, days);
      await fetchChart(chartKey, chartType, days);
    }
  },

  hasData: () => {
    const state = get();
    return (
      state.overview !== null ||
      state.topUsers.length > 0 ||
      state.topConversations.length > 0 ||
      Object.values(state.charts).some((arr) => arr.length > 0)
    );
  },
}));
