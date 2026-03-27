from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from database import get_db


@dataclass
class ChartDataPoint:
    label: str
    value: float
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        result = {"label": self.label, "value": self.value}
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class DashboardMetric:
    id: str
    label: str
    value: float
    change: Optional[float] = None
    change_direction: Optional[str] = None
    unit: Optional[str] = None
    trend: Optional[List[float]] = None

    def to_dict(self) -> Dict:
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


class AnalyticsService:
    @staticmethod
    def _get_date_range(period: str) -> tuple:
        end_date = datetime.now()
        if period == "daily":
            start_date = end_date - timedelta(days=7)
        elif period == "weekly":
            start_date = end_date - timedelta(weeks=4)
        elif period == "monthly":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=7)
        return start_date, end_date

    @staticmethod
    def _format_date(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d")

    @classmethod
    def get_total_users(cls) -> DashboardMetric:
        db = get_db()
        row = db.execute("SELECT COUNT(*) as count FROM users").fetchone()
        total = row["count"] if row else 0
        
        start_date, _ = cls._get_date_range("daily")
        prev_row = db.execute(
            "SELECT COUNT(*) as count FROM users WHERE created_at < ?",
            (start_date.isoformat(),)
        ).fetchone()
        prev_total = prev_row["count"] if prev_row else 0
        
        change = None
        direction = None
        if prev_total > 0:
            change = round(((total - prev_total) / prev_total) * 100, 2)
            direction = "up" if total > prev_total else "down"
        
        return DashboardMetric(
            id="total_users",
            label="Total Users",
            value=total,
            change=change,
            change_direction=direction,
        )

    @classmethod
    def get_total_messages(cls) -> DashboardMetric:
        db = get_db()
        row = db.execute("SELECT COUNT(*) as count FROM messages").fetchone()
        total = row["count"] if row else 0
        
        start_date, _ = cls._get_date_range("daily")
        prev_row = db.execute(
            "SELECT COUNT(*) as count FROM messages WHERE created_at < ?",
            (start_date.isoformat(),)
        ).fetchone()
        prev_total = prev_row["count"] if prev_row else 0
        
        change = None
        direction = None
        if prev_total > 0:
            change = round(((total - prev_total) / prev_total) * 100, 2)
            direction = "up" if total > prev_total else "down"
        
        return DashboardMetric(
            id="total_messages",
            label="Total Messages",
            value=total,
            change=change,
            change_direction=direction,
        )

    @classmethod
    def get_total_conversations(cls) -> DashboardMetric:
        db = get_db()
        row = db.execute("SELECT COUNT(*) as count FROM conversations").fetchone()
        total = row["count"] if row else 0
        
        start_date, _ = cls._get_date_range("daily")
        prev_row = db.execute(
            "SELECT COUNT(*) as count FROM conversations WHERE created_at < ?",
            (start_date.isoformat(),)
        ).fetchone()
        prev_total = prev_row["count"] if prev_row else 0
        
        change = None
        direction = None
        if prev_total > 0:
            change = round(((total - prev_total) / prev_total) * 100, 2)
            direction = "up" if total > prev_total else "down"
        
        return DashboardMetric(
            id="total_conversations",
            label="Total Conversations",
            value=total,
            change=change,
            change_direction=direction,
        )

    @classmethod
    def get_active_users_count(cls, period: str = "daily") -> DashboardMetric:
        db = get_db()
        start_date, end_date = cls._get_date_range(period)
        
        row = db.execute(
            """
            SELECT COUNT(DISTINCT user_id) as count FROM (
                SELECT sender_id as user_id FROM messages 
                WHERE created_at BETWEEN ? AND ?
                UNION
                SELECT user_id FROM conversation_participants
                WHERE joined_at BETWEEN ? AND ?
            )
            """,
            (start_date.isoformat(), end_date.isoformat(), 
             start_date.isoformat(), end_date.isoformat()),
        ).fetchone()
        
        active = row["count"] if row else 0
        
        return DashboardMetric(
            id=f"active_users_{period}",
            label=f"Active Users ({period})",
            value=active,
        )

    @classmethod
    def get_messages_per_day(cls, days: int = 7) -> List[ChartDataPoint]:
        db = get_db()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        rows = db.execute(
            """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM messages
            WHERE created_at BETWEEN ? AND ?
            GROUP BY DATE(created_at)
            ORDER BY date
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
        
        data_dict = {row["date"]: row["count"] for row in rows}
        
        result = []
        current = start_date
        while current <= end_date:
            date_str = cls._format_date(current)
            result.append(ChartDataPoint(
                label=date_str,
                value=data_dict.get(date_str, 0),
            ))
            current += timedelta(days=1)
        
        return result

    @classmethod
    def get_users_per_day(cls, days: int = 7) -> List[ChartDataPoint]:
        db = get_db()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        rows = db.execute(
            """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM users
            WHERE created_at BETWEEN ? AND ?
            GROUP BY DATE(created_at)
            ORDER BY date
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
        
        data_dict = {row["date"]: row["count"] for row in rows}
        
        result = []
        current = start_date
        while current <= end_date:
            date_str = cls._format_date(current)
            result.append(ChartDataPoint(
                label=date_str,
                value=data_dict.get(date_str, 0),
            ))
            current += timedelta(days=1)
        
        return result

    @classmethod
    def get_conversations_per_day(cls, days: int = 7) -> List[ChartDataPoint]:
        db = get_db()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        rows = db.execute(
            """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM conversations
            WHERE created_at BETWEEN ? AND ?
            GROUP BY DATE(created_at)
            ORDER BY date
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
        
        data_dict = {row["date"]: row["count"] for row in rows}
        
        result = []
        current = start_date
        while current <= end_date:
            date_str = cls._format_date(current)
            result.append(ChartDataPoint(
                label=date_str,
                value=data_dict.get(date_str, 0),
            ))
            current += timedelta(days=1)
        
        return result

    @classmethod
    def get_messages_by_hour(cls, days: int = 7) -> List[ChartDataPoint]:
        db = get_db()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        rows = db.execute(
            """
            SELECT CAST(strftime('%H', created_at) AS INTEGER) as hour,
                   COUNT(*) as count
            FROM messages
            WHERE created_at BETWEEN ? AND ?
            GROUP BY hour
            ORDER BY hour
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
        
        data_dict = {row["hour"]: row["count"] for row in rows}
        
        return [
            ChartDataPoint(label=f"{h:02d}:00", value=data_dict.get(h, 0))
            for h in range(24)
        ]

    @classmethod
    def get_top_active_users(cls, limit: int = 10) -> List[Dict[str, Any]]:
        db = get_db()
        rows = db.execute(
            """
            SELECT u.id, u.username, u.email, COUNT(m.id) as message_count,
                   MAX(m.created_at) as last_activity
            FROM users u
            LEFT JOIN messages m ON u.id = m.sender_id
            GROUP BY u.id
            ORDER BY message_count DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        
        return [
            {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "message_count": row["message_count"],
                "last_activity": row["last_activity"],
            }
            for row in rows
        ]

    @classmethod
    def get_top_conversations(cls, limit: int = 10) -> List[Dict[str, Any]]:
        db = get_db()
        rows = db.execute(
            """
            SELECT c.id, c.name, c.is_group,
                   COUNT(DISTINCT cp.user_id) as participant_count,
                   COUNT(m.id) as message_count,
                   MAX(m.created_at) as last_message
            FROM conversations c
            LEFT JOIN conversation_participants cp ON c.id = cp.conversation_id
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id
            ORDER BY message_count DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "is_group": bool(row["is_group"]),
                "participant_count": row["participant_count"],
                "message_count": row["message_count"],
                "last_message": row["last_message"],
            }
            for row in rows
        ]

    @classmethod
    def get_message_type_distribution(cls) -> List[ChartDataPoint]:
        db = get_db()
        rows = db.execute(
            """
            SELECT message_type, COUNT(*) as count
            FROM messages
            GROUP BY message_type
            ORDER BY count DESC
            """,
        ).fetchall()
        
        total = sum(row["count"] for row in rows) or 1
        
        return [
            ChartDataPoint(
                label=row["message_type"],
                value=row["count"],
                metadata={"percentage": round((row["count"] / total) * 100, 2)},
            )
            for row in rows
        ]

    @classmethod
    def get_engagement_metrics(cls) -> Dict[str, Any]:
        db = get_db()
        
        total_users = db.execute("SELECT COUNT(*) as count FROM users").fetchone()["count"]
        total_messages = db.execute("SELECT COUNT(*) as count FROM messages").fetchone()["count"]
        
        avg_messages_per_user = round(total_messages / total_users, 2) if total_users > 0 else 0
        
        active_users_row = db.execute(
            """
            SELECT COUNT(DISTINCT sender_id) as count
            FROM messages
            WHERE created_at >= datetime('now', '-7 days')
            """,
        ).fetchone()
        active_users = active_users_row["count"] if active_users_row else 0
        
        engagement_rate = round((active_users / total_users) * 100, 2) if total_users > 0 else 0
        
        return {
            "avg_messages_per_user": avg_messages_per_user,
            "active_users_7d": active_users,
            "engagement_rate": engagement_rate,
            "total_users": total_users,
        }

    @classmethod
    def get_dashboard_overview(cls) -> Dict[str, Any]:
        return {
            "metrics": [
                cls.get_total_users().to_dict(),
                cls.get_total_messages().to_dict(),
                cls.get_total_conversations().to_dict(),
                cls.get_active_users_count().to_dict(),
            ],
            "generated_at": datetime.now().isoformat(),
        }

    @classmethod
    def get_chart_data(cls, chart_type: str, **kwargs) -> Dict[str, Any]:
        chart_generators = {
            "messages_per_day": cls.get_messages_per_day,
            "users_per_day": cls.get_users_per_day,
            "conversations_per_day": cls.get_conversations_per_day,
            "messages_by_hour": cls.get_messages_by_hour,
            "message_type_distribution": cls.get_message_type_distribution,
        }
        
        if chart_type not in chart_generators:
            return {"error": f"Unknown chart type: {chart_type}"}
        
        generator = chart_generators[chart_type]
        days = kwargs.get("days", 7)
        
        if chart_type in ["messages_per_day", "users_per_day", "conversations_per_day", "messages_by_hour"]:
            data = generator(days=days)
        else:
            data = generator()
        
        return {
            "chart_type": chart_type,
            "data": [dp.to_dict() for dp in data],
            "generated_at": datetime.now().isoformat(),
        }

    @classmethod
    def get_all_analytics(cls) -> Dict[str, Any]:
        return {
            "overview": cls.get_dashboard_overview(),
            "charts": {
                "messages_per_day": cls.get_messages_per_day(30),
                "users_per_day": cls.get_users_per_day(30),
                "conversations_per_day": cls.get_conversations_per_day(30),
                "messages_by_hour": cls.get_messages_by_hour(30),
                "message_type_distribution": cls.get_message_type_distribution(),
            },
            "top_lists": {
                "active_users": cls.get_top_active_users(),
                "conversations": cls.get_top_conversations(),
            },
            "engagement": cls.get_engagement_metrics(),
            "generated_at": datetime.now().isoformat(),
        }
