"""Drawing repository for sweepstakes data access."""

from typing import Any

from fittrack.core.database import execute_dml, execute_json_query
from fittrack.models.enums import DrawingStatus, DrawingType
from fittrack.repositories.base import BaseRepository


class DrawingRepository(BaseRepository[dict[str, Any]]):
    """Repository for Drawing entities."""

    def __init__(self):
        """Initialize DrawingRepository."""
        super().__init__(duality_view="drawings_dv")

    def find_by_status(
        self,
        status: DrawingStatus,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find drawings by status.

        Args:
            status: Drawing status to filter by.
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of drawings with the given status.
        """
        where_clause = "JSON_VALUE(data, '$.status') = :status"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"status": status.value},
            order_by="JSON_VALUE(data, '$.drawing_time') ASC",
            limit=limit,
            offset=offset,
        )

    def find_by_type(
        self,
        drawing_type: DrawingType,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find drawings by type.

        Args:
            drawing_type: Drawing type to filter by.
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of drawings of the given type.
        """
        where_clause = "JSON_VALUE(data, '$.drawing_type') = :drawing_type"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"drawing_type": drawing_type.value},
            order_by="JSON_VALUE(data, '$.drawing_time') DESC",
            limit=limit,
            offset=offset,
        )

    def find_open_drawings(self) -> list[dict[str, Any]]:
        """Find all open drawings available for ticket purchase.

        Returns:
            List of open drawings where ticket sales haven't closed.
        """
        where_clause = """
            JSON_VALUE(data, '$.status') = 'open'
            AND TO_TIMESTAMP(JSON_VALUE(data, '$.ticket_sales_close'), 'YYYY-MM-DD"T"HH24:MI:SS.FF"Z"') > SYSTIMESTAMP
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            order_by="JSON_VALUE(data, '$.drawing_time') ASC",
        )

    def find_due_for_execution(self) -> list[dict[str, Any]]:
        """Find drawings due for winner selection.

        Drawings are due when:
        - Status is 'closed'
        - Drawing time has passed

        Returns:
            List of drawings ready for execution.
        """
        where_clause = """
            JSON_VALUE(data, '$.status') = 'closed'
            AND TO_TIMESTAMP(JSON_VALUE(data, '$.drawing_time'), 'YYYY-MM-DD"T"HH24:MI:SS.FF"Z"') <= SYSTIMESTAMP
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            order_by="JSON_VALUE(data, '$.drawing_time') ASC",
        )

    def find_due_for_close(self) -> list[dict[str, Any]]:
        """Find drawings due for ticket sales close.

        Returns:
            List of open drawings past their sales close time.
        """
        where_clause = """
            JSON_VALUE(data, '$.status') = 'open'
            AND TO_TIMESTAMP(JSON_VALUE(data, '$.ticket_sales_close'), 'YYYY-MM-DD"T"HH24:MI:SS.FF"Z"') <= SYSTIMESTAMP
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
        )

    def update_status(self, drawing_id: str, status: DrawingStatus) -> bool:
        """Update drawing status.

        Args:
            drawing_id: Drawing ID.
            status: New status.

        Returns:
            True if updated, False if not found.
        """
        sql = """
            UPDATE drawings
            SET status = :status,
                updated_at = SYSTIMESTAMP
            WHERE id = :drawing_id
        """
        rowcount = execute_dml(
            sql,
            {"status": status.value, "drawing_id": drawing_id},
        )
        return rowcount > 0

    def complete_drawing(
        self,
        drawing_id: str,
        random_seed: str,
        total_tickets: int,
    ) -> bool:
        """Mark drawing as completed with execution details.

        Args:
            drawing_id: Drawing ID.
            random_seed: CSPRNG seed used for winner selection.
            total_tickets: Total tickets in the drawing.

        Returns:
            True if updated, False if not found.
        """
        sql = """
            UPDATE drawings
            SET status = 'completed',
                random_seed = :random_seed,
                total_tickets = :total_tickets,
                completed_at = SYSTIMESTAMP,
                updated_at = SYSTIMESTAMP
            WHERE id = :drawing_id
        """
        rowcount = execute_dml(
            sql,
            {
                "random_seed": random_seed,
                "total_tickets": total_tickets,
                "drawing_id": drawing_id,
            },
        )
        return rowcount > 0

    def increment_ticket_count(self, drawing_id: str, count: int = 1) -> bool:
        """Increment the total ticket count.

        Args:
            drawing_id: Drawing ID.
            count: Number to add.

        Returns:
            True if updated, False if not found.
        """
        sql = """
            UPDATE drawings
            SET total_tickets = total_tickets + :count,
                updated_at = SYSTIMESTAMP
            WHERE id = :drawing_id
        """
        rowcount = execute_dml(
            sql,
            {"count": count, "drawing_id": drawing_id},
        )
        return rowcount > 0
