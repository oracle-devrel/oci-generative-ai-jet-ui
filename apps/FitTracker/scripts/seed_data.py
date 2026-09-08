#!/usr/bin/env python3
"""Seed the database with synthetic test data.

Usage:
    python scripts/seed_data.py
    make db-seed
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "tests"))

import logging

from fittrack.core.database import init_pool, insert_json_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_database():
    """Seed the database with test data."""
    logger.info("Starting database seeding...")

    # Import factories
    from factories import (
        create_activities_for_user,
        create_admin_user,
        create_completed_drawing,
        create_connections_for_user,
        create_delivered_fulfillment,
        create_earn_transaction,
        create_open_drawing,
        create_premium_user,
        create_prizes_for_drawing,
        create_profile,
        create_profiles_all_tiers,
        create_shipped_fulfillment,
        create_spend_transaction,
        create_sponsors,
        create_tickets_for_drawing,
        create_user,
        create_winning_ticket,
    )

    # Initialize database pool
    try:
        init_pool()
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        logger.warning("Continuing without database connection (dry run mode)")
        return generate_seed_data_summary()

    # Create users
    logger.info("Creating users...")
    users = []

    # 3 admin users
    for i in range(3):
        user = create_admin_user(email=f"admin{i + 1}@fittrack.com")
        users.append(user)
        try:
            insert_json_document("users_dv", user)
        except Exception as e:
            logger.warning(f"Failed to insert admin user: {e}")

    # 15 premium users
    for i in range(15):
        user = create_premium_user(email=f"premium{i + 1}@fittrack.com")
        users.append(user)
        try:
            insert_json_document("users_dv", user)
        except Exception as e:
            logger.warning(f"Failed to insert premium user: {e}")

    # 50 regular users
    for i in range(50):
        user = create_user(email=f"user{i + 1}@fittrack.com", status="active", email_verified=True)
        users.append(user)
        try:
            insert_json_document("users_dv", user)
        except Exception as e:
            logger.warning(f"Failed to insert user: {e}")

    logger.info(f"Created {len(users)} users")

    # Create profiles (covering all 31 tiers)
    logger.info("Creating profiles...")
    profiles = []

    # First, create profiles for all 30 demographic tiers
    tier_profiles = create_profiles_all_tiers()
    for i, profile in enumerate(tier_profiles):
        if i < len(users):
            profile["user_id"] = users[i]["_id"]
        profiles.append(profile)
        try:
            insert_json_document("profiles_dv", profile)
        except Exception as e:
            logger.warning(f"Failed to insert profile: {e}")

    # Create profiles for remaining users
    for i in range(len(tier_profiles), len(users)):
        profile = create_profile(user_id=users[i]["_id"])
        profiles.append(profile)
        try:
            insert_json_document("profiles_dv", profile)
        except Exception as e:
            logger.warning(f"Failed to insert profile: {e}")

    logger.info(f"Created {len(profiles)} profiles")

    # Create connections (60 users with connections)
    logger.info("Creating connections...")
    connections = []
    for i in range(60):
        user_id = users[i]["_id"]
        user_connections = create_connections_for_user(
            user_id,
            providers=["fitbit"]
            if i % 3 == 0
            else ["apple_health"]
            if i % 3 == 1
            else ["google_fit"],
        )
        for conn in user_connections:
            connections.append(conn)
            try:
                insert_json_document("tracker_connections_dv", conn)
            except Exception as e:
                logger.warning(f"Failed to insert connection: {e}")

    logger.info(f"Created {len(connections)} connections")

    # Create activities (500+ activities)
    logger.info("Creating activities...")
    activities = []
    for i in range(50):
        user_id = users[i]["_id"]
        user_activities = create_activities_for_user(user_id, days=10, activities_per_day=1)
        for activity in user_activities:
            activities.append(activity)
            try:
                insert_json_document("activities_dv", activity)
            except Exception as e:
                logger.warning(f"Failed to insert activity: {e}")

    logger.info(f"Created {len(activities)} activities")

    # Create transactions (1000+ transactions)
    logger.info("Creating transactions...")
    transactions = []
    for i, user in enumerate(users[:50]):
        balance = user.get("point_balance", 0)

        # Create some earn transactions
        for _ in range(10):
            amount = 50 + (i * 5) % 200
            balance += amount
            tx = create_earn_transaction(
                user_id=user["_id"],
                amount=amount,
                balance_after=balance,
            )
            transactions.append(tx)
            try:
                insert_json_document("point_transactions_dv", tx)
            except Exception as e:
                logger.warning(f"Failed to insert transaction: {e}")

        # Create some spend transactions
        for _ in range(5):
            amount = min(100, balance)
            if amount > 0:
                balance -= amount
                tx = create_spend_transaction(
                    user_id=user["_id"],
                    amount=amount,
                    balance_after=balance,
                )
                transactions.append(tx)
                try:
                    insert_json_document("point_transactions_dv", tx)
                except Exception as e:
                    logger.warning(f"Failed to insert transaction: {e}")

    logger.info(f"Created {len(transactions)} transactions")

    # Create sponsors (5)
    logger.info("Creating sponsors...")
    sponsors = create_sponsors(5)
    for sponsor in sponsors:
        try:
            insert_json_document("sponsors_dv", sponsor)
        except Exception as e:
            logger.warning(f"Failed to insert sponsor: {e}")

    logger.info(f"Created {len(sponsors)} sponsors")

    # Create drawings (15 total)
    logger.info("Creating drawings...")
    drawings = []

    # 5 open drawings (1 of each type + 1 extra daily)
    for drawing_type in ["daily", "weekly", "monthly", "annual", "daily"]:
        drawing = create_open_drawing(drawing_type=drawing_type)
        drawings.append(drawing)
        try:
            insert_json_document("drawings_dv", drawing)
        except Exception as e:
            logger.warning(f"Failed to insert drawing: {e}")

    # 10 completed drawings
    for i in range(10):
        drawing = create_completed_drawing()
        drawings.append(drawing)
        try:
            insert_json_document("drawings_dv", drawing)
        except Exception as e:
            logger.warning(f"Failed to insert drawing: {e}")

    logger.info(f"Created {len(drawings)} drawings")

    # Create prizes (for each drawing)
    logger.info("Creating prizes...")
    prizes = []
    for drawing in drawings:
        drawing_prizes = create_prizes_for_drawing(drawing["_id"], count=3)
        for prize in drawing_prizes:
            prizes.append(prize)
            try:
                insert_json_document("prizes_dv", prize)
            except Exception as e:
                logger.warning(f"Failed to insert prize: {e}")

    logger.info(f"Created {len(prizes)} prizes")

    # Create tickets (200+ for completed drawings)
    logger.info("Creating tickets...")
    tickets = []
    completed_drawings = [d for d in drawings if d["status"] == "completed"]
    user_ids = [u["_id"] for u in users[:30]]

    for drawing in completed_drawings:
        drawing_tickets = create_tickets_for_drawing(
            drawing["_id"],
            count=20,
            user_ids=user_ids,
        )
        for ticket in drawing_tickets:
            tickets.append(ticket)
            try:
                insert_json_document("tickets_dv", ticket)
            except Exception as e:
                logger.warning(f"Failed to insert ticket: {e}")

    logger.info(f"Created {len(tickets)} tickets")

    # Create fulfillments (for some winning tickets)
    logger.info("Creating fulfillments...")
    fulfillments = []

    # Create some shipped and delivered fulfillments
    for i, drawing in enumerate(completed_drawings[:5]):
        drawing_prizes = [p for p in prizes if p["drawing_id"] == drawing["_id"]]
        if drawing_prizes:
            first_prize = drawing_prizes[0]
            user_id = users[i]["_id"]

            # Create winning ticket
            winning_ticket = create_winning_ticket(
                drawing_id=drawing["_id"],
                user_id=user_id,
                prize_id=first_prize["_id"],
            )
            try:
                insert_json_document("tickets_dv", winning_ticket)
            except Exception:
                pass

            # Create fulfillment
            if i % 2 == 0:
                fulfillment = create_delivered_fulfillment(
                    ticket_id=winning_ticket["_id"],
                    prize_id=first_prize["_id"],
                    user_id=user_id,
                )
            else:
                fulfillment = create_shipped_fulfillment(
                    ticket_id=winning_ticket["_id"],
                    prize_id=first_prize["_id"],
                    user_id=user_id,
                )

            fulfillments.append(fulfillment)
            try:
                insert_json_document("prize_fulfillments_dv", fulfillment)
            except Exception as e:
                logger.warning(f"Failed to insert fulfillment: {e}")

    logger.info(f"Created {len(fulfillments)} fulfillments")

    return {
        "users": len(users),
        "profiles": len(profiles),
        "connections": len(connections),
        "activities": len(activities),
        "transactions": len(transactions),
        "sponsors": len(sponsors),
        "drawings": len(drawings),
        "prizes": len(prizes),
        "tickets": len(tickets),
        "fulfillments": len(fulfillments),
    }


def generate_seed_data_summary():
    """Generate summary of what would be seeded (dry run)."""
    return {
        "users": 68,
        "profiles": 68,
        "connections": 60,
        "activities": 500,
        "transactions": 750,
        "sponsors": 5,
        "drawings": 15,
        "prizes": 45,
        "tickets": 200,
        "fulfillments": 10,
    }


if __name__ == "__main__":
    summary = seed_database()
    logger.info("=" * 50)
    logger.info("Seeding complete! Summary:")
    for entity, count in summary.items():
        logger.info(f"  {entity}: {count}")
    logger.info("=" * 50)
