"""Commit message analysis for determining release types."""

import re
from typing import TypedDict

from contiamo_release_please.config import ReleaseConfig


class ParsedCommit(TypedDict):
    """Parsed conventional commit structure."""

    type: str
    scope: str
    breaking: bool
    description: str


# Release type priority (higher index = higher priority)
RELEASE_TYPE_PRIORITY = ["patch", "minor", "major"]

# Release commit patterns that identify release infrastructure commits
# These patterns use {release_branch} as a placeholder for dynamic substitution
RELEASE_COMMIT_PATTERNS = [
    # Pattern 1: Standard merge commit
    # Example: "Merge branch 'release-please--branches--main' into main"
    r"Merge branch '{release_branch}' into",
    # Pattern 2: GitHub PR merge commit
    # Example: "Merge pull request #72 from contiamo/release-please--branches--main"
    r"Merge pull request #\d+ from [^/]+/{release_branch}",
    # Pattern 3: Release commits (squash merge, PR title, or Azure DevOps wrapped)
    # Examples:
    # - "chore(main): update files for release 1.2.3" (squash merge)
    # - "chore(main): release 1.2.3" (PR title format)
    # - "Merged PR 10: chore(main): release 1.2.3" (Azure DevOps)
    r"^(Merged PR \d+: )?chore\([^)]+\):\s+(update files for )?release",
]


def parse_commit_message(message: str) -> ParsedCommit:
    """Parse a conventional commit message.

    Args:
        message: Commit message string

    Returns:
        Dictionary with 'type', 'scope', 'breaking', and 'description' keys
    """
    # Conventional commit format: type(scope)!: description
    # Breaking change indicators: ! after type/scope, or "BREAKING CHANGE:" in body
    pattern = r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?\s*:\s*(?P<description>.+)$"

    match = re.match(pattern, message.strip())

    if match:
        return {
            "type": match.group("type"),
            "scope": match.group("scope") or "",
            "breaking": match.group("breaking") == "!",
            "description": match.group("description"),
        }

    # If doesn't match conventional commit format, return unknown type
    return {
        "type": "unknown",
        "scope": "",
        "breaking": False,
        "description": message.strip(),
    }


def check_breaking_change(message: str, parsed: ParsedCommit) -> bool:
    """Check if commit message indicates a breaking change.

    Args:
        message: Full commit message (may include body)
        parsed: Parsed commit dictionary

    Returns:
        True if this is a breaking change
    """
    # Check for ! in commit type
    if parsed["breaking"]:
        return True

    # Check for BREAKING CHANGE: in commit body
    if "BREAKING CHANGE:" in message.upper() or "BREAKING-CHANGE:" in message.upper():
        return True

    return False


def analyse_commits(commit_messages: list[str], config: ReleaseConfig) -> str | None:
    """Analyse commit messages and determine the release type.

    Args:
        commit_messages: List of commit message strings
        config: Release configuration

    Returns:
        Release type ('major', 'minor', 'patch') or None if no relevant commits
    """
    if not commit_messages:
        return None

    highest_release_type = None
    highest_priority = -1

    for message in commit_messages:
        parsed = parse_commit_message(message)
        commit_type = parsed["type"]

        # Check for breaking changes first
        if check_breaking_change(message, parsed):
            commit_type = "breaking"

        # Get release type for this commit type
        release_type = config.get_release_type_for_prefix(commit_type)

        if release_type:
            # Check if this release type has higher priority
            priority = RELEASE_TYPE_PRIORITY.index(release_type)
            if priority > highest_priority:
                highest_priority = priority
                highest_release_type = release_type

            # Early exit if we found a major release (highest priority)
            if release_type == "major":
                break

    return highest_release_type


def get_commit_type_summary(
    commit_messages: list[str], config: ReleaseConfig
) -> dict[str, int]:
    """Get a summary of commit types found.

    Args:
        commit_messages: List of commit message strings
        config: Release configuration

    Returns:
        Dictionary mapping commit types to counts
    """
    summary: dict[str, int] = {}

    for message in commit_messages:
        parsed = parse_commit_message(message)
        commit_type = parsed["type"]

        # Check for breaking changes
        if check_breaking_change(message, parsed):
            commit_type = "breaking"

        summary[commit_type] = summary.get(commit_type, 0) + 1

    return summary


def is_release_commit(commit_message: str, release_branch_name: str) -> bool:
    """Check if commit is a release infrastructure commit that should be excluded from analysis.

    Release infrastructure commits are created by the tool itself during the release process
    and should not trigger new releases or appear in changelogs.

    Args:
        commit_message: The commit message to check
        release_branch_name: Name of the release branch (e.g., 'release-please--branches--main')

    Returns:
        True if this is a release infrastructure commit, False otherwise
    """
    for pattern in RELEASE_COMMIT_PATTERNS:
        # Substitute the release branch name into the pattern
        resolved_pattern = pattern.replace("{release_branch}", release_branch_name)

        if re.search(resolved_pattern, commit_message):
            return True

    return False
