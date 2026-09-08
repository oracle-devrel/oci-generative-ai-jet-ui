"""Unit tests for domain models.

TDD: These tests are written FIRST before the model implementations.
All tests should FAIL initially until models are implemented.
"""

import uuid
from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError


class TestEnums:
    """Tests for enum definitions."""

    def test_user_status_values(self):
        """User status should have pending, active, suspended, banned."""
        from fittrack.models.enums import UserStatus

        assert UserStatus.PENDING == "pending"
        assert UserStatus.ACTIVE == "active"
        assert UserStatus.SUSPENDED == "suspended"
        assert UserStatus.BANNED == "banned"

    def test_user_role_values(self):
        """User role should have user, premium, admin."""
        from fittrack.models.enums import UserRole

        assert UserRole.USER == "user"
        assert UserRole.PREMIUM == "premium"
        assert UserRole.ADMIN == "admin"

    def test_provider_values(self):
        """Provider should have apple_health, google_fit, fitbit."""
        from fittrack.models.enums import Provider

        assert Provider.APPLE_HEALTH == "apple_health"
        assert Provider.GOOGLE_FIT == "google_fit"
        assert Provider.FITBIT == "fitbit"

    def test_sync_status_values(self):
        """Sync status should have pending, syncing, success, error."""
        from fittrack.models.enums import SyncStatus

        assert SyncStatus.PENDING == "pending"
        assert SyncStatus.SYNCING == "syncing"
        assert SyncStatus.SUCCESS == "success"
        assert SyncStatus.ERROR == "error"

    def test_activity_type_values(self):
        """Activity type should have steps, workout, active_minutes."""
        from fittrack.models.enums import ActivityType

        assert ActivityType.STEPS == "steps"
        assert ActivityType.WORKOUT == "workout"
        assert ActivityType.ACTIVE_MINUTES == "active_minutes"

    def test_intensity_values(self):
        """Intensity should have light, moderate, vigorous."""
        from fittrack.models.enums import Intensity

        assert Intensity.LIGHT == "light"
        assert Intensity.MODERATE == "moderate"
        assert Intensity.VIGOROUS == "vigorous"

    def test_transaction_type_values(self):
        """Transaction type should have earn, spend, adjust, expire."""
        from fittrack.models.enums import TransactionType

        assert TransactionType.EARN == "earn"
        assert TransactionType.SPEND == "spend"
        assert TransactionType.ADJUST == "adjust"
        assert TransactionType.EXPIRE == "expire"

    def test_drawing_type_values(self):
        """Drawing type should have daily, weekly, monthly, annual."""
        from fittrack.models.enums import DrawingType

        assert DrawingType.DAILY == "daily"
        assert DrawingType.WEEKLY == "weekly"
        assert DrawingType.MONTHLY == "monthly"
        assert DrawingType.ANNUAL == "annual"

    def test_drawing_status_values(self):
        """Drawing status should have all lifecycle states."""
        from fittrack.models.enums import DrawingStatus

        assert DrawingStatus.DRAFT == "draft"
        assert DrawingStatus.SCHEDULED == "scheduled"
        assert DrawingStatus.OPEN == "open"
        assert DrawingStatus.CLOSED == "closed"
        assert DrawingStatus.COMPLETED == "completed"
        assert DrawingStatus.CANCELLED == "cancelled"

    def test_fulfillment_type_values(self):
        """Fulfillment type should have digital, physical."""
        from fittrack.models.enums import FulfillmentType

        assert FulfillmentType.DIGITAL == "digital"
        assert FulfillmentType.PHYSICAL == "physical"

    def test_fulfillment_status_values(self):
        """Fulfillment status should have all workflow states."""
        from fittrack.models.enums import FulfillmentStatus

        assert FulfillmentStatus.PENDING == "pending"
        assert FulfillmentStatus.WINNER_NOTIFIED == "winner_notified"
        assert FulfillmentStatus.ADDRESS_CONFIRMED == "address_confirmed"
        assert FulfillmentStatus.ADDRESS_INVALID == "address_invalid"
        assert FulfillmentStatus.SHIPPED == "shipped"
        assert FulfillmentStatus.DELIVERED == "delivered"
        assert FulfillmentStatus.FORFEITED == "forfeited"

    def test_biological_sex_values(self):
        """Biological sex should have male, female."""
        from fittrack.models.enums import BiologicalSex

        assert BiologicalSex.MALE == "male"
        assert BiologicalSex.FEMALE == "female"

    def test_age_bracket_values(self):
        """Age bracket should have all defined ranges."""
        from fittrack.models.enums import AgeBracket

        assert AgeBracket.AGE_18_29 == "18-29"
        assert AgeBracket.AGE_30_39 == "30-39"
        assert AgeBracket.AGE_40_49 == "40-49"
        assert AgeBracket.AGE_50_59 == "50-59"
        assert AgeBracket.AGE_60_PLUS == "60+"

    def test_fitness_level_values(self):
        """Fitness level should have beginner, intermediate, advanced."""
        from fittrack.models.enums import FitnessLevel

        assert FitnessLevel.BEGINNER == "beginner"
        assert FitnessLevel.INTERMEDIATE == "intermediate"
        assert FitnessLevel.ADVANCED == "advanced"


