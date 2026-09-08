"""Ticket repository for sweepstakes entries data access."""

from typing import Any

from fittrack.core.database import (
    count_json_documents,
    execute_dml,
    execute_json_query,
)
from fittrack.repositories.base import BaseRepository


class TicketRepository(BaseRepository[dict[str, Any]]):
    """Repository for Ticket entities."""

    def __init__(self):
        """Initialize TicketRepository."""
        super().__init__(duality_view="tickets_dv")

    def find_by_drawing(
        self,
        drawing_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find tickets for a drawing.

        Args:
            drawing_id: Drawing ID.
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of ticket documents.
        """
        where_clause = "JSON_VALUE(data, '$.drawing_id') = :drawing_id"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"drawing_id": drawing_id},
            order_by="JSON_VALUE(data, '$.created_at') ASC",
            limit=limit,
            offset=offset,
        )

    def find_by_user(
        self,
        user_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find tickets for a user.

        Args:
            user_id: User ID.
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of ticket documents.
        """
        where_clause = "JSON_VALUE(data, '$.user_id') = :user_id"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"user_id": user_id},
            order_by="JSON_VALUE(data, '$.created_at') DESC",
            limit=limit,
            offset=offset,
        )

    def find_by_user_and_drawing(
        self,
        user_id: str,
        drawing_id: str,
    ) -> list[dict[str, Any]]:
        """Find tickets for a user in a specific drawing.

        Args:
            user_id: User ID.
            drawing_id: Drawing ID.

        Returns:
            List of user's tickets in the drawing.
        """
        where_clause = """
            JSON_VALUE(data, '$.user_id') = :user_id
            AND JSON_VALUE(data, '$.drawing_id') = :drawing_id
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"user_id": user_id, "drawing_id": drawing_id},
        )

    def find_winners(self, drawing_id: str) -> list[dict[str, Any]]:
        """Find winning tickets for a drawing.

        Args:
            drawing_id: Drawing ID.

        Returns:
            List of winning tickets.
        """
        where_clause = """
            JSON_VALUE(data, '$.drawing_id') = :drawing_id
            AND JSON_VALUE(data, '$.is_winner') = 'true'
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"drawing_id": drawing_id},
            order_by="JSON_VALUE(data, '$.ticket_number') ASC",
        )

    def count_by_drawing(self, drawing_id: str) -> int:
        """Count tickets in a drawing.

        Args:
            drawing_id: Drawing ID.

        Returns:
            Number of tickets in the drawing.
        """
        where_clause = "JSON_VALUE(data, '$.drawing_id') = :drawing_id"
        return count_json_documents(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"drawing_id": drawing_id},
        )

    def count_by_user_and_drawing(self, user_id: str, drawing_id: str) -> int:
        """Count user's tickets in a drawing.

        Args:
            user_id: User ID.
            drawing_id: Drawing ID.

        Returns:
            Number of user's tickets in the drawing.
        """
        where_clause = """
            JSON_VALUE(data, '$.user_id') = :user_id
            AND JSON_VALUE(data, '$.drawing_id') = :drawing_id
        """
        return count_json_documents(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"user_id": user_id, "drawing_id": drawing_id},
        )

    def assign_ticket_numbers(self, drawing_id: str) -> int:
        """Assign sequential ticket numbers to all tickets in a drawing.

        Called when ticket sales close.

        Args:
            drawing_id: Drawing ID.

        Returns:
            Number of tickets assigned numbers.
        """
        # Use Oracle's ROW_NUMBER to assign sequential numbers
        sql = """
            MERGE INTO tickets t
            USING (
                SELECT id,
                       ROW_NUMBER() OVER (ORDER BY created_at) as ticket_num
                FROM tickets
                WHERE drawing_id = :drawing_id
            ) src
            ON (t.id = src.id)
            WHEN MATCHED THEN UPDATE
                SET t.ticket_number = src.ticket_num,
                    t.updated_at = SYSTIMESTAMP
        """
        return execute_dml(sql, {"drawing_id": drawing_id})

    def mark_winner(
        self,
        ticket_id: str,
        prize_id: str,
    ) -> bool:
        """Mark a ticket as a winner.

        Args:
            ticket_id: Ticket ID.
            prize_id: Prize ID won.

        Returns:
            True if updated, False if not found.
        """
        sql = """
            UPDATE tickets
            SET is_winner = 1,
                prize_id = :prize_id,
                updated_at = SYSTIMESTAMP
            WHERE id = :ticket_id
        """
        rowcount = execute_dml(
            sql,
            {"prize_id": prize_id, "ticket_id": ticket_id},
        )
        return rowcount > 0

    def find_user_wins(self, user_id: str) -> list[dict[str, Any]]:
        """Find all winning tickets for a user.

        Args:
            user_id: User ID.

        Returns:
            List of winning tickets.
        """
        where_clause = """
            JSON_VALUE(data, '$.user_id') = :user_id
            AND JSON_VALUE(data, '$.is_winner') = 'true'
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"user_id": user_id},
            order_by="JSON_VALUE(data, '$.created_at') DESC",
        )
