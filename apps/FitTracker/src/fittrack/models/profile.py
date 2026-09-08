"""Profile model for user demographics and tier assignment."""

from datetime import date

from pydantic import Field, field_validator, model_validator

from fittrack.models.base import IdentifiedModel
from fittrack.models.enums import AgeBracket, BiologicalSex, FitnessLevel

# Valid US state codes
VALID_STATES = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
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
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
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
}

# States ineligible for sweepstakes
INELIGIBLE_STATES = {"NY", "FL", "RI"}


def calculate_age(dob: date) -> int:
    """Calculate age in years from date of birth."""
    today = date.today()
    age = today.year - dob.year
    # Adjust if birthday hasn't occurred yet this year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


def calculate_age_bracket(dob: date) -> str:
    """Calculate age bracket from date of birth."""
    age = calculate_age(dob)
    if 18 <= age <= 29:
        return AgeBracket.AGE_18_29.value
    elif 30 <= age <= 39:
        return AgeBracket.AGE_30_39.value
    elif 40 <= age <= 49:
        return AgeBracket.AGE_40_49.value
    elif 50 <= age <= 59:
        return AgeBracket.AGE_50_59.value
    else:  # 60+
        return AgeBracket.AGE_60_PLUS.value


def calculate_tier_code(sex: str, age_bracket: str, fitness_level: str) -> str:
    """Generate tier code from profile attributes.

    Format: {SEX_PREFIX}-{AGE_BRACKET}-{FITNESS_ABBREV}
    Example: M-30-39-INT
    """
    sex_prefix = "M" if sex == BiologicalSex.MALE.value else "F"
    fitness_abbrev = fitness_level[:3].upper()
    return f"{sex_prefix}-{age_bracket}-{fitness_abbrev}"


class Profile(IdentifiedModel):
    """User profile with demographics and tier assignment."""

    user_id: str
    display_name: str = Field(min_length=3, max_length=50)
    date_of_birth: date
    state_of_residence: str = Field(min_length=2, max_length=2)
    biological_sex: BiologicalSex
    fitness_level: FitnessLevel
    age_bracket: str | None = None
    tier_code: str | None = None
    height_inches: int | None = Field(default=None, ge=36, le=96)
    weight_pounds: int | None = Field(default=None, ge=50, le=1000)
    goals: list[str] | None = None

    @field_validator("state_of_residence")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate state is a valid US state code."""
        v = v.upper()
        if v not in VALID_STATES:
            raise ValueError(f"Invalid state code: {v}")
        if v in INELIGIBLE_STATES:
            raise ValueError(f"State {v} is ineligible for sweepstakes participation")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: date) -> date:
        """Validate user is at least 18 years old."""
        age = calculate_age(v)
        if age < 18:
            raise ValueError("User must be at least 18 years old")
        return v

    @model_validator(mode="after")
    def set_computed_fields(self) -> "Profile":
        """Set age_bracket and tier_code from other fields."""
        # Calculate age bracket from DOB
        age_bracket = calculate_age_bracket(self.date_of_birth)

        # Calculate tier code
        sex_value = (
            self.biological_sex.value
            if isinstance(self.biological_sex, BiologicalSex)
            else self.biological_sex
        )
        fitness_value = (
            self.fitness_level.value
            if isinstance(self.fitness_level, FitnessLevel)
            else self.fitness_level
        )

        tier_code = calculate_tier_code(
            sex_value,
            age_bracket,
            fitness_value,
        )

        # Use object.__setattr__ to avoid triggering validate_assignment recursion
        object.__setattr__(self, "age_bracket", age_bracket)
        object.__setattr__(self, "tier_code", tier_code)
        return self