class TestUserModel:
    """Tests for User model."""

    def test_create_user_with_required_fields(self):
        """User can be created with required fields."""
        from fittrack.models.user import User

        user = User(
            email="test@example.com",
            password_hash="hashed_password_here",
        )
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password_here"
        assert user.id is not None  # Auto-generated
        assert user.status.value == "pending"
        assert user.role.value == "user"
        assert user.point_balance == 0

    def test_user_email_validation(self):
        """User email must be valid format."""
        from fittrack.models.user import User

        with pytest.raises(ValidationError) as exc_info:
            User(email="invalid-email", password_hash="hash")
        assert "email" in str(exc_info.value).lower()

    def test_user_point_balance_non_negative(self):
        """User point balance cannot be negative."""
        from fittrack.models.user import User

        with pytest.raises(ValidationError) as exc_info:
            User(
                email="test@example.com",
                password_hash="hash",
                point_balance=-100,
            )
        assert "point_balance" in str(exc_info.value).lower()

    def test_user_default_timestamps(self):
        """User should have auto-generated timestamps."""
        from fittrack.models.user import User

        user = User(email="test@example.com", password_hash="hash")
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_id_is_uuid(self):
        """User ID should be a valid UUID string."""
        from fittrack.models.user import User

        user = User(email="test@example.com", password_hash="hash")
        # Should not raise
        uuid.UUID(user.id)


class TestProfileModel:
    """Tests for Profile model."""

    def test_create_profile_with_required_fields(self):
        """Profile can be created with required fields."""
        from fittrack.models.profile import Profile

        profile = Profile(
            user_id=str(uuid.uuid4()),
            display_name="FitRunner42",
            date_of_birth=date(1990, 5, 15),
            state_of_residence="TX",
            biological_sex="male",
            fitness_level="intermediate",
        )
        assert profile.display_name == "FitRunner42"
        assert profile.state_of_residence == "TX"

    def test_profile_age_bracket_calculated(self):
        """Profile age bracket should be calculated from DOB."""
        from fittrack.models.profile import Profile

        # 30 years old -> 30-39 bracket (use date replace for accurate age)
        today = date.today()
        dob = date(today.year - 30, today.month, today.day)
        profile = Profile(
            user_id=str(uuid.uuid4()),
            display_name="Test",
            date_of_birth=dob,
            state_of_residence="TX",
            biological_sex="male",
            fitness_level="beginner",
        )
        assert profile.age_bracket == "30-39"

    def test_profile_tier_code_generated(self):
        """Profile tier code should be generated from attributes."""
        from fittrack.models.profile import Profile

        dob = date.today() - timedelta(days=35 * 365)  # 35 years old
        profile = Profile(
            user_id=str(uuid.uuid4()),
            display_name="Test",
            date_of_birth=dob,
            state_of_residence="TX",
            biological_sex="male",
            fitness_level="intermediate",
        )
        assert profile.tier_code == "M-30-39-INT"

    def test_profile_tier_code_female(self):
        """Female profile should have F prefix in tier code."""
        from fittrack.models.profile import Profile

        dob = date.today() - timedelta(days=25 * 365)  # 25 years old
        profile = Profile(
            user_id=str(uuid.uuid4()),
            display_name="Test",
            date_of_birth=dob,
            state_of_residence="CA",
            biological_sex="female",
            fitness_level="advanced",
        )
        assert profile.tier_code == "F-18-29-ADV"

    def test_profile_display_name_length(self):
        """Display name should be between 3 and 50 characters."""
        from fittrack.models.profile import Profile

        with pytest.raises(ValidationError):
            Profile(
                user_id=str(uuid.uuid4()),
                display_name="AB",  # Too short
                date_of_birth=date(1990, 1, 1),
                state_of_residence="TX",
                biological_sex="male",
                fitness_level="beginner",
            )

    def test_profile_state_validation(self):
        """State must be valid 2-letter US state code."""
        from fittrack.models.profile import Profile

        with pytest.raises(ValidationError):
            Profile(
                user_id=str(uuid.uuid4()),
                display_name="Test",
                date_of_birth=date(1990, 1, 1),
                state_of_residence="XX",  # Invalid
                biological_sex="male",
                fitness_level="beginner",
            )

    def test_profile_ineligible_state_flagged(self):
        """Ineligible states (NY, FL, RI) should be rejected."""
        from fittrack.models.profile import Profile

        for state in ["NY", "FL", "RI"]:
            with pytest.raises(ValidationError) as exc_info:
                Profile(
                    user_id=str(uuid.uuid4()),
                    display_name="Test",
                    date_of_birth=date(1990, 1, 1),
                    state_of_residence=state,
                    biological_sex="male",
                    fitness_level="beginner",
                )
            assert "ineligible" in str(exc_info.value).lower()

    def test_profile_age_must_be_18_plus(self):
        """User must be 18+ years old."""
        from fittrack.models.profile import Profile

        # 17 years old
        dob = date.today() - timedelta(days=17 * 365)
        with pytest.raises(ValidationError) as exc_info:
            Profile(
                user_id=str(uuid.uuid4()),
                display_name="Test",
                date_of_birth=dob,
                state_of_residence="TX",
                biological_sex="male",
                fitness_level="beginner",
            )
        assert "18" in str(exc_info.value)


