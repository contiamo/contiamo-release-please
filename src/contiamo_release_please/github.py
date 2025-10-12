"""GitHub API integration for pull request creation."""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import requests


class GitHubError(Exception):
    """Raised when GitHub API operations fail."""


def get_github_token(config: dict[str, Any]) -> str:
    """Get GitHub token from environment or config.

    Args:
        config: Configuration dict

    Returns:
        GitHub token

    Raises:
        GitHubError: If no token is found
    """
    # Environment variable takes precedence
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token

    # Fall back to config
    github_config = config.get("github", {})
    token = github_config.get("token")
    if token:
        return token

    raise GitHubError(
        "GitHub token not found. Set GITHUB_TOKEN environment variable or "
        "add 'github.token' to config file. Token needs 'repo' scope for "
        "private repos, 'public_repo' for public repos."
    )


def get_repo_info(git_root: Path) -> tuple[str, str]:
    """Extract owner and repo name from git remote URL.

    Args:
        git_root: Git repository root path

    Returns:
        Tuple of (owner, repo_name)

    Raises:
        GitHubError: If remote URL cannot be parsed
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
        # - https://github.com/owner/repo.git
        # - git@github.com:owner/repo.git
        # - https://github.com/owner/repo

        # HTTPS format
        https_match = re.match(
            r"https://github\.com/([^/]+)/(.+?)(?:\.git)?$", remote_url
        )
        if https_match:
            return https_match.group(1), https_match.group(2)

        # SSH format
        ssh_match = re.match(r"git@github\.com:([^/]+)/(.+?)(?:\.git)?$", remote_url)
        if ssh_match:
            return ssh_match.group(1), ssh_match.group(2)

        raise GitHubError(
            f"Could not parse GitHub owner/repo from remote URL: {remote_url}"
        )

    except subprocess.CalledProcessError as e:
        raise GitHubError(f"Failed to get git remote URL: {e}")


def find_existing_pr(
    owner: str,
    repo: str,
    head_branch: str,
    base_branch: str,
    token: str,
) -> int | None:
    """Find existing PR by head and base branches.

    Args:
        owner: Repository owner
        repo: Repository name
        head_branch: Source branch
        base_branch: Target branch
        token: GitHub token

    Returns:
        PR number if found, None otherwise

    Raises:
        GitHubError: If API request fails
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    params = {
        "state": "open",
        "head": f"{owner}:{head_branch}",
        "base": base_branch,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        prs = response.json()
        if prs and len(prs) > 0:
            return prs[0]["number"]

        return None

    except requests.exceptions.RequestException as e:
        raise GitHubError(f"Failed to check for existing PR: {e}")


def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str,
    token: str,
) -> dict[str, Any]:
    """Create a new pull request.

    Args:
        owner: Repository owner
        repo: Repository name
        title: PR title
        body: PR description
        head_branch: Source branch
        base_branch: Target branch
        token: GitHub token

    Returns:
        PR data from GitHub API

    Raises:
        GitHubError: If PR creation fails
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    payload = {
        "title": title,
        "body": body,
        "head": head_branch,
        "base": base_branch,
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to create pull request: {e}"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                if "message" in error_data:
                    error_msg += f" - {error_data['message']}"
            except Exception:
                pass
        raise GitHubError(error_msg)


def update_pull_request(
    owner: str,
    repo: str,
    pr_number: int,
    title: str,
    body: str,
    token: str,
) -> dict[str, Any]:
    """Update an existing pull request.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number to update
        title: New PR title
        body: New PR description
        token: GitHub token

    Returns:
        Updated PR data from GitHub API

    Raises:
        GitHubError: If PR update fails
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    payload = {
        "title": title,
        "body": body,
    }

    try:
        response = requests.patch(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to update pull request: {e}"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                if "message" in error_data:
                    error_msg += f" - {error_data['message']}"
            except Exception:
                pass
        raise GitHubError(error_msg)


def create_github_release(
    owner: str,
    repo: str,
    tag_name: str,
    release_name: str,
    body: str,
    token: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any] | None:
    """Create a GitHub release.

    Args:
        owner: Repository owner
        repo: Repository name
        tag_name: Git tag name for the release
        release_name: Name of the release
        body: Release description (markdown)
        token: GitHub token
        dry_run: If True, only show what would be done
        verbose: If True, show detailed output

    Returns:
        Release data from GitHub API, or None if dry_run

    Raises:
        GitHubError: If release creation fails
    """
    if dry_run:
        return None

    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    payload = {
        "tag_name": tag_name,
        "name": release_name,
        "body": body,
        "draft": False,
        "prerelease": False,
    }

    try:
        if verbose:
            print(f"Creating GitHub release for tag {tag_name}")

        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to create GitHub release: {e}"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                if "message" in error_data:
                    error_msg += f" - {error_data['message']}"
            except Exception:
                pass
        raise GitHubError(error_msg)


def create_or_update_pr(
    owner: str,
    repo: str,
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
        owner: Repository owner
        repo: Repository name
        title: PR title
        body: PR description
        head_branch: Source branch
        base_branch: Target branch
        token: GitHub token
        dry_run: If True, only show what would be done
        verbose: If True, show detailed output

    Returns:
        PR data from GitHub API, or None if dry_run

    Raises:
        GitHubError: If PR creation/update fails
    """
    if dry_run:
        return None

    # Check if PR already exists
    existing_pr = find_existing_pr(owner, repo, head_branch, base_branch, token)

    if existing_pr:
        if verbose:
            print(f"Updating existing PR #{existing_pr}")
        return update_pull_request(owner, repo, existing_pr, title, body, token)
    else:
        if verbose:
            print(f"Creating new PR from {head_branch} to {base_branch}")
        return create_pull_request(
            owner, repo, title, body, head_branch, base_branch, token
        )
