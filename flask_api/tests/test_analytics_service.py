import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

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
from services.analytics import AnalyticsService, ChartDataPoint, DashboardMetric


class ChartDataPointTestCase(unittest.TestCase):
    def test_to_dict_basic(self):
        dp = ChartDataPoint(label="2026-03-27", value=42)
        result = dp.to_dict()
        self.assertEqual(result["label"], "2026-03-27")
        self.assertEqual(result["value"], 42)
        self.assertNotIn("metadata", result)

    def test_to_dict_with_metadata(self):
        dp = ChartDataPoint(label="text", value=10, metadata={"percentage": 50.0})
        result = dp.to_dict()
        self.assertEqual(result["label"], "text")
        self.assertEqual(result["value"], 10)
        self.assertEqual(result["metadata"], {"percentage": 50.0})

    def test_to_dict_with_none_metadata(self):
        dp = ChartDataPoint(label="x", value=1, metadata=None)
        result = dp.to_dict()
        self.assertNotIn("metadata", result)

    def test_to_dict_with_empty_metadata(self):
        dp = ChartDataPoint(label="x", value=1, metadata={})
        result = dp.to_dict()
        self.assertNotIn("metadata", result)

    def test_zero_value(self):
        dp = ChartDataPoint(label="empty", value=0)
        result = dp.to_dict()
        self.assertEqual(result["value"], 0)

    def test_negative_value(self):
        dp = ChartDataPoint(label="neg", value=-5.5)
        result = dp.to_dict()
        self.assertEqual(result["value"], -5.5)

    def test_float_value(self):
        dp = ChartDataPoint(label="float", value=3.14159)
        result = dp.to_dict()
        self.assertAlmostEqual(result["value"], 3.14159)


class DashboardMetricTestCase(unittest.TestCase):
    def test_to_dict_basic(self):
        dm = DashboardMetric(id="total_users", label="Total Users", value=100)
        result = dm.to_dict()
        self.assertEqual(result["id"], "total_users")
        self.assertEqual(result["label"], "Total Users")
        self.assertEqual(result["value"], 100)
        self.assertIsNone(result["unit"])
        self.assertNotIn("change", result)
        self.assertNotIn("trend", result)

    def test_to_dict_with_change_up(self):
        dm = DashboardMetric(
            id="total_users", label="Total Users", value=150,
            change=50.0, change_direction="up"
        )
        result = dm.to_dict()
        self.assertEqual(result["change"], 50.0)
        self.assertEqual(result["change_direction"], "up")

    def test_to_dict_with_change_down(self):
        dm = DashboardMetric(
            id="total_messages", label="Total Messages", value=80,
            change=-20.0, change_direction="down"
        )
        result = dm.to_dict()
        self.assertEqual(result["change"], -20.0)
        self.assertEqual(result["change_direction"], "down")

    def test_to_dict_with_trend(self):
        dm = DashboardMetric(
            id="users", label="Users", value=10,
            trend=[1.0, 2.0, 3.0, 4.0, 5.0]
        )
        result = dm.to_dict()
        self.assertEqual(result["trend"], [1.0, 2.0, 3.0, 4.0, 5.0])

    def test_to_dict_with_unit(self):
        dm = DashboardMetric(id="rate", label="Rate", value=75.5, unit="%")
        result = dm.to_dict()
        self.assertEqual(result["unit"], "%")

    def test_to_dict_change_zero_not_omitted(self):
        dm = DashboardMetric(
            id="x", label="X", value=10, change=0.0, change_direction="up"
        )
        result = dm.to_dict()
        self.assertIn("change", result)
        self.assertEqual(result["change"], 0.0)

    def test_to_dict_empty_trend_omitted(self):
        dm = DashboardMetric(id="x", label="X", value=10, trend=[])
        result = dm.to_dict()
        self.assertNotIn("trend", result)