class TestTrackerConnectionModel:
    """Tests for TrackerConnection model."""

    def test_create_connection(self):
        """Connection can be created with required fields."""
        from fittrack.models.connection import TrackerConnection

        conn = TrackerConnection(
            user_id=str(uuid.uuid4()),
            provider="fitbit",
        )
        assert conn.provider == "fitbit"
        assert conn.sync_status == "pending"
        assert conn.is_primary is False

    def test_connection_provider_validation(self):
        """Provider must be one of the allowed values."""
        from fittrack.models.connection import TrackerConnection

        with pytest.raises(ValidationError):
            TrackerConnection(
                user_id=str(uuid.uuid4()),
                provider="invalid_provider",
            )


class TestActivityModel:
    """Tests for Activity model."""

    def test_create_activity(self):
        """Activity can be created with required fields."""
        from fittrack.models.activity import Activity

        activity = Activity(
            user_id=str(uuid.uuid4()),
            activity_type="steps",
            start_time=datetime.utcnow(),
        )
        assert activity.activity_type == "steps"
        assert activity.points_earned == 0
        assert activity.processed is False

    def test_activity_with_metrics(self):
        """Activity can store metrics as JSON."""
        from fittrack.models.activity import Activity

        metrics = {"steps": 5000, "calories": 250}
        activity = Activity(
            user_id=str(uuid.uuid4()),
            activity_type="steps",
            start_time=datetime.utcnow(),
            metrics=metrics,
        )
        assert activity.metrics["steps"] == 5000

    def test_activity_intensity_validation(self):
        """Intensity must be light, moderate, or vigorous."""
        from fittrack.models.activity import Activity

        with pytest.raises(ValidationError):
            Activity(
                user_id=str(uuid.uuid4()),
                activity_type="workout",
                start_time=datetime.utcnow(),
                intensity="extreme",  # Invalid
            )


class TestPointTransactionModel:
    """Tests for PointTransaction model."""

    def test_create_earn_transaction(self):
        """Earn transaction can be created."""
        from fittrack.models.transaction import PointTransaction

        tx = PointTransaction(
            user_id=str(uuid.uuid4()),
            transaction_type="earn",
            amount=100,
            balance_after=1100,
            description="Daily step goal achieved",
        )
        assert tx.amount == 100
        assert tx.transaction_type == "earn"

    def test_spend_transaction_amount_validation(self):
        """Spend amount should be positive (stored as positive, deducted from balance)."""
        from fittrack.models.transaction import PointTransaction

        tx = PointTransaction(
            user_id=str(uuid.uuid4()),
            transaction_type="spend",
            amount=500,  # Positive amount that will be deducted
            balance_after=500,
            description="Ticket purchase",
        )
        assert tx.amount == 500

    def test_transaction_amount_must_be_positive(self):
        """Transaction amount must be positive."""
        from fittrack.models.transaction import PointTransaction

        with pytest.raises(ValidationError):
            PointTransaction(
                user_id=str(uuid.uuid4()),
                transaction_type="earn",
                amount=-100,  # Negative not allowed
                balance_after=1000,
            )


