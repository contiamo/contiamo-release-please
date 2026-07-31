"""Tests for Azure DevOps API integration."""

import json
from unittest.mock import MagicMock, patch

from contiamo_release_please.azure import (
    MAX_PR_DESCRIPTION_LENGTH,
    create_pull_request,
    truncate_pr_description,
    update_pull_request,
)


def test_truncate_short_description_unchanged():
    """A description within the limit is passed through untouched."""
    description = "## 1.2.3\n\n### Features\n\n- something small\n"
    assert truncate_pr_description(description) == description


def test_truncate_description_exactly_at_limit_unchanged():
    """The limit itself is allowed, so no truncation at the boundary."""
    description = "x" * MAX_PR_DESCRIPTION_LENGTH
    assert truncate_pr_description(description) == description


def test_truncate_long_description_fits_limit():
    """An oversized description is cut to fit and marked as truncated."""
    description = "\n".join(f"- change number {i}" for i in range(1000))
    assert len(description) > MAX_PR_DESCRIPTION_LENGTH

    result = truncate_pr_description(description)

    assert len(result) <= MAX_PR_DESCRIPTION_LENGTH
    assert "truncated" in result.lower()
    assert "CHANGELOG.md" in result
    # The surviving content is a prefix of the original.
    assert description.startswith(result.split("\n\n---\n")[0].rstrip())


def test_truncate_prefers_line_boundary():
    """Truncation backs off to a newline rather than cutting mid-line."""
    description = "\n".join(f"- change number {i}" for i in range(1000))

    body = truncate_pr_description(description).split("\n\n---\n")[0]

    # Every retained line should be a complete line from the original.
    original_lines = set(description.split("\n"))
    assert all(line in original_lines for line in body.split("\n"))


def test_truncate_single_long_line_without_boundary():
    """A single unbroken line is still cut down to the limit."""
    description = "x" * (MAX_PR_DESCRIPTION_LENGTH * 2)

    result = truncate_pr_description(description)

    assert len(result) <= MAX_PR_DESCRIPTION_LENGTH
    assert "truncated" in result.lower()


def test_truncate_limit_too_small_for_notice():
    """A limit with no room for the footer degrades to a plain cut."""
    result = truncate_pr_description("y" * 500, limit=10)
    assert result == "y" * 10


@patch("contiamo_release_please.azure.requests.post")
def test_create_pull_request_truncates_description(mock_post):
    """create_pull_request must not send an over-long description."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"pullRequestId": 1}
    mock_post.return_value = mock_response

    create_pull_request(
        org="org",
        project="project",
        repo="repo",
        title="chore(main): release 1.0.0",
        description="\n".join(f"- change {i}" for i in range(1000)),
        source_branch="release-please--branches--main",
        target_branch="main",
        token="token",
    )

    payload = json.loads(mock_post.call_args.kwargs["data"])
    assert len(payload["description"]) <= MAX_PR_DESCRIPTION_LENGTH


@patch("contiamo_release_please.azure.requests.patch")
def test_update_pull_request_truncates_description(mock_patch):
    """update_pull_request must not send an over-long description.

    This is the path that failed in practice: the release branch pushes fine,
    then updating the existing release PR is rejected with a 400.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {"pullRequestId": 83}
    mock_patch.return_value = mock_response

    update_pull_request(
        org="org",
        project="project",
        repo="repo",
        pr_id=83,
        title="chore(main): release 1.0.0",
        description="\n".join(f"- change {i}" for i in range(1000)),
        token="token",
    )

    payload = json.loads(mock_patch.call_args.kwargs["data"])
    assert len(payload["description"]) <= MAX_PR_DESCRIPTION_LENGTH
