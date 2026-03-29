import math
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ============================================================
# Calculator Operations
# ============================================================


def test_add(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "add", "num1": 5, "num2": 3}
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 8
    assert response.status_code == 200


def test_subtract(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "subtract", "num1": 10, "num2": 4},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 6
    assert response.status_code == 200


def test_multiply(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "multiply", "num1": 7, "num2": 6},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 42
    assert response.status_code == 200


def test_divide(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "divide", "num1": 20, "num2": 4},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 5
    assert response.status_code == 200


def test_add_negative_result(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "add", "num1": -10, "num2": 3}
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == -7


def test_subtract_negative_numbers(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "subtract", "num1": -5, "num2": -3},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == -2


def test_multiply_negative_numbers(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "multiply", "num1": -4, "num2": -5},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 20


def test_multiply_by_zero(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "multiply", "num1": 100, "num2": 0},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 0


def test_add_with_zero(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "add", "num1": 42, "num2": 0}
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 42


def test_float_operands(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": 5.5, "num2": 3.5},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == pytest.approx(9.0)


def test_float_precision(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": 0.1, "num2": 0.2},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == pytest.approx(0.3)


def test_divide_fractional_result(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "divide", "num1": 1, "num2": 3},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == pytest.approx(0.3333333333333333)


def test_string_numbers(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": "10", "num2": "20"},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 30


def test_string_number_conversion(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "multiply", "num1": "6", "num2": "7"},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 42


def test_case_insensitive_operation(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "ADD", "num1": 5, "num2": 3}
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 8


def test_mixed_case_operation(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "MuLtIpLy", "num1": 3, "num2": 4},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 12


def test_whitespace_operation(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "  add  ", "num1": 5, "num2": 3},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 8


def test_divide_zero_dividend(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "divide", "num1": 0, "num2": 5},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 0


def test_large_numbers_add(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": 1e15, "num2": 1e15},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == pytest.approx(2e15)


def test_large_numbers_multiply(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "multiply", "num1": 1e10, "num2": 1e10},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == pytest.approx(1e20)


def test_very_small_numbers(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": 1e-15, "num2": 1e-15},
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == pytest.approx(2e-15)


def test_response_structure_success(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "add", "num1": 5, "num2": 3}
    )
    data = response.get_json()
    assert "success" in data
    assert "result" in data
    assert "error" in data
    assert "operation" in data
    assert "operands" in data
    assert data["success"] is True
    assert data["error"] is None
    assert data["operation"] == "add"
    assert data["operands"]["num1"] == 5
    assert data["operands"]["num2"] == 3


def test_response_structure_error(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "divide", "num1": 10, "num2": 0}
    )
    data = response.get_json()
    assert "success" in data
    assert "result" in data
    assert "error" in data
    assert data["success"] is False
    assert data["result"] is None
    assert "code" in data["error"]
    assert "message" in data["error"]


def test_all_operations_return_200(client):
    for op, n1, n2, expected in [
        ("add", 10, 5, 15),
        ("subtract", 10, 5, 5),
        ("multiply", 10, 5, 50),
        ("divide", 10, 5, 2),
    ]:
        response = client.post(
            "/api/calculator/calculate", json={"operation": op, "num1": n1, "num2": n2}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["result"] == expected


# ============================================================
# Division by Zero Handling
# ============================================================


def test_divide_by_zero(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "divide", "num1": 10, "num2": 0}
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "DIVISION_BY_ZERO"
    assert "Cannot divide by zero" in data["error"]["message"]
    assert response.status_code == 400


def test_divide_negative_by_zero(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "divide", "num1": -5, "num2": 0},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "DIVISION_BY_ZERO"
    assert response.status_code == 400


def test_divide_by_float_zero(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "divide", "num1": 10, "num2": 0.0},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "DIVISION_BY_ZERO"
    assert response.status_code == 400


def test_divide_by_string_zero(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "divide", "num1": 10, "num2": "0"},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "DIVISION_BY_ZERO"
    assert response.status_code == 400


# ============================================================
# Validation Failures
# ============================================================


def test_invalid_operation(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "modulo", "num1": 10, "num2": 3}
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERATION"
    assert response.status_code == 400


def test_empty_operation(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "   ", "num1": 5, "num2": 3},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_OPERATION"
    assert response.status_code == 400


def test_missing_operation(client):
    response = client.post("/api/calculator/calculate", json={"num1": 5, "num2": 3})
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_OPERATION"
    assert response.status_code == 400


def test_none_operation(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": None, "num1": 5, "num2": 3}
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_OPERATION"
    assert response.status_code == 400


def test_integer_operation(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": 123, "num1": 5, "num2": 3}
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_OPERATION"
    assert response.status_code == 400


def test_missing_num1(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "add", "num2": 3}
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_OPERAND"
    assert response.status_code == 400


def test_missing_num2(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "add", "num1": 5}
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_OPERAND"
    assert response.status_code == 400


def test_missing_both_operands(client):
    response = client.post("/api/calculator/calculate", json={"operation": "add"})
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_OPERAND"
    assert response.status_code == 400


def test_invalid_num1(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": "abc", "num2": 5},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_invalid_num2(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": 5, "num2": "xyz"},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_both_operands_invalid(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": "abc", "num2": "xyz"},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_empty_string_num1(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": "", "num2": 5},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_empty_string_num2(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": 5, "num2": ""},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_boolean_num1_true(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": True, "num2": 5},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_boolean_num1_false(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": False, "num2": 5},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_boolean_num2(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": 5, "num2": True},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_list_operand(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": [1, 2], "num2": 5},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_dict_operand(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": 5, "num2": {"a": 1}},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_nan_operand(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": float("nan"), "num2": 3},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_infinity_operand(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": float("inf"), "num2": 3},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_negative_infinity_operand(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "divide", "num1": 5, "num2": float("-inf")},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERAND"
    assert response.status_code == 400


def test_empty_request_body(client):
    response = client.post(
        "/api/calculator/calculate", data="", content_type="application/json"
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_REQUEST"
    assert response.status_code == 400


def test_null_request_body(client):
    response = client.post("/api/calculator/calculate", json=None)
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_REQUEST"
    assert response.status_code == 400


def test_malformed_json(client):
    response = client.post(
        "/api/calculator/calculate",
        data="{invalid json",
        content_type="application/json",
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_REQUEST"
    assert response.status_code == 400


def test_missing_num1_and_operation(client):
    response = client.post("/api/calculator/calculate", json={"num2": 5})
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_OPERATION"
    assert response.status_code == 400


def test_unknown_operation_error_message(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "modulo", "num1": 10, "num2": 3}
    )
    data = response.get_json()
    assert "modulo" in data["error"]["message"]
    assert "add" in data["error"]["message"]
    assert "subtract" in data["error"]["message"]
    assert "multiply" in data["error"]["message"]
    assert "divide" in data["error"]["message"]


# ============================================================
# Backend Health and Runtime Behavior
# ============================================================


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


def test_health_endpoint_method(client):
    response = client.post("/api/health")
    assert response.status_code == 405


def test_calculator_get_method_rejected(client):
    response = client.get("/api/calculator/calculate")
    assert response.status_code == 405


def test_calculator_put_method_rejected(client):
    response = client.put(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": 5, "num2": 3},
    )
    assert response.status_code == 405


def test_calculator_delete_method_rejected(client):
    response = client.delete("/api/calculator/calculate")
    assert response.status_code == 405


def test_unknown_route_returns_404(client):
    response = client.get("/api/nonexistent")
    assert response.status_code == 404


def test_root_route_returns_404(client):
    response = client.get("/")
    assert response.status_code == 404


def test_content_type_json(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "add", "num1": 5, "num2": 3}
    )
    assert response.content_type == "application/json"


def test_error_content_type_json(client):
    response = client.post(
        "/api/calculator/calculate", json={"operation": "divide", "num1": 10, "num2": 0}
    )
    assert response.content_type == "application/json"


def test_cors_headers(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "add", "num1": 5, "num2": 3},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in response.headers


def test_cors_preflight(client):
    response = client.options(
        "/api/calculator/calculate",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in response.headers


def test_consecutive_requests(client):
    for i in range(5):
        response = client.post(
            "/api/calculator/calculate",
            json={"operation": "add", "num1": i, "num2": i},
        )
        data = response.get_json()
        assert data["success"] is True
        assert data["result"] == i + i


def test_error_does_not_affect_subsequent_request(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "divide", "num1": 10, "num2": 0},
    )
    assert response.get_json()["success"] is False

    response = client.post(
        "/api/calculator/calculate", json={"operation": "add", "num1": 1, "num2": 2}
    )
    data = response.get_json()
    assert data["success"] is True
    assert data["result"] == 3


def test_internal_error_handler(client):
    response = client.post(
        "/api/calculator/calculate",
        data="null",
        content_type="application/json",
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_REQUEST"
    assert response.status_code == 400


def test_division_by_zero_result(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "divide", "num1": 0, "num2": 0},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_RESULT"
    assert response.status_code == 400


def test_invalid_operation_returns_supported_list(client):
    response = client.post(
        "/api/calculator/calculate",
        json={"operation": "power", "num1": 2, "num2": 3},
    )
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_OPERATION"
    message = data["error"]["message"]
    assert "add" in message
    assert "subtract" in message
    assert "multiply" in message
    assert "divide" in message
