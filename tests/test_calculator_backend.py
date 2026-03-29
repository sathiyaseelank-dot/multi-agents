import math
import pytest
from flask import Flask
from flask_cors import CORS
from backend.routes.calculator import bp as calculator_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    CORS(app)
    app.register_blueprint(calculator_bp, url_prefix="/api/calculator")

    @app.route("/api/health")
    def health_check():
        return {"status": "ok"}

    with app.test_client() as client:
        yield client


def post_calc(client, json_data):
    return client.post("/api/calculator/calculate", json=json_data)


# ============================================================
# Calculator Operations
# ============================================================


class TestCalculatorOperations:
    def test_add_integers(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 5, "num2": 3})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 8
        assert data["operation"] == "add"
        assert data["operands"] == {"num1": 5.0, "num2": 3.0}
        assert data["error"] is None

    def test_subtract_integers(self, client):
        resp = post_calc(client, {"operation": "subtract", "num1": 10, "num2": 4})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 6

    def test_multiply_integers(self, client):
        resp = post_calc(client, {"operation": "multiply", "num1": 7, "num2": 6})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 42

    def test_divide_integers(self, client):
        resp = post_calc(client, {"operation": "divide", "num1": 20, "num2": 4})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 5

    def test_add_negative_result(self, client):
        resp = post_calc(client, {"operation": "add", "num1": -10, "num2": 3})
        assert resp.get_json()["result"] == -7

    def test_subtract_negative_numbers(self, client):
        resp = post_calc(client, {"operation": "subtract", "num1": -5, "num2": -3})
        assert resp.get_json()["result"] == -2

    def test_multiply_negative_numbers(self, client):
        resp = post_calc(client, {"operation": "multiply", "num1": -4, "num2": -5})
        assert resp.get_json()["result"] == 20

    def test_multiply_by_zero(self, client):
        resp = post_calc(client, {"operation": "multiply", "num1": 100, "num2": 0})
        assert resp.get_json()["result"] == 0

    def test_add_with_zero(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 42, "num2": 0})
        assert resp.get_json()["result"] == 42

    def test_divide_zero_dividend(self, client):
        resp = post_calc(client, {"operation": "divide", "num1": 0, "num2": 5})
        data = resp.get_json()
        assert data["success"] is True
        assert data["result"] == 0

    def test_float_operands(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 5.5, "num2": 3.5})
        assert resp.get_json()["result"] == pytest.approx(9.0)

    def test_float_precision(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 0.1, "num2": 0.2})
        assert resp.get_json()["result"] == pytest.approx(0.3)

    def test_divide_fractional_result(self, client):
        resp = post_calc(client, {"operation": "divide", "num1": 1, "num2": 3})
        assert resp.get_json()["result"] == pytest.approx(0.3333333333333333)

    def test_string_number_coercion(self, client):
        resp = post_calc(client, {"operation": "add", "num1": "10", "num2": "20"})
        data = resp.get_json()
        assert data["success"] is True
        assert data["result"] == 30

    def test_string_multiply(self, client):
        resp = post_calc(client, {"operation": "multiply", "num1": "6", "num2": "7"})
        assert resp.get_json()["result"] == 42

    def test_case_insensitive_operation(self, client):
        resp = post_calc(client, {"operation": "ADD", "num1": 5, "num2": 3})
        assert resp.get_json()["success"] is True

    def test_mixed_case_operation(self, client):
        resp = post_calc(client, {"operation": "MuLtIpLy", "num1": 3, "num2": 4})
        assert resp.get_json()["result"] == 12

    def test_whitespace_trimmed_operation(self, client):
        resp = post_calc(client, {"operation": "  add  ", "num1": 5, "num2": 3})
        assert resp.get_json()["success"] is True

    def test_large_numbers(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 1e15, "num2": 1e15})
        assert resp.get_json()["result"] == pytest.approx(2e15)

    def test_large_multiply(self, client):
        resp = post_calc(client, {"operation": "multiply", "num1": 1e10, "num2": 1e10})
        assert resp.get_json()["result"] == pytest.approx(1e20)

    def test_very_small_numbers(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 1e-15, "num2": 1e-15})
        assert resp.get_json()["result"] == pytest.approx(2e-15)

    def test_subtract_resulting_in_zero(self, client):
        resp = post_calc(client, {"operation": "subtract", "num1": 7, "num2": 7})
        data = resp.get_json()
        assert data["success"] is True
        assert data["result"] == 0

    def test_all_four_operations_sequential(self, client):
        cases = [
            ("add", 10, 5, 15),
            ("subtract", 10, 5, 5),
            ("multiply", 10, 5, 50),
            ("divide", 10, 5, 2),
        ]
        for op, n1, n2, expected in cases:
            resp = post_calc(client, {"operation": op, "num1": n1, "num2": n2})
            assert resp.status_code == 200
            assert resp.get_json()["result"] == expected


