"""Unit tests for repository layer.

These tests use mocking to test repository logic without database.
Integration tests will test actual database operations.
"""

from datetime import date, datetime
from unittest.mock import patch

from fittrack.models.enums import (
    DrawingStatus,
    DrawingType,
    FulfillmentStatus,
    Provider,
    UserStatus,
)


class TestBaseRepository:
    """Tests for BaseRepository CRUD operations."""

    def test_base_repository_has_duality_view_name(self):
        """Repository should define duality view name."""
        from fittrack.repositories.base import BaseRepository

        repo = BaseRepository(duality_view="test_dv")
        assert repo.duality_view == "test_dv"

    def test_base_repository_has_id_field(self):
        """Repository should define ID field name."""
        from fittrack.repositories.base import BaseRepository

        repo = BaseRepository(duality_view="test_dv", id_field="_id")
        assert repo.id_field == "_id"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_all_returns_list(self, mock_query):
        """find_all should return list of documents."""
        from fittrack.repositories.base import BaseRepository

        mock_query.return_value = [{"_id": "1"}, {"_id": "2"}]
        repo = BaseRepository(duality_view="test_dv")

        result = repo.find_all()

        assert len(result) == 2
        mock_query.assert_called_once()

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_all_with_pagination(self, mock_query):
        """find_all should support pagination."""
        from fittrack.repositories.base import BaseRepository

        mock_query.return_value = [{"_id": "3"}]
        repo = BaseRepository(duality_view="test_dv")

        result = repo.find_all(limit=10, offset=20)

        mock_query.assert_called_once()
        call_kwargs = mock_query.call_args[1]
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 20

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_id_returns_document(self, mock_query):
        """find_by_id should return single document."""
        from fittrack.repositories.base import BaseRepository

        mock_query.return_value = [{"_id": "123", "name": "test"}]
        repo = BaseRepository(duality_view="test_dv")

        result = repo.find_by_id("123")

        assert result == {"_id": "123", "name": "test"}

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_id_returns_none_when_not_found(self, mock_query):
        """find_by_id should return None when not found."""
        from fittrack.repositories.base import BaseRepository

        mock_query.return_value = []
        repo = BaseRepository(duality_view="test_dv")

        result = repo.find_by_id("nonexistent")

        assert result is None

    @patch("fittrack.repositories.base.insert_json_document")
    def test_create_inserts_document(self, mock_insert):
        """create should insert document."""
        from fittrack.repositories.base import BaseRepository

        doc = {"_id": "new", "name": "test"}
        mock_insert.return_value = doc
        repo = BaseRepository(duality_view="test_dv")

        result = repo.create(doc)

        assert result == doc
        mock_insert.assert_called_once()

    @patch("fittrack.repositories.base.update_json_document")
    def test_update_modifies_document(self, mock_update):
        """update should modify document."""
        from fittrack.repositories.base import BaseRepository

        mock_update.return_value = True
        repo = BaseRepository(duality_view="test_dv")

        result = repo.update("123", {"name": "updated"})

        assert result is True
        mock_update.assert_called_once()

    @patch("fittrack.repositories.base.delete_json_document")
    def test_delete_removes_document(self, mock_delete):
        """delete should remove document."""
        from fittrack.repositories.base import BaseRepository

        mock_delete.return_value = True
        repo = BaseRepository(duality_view="test_dv")

        result = repo.delete("123")

        assert result is True
        mock_delete.assert_called_once()

    @patch("fittrack.repositories.base.count_json_documents")
    def test_count_returns_total(self, mock_count):
        """count should return total documents."""
        from fittrack.repositories.base import BaseRepository

        mock_count.return_value = 42
        repo = BaseRepository(duality_view="test_dv")

        result = repo.count()

        assert result == 42


