"""Activity factory for test data generation."""

from datetime import datetime, timedelta
from typing import Any

from tests.factories.base import fake, generate_id, random_choice, utc_now

ACTIVITY_TYPES = ["steps", "workout", "active_minutes"]
INTENSITIES = ["light", "moderate", "vigorous"]


def create_activity(
    id: str | None = None,
    user_id: str | None = None,
    connection_id: str | None = None,
    external_id: str | None = None,
    activity_type: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    duration_minutes: int | None = None,
    intensity: str | None = None,
    metrics: dict | None = None,
    points_earned: int = 0,
    processed: bool = False,
    **kwargs,
) -> dict[str, Any]:
    """Create an activity document for testing."""
    now = utc_now()

    if activity_type is None:
        activity_type = random_choice(ACTIVITY_TYPES)

    if start_time is None:
        start_time = now - timedelta(hours=fake.random_int(1, 24))

    if duration_minutes is None:
        duration_minutes = fake.random_int(10, 60)

    if end_time is None:
        end_time = start_time + timedelta(minutes=duration_minutes)

    if metrics is None:
        if activity_type == "steps":
            metrics = {"step_count": fake.random_int(1000, 15000)}
        elif activity_type == "workout":
            metrics = {
                "calories_burned": fake.random_int(100, 500),
                "avg_heart_rate": fake.random_int(100, 160),
            }
        else:
            metrics = {"active_minutes": duration_minutes}

    return {
        "_id": id or generate_id(),
        "user_id": user_id or generate_id(),
        "connection_id": connection_id,
        "external_id": external_id or f"ext_{generate_id()[:8]}",
        "activity_type": activity_type,
        "start_time": start_time.isoformat() + "Z",
        "end_time": end_time.isoformat() + "Z" if end_time else None,
        "duration_minutes": duration_minutes,
        "intensity": intensity or random_choice(INTENSITIES),
        "metrics": metrics,
        "points_earned": points_earned,
        "processed": processed,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        **kwargs,
    }


def create_activities_for_user(
    user_id: str,
    days: int = 30,
    activities_per_day: int = 3,
) -> list[dict[str, Any]]:
    """Create a set of activities over multiple days for a user."""
    activities = []
    now = utc_now()

    for day_offset in range(days):
        day = now - timedelta(days=day_offset)
        # Create activities throughout the day
        for _ in range(activities_per_day):
            hour = fake.random_int(6, 22)
            start = day.replace(hour=hour, minute=fake.random_int(0, 59))
            activities.append(create_activity(user_id=user_id, start_time=start))

    return activities
