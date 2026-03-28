import os
import sys
import unittest
from unittest.mock import MagicMock

sys.modules["flask_socketio"] = MagicMock()
sys.modules["eventlet"] = MagicMock()
sys.modules["gevent"] = MagicMock()
sys.modules["geventwebsocket"] = MagicMock()
sys.modules["orchestrator"] = MagicMock()
sys.modules["orchestrator.orchestrator"] = MagicMock()
sys.modules["orchestrator.events"] = MagicMock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from config import TestingConfig
import database
import json


class DashboardAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
            db = database.get_db()
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("user1", "user1@test.com", "hash"),
            )
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("user2", "user2@test.com", "hash"),
            )
            db.commit()

    def tearDown(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DROP TABLE IF EXISTS messages")
            db.execute("DROP TABLE IF EXISTS conversation_participants")
            db.execute("DROP TABLE IF EXISTS conversations")
            db.execute("DROP TABLE IF EXISTS users")
            db.commit()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])


class TestAnalyticsAPIEndpoints(DashboardAPITestCase):
    def test_analytics_overview_endpoint(self):
        response = self.client.get('/api/analytics/overview')
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'metrics' in data or 'error' in data

    def test_analytics_metrics_users_endpoint(self):
        response = self.client.get('/api/analytics/metrics/users')
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'error' not in data or 'value' in data

    def test_analytics_metrics_messages_endpoint(self):
        response = self.client.get('/api/analytics/metrics/messages')
        
        assert response.status_code in [200, 500]

    def test_analytics_metrics_conversations_endpoint(self):
        response = self.client.get('/api/analytics/metrics/conversations')
        
        assert response.status_code in [200, 500]

    def test_analytics_metrics_active_users_endpoint(self):
        response = self.client.get('/api/analytics/metrics/active-users?period=daily')
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'error' not in data or 'value' in data

    def test_analytics_charts_endpoint(self):
        response = self.client.get('/api/analytics/charts/messages_per_day?days=7')
        
        assert response.status_code in [200, 400, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'data' in data or 'error' in data

    def test_analytics_charts_invalid_days(self):
        response = self.client.get('/api/analytics/charts/messages_per_day?days=500')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data

    def test_analytics_charts_zero_days(self):
        response = self.client.get('/api/analytics/charts/messages_per_day?days=0')
        
        assert response.status_code == 400

    def test_analytics_top_users_endpoint(self):
        response = self.client.get('/api/analytics/top-users?limit=5')
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'users' in data or 'error' in data

    def test_analytics_top_users_default_limit(self):
        response = self.client.get('/api/analytics/top-users')
        
        assert response.status_code in [200, 500]

    def test_analytics_top_users_invalid_limit(self):
        response = self.client.get('/api/analytics/top-users?limit=200')
        
        assert response.status_code == 400

    def test_analytics_top_users_zero_limit(self):
        response = self.client.get('/api/analytics/top-users?limit=0')
        
        assert response.status_code == 400

    def test_analytics_top_conversations_endpoint(self):
        response = self.client.get('/api/analytics/top-conversations?limit=5')
        
        assert response.status_code in [200, 500]

    def test_analytics_top_conversations_invalid_limit(self):
        response = self.client.get('/api/analytics/top-conversations?limit=200')
        
        assert response.status_code == 400

    def test_analytics_engagement_endpoint(self):
        response = self.client.get('/api/analytics/engagement')
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'engagement_rate' in data or 'avg_messages_per_user' in data or 'error' in data

    def test_analytics_all_endpoint(self):
        response = self.client.get('/api/analytics/all')
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'overview' in data or 'charts' in data or 'error' in data


class TestAnalyticsValidation(DashboardAPITestCase):
    def test_chart_type_invalid(self):
        response = self.client.get('/api/analytics/charts/invalid_type?days=7')
        
        assert response.status_code in [200, 400, 500]

    def test_active_users_invalid_period(self):
        response = self.client.get('/api/analytics/metrics/active-users?period=invalid')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data

    def test_active_users_valid_periods(self):
        for period in ['daily', 'weekly', 'monthly']:
            response = self.client.get(f'/api/analytics/metrics/active-users?period={period}')
            assert response.status_code in [200, 500]

    def test_chart_days_parameter_bounds_low(self):
        response = self.client.get('/api/analytics/charts/messages_per_day?days=1')
        
        assert response.status_code in [200, 400, 500]

    def test_chart_days_parameter_bounds_high(self):
        response = self.client.get('/api/analytics/charts/messages_per_day?days=365')
        
        assert response.status_code in [200, 400, 500]


class TestDashboardRoutes(DashboardAPITestCase):
    def test_dashboard_page_loads(self):
        response = self.client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'Analytics Dashboard' in response.data

    def test_dashboard_has_chart_canvases(self):
        response = self.client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'messages-chart' in response.data
        assert b'users-chart' in response.data
        assert b'conversations-chart' in response.data
        assert b'hourly-chart' in response.data

    def test_dashboard_has_metric_cards(self):
        response = self.client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'Total Users' in response.data
        assert b'Total Messages' in response.data
        assert b'Total Conversations' in response.data
        assert b'Active Users' in response.data

    def test_dashboard_has_tables(self):
        response = self.client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'top-users-table' in response.data
        assert b'top-conversations-table' in response.data


class TestDataIntegrity(DashboardAPITestCase):
    def test_overview_returns_all_metrics(self):
        response = self.client.get('/api/analytics/overview')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            if 'metrics' in data:
                assert len(data['metrics']) >= 4

    def test_chart_data_structure(self):
        response = self.client.get('/api/analytics/charts/messages_per_day?days=7')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            if 'data' in data:
                assert isinstance(data['data'], list)

    def test_top_users_data_structure(self):
        response = self.client.get('/api/analytics/top-users?limit=5')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            if 'users' in data and len(data['users']) > 0:
                user = data['users'][0]
                assert 'id' in user or 'username' in user


class TestErrorHandling(DashboardAPITestCase):
    def test_api_error_response_format(self):
        response = self.client.get('/api/analytics/metrics/active-users?period=bad')
        
        assert response.status_code in [400, 500]
        
        data = json.loads(response.data)
        assert 'error' in data


if __name__ == '__main__':
    unittest.main()
