import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { analyticsApi, ApiError } from '../../src/api/analytics';

global.fetch = vi.fn();

describe('Analytics API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const mockResponse = (data, ok = true, status = 200) => ({
    ok,
    status,
    json: vi.fn().mockResolvedValue(data),
  });

  describe('fetchWithError', () => {
    it('should return data on successful response', async () => {
      const data = { test: 'data' };
      global.fetch.mockResolvedValue(mockResponse(data));
      
      const result = await analyticsApi.getOverview();
      expect(result).toEqual(data);
    });

    it('should throw ApiError on non-ok response', async () => {
      const errorData = { error: 'Not found' };
      global.fetch.mockResolvedValue(mockResponse(errorData, false, 404));
      
      await expect(analyticsApi.getOverview()).rejects.toThrow(ApiError);
    });

    it('should include status and data in ApiError', async () => {
      const errorData = { error: 'Bad request', details: {} };
      global.fetch.mockResolvedValue(mockResponse(errorData, false, 400));
      
      try {
        await analyticsApi.getOverview();
      } catch (error) {
        expect(error.name).toBe('ApiError');
        expect(error.status).toBe(400);
        expect(error.data).toEqual(errorData);
      }
    });
  });

  describe('getOverview', () => {
    it('should call /api/analytics/overview', async () => {
      global.fetch.mockResolvedValue(mockResponse({ metrics: [] }));
      
      await analyticsApi.getOverview();
      
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/analytics/overview',
        expect.objectContaining({
          headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        })
      );
    });
  });

  describe('getMetric', () => {
    it('should call correct metrics endpoint', async () => {
      global.fetch.mockResolvedValue(mockResponse({ value: 100 }));
      
      await analyticsApi.getMetric('users');
      
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/analytics/metrics/users',
        expect.any(Object)
      );
    });
  });

  describe('getChart', () => {
    it('should call chart endpoint with days parameter', async () => {
      global.fetch.mockResolvedValue(mockResponse({ data: [] }));
      
      await analyticsApi.getChart('messages_per_day', 30);
      
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/analytics/charts/messages_per_day?days=30',
        expect.any(Object)
      );
    });

    it('should use default days parameter', async () => {
      global.fetch.mockResolvedValue(mockResponse({ data: [] }));
      
      await analyticsApi.getChart('messages_per_day');
      
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/analytics/charts/messages_per_day?days=7',
        expect.any(Object)
      );
    });
  });

  describe('getTopUsers', () => {
    it('should call top-users endpoint with limit', async () => {
      global.fetch.mockResolvedValue(mockResponse({ users: [] }));
      
      await analyticsApi.getTopUsers(5);
      
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/analytics/top-users?limit=5',
        expect.any(Object)
      );
    });

    it('should use default limit', async () => {
      global.fetch.mockResolvedValue(mockResponse({ users: [] }));
      
      await analyticsApi.getTopUsers();
      
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/analytics/top-users?limit=10',
        expect.any(Object)
      );
    });
  });

  describe('getTopConversations', () => {
    it('should call top-conversations endpoint with limit', async () => {
      global.fetch.mockResolvedValue(mockResponse({ conversations: [] }));
      
      await analyticsApi.getTopConversations(5);
      
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/analytics/top-conversations?limit=5',
        expect.any(Object)
      );
    });
  });

  describe('getEngagement', () => {
    it('should call /api/analytics/engagement', async () => {
      global.fetch.mockResolvedValue(mockResponse({ engagement_rate: 50 }));
      
      await analyticsApi.getEngagement();
      
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/analytics/engagement',
        expect.any(Object)
      );
    });
  });

  describe('getAll', () => {
    it('should call /api/analytics/all', async () => {
      global.fetch.mockResolvedValue(mockResponse({ overview: {} }));
      
      await analyticsApi.getAll();
      
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/analytics/all',
        expect.any(Object)
      );
    });
  });
});
