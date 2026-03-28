"""Analytics service layer - business logic for dashboard data."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from backend.data_source import AnalyticsDataSource
from backend.models import (
    ChartData,
    ChartDataPoint,
    DashboardMetric,
    DashboardOverview,
    EngagementMetrics,
    AnalyticsResponse,
)
from backend.errors import DataSourceError, MalformedDataError

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for fetching and normalizing analytics data."""

    def __init__(self, data_source: Optional[AnalyticsDataSource] = None):
        self.data_source = data_source or AnalyticsDataSource()
        self._validate_data_source()

    def _validate_data_source(self) -> None:
        """Validate that data source is properly configured."""
        if self.data_source is None:
            raise DataSourceError(
                "Data source is not initialized",
                source="analytics_service"
            )

    def _calculate_change(self, current: int, previous: int) -> tuple:
        """Calculate percentage change and direction."""
        if previous <= 0:
            return None, None
        change = round(((current - previous) / previous) * 100, 2)
        direction = "up" if current > previous else "down"
        return change, direction

    def _get_date_range(self, period: str) -> tuple:
        """Get date range for a period."""
        return self.data_source.get_date_range(period)

    def get_total_users(self) -> DashboardMetric:
        """Get total users with trend calculation."""
        total = self.data_source.get_total_users()
        
        start_date, _ = self._get_date_range("daily")
        prev_total = self.data_source.get_users_before_date(start_date.isoformat())
        
        change, direction = self._calculate_change(total, prev_total)
        
        metric = DashboardMetric(
            id="total_users",
            label="Total Users",
            value=total,
            change=change,
            change_direction=direction,
        )
        self._validate_metric(metric, "total_users")
        return metric

    def get_total_messages(self) -> DashboardMetric:
        """Get total messages with trend calculation."""
        total = self.data_source.get_total_messages()
        
        start_date, _ = self._get_date_range("daily")
        prev_total = self.data_source.get_messages_before_date(start_date.isoformat())
        
        change, direction = self._calculate_change(total, prev_total)
        
        metric = DashboardMetric(
            id="total_messages",
            label="Total Messages",
            value=total,
            change=change,
            change_direction=direction,
        )
        self._validate_metric(metric, "total_messages")
        return metric

    def get_total_conversations(self) -> DashboardMetric:
        """Get total conversations with trend calculation."""
        total = self.data_source.get_total_conversations()
        
        start_date, _ = self._get_date_range("daily")
        prev_total = self.data_source.get_conversations_before_date(start_date.isoformat())
        
        change, direction = self._calculate_change(total, prev_total)
        
        metric = DashboardMetric(
            id="total_conversations",
            label="Total Conversations",
            value=total,
            change=change,
            change_direction=direction,
        )
        self._validate_metric(metric, "total_conversations")
        return metric

    def get_active_users_count(self, period: str = "daily") -> DashboardMetric:
        """Get active users count for a period."""
        active = self.data_source.get_active_users_count(period)
        
        metric = DashboardMetric(
            id=f"active_users_{period}",
            label=f"Active Users ({period})",
            value=active,
        )
        self._validate_metric(metric, f"active_users_{period}")
        return metric

    def _fill_date_gaps(
        self,
        data: List[Dict[str, Any]],
        days: int,
        date_key: str = "date",
        count_key: str = "count"
    ) -> List[ChartDataPoint]:
        """Fill gaps in date-series data with zeros."""
        if data is None:
            raise MalformedDataError(
                "Chart data returned null from data source",
                expected_type="list of dicts"
            )
        
        data_dict = {row[date_key]: row[count_key] for row in data}
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        result = []
        current = start_date
        while current <= end_date:
            date_str = self._format_date(current)
            result.append(ChartDataPoint(
                label=date_str,
                value=data_dict.get(date_str, 0),
            ))
            current += timedelta(days=1)
        
        return result

    def _format_date(self, dt: datetime) -> str:
        """Format datetime to date string."""
        return dt.strftime("%Y-%m-%d")

    def get_messages_per_day(self, days: int = 7) -> List[ChartDataPoint]:
        """Get messages per day for chart."""
        data = self.data_source.get_messages_per_day(days)
        if data is None:
            raise DataSourceError(
                "Failed to fetch messages per day",
                source="database"
            )
        return self._fill_date_gaps(data, days)

    def get_users_per_day(self, days: int = 7) -> List[ChartDataPoint]:
        """Get users per day for chart."""
        data = self.data_source.get_users_per_day(days)
        if data is None:
            raise DataSourceError(
                "Failed to fetch users per day",
                source="database"
            )
        return self._fill_date_gaps(data, days)

    def get_conversations_per_day(self, days: int = 7) -> List[ChartDataPoint]:
        """Get conversations per day for chart."""
        data = self.data_source.get_conversations_per_day(days)
        if data is None:
            raise DataSourceError(
                "Failed to fetch conversations per day",
                source="database"
            )
        return self._fill_date_gaps(data, days)

    def get_messages_by_hour(self, days: int = 7) -> List[ChartDataPoint]:
        """Get messages grouped by hour for chart."""
        data = self.data_source.get_messages_by_hour(days)
        if data is None:
            raise DataSourceError(
                "Failed to fetch messages by hour",
                source="database"
            )
        data_dict = {row["hour"]: row["count"] for row in data}
        
        return [
            ChartDataPoint(label=f"{h:02d}:00", value=data_dict.get(h, 0))
            for h in range(24)
        ]

    def get_message_type_distribution(self) -> List[ChartDataPoint]:
        """Get message type distribution for chart."""
        data = self.data_source.get_message_type_distribution()
        if data is None:
            raise DataSourceError(
                "Failed to fetch message type distribution",
                source="database"
            )
        
        return [
            ChartDataPoint(
                label=row["message_type"],
                value=row["count"],
                metadata={"percentage": row["percentage"]},
            )
            for row in data
        ]

    def get_top_active_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top active users."""
        data = self.data_source.get_top_active_users(limit)
        if data is None:
            raise DataSourceError(
                "Failed to fetch top active users",
                source="database"
            )
        self._validate_list_data(data, "top_active_users")
        return data

    def get_top_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top conversations."""
        data = self.data_source.get_top_conversations(limit)
        if data is None:
            raise DataSourceError(
                "Failed to fetch top conversations",
                source="database"
            )
        self._validate_list_data(data, "top_conversations")
        return data

    def get_engagement_metrics(self) -> EngagementMetrics:
        """Get engagement metrics."""
        data = self.data_source.get_engagement_metrics()
        if data is None:
            raise DataSourceError(
                "Failed to fetch engagement metrics",
                source="database"
            )
        
        metrics = EngagementMetrics(
            avg_messages_per_user=data["avg_messages_per_user"],
            active_users_7d=data["active_users_7d"],
            engagement_rate=data["engagement_rate"],
            total_users=data["total_users"],
        )
        self._validate_engagement_metrics(metrics)
        return metrics

    def get_dashboard_overview(self) -> DashboardOverview:
        """Get dashboard overview with all key metrics."""
        overview = DashboardOverview(
            metrics=[
                self.get_total_users(),
                self.get_total_messages(),
                self.get_total_conversations(),
                self.get_active_users_count(),
            ],
            generated_at=datetime.utcnow().isoformat(),
        )
        self._validate_dashboard_overview(overview)
        return overview

    def get_chart_data(self, chart_type: str, **kwargs) -> Dict[str, Any]:
        """Get chart data for a specific chart type."""
        chart_generators = {
            "messages_per_day": self.get_messages_per_day,
            "users_per_day": self.get_users_per_day,
            "conversations_per_day": self.get_conversations_per_day,
            "messages_by_hour": self.get_messages_by_hour,
            "message_type_distribution": self.get_message_type_distribution,
        }
        
        if chart_type not in chart_generators:
            return {"error": f"Unknown chart type: {chart_type}"}
        
        generator = chart_generators[chart_type]
        days = kwargs.get("days", 7)
        
        if chart_type in [
            "messages_per_day", 
            "users_per_day", 
            "conversations_per_day", 
            "messages_by_hour"
        ]:
            data = generator(days=days)
        else:
            data = generator()
        
        result = {
            "chart_type": chart_type,
            "data": [dp.to_dict() for dp in data],
            "generated_at": datetime.utcnow().isoformat(),
        }
        self._validate_chart_response(result, chart_type)
        return result

    def get_all_analytics(self) -> Dict[str, Any]:
        """Get complete analytics data for dashboard."""
        try:
            overview = self.get_dashboard_overview()
        except Exception as e:
            logger.error(f"Failed to get dashboard overview: {e}")
            overview = DashboardOverview(
                metrics=[],
                generated_at=datetime.utcnow().isoformat()
            )
        
        try:
            charts = {
                "messages_per_day": [dp.to_dict() for dp in self.get_messages_per_day(30)],
                "users_per_day": [dp.to_dict() for dp in self.get_users_per_day(30)],
                "conversations_per_day": [dp.to_dict() for dp in self.get_conversations_per_day(30)],
                "messages_by_hour": [dp.to_dict() for dp in self.get_messages_by_hour(30)],
                "message_type_distribution": [dp.to_dict() for dp in self.get_message_type_distribution()],
            }
        except Exception as e:
            logger.error(f"Failed to get chart data: {e}")
            charts = {}

        try:
            top_lists = {
                "active_users": self.get_top_active_users(),
                "conversations": self.get_top_conversations(),
            }
        except Exception as e:
            logger.error(f"Failed to get top lists: {e}")
            top_lists = {"active_users": [], "conversations": []}

        try:
            engagement = self.get_engagement_metrics().to_dict()
        except Exception as e:
            logger.error(f"Failed to get engagement metrics: {e}")
            engagement = {
                "avg_messages_per_user": 0,
                "active_users_7d": 0,
                "engagement_rate": 0,
                "total_users": 0,
            }

        result = {
            "overview": overview.to_dict(),
            "charts": charts,
            "top_lists": top_lists,
            "engagement": engagement,
            "generated_at": datetime.utcnow().isoformat(),
        }
        self._validate_all_analytics_response(result)
        return result

    def _validate_metric(self, metric: DashboardMetric, metric_name: str) -> None:
        """Validate a dashboard metric has required fields."""
        if metric is None:
            raise MalformedDataError(
                f"{metric_name} returned null",
                expected_type="DashboardMetric"
            )
        if not metric.id or not metric.label:
            raise MalformedDataError(
                f"{metric_name} missing required fields",
                expected_type="DashboardMetric with id and label"
            )

    def _validate_list_data(self, data: List[Dict[str, Any]], field_name: str) -> None:
        """Validate list data from data source."""
        if not isinstance(data, list):
            raise MalformedDataError(
                f"{field_name} must be a list",
                expected_type="list"
            )

    def _validate_engagement_metrics(self, metrics: EngagementMetrics) -> None:
        """Validate engagement metrics."""
        if metrics is None:
            raise MalformedDataError(
                "Engagement metrics returned null",
                expected_type="EngagementMetrics"
            )

    def _validate_dashboard_overview(self, overview: DashboardOverview) -> None:
        """Validate dashboard overview."""
        if overview is None:
            raise MalformedDataError(
                "Dashboard overview returned null",
                expected_type="DashboardOverview"
            )
        if not isinstance(overview.metrics, list):
            raise MalformedDataError(
                "Dashboard overview metrics must be a list",
                expected_type="list"
            )

    def _validate_chart_response(self, response: Dict[str, Any], chart_type: str) -> None:
        """Validate chart response structure."""
        if "data" not in response:
            raise MalformedDataError(
                f"Chart {chart_type} response missing data field",
                expected_type="dict with 'data' key"
            )
        if not isinstance(response.get("data"), list):
            raise MalformedDataError(
                f"Chart {chart_type} data must be a list",
                expected_type="list"
            )

    def _validate_all_analytics_response(self, response: Dict[str, Any]) -> None:
        """Validate complete analytics response."""
        required_fields = ["overview", "charts", "top_lists", "engagement", "generated_at"]
        for field in required_fields:
            if field not in response:
                raise MalformedDataError(
                    f"Analytics response missing required field: {field}",
                    expected_type=f"dict with {field} key"
                )
