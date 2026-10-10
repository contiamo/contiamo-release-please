"""Tests for version calculation."""

import pytest

from contiamo_release_please.version import FIRST_RELEASE, get_next_version


@pytest.mark.parametrize(
    ("current", "release_type", "expected"),
    [
        ("0.68.0", "major", "1.0.0"),
        ("0.68.0", "minor", "0.69.0"),
        ("0.68.3", "patch", "0.68.4"),
        ("1.2.3", "major", "2.0.0"),
    ],
)
def test_get_next_version_default(current, release_type, expected):
    """Test that major releases bump major by default, including below 1.0.0."""
    assert get_next_version(current, release_type) == expected


@pytest.mark.parametrize(
    ("current", "release_type", "expected"),
    [
        ("0.68.0", "major", "0.69.0"),
        ("0.68.3", "major", "0.69.0"),
        ("0.68.0", "minor", "0.69.0"),
        ("0.68.3", "patch", "0.68.4"),
        ("1.2.3", "major", "2.0.0"),
    ],
)
def test_get_next_version_bump_minor_pre_major(current, release_type, expected):
    """Test that major releases bump minor below 1.0.0 only."""
    assert (
        get_next_version(current, release_type, bump_minor_pre_major=True) == expected
    )


def test_get_next_version_bump_minor_pre_major_first_release():
    """Test that the first release is unaffected by bump_minor_pre_major."""
    assert get_next_version(None, "major", bump_minor_pre_major=True) == FIRST_RELEASE
