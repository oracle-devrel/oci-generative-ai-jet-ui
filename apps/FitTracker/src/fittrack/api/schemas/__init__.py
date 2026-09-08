"""API request/response schemas."""

from fittrack.api.schemas.activity import (
    ActivityCreate,
    ActivityDateRangeQuery,
    ActivityResponse,
    ActivitySummary,
)
from fittrack.api.schemas.common import (
    DeleteResponse,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationRequest,
    SuccessResponse,
)
from fittrack.api.schemas.connection import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionSummary,
)
from fittrack.api.schemas.drawing import (
    DrawingCreate,
    DrawingResponse,
    DrawingSummary,
    DrawingUpdate,
)
from fittrack.api.schemas.fulfillment import (
    FulfillmentResponse,
    FulfillmentSummary,
    FulfillmentUpdate,
    ShippingAddress,
)
from fittrack.api.schemas.prize import (
    PrizeCreate,
    PrizeResponse,
    PrizeSummary,
    PrizeUpdate,
)
from fittrack.api.schemas.profile import (
    ProfileCreate,
    ProfileResponse,
    ProfileSummary,
    ProfileUpdate,
)
from fittrack.api.schemas.sponsor import (
    SponsorCreate,
    SponsorResponse,
    SponsorSummary,
    SponsorUpdate,
)
from fittrack.api.schemas.ticket import (
    TicketCreate,
    TicketPurchaseResponse,
    TicketResponse,
    TicketSummary,
)
from fittrack.api.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionSummary,
)
from fittrack.api.schemas.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserSummary,
    UserUpdate,
)

__all__ = [
    # Common
    "PaginationRequest",
    "PaginationMeta",
    "PaginatedResponse",
    "ErrorResponse",
    "SuccessResponse",
    "DeleteResponse",
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserSummary",
    "UserListResponse",
    # Profile
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileResponse",
    "ProfileSummary",
    # Connection
    "ConnectionCreate",
    "ConnectionResponse",
    "ConnectionSummary",
    # Activity
    "ActivityCreate",
    "ActivityResponse",
    "ActivitySummary",
    "ActivityDateRangeQuery",
    # Transaction
    "TransactionCreate",
    "TransactionResponse",
    "TransactionSummary",
    # Drawing
    "DrawingCreate",
    "DrawingUpdate",
    "DrawingResponse",
    "DrawingSummary",
    # Ticket
    "TicketCreate",
    "TicketResponse",
    "TicketSummary",
    "TicketPurchaseResponse",
    # Prize
    "PrizeCreate",
    "PrizeUpdate",
    "PrizeResponse",
    "PrizeSummary",
    # Fulfillment
    "FulfillmentUpdate",
    "FulfillmentResponse",
    "FulfillmentSummary",
    "ShippingAddress",
    # Sponsor
    "SponsorCreate",
    "SponsorUpdate",
    "SponsorResponse",
    "SponsorSummary",
]
