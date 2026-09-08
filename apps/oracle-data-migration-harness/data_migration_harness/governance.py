"""Layer 9: PII flag-only in v3."""

PII_FIELD_HINTS = {"email", "phone", "ssn", "reviewer_id"}


def flag_pii(schema: dict) -> dict:
    flagged = {}
    for field in schema.get("fields", {}):
        if any(hint in field.lower() for hint in PII_FIELD_HINTS):
            flagged[field] = "likely_pii"
    return flagged
