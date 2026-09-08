"""Repository layer for data access via JSON Duality Views."""

from fittrack.repositories.activity import ActivityRepository
from fittrack.repositories.base import BaseRepository
from fittrack.repositories.connection import ConnectionRepository
from fittrack.repositories.drawing import DrawingRepository
from fittrack.repositories.fulfillment import FulfillmentRepository
from fittrack.repositories.prize import PrizeRepository
from fittrack.repositories.profile import ProfileRepository
from fittrack.repositories.sponsor import SponsorRepository
from fittrack.repositories.ticket import TicketRepository
from fittrack.repositories.transaction import TransactionRepository
from fittrack.repositories.user import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "ProfileRepository",
    "ConnectionRepository",
    "ActivityRepository",
    "TransactionRepository",
    "DrawingRepository",
    "TicketRepository",
    "PrizeRepository",
    "FulfillmentRepository",
    "SponsorRepository",
]