class AnalyticsServiceDateRangeTestCase(unittest.TestCase):
    def test_daily_range(self):
        start, end = AnalyticsService._get_date_range("daily")
        delta = end - start
        self.assertAlmostEqual(delta.days, 7, delta=1)

    def test_weekly_range(self):
        start, end = AnalyticsService._get_date_range("weekly")
        delta = end - start
        self.assertAlmostEqual(delta.days, 28, delta=1)

    def test_monthly_range(self):
        start, end = AnalyticsService._get_date_range("monthly")
        delta = end - start
        self.assertAlmostEqual(delta.days, 365, delta=1)

    def test_unknown_period_defaults_to_daily(self):
        start, end = AnalyticsService._get_date_range("unknown")
        delta = end - start
        self.assertAlmostEqual(delta.days, 7, delta=1)

    def test_empty_string_defaults_to_daily(self):
        start, end = AnalyticsService._get_date_range("")
        delta = end - start
        self.assertAlmostEqual(delta.days, 7, delta=1)

    def test_format_date(self):
        dt = datetime(2026, 3, 27, 14, 30, 0)
        result = AnalyticsService._format_date(dt)
        self.assertEqual(result, "2026-03-27")

    def test_format_date_single_digit(self):
        dt = datetime(2026, 1, 5, 0, 0, 0)
        result = AnalyticsService._format_date(dt)
        self.assertEqual(result, "2026-01-05")


class AnalyticsServiceEmptyDBTestCase(unittest.TestCase):
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

    def test_total_users_empty_db(self):
        with self.app.app_context():
            metric = AnalyticsService.get_total_users()
            self.assertEqual(metric.value, 0)
            self.assertIsNone(metric.change)
            self.assertIsNone(metric.change_direction)

    def test_total_messages_empty_db(self):
        with self.app.app_context():
            metric = AnalyticsService.get_total_messages()
            self.assertEqual(metric.value, 0)
            self.assertIsNone(metric.change)

    def test_total_conversations_empty_db(self):
        with self.app.app_context():
            metric = AnalyticsService.get_total_conversations()
            self.assertEqual(metric.value, 0)
            self.assertIsNone(metric.change)

    def test_active_users_empty_db(self):
        with self.app.app_context():
            metric = AnalyticsService.get_active_users_count("daily")
            self.assertEqual(metric.value, 0)

    def test_messages_per_day_empty_db(self):
        with self.app.app_context():
            result = AnalyticsService.get_messages_per_day(days=7)
            self.assertIsInstance(result, list)
            self.assertTrue(all(dp.value == 0 for dp in result))
            self.assertEqual(len(result), 8)

    def test_users_per_day_empty_db(self):
        with self.app.app_context():
            result = AnalyticsService.get_users_per_day(days=7)
            self.assertIsInstance(result, list)
            self.assertTrue(all(dp.value == 0 for dp in result))

    def test_conversations_per_day_empty_db(self):
        with self.app.app_context():
            result = AnalyticsService.get_conversations_per_day(days=7)
            self.assertIsInstance(result, list)
            self.assertTrue(all(dp.value == 0 for dp in result))

    def test_messages_by_hour_empty_db(self):
        with self.app.app_context():
            result = AnalyticsService.get_messages_by_hour(days=7)
            self.assertEqual(len(result), 24)
            self.assertTrue(all(dp.value == 0 for dp in result))
            self.assertEqual(result[0].label, "00:00")
            self.assertEqual(result[23].label, "23:00")

    def test_top_active_users_empty_db(self):
        with self.app.app_context():
            result = AnalyticsService.get_top_active_users(limit=10)
            self.assertEqual(result, [])

    def test_top_conversations_empty_db(self):
        with self.app.app_context():
            result = AnalyticsService.get_top_conversations(limit=10)
            self.assertEqual(result, [])

    def test_message_type_distribution_empty_db(self):
        with self.app.app_context():
            result = AnalyticsService.get_message_type_distribution()
            self.assertEqual(result, [])

    def test_engagement_metrics_empty_db(self):
        with self.app.app_context():
            result = AnalyticsService.get_engagement_metrics()
            self.assertEqual(result["total_users"], 0)
            self.assertEqual(result["avg_messages_per_user"], 0)
            self.assertEqual(result["active_users_7d"], 0)
            self.assertEqual(result["engagement_rate"], 0)

    def test_dashboard_overview_empty_db(self):
        with self.app.app_context():
            result = AnalyticsService.get_dashboard_overview()
            self.assertIn("metrics", result)
            self.assertIn("generated_at", result)
            self.assertEqual(len(result["metrics"]), 4)

    def test_all_analytics_empty_db(self):
        with self.app.app_context():
            result = AnalyticsService.get_all_analytics()
            self.assertIn("overview", result)
            self.assertIn("charts", result)
            self.assertIn("top_lists", result)
            self.assertIn("engagement", result)
            self.assertIn("generated_at", result)


class AnalyticsServiceWithDataTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
            db = database.get_db()
            for i in range(5):
                db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (f"user{i}", f"user{i}@test.com", "hash"),
                )
            db.execute(
                "INSERT INTO conversations (name, is_group) VALUES (?, ?)", ("conv1", 0)
            )
            db.execute(
                "INSERT INTO conversations (name, is_group) VALUES (?, ?)", ("group1", 1)
            )
            for i in range(10):
                db.execute(
                    "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                    (1, (i % 5) + 1, f"Message {i}", "text"),
                )
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                (1, 1, "Image", "image"),
            )
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                (2, 2, "File", "file"),
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

    def test_total_users_returns_five(self):
        with self.app.app_context():
            metric = AnalyticsService.get_total_users()
            self.assertEqual(metric.value, 5)
            self.assertEqual(metric.id, "total_users")
            self.assertEqual(metric.label, "Total Users")

    def test_total_messages_returns_twelve(self):
        with self.app.app_context():
            metric = AnalyticsService.get_total_messages()
            self.assertEqual(metric.value, 12)

    def test_total_conversations_returns_two(self):
        with self.app.app_context():
            metric = AnalyticsService.get_total_conversations()
            self.assertEqual(metric.value, 2)

    def test_total_users_change_none_when_no_history(self):
        with self.app.app_context():
            metric = AnalyticsService.get_total_users()
            self.assertIsNotNone(metric.value)
            self.assertIn(metric.change_direction, ("up", "down", None))

    def test_active_users_daily(self):
        with self.app.app_context():
            metric = AnalyticsService.get_active_users_count("daily")
            self.assertEqual(metric.id, "active_users_daily")
            self.assertGreaterEqual(metric.value, 0)

    def test_active_users_weekly(self):
        with self.app.app_context():
            metric = AnalyticsService.get_active_users_count("weekly")
            self.assertEqual(metric.id, "active_users_weekly")

    def test_active_users_monthly(self):
        with self.app.app_context():
            metric = AnalyticsService.get_active_users_count("monthly")
            self.assertEqual(metric.id, "active_users_monthly")

    def test_messages_per_day_returns_correct_length(self):
        with self.app.app_context():
            result = AnalyticsService.get_messages_per_day(days=7)
            self.assertEqual(len(result), 8)
            for dp in result:
                self.assertIsInstance(dp, ChartDataPoint)
                self.assertRegex(dp.label, r"^\d{4}-\d{2}-\d{2}$")

    def test_messages_per_day_values_sum_to_total(self):
        with self.app.app_context():
            result = AnalyticsService.get_messages_per_day(days=7)
            total = sum(dp.value for dp in result)
            self.assertEqual(total, 12)

    def test_users_per_day_values_sum_to_total(self):
        with self.app.app_context():
            result = AnalyticsService.get_users_per_day(days=7)
            total = sum(dp.value for dp in result)
            self.assertEqual(total, 5)

    def test_conversations_per_day_values_sum_to_total(self):
        with self.app.app_context():
            result = AnalyticsService.get_conversations_per_day(days=7)
            total = sum(dp.value for dp in result)
            self.assertEqual(total, 2)

    def test_messages_by_hour_returns_24_entries(self):
        with self.app.app_context():
            result = AnalyticsService.get_messages_by_hour(days=7)
            self.assertEqual(len(result), 24)
            for i, dp in enumerate(result):
                self.assertEqual(dp.label, f"{i:02d}:00")

    def test_messages_by_hour_values_sum_to_total(self):
        with self.app.app_context():
            result = AnalyticsService.get_messages_by_hour(days=7)
            total = sum(dp.value for dp in result)
            self.assertEqual(total, 12)

    def test_top_active_users_ordered_by_message_count(self):
        with self.app.app_context():
            result = AnalyticsService.get_top_active_users(limit=5)
            self.assertEqual(len(result), 5)
            counts = [u["message_count"] for u in result]
            self.assertEqual(counts, sorted(counts, reverse=True))

    def test_top_active_users_fields(self):
        with self.app.app_context():
            result = AnalyticsService.get_top_active_users(limit=1)
            self.assertEqual(len(result), 1)
            user = result[0]
            self.assertIn("id", user)
            self.assertIn("username", user)
            self.assertIn("email", user)
            self.assertIn("message_count", user)
            self.assertIn("last_activity", user)

    def test_top_active_users_limit(self):
        with self.app.app_context():
            result = AnalyticsService.get_top_active_users(limit=3)
            self.assertEqual(len(result), 3)

    def test_top_active_users_limit_larger_than_data(self):
        with self.app.app_context():
            result = AnalyticsService.get_top_active_users(limit=100)
            self.assertEqual(len(result), 5)

    def test_top_conversations_ordered_by_message_count(self):
        with self.app.app_context():
            result = AnalyticsService.get_top_conversations(limit=2)
            self.assertEqual(len(result), 2)
            counts = [c["message_count"] for c in result]
            self.assertEqual(counts, sorted(counts, reverse=True))

    def test_top_conversations_fields(self):
        with self.app.app_context():
            result = AnalyticsService.get_top_conversations(limit=1)
            conv = result[0]
            self.assertIn("id", conv)
            self.assertIn("name", conv)
            self.assertIn("is_group", conv)
            self.assertIn("participant_count", conv)
            self.assertIn("message_count", conv)
            self.assertIn("last_message", conv)

    def test_top_conversations_is_group_is_bool(self):
        with self.app.app_context():
            result = AnalyticsService.get_top_conversations(limit=2)
            for conv in result:
                self.assertIsInstance(conv["is_group"], bool)

    def test_message_type_distribution(self):
        with self.app.app_context():
            result = AnalyticsService.get_message_type_distribution()
            types = {dp.label for dp in result}
            self.assertIn("text", types)
            self.assertIn("image", types)
            self.assertIn("file", types)

    def test_message_type_distribution_percentages_sum_to_100(self):
        with self.app.app_context():
            result = AnalyticsService.get_message_type_distribution()
            total_pct = sum(dp.metadata["percentage"] for dp in result)
            self.assertAlmostEqual(total_pct, 100.0, places=1)

    def test_message_type_distribution_metadata_has_percentage(self):
        with self.app.app_context():
            result = AnalyticsService.get_message_type_distribution()
            for dp in result:
                self.assertIn("metadata", dp.to_dict())
                self.assertIn("percentage", dp.metadata)

    def test_engagement_metrics_with_data(self):
        with self.app.app_context():
            result = AnalyticsService.get_engagement_metrics()
            self.assertEqual(result["total_users"], 5)
            self.assertAlmostEqual(
                result["avg_messages_per_user"], 12 / 5, places=2
            )
            self.assertGreaterEqual(result["engagement_rate"], 0)
            self.assertLessEqual(result["engagement_rate"], 100)

    def test_get_chart_data_messages_per_day(self):
        with self.app.app_context():
            result = AnalyticsService.get_chart_data("messages_per_day", days=7)
            self.assertEqual(result["chart_type"], "messages_per_day")
            self.assertIn("data", result)
            self.assertIn("generated_at", result)
            self.assertIsInstance(result["data"], list)

    def test_get_chart_data_unknown_type(self):
        with self.app.app_context():
            result = AnalyticsService.get_chart_data("nonexistent")
            self.assertIn("error", result)
            self.assertIn("Unknown chart type", result["error"])

    def test_get_all_analytics_structure(self):
        with self.app.app_context():
            result = AnalyticsService.get_all_analytics()
            self.assertIn("overview", result)
            self.assertIn("charts", result)
            self.assertIn("top_lists", result)
            self.assertIn("engagement", result)
            self.assertEqual(
                len(result["charts"]["messages_per_day"]), 31
            )


class AnalyticsServiceAggregationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
            db = database.get_db()
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("sender1", "s1@test.com", "hash"),
            )
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("sender2", "s2@test.com", "hash"),
            )
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("inactive", "inactive@test.com", "hash"),
            )
            db.execute(
                "INSERT INTO conversations (name, is_group) VALUES (?, ?)", ("dm", 0)
            )
            db.execute(
                "INSERT INTO conversations (name, is_group) VALUES (?, ?)", ("group", 1)
            )
            db.execute(
                "INSERT INTO conversation_participants (conversation_id, user_id) VALUES (?, ?)",
                (1, 1),
            )
            db.execute(
                "INSERT INTO conversation_participants (conversation_id, user_id) VALUES (?, ?)",
                (1, 2),
            )
            db.execute(
                "INSERT INTO conversation_participants (conversation_id, user_id) VALUES (?, ?)",
                (2, 1),
            )
            for _ in range(20):
                db.execute(
                    "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                    (1, 1, "msg", "text"),
                )
            for _ in range(5):
                db.execute(
                    "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                    (2, 2, "msg", "text"),
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

    def test_top_users_reflects_message_counts(self):
        with self.app.app_context():
            result = AnalyticsService.get_top_active_users(limit=3)
            self.assertEqual(result[0]["message_count"], 20)
            self.assertEqual(result[1]["message_count"], 5)
            self.assertEqual(result[2]["message_count"], 0)

    def test_top_conversations_reflects_message_counts(self):
        with self.app.app_context():
            result = AnalyticsService.get_top_conversations(limit=2)
            counts = [c["message_count"] for c in result]
            self.assertEqual(counts, sorted(counts, reverse=True))
            self.assertGreater(counts[0], 0)

    def test_top_conversations_reflects_participant_counts(self):
        with self.app.app_context():
            result = AnalyticsService.get_top_conversations(limit=2)
            conv1 = result[0]
            conv2 = result[1]
            self.assertEqual(conv1["participant_count"], 2)
            self.assertEqual(conv2["participant_count"], 1)

    def test_engagement_rate_with_active_users(self):
        with self.app.app_context():
            result = AnalyticsService.get_engagement_metrics()
            self.assertEqual(result["total_users"], 3)
            self.assertGreater(result["active_users_7d"], 0)
            self.assertGreater(result["engagement_rate"], 0)

    def test_avg_messages_per_user(self):
        with self.app.app_context():
            result = AnalyticsService.get_engagement_metrics()
            self.assertAlmostEqual(
                result["avg_messages_per_user"], 25 / 3, places=2
            )


class AnalyticsServiceChartAggregationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
            db = database.get_db()
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("u1", "u1@test.com", "hash"),
            )
            db.execute(
                "INSERT INTO conversations (name, is_group) VALUES (?, ?)", ("c1", 0)
            )
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                (1, 1, "t1", "text"),
            )
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                (1, 1, "t2", "text"),
            )
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                (1, 1, "img", "image"),
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

    def test_chart_data_points_contiguous_dates(self):
        with self.app.app_context():
            result = AnalyticsService.get_messages_per_day(days=7)
            dates = [dp.label for dp in result]
            for i in range(1, len(dates)):
                d1 = datetime.strptime(dates[i - 1], "%Y-%m-%d")
                d2 = datetime.strptime(dates[i], "%Y-%m-%d")
                self.assertEqual((d2 - d1).days, 1)

    def test_chart_data_points_contiguous_hours(self):
        with self.app.app_context():
            result = AnalyticsService.get_messages_by_hour(days=7)
            for i in range(24):
                self.assertEqual(result[i].label, f"{i:02d}:00")

    def test_messages_per_day_custom_days_30(self):
        with self.app.app_context():
            result = AnalyticsService.get_messages_per_day(days=30)
            self.assertEqual(len(result), 31)

    def test_messages_per_day_custom_days_1(self):
        with self.app.app_context():
            result = AnalyticsService.get_messages_per_day(days=1)
            self.assertEqual(len(result), 2)

    def test_chart_data_serializable(self):
        with self.app.app_context():
            result = AnalyticsService.get_chart_data("messages_per_day", days=7)
            for dp in result["data"]:
                self.assertIn("label", dp)
                self.assertIn("value", dp)
                self.assertIsInstance(dp["label"], str)
                self.assertIsInstance(dp["value"], (int, float))

    def test_all_chart_types_valid(self):
        chart_types_without_days = [
            "messages_per_day",
            "users_per_day",
            "conversations_per_day",
            "messages_by_hour",
        ]
        with self.app.app_context():
            for ct in chart_types_without_days:
                result = AnalyticsService.get_chart_data(ct, days=7)
                self.assertEqual(result["chart_type"], ct)
                self.assertIn("data", result)
                self.assertIn("generated_at", result)

    def test_message_type_distribution_chart_raises_type_error(self):
        with self.app.app_context():
            result = AnalyticsService.get_chart_data("message_type_distribution", days=7)
            self.assertIn("data", result)
            self.assertIsInstance(result["data"], list)


