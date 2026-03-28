"""Tests for analytics backend module."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import (
    ChartDataPoint,
    DashboardMetric,
    UserSummary,
    ConversationSummary,
    EngagementMetrics,
    DashboardOverview,
    ChartData,
)
from backend.validators import (
    validate_period,
    validate_days,
    validate_limit,
    validate_chart_type,
    sanitize_string,
    validate_positive_number,
)
from backend.errors import (
    AnalyticsValidationError,
    DataSourceError,
    MalformedDataError,
    ErrorResponse,
    validation_error_response,
    data_source_error_response,
    malformed_data_error_response,
    internal_error_response,
    ValidationError,
)
from backend.data_source import AnalyticsDataSource
from backend.service import AnalyticsService


class TestModels(unittest.TestCase):
    """Test data models."""

    def test_chart_data_point_to_dict(self):
        """Test ChartDataPoint serialization."""
        dp = ChartDataPoint(label="2024-01-01", value=42, metadata={"test": True})
        result = dp.to_dict()
        
        self.assertEqual(result["label"], "2024-01-01")
        self.assertEqual(result["value"], 42)
        self.assertEqual(result["metadata"]["test"], True)

    def test_chart_data_point_from_dict(self):
        """Test ChartDataPoint deserialization."""
        data = {"label": "2024-01-01", "value": 42}
        dp = ChartDataPoint.from_dict(data)
        
        self.assertEqual(dp.label, "2024-01-01")
        self.assertEqual(dp.value, 42.0)

    def test_dashboard_metric_to_dict(self):
        """Test DashboardMetric serialization."""
        metric = DashboardMetric(
            id="test_metric",
            label="Test Metric",
            value=100,
            change=10.5,
            change_direction="up",
            unit="%",
        )
        result = metric.to_dict()
        
        self.assertEqual(result["id"], "test_metric")
        self.assertEqual(result["value"], 100)
        self.assertEqual(result["change"], 10.5)
        self.assertEqual(result["change_direction"], "up")
        self.assertEqual(result["unit"], "%")

    def test_engagement_metrics_to_dict(self):
        """Test EngagementMetrics serialization."""
        metrics = EngagementMetrics(
            avg_messages_per_user=5.5,
            active_users_7d=100,
            engagement_rate=25.0,
            total_users=400,
        )
        result = metrics.to_dict()
        
        self.assertEqual(result["avg_messages_per_user"], 5.5)
        self.assertEqual(result["active_users_7d"], 100)
        self.assertEqual(result["engagement_rate"], 25.0)
        self.assertEqual(result["total_users"], 400)


class TestValidators(unittest.TestCase):
    """Test input validators."""

    def test_validate_period_valid(self):
        """Test valid period values."""
        for period in ["daily", "weekly", "monthly"]:
            valid, error = validate_period(period)
            self.assertTrue(valid)
            self.assertIsNone(error)

    def test_validate_period_invalid(self):
        """Test invalid period value."""
        valid, error = validate_period("invalid")
        self.assertFalse(valid)
        self.assertEqual(error.field, "period")
        self.assertEqual(error.code, "INVALID_PERIOD")

    def test_validate_period_none(self):
        """Test None period value."""
        valid, error = validate_period(None)
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_days_valid(self):
        """Test valid days values."""
        for days in [1, 7, 30, 365]:
            valid, error = validate_days(days)
            self.assertTrue(valid)
            self.assertIsNone(error)

    def test_validate_days_invalid_range(self):
        """Test days out of range."""
        valid, error = validate_days(400)
        self.assertFalse(valid)
        self.assertEqual(error.code, "OUT_OF_RANGE")

    def test_validate_days_invalid_type(self):
        """Test days with invalid type."""
        valid, error = validate_days("7")
        self.assertFalse(valid)
        self.assertEqual(error.code, "INVALID_TYPE")

    def test_validate_limit_valid(self):
        """Test valid limit values."""
        for limit in [1, 10, 50, 100]:
            valid, error = validate_limit(limit)
            self.assertTrue(valid)
            self.assertIsNone(error)

    def test_validate_limit_invalid_range(self):
        """Test limit out of range."""
        valid, error = validate_limit(200)
        self.assertFalse(valid)
        self.assertEqual(error.code, "OUT_OF_RANGE")

    def test_validate_chart_type_valid(self):
        """Test valid chart types."""
        valid_types = [
            "messages_per_day",
            "users_per_day",
            "conversations_per_day",
            "messages_by_hour",
            "message_type_distribution",
        ]
        for chart_type in valid_types:
            valid, error = validate_chart_type(chart_type)
            self.assertTrue(valid)
            self.assertIsNone(error)

    def test_validate_chart_type_invalid(self):
        """Test invalid chart type."""
        valid, error = validate_chart_type("invalid_chart")
        self.assertFalse(valid)
        self.assertEqual(error.code, "INVALID_CHART_TYPE")

    def test_sanitize_string_valid(self):
        """Test string sanitization."""
        result = sanitize_string("  test  ", "test_field")
        self.assertEqual(result, "test")

    def test_sanitize_string_empty(self):
        """Test empty string raises error."""
        with self.assertRaises(MalformedDataError):
            sanitize_string("   ", "test_field")

    def test_sanitize_string_none(self):
        """Test None raises error."""
        with self.assertRaises(MalformedDataError):
            sanitize_string(None, "test_field")

    def test_validate_positive_number_valid(self):
        """Test valid positive number."""
        result = validate_positive_number(42, "test_field")
        self.assertEqual(result, 42.0)

    def test_validate_positive_number_zero(self):
        """Test zero is valid."""
        result = validate_positive_number(0, "test_field")
        self.assertEqual(result, 0.0)

    def test_validate_positive_number_negative(self):
        """Test negative raises error."""
        with self.assertRaises(MalformedDataError):
            validate_positive_number(-1, "test_field")


class TestErrors(unittest.TestCase):
    """Test error handling."""

    def test_error_response_to_dict(self):
        """Test ErrorResponse serialization."""
        error = ErrorResponse(
            message="Test error",
            code="TEST_ERROR",
            status_code=400,
            details={"field": "test"},
            field_errors=[{"field": "name", "message": "Required"}],
        )
        result = error.to_dict()
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["message"], "Test error")
        self.assertEqual(result["error"]["code"], "TEST_ERROR")
        self.assertEqual(result["error"]["details"]["field"], "test")
        self.assertEqual(len(result["error"]["field_errors"]), 1)

    def test_validation_error_response(self):
        """Test validation error response factory."""
        response = validation_error_response(
            "Validation failed",
            field_errors=[{"field": "name", "message": "Required"}],
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.code, "VALIDATION_ERROR")

    def test_data_source_error_response(self):
        """Test data source error response factory."""
        response = data_source_error_response(
            "Database error",
            source="database",
        )
        
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.code, "DATA_SOURCE_ERROR")
        self.assertEqual(response.details["source"], "database")

    def test_malformed_data_error_response(self):
        """Test malformed data error response factory."""
        response = malformed_data_error_response(
            "Invalid data",
            details={"expected_type": "string"},
        )
        
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.code, "MALFORMED_DATA")

    def test_analytics_validation_error(self):
        """Test AnalyticsValidationError."""
        errors = [
            ValidationError("field1", "Error 1", "INVALID_FIELD"),
            ValidationError("field2", "Error 2", "INVALID_FIELD"),
        ]
        exc = AnalyticsValidationError(errors)
        
        self.assertEqual(len(exc.errors), 2)


class TestDataSource(unittest.TestCase):
    """Test data source layer."""

    @patch('backend.data_source.get_db')
    def test_get_total_users(self, mock_get_db):
        """Test getting total users."""
        mock_db = Mock()
        mock_db.execute.return_value.fetchone.return_value = {"count": 100}
        mock_get_db.return_value = mock_db
        
        ds = AnalyticsDataSource()
        result = ds.get_total_users()
        
        self.assertEqual(result, 100)
        mock_db.execute.assert_called_once()

    @patch('backend.data_source.get_db')
    def test_get_total_messages(self, mock_get_db):
        """Test getting total messages."""
        mock_db = Mock()
        mock_db.execute.return_value.fetchone.return_value = {"count": 500}
        mock_get_db.return_value = mock_db
        
        ds = AnalyticsDataSource()
        result = ds.get_total_messages()
        
        self.assertEqual(result, 500)

    @patch('backend.data_source.get_db')
    def test_get_messages_per_day(self, mock_get_db):
        """Test getting messages per day."""
        mock_db = Mock()
        mock_db.execute.return_value.fetchall.return_value = [
            {"date": "2024-01-01", "count": 10},
            {"date": "2024-01-02", "count": 20},
        ]
        mock_get_db.return_value = mock_db
        
        ds = AnalyticsDataSource()
        result = ds.get_messages_per_day(7)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["date"], "2024-01-01")

    @patch('backend.data_source.get_db')
    def test_data_source_error_handling(self, mock_get_db):
        """Test data source error handling."""
        mock_get_db.side_effect = Exception("Database error")
        
        ds = AnalyticsDataSource()
        
        with self.assertRaises(DataSourceError) as context:
            ds.get_total_users()
        
        self.assertEqual(context.exception.source, "database")


class TestAnalyticsService(unittest.TestCase):
    """Test analytics service layer."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_source = Mock(spec=AnalyticsDataSource)
        self.service = AnalyticsService(data_source=self.mock_data_source)

    def test_get_total_users(self):
        """Test getting total users metric."""
        self.mock_data_source.get_total_users.return_value = 100
        self.mock_data_source.get_users_before_date.return_value = 80
        self.mock_data_source.get_date_range.return_value = (
            datetime(2024, 1, 1),
            datetime(2024, 1, 8)
        )
        
        metric = self.service.get_total_users()
        
        self.assertEqual(metric.id, "total_users")
        self.assertEqual(metric.value, 100)
        self.assertEqual(metric.change, 25.0)
        self.assertEqual(metric.change_direction, "up")

    def test_get_total_users_no_previous(self):
        """Test getting total users with no previous data."""
        self.mock_data_source.get_total_users.return_value = 10
        self.mock_data_source.get_users_before_date.return_value = 0
        self.mock_data_source.get_date_range.return_value = (
            datetime(2024, 1, 1),
            datetime(2024, 1, 8)
        )
        
        metric = self.service.get_total_users()
        
        self.assertIsNone(metric.change)
        self.assertIsNone(metric.change_direction)

    def test_get_messages_per_day(self):
        """Test getting messages per day."""
        self.mock_data_source.get_messages_per_day.return_value = [
            {"date": "2024-01-01", "count": 10},
            {"date": "2024-01-02", "count": 20},
        ]
        
        with patch.object(self.service, '_fill_date_gaps') as mock_fill:
            mock_fill.return_value = [
                ChartDataPoint("2024-01-01", 10),
                ChartDataPoint("2024-01-02", 20),
            ]
            result = self.service.get_messages_per_day(7)
        
        self.assertEqual(len(result), 2)

    def test_get_chart_data_valid(self):
        """Test getting chart data for valid chart type."""
        self.mock_data_source.get_messages_per_day.return_value = [
            {"date": "2024-01-01", "count": 10},
        ]
        
        with patch.object(self.service, 'get_messages_per_day') as mock_method:
            mock_method.return_value = [ChartDataPoint("2024-01-01", 10)]
            result = self.service.get_chart_data("messages_per_day", days=7)
        
        self.assertIn("chart_type", result)
        self.assertIn("data", result)

    def test_get_chart_data_invalid(self):
        """Test getting chart data for invalid chart type."""
        result = self.service.get_chart_data("invalid_chart")
        
        self.assertIn("error", result)

    def test_get_engagement_metrics(self):
        """Test getting engagement metrics."""
        self.mock_data_source.get_engagement_metrics.return_value = {
            "avg_messages_per_user": 5.5,
            "active_users_7d": 100,
            "engagement_rate": 25.0,
            "total_users": 400,
        }
        
        metrics = self.service.get_engagement_metrics()
        
        self.assertEqual(metrics.avg_messages_per_user, 5.5)
        self.assertEqual(metrics.active_users_7d, 100)
        self.assertEqual(metrics.engagement_rate, 25.0)

    def test_get_dashboard_overview(self):
        """Test getting dashboard overview."""
        self.mock_data_source.get_total_users.return_value = 100
        self.mock_data_source.get_users_before_date.return_value = 80
        self.mock_data_source.get_total_messages.return_value = 500
        self.mock_data_source.get_messages_before_date.return_value = 400
        self.mock_data_source.get_total_conversations.return_value = 50
        self.mock_data_source.get_conversations_before_date.return_value = 40
        self.mock_data_source.get_active_users_count.return_value = 30
        self.mock_data_source.get_date_range.return_value = (
            datetime(2024, 1, 1),
            datetime(2024, 1, 8)
        )
        
        overview = self.service.get_dashboard_overview()
        
        self.assertEqual(len(overview.metrics), 4)


