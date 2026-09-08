"""Base factory for test data generation."""

import random
import string
from datetime import date, datetime, timedelta
from typing import TypeVar

from faker import Faker

fake = Faker()
Faker.seed(42)  # For reproducible test data
random.seed(42)

T = TypeVar("T")


def generate_id() -> str:
    """Generate a UUID-like ID."""
    import uuid

    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()


def random_datetime(
    start: datetime | None = None,
    end: datetime | None = None,
) -> datetime:
    """Generate a random datetime within range."""
    if start is None:
        start = datetime(2024, 1, 1)
    if end is None:
        end = utc_now()
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def random_date(
    start: date | None = None,
    end: date | None = None,
) -> date:
    """Generate a random date within range."""
    if start is None:
        start = date(1960, 1, 1)
    if end is None:
        end = date(2006, 1, 1)  # At least 18 years old
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


def random_choice(choices: list[T]) -> T:
    """Random choice from a list."""
    return random.choice(choices)


def random_string(length: int = 10) -> str:
    """Generate random alphanumeric string."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
