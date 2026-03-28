"""Backend analytics module for user analytics dashboard.

This module provides:
- Data source integration for database access
- Analytics service layer for business logic
- REST API endpoints for dashboard data
- Input validation and error handling
"""

from flask import Blueprint

bp = Blueprint("analytics_api", __name__, url_prefix="/api/analytics")

from backend import routes  # noqa: E402, F401
