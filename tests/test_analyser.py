"""Tests for commit analysis functionality."""

import pytest

from contiamo_release_please.analyser import (
    analyse_commits,
    check_breaking_change,
    get_commit_type_summary,
    parse_commit_message,
)
from contiamo_release_please.config import ReleaseConfig


@pytest.fixture
def config(tmp_path):
    """Create a test configuration file."""
    config_content = """
release-rules:
  major:
    - breaking
  minor:
    - feat
  patch:
    - fix
    - chore
"""
    config_file = tmp_path / "test-config.yaml"
    config_file.write_text(config_content)
    return ReleaseConfig(config_file)


class TestParseCommitMessage:
    """Tests for parse_commit_message function."""

    def test_simple_commit(self):
        """Test parsing a simple conventional commit."""
        result = parse_commit_message("feat: add new feature")
        assert result["type"] == "feat"
        assert result["description"] == "add new feature"
        assert result["scope"] == ""
        assert result["breaking"] is False

    def test_commit_with_scope(self):
        """Test parsing a commit with scope."""
        result = parse_commit_message("fix(api): resolve bug")
        assert result["type"] == "fix"
        assert result["scope"] == "api"
        assert result["description"] == "resolve bug"
        assert result["breaking"] is False

    def test_breaking_change_with_exclamation(self):
        """Test parsing a breaking change with ! indicator."""
        result = parse_commit_message("feat!: breaking change")
        assert result["type"] == "feat"
        assert result["breaking"] is True

    def test_breaking_change_with_scope(self):
        """Test parsing a breaking change with scope."""
        result = parse_commit_message("feat(api)!: breaking API change")
        assert result["type"] == "feat"
        assert result["scope"] == "api"
        assert result["breaking"] is True

    def test_non_conventional_commit(self):
        """Test parsing a non-conventional commit."""
        result = parse_commit_message("some random commit message")
        assert result["type"] == "unknown"
        assert result["breaking"] is False


class TestCheckBreakingChange:
    """Tests for check_breaking_change function."""

    def test_breaking_with_exclamation(self):
        """Test detecting breaking change with ! in commit type."""
        parsed = {"breaking": True, "type": "feat"}
        assert check_breaking_change("feat!: test", parsed) is True

    def test_breaking_with_footer(self):
        """Test detecting breaking change in commit body."""
        parsed = {"breaking": False, "type": "feat"}
        message = "feat: test\n\nBREAKING CHANGE: this breaks things"
        assert check_breaking_change(message, parsed) is True

    def test_not_breaking(self):
        """Test non-breaking commit."""
        parsed = {"breaking": False, "type": "feat"}
        assert check_breaking_change("feat: test", parsed) is False


class TestAnalyseCommits:
    """Tests for analyse_commits function."""

    def test_empty_commits(self, config):
        """Test with no commits."""
        result = analyse_commits([], config)
        assert result is None

    def test_patch_commits_only(self, config):
        """Test with only patch-level commits."""
        commits = [
            "fix: bug fix",
            "chore: update dependencies",
        ]
        result = analyse_commits(commits, config)
        assert result == "patch"

    def test_minor_commits(self, config):
        """Test with minor-level commits."""
        commits = [
            "feat: new feature",
            "fix: bug fix",
        ]
        result = analyse_commits(commits, config)
        assert result == "minor"

    def test_major_commits(self, config):
        """Test with breaking changes."""
        commits = [
            "feat!: breaking change",
            "feat: new feature",
            "fix: bug fix",
        ]
        result = analyse_commits(commits, config)
        assert result == "major"

    def test_priority_ordering(self, config):
        """Test that major > minor > patch in priority."""
        commits = [
            "fix: patch change",
            "feat: minor change",
            "feat!: major change",
        ]
        result = analyse_commits(commits, config)
        assert result == "major"

    def test_unknown_commit_types_ignored(self, config):
        """Test that unknown commit types are ignored."""
        commits = [
            "random: not a valid type",
            "fix: valid fix",
        ]
        result = analyse_commits(commits, config)
        assert result == "patch"

    def test_only_unknown_commits(self, config):
        """Test with only unknown commit types."""
        commits = [
            "random: message",
            "another: message",
        ]
        result = analyse_commits(commits, config)
        assert result is None


class TestGetCommitTypeSummary:
    """Tests for get_commit_type_summary function."""

    def test_summary_counts(self, config):
        """Test that commit types are counted correctly."""
        commits = [
            "feat: feature 1",
            "feat: feature 2",
            "fix: fix 1",
            "chore: chore 1",
        ]
        summary = get_commit_type_summary(commits, config)
        assert summary["feat"] == 2
        assert summary["fix"] == 1
        assert summary["chore"] == 1

    def test_breaking_in_summary(self, config):
        """Test that breaking changes are counted separately."""
        commits = [
            "feat!: breaking feature",
            "feat: regular feature",
        ]
        summary = get_commit_type_summary(commits, config)
        assert summary["breaking"] == 1
        assert summary["feat"] == 1
