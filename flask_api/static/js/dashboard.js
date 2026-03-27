const API_BASE = '/api/analytics';

const DashboardState = {
    overview: null,
    charts: {},
    topUsers: [],
    topConversations: [],
    loading: {
        overview: false,
        charts: false,
        topUsers: false,
        topConversations: false
    },
    error: null,
    filters: {
        period: 'daily',
        chartDays: {
            messages_per_day: 7,
            users_per_day: 7,
            conversations_per_day: 7,
            messages_by_hour: 7
        }
    }
};

const ChartManager = {
    charts: {},

    init() {
        this.messagesChart = this.createLineChart('messages-chart', 'Messages');
        this.usersChart = this.createLineChart('users-chart', 'Users');
        this.conversationsChart = this.createLineChart('conversations-chart', 'Conversations');
        this.hourlyChart = this.createBarChart('hourly-chart', 'Messages by Hour');
        this.typesChart = this.createDoughnutChart('types-chart', 'Message Types');
    },

    createLineChart(canvasId, label) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label,
                    data: [],
                    borderColor: '#4a90d9',
                    backgroundColor: 'rgba(74, 144, 217, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: this.getLineChartOptions()
        });
    },

    createBarChart(canvasId, label) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label,
                    data: [],
                    backgroundColor: '#4a90d9'
                }]
            },
            options: this.getBarChartOptions()
        });
    },

    createDoughnutChart(canvasId, label) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    label,
                    data: [],
                    backgroundColor: ['#4a90d9', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6']
                }]
            },
            options: this.getDoughnutChartOptions()
        });
    },

    getLineChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { beginAtZero: true, grid: { color: '#f0f0f0' } }
            }
        };
    },

    getBarChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { beginAtZero: true, grid: { color: '#f0f0f0' } }
            }
        };
    },

    getDoughnutChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'right' } }
        };
    },

    updateLineChart(chart, data) {
        if (!chart) return;
        chart.data.labels = data.map(d => d.label);
        chart.data.datasets[0].data = data.map(d => d.value);
        chart.update();
    },

    updateBarChart(chart, data) {
        if (!chart) return;
        chart.data.labels = data.map(d => d.label);
        chart.data.datasets[0].data = data.map(d => d.value);
        chart.update();
    },

    updateDoughnutChart(chart, data) {
        if (!chart) return;
        chart.data.labels = data.map(d => d.label);
        chart.data.datasets[0].data = data.map(d => d.value);
        chart.update();
    }
};

const API = {
    async fetchWithError(url) {
        const response = await fetch(url);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        return data;
    },

    async getOverview() {
        return this.fetchWithError(`${API_BASE}/overview`);
    },

    async getMetric(endpoint) {
        return this.fetchWithError(`${API_BASE}/metrics/${endpoint}`);
    },

    async getChart(chartType, days = 7) {
        return this.fetchWithError(`${API_BASE}/charts/${chartType}?days=${days}`);
    },

    async getTopUsers(limit = 10) {
        return this.fetchWithError(`${API_BASE}/top-users?limit=${limit}`);
    },

    async getTopConversations(limit = 10) {
        return this.fetchWithError(`${API_BASE}/top-conversations?limit=${limit}`);
    }
};

