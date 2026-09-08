"""Test data factories for FitTrack."""

from tests.factories.activity import (
    create_activities_for_user,
    create_activity,
)
from tests.factories.base import (
    fake,
    generate_id,
    random_choice,
    random_date,
    random_datetime,
    utc_now,
)
from tests.factories.connection import (
    create_connection,
    create_connections_for_user,
)
from tests.factories.drawing import (
    create_completed_drawing,
    create_drawing,
    create_open_drawing,
)
from tests.factories.fulfillment import (
    create_delivered_fulfillment,
    create_fulfillment,
    create_shipped_fulfillment,
    create_shipping_address,
)
from tests.factories.prize import (
    create_prize,
    create_prizes_for_drawing,
)
from tests.factories.profile import (
    create_profile,
    create_profiles_all_tiers,
)
from tests.factories.sponsor import (
    create_active_sponsor,
    create_sponsor,
    create_sponsors,
)
from tests.factories.ticket import (
    create_ticket,
    create_tickets_for_drawing,
    create_winning_ticket,
)
from tests.factories.transaction import (
    create_earn_transaction,
    create_spend_transaction,
    create_transaction,
)
from tests.factories.user import (
    create_admin_user,
    create_premium_user,
    create_user,
    create_users,
)

__all__ = [
    # Base
    "fake",
    "generate_id",
    "random_choice",
    "random_date",
    "random_datetime",
    "utc_now",
    # User
    "create_user",
    "create_users",
    "create_admin_user",
    "create_premium_user",
    # Profile
    "create_profile",
    "create_profiles_all_tiers",
    # Connection
    "create_connection",
    "create_connections_for_user",
    # Activity
    "create_activity",
    "create_activities_for_user",
    # Transaction
    "create_transaction",
    "create_earn_transaction",
    "create_spend_transaction",
    # Drawing
    "create_drawing",
    "create_open_drawing",
    "create_completed_drawing",
    # Ticket
    "create_ticket",
    "create_tickets_for_drawing",
    "create_winning_ticket",
    # Prize
    "create_prize",
    "create_prizes_for_drawing",
    # Fulfillment
    "create_fulfillment",
    "create_shipping_address",
    "create_shipped_fulfillment",
    "create_delivered_fulfillment",
    # Sponsor
    "create_sponsor",
    "create_active_sponsor",
    "create_sponsors",
]