class TestDrawingModel:
    """Tests for Drawing model."""

    def test_create_drawing(self):
        """Drawing can be created with required fields."""
        from fittrack.models.drawing import Drawing

        drawing = Drawing(
            drawing_type="daily",
            name="Daily Drawing - Jan 15",
            ticket_cost_points=100,
            drawing_time=datetime.utcnow() + timedelta(hours=5),
            ticket_sales_close=datetime.utcnow() + timedelta(hours=4, minutes=55),
        )
        assert drawing.drawing_type == "daily"
        assert drawing.status == "draft"
        assert drawing.total_tickets == 0

    def test_drawing_sales_close_before_drawing_time(self):
        """Ticket sales must close before drawing time."""
        from fittrack.models.drawing import Drawing

        drawing_time = datetime.utcnow() + timedelta(hours=5)
        sales_close = drawing_time - timedelta(minutes=5)

        drawing = Drawing(
            drawing_type="daily",
            name="Test Drawing",
            ticket_cost_points=100,
            drawing_time=drawing_time,
            ticket_sales_close=sales_close,
        )
        assert drawing.ticket_sales_close < drawing.drawing_time

    def test_drawing_ticket_cost_positive(self):
        """Ticket cost must be positive."""
        from fittrack.models.drawing import Drawing

        with pytest.raises(ValidationError):
            Drawing(
                drawing_type="daily",
                name="Test",
                ticket_cost_points=0,  # Must be positive
                drawing_time=datetime.utcnow() + timedelta(hours=5),
                ticket_sales_close=datetime.utcnow() + timedelta(hours=4),
            )


class TestTicketModel:
    """Tests for Ticket model."""

    def test_create_ticket(self):
        """Ticket can be created with required fields."""
        from fittrack.models.ticket import Ticket

        ticket = Ticket(
            drawing_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
        )
        assert ticket.is_winner is False
        assert ticket.ticket_number is None  # Assigned at close


class TestPrizeModel:
    """Tests for Prize model."""

    def test_create_prize(self):
        """Prize can be created with required fields."""
        from fittrack.models.prize import Prize

        prize = Prize(
            drawing_id=str(uuid.uuid4()),
            rank=1,
            name="$50 Amazon Gift Card",
            fulfillment_type="digital",
        )
        assert prize.rank == 1
        assert prize.quantity == 1

    def test_prize_value_non_negative(self):
        """Prize value must be non-negative."""
        from fittrack.models.prize import Prize

        with pytest.raises(ValidationError):
            Prize(
                drawing_id=str(uuid.uuid4()),
                rank=1,
                name="Test",
                fulfillment_type="digital",
                value_usd=-10,
            )


class TestFulfillmentModel:
    """Tests for PrizeFulfillment model."""

    def test_create_fulfillment(self):
        """Fulfillment can be created with required fields."""
        from fittrack.models.fulfillment import PrizeFulfillment

        fulfillment = PrizeFulfillment(
            ticket_id=str(uuid.uuid4()),
            prize_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
        )
        assert fulfillment.status == "pending"

    def test_fulfillment_shipping_address_json(self):
        """Shipping address can be stored as JSON."""
        from fittrack.models.fulfillment import PrizeFulfillment

        address = {
            "street": "123 Main St",
            "city": "Austin",
            "state": "TX",
            "zip": "78701",
        }
        fulfillment = PrizeFulfillment(
            ticket_id=str(uuid.uuid4()),
            prize_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            shipping_address=address,
        )
        assert fulfillment.shipping_address["city"] == "Austin"


class TestSponsorModel:
    """Tests for Sponsor model."""

    def test_create_sponsor(self):
        """Sponsor can be created with required fields."""
        from fittrack.models.sponsor import Sponsor

        sponsor = Sponsor(name="Amazon")
        assert sponsor.name == "Amazon"
        assert sponsor.status == "active"

    def test_sponsor_contact_email_validation(self):
        """Sponsor contact email must be valid if provided."""
        from fittrack.models.sponsor import Sponsor

        with pytest.raises(ValidationError):
            Sponsor(
                name="Test Sponsor",
                contact_email="invalid-email",
            )


class TestTierCodeGeneration:
    """Tests for tier code generation logic."""

    def test_all_tier_combinations(self):
        """All 30 demographic tier combinations should be valid."""
        from fittrack.models.profile import Profile

        sexes = ["male", "female"]
        fitness_levels = ["beginner", "intermediate", "advanced"]
        age_ranges = [
            (22, "18-29"),
            (35, "30-39"),
            (45, "40-49"),
            (55, "50-59"),
            (65, "60+"),
        ]

        for sex in sexes:
            for level in fitness_levels:
                for age, bracket in age_ranges:
                    dob = date.today() - timedelta(days=age * 365)
                    profile = Profile(
                        user_id=str(uuid.uuid4()),
                        display_name="Test",
                        date_of_birth=dob,
                        state_of_residence="TX",
                        biological_sex=sex,
                        fitness_level=level,
                    )
                    sex_prefix = "M" if sex == "male" else "F"
                    level_code = level[:3].upper()
                    expected = f"{sex_prefix}-{bracket}-{level_code}"
                    assert (
                        profile.tier_code == expected
                    ), f"Expected {expected}, got {profile.tier_code}"
