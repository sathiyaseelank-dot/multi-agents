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


class AnalyticsErrorResponseFormatTestCase(unittest.TestCase):
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

    def test_validation_error_response_format(self):
        response = self.client.get("/api/analytics/metrics/active-users?period=yearly")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)
        self.assertIn("code", data["error"])
        self.assertIn("message", data["error"])
        self.assertIn("timestamp", data["error"])
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    def test_validation_error_includes_field_errors(self):
        response = self.client.get("/api/analytics/metrics/active-users?period=yearly")
        data = response.get_json()
        self.assertIn("field_errors", data["error"])
        self.assertEqual(len(data["error"]["field_errors"]), 1)
        self.assertEqual(data["error"]["field_errors"][0]["field"], "period")

    def test_days_out_of_range_error_format(self):
        response = self.client.get("/api/analytics/charts/messages_per_day?days=0")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    def test_limit_out_of_range_error_format(self):
        response = self.client.get("/api/analytics/top-users?limit=0")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    def test_invalid_chart_type_error_format(self):
        response = self.client.get("/api/analytics/charts/invalid_chart")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    def test_successful_response_no_error_key(self):
        response = self.client.get("/api/analytics/metrics/users")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertNotIn("error", data)


class AnalyticsErrorResponseConsistencyTestCase(unittest.TestCase):
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

    def test_all_validation_errors_have_timestamp(self):
        test_cases = [
            "/api/analytics/metrics/active-users?period=yearly",
            "/api/analytics/charts/messages_per_day?days=0",
            "/api/analytics/top-users?limit=0",
            "/api/analytics/charts/invalid_type",
        ]
        for endpoint in test_cases:
            response = self.client.get(endpoint)
            data = response.get_json()
            self.assertIn("timestamp", data["error"], f"Missing timestamp for {endpoint}")

    def test_all_validation_errors_have_code(self):
        test_cases = [
            "/api/analytics/metrics/active-users?period=yearly",
            "/api/analytics/charts/messages_per_day?days=0",
            "/api/analytics/top-users?limit=0",
        ]
        for endpoint in test_cases:
            response = self.client.get(endpoint)
            data = response.get_json()
            self.assertIn("code", data["error"], f"Missing code for {endpoint}")

    def test_error_response_content_type(self):
        response = self.client.get("/api/analytics/metrics/active-users?period=yearly")
        self.assertEqual(response.content_type, "application/json")


class AnalyticsMalformedDataHandlingTestCase(unittest.TestCase):
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


class AnalyticsErrorRecoveryTestCase(unittest.TestCase):
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

    def test_recovery_after_validation_error(self):
        response1 = self.client.get("/api/analytics/metrics/active-users?period=yearly")
        self.assertEqual(response1.status_code, 400)

        response2 = self.client.get("/api/analytics/metrics/users")
        self.assertEqual(response2.status_code, 200)
        data = response2.get_json()
        self.assertIn("value", data)

    def test_recovery_after_invalid_days(self):
        response1 = self.client.get("/api/analytics/charts/messages_per_day?days=0")
        self.assertEqual(response1.status_code, 400)

        response2 = self.client.get("/api/analytics/charts/messages_per_day?days=7")
        self.assertEqual(response2.status_code, 200)


class AnalyticsInputEdgeCasesTestCase(unittest.TestCase):
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

    def test_empty_string_period(self):
        response = self.client.get("/api/analytics/metrics/active-users?period=")
        self.assertEqual(response.status_code, 400)

    def test_non_numeric_days(self):
        response = self.client.get("/api/analytics/charts/messages_per_day?days=abc")
        self.assertEqual(response.status_code, 200)

    def test_non_numeric_limit(self):
        response = self.client.get("/api/analytics/top-users?limit=xyz")
        self.assertEqual(response.status_code, 200)

    def test_boundary_values_for_days(self):
        response1 = self.client.get("/api/analytics/charts/messages_per_day?days=1")
        self.assertEqual(response1.status_code, 200)

        response2 = self.client.get("/api/analytics/charts/messages_per_day?days=365")
        self.assertEqual(response2.status_code, 200)

    def test_boundary_values_for_limit(self):
        response1 = self.client.get("/api/analytics/top-users?limit=1")
        self.assertEqual(response1.status_code, 200)

        response2 = self.client.get("/api/analytics/top-users?limit=100")
        self.assertEqual(response2.status_code, 200)


if __name__ == "__main__":
    unittest.main()
