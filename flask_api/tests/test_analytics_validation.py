import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.modules["flask_socketio"] = MagicMock()
sys.modules["eventlet"] = MagicMock()
sys.modules["gevent"] = MagicMock()
sys.modules["geventwebsocket"] = MagicMock()
sys.modules["orchestrator"] = MagicMock()
sys.modules["orchestrator.orchestrator"] = MagicMock()
sys.modules["orchestrator.events"] = MagicMock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.analytics_validation import (
    validate_period,
    validate_days,
    validate_limit,
    validate_chart_type,
    validate_positive_number,
    validate_required_fields,
    sanitize_string,
    AnalyticsValidationError,
    DataSourceError,
    MalformedDataError,
    ValidationError,
)
from services.analytics_errors import (
    ErrorResponse,
    validation_error_response,
    not_found_error_response,
    data_source_error_response,
    malformed_data_error_response,
    internal_error_response,
    ERROR_CODES,
)


class ValidationErrorTestCase(unittest.TestCase):
    def test_validate_period_valid_daily(self):
        valid, error = validate_period("daily")
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_period_valid_weekly(self):
        valid, error = validate_period("weekly")
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_period_valid_monthly(self):
        valid, error = validate_period("monthly")
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_period_invalid(self):
        valid, error = validate_period("yearly")
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error.field, "period")
        self.assertEqual(error.code, "INVALID_PERIOD")

    def test_validate_period_none(self):
        valid, error = validate_period(None)
        self.assertTrue(valid)
        self.assertIsNone(error)


class ValidateDaysTestCase(unittest.TestCase):
    def test_validate_days_valid_min(self):
        valid, error = validate_days(1)
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_days_valid_max(self):
        valid, error = validate_days(365)
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_days_valid_mid(self):
        valid, error = validate_days(30)
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_days_zero(self):
        valid, error = validate_days(0)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error.field, "days")
        self.assertEqual(error.code, "OUT_OF_RANGE")

    def test_validate_days_negative(self):
        valid, error = validate_days(-1)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error.code, "OUT_OF_RANGE")

    def test_validate_days_over_365(self):
        valid, error = validate_days(366)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error.code, "OUT_OF_RANGE")

    def test_validate_days_none(self):
        valid, error = validate_days(None)
        self.assertTrue(valid)
        self.assertIsNone(error)


class ValidateLimitTestCase(unittest.TestCase):
    def test_validate_limit_valid_min(self):
        valid, error = validate_limit(1)
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_limit_valid_max(self):
        valid, error = validate_limit(100)
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_limit_zero(self):
        valid, error = validate_limit(0)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error.field, "limit")
        self.assertEqual(error.code, "OUT_OF_RANGE")

    def test_validate_limit_negative(self):
        valid, error = validate_limit(-5)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error.code, "OUT_OF_RANGE")

    def test_validate_limit_over_100(self):
        valid, error = validate_limit(101)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error.code, "OUT_OF_RANGE")

    def test_validate_limit_none(self):
        valid, error = validate_limit(None)
        self.assertTrue(valid)
        self.assertIsNone(error)


class ValidateChartTypeTestCase(unittest.TestCase):
    def test_validate_chart_type_valid_messages_per_day(self):
        valid, error = validate_chart_type("messages_per_day")
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_chart_type_valid_users_per_day(self):
        valid, error = validate_chart_type("users_per_day")
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_chart_type_valid_conversations_per_day(self):
        valid, error = validate_chart_type("conversations_per_day")
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_chart_type_valid_messages_by_hour(self):
        valid, error = validate_chart_type("messages_by_hour")
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_chart_type_valid_message_type_distribution(self):
        valid, error = validate_chart_type("message_type_distribution")
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_chart_type_invalid(self):
        valid, error = validate_chart_type("invalid_type")
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error.field, "chart_type")
        self.assertEqual(error.code, "INVALID_CHART_TYPE")


class ValidateRequiredFieldsTestCase(unittest.TestCase):
    def test_validate_required_fields_all_present(self):
        data = {"name": "test", "value": 123}
        errors = validate_required_fields(data, ["name", "value"])
        self.assertEqual(len(errors), 0)

    def test_validate_required_fields_missing_one(self):
        data = {"name": "test"}
        errors = validate_required_fields(data, ["name", "value"])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].field, "value")
        self.assertEqual(errors[0].code, "MISSING_FIELD")

    def test_validate_required_fields_missing_multiple(self):
        data = {}
        errors = validate_required_fields(data, ["name", "value", "id"])
        self.assertEqual(len(errors), 3)

    def test_validate_required_fields_with_none_value(self):
        data = {"name": None}
        errors = validate_required_fields(data, ["name"])
        self.assertEqual(len(errors), 1)


class SanitizeStringTestCase(unittest.TestCase):
    def test_sanitize_string_valid(self):
        result = sanitize_string("  hello  ", "name")
        self.assertEqual(result, "hello")

    def test_sanitize_string_empty_after_trim(self):
        with self.assertRaises(MalformedDataError) as ctx:
            sanitize_string("   ", "name")
        self.assertIn("cannot be empty", str(ctx.exception))

    def test_sanitize_string_none(self):
        with self.assertRaises(MalformedDataError):
            sanitize_string(None, "name")

    def test_sanitize_string_max_length(self):
        long_string = "a" * 300
        result = sanitize_string(long_string, "name", max_length=255)
        self.assertEqual(len(result), 255)

    def test_sanitize_string_non_string(self):
        with self.assertRaises(MalformedDataError) as ctx:
            sanitize_string(123, "name")
        self.assertIn("Expected string", str(ctx.exception))


