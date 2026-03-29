from flask import Blueprint, request, jsonify
import math

bp = Blueprint("calculator", __name__)

OPERATIONS = {
    "add": lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
    "multiply": lambda a, b: a * b,
    "divide": lambda a, b: a / b,
}

SUPPORTED_OPERATIONS = ", ".join(OPERATIONS.keys())


def validate_request(data):
    if not data:
        return {"code": "INVALID_REQUEST", "message": "Request body is required"}, 400

    operation = data.get("operation")
    if operation is None or not isinstance(operation, str) or not operation.strip():
        return {
            "code": "MISSING_OPERATION",
            "message": "Operation is required and must be a non-empty string",
        }, 400

    num1 = data.get("num1")
    num2 = data.get("num2")

    if num1 is None:
        return {"code": "MISSING_OPERAND", "message": "num1 is required"}, 400

    if num2 is None:
        return {"code": "MISSING_OPERAND", "message": "num2 is required"}, 400

    try:
        num1 = float(num1)
    except (ValueError, TypeError):
        return {
            "code": "INVALID_OPERAND",
            "message": "num1 must be a valid number",
        }, 400

    try:
        num2 = float(num2)
    except (ValueError, TypeError):
        return {
            "code": "INVALID_OPERAND",
            "message": "num2 must be a valid number",
        }, 400

    if math.isnan(num1) or math.isnan(num2):
        return {
            "code": "INVALID_OPERAND",
            "message": "Operands cannot be NaN",
        }, 400

    if math.isinf(num1) or math.isinf(num2):
        return {
            "code": "INVALID_OPERAND",
            "message": "Operands cannot be infinity",
        }, 400

    operation = operation.strip().lower()

    if operation not in OPERATIONS:
        return {
            "code": "INVALID_OPERATION",
            "message": f"Unknown operation: '{operation}'. Supported: {SUPPORTED_OPERATIONS}",
        }, 400

    if operation == "divide" and num2 == 0:
        return {"code": "DIVISION_BY_ZERO", "message": "Cannot divide by zero"}, 400

    return None, num1, num2, operation


@bp.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.get_json(silent=True)

        if data is None:
            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Request body is required",
                    },
                    "result": None,
                }
            ), 400

        error = validate_request(data)
        if error[0]:
            return jsonify(
                {"success": False, "error": error[0], "result": None}
            ), error[1]

        _, num1, num2, operation = error

        result = OPERATIONS[operation](num1, num2)

        if math.isnan(result):
            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_RESULT",
                        "message": "Result is not a number",
                    },
                    "result": None,
                }
            ), 400

        return jsonify(
            {
                "success": True,
                "error": None,
                "result": result,
                "operation": operation,
                "operands": {"num1": num1, "num2": num2},
            }
        ), 200

    except Exception:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                },
                "result": None,
            }
        ), 500