# ============================================================
# Division by Zero Handling
# ============================================================


class TestDivisionByZero:
    def test_divide_by_zero_integer(self, client):
        resp = post_calc(client, {"operation": "divide", "num1": 10, "num2": 0})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "DIVISION_BY_ZERO"
        assert "Cannot divide by zero" in data["error"]["message"]
        assert data["result"] is None

    def test_divide_negative_by_zero(self, client):
        resp = post_calc(client, {"operation": "divide", "num1": -5, "num2": 0})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "DIVISION_BY_ZERO"

    def test_divide_by_float_zero(self, client):
        resp = post_calc(client, {"operation": "divide", "num1": 10, "num2": 0.0})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "DIVISION_BY_ZERO"

    def test_divide_by_string_zero(self, client):
        resp = post_calc(client, {"operation": "divide", "num1": 10, "num2": "0"})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "DIVISION_BY_ZERO"

    def test_divide_zero_by_zero(self, client):
        resp = post_calc(client, {"operation": "divide", "num1": 0, "num2": 0})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "DIVISION_BY_ZERO"

    def test_division_by_zero_does_not_affect_next_request(self, client):
        post_calc(client, {"operation": "divide", "num1": 10, "num2": 0})
        resp = post_calc(client, {"operation": "add", "num1": 1, "num2": 2})
        data = resp.get_json()
        assert data["success"] is True
        assert data["result"] == 3


# ============================================================
# Validation Failures
# ============================================================


class TestValidationFailures:
    # --- Operation validation ---

    def test_invalid_operation(self, client):
        resp = post_calc(client, {"operation": "modulo", "num1": 10, "num2": 3})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_OPERATION"

    def test_invalid_operation_message_lists_supported(self, client):
        resp = post_calc(client, {"operation": "power", "num1": 2, "num2": 3})
        msg = resp.get_json()["error"]["message"]
        for op in ("add", "subtract", "multiply", "divide"):
            assert op in msg

    def test_empty_operation(self, client):
        resp = post_calc(client, {"operation": "   ", "num1": 5, "num2": 3})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "MISSING_OPERATION"

    def test_missing_operation_key(self, client):
        resp = post_calc(client, {"num1": 5, "num2": 3})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "MISSING_OPERATION"

    def test_null_operation(self, client):
        resp = post_calc(client, {"operation": None, "num1": 5, "num2": 3})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "MISSING_OPERATION"

    def test_integer_operation_type(self, client):
        resp = post_calc(client, {"operation": 123, "num1": 5, "num2": 3})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "MISSING_OPERATION"

    # --- Operand presence ---

    def test_missing_num1(self, client):
        resp = post_calc(client, {"operation": "add", "num2": 3})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "MISSING_OPERAND"

    def test_missing_num2(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 5})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "MISSING_OPERAND"

    def test_missing_both_operands(self, client):
        resp = post_calc(client, {"operation": "add"})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "MISSING_OPERAND"

    def test_missing_operation_and_num1(self, client):
        resp = post_calc(client, {"num2": 5})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "MISSING_OPERATION"

    # --- Operand type validation ---

    def test_invalid_num1_string(self, client):
        resp = post_calc(client, {"operation": "add", "num1": "abc", "num2": 5})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_OPERAND"

    def test_invalid_num2_string(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 5, "num2": "xyz"})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_OPERAND"

    def test_both_operands_invalid(self, client):
        resp = post_calc(client, {"operation": "add", "num1": "abc", "num2": "xyz"})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_OPERAND"

    def test_empty_string_num1(self, client):
        resp = post_calc(client, {"operation": "add", "num1": "", "num2": 5})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_OPERAND"

    def test_empty_string_num2(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 5, "num2": ""})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_OPERAND"

    def test_boolean_true_coerced_to_one(self, client):
        resp = post_calc(client, {"operation": "add", "num1": True, "num2": 5})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["result"] == 6

    def test_boolean_false_coerced_to_zero(self, client):
        resp = post_calc(client, {"operation": "add", "num1": False, "num2": 5})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["result"] == 5

    def test_boolean_num2_coerced(self, client):
        resp = post_calc(client, {"operation": "multiply", "num1": 5, "num2": True})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["result"] == 5

    def test_list_operand(self, client):
        resp = post_calc(client, {"operation": "add", "num1": [1, 2], "num2": 5})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_OPERAND"

    def test_dict_operand(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 5, "num2": {"a": 1}})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_OPERAND"

    # --- Special float values ---

    def test_nan_operand_num1(self, client):
        resp = post_calc(client, {"operation": "add", "num1": float("nan"), "num2": 3})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_OPERAND"

    def test_nan_operand_num2(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 3, "num2": float("nan")})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_OPERAND"

    def test_infinity_operand_num1(self, client):
        resp = post_calc(client, {"operation": "add", "num1": float("inf"), "num2": 3})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_OPERAND"

    def test_infinity_operand_num2(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 3, "num2": float("inf")})
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_OPERAND"

    def test_negative_infinity_operand(self, client):
        resp = post_calc(
            client, {"operation": "divide", "num1": 5, "num2": float("-inf")}
        )
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_OPERAND"

    # --- Request body validation ---

    def test_empty_request_body(self, client):
        resp = client.post(
            "/api/calculator/calculate", data="", content_type="application/json"
        )
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_REQUEST"

    def test_null_request_body(self, client):
        resp = post_calc(client, None)
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_REQUEST"

    def test_malformed_json(self, client):
        resp = client.post(
            "/api/calculator/calculate",
            data="{invalid json",
            content_type="application/json",
        )
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_REQUEST"

    def test_null_json_literal(self, client):
        resp = client.post(
            "/api/calculator/calculate",
            data="null",
            content_type="application/json",
        )
        data = resp.get_json()
        assert resp.status_code == 400
        assert data["error"]["code"] == "INVALID_REQUEST"


