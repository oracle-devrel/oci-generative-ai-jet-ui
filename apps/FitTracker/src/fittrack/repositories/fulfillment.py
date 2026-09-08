"""Fulfillment repository for prize fulfillment tracking."""

from datetime import datetime, timedelta
from typing import Any

from fittrack.core.database import execute_dml, execute_json_query
from fittrack.models.enums import FulfillmentStatus
from fittrack.repositories.base import BaseRepository


class FulfillmentRepository(BaseRepository[dict[str, Any]]):
    """Repository for PrizeFulfillment entities."""

    def __init__(self):
        """Initialize FulfillmentRepository."""
        super().__init__(duality_view="prize_fulfillments_dv")

    def find_by_status(
        self,
        status: FulfillmentStatus,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find fulfillments by status.

        Args:
            status: Fulfillment status to filter by.
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of fulfillments with the given status.
        """
        where_clause = "JSON_VALUE(data, '$.status') = :status"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"status": status.value},
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
        """Find fulfillments for a user.

        Args:
            user_id: User ID.
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of fulfillment documents.
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

    def find_by_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        """Find fulfillment for a ticket.

        Args:
            ticket_id: Ticket ID.

        Returns:
            Fulfillment document if found, None otherwise.
        """
        results = self.find_by_field("ticket_id", ticket_id, limit=1)
        return results[0] if results else None

    def find_overdue(self, days: int = 30) -> list[dict[str, Any]]:
        """Find fulfillments that are overdue for action.

        Args:
            days: Number of days after notification to consider overdue.

        Returns:
            List of overdue fulfillments.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        where_clause = """
            JSON_VALUE(data, '$.status') = 'winner_notified'
            AND TO_TIMESTAMP(JSON_VALUE(data, '$.notified_at'), 'YYYY-MM-DD"T"HH24:MI:SS.FF"Z"') < :cutoff
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"cutoff": cutoff},
        )

    def find_pending_shipment(self) -> list[dict[str, Any]]:
        """Find fulfillments ready for shipment.

        Returns:
            List of fulfillments with confirmed addresses awaiting shipment.
        """
        where_clause = "JSON_VALUE(data, '$.status') = 'address_confirmed'"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            order_by="JSON_VALUE(data, '$.address_confirmed_at') ASC",
        )

    def update_status(
        self,
        fulfillment_id: str,
        status: FulfillmentStatus,
    ) -> bool:
        """Update fulfillment status.

        Args:
            fulfillment_id: Fulfillment ID.
            status: New status.

        Returns:
            True if updated, False if not found.
        """
        # Determine which timestamp field to update based on status
        timestamp_field = {
            FulfillmentStatus.WINNER_NOTIFIED: "notified_at",
            FulfillmentStatus.ADDRESS_CONFIRMED: "address_confirmed_at",
            FulfillmentStatus.SHIPPED: "shipped_at",
            FulfillmentStatus.DELIVERED: "delivered_at",
            FulfillmentStatus.FORFEITED: "forfeit_at",
        }.get(status)

        if timestamp_field:
            sql = f"""
                UPDATE prize_fulfillments
                SET status = :status,
                    {timestamp_field} = SYSTIMESTAMP,
                    updated_at = SYSTIMESTAMP
                WHERE id = :fulfillment_id
            """
        else:
            sql = """
                UPDATE prize_fulfillments
                SET status = :status,
                    updated_at = SYSTIMESTAMP
                WHERE id = :fulfillment_id
            """

        rowcount = execute_dml(
            sql,
            {"status": status.value, "fulfillment_id": fulfillment_id},
        )
        return rowcount > 0

    def update_shipping_info(
        self,
        fulfillment_id: str,
        tracking_number: str,
        carrier: str,
    ) -> bool:
        """Update shipping information.

        Args:
            fulfillment_id: Fulfillment ID.
            tracking_number: Shipping tracking number.
            carrier: Shipping carrier name.

        Returns:
            True if updated, False if not found.
        """
        sql = """
            UPDATE prize_fulfillments
            SET tracking_number = :tracking_number,
                carrier = :carrier,
                status = 'shipped',
                shipped_at = SYSTIMESTAMP,
                updated_at = SYSTIMESTAMP
            WHERE id = :fulfillment_id
        """
        rowcount = execute_dml(
            sql,
            {
                "tracking_number": tracking_number,
                "carrier": carrier,
                "fulfillment_id": fulfillment_id,
            },
        )
        return rowcount > 0

    def update_address(
        self,
        fulfillment_id: str,
        shipping_address: dict[str, Any],
    ) -> bool:
        """Update shipping address.

        Args:
            fulfillment_id: Fulfillment ID.
            shipping_address: New shipping address.

        Returns:
            True if updated, False if not found.
        """
        import json

        sql = """
            UPDATE prize_fulfillments
            SET shipping_address = :shipping_address,
                updated_at = SYSTIMESTAMP
            WHERE id = :fulfillment_id
        """
        rowcount = execute_dml(
            sql,
            {
                "shipping_address": json.dumps(shipping_address),
                "fulfillment_id": fulfillment_id,
            },
        )
        return rowcount > 0
