"""Bitbucket Cloud API integration for pull request creation.

Only Bitbucket Cloud (bitbucket.org) is supported. Bitbucket Server and Data
Center expose a different REST API and are out of scope.

Authentication uses a repository, project or workspace *access token* sent
as a Bearer token. Access tokens are created by a repository admin under
Repository settings → Security → Access tokens and need the scopes
``repository:write`` (push branches and tags) and ``pullrequest:write``
(create and update pull requests; implies read).
"""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import requests

from contiamo_release_please.analyser import (
    BITBUCKET_MERGED_PR_RE,
    BITBUCKET_PR_SUFFIX_RE,
)

API_BASE = "https://api.bitbucket.org/2.0"


class BitbucketError(Exception):
    """Raised when Bitbucket API operations fail."""


def get_bitbucket_token(config: dict[str, Any]) -> str:
    """Get Bitbucket access token from environment or config.

    Args:
        config: Configuration dict

    Returns:
        Bitbucket access token

    Raises:
        BitbucketError: If no token is found
    """
    # Environment variable takes precedence
    token = os.getenv("BITBUCKET_TOKEN")
    if token:
        return token

    # Fall back to config
    bitbucket_config = config.get("bitbucket", {})
    token = bitbucket_config.get("token")
    if token:
        return token

    raise BitbucketError(
        "Bitbucket token not found. Set BITBUCKET_TOKEN environment variable or "
        "add 'bitbucket.token' to config file. Use a repository access token "
        "(Repository settings → Security → Access tokens, created by a repository "
        "admin) with scopes 'repository:write' and 'pullrequest:write'."
    )