class ValidatePositiveNumberTestCase(unittest.TestCase):
    def test_validate_positive_number_valid_int(self):
        result = validate_positive_number(42, "count")
        self.assertEqual(result, 42.0)

    def test_validate_positive_number_valid_float(self):
        result = validate_positive_number(3.14, "rate")
        self.assertEqual(result, 3.14)

    def test_validate_positive_number_zero(self):
        result = validate_positive_number(0, "count")
        self.assertEqual(result, 0.0)

    def test_validate_positive_number_negative(self):
        with self.assertRaises(MalformedDataError) as ctx:
            validate_positive_number(-5, "count")
        self.assertIn("cannot be negative", str(ctx.exception))

    def test_validate_positive_number_invalid_type(self):
        with self.assertRaises(MalformedDataError):
            validate_positive_number("abc", "count")


class ErrorResponseTestCase(unittest.TestCase):
    def test_error_response_basic(self):
        err = ErrorResponse("Test error", "TEST_ERROR", 400)
        result = err.to_dict()
        self.assertEqual(result["error"]["code"], "TEST_ERROR")
        self.assertEqual(result["error"]["message"], "Test error")
        self.assertIn("timestamp", result["error"])

    def test_error_response_with_details(self):
        err = ErrorResponse("Test error", "TEST_ERROR", 400, {"key": "value"})
        result = err.to_dict()
        self.assertEqual(result["error"]["details"], {"key": "value"})

    def test_error_response_with_field_errors(self):
        err = ErrorResponse(
            "Validation failed",
            "VALIDATION_ERROR",
            400,
            field_errors=[{"field": "name", "message": "Required", "code": "MISSING"}],
        )
        result = err.to_dict()
        self.assertEqual(len(result["error"]["field_errors"]), 1)

    def test_error_response_to_response(self):
        from app import create_app
        from config import TestingConfig
        app = create_app(TestingConfig)
        with app.app_context():
            err = ErrorResponse("Test error", "TEST_ERROR", 400)
            response, status = err.to_response()
            self.assertEqual(status, 400)


class ValidationErrorResponseTestCase(unittest.TestCase):
    def test_validation_error_response_default(self):
        resp = validation_error_response()
        result = resp.to_dict()
        self.assertEqual(result["error"]["code"], ERROR_CODES["VALIDATION_ERROR"])
        self.assertEqual(result["error"]["message"], "Validation failed")

    def test_validation_error_response_with_field_errors(self):
        resp = validation_error_response(
            "Invalid request",
            field_errors=[{"field": "period", "message": "Invalid", "code": "INVALID"}],
        )
        result = resp.to_dict()
        self.assertEqual(len(result["error"]["field_errors"]), 1)


class DataSourceErrorResponseTestCase(unittest.TestCase):
    def test_data_source_error_response(self):
        resp = data_source_error_response("Connection failed", "redis")
        result = resp.to_dict()
        self.assertEqual(result["error"]["code"], ERROR_CODES["DATA_SOURCE_ERROR"])
        self.assertEqual(result["error"]["details"]["source"], "redis")
        self.assertEqual(resp.status_code, 503)


class MalformedDataErrorResponseTestCase(unittest.TestCase):
    def test_malformed_data_error_response(self):
        resp = malformed_data_error_response("Invalid format", {"field": "value"})
        result = resp.to_dict()
        self.assertEqual(result["error"]["code"], ERROR_CODES["MALFORMED_DATA"])
        self.assertEqual(resp.status_code, 422)


class NotFoundErrorResponseTestCase(unittest.TestCase):
    def test_not_found_error_response(self):
        resp = not_found_error_response("User not found")
        result = resp.to_dict()
        self.assertEqual(result["error"]["code"], ERROR_CODES["NOT_FOUND"])
        self.assertEqual(resp.status_code, 404)


class InternalErrorResponseTestCase(unittest.TestCase):
    def test_internal_error_response(self):
        resp = internal_error_response("Server error")
        result = resp.to_dict()
        self.assertEqual(result["error"]["code"], ERROR_CODES["INTERNAL_ERROR"])
        self.assertEqual(resp.status_code, 500)


class AnalyticsValidationErrorExceptionTestCase(unittest.TestCase):
    def test_analytics_validation_error_creation(self):
        errors = [
            ValidationError("field1", "Error 1", "ERR_1"),
            ValidationError("field2", "Error 2", "ERR_2"),
        ]
        exc = AnalyticsValidationError(errors)
        self.assertEqual(len(exc.errors), 2)
        self.assertEqual(exc.errors[0].field, "field1")


class DataSourceErrorExceptionTestCase(unittest.TestCase):
    def test_data_source_error_creation(self):
        exc = DataSourceError("Connection refused", "redis")
        self.assertEqual(exc.message, "Connection refused")
        self.assertEqual(exc.source, "redis")


class MalformedDataErrorExceptionTestCase(unittest.TestCase):
    def test_malformed_data_error_creation(self):
        exc = MalformedDataError("Invalid JSON", "object")
        self.assertEqual(exc.message, "Invalid JSON")
        self.assertEqual(exc.expected_type, "object")

    def test_malformed_data_error_without_type(self):
        exc = MalformedDataError("Invalid data")
        self.assertIsNone(exc.expected_type)


if __name__ == "__main__":
    unittest.main()
