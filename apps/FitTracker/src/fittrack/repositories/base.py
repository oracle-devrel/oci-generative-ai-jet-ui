"""Base repository with generic CRUD operations via JSON Duality Views."""

from typing import Any, Generic, TypeVar

from fittrack.core.database import (
    count_json_documents,
    delete_json_document,
    execute_json_query,
    insert_json_document,
    update_json_document,
)

T = TypeVar("T", bound=dict[str, Any])


class BaseRepository(Generic[T]):
    """Base repository providing CRUD operations via JSON Duality Views."""

    def __init__(
        self,
        duality_view: str,
        id_field: str = "_id",
    ):
        """Initialize repository.

        Args:
            duality_view: Name of the JSON Duality View.
            id_field: Name of the ID field in JSON documents.
        """
        self.duality_view = duality_view
        self.id_field = id_field

    def find_all(
        self,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
    ) -> list[T]:
        """Find all documents with optional pagination.

        Args:
            limit: Maximum number of documents to return.
            offset: Number of documents to skip.
            order_by: ORDER BY clause for sorting.

        Returns:
            List of documents.
        """
        return execute_json_query(
            duality_view=self.duality_view,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )

    def find_by_id(self, id_value: str) -> T | None:
        """Find document by ID.

        Args:
            id_value: Document ID.

        Returns:
            Document if found, None otherwise.
        """
        where_clause = f"JSON_VALUE(data, '$.{self.id_field}') = :id_value"
        results = execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"id_value": id_value},
        )
        return results[0] if results else None

    def find_by_field(
        self,
        field: str,
        value: Any,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[T]:
        """Find documents by a specific field value.

        Args:
            field: JSON path to field (e.g., 'status', 'user_id').
            value: Value to match.
            limit: Maximum number of documents.
            offset: Number to skip.

        Returns:
            List of matching documents.
        """
        where_clause = f"JSON_VALUE(data, '$.{field}') = :value"
        return execute_json_query(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"value": value},
            limit=limit,
            offset=offset,
        )

    def create(self, document: T) -> T:
        """Create a new document.

        Args:
            document: Document to insert.

        Returns:
            Inserted document.
        """
        return insert_json_document(
            duality_view=self.duality_view,
            document=document,
        )

    def update(self, id_value: str, document: T) -> bool:
        """Update an existing document.

        Args:
            id_value: Document ID.
            document: Updated document.

        Returns:
            True if updated, False if not found.
        """
        return update_json_document(
            duality_view=self.duality_view,
            id_field=self.id_field,
            id_value=id_value,
            document=document,
        )

    def delete(self, id_value: str) -> bool:
        """Delete a document.

        Args:
            id_value: Document ID.

        Returns:
            True if deleted, False if not found.
        """
        return delete_json_document(
            duality_view=self.duality_view,
            id_field=self.id_field,
            id_value=id_value,
        )

    def count(self, where_clause: str | None = None, params: dict | None = None) -> int:
        """Count documents.

        Args:
            where_clause: Optional WHERE clause.
            params: Query parameters.

        Returns:
            Number of documents.
        """
        return count_json_documents(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params=params,
        )

    def exists(self, id_value: str) -> bool:
        """Check if document exists.

        Args:
            id_value: Document ID.

        Returns:
            True if exists, False otherwise.
        """
        where_clause = f"JSON_VALUE(data, '$.{self.id_field}') = :id_value"
        count = count_json_documents(
            duality_view=self.duality_view,
            where_clause=where_clause,
            params={"id_value": id_value},
        )
        return count > 0
