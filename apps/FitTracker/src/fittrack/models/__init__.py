"""FitTrack domain models."""

from fittrack.models.activity import Activity
from fittrack.models.connection import TrackerConnection
from fittrack.models.drawing import Drawing
from fittrack.models.enums import (
    ActivityType,
    AgeBracket,
    BiologicalSex,
    DrawingStatus,
    DrawingType,
    FitnessLevel,
    FulfillmentStatus,
    FulfillmentType,
    Intensity,
    Provider,
    SponsorStatus,
    SyncStatus,
    TransactionType,
    UserRole,
    UserStatus,
)
from fittrack.models.fulfillment import PrizeFulfillment
from fittrack.models.prize import Prize
from fittrack.models.profile import Profile
from fittrack.models.sponsor import Sponsor
from fittrack.models.ticket import Ticket
from fittrack.models.transaction import PointTransaction
from fittrack.models.user import User

__all__ = [
    # Models
    "User",
    "Profile",
    "TrackerConnection",
    "Activity",
    "PointTransaction",
    "Drawing",
    "Ticket",
    "Prize",
    "PrizeFulfillment",
    "Sponsor",
    # Enums
    "UserStatus",
    "UserRole",
    "Provider",
    "SyncStatus",
    "ActivityType",
    "Intensity",
    "TransactionType",
    "DrawingType",
    "DrawingStatus",
    "FulfillmentType",
    "FulfillmentStatus",
    "BiologicalSex",
    "AgeBracket",
    "FitnessLevel",
    "SponsorStatus",
]