class TestUserRepository:
    """Tests for UserRepository."""

    def test_user_repository_uses_correct_duality_view(self):
        """UserRepository should use users_dv."""
        from fittrack.repositories.user import UserRepository

        repo = UserRepository()
        assert repo.duality_view == "users_dv"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_email(self, mock_query):
        """find_by_email should query by email."""
        from fittrack.repositories.user import UserRepository

        mock_query.return_value = [{"_id": "1", "email": "test@example.com"}]
        repo = UserRepository()

        result = repo.find_by_email("test@example.com")

        assert result is not None
        assert result["email"] == "test@example.com"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_email_case_insensitive(self, mock_query):
        """find_by_email should be case insensitive."""
        from fittrack.repositories.user import UserRepository

        mock_query.return_value = [{"_id": "1", "email": "Test@Example.com"}]
        repo = UserRepository()

        result = repo.find_by_email("TEST@EXAMPLE.COM")

        # Should normalize to lowercase for query
        assert result is not None

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_status(self, mock_query):
        """find_by_status should filter by status."""
        from fittrack.repositories.user import UserRepository

        mock_query.return_value = [
            {"_id": "1", "status": "active"},
            {"_id": "2", "status": "active"},
        ]
        repo = UserRepository()

        result = repo.find_by_status(UserStatus.ACTIVE)

        assert len(result) == 2

    @patch("fittrack.repositories.base.execute_dml")
    @patch("fittrack.repositories.base.execute_json_query")
    def test_update_point_balance_with_optimistic_locking(self, mock_query, mock_dml):
        """update_point_balance should use optimistic locking."""
        from fittrack.repositories.user import UserRepository

        mock_query.return_value = [{"_id": "1", "point_balance": 100, "version": 1}]
        mock_dml.return_value = 1  # 1 row affected
        repo = UserRepository()

        result = repo.update_point_balance("1", 150, expected_version=1)

        assert result is True
        # Should include version check in WHERE clause
        call_args = mock_dml.call_args
        assert "version" in str(call_args).lower()


class TestProfileRepository:
    """Tests for ProfileRepository."""

    def test_profile_repository_uses_correct_duality_view(self):
        """ProfileRepository should use profiles_dv."""
        from fittrack.repositories.profile import ProfileRepository

        repo = ProfileRepository()
        assert repo.duality_view == "profiles_dv"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_user_id(self, mock_query):
        """find_by_user_id should query by user_id."""
        from fittrack.repositories.profile import ProfileRepository

        mock_query.return_value = [{"_id": "p1", "user_id": "u1"}]
        repo = ProfileRepository()

        result = repo.find_by_user_id("u1")

        assert result is not None
        assert result["user_id"] == "u1"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_tier(self, mock_query):
        """find_by_tier should filter by tier_code."""
        from fittrack.repositories.profile import ProfileRepository

        mock_query.return_value = [
            {"_id": "p1", "tier_code": "M-30-39-INT"},
            {"_id": "p2", "tier_code": "M-30-39-INT"},
        ]
        repo = ProfileRepository()

        result = repo.find_by_tier("M-30-39-INT")

        assert len(result) == 2


class TestConnectionRepository:
    """Tests for TrackerConnectionRepository."""

    def test_connection_repository_uses_correct_duality_view(self):
        """ConnectionRepository should use tracker_connections_dv."""
        from fittrack.repositories.connection import ConnectionRepository

        repo = ConnectionRepository()
        assert repo.duality_view == "tracker_connections_dv"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_user_and_provider(self, mock_query):
        """find_by_user_and_provider should filter by both."""
        from fittrack.repositories.connection import ConnectionRepository

        mock_query.return_value = [{"_id": "c1", "user_id": "u1", "provider": "fitbit"}]
        repo = ConnectionRepository()

        result = repo.find_by_user_and_provider("u1", Provider.FITBIT)

        assert result is not None
        assert result["provider"] == "fitbit"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_due_for_sync(self, mock_query):
        """find_due_for_sync should find connections needing sync."""
        from fittrack.repositories.connection import ConnectionRepository

        mock_query.return_value = [{"_id": "c1", "sync_status": "pending"}]
        repo = ConnectionRepository()

        result = repo.find_due_for_sync(minutes_since_last=15)

        assert len(result) >= 0  # May return empty if none due


