"""Point transaction repository for points ledger access."""

from datetime import datetime
from typing import Any

from fittrack.core.database import execute_json_query, execute_query_one
from fittrack.models.enums import TransactionType
from fittrack.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[dict[str, Any]]):
    """Repository for PointTransaction entities."""

    def __init__(self):
        """Initialize TransactionRepository."""
        super().__init__(duality_view="point_transactions_dv")

    def find_by_user(
        self,
        user_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find transactions for a user.

        Args:
            user_id: User ID.
            limit: Maximum number to return.
            offset: Number to skip.

        Returns:
            List of transaction documents, newest first.
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

    def find_by_user_and_type(
        self,
        user_id: str,
        transaction_type: TransactionType,
    ) -> list[dict[str, Any]]:
        """Find transactions for a user of a specific type.

        Args:
            user_id: User ID.
            transaction_type: Type of transaction.

        Returns:
            List of transactions of the given type.
        """
        where_clause = """
            JSON_VALUE(data, '$.user_id') = :user_id
            AND JSON_VALUE(data, '$.transaction_type') = :transaction_type
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={
                "user_id": user_id,
                "transaction_type": transaction_type.value,
            },
            order_by="JSON_VALUE(data, '$.created_at') DESC",
        )

    def find_by_reference(
        self,
        reference_type: str,
        reference_id: str,
    ) -> list[dict[str, Any]]:
        """Find transactions by reference.

        Args:
            reference_type: Type of reference (activity, ticket_purchase, etc.).
            reference_id: ID of the referenced entity.

        Returns:
            List of transactions with the given reference.
        """
        where_clause = """
            JSON_VALUE(data, '$.reference_type') = :reference_type
            AND JSON_VALUE(data, '$.reference_id') = :reference_id
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={
                "reference_type": reference_type,
                "reference_id": reference_id,
            },
        )

    def calculate_balance(self, user_id: str) -> int:
        """Calculate current point balance from transactions.

        Args:
            user_id: User ID.

        Returns:
            Calculated point balance.
        """
        sql = """
            SELECT COALESCE(
                SUM(CASE
                    WHEN transaction_type = 'earn' THEN amount
                    WHEN transaction_type = 'spend' THEN -amount
                    WHEN transaction_type = 'adjust' THEN amount
                    WHEN transaction_type = 'expire' THEN -amount
                    ELSE 0
                END), 0
            ) as balance
            FROM point_transactions
            WHERE user_id = :user_id
        """
        result = execute_query_one(sql, {"user_id": user_id})
        return int(result["balance"]) if result else 0

    def get_last_balance(self, user_id: str) -> int:
        """Get the balance_after from the most recent transaction.

        Args:
            user_id: User ID.

        Returns:
            Last recorded balance, or 0 if no transactions.
        """
        sql = """
            SELECT balance_after
            FROM point_transactions
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            FETCH FIRST 1 ROW ONLY
        """
        result = execute_query_one(sql, {"user_id": user_id})
        return int(result["balance_after"]) if result else 0

    def find_by_date_range(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Find transactions in a date range.

        Args:
            user_id: User ID.
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            List of transactions in the date range.
        """
        where_clause = """
            JSON_VALUE(data, '$.user_id') = :user_id
            AND TO_TIMESTAMP(JSON_VALUE(data, '$.created_at'), 'YYYY-MM-DD"T"HH24:MI:SS.FF"Z"') >= :start_date
            AND TO_TIMESTAMP(JSON_VALUE(data, '$.created_at'), 'YYYY-MM-DD"T"HH24:MI:SS.FF"Z"') <= :end_date
        """
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
            },
            order_by="JSON_VALUE(data, '$.created_at') ASC",
        )

    def sum_earned_today(self, user_id: str, target_date: datetime) -> int:
        """Sum points earned today (for daily cap check).

        Args:
            user_id: User ID.
            target_date: Date to sum.

        Returns:
            Total points earned on the given date.
        """
        sql = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM point_transactions
            WHERE user_id = :user_id
            AND transaction_type = 'earn'
            AND TRUNC(created_at) = TRUNC(:target_date)
        """
        result = execute_query_one(sql, {"user_id": user_id, "target_date": target_date})
        return int(result["total"]) if result else 0
