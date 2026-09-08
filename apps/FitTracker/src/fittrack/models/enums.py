"""Enums for FitTrack domain models."""

from enum import Enum


class UserStatus(str, Enum):
    """User account status."""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"


class UserRole(str, Enum):
    """User role for authorization."""

    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"


class Provider(str, Enum):
    """Fitness tracker provider."""

    APPLE_HEALTH = "apple_health"
    GOOGLE_FIT = "google_fit"
    FITBIT = "fitbit"


class SyncStatus(str, Enum):
    """Tracker sync status."""

    PENDING = "pending"
    SYNCING = "syncing"
    SUCCESS = "success"
    ERROR = "error"


class ActivityType(str, Enum):
    """Type of fitness activity."""

    STEPS = "steps"
    WORKOUT = "workout"
    ACTIVE_MINUTES = "active_minutes"


class Intensity(str, Enum):
    """Activity intensity level."""

    LIGHT = "light"
    MODERATE = "moderate"
    VIGOROUS = "vigorous"


class TransactionType(str, Enum):
    """Point transaction type."""

    EARN = "earn"
    SPEND = "spend"
    ADJUST = "adjust"
    EXPIRE = "expire"


class DrawingType(str, Enum):
    """Sweepstakes drawing type."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ANNUAL = "annual"


class DrawingStatus(str, Enum):
    """Drawing lifecycle status."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    OPEN = "open"
    CLOSED = "closed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FulfillmentType(str, Enum):
    """Prize fulfillment type."""

    DIGITAL = "digital"
    PHYSICAL = "physical"


class FulfillmentStatus(str, Enum):
    """Prize fulfillment workflow status."""

    PENDING = "pending"
    WINNER_NOTIFIED = "winner_notified"
    ADDRESS_CONFIRMED = "address_confirmed"
    ADDRESS_INVALID = "address_invalid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    FORFEITED = "forfeited"


class BiologicalSex(str, Enum):
    """Biological sex for competition tiering."""

    MALE = "male"
    FEMALE = "female"


class AgeBracket(str, Enum):
    """Age bracket for competition tiering."""

    AGE_18_29 = "18-29"
    AGE_30_39 = "30-39"
    AGE_40_49 = "40-49"
    AGE_50_59 = "50-59"
    AGE_60_PLUS = "60+"


class FitnessLevel(str, Enum):
    """Fitness level for competition tiering."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class SponsorStatus(str, Enum):
    """Sponsor status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