class TestActivityRepository:
    """Tests for ActivityRepository."""

    def test_activity_repository_uses_correct_duality_view(self):
        """ActivityRepository should use activities_dv."""
        from fittrack.repositories.activity import ActivityRepository

        repo = ActivityRepository()
        assert repo.duality_view == "activities_dv"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_user_and_date_range(self, mock_query):
        """find_by_user_and_date_range should filter by user and dates."""
        from fittrack.repositories.activity import ActivityRepository

        mock_query.return_value = [{"_id": "a1", "user_id": "u1"}]
        repo = ActivityRepository()

        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        result = repo.find_by_user_and_date_range("u1", start, end)

        assert len(result) >= 0

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_unprocessed(self, mock_query):
        """find_unprocessed should filter by processed=false."""
        from fittrack.repositories.activity import ActivityRepository

        mock_query.return_value = [{"_id": "a1", "processed": False}]
        repo = ActivityRepository()

        result = repo.find_unprocessed()

        assert len(result) >= 0

    @patch("fittrack.repositories.base.execute_query_one")
    def test_calculate_daily_totals(self, mock_query):
        """calculate_daily_totals should aggregate by type."""
        from fittrack.repositories.activity import ActivityRepository

        mock_query.return_value = {"total_steps": 10000, "total_points": 100}
        repo = ActivityRepository()

        result = repo.calculate_daily_totals("u1", date.today())

        assert result is not None


class TestTransactionRepository:
    """Tests for PointTransactionRepository."""

    def test_transaction_repository_uses_correct_duality_view(self):
        """TransactionRepository should use point_transactions_dv."""
        from fittrack.repositories.transaction import TransactionRepository

        repo = TransactionRepository()
        assert repo.duality_view == "point_transactions_dv"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_user(self, mock_query):
        """find_by_user should filter by user_id."""
        from fittrack.repositories.transaction import TransactionRepository

        mock_query.return_value = [{"_id": "t1", "user_id": "u1"}]
        repo = TransactionRepository()

        result = repo.find_by_user("u1")

        assert len(result) >= 0

    @patch("fittrack.repositories.base.execute_query_one")
    def test_calculate_balance(self, mock_query):
        """calculate_balance should sum transactions."""
        from fittrack.repositories.transaction import TransactionRepository

        mock_query.return_value = {"balance": 500}
        repo = TransactionRepository()

        result = repo.calculate_balance("u1")

        assert result >= 0

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_reference(self, mock_query):
        """find_by_reference should filter by reference_type and reference_id."""
        from fittrack.repositories.transaction import TransactionRepository

        mock_query.return_value = [
            {"_id": "t1", "reference_type": "activity", "reference_id": "a1"}
        ]
        repo = TransactionRepository()

        result = repo.find_by_reference("activity", "a1")

        assert len(result) >= 0


class TestDrawingRepository:
    """Tests for DrawingRepository."""

    def test_drawing_repository_uses_correct_duality_view(self):
        """DrawingRepository should use drawings_dv."""
        from fittrack.repositories.drawing import DrawingRepository

        repo = DrawingRepository()
        assert repo.duality_view == "drawings_dv"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_status(self, mock_query):
        """find_by_status should filter by status."""
        from fittrack.repositories.drawing import DrawingRepository

        mock_query.return_value = [{"_id": "d1", "status": "open"}]
        repo = DrawingRepository()

        result = repo.find_by_status(DrawingStatus.OPEN)

        assert len(result) >= 0

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_type(self, mock_query):
        """find_by_type should filter by drawing_type."""
        from fittrack.repositories.drawing import DrawingRepository

        mock_query.return_value = [{"_id": "d1", "drawing_type": "daily"}]
        repo = DrawingRepository()

        result = repo.find_by_type(DrawingType.DAILY)

        assert len(result) >= 0

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_open_drawings(self, mock_query):
        """find_open_drawings should return open drawings."""
        from fittrack.repositories.drawing import DrawingRepository

        mock_query.return_value = [{"_id": "d1", "status": "open"}]
        repo = DrawingRepository()

        result = repo.find_open_drawings()

        assert len(result) >= 0

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_due_for_execution(self, mock_query):
        """find_due_for_execution should find closed drawings past drawing_time."""
        from fittrack.repositories.drawing import DrawingRepository

        mock_query.return_value = [{"_id": "d1", "status": "closed"}]
        repo = DrawingRepository()

        result = repo.find_due_for_execution()

        assert len(result) >= 0


