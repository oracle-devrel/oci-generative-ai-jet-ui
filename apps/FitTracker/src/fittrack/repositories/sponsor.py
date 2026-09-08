"""Sponsor repository for prize sponsor data access."""

from typing import Any

from fittrack.core.database import execute_json_query
from fittrack.models.enums import SponsorStatus
from fittrack.repositories.base import BaseRepository


class SponsorRepository(BaseRepository[dict[str, Any]]):
    """Repository for Sponsor entities."""

    def __init__(self):
        """Initialize SponsorRepository."""
        super().__init__(duality_view="sponsors_dv")

    def find_active(
        self,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find active sponsors.

        Args:
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of active sponsor documents.
        """
        where_clause = "JSON_VALUE(data, '$.status') = 'active'"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            order_by="JSON_VALUE(data, '$.name') ASC",
            limit=limit,
            offset=offset,
        )

    def find_by_status(
        self,
        status: SponsorStatus,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find sponsors by status.

        Args:
            status: Sponsor status to filter by.
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of sponsors with the given status.
        """
        where_clause = "JSON_VALUE(data, '$.status') = :status"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"status": status.value},
            order_by="JSON_VALUE(data, '$.name') ASC",
            limit=limit,
            offset=offset,
        )

    def find_by_name(self, name: str) -> dict[str, Any] | None:
        """Find sponsor by name (case-insensitive).

        Args:
            name: Sponsor name.

        Returns:
            Sponsor document if found, None otherwise.
        """
        where_clause = "LOWER(JSON_VALUE(data, '$.name')) = LOWER(:name)"
        results = execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"name": name.lower()},
        )
        return results[0] if results else None

    def search_by_name(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search sponsors by name.

        Args:
            query: Search query.
            limit: Maximum results.

        Returns:
            List of matching sponsors.
        """
        where_clause = "LOWER(JSON_VALUE(data, '$.name')) LIKE LOWER(:query)"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"query": f"%{query}%"},
            order_by="JSON_VALUE(data, '$.name') ASC",
            limit=limit,
        )