const UIManager = {
    showLoading() {
        document.getElementById('loading-overlay').classList.remove('hidden');
    },

    hideLoading() {
        document.getElementById('loading-overlay').classList.add('hidden');
    },

    showError(message) {
        const errorEl = document.getElementById('error-message');
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
    },

    hideError() {
        document.getElementById('error-message').classList.add('hidden');
    },

    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    },

    updateMetric(metricId, value, change, direction) {
        const valueEl = document.getElementById(`metric-${metricId}-value`);
        const changeEl = document.getElementById(`metric-${metricId}-change`);
        
        if (valueEl) valueEl.textContent = this.formatNumber(value);
        
        if (changeEl && change !== undefined && change !== null) {
            const sign = direction === 'up' ? '+' : '';
            changeEl.textContent = `${sign}${change}%`;
            changeEl.className = `metric-change ${direction === 'up' ? 'positive' : 'negative'}`;
        }
    },

    renderTopUsers(users) {
        const tbody = document.querySelector('#top-users-table tbody');
        if (!users || users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-cell">No data available</td></tr>';
            return;
        }
        tbody.innerHTML = users.map(user => `
            <tr>
                <td>${this.escapeHtml(user.username)}</td>
                <td>${this.escapeHtml(user.email)}</td>
                <td>${user.message_count}</td>
                <td>${user.last_activity ? new Date(user.last_activity).toLocaleDateString() : '-'}</td>
            </tr>
        `).join('');
    },

    renderTopConversations(conversations) {
        const tbody = document.querySelector('#top-conversations-table tbody');
        if (!conversations || conversations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-cell">No data available</td></tr>';
            return;
        }
        tbody.innerHTML = conversations.map(conv => `
            <tr>
                <td>${this.escapeHtml(conv.name || 'Unnamed')}</td>
                <td>${conv.is_group ? 'Group' : 'Direct'}</td>
                <td>${conv.participant_count}</td>
                <td>${conv.message_count}</td>
            </tr>
        `).join('');
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

const Dashboard = {
    async init() {
        this.setupEventListeners();
        ChartManager.init();
        await this.loadAllData();
    },

    setupEventListeners() {
        document.getElementById('refresh-btn').addEventListener('click', () => this.loadAllData());
        
        document.getElementById('period-filter').addEventListener('change', (e) => {
            DashboardState.filters.period = e.target.value;
            this.loadActiveUsers();
        });

        document.querySelectorAll('.days-filter').forEach(select => {
            select.addEventListener('change', (e) => {
                const chartType = e.target.dataset.chart;
                const days = parseInt(e.target.value);
                DashboardState.filters.chartDays[chartType] = days;
                this.loadChart(chartType, days);
            });
        });
    },

    async loadAllData() {
        UIManager.showLoading();
        UIManager.hideError();

        try {
            await Promise.all([
                this.loadOverview(),
                this.loadAllCharts(),
                this.loadTopUsers(),
                this.loadTopConversations()
            ]);
        } catch (error) {
            UIManager.showError(`Failed to load data: ${error.message}`);
            console.error('Dashboard load error:', error);
        } finally {
            UIManager.hideLoading();
        }
    },

    async loadOverview() {
        DashboardState.loading.overview = true;
        try {
            const data = await API.getOverview();
            DashboardState.overview = data;
            
            data.metrics.forEach(metric => {
                UIManager.updateMetric(
                    metric.id.replace('total_', '').replace('active_users_', 'active-users'),
                    metric.value,
                    metric.change,
                    metric.change_direction
                );
            });
        } catch (error) {
            console.error('Overview load error:', error);
            throw error;
        } finally {
            DashboardState.loading.overview = false;
        }
    },

    async loadActiveUsers() {
        try {
            const period = DashboardState.filters.period;
            const data = await API.getMetric(`active-users?period=${period}`);
            UIManager.updateMetric('active-users', data.value, data.change, data.change_direction);
        } catch (error) {
            console.error('Active users load error:', error);
        }
    },

    async loadAllCharts() {
        DashboardState.loading.charts = true;
        const chartTypes = ['messages_per_day', 'users_per_day', 'conversations_per_day', 'messages_by_hour'];
        
        try {
            await Promise.all(chartTypes.map(type => 
                this.loadChart(type, DashboardState.filters.chartDays[type])
            ));
            await this.loadChart('message_type_distribution', 7);
        } catch (error) {
            console.error('Charts load error:', error);
            throw error;
        } finally {
            DashboardState.loading.charts = false;
        }
    },

    async loadChart(chartType, days = 7) {
        try {
            const data = await API.getChart(chartType, days);
            DashboardState.charts[chartType] = data.data;

            switch (chartType) {
                case 'messages_per_day':
                    ChartManager.updateLineChart(ChartManager.messagesChart, data.data);
                    break;
                case 'users_per_day':
                    ChartManager.updateLineChart(ChartManager.usersChart, data.data);
                    break;
                case 'conversations_per_day':
                    ChartManager.updateLineChart(ChartManager.conversationsChart, data.data);
                    break;
                case 'messages_by_hour':
                    ChartManager.updateBarChart(ChartManager.hourlyChart, data.data);
                    break;
                case 'message_type_distribution':
                    ChartManager.updateDoughnutChart(ChartManager.typesChart, data.data);
                    break;
            }
        } catch (error) {
            console.error(`Chart load error (${chartType}):`, error);
        }
    },

    async loadTopUsers() {
        DashboardState.loading.topUsers = true;
        try {
            const data = await API.getTopUsers();
            DashboardState.topUsers = data.users;
            UIManager.renderTopUsers(data.users);
        } catch (error) {
            console.error('Top users load error:', error);
            UIManager.renderTopUsers([]);
        } finally {
            DashboardState.loading.topUsers = false;
        }
    },

    async loadTopConversations() {
        DashboardState.loading.topConversations = true;
        try {
            const data = await API.getTopConversations();
            DashboardState.topConversations = data.conversations;
            UIManager.renderTopConversations(data.conversations);
        } catch (error) {
            console.error('Top conversations load error:', error);
            UIManager.renderTopConversations([]);
        } finally {
            DashboardState.loading.topConversations = false;
        }
    }
};

document.addEventListener('DOMContentLoaded', () => Dashboard.init());