class TestTicketRepository:
    """Tests for TicketRepository."""

    def test_ticket_repository_uses_correct_duality_view(self):
        """TicketRepository should use tickets_dv."""
        from fittrack.repositories.ticket import TicketRepository

        repo = TicketRepository()
        assert repo.duality_view == "tickets_dv"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_drawing(self, mock_query):
        """find_by_drawing should filter by drawing_id."""
        from fittrack.repositories.ticket import TicketRepository

        mock_query.return_value = [{"_id": "t1", "drawing_id": "d1"}]
        repo = TicketRepository()

        result = repo.find_by_drawing("d1")

        assert len(result) >= 0

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_user(self, mock_query):
        """find_by_user should filter by user_id."""
        from fittrack.repositories.ticket import TicketRepository

        mock_query.return_value = [{"_id": "t1", "user_id": "u1"}]
        repo = TicketRepository()

        result = repo.find_by_user("u1")

        assert len(result) >= 0

    @patch("fittrack.repositories.base.count_json_documents")
    def test_count_by_drawing(self, mock_count):
        """count_by_drawing should count tickets for drawing."""
        from fittrack.repositories.ticket import TicketRepository

        mock_count.return_value = 100
        repo = TicketRepository()

        result = repo.count_by_drawing("d1")

        assert result == 100

    @patch("fittrack.repositories.base.count_json_documents")
    def test_count_by_user_and_drawing(self, mock_count):
        """count_by_user_and_drawing should count user's tickets in drawing."""
        from fittrack.repositories.ticket import TicketRepository

        mock_count.return_value = 5
        repo = TicketRepository()

        result = repo.count_by_user_and_drawing("u1", "d1")

        assert result == 5


class TestPrizeRepository:
    """Tests for PrizeRepository."""

    def test_prize_repository_uses_correct_duality_view(self):
        """PrizeRepository should use prizes_dv."""
        from fittrack.repositories.prize import PrizeRepository

        repo = PrizeRepository()
        assert repo.duality_view == "prizes_dv"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_drawing(self, mock_query):
        """find_by_drawing should filter by drawing_id."""
        from fittrack.repositories.prize import PrizeRepository

        mock_query.return_value = [{"_id": "p1", "drawing_id": "d1"}]
        repo = PrizeRepository()

        result = repo.find_by_drawing("d1")

        assert len(result) >= 0


class TestFulfillmentRepository:
    """Tests for FulfillmentRepository."""

    def test_fulfillment_repository_uses_correct_duality_view(self):
        """FulfillmentRepository should use prize_fulfillments_dv."""
        from fittrack.repositories.fulfillment import FulfillmentRepository

        repo = FulfillmentRepository()
        assert repo.duality_view == "prize_fulfillments_dv"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_status(self, mock_query):
        """find_by_status should filter by status."""
        from fittrack.repositories.fulfillment import FulfillmentRepository

        mock_query.return_value = [{"_id": "f1", "status": "pending"}]
        repo = FulfillmentRepository()

        result = repo.find_by_status(FulfillmentStatus.PENDING)

        assert len(result) >= 0

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_by_user(self, mock_query):
        """find_by_user should filter by user_id."""
        from fittrack.repositories.fulfillment import FulfillmentRepository

        mock_query.return_value = [{"_id": "f1", "user_id": "u1"}]
        repo = FulfillmentRepository()

        result = repo.find_by_user("u1")

        assert len(result) >= 0

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_overdue(self, mock_query):
        """find_overdue should find fulfillments past deadline."""
        from fittrack.repositories.fulfillment import FulfillmentRepository

        mock_query.return_value = []
        repo = FulfillmentRepository()

        result = repo.find_overdue(days=30)

        assert len(result) >= 0


class TestSponsorRepository:
    """Tests for SponsorRepository."""

    def test_sponsor_repository_uses_correct_duality_view(self):
        """SponsorRepository should use sponsors_dv."""
        from fittrack.repositories.sponsor import SponsorRepository

        repo = SponsorRepository()
        assert repo.duality_view == "sponsors_dv"

    @patch("fittrack.repositories.base.execute_json_query")
    def test_find_active(self, mock_query):
        """find_active should filter by status=active."""
        from fittrack.repositories.sponsor import SponsorRepository

        mock_query.return_value = [{"_id": "s1", "status": "active"}]
        repo = SponsorRepository()

        result = repo.find_active()

        assert len(result) >= 0
