"""GitLab API integration for merge request creation."""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import requests


class GitLabError(Exception):
    """Raised when GitLab API operations fail."""


def get_gitlab_token(config: dict[str, Any]) -> str:
    """Get GitLab token from environment or config.

    Args:
        config: Configuration dict

    Returns:
        GitLab token

    Raises:
        GitLabError: If no token is found
    """
    # Environment variable takes precedence
    token = os.getenv("GITLAB_TOKEN")
    if token:
        return token

    # Fall back to config
    gitlab_config = config.get("gitlab", {})
    token = gitlab_config.get("token")
    if token:
        return token

    raise GitLabError(
        "GitLab token not found. Set GITLAB_TOKEN environment variable or "
        "add 'gitlab.token' to config file. Token needs 'api' scope. "
        "Create at: Settings → Access Tokens (for personal repos) or "
        "Settings → Access Tokens (for group repos)."
    )


def get_gitlab_repo_info(git_root: Path) -> tuple[str, str]:
    """Extract GitLab host and project path from git remote URL.

    Args:
        git_root: Git repository root path

    Returns:
        Tuple of (gitlab_host, project_path)
        Example: ("gitlab.com", "owner/repo")
                 ("gitlab.devops.telekom.de", "gsus/innovationplatform/dcpo/agent/apps/bond")

    Raises:
        GitLabError: If remote URL cannot be parsed
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
        # - https://gitlab.com/owner/repo.git
        # - https://gitlab.devops.telekom.de/org/subgroup/project.git
        # - git@gitlab.com:owner/repo.git
        # - git@gitlab.devops.telekom.de:org/subgroup/project.git

        # HTTPS format
        https_match = re.match(r"https://([^/]+)/(.+?)(?:\.git)?$", remote_url)
        if https_match:
            host = https_match.group(1)
            project_path = https_match.group(2)
            # Validate it's actually GitLab
            if "gitlab" in host.lower():
                return host, project_path

        # SSH format
        ssh_match = re.match(r"git@([^:]+):(.+?)(?:\.git)?$", remote_url)
        if ssh_match:
            host = ssh_match.group(1)
            project_path = ssh_match.group(2)
            # Validate it's actually GitLab
            if "gitlab" in host.lower():
                return host, project_path

        raise GitLabError(
            f"Could not parse GitLab host/project from remote URL: {remote_url}. "
            f"Expected GitLab URL format (e.g., https://gitlab.com/owner/repo.git)"
        )

    except subprocess.CalledProcessError as e:
        raise GitLabError(f"Failed to get git remote URL: {e}")


def get_project_id(host: str, project_path: str) -> str:
    """Get URL-encoded project ID for GitLab API.

    GitLab API requires project paths to be URL-encoded when used in API URLs.
    Example: "gsus/innovationplatform/dcpo" -> "gsus%2Finnovationplatform%2Fdcpo"

    Args:
        host: GitLab host (not used, kept for API consistency)
        project_path: Project path (e.g., "owner/repo" or "group/subgroup/project")

    Returns:
        URL-encoded project ID for use in API calls
    """
    return quote_plus(project_path)


def find_existing_pr(
    host: str,
    project_path: str,
    source_branch: str,
    target_branch: str,
    token: str,
) -> int | None:
    """Find existing MR by source and target branches.

    Args:
        host: GitLab host (e.g., "gitlab.com", "gitlab.devops.telekom.de")
        project_path: Project path (e.g., "owner/repo")
        source_branch: Source branch name
        target_branch: Target branch name
        token: GitLab Personal Access Token

    Returns:
        MR IID (internal ID) if found, None otherwise

    Raises:
        GitLabError: If API request fails
    """
    project_id = get_project_id(host, project_path)
    url = f"https://{host}/api/v4/projects/{project_id}/merge_requests"
    headers = {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json",
    }
    params = {
        "state": "opened",
        "source_branch": source_branch,
        "target_branch": target_branch,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        mrs = response.json()
        if mrs and len(mrs) > 0:
            return mrs[0]["iid"]

        return None

    except requests.exceptions.RequestException as e:
        raise GitLabError(f"Failed to check for existing MR: {e}")


def create_pull_request(
    host: str,
    project_path: str,
    title: str,
    description: str,
    source_branch: str,
    target_branch: str,
    token: str,
) -> dict[str, Any]:
    """Create a new merge request.

    Args:
        host: GitLab host (e.g., "gitlab.com")
        project_path: Project path (e.g., "owner/repo")
        title: MR title
        description: MR description
        source_branch: Source branch name
        target_branch: Target branch name
        token: GitLab Personal Access Token

    Returns:
        MR data from GitLab API

    Raises:
        GitLabError: If MR creation fails
    """
    project_id = get_project_id(host, project_path)
    url = f"https://{host}/api/v4/projects/{project_id}/merge_requests"
    headers = {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json",
    }
    payload = {
        "source_branch": source_branch,
        "target_branch": target_branch,
        "title": title,
        "description": description,
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
        error_msg = f"Failed to create merge request: {e}"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                if "message" in error_data:
                    error_msg += f" - {error_data['message']}"
            except Exception:
                pass
        raise GitLabError(error_msg)


def update_pull_request(
    host: str,
    project_path: str,
    mr_iid: int,
    title: str,
    description: str,
    token: str,
) -> dict[str, Any]:
    """Update an existing merge request.

    Args:
        host: GitLab host
        project_path: Project path
        mr_iid: Merge request IID (internal ID) to update
        title: New MR title
        description: New MR description
        token: GitLab Personal Access Token

    Returns:
        Updated MR data from GitLab API

    Raises:
        GitLabError: If MR update fails
    """
    project_id = get_project_id(host, project_path)
    url = f"https://{host}/api/v4/projects/{project_id}/merge_requests/{mr_iid}"
    headers = {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json",
    }
    payload = {
        "title": title,
        "description": description,
    }

    try:
        response = requests.put(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to update merge request: {e}"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                if "message" in error_data:
                    error_msg += f" - {error_data['message']}"
            except Exception:
                pass
        raise GitLabError(error_msg)


def create_gitlab_release(
    host: str,
    project_path: str,
    tag_name: str,
    release_name: str,
    description: str,
    token: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any] | None:
    """Create a GitLab release.

    Args:
        host: GitLab host
        project_path: Project path
        tag_name: Git tag name for the release
        release_name: Name of the release
        description: Release description (markdown)
        token: GitLab Personal Access Token
        dry_run: If True, only show what would be done
        verbose: If True, show detailed output

    Returns:
        Release data from GitLab API, or None if dry_run

    Raises:
        GitLabError: If release creation fails
    """
    if dry_run:
        return None

    project_id = get_project_id(host, project_path)
    url = f"https://{host}/api/v4/projects/{project_id}/releases"
    headers = {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json",
    }
    payload = {
        "tag_name": tag_name,
        "name": release_name,
        "description": description,
    }

    try:
        if verbose:
            print(f"Creating GitLab release for tag {tag_name}")

        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to create GitLab release: {e}"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                if "message" in error_data:
                    error_msg += f" - {error_data['message']}"
            except Exception:
                pass
        raise GitLabError(error_msg)


def create_or_update_pr(
    host: str,
    project_path: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str,
    token: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any] | None:
    """Create a new MR or update existing one.

    Args:
        host: GitLab host
        project_path: Project path
        title: MR title
        body: MR description
        head_branch: Source branch name
        base_branch: Target branch name
        token: GitLab Personal Access Token
        dry_run: If True, only show what would be done
        verbose: If True, show detailed output

    Returns:
        MR data from GitLab API, or None if dry_run

    Raises:
        GitLabError: If MR creation/update fails
    """
    if dry_run:
        return None

    # Check if MR already exists
    existing_mr = find_existing_pr(host, project_path, head_branch, base_branch, token)

    if existing_mr:
        if verbose:
            print(f"Updating existing MR !{existing_mr}")
        return update_pull_request(host, project_path, existing_mr, title, body, token)
    else:
        if verbose:
            print(f"Creating new MR from {head_branch} to {base_branch}")
        return create_pull_request(
            host, project_path, title, body, head_branch, base_branch, token
        )