# ============================================================
# Response Structure
# ============================================================


class TestResponseStructure:
    def test_success_response_has_all_fields(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 5, "num2": 3})
        data = resp.get_json()
        assert set(data.keys()) == {
            "success",
            "error",
            "result",
            "operation",
            "operands",
        }
        assert data["success"] is True
        assert data["error"] is None
        assert data["operation"] == "add"
        assert data["operands"]["num1"] == 5.0
        assert data["operands"]["num2"] == 3.0

    def test_error_response_has_all_fields(self, client):
        resp = post_calc(client, {"operation": "divide", "num1": 10, "num2": 0})
        data = resp.get_json()
        assert data["success"] is False
        assert data["result"] is None
        assert "code" in data["error"]
        assert "message" in data["error"]

    def test_success_content_type(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 5, "num2": 3})
        assert resp.content_type == "application/json"

    def test_error_content_type(self, client):
        resp = post_calc(client, {"operation": "divide", "num1": 10, "num2": 0})
        assert resp.content_type == "application/json"


# ============================================================
# Backend Health and Runtime Behavior
# ============================================================


class TestHealthAndRuntime:
    def test_health_endpoint_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_health_rejects_post(self, client):
        resp = client.post("/api/health")
        assert resp.status_code == 405

    def test_calculator_rejects_get(self, client):
        resp = client.get("/api/calculator/calculate")
        assert resp.status_code == 405

    def test_calculator_rejects_put(self, client):
        resp = client.put(
            "/api/calculator/calculate",
            json={"operation": "add", "num1": 5, "num2": 3},
        )
        assert resp.status_code == 405

    def test_calculator_rejects_delete(self, client):
        resp = client.delete("/api/calculator/calculate")
        assert resp.status_code == 405

    def test_unknown_route_returns_404(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_root_returns_404(self, client):
        resp = client.get("/")
        assert resp.status_code == 404

    def test_cors_headers_present(self, client):
        resp = post_calc(client, {"operation": "add", "num1": 5, "num2": 3})
        assert resp.status_code == 200
        assert "Access-Control-Allow-Origin" in resp.headers

    def test_cors_preflight(self, client):
        resp = client.options(
            "/api/calculator/calculate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.status_code == 200
        assert "Access-Control-Allow-Origin" in resp.headers

    def test_consecutive_requests_stable(self, client):
        for i in range(10):
            resp = post_calc(client, {"operation": "add", "num1": i, "num2": i})
            data = resp.get_json()
            assert data["success"] is True
            assert data["result"] == i + i

    def test_error_then_success_recovery(self, client):
        resp = post_calc(client, {"operation": "divide", "num1": 10, "num2": 0})
        assert resp.get_json()["success"] is False

        resp = post_calc(client, {"operation": "multiply", "num1": 6, "num2": 7})
        data = resp.get_json()
        assert data["success"] is True
        assert data["result"] == 42
