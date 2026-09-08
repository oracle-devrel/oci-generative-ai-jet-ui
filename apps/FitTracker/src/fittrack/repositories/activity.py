"""Activity repository for fitness activity data access."""

from datetime import date, datetime
from typing import Any

from fittrack.core.database import execute_dml, execute_json_query, execute_query_one
from fittrack.models.enums import ActivityType
from fittrack.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[dict[str, Any]]):
    """Repository for Activity entities."""

    def __init__(self):
        """Initialize ActivityRepository."""
        super().__init__(duality_view="activities_dv")

    def find_by_user(
        self,
        user_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find activities for a user.

        Args:
            user_id: User ID.
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of activity documents.
        """
        where_clause = "JSON_VALUE(data, '$.user_id') = :user_id"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"user_id": user_id},
            order_by="JSON_VALUE(data, '$.start_time') DESC",
            limit=limit,
            offset=offset,
        )

    def find_by_user_and_date_range(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Find activities for a user within a date range.

        Args:
            user_id: User ID.
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            List of activities in the date range.
        """
        where_clause = """
            JSON_VALUE(data, '$.user_id') = :user_id
            AND TO_TIMESTAMP(JSON_VALUE(data, '$.start_time'), 'YYYY-MM-DD"T"HH24:MI:SS.FF"Z"') >= :start_date
            AND TO_TIMESTAMP(JSON_VALUE(data, '$.start_time'), 'YYYY-MM-DD"T"HH24:MI:SS.FF"Z"') <= :end_date
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
            },
            order_by="JSON_VALUE(data, '$.start_time') ASC",
        )

    def find_by_user_and_type(
        self,
        user_id: str,
        activity_type: ActivityType,
    ) -> list[dict[str, Any]]:
        """Find activities for a user of a specific type.

        Args:
            user_id: User ID.
            activity_type: Type of activity.

        Returns:
            List of activities of the given type.
        """
        where_clause = """
            JSON_VALUE(data, '$.user_id') = :user_id
            AND JSON_VALUE(data, '$.activity_type') = :activity_type
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"user_id": user_id, "activity_type": activity_type.value},
        )

    def find_unprocessed(self, limit: int = 100) -> list[dict[str, Any]]:
        """Find unprocessed activities.

        Args:
            limit: Maximum number to return.

        Returns:
            List of unprocessed activities.
        """
        where_clause = "JSON_VALUE(data, '$.processed') = 'false'"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            order_by="JSON_VALUE(data, '$.start_time') ASC",
            limit=limit,
        )

    def find_by_external_id(self, external_id: str) -> dict[str, Any] | None:
        """Find activity by external provider ID.

        Args:
            external_id: External activity ID from provider.

        Returns:
            Activity if found, None otherwise.
        """
        results = self.find_by_field("external_id", external_id, limit=1)
        return results[0] if results else None

    def mark_processed(
        self,
        activity_id: str,
        points_earned: int,
    ) -> bool:
        """Mark activity as processed with points.

        Args:
            activity_id: Activity ID.
            points_earned: Points earned from this activity.

        Returns:
            True if updated, False if not found.
        """
        sql = """
            UPDATE activities
            SET processed = 1,
                points_earned = :points_earned,
                updated_at = SYSTIMESTAMP
            WHERE id = :activity_id
        """
        rowcount = execute_dml(
            sql,
            {"points_earned": points_earned, "activity_id": activity_id},
        )
        return rowcount > 0

    def calculate_daily_totals(
        self,
        user_id: str,
        target_date: date,
    ) -> dict[str, Any] | None:
        """Calculate daily activity totals for a user.

        Args:
            user_id: User ID.
            target_date: Date to calculate totals for.

        Returns:
            Dictionary with totals by activity type and total points.
        """
        sql = """
            SELECT
                SUM(CASE WHEN activity_type = 'steps' THEN
                    COALESCE(JSON_VALUE(metrics, '$.step_count'), 0) ELSE 0 END) as total_steps,
                SUM(CASE WHEN activity_type = 'active_minutes' THEN
                    COALESCE(duration_minutes, 0) ELSE 0 END) as total_active_minutes,
                COUNT(CASE WHEN activity_type = 'workout' AND duration_minutes >= 20 THEN 1 END) as workout_count,
                SUM(points_earned) as total_points
            FROM activities
            WHERE user_id = :user_id
            AND TRUNC(start_time) = :target_date
        """
        return execute_query_one(
            sql,
            {"user_id": user_id, "target_date": target_date},
        )

    def count_workouts_today(self, user_id: str, target_date: date) -> int:
        """Count completed workouts for a user on a given date.

        Args:
            user_id: User ID.
            target_date: Date to count workouts for.

        Returns:
            Number of qualifying workouts (20+ minutes).
        """
        sql = """
            SELECT COUNT(*) as cnt
            FROM activities
            WHERE user_id = :user_id
            AND activity_type = 'workout'
            AND duration_minutes >= 20
            AND TRUNC(start_time) = :target_date
        """
        result = execute_query_one(sql, {"user_id": user_id, "target_date": target_date})
        return result["cnt"] if result else 0
