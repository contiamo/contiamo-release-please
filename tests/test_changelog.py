"""Tests for changelog generation."""

import tempfile
from pathlib import Path
from typing import cast

import pytest

from contiamo_release_please.analyser import ParsedCommit
from contiamo_release_please.changelog import (
    extract_changelog_for_version,
    format_changelog_entry,
    group_commits_by_section,
    prepend_to_changelog,
)
from contiamo_release_please.config import ReleaseConfig


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    config_content = """
version-prefix: "v"

release-rules:
  major:
    - breaking
  minor:
    - feat
  patch:
    - fix
    - chore
    - docs
    - refactor
    - ci

changelog-sections:
  - type: feat
    section: Features
  - type: fix
    section: Bug Fixes
  - type: chore
    section: Miscellaneous Changes
  - type: ci
    section: Miscellaneous Changes
  - type: docs
    section: Documentation
  - type: refactor
    section: Code Refactoring
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        temp_path = f.name

    yield temp_path
    Path(temp_path).unlink()


def test_group_commits_by_section(temp_config_file):
    """Test grouping commits by their changelog section."""
    config = ReleaseConfig(temp_config_file)

    commits = [
        "feat: add user authentication",
        "fix: correct login redirect",
        "feat: implement dashboard",
        "docs: update README",
        "chore: update dependencies",
    ]

    grouped = group_commits_by_section(commits, config)

    assert "Features" in grouped
    assert "Bug Fixes" in grouped
    assert "Documentation" in grouped
    assert "Miscellaneous Changes" in grouped

    assert len(grouped["Features"]) == 2
    assert len(grouped["Bug Fixes"]) == 1
    assert len(grouped["Documentation"]) == 1
    assert len(grouped["Miscellaneous Changes"]) == 1


def test_group_commits_with_scopes(temp_config_file):
    """Test grouping commits that have scopes."""
    config = ReleaseConfig(temp_config_file)

    commits = [
        "feat(auth): add user authentication",
        "fix(ui): correct login redirect",
        "feat(dashboard): implement dashboard",
    ]

    grouped = group_commits_by_section(commits, config)

    assert "Features" in grouped
    assert "Bug Fixes" in grouped
    assert len(grouped["Features"]) == 2
    assert len(grouped["Bug Fixes"]) == 1

    # Check that scopes are preserved
    features = grouped["Features"]
    assert features[0]["scope"] == "auth"
    assert features[1]["scope"] == "dashboard"


def test_group_commits_ignores_unknown_types(temp_config_file):
    """Test that unknown commit types are ignored."""
    config = ReleaseConfig(temp_config_file)

    commits = [
        "feat: add feature",
        "not a conventional commit",
        "random: unknown type",
    ]

    grouped = group_commits_by_section(commits, config)

    assert "Features" in grouped
    assert len(grouped["Features"]) == 1
    # Unknown types should not create sections
    assert len(grouped) == 1


def test_format_changelog_entry_basic(temp_config_file):
    """Test basic changelog entry formatting."""
    config = ReleaseConfig(temp_config_file)

    grouped = {
        "Features": [
            cast(
                ParsedCommit,
                {
                    "type": "feat",
                    "scope": "",
                    "breaking": False,
                    "description": "add user authentication",
                },
            )
        ],
        "Bug Fixes": [
            cast(
                ParsedCommit,
                {
                    "type": "fix",
                    "scope": "",
                    "breaking": False,
                    "description": "correct login redirect",
                },
            )
        ],
    }

    entry = format_changelog_entry("1.2.0", grouped, config, date="2025-10-10")

    assert "## [1.2.0] (2025-10-10)" in entry
    assert "### Features" in entry
    assert "* add user authentication" in entry
    assert "### Bug Fixes" in entry
    assert "* correct login redirect" in entry


def test_format_changelog_entry_with_scopes(temp_config_file):
    """Test changelog entry formatting with scopes."""
    config = ReleaseConfig(temp_config_file)

    grouped = {
        "Features": [
            cast(
                ParsedCommit,
                {
                    "type": "feat",
                    "scope": "auth",
                    "breaking": False,
                    "description": "add user authentication",
                },
            )
        ],
        "Bug Fixes": [
            cast(
                ParsedCommit,
                {
                    "type": "fix",
                    "scope": "ui",
                    "breaking": False,
                    "description": "correct login redirect",
                },
            )
        ],
    }

    entry = format_changelog_entry("1.2.0", grouped, config, date="2025-10-10")

    assert "* **auth**: add user authentication" in entry
    assert "* **ui**: correct login redirect" in entry


def test_format_changelog_entry_section_order(temp_config_file):
    """Test that sections appear in configured order."""
    config = ReleaseConfig(temp_config_file)

    grouped = {
        "Documentation": [
            cast(
                ParsedCommit,
                {
                    "type": "docs",
                    "scope": "",
                    "breaking": False,
                    "description": "update README",
                },
            )
        ],
        "Features": [
            cast(
                ParsedCommit,
                {
                    "type": "feat",
                    "scope": "",
                    "breaking": False,
                    "description": "add feature",
                },
            )
        ],
        "Bug Fixes": [
            cast(
                ParsedCommit,
                {
                    "type": "fix",
                    "scope": "",
                    "breaking": False,
                    "description": "fix bug",
                },
            )
        ],
    }

    entry = format_changelog_entry("1.0.0", grouped, config, date="2025-10-10")

    # Features should come before Bug Fixes, which should come before Documentation
    features_pos = entry.find("### Features")
    bugfixes_pos = entry.find("### Bug Fixes")
    docs_pos = entry.find("### Documentation")

    assert features_pos < bugfixes_pos < docs_pos


def test_prepend_to_changelog_new_file():
    """Test creating a new changelog file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        changelog_path = Path(tmpdir) / "CHANGELOG.md"

        new_entry = """## [1.0.0] (2025-10-10)

### Features

* add initial feature
"""

        prepend_to_changelog(changelog_path, new_entry)

        assert changelog_path.exists()
        content = changelog_path.read_text()

        assert "# Changelog" in content
        assert "## [1.0.0]" in content
        assert "### Features" in content


def test_prepend_to_changelog_existing_file():
    """Test prepending to an existing changelog file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        changelog_path = Path(tmpdir) / "CHANGELOG.md"

        # Create existing changelog
        existing_content = """# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] (2025-09-01)

### Features

* initial release
"""
        changelog_path.write_text(existing_content)

        # Prepend new entry
        new_entry = """## [1.1.0] (2025-10-10)

### Features

* add new feature
"""

        prepend_to_changelog(changelog_path, new_entry)

        content = changelog_path.read_text()

        # New entry should come before old entry
        new_pos = content.find("## [1.1.0]")
        old_pos = content.find("## [1.0.0]")

        assert new_pos < old_pos
        assert "# Changelog" in content


def test_prepend_to_changelog_preserves_header():
    """Test that prepending preserves the changelog header."""
    with tempfile.TemporaryDirectory() as tmpdir:
        changelog_path = Path(tmpdir) / "CHANGELOG.md"

        # Create existing changelog with custom header
        existing_content = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [1.0.0] (2025-09-01)

### Features

* initial release
"""
        changelog_path.write_text(existing_content)

        # Prepend new entry
        new_entry = """## [1.1.0] (2025-10-10)

### Features

* add new feature
"""

        prepend_to_changelog(changelog_path, new_entry)

        content = changelog_path.read_text()

        # Header should be preserved
        assert content.startswith("# Changelog")
        assert "The format is based on Keep a Changelog" in content


def test_config_get_changelog_path_default(temp_config_file):
    """Test that default changelog path is returned."""
    config = ReleaseConfig(temp_config_file)
    assert config.get_changelog_path() == "CHANGELOG.md"


def test_config_get_changelog_sections_default(temp_config_file):
    """Test that changelog sections are loaded from config."""
    config = ReleaseConfig(temp_config_file)
    sections = config.get_changelog_sections()

    assert len(sections) == 6
    assert sections[0] == {"type": "feat", "section": "Features"}
    assert sections[1] == {"type": "fix", "section": "Bug Fixes"}


def test_extract_changelog_for_version():
    """Test extracting changelog entry for a specific version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        changelog_path = Path(tmpdir) / "CHANGELOG.md"
        content = """# Changelog

All notable changes to this project will be documented in this file.

## [1.2.3] (2025-01-10)

### Features

* **auth**: Add OAuth support
* Add new dashboard

### Bug Fixes

* Fix login issue

## [1.2.2] (2025-01-05)

### Features

* Add profile page
"""
        changelog_path.write_text(content)

        # Extract version 1.2.3
        result = extract_changelog_for_version(changelog_path, "1.2.3")
        assert result is not None
        assert "### Features" in result
        assert "**auth**: Add OAuth support" in result
        assert "### Bug Fixes" in result
        assert "Fix login issue" in result
        # Should not include the next version
        assert "1.2.2" not in result
        assert "Add profile page" not in result


def test_extract_changelog_for_version_first_entry():
    """Test extracting the first (most recent) changelog entry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        changelog_path = Path(tmpdir) / "CHANGELOG.md"
        content = """# Changelog

## [2.0.0] (2025-01-15)

### Features

* Major refactor
"""
        changelog_path.write_text(content)

        result = extract_changelog_for_version(changelog_path, "2.0.0")
        assert result is not None
        assert "### Features" in result
        assert "Major refactor" in result


def test_extract_changelog_for_version_not_found():
    """Test that None is returned when version doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        changelog_path = Path(tmpdir) / "CHANGELOG.md"
        content = """# Changelog

## [1.0.0] (2025-01-01)

### Features

* Initial release
"""
        changelog_path.write_text(content)

        result = extract_changelog_for_version(changelog_path, "9.9.9")
        assert result is None


def test_extract_changelog_for_version_file_not_found():
    """Test that None is returned when file doesn't exist."""
    changelog_path = Path("/nonexistent/CHANGELOG.md")
    result = extract_changelog_for_version(changelog_path, "1.0.0")
    assert result is None