class TestRoutes(unittest.TestCase):
    """Test API routes."""

    def setUp(self):
        """Set up test fixtures."""
        from flask import Flask
        from backend.routes import bp
        self.app = Flask(__name__)
        self.app.register_blueprint(bp)
        self.client = self.app.test_client()

    @patch('backend.routes.AnalyticsService')
    def test_health_check_healthy(self, mock_service_class):
        """Test health check when healthy."""
        mock_service = Mock()
        mock_service.get_dashboard_overview.return_value = Mock()
        mock_service_class.return_value = mock_service
        
        response = self.client.get('/api/analytics/health')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "healthy")

    @patch('backend.routes.AnalyticsService')
    def test_health_check_unhealthy(self, mock_service_class):
        """Test health check when unhealthy."""
        mock_service_class.side_effect = Exception("Database error")
        
        response = self.client.get('/api/analytics/health')
        
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["status"], "unhealthy")

    @patch('backend.routes.AnalyticsService')
    def test_get_overview(self, mock_service_class):
        """Test overview endpoint."""
        mock_service = Mock()
        mock_service.get_dashboard_overview.return_value.to_dict.return_value = {
            "metrics": []
        }
        mock_service_class.return_value = mock_service
        
        response = self.client.get('/api/analytics/overview')
        
        self.assertEqual(response.status_code, 200)

    @patch('backend.routes.AnalyticsService')
    def test_get_chart_invalid_type(self, mock_service_class):
        """Test chart endpoint with invalid chart type."""
        response = self.client.get('/api/analytics/charts/invalid_type')
        
        self.assertEqual(response.status_code, 400)

    @patch('backend.routes.AnalyticsService')
    def test_get_top_users(self, mock_service_class):
        """Test top users endpoint."""
        mock_service = Mock()
        mock_service.get_top_active_users.return_value = [
            {"id": 1, "username": "user1", "message_count": 100}
        ]
        mock_service_class.return_value = mock_service
        
        response = self.client.get('/api/analytics/top-users')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("users", response.json)


if __name__ == '__main__':
    unittest.main()
