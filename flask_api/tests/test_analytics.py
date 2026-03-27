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


class AnalyticsOverviewTestCase(unittest.TestCase):
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

    def test_overview_returns_metrics(self):
        response = self.client.get("/api/analytics/overview")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("metrics", data)
        self.assertIn("generated_at", data)
        self.assertEqual(len(data["metrics"]), 4)

    def test_overview_includes_total_users(self):
        response = self.client.get("/api/analytics/overview")
        data = response.get_json()
        user_metric = next((m for m in data["metrics"] if m["id"] == "total_users"), None)
        self.assertIsNotNone(user_metric)
        self.assertEqual(user_metric["value"], 2)

    def test_overview_error_handling(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DROP TABLE IF EXISTS users")
            db.commit()
        response = self.client.get("/api/analytics/overview")
        self.assertEqual(response.status_code, 500)


class AnalyticsMetricsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
            db = database.get_db()
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("testuser", "test@test.com", "hash"),
            )
            db.execute("INSERT INTO conversations (name, is_group) VALUES (?, ?)", ("Test", 0))
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                (1, 1, "Hello", "text"),
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

    def test_get_total_users_metric(self):
        response = self.client.get("/api/analytics/metrics/users")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["id"], "total_users")
        self.assertEqual(data["value"], 1)

    def test_get_total_messages_metric(self):
        response = self.client.get("/api/analytics/metrics/messages")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["id"], "total_messages")
        self.assertEqual(data["value"], 1)

    def test_get_total_conversations_metric(self):
        response = self.client.get("/api/analytics/metrics/conversations")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["id"], "total_conversations")
        self.assertEqual(data["value"], 1)

    def test_get_active_users_daily(self):
        response = self.client.get("/api/analytics/metrics/active-users?period=daily")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("active_users_daily", data["id"])

    def test_get_active_users_invalid_period(self):
        response = self.client.get("/api/analytics/metrics/active-users?period=invalid")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_invalid_metric_returns_404(self):
        response = self.client.get("/api/analytics/metrics/nonexistent")
        self.assertEqual(response.status_code, 404)


class AnalyticsChartsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
            db = database.get_db()
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("chartuser", "chart@test.com", "hash"),
            )
            db.execute("INSERT INTO conversations (name, is_group) VALUES (?, ?)", ("ChartConv", 0))
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                (1, 1, "Test message", "text"),
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

    def test_get_messages_per_day_chart(self):
        response = self.client.get("/api/analytics/charts/messages_per_day")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["chart_type"], "messages_per_day")
        self.assertIn("data", data)
        self.assertIn("generated_at", data)

    def test_get_users_per_day_chart(self):
        response = self.client.get("/api/analytics/charts/users_per_day")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["chart_type"], "users_per_day")

    def test_get_conversations_per_day_chart(self):
        response = self.client.get("/api/analytics/charts/conversations_per_day")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["chart_type"], "conversations_per_day")

    def test_get_messages_by_hour_chart(self):
        response = self.client.get("/api/analytics/charts/messages_by_hour")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("data", data)

    def test_get_message_type_distribution_chart(self):
        response = self.client.get("/api/analytics/charts/message_type_distribution")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("data", data)

    def test_chart_with_custom_days(self):
        response = self.client.get("/api/analytics/charts/messages_per_day?days=30")
        self.assertEqual(response.status_code, 200)

    def test_chart_invalid_days_too_small(self):
        response = self.client.get("/api/analytics/charts/messages_per_day?days=0")
        self.assertEqual(response.status_code, 400)

    def test_chart_invalid_days_too_large(self):
        response = self.client.get("/api/analytics/charts/messages_per_day?days=500")
        self.assertEqual(response.status_code, 400)

    def test_invalid_chart_type(self):
        response = self.client.get("/api/analytics/charts/invalid_type")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)


class AnalyticsTopListsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
            db = database.get_db()
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("active1", "active1@test.com", "hash"),
            )
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("active2", "active2@test.com", "hash"),
            )
            db.execute("INSERT INTO conversations (name, is_group) VALUES (?, ?)", ("Conv1", 0))
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                (1, 1, "Message 1", "text"),
            )
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                (1, 2, "Message 2", "text"),
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

    def test_get_top_users(self):
        response = self.client.get("/api/analytics/top-users")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("users", data)
        self.assertIsInstance(data["users"], list)

    def test_get_top_users_custom_limit(self):
        response = self.client.get("/api/analytics/top-users?limit=5")
        self.assertEqual(response.status_code, 200)

    def test_get_top_users_invalid_limit_too_small(self):
        response = self.client.get("/api/analytics/top-users?limit=0")
        self.assertEqual(response.status_code, 400)

    def test_get_top_users_invalid_limit_too_large(self):
        response = self.client.get("/api/analytics/top-users?limit=200")
        self.assertEqual(response.status_code, 400)

    def test_get_top_conversations(self):
        response = self.client.get("/api/analytics/top-conversations")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("conversations", data)
        self.assertIsInstance(data["conversations"], list)

    def test_get_top_conversations_custom_limit(self):
        response = self.client.get("/api/analytics/top-conversations?limit=5")
        self.assertEqual(response.status_code, 200)


class AnalyticsEngagementTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
            db = database.get_db()
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("user", "user@test.com", "hash"),
            )
            db.execute("INSERT INTO conversations (name, is_group) VALUES (?, ?)", ("C", 0))
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                (1, 1, "Hello", "text"),
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

    def test_get_engagement_metrics(self):
        response = self.client.get("/api/analytics/engagement")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("avg_messages_per_user", data)
        self.assertIn("active_users_7d", data)
        self.assertIn("engagement_rate", data)
        self.assertIn("total_users", data)

    def test_engagement_rate_calculation(self):
        response = self.client.get("/api/analytics/engagement")
        data = response.get_json()
        self.assertGreaterEqual(data["engagement_rate"], 0)
        self.assertLessEqual(data["engagement_rate"], 100)


class AnalyticsAllTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()

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

    def test_get_all_analytics(self):
        response = self.client.get("/api/analytics/all")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("overview", data)
        self.assertIn("charts", data)
        self.assertIn("top_lists", data)
        self.assertIn("engagement", data)
        self.assertIn("generated_at", data)

    def test_all_analytics_contains_all_charts(self):
        response = self.client.get("/api/analytics/all")
        data = response.get_json()
        expected_charts = [
            "messages_per_day",
            "users_per_day",
            "conversations_per_day",
            "messages_by_hour",
            "message_type_distribution",
        ]
        for chart in expected_charts:
            self.assertIn(chart, data["charts"])

    def test_all_analytics_contains_top_lists(self):
        response = self.client.get("/api/analytics/all")
        data = response.get_json()
        self.assertIn("active_users", data["top_lists"])
        self.assertIn("conversations", data["top_lists"])


class AnalyticsValidationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()

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

    def test_chart_data_returns_list(self):
        response = self.client.get("/api/analytics/charts/messages_per_day")
        data = response.get_json()
        self.assertIsInstance(data["data"], list)

    def test_chart_data_has_label_and_value(self):
        response = self.client.get("/api/analytics/charts/messages_per_day")
        data = response.get_json()
        if data["data"]:
            point = data["data"][0]
            self.assertIn("label", point)
            self.assertIn("value", point)

    def test_metric_has_required_fields(self):
        response = self.client.get("/api/analytics/metrics/users")
        data = response.get_json()
        self.assertIn("id", data)
        self.assertIn("label", data)
        self.assertIn("value", data)

    def test_overview_generates_iso_timestamp(self):
        response = self.client.get("/api/analytics/overview")
        data = response.get_json()
        self.assertIn("generated_at", data)
        self.assertIn("T", data["generated_at"])


if __name__ == "__main__":
    unittest.main()