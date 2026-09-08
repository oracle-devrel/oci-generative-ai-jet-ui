import pytest
from data_migration_harness.governance import flag_pii
from data_migration_harness.verify import counts


@pytest.mark.integration
def test_count_returns_bool():
    assert isinstance(counts.check(), bool)


def test_pii_flag_finds_reviewer_id():
    schema = {"fields": {"name": {"type": "str"}, "reviewer_id": {"type": "str"}}}
    flagged = flag_pii(schema)
    assert "reviewer_id" in flagged
