"""Profile factory for test data generation."""

from datetime import date
from typing import Any

from fittrack.models.profile import calculate_age_bracket, calculate_tier_code
from tests.factories.base import fake, generate_id, random_choice, random_date, utc_now

# Valid US states (excluding ineligible ones)
ELIGIBLE_STATES = [
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
]

BIOLOGICAL_SEXES = ["male", "female"]
FITNESS_LEVELS = ["beginner", "intermediate", "advanced"]


def create_profile(
    id: str | None = None,
    user_id: str | None = None,
    display_name: str | None = None,
    date_of_birth: date | None = None,
    state_of_residence: str | None = None,
    biological_sex: str | None = None,
    fitness_level: str | None = None,
    height_inches: int | None = None,
    weight_pounds: int | None = None,
    goals: list[str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create a profile document for testing.

    Args:
        id: Profile ID.
        user_id: Associated user ID.
        display_name: Display name.
        date_of_birth: Date of birth (generates 18+ age).
        state_of_residence: US state code.
        biological_sex: male or female.
        fitness_level: beginner, intermediate, or advanced.
        height_inches: Height in inches.
        weight_pounds: Weight in pounds.
        goals: List of fitness goals.

    Returns:
        Profile document dictionary.
    """
    now = utc_now()

    if date_of_birth is None:
        # Generate DOB for someone 18-70 years old
        date_of_birth = random_date(
            start=date(1954, 1, 1),
            end=date(2006, 1, 1),
        )

    if biological_sex is None:
        biological_sex = random_choice(BIOLOGICAL_SEXES)

    if fitness_level is None:
        fitness_level = random_choice(FITNESS_LEVELS)

    age_bracket = calculate_age_bracket(date_of_birth)
    tier_code = calculate_tier_code(biological_sex, age_bracket, fitness_level)

    return {
        "_id": id or generate_id(),
        "user_id": user_id or generate_id(),
        "display_name": display_name or fake.user_name()[:50],
        "date_of_birth": date_of_birth.isoformat(),
        "state_of_residence": state_of_residence or random_choice(ELIGIBLE_STATES),
        "biological_sex": biological_sex,
        "fitness_level": fitness_level,
        "age_bracket": age_bracket,
        "tier_code": tier_code,
        "height_inches": height_inches or fake.random_int(min=60, max=78),
        "weight_pounds": weight_pounds or fake.random_int(min=100, max=250),
        "goals": goals
        or [random_choice(["lose_weight", "build_muscle", "improve_endurance", "stay_healthy"])],
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        **kwargs,
    }


def create_profiles_all_tiers() -> list[dict[str, Any]]:
    """Create profiles covering all 30 demographic tiers."""
    profiles = []

    # Age ranges that map to each bracket
    age_ranges = {
        "18-29": (date(1996, 1, 1), date(2006, 1, 1)),
        "30-39": (date(1986, 1, 1), date(1995, 12, 31)),
        "40-49": (date(1976, 1, 1), date(1985, 12, 31)),
        "50-59": (date(1966, 1, 1), date(1975, 12, 31)),
        "60+": (date(1954, 1, 1), date(1965, 12, 31)),
    }

    for sex in BIOLOGICAL_SEXES:
        for bracket, (start, end) in age_ranges.items():
            for level in FITNESS_LEVELS:
                dob = random_date(start=start, end=end)
                profiles.append(
                    create_profile(
                        biological_sex=sex,
                        date_of_birth=dob,
                        fitness_level=level,
                    )
                )

    return profiles
