"""Data source layer for analytics - handles database access."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database import get_db
from backend.errors import DataSourceError


class AnalyticsDataSource:
    """Data source for analytics - abstracts database queries."""

    @staticmethod
    def _format_date(dt: datetime) -> str:
        """Format datetime to date string."""
        return dt.strftime("%Y-%m-%d")

    @staticmethod
    def get_date_range(period: str) -> tuple:
        """Get start and end dates for a given period."""
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

    def get_total_users(self) -> int:
        """Get total count of users."""
        try:
            db = get_db()
            row = db.execute("SELECT COUNT(*) as count FROM users").fetchone()
            return row["count"] if row else 0
        except Exception as e:
            raise DataSourceError(f"Failed to get total users: {e}", source="database")

    def get_users_before_date(self, date: str) -> int:
        """Get count of users created before a specific date."""
        try:
            db = get_db()
            row = db.execute(
                "SELECT COUNT(*) as count FROM users WHERE created_at < ?",
                (date,)
            ).fetchone()
            return row["count"] if row else 0
        except Exception as e:
            raise DataSourceError(f"Failed to get users before date: {e}", source="database")

    def get_total_messages(self) -> int:
        """Get total count of messages."""
        try:
            db = get_db()
            row = db.execute("SELECT COUNT(*) as count FROM messages").fetchone()
            return row["count"] if row else 0
        except Exception as e:
            raise DataSourceError(f"Failed to get total messages: {e}", source="database")

    def get_messages_before_date(self, date: str) -> int:
        """Get count of messages created before a specific date."""
        try:
            db = get_db()
            row = db.execute(
                "SELECT COUNT(*) as count FROM messages WHERE created_at < ?",
                (date,)
            ).fetchone()
            return row["count"] if row else 0
        except Exception as e:
            raise DataSourceError(f"Failed to get messages before date: {e}", source="database")

    def get_total_conversations(self) -> int:
        """Get total count of conversations."""
        try:
            db = get_db()
            row = db.execute("SELECT COUNT(*) as count FROM conversations").fetchone()
            return row["count"] if row else 0
        except Exception as e:
            raise DataSourceError(f"Failed to get total conversations: {e}", source="database")

    def get_conversations_before_date(self, date: str) -> int:
        """Get count of conversations created before a specific date."""
        try:
            db = get_db()
            row = db.execute(
                "SELECT COUNT(*) as count FROM conversations WHERE created_at < ?",
                (date,)
            ).fetchone()
            return row["count"] if row else 0
        except Exception as e:
            raise DataSourceError(f"Failed to get conversations before date: {e}", source="database")

    def get_active_users_count(self, period: str) -> int:
        """Get count of active users in a period."""
        try:
            db = get_db()
            start_date, end_date = self.get_date_range(period)
            
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
            
            return row["count"] if row else 0
        except Exception as e:
            raise DataSourceError(f"Failed to get active users: {e}", source="database")

    def get_messages_per_day(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get message counts grouped by day."""
        try:
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
            
            return [{"date": row["date"], "count": row["count"]} for row in rows]
        except Exception as e:
            raise DataSourceError(f"Failed to get messages per day: {e}", source="database")

    def get_users_per_day(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get user counts grouped by day."""
        try:
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
            
            return [{"date": row["date"], "count": row["count"]} for row in rows]
        except Exception as e:
            raise DataSourceError(f"Failed to get users per day: {e}", source="database")

    def get_conversations_per_day(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get conversation counts grouped by day."""
        try:
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
            
            return [{"date": row["date"], "count": row["count"]} for row in rows]
        except Exception as e:
            raise DataSourceError(f"Failed to get conversations per day: {e}", source="database")

    def get_messages_by_hour(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get message counts grouped by hour of day."""
        try:
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
            
            return [{"hour": row["hour"], "count": row["count"]} for row in rows]
        except Exception as e:
            raise DataSourceError(f"Failed to get messages by hour: {e}", source="database")

    def get_message_type_distribution(self) -> List[Dict[str, Any]]:
        """Get distribution of message types."""
        try:
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
                {
                    "message_type": row["message_type"],
                    "count": row["count"],
                    "percentage": round((row["count"] / total) * 100, 2)
                }
                for row in rows
            ]
        except Exception as e:
            raise DataSourceError(f"Failed to get message type distribution: {e}", source="database")

    def get_top_active_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most active users by message count."""
        try:
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
        except Exception as e:
            raise DataSourceError(f"Failed to get top active users: {e}", source="database")

    def get_top_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most active conversations by message count."""
        try:
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
        except Exception as e:
            raise DataSourceError(f"Failed to get top conversations: {e}", source="database")

    def get_engagement_metrics(self) -> Dict[str, Any]:
        """Get engagement metrics."""
        try:
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
        except Exception as e:
            raise DataSourceError(f"Failed to get engagement metrics: {e}", source="database")
