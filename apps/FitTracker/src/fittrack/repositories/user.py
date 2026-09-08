"""User repository for user data access."""

from typing import Any

from fittrack.core.database import execute_dml, execute_json_query
from fittrack.models.enums import UserStatus
from fittrack.repositories.base import BaseRepository


class UserRepository(BaseRepository[dict[str, Any]]):
    """Repository for User entities."""

    def __init__(self):
        """Initialize UserRepository."""
        super().__init__(duality_view="users_dv")

    def find_by_email(self, email: str) -> dict[str, Any] | None:
        """Find user by email (case-insensitive).

        Args:
            email: User email address.

        Returns:
            User document if found, None otherwise.
        """
        where_clause = "LOWER(JSON_VALUE(data, '$.email')) = LOWER(:email)"
        results = execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"email": email.lower()},
        )
        return results[0] if results else None

    def find_by_status(self, status: UserStatus) -> list[dict[str, Any]]:
        """Find users by status.

        Args:
            status: User status to filter by.

        Returns:
            List of users with the given status.
        """
        return self.find_by_field("status", status.value)

    def find_by_role(self, role: str) -> list[dict[str, Any]]:
        """Find users by role.

        Args:
            role: User role to filter by.

        Returns:
            List of users with the given role.
        """
        return self.find_by_field("role", role)

    def update_point_balance(
        self,
        user_id: str,
        new_balance: int,
        expected_version: int,
    ) -> bool:
        """Update user's point balance with optimistic locking.

        Args:
            user_id: User ID.
            new_balance: New point balance.
            expected_version: Expected version for optimistic locking.

        Returns:
            True if updated, False if version mismatch or not found.
        """
        sql = """
            UPDATE users
            SET point_balance = :new_balance,
                version = version + 1,
                updated_at = SYSTIMESTAMP
            WHERE id = :user_id
            AND version = :expected_version
        """
        rowcount = execute_dml(
            sql,
            {
                "new_balance": new_balance,
                "user_id": user_id,
                "expected_version": expected_version,
            },
        )
        return rowcount > 0

    def increment_point_balance(
        self,
        user_id: str,
        amount: int,
        expected_version: int,
    ) -> bool:
        """Increment user's point balance with optimistic locking.

        Args:
            user_id: User ID.
            amount: Amount to add (positive) or subtract (negative).
            expected_version: Expected version for optimistic locking.

        Returns:
            True if updated, False if version mismatch or not found.
        """
        sql = """
            UPDATE users
            SET point_balance = point_balance + :amount,
                version = version + 1,
                updated_at = SYSTIMESTAMP
            WHERE id = :user_id
            AND version = :expected_version
            AND point_balance + :amount >= 0
        """
        rowcount = execute_dml(
            sql,
            {
                "amount": amount,
                "user_id": user_id,
                "expected_version": expected_version,
            },
        )
        return rowcount > 0

    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp.

        Args:
            user_id: User ID.

        Returns:
            True if updated, False if not found.
        """
        sql = """
            UPDATE users
            SET last_login_at = SYSTIMESTAMP,
                updated_at = SYSTIMESTAMP
            WHERE id = :user_id
        """
        rowcount = execute_dml(sql, {"user_id": user_id})
        return rowcount > 0

    def verify_email(self, user_id: str) -> bool:
        """Mark user's email as verified and activate account.

        Args:
            user_id: User ID.

        Returns:
            True if updated, False if not found.
        """
        sql = """
            UPDATE users
            SET email_verified = 1,
                email_verified_at = SYSTIMESTAMP,
                status = 'active',
                updated_at = SYSTIMESTAMP
            WHERE id = :user_id
        """
        rowcount = execute_dml(sql, {"user_id": user_id})
        return rowcount > 0
