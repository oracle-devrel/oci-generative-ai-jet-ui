"""Profile repository for user profile data access."""

from typing import Any

from fittrack.core.database import execute_dml, execute_json_query
from fittrack.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[dict[str, Any]]):
    """Repository for Profile entities."""

    def __init__(self):
        """Initialize ProfileRepository."""
        super().__init__(duality_view="profiles_dv")

    def find_by_user_id(self, user_id: str) -> dict[str, Any] | None:
        """Find profile by user ID.

        Args:
            user_id: User ID.

        Returns:
            Profile document if found, None otherwise.
        """
        results = self.find_by_field("user_id", user_id, limit=1)
        return results[0] if results else None

    def find_by_tier(
        self,
        tier_code: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find profiles by tier code.

        Args:
            tier_code: Tier code to filter by (e.g., "M-30-39-INT").
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of profiles in the given tier.
        """
        where_clause = "JSON_VALUE(data, '$.tier_code') = :tier_code"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"tier_code": tier_code},
            limit=limit,
            offset=offset,
        )

    def find_by_state(self, state_code: str) -> list[dict[str, Any]]:
        """Find profiles by state of residence.

        Args:
            state_code: Two-letter state code.

        Returns:
            List of profiles in the given state.
        """
        return self.find_by_field("state_of_residence", state_code.upper())

    def update_tier_code(self, profile_id: str, tier_code: str) -> bool:
        """Update profile's tier code.

        Args:
            profile_id: Profile ID.
            tier_code: New tier code.

        Returns:
            True if updated, False if not found.
        """
        sql = """
            UPDATE profiles
            SET tier_code = :tier_code,
                updated_at = SYSTIMESTAMP
            WHERE id = :profile_id
        """
        rowcount = execute_dml(
            sql,
            {"tier_code": tier_code, "profile_id": profile_id},
        )
        return rowcount > 0

    def count_by_tier(self, tier_code: str) -> int:
        """Count profiles in a tier.

        Args:
            tier_code: Tier code to count.

        Returns:
            Number of profiles in the tier.
        """
        where_clause = "JSON_VALUE(data, '$.tier_code') = :tier_code"
        return self.count(where_clause, {"tier_code": tier_code})