class AnalyticsRouteErrorHandlingTestCase(unittest.TestCase):
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

    def test_overview_returns_500_on_db_error(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DROP TABLE IF EXISTS users")
            db.commit()
        response = self.client.get("/api/analytics/overview")
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())

    def test_metrics_users_returns_500_on_db_error(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DROP TABLE IF EXISTS users")
            db.commit()
        response = self.client.get("/api/analytics/metrics/users")
        self.assertEqual(response.status_code, 500)

    def test_metrics_messages_returns_500_on_db_error(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DROP TABLE IF EXISTS messages")
            db.commit()
        response = self.client.get("/api/analytics/metrics/messages")
        self.assertEqual(response.status_code, 500)

    def test_charts_returns_500_on_db_error(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DROP TABLE IF EXISTS messages")
            db.commit()
        response = self.client.get("/api/analytics/charts/messages_per_day")
        self.assertEqual(response.status_code, 500)

    def test_top_users_returns_500_on_db_error(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DROP TABLE IF EXISTS users")
            db.commit()
        response = self.client.get("/api/analytics/top-users")
        self.assertEqual(response.status_code, 500)

    def test_engagement_returns_500_on_db_error(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DROP TABLE IF EXISTS users")
            db.commit()
        response = self.client.get("/api/analytics/engagement")
        self.assertEqual(response.status_code, 500)

    def test_all_returns_500_on_db_error(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DROP TABLE IF EXISTS users")
            db.commit()
        response = self.client.get("/api/analytics/all")
        self.assertEqual(response.status_code, 500)


class AnalyticsRouteValidationTestCase(unittest.TestCase):
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

    def test_active_users_period_daily(self):
        response = self.client.get("/api/analytics/metrics/active-users?period=daily")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["id"], "active_users_daily")

    def test_active_users_period_weekly(self):
        response = self.client.get("/api/analytics/metrics/active-users?period=weekly")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["id"], "active_users_weekly")

    def test_active_users_period_monthly(self):
        response = self.client.get("/api/analytics/metrics/active-users?period=monthly")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["id"], "active_users_monthly")

    def test_active_users_invalid_period(self):
        response = self.client.get("/api/analytics/metrics/active-users?period=yearly")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_chart_days_boundary_1(self):
        response = self.client.get("/api/analytics/charts/messages_per_day?days=1")
        self.assertEqual(response.status_code, 200)

    def test_chart_days_boundary_365(self):
        response = self.client.get("/api/analytics/charts/messages_per_day?days=365")
        self.assertEqual(response.status_code, 200)

    def test_chart_days_zero_rejected(self):
        response = self.client.get("/api/analytics/charts/messages_per_day?days=0")
        self.assertEqual(response.status_code, 400)

    def test_chart_days_negative_rejected(self):
        response = self.client.get("/api/analytics/charts/messages_per_day?days=-1")
        self.assertEqual(response.status_code, 400)

    def test_chart_days_over_365_rejected(self):
        response = self.client.get("/api/analytics/charts/messages_per_day?days=366")
        self.assertEqual(response.status_code, 400)

    def test_top_users_limit_boundary_1(self):
        response = self.client.get("/api/analytics/top-users?limit=1")
        self.assertEqual(response.status_code, 200)

    def test_top_users_limit_boundary_100(self):
        response = self.client.get("/api/analytics/top-users?limit=100")
        self.assertEqual(response.status_code, 200)

    def test_top_users_limit_zero_rejected(self):
        response = self.client.get("/api/analytics/top-users?limit=0")
        self.assertEqual(response.status_code, 400)

    def test_top_users_limit_over_100_rejected(self):
        response = self.client.get("/api/analytics/top-users?limit=101")
        self.assertEqual(response.status_code, 400)

    def test_top_conversations_limit_boundary_1(self):
        response = self.client.get("/api/analytics/top-conversations?limit=1")
        self.assertEqual(response.status_code, 200)

    def test_top_conversations_limit_zero_rejected(self):
        response = self.client.get("/api/analytics/top-conversations?limit=0")
        self.assertEqual(response.status_code, 400)

    def test_top_conversations_limit_over_100_rejected(self):
        response = self.client.get("/api/analytics/top-conversations?limit=101")
        self.assertEqual(response.status_code, 400)

    def test_invalid_chart_type_returns_400(self):
        response = self.client.get("/api/analytics/charts/invalid_chart")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_invalid_metric_returns_404(self):
        response = self.client.get("/api/analytics/metrics/nonexistent")
        self.assertEqual(response.status_code, 404)


class AnalyticsRouteIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
            db = database.get_db()
            for i in range(3):
                db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (f"intuser{i}", f"int{i}@test.com", "hash"),
                )
            db.execute(
                "INSERT INTO conversations (name, is_group) VALUES (?, ?)", ("IntConv", 1)
            )
            for i in range(3):
                db.execute(
                    "INSERT INTO conversation_participants (conversation_id, user_id) VALUES (?, ?)",
                    (1, i + 1),
                )
            for i in range(8):
                db.execute(
                    "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                    (1, (i % 3) + 1, f"msg {i}", "text"),
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

    def test_overview_reflects_data(self):
        response = self.client.get("/api/analytics/overview")
        data = response.get_json()
        user_metric = next(m for m in data["metrics"] if m["id"] == "total_users")
        self.assertEqual(user_metric["value"], 3)
        msg_metric = next(m for m in data["metrics"] if m["id"] == "total_messages")
        self.assertEqual(msg_metric["value"], 8)

    def test_all_endpoint_returns_complete_data(self):
        response = self.client.get("/api/analytics/all")
        data = response.get_json()
        self.assertEqual(
            data["overview"]["metrics"][0]["value"], 3
        )
        self.assertEqual(
            len(data["charts"]["messages_per_day"]), 31
        )
        self.assertIsInstance(data["top_lists"]["active_users"], list)
        self.assertEqual(data["engagement"]["total_users"], 3)

    def test_chart_data_matches_service(self):
        response = self.client.get("/api/analytics/charts/messages_per_day?days=7")
        data = response.get_json()
        self.assertEqual(data["chart_type"], "messages_per_day")
        total = sum(dp["value"] for dp in data["data"])
        self.assertEqual(total, 8)

    def test_top_users_returns_correct_count_order(self):
        response = self.client.get("/api/analytics/top-users?limit=3")
        data = response.get_json()
        users = data["users"]
        self.assertEqual(len(users), 3)
        counts = [u["message_count"] for u in users]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_engagement_metrics_consistency(self):
        response = self.client.get("/api/analytics/engagement")
        data = response.get_json()
        self.assertEqual(data["total_users"], 3)
        self.assertAlmostEqual(data["avg_messages_per_user"], 8 / 3, places=2)
        self.assertLessEqual(data["engagement_rate"], 100)

    def test_messages_by_hour_aggregates_correctly(self):
        response = self.client.get("/api/analytics/charts/messages_by_hour?days=7")
        data = response.get_json()
        total = sum(dp["value"] for dp in data["data"])
        self.assertEqual(total, 8)
        self.assertEqual(len(data["data"]), 24)

    def test_message_type_distribution_single_type(self):
        response = self.client.get("/api/analytics/charts/message_type_distribution")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("data", data)
        self.assertEqual(len(data["data"]), 1)


class AnalyticsServiceNormalizedOutputTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
            db = database.get_db()
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("norm", "norm@test.com", "hash"),
            )
            db.execute(
                "INSERT INTO conversations (name, is_group) VALUES (?, ?)", ("c", 0)
            )
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                (1, 1, "hello", "text"),
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

    def test_overview_response_schema(self):
        response = self.client.get("/api/analytics/overview")
        data = response.get_json()
        self.assertIsInstance(data["metrics"], list)
        self.assertIsInstance(data["generated_at"], str)
        for metric in data["metrics"]:
            self.assertIn("id", metric)
            self.assertIn("label", metric)
            self.assertIn("value", metric)
            self.assertIn("unit", metric)

    def test_metric_response_schema(self):
        response = self.client.get("/api/analytics/metrics/users")
        data = response.get_json()
        self.assertIn("id", data)
        self.assertIn("label", data)
        self.assertIn("value", data)
        self.assertIn("unit", data)

    def test_chart_response_schema(self):
        response = self.client.get("/api/analytics/charts/messages_per_day")
        data = response.get_json()
        self.assertIn("chart_type", data)
        self.assertIn("data", data)
        self.assertIn("generated_at", data)
        self.assertIsInstance(data["data"], list)
        for point in data["data"]:
            self.assertIn("label", point)
            self.assertIn("value", point)

    def test_top_users_response_schema(self):
        response = self.client.get("/api/analytics/top-users")
        data = response.get_json()
        self.assertIn("users", data)
        self.assertIsInstance(data["users"], list)
        for user in data["users"]:
            self.assertIn("id", user)
            self.assertIn("username", user)
            self.assertIn("email", user)
            self.assertIn("message_count", user)
            self.assertIn("last_activity", user)

    def test_top_conversations_response_schema(self):
        response = self.client.get("/api/analytics/top-conversations")
        data = response.get_json()
        self.assertIn("conversations", data)
        self.assertIsInstance(data["conversations"], list)
        for conv in data["conversations"]:
            self.assertIn("id", conv)
            self.assertIn("name", conv)
            self.assertIn("is_group", conv)
            self.assertIn("participant_count", conv)
            self.assertIn("message_count", conv)
            self.assertIn("last_message", conv)

    def test_engagement_response_schema(self):
        response = self.client.get("/api/analytics/engagement")
        data = response.get_json()
        self.assertIn("avg_messages_per_user", data)
        self.assertIn("active_users_7d", data)
        self.assertIn("engagement_rate", data)
        self.assertIn("total_users", data)
        self.assertIsInstance(data["avg_messages_per_user"], (int, float))
        self.assertIsInstance(data["active_users_7d"], int)
        self.assertIsInstance(data["engagement_rate"], (int, float))
        self.assertIsInstance(data["total_users"], int)

    def test_all_response_schema(self):
        response = self.client.get("/api/analytics/all")
        data = response.get_json()
        self.assertIn("overview", data)
        self.assertIn("charts", data)
        self.assertIn("top_lists", data)
        self.assertIn("engagement", data)
        self.assertIn("generated_at", data)
        self.assertIsInstance(data["charts"], dict)
        self.assertIsInstance(data["top_lists"], dict)

    def test_generated_at_is_iso_format(self):
        response = self.client.get("/api/analytics/overview")
        data = response.get_json()
        ts = data["generated_at"]
        self.assertIn("T", ts)
        datetime.fromisoformat(ts)


if __name__ == "__main__":
    unittest.main()
