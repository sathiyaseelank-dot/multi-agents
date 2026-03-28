"""Data models for analytics dashboard."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ChartDataPoint:
    """Represents a single data point for chart visualization."""
    label: str
    value: float
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"label": self.label, "value": self.value}
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChartDataPoint":
        return cls(
            label=data.get("label", ""),
            value=float(data.get("value", 0)),
            metadata=data.get("metadata"),
        )


@dataclass
class DashboardMetric:
    """Represents a metric displayed on the dashboard."""
    id: str
    label: str
    value: float
    change: Optional[float] = None
    change_direction: Optional[str] = None
    unit: Optional[str] = None
    trend: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
        }
        if self.change is not None:
            result["change"] = self.change
            result["change_direction"] = self.change_direction
        if self.trend:
            result["trend"] = self.trend
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DashboardMetric":
        return cls(
            id=data.get("id", ""),
            label=data.get("label", ""),
            value=float(data.get("value", 0)),
            change=data.get("change"),
            change_direction=data.get("change_direction"),
            unit=data.get("unit"),
            trend=data.get("trend"),
        )


@dataclass
class UserSummary:
    """Summary of a user for analytics."""
    id: int
    username: str
    email: str
    message_count: int = 0
    last_activity: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "message_count": self.message_count,
            "last_activity": self.last_activity,
        }


@dataclass
class ConversationSummary:
    """Summary of a conversation for analytics."""
    id: int
    name: Optional[str]
    is_group: bool
    participant_count: int = 0
    message_count: int = 0
    last_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "is_group": self.is_group,
            "participant_count": self.participant_count,
            "message_count": self.message_count,
            "last_message": self.last_message,
        }


@dataclass
class EngagementMetrics:
    """Engagement metrics for the dashboard."""
    avg_messages_per_user: float
    active_users_7d: int
    engagement_rate: float
    total_users: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_messages_per_user": self.avg_messages_per_user,
            "active_users_7d": self.active_users_7d,
            "engagement_rate": self.engagement_rate,
            "total_users": self.total_users,
        }


@dataclass
class DashboardOverview:
    """Complete dashboard overview with metrics."""
    metrics: List[DashboardMetric]
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": [m.to_dict() for m in self.metrics],
            "generated_at": self.generated_at,
        }


@dataclass
class ChartData:
    """Container for chart data with metadata."""
    chart_type: str
    data: List[ChartDataPoint]
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chart_type": self.chart_type,
            "data": [dp.to_dict() for dp in self.data],
            "generated_at": self.generated_at,
        }


@dataclass
class AnalyticsResponse:
    """Complete analytics response for the dashboard."""
    overview: DashboardOverview
    charts: Dict[str, List[ChartDataPoint]]
    top_lists: Dict[str, Any]
    engagement: EngagementMetrics
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overview": self.overview.to_dict(),
            "charts": {
                name: [dp.to_dict() for dp in points]
                for name, points in self.charts.items()
            },
            "top_lists": self.top_lists,
            "engagement": self.engagement.to_dict(),
            "generated_at": self.generated_at,
        }
