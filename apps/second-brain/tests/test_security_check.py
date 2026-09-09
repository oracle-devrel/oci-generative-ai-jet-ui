"""Pure tests for the routine security check (no DB needed).

Run:  ./.venv/bin/python tests/test_security_check.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import security_check as sc  # noqa: E402
from redaction import redact  # noqa: E402


def test_redaction_catches_known_shapes():
    for sample in ["sk-ant-api03-AbCdEf1234567890AbCdEf",
                   "sk-proj-AbCdEf1234567890AbCdEfGh",
                   "AKIAIOSFODNN7EXAMPLE",
                   "ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345",
                   "xoxb-1234567890-abcdefghij",
                   "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaws"]:
        assert "[REDACTED]" in redact(f"x {sample} y"), sample


def test_redaction_leaves_prose_alone():
    for sample in ["the desk-with-ocean-view photo",
                   "kiosk-mode-enabled-for-the-day",
                   "meet at 12:30 tomorrow",
                   "no credentials here at all"]:
        assert redact(sample) == sample, sample


def test_tracked_secret_scan_is_clean_on_this_repo():
    findings = []
    sc.check_tracked_secrets(findings)
    reds = [m for lvl, m in findings if lvl == "RED"]
    assert not reds, reds


def test_ignore_guards_hold_on_this_repo():
    findings = []
    sc.check_ignore_guards(findings)
    reds = [m for lvl, m in findings if lvl == "RED"]
    assert not reds, reds


def test_hook_matrix_holds_on_this_repo():
    findings = []
    sc.check_hook(findings)
    reds = [m for lvl, m in findings if lvl == "RED"]
    assert not reds, reds


def test_hook_absence_is_a_nudge_not_an_alarm(tmp_root=None):
    real = sc.ROOT
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            sc.ROOT = pathlib.Path(td)
            findings = []
            sc.check_hook(findings)
            assert findings and findings[0][0] == "SKIP", findings
    finally:
        sc.ROOT = real


def test_deploy_pins_hold_on_this_repo():
    findings = []
    sc.check_pins(findings)
    reds = [m for lvl, m in findings if lvl == "RED"]
    assert not reds, reds


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
                passed += 1
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
