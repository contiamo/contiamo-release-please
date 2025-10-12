"""Azure DevOps API integration for pull request creation."""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import requests


class AzureDevOpsError(Exception):
    """Raised when Azure DevOps API operations fail."""


def get_azure_token(config: dict[str, Any]) -> str:
    """Get Azure DevOps token from environment or config.

    Args:
        config: Configuration dict

    Returns:
        Azure DevOps Personal Access Token

    Raises:
        AzureDevOpsError: If no token is found
    """
    # Environment variable takes precedence
    token = os.getenv("AZURE_DEVOPS_TOKEN")
    if token:
        return token

    # Fall back to config
    azure_config = config.get("azure", {})
    token = azure_config.get("token")
    if token:
        return token

    raise AzureDevOpsError(
        "Azure DevOps token not found. Set AZURE_DEVOPS_TOKEN environment variable or "
        "add 'azure.token' to config file. Create a Personal Access Token with "
        "'Code (Read & Write)' scope at https://dev.azure.com/{org}/_usersSettings/tokens"
    )


def get_azure_repo_info(git_root: Path) -> tuple[str, str, str]:
    """Extract organisation, project, and repo name from git remote URL.

    Args:
        git_root: Git repository root path

    Returns:
        Tuple of (organisation, project, repo_name)

    Raises:
        AzureDevOpsError: If remote URL cannot be parsed
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
        # - https://dev.azure.com/org/project/_git/repo
        # - https://org@dev.azure.com/org/project/_git/repo
        # - git@ssh.dev.azure.com:v3/org/project/repo
        # - https://org.visualstudio.com/project/_git/repo

        # New Azure DevOps format (dev.azure.com)
        https_match = re.match(
            r"https://(?:[^@]+@)?dev\.azure\.com/([^/]+)/([^/]+)/_git/(.+?)(?:\.git)?$",
            remote_url,
        )
        if https_match:
            return https_match.group(1), https_match.group(2), https_match.group(3)

        # SSH format
        ssh_match = re.match(
            r"git@ssh\.dev\.azure\.com:v3/([^/]+)/([^/]+)/(.+?)(?:\.git)?$", remote_url
        )
        if ssh_match:
            return ssh_match.group(1), ssh_match.group(2), ssh_match.group(3)

        # Old visualstudio.com format
        vs_match = re.match(
            r"https://([^.]+)\.visualstudio\.com/([^/]+)/_git/(.+?)(?:\.git)?$",
            remote_url,
        )
        if vs_match:
            return vs_match.group(1), vs_match.group(2), vs_match.group(3)

        raise AzureDevOpsError(
            f"Could not parse Azure DevOps org/project/repo from remote URL: {remote_url}"
        )

    except subprocess.CalledProcessError as e:
        raise AzureDevOpsError(f"Failed to get git remote URL: {e}")


def find_existing_pr(
    org: str,
    project: str,
    repo: str,
    source_branch: str,
    target_branch: str,
    token: str,
) -> int | None:
    """Find existing PR by source and target branches.

    Args:
        org: Azure DevOps organisation
        project: Project name
        repo: Repository name
        source_branch: Source branch name (without refs/heads/)
        target_branch: Target branch name (without refs/heads/)
        token: Azure DevOps Personal Access Token

    Returns:
        PR ID if found, None otherwise

    Raises:
        AzureDevOpsError: If API request fails
    """
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/pullrequests"
    headers = {
        "Content-Type": "application/json",
    }
    params = {
        "searchCriteria.status": "active",
        "searchCriteria.sourceRefName": f"refs/heads/{source_branch}",
        "searchCriteria.targetRefName": f"refs/heads/{target_branch}",
        "api-version": "7.1",
    }

    try:
        response = requests.get(
            url,
            auth=("", token),  # Empty username, PAT as password
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        prs = response.json().get("value", [])
        if prs and len(prs) > 0:
            return prs[0]["pullRequestId"]

        return None

    except requests.exceptions.RequestException as e:
        raise AzureDevOpsError(f"Failed to check for existing PR: {e}")


def create_pull_request(
    org: str,
    project: str,
    repo: str,
    title: str,
    description: str,
    source_branch: str,
    target_branch: str,
    token: str,
) -> dict[str, Any]:
    """Create a new pull request.

    Args:
        org: Azure DevOps organisation
        project: Project name
        repo: Repository name
        title: PR title
        description: PR description
        source_branch: Source branch name (without refs/heads/)
        target_branch: Target branch name (without refs/heads/)
        token: Azure DevOps Personal Access Token

    Returns:
        PR data from Azure DevOps API

    Raises:
        AzureDevOpsError: If PR creation fails
    """
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/pullrequests"
    headers = {
        "Content-Type": "application/json",
    }
    params = {
        "api-version": "7.1",
    }
    payload = {
        "sourceRefName": f"refs/heads/{source_branch}",
        "targetRefName": f"refs/heads/{target_branch}",
        "title": title,
        "description": description,
    }

    try:
        response = requests.post(
            url,
            auth=("", token),  # Empty username, PAT as password
            headers=headers,
            params=params,
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
        raise AzureDevOpsError(error_msg)


def update_pull_request(
    org: str,
    project: str,
    repo: str,
    pr_id: int,
    title: str,
    description: str,
    token: str,
) -> dict[str, Any]:
    """Update an existing pull request.

    Args:
        org: Azure DevOps organisation
        project: Project name
        repo: Repository name
        pr_id: Pull request ID to update
        title: New PR title
        description: New PR description
        token: Azure DevOps Personal Access Token

    Returns:
        Updated PR data from Azure DevOps API

    Raises:
        AzureDevOpsError: If PR update fails
    """
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/pullrequests/{pr_id}"
    headers = {
        "Content-Type": "application/json",
    }
    params = {
        "api-version": "7.1",
    }
    payload = {
        "title": title,
        "description": description,
    }

    try:
        response = requests.patch(
            url,
            auth=("", token),  # Empty username, PAT as password
            headers=headers,
            params=params,
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
        raise AzureDevOpsError(error_msg)


def create_or_update_pr(
    org: str,
    project: str,
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
        org: Azure DevOps organisation
        project: Project name
        repo: Repository name
        title: PR title
        body: PR description
        head_branch: Source branch name
        base_branch: Target branch name
        token: Azure DevOps Personal Access Token
        dry_run: If True, only show what would be done
        verbose: If True, show detailed output

    Returns:
        PR data from Azure DevOps API, or None if dry_run

    Raises:
        AzureDevOpsError: If PR creation/update fails
    """
    if dry_run:
        return None

    # Check if PR already exists
    existing_pr = find_existing_pr(org, project, repo, head_branch, base_branch, token)

    if existing_pr:
        if verbose:
            print(f"Updating existing PR #{existing_pr}")
        return update_pull_request(org, project, repo, existing_pr, title, body, token)
    else:
        if verbose:
            print(f"Creating new PR from {head_branch} to {base_branch}")
        return create_pull_request(
            org, project, repo, title, body, head_branch, base_branch, token
        )
