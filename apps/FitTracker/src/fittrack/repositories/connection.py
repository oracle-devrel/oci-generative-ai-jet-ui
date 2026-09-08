"""Tracker connection repository for fitness API connections."""

from datetime import datetime, timedelta
from typing import Any

from fittrack.core.database import execute_dml, execute_json_query
from fittrack.models.enums import Provider, SyncStatus
from fittrack.repositories.base import BaseRepository


class ConnectionRepository(BaseRepository[dict[str, Any]]):
    """Repository for TrackerConnection entities."""

    def __init__(self):
        """Initialize ConnectionRepository."""
        super().__init__(duality_view="tracker_connections_dv")

    def find_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Find all connections for a user.

        Args:
            user_id: User ID.

        Returns:
            List of connection documents.
        """
        return self.find_by_field("user_id", user_id)

    def find_by_user_and_provider(
        self,
        user_id: str,
        provider: Provider,
    ) -> dict[str, Any] | None:
        """Find connection by user and provider.

        Args:
            user_id: User ID.
            provider: Tracker provider.

        Returns:
            Connection document if found, None otherwise.
        """
        where_clause = """
            JSON_VALUE(data, '$.user_id') = :user_id
            AND JSON_VALUE(data, '$.provider') = :provider
        """
        results = execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"user_id": user_id, "provider": provider.value},
        )
        return results[0] if results else None

    def find_primary_for_user(self, user_id: str) -> dict[str, Any] | None:
        """Find user's primary connection.

        Args:
            user_id: User ID.

        Returns:
            Primary connection if exists, None otherwise.
        """
        where_clause = """
            JSON_VALUE(data, '$.user_id') = :user_id
            AND JSON_VALUE(data, '$.is_primary') = 'true'
        """
        results = execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"user_id": user_id},
        )
        return results[0] if results else None

    def find_due_for_sync(
        self,
        minutes_since_last: int = 15,
    ) -> list[dict[str, Any]]:
        """Find connections due for sync.

        Args:
            minutes_since_last: Minutes since last sync to consider due.

        Returns:
            List of connections needing sync.
        """
        cutoff = datetime.utcnow() - timedelta(minutes=minutes_since_last)
        where_clause = """
            JSON_VALUE(data, '$.sync_status') != 'syncing'
            AND (
                JSON_VALUE(data, '$.last_sync_at') IS NULL
                OR TO_TIMESTAMP(JSON_VALUE(data, '$.last_sync_at'), 'YYYY-MM-DD"T"HH24:MI:SS.FF"Z"') < :cutoff
            )
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"cutoff": cutoff},
        )

    def find_by_sync_status(self, status: SyncStatus) -> list[dict[str, Any]]:
        """Find connections by sync status.

        Args:
            status: Sync status to filter by.

        Returns:
            List of connections with the given status.
        """
        return self.find_by_field("sync_status", status.value)

    def update_sync_status(
        self,
        connection_id: str,
        status: SyncStatus,
        error_message: str | None = None,
    ) -> bool:
        """Update connection sync status.

        Args:
            connection_id: Connection ID.
            status: New sync status.
            error_message: Error message if status is error.

        Returns:
            True if updated, False if not found.
        """
        if status == SyncStatus.SUCCESS:
            sql = """
                UPDATE tracker_connections
                SET sync_status = :status,
                    last_sync_at = SYSTIMESTAMP,
                    error_message = NULL,
                    updated_at = SYSTIMESTAMP
                WHERE id = :connection_id
            """
            params = {"status": status.value, "connection_id": connection_id}
        else:
            sql = """
                UPDATE tracker_connections
                SET sync_status = :status,
                    error_message = :error_message,
                    updated_at = SYSTIMESTAMP
                WHERE id = :connection_id
            """
            params = {
                "status": status.value,
                "error_message": error_message,
                "connection_id": connection_id,
            }
        rowcount = execute_dml(sql, params)
        return rowcount > 0

    def update_tokens(
        self,
        connection_id: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
    ) -> bool:
        """Update connection OAuth tokens.

        Args:
            connection_id: Connection ID.
            access_token: New access token (should be encrypted before storing).
            refresh_token: New refresh token (should be encrypted before storing).
            expires_at: Token expiration time.

        Returns:
            True if updated, False if not found.
        """
        sql = """
            UPDATE tracker_connections
            SET access_token = :access_token,
                refresh_token = :refresh_token,
                token_expires_at = :expires_at,
                updated_at = SYSTIMESTAMP
            WHERE id = :connection_id
        """
        rowcount = execute_dml(
            sql,
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "connection_id": connection_id,
            },
        )
        return rowcount > 0
