"""Prize repository for drawing prizes data access."""

from typing import Any

from fittrack.core.database import execute_json_query
from fittrack.models.enums import FulfillmentType
from fittrack.repositories.base import BaseRepository


class PrizeRepository(BaseRepository[dict[str, Any]]):
    """Repository for Prize entities."""

    def __init__(self):
        """Initialize PrizeRepository."""
        super().__init__(duality_view="prizes_dv")

    def find_by_drawing(
        self,
        drawing_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find prizes for a drawing.

        Args:
            drawing_id: Drawing ID.
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of prize documents ordered by rank.
        """
        where_clause = "JSON_VALUE(data, '$.drawing_id') = :drawing_id"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"drawing_id": drawing_id},
            order_by="TO_NUMBER(JSON_VALUE(data, '$.rank')) ASC",
            limit=limit,
            offset=offset,
        )

    def find_by_sponsor(
        self,
        sponsor_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find prizes from a sponsor.

        Args:
            sponsor_id: Sponsor ID.
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of prizes from the sponsor.
        """
        where_clause = "JSON_VALUE(data, '$.sponsor_id') = :sponsor_id"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"sponsor_id": sponsor_id},
            order_by="JSON_VALUE(data, '$.created_at') DESC",
            limit=limit,
            offset=offset,
        )

    def find_by_fulfillment_type(
        self,
        fulfillment_type: FulfillmentType,
    ) -> list[dict[str, Any]]:
        """Find prizes by fulfillment type.

        Args:
            fulfillment_type: Type of fulfillment.

        Returns:
            List of prizes with the given fulfillment type.
        """
        return self.find_by_field("fulfillment_type", fulfillment_type.value)

    def get_total_value_by_drawing(self, drawing_id: str) -> float:
        """Get total prize value for a drawing.

        Args:
            drawing_id: Drawing ID.

        Returns:
            Total USD value of all prizes.
        """
        from fittrack.core.database import execute_query_one

        sql = """
            SELECT COALESCE(SUM(value_usd * quantity), 0) as total
            FROM prizes
            WHERE drawing_id = :drawing_id
        """
        result = execute_query_one(sql, {"drawing_id": drawing_id})
        return float(result["total"]) if result else 0.0

    def count_by_drawing(self, drawing_id: str) -> int:
        """Count prizes in a drawing.

        Args:
            drawing_id: Drawing ID.

        Returns:
            Number of prize tiers in the drawing.
        """
        where_clause = "JSON_VALUE(data, '$.drawing_id') = :drawing_id"
        return self.count(where_clause, {"drawing_id": drawing_id})
