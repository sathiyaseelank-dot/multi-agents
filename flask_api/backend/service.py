"""Analytics service layer - business logic for dashboard data."""

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


class AnalyticsService:
    """Service for fetching and normalizing analytics data."""

    def __init__(self, data_source: Optional[AnalyticsDataSource] = None):
        self.data_source = data_source or AnalyticsDataSource()

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
        
        return DashboardMetric(
            id="total_users",
            label="Total Users",
            value=total,
            change=change,
            change_direction=direction,
        )

    def get_total_messages(self) -> DashboardMetric:
        """Get total messages with trend calculation."""
        total = self.data_source.get_total_messages()
        
        start_date, _ = self._get_date_range("daily")
        prev_total = self.data_source.get_messages_before_date(start_date.isoformat())
        
        change, direction = self._calculate_change(total, prev_total)
        
        return DashboardMetric(
            id="total_messages",
            label="Total Messages",
            value=total,
            change=change,
            change_direction=direction,
        )

    def get_total_conversations(self) -> DashboardMetric:
        """Get total conversations with trend calculation."""
        total = self.data_source.get_total_conversations()
        
        start_date, _ = self._get_date_range("daily")
        prev_total = self.data_source.get_conversations_before_date(start_date.isoformat())
        
        change, direction = self._calculate_change(total, prev_total)
        
        return DashboardMetric(
            id="total_conversations",
            label="Total Conversations",
            value=total,
            change=change,
            change_direction=direction,
        )

    def get_active_users_count(self, period: str = "daily") -> DashboardMetric:
        """Get active users count for a period."""
        active = self.data_source.get_active_users_count(period)
        
        return DashboardMetric(
            id=f"active_users_{period}",
            label=f"Active Users ({period})",
            value=active,
        )

    def _fill_date_gaps(
        self,
        data: List[Dict[str, Any]],
        days: int,
        date_key: str = "date",
        count_key: str = "count"
    ) -> List[ChartDataPoint]:
        """Fill gaps in date-series data with zeros."""
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
        return self._fill_date_gaps(data, days)

    def get_users_per_day(self, days: int = 7) -> List[ChartDataPoint]:
        """Get users per day for chart."""
        data = self.data_source.get_users_per_day(days)
        return self._fill_date_gaps(data, days)

    def get_conversations_per_day(self, days: int = 7) -> List[ChartDataPoint]:
        """Get conversations per day for chart."""
        data = self.data_source.get_conversations_per_day(days)
        return self._fill_date_gaps(data, days)

    def get_messages_by_hour(self, days: int = 7) -> List[ChartDataPoint]:
        """Get messages grouped by hour for chart."""
        data = self.data_source.get_messages_by_hour(days)
        data_dict = {row["hour"]: row["count"] for row in data}
        
        return [
            ChartDataPoint(label=f"{h:02d}:00", value=data_dict.get(h, 0))
            for h in range(24)
        ]

    def get_message_type_distribution(self) -> List[ChartDataPoint]:
        """Get message type distribution for chart."""
        data = self.data_source.get_message_type_distribution()
        
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
        return self.data_source.get_top_active_users(limit)

    def get_top_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top conversations."""
        return self.data_source.get_top_conversations(limit)

    def get_engagement_metrics(self) -> EngagementMetrics:
        """Get engagement metrics."""
        data = self.data_source.get_engagement_metrics()
        return EngagementMetrics(
            avg_messages_per_user=data["avg_messages_per_user"],
            active_users_7d=data["active_users_7d"],
            engagement_rate=data["engagement_rate"],
            total_users=data["total_users"],
        )

    def get_dashboard_overview(self) -> DashboardOverview:
        """Get dashboard overview with all key metrics."""
        return DashboardOverview(
            metrics=[
                self.get_total_users(),
                self.get_total_messages(),
                self.get_total_conversations(),
                self.get_active_users_count(),
            ],
            generated_at=datetime.utcnow().isoformat(),
        )

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
        
        return {
            "chart_type": chart_type,
            "data": [dp.to_dict() for dp in data],
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_all_analytics(self) -> Dict[str, Any]:
        """Get complete analytics data for dashboard."""
        return {
            "overview": self.get_dashboard_overview().to_dict(),
            "charts": {
                "messages_per_day": [dp.to_dict() for dp in self.get_messages_per_day(30)],
                "users_per_day": [dp.to_dict() for dp in self.get_users_per_day(30)],
                "conversations_per_day": [dp.to_dict() for dp in self.get_conversations_per_day(30)],
                "messages_by_hour": [dp.to_dict() for dp in self.get_messages_by_hour(30)],
                "message_type_distribution": [dp.to_dict() for dp in self.get_message_type_distribution()],
            },
            "top_lists": {
                "active_users": self.get_top_active_users(),
                "conversations": self.get_top_conversations(),
            },
            "engagement": self.get_engagement_metrics().to_dict(),
            "generated_at": datetime.utcnow().isoformat(),
        }
