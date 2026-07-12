"""Path-traversal defence (audit #01): validate_id rejects unsafe ids; safe_under stays in base."""

from pathlib import Path

import pytest

from core.paths import InvalidId, safe_under, validate_id

# Six distinct traversal / injection shapes an attacker might send as a scenario/branch id.
ATTACKS = [
    "..",  # parent dir
    "/etc",  # absolute path escape
    "\\..\\..\\",  # windows-style traversal
    "%2e%2e",  # url-encoded dots
    "~",  # home expansion
    "．．",  # unicode confusable for ".."
]


@pytest.mark.parametrize("value", ATTACKS)
def test_validate_id_rejects_attacks(value):
    with pytest.raises(InvalidId):
        validate_id(value, "scenario_id")


@pytest.mark.parametrize("value", ["abc123", "fork-1720", "main", "a1b2c3d4e5f6", "A_B-c"])
def test_validate_id_accepts_safe_ids(value):
    assert validate_id(value, "scenario_id") == value


def test_validate_id_rejects_too_long():
    with pytest.raises(InvalidId):
        validate_id("x" * 65, "scenario_id")


def test_safe_under_blocks_escape(tmp_path: Path):
    (tmp_path / "ok").mkdir()
    assert safe_under(tmp_path, "ok").parent == tmp_path.resolve()
    with pytest.raises(InvalidId):
        safe_under(tmp_path, "..", "escape")
