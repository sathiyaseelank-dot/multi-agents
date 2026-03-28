const API_BASE = '/api/analytics';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function fetchWithError(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  let data;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const errorMessage = data?.error || `HTTP ${response.status}`;
    throw new ApiError(errorMessage, response.status, data);
  }

  return data;
}

export const analyticsApi = {
  async getOverview() {
    return fetchWithError(`${API_BASE}/overview`);
  },

  async getMetric(endpoint) {
    return fetchWithError(`${API_BASE}/metrics/${endpoint}`);
  },

  async getChart(chartType, days = 7) {
    return fetchWithError(`${API_BASE}/charts/${chartType}?days=${days}`);
  },

  async getTopUsers(limit = 10) {
    return fetchWithError(`${API_BASE}/top-users?limit=${limit}`);
  },

  async getTopConversations(limit = 10) {
    return fetchWithError(`${API_BASE}/top-conversations?limit=${limit}`);
  },

  async getEngagement() {
    return fetchWithError(`${API_BASE}/engagement`);
  },

  async getAll() {
    return fetchWithError(`${API_BASE}/all`);
  }
};

export { ApiError };