def get_bitbucket_repo_info(git_root: Path) -> tuple[str, str]:
    """Extract workspace and repository slug from git remote URL.

    Args:
        git_root: Git repository root path

    Returns:
        Tuple of (workspace, repo_slug), e.g. ("appdl", "kamin")

    Raises:
        BitbucketError: If remote URL cannot be parsed
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=git_root,
            check=True,
            capture_output=True,
            text=True,
        )
        remote_url = result.stdout.strip()

        # Parse different URL formats:
        # - https://bitbucket.org/workspace/repo.git
        # - https://user@bitbucket.org/workspace/repo.git
        # - git@bitbucket.org:workspace/repo.git
        # - ssh://git@bitbucket.org/workspace/repo.git

        https_match = re.match(
            r"https://(?:[^@/]+@)?bitbucket\.org/([^/]+)/([^/]+?)(?:\.git)?/?$",
            remote_url,
        )
        if https_match:
            return https_match.group(1), https_match.group(2)

        ssh_match = re.match(
            r"(?:ssh://)?git@bitbucket\.org[:/]([^/]+)/([^/]+?)(?:\.git)?/?$",
            remote_url,
        )
        if ssh_match:
            return ssh_match.group(1), ssh_match.group(2)

        raise BitbucketError(
            f"Could not parse Bitbucket workspace/repo from remote URL: {remote_url}. "
            f"Expected Bitbucket Cloud URL format (e.g., git@bitbucket.org:workspace/repo.git)"
        )

    except subprocess.CalledProcessError as e:
        raise BitbucketError(f"Failed to get git remote URL: {e}")


def get_bitbucket_pr_url(workspace: str, repo_slug: str, pr_id: int) -> str:
    """Build the web URL of a pull request."""
    return f"https://bitbucket.org/{workspace}/{repo_slug}/pull-requests/{pr_id}"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _error_message(prefix: str, e: requests.exceptions.RequestException) -> str:
    error_msg = f"{prefix}: {e}"
    if hasattr(e, "response") and e.response is not None:
        try:
            error_data = e.response.json()
            # Bitbucket wraps errors as {"error": {"message": "..."}}
            message = error_data.get("error", {}).get("message")
            if message:
                error_msg += f" - {message}"
        except Exception:
            pass
    return error_msg


def find_existing_pr(
    workspace: str,
    repo_slug: str,
    source_branch: str,
    target_branch: str,
    token: str,
) -> int | None:
    """Find an open PR by source and destination branches.

    Args:
        workspace: Bitbucket workspace
        repo_slug: Repository slug
        source_branch: Source branch name
        target_branch: Destination branch name
        token: Bitbucket access token

    Returns:
        PR id if found, None otherwise

    Raises:
        BitbucketError: If API request fails
    """
    url = f"{API_BASE}/repositories/{workspace}/{repo_slug}/pullrequests"
    params = {
        "state": "OPEN",
        "q": (
            f'source.branch.name = "{source_branch}" AND '
            f'destination.branch.name = "{target_branch}"'
        ),
    }

    try:
        response = requests.get(url, headers=_headers(token), params=params, timeout=30)
        response.raise_for_status()

        prs = response.json().get("values", [])
        if prs:
            return prs[0]["id"]

        return None

    except requests.exceptions.RequestException as e:
        raise BitbucketError(_error_message("Failed to check for existing PR", e))


def create_pull_request(
    workspace: str,
    repo_slug: str,
    title: str,
    description: str,
    source_branch: str,
    target_branch: str,
    token: str,
) -> dict[str, Any]:
    """Create a new pull request.

    Args:
        workspace: Bitbucket workspace
        repo_slug: Repository slug
        title: PR title
        description: PR description (markdown)
        source_branch: Source branch name
        target_branch: Destination branch name
        token: Bitbucket access token

    Returns:
        PR data from Bitbucket API

    Raises:
        BitbucketError: If PR creation fails
    """
    url = f"{API_BASE}/repositories/{workspace}/{repo_slug}/pullrequests"
    payload = {
        "title": title,
        "description": description,
        "source": {"branch": {"name": source_branch}},
        "destination": {"branch": {"name": target_branch}},
        "close_source_branch": True,
    }

    try:
        response = requests.post(
            url,
            headers=_headers(token),
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        raise BitbucketError(_error_message("Failed to create pull request", e))


def update_pull_request(
    workspace: str,
    repo_slug: str,
    pr_id: int,
    title: str,
    description: str,
    token: str,
) -> dict[str, Any]:
    """Update an existing pull request.

    Args:
        workspace: Bitbucket workspace
        repo_slug: Repository slug
        pr_id: Pull request id to update
        title: New PR title
        description: New PR description
        token: Bitbucket access token

    Returns:
        Updated PR data from Bitbucket API

    Raises:
        BitbucketError: If PR update fails
    """
    url = f"{API_BASE}/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}"
    payload = {
        "title": title,
        "description": description,
    }

    try:
        response = requests.put(
            url,
            headers=_headers(token),
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        raise BitbucketError(_error_message("Failed to update pull request", e))


def get_pull_request_title(
    workspace: str,
    repo_slug: str,
    pr_id: int,
    token: str,
) -> str | None:
    """Return the title of a pull request, or None if it cannot be fetched.

    Failures are silently suppressed so a missing or inaccessible PR never
    blocks a release; callers fall back to whatever git already knows.
    """
    url = f"{API_BASE}/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}"

    try:
        response = requests.get(url, headers=_headers(token), timeout=30)
        if response.status_code != 200:
            return None
        title = response.json().get("title")
        return title.strip() if isinstance(title, str) and title.strip() else None
    except requests.exceptions.RequestException:
        return None


def extract_pr_id(message: str) -> int | None:
    """Return the PR id carried by a (normalised or raw) Bitbucket merge subject."""
    match = BITBUCKET_PR_SUFFIX_RE.search(message) or BITBUCKET_MERGED_PR_RE.match(
        message.strip()
    )
    return int(match.group("pr_id")) if match else None


def resolve_merge_commit_titles(
    commits_with_sha: list[tuple[str, str]],
    workspace: str,
    repo_slug: str,
    token: str,
) -> list[tuple[str, str]]:
    """Replace Bitbucket merge subjects with the authoritative PR title from the API.

    git.py already promotes the first body line of a Bitbucket merge commit to
    the subject. That is a good offline approximation, but the merge message
    can be edited at merge time, so when a token is available the title is
    fetched from the API instead. The "(pull request #N)" suffix is kept so
    the changelog can link the PR.

    Commits without a PR id, or whose title cannot be fetched, are returned
    unchanged.
    """
    resolved: list[tuple[str, str]] = []
    for sha, message in commits_with_sha:
        pr_id = extract_pr_id(message)
        if pr_id is None:
            resolved.append((sha, message))
            continue

        title = get_pull_request_title(workspace, repo_slug, pr_id, token)
        if title is None:
            resolved.append((sha, message))
            continue

        resolved.append((sha, f"{title} (pull request #{pr_id})"))
    return resolved


def create_or_update_pr(
    workspace: str,
    repo_slug: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str,
    token: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any] | None:
    """Create a new PR or update existing one.

    Args:
        workspace: Bitbucket workspace
        repo_slug: Repository slug
        title: PR title
        body: PR description
        head_branch: Source branch name
        base_branch: Destination branch name
        token: Bitbucket access token
        dry_run: If True, only show what would be done
        verbose: If True, show detailed output

    Returns:
        PR data from Bitbucket API, or None if dry_run

    Raises:
        BitbucketError: If PR creation/update fails
    """
    if dry_run:
        return None

    # Check if PR already exists
    existing_pr = find_existing_pr(
        workspace, repo_slug, head_branch, base_branch, token
    )

    if existing_pr:
        if verbose:
            print(f"Updating existing PR #{existing_pr}")
        return update_pull_request(
            workspace, repo_slug, existing_pr, title, body, token
        )
    else:
        if verbose:
            print(f"Creating new PR from {head_branch} to {base_branch}")
        return create_pull_request(
            workspace, repo_slug, title, body, head_branch, base_branch, token
        )
