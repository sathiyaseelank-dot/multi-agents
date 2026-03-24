"""Tests for the calculator module."""
import pytest

from calculator import add, subtract, multiply, divide


class TestCalculatorFunctions:
    def test_add_positive_numbers(self):
        assert add(2, 3) == 5
        assert add(10, 20) == 30

    def test_add_negative_numbers(self):
        assert add(-5, -3) == -8
        assert add(-5, 5) == 0

    def test_add_decimal_numbers(self):
        assert add(1.5, 2.5) == 4.0
        assert add(0.1, 0.2) == pytest.approx(0.3)

    def test_subtract_positive_numbers(self):
        assert subtract(10, 5) == 5
        assert subtract(5, 10) == -5

    def test_subtract_negative_numbers(self):
        assert subtract(-5, -3) == -2
        assert subtract(-5, 3) == -8

    def test_subtract_decimal_numbers(self):
        assert subtract(5.5, 2.2) == pytest.approx(3.3)

    def test_multiply_positive_numbers(self):
        assert multiply(3, 4) == 12
        assert multiply(10, 10) == 100

    def test_multiply_by_zero(self):
        assert multiply(5, 0) == 0
        assert multiply(0, 100) == 0

    def test_multiply_negative_numbers(self):
        assert multiply(-3, 4) == -12
        assert multiply(-3, -4) == 12

    def test_multiply_decimal_numbers(self):
        assert multiply(2.5, 4) == 10.0

    def test_divide_positive_numbers(self):
        assert divide(10, 2) == 5
        assert divide(15, 3) == 5

    def test_divide_negative_numbers(self):
        assert divide(-10, 2) == -5
        assert divide(-10, -2) == 5

    def test_divide_decimal_numbers(self):
        assert divide(7.5, 2.5) == 3.0

    def test_divide_by_zero_raises_error(self):
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(10, 0)

    def test_divide_by_zero_negative_dividend(self):
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(-5, 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
