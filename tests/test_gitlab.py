"""Tests for GitLab API integration."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from contiamo_release_please.gitlab import (
    GitLabError,
    create_gitlab_release,
    create_or_update_pr,
    create_pull_request,
    find_existing_pr,
    get_gitlab_repo_info,
    get_gitlab_token,
    get_project_id,
    update_pull_request,
)


def test_get_gitlab_token_from_env():
    """Test getting GitLab token from environment variable."""
    with patch.dict(os.environ, {"GITLAB_TOKEN": "test-token"}):
        assert get_gitlab_token({}) == "test-token"


def test_get_gitlab_token_from_config():
    """Test getting GitLab token from config."""
    config = {"gitlab": {"token": "config-token"}}
    with patch.dict(os.environ, {}, clear=True):
        assert get_gitlab_token(config) == "config-token"


def test_get_gitlab_token_env_precedence():
    """Test that environment variable takes precedence over config."""
    config = {"gitlab": {"token": "config-token"}}
    with patch.dict(os.environ, {"GITLAB_TOKEN": "env-token"}):
        assert get_gitlab_token(config) == "env-token"


def test_get_gitlab_token_not_found():
    """Test error when no token is available."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(GitLabError, match="GitLab token not found"):
            get_gitlab_token({})


def test_get_gitlab_repo_info_https():
    """Test parsing HTTPS GitLab URL."""
    mock_run = MagicMock()
    mock_run.stdout = "https://gitlab.com/owner/repo.git\n"
    mock_run.returncode = 0

    with patch("subprocess.run", return_value=mock_run):
        host, project_path = get_gitlab_repo_info(Path("/test"))

    assert host == "gitlab.com"
    assert project_path == "owner/repo"


def test_get_gitlab_repo_info_https_custom_instance():
    """Test parsing custom GitLab instance HTTPS URL."""
    mock_run = MagicMock()
    mock_run.stdout = "https://gitlab.devops.telekom.de/gsus/innovationplatform/dcpo/agent/apps/bond.git\n"
    mock_run.returncode = 0

    with patch("subprocess.run", return_value=mock_run):
        host, project_path = get_gitlab_repo_info(Path("/test"))

    assert host == "gitlab.devops.telekom.de"
    assert project_path == "gsus/innovationplatform/dcpo/agent/apps/bond"


def test_get_gitlab_repo_info_ssh():
    """Test parsing SSH GitLab URL."""
    mock_run = MagicMock()
    mock_run.stdout = "git@gitlab.com:owner/repo.git\n"
    mock_run.returncode = 0

    with patch("subprocess.run", return_value=mock_run):
        host, project_path = get_gitlab_repo_info(Path("/test"))

    assert host == "gitlab.com"
    assert project_path == "owner/repo"


def test_get_gitlab_repo_info_ssh_custom_instance():
    """Test parsing custom GitLab instance SSH URL."""
    mock_run = MagicMock()
    mock_run.stdout = "git@gitlab.devops.telekom.de:org/subgroup/project.git\n"
    mock_run.returncode = 0

    with patch("subprocess.run", return_value=mock_run):
        host, project_path = get_gitlab_repo_info(Path("/test"))

    assert host == "gitlab.devops.telekom.de"
    assert project_path == "org/subgroup/project"


def test_get_gitlab_repo_info_invalid_url():
    """Test error with non-GitLab URL."""
    mock_run = MagicMock()
    mock_run.stdout = "https://github.com/owner/repo.git\n"
    mock_run.returncode = 0

    with patch("subprocess.run", return_value=mock_run):
        with pytest.raises(GitLabError, match="Could not parse GitLab host/project"):
            get_gitlab_repo_info(Path("/test"))


def test_get_project_id():
    """Test URL encoding of project path."""
    project_id = get_project_id("gitlab.com", "owner/repo")
    assert project_id == "owner%2Frepo"

    project_id = get_project_id("gitlab.com", "gsus/innovationplatform/dcpo")
    assert project_id == "gsus%2Finnovationplatform%2Fdcpo"


def test_find_existing_pr_found():
    """Test finding an existing MR."""
    mock_response = MagicMock()
    mock_response.json.return_value = [{"iid": 42, "title": "Test MR"}]
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        mr_iid = find_existing_pr(
            "gitlab.com",
            "owner/repo",
            "source-branch",
            "target-branch",
            "test-token",
        )

    assert mr_iid == 42


def test_find_existing_pr_not_found():
    """Test when no existing MR is found."""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        mr_iid = find_existing_pr(
            "gitlab.com",
            "owner/repo",
            "source-branch",
            "target-branch",
            "test-token",
        )

    assert mr_iid is None


def test_find_existing_pr_api_error():
    """Test error handling when API request fails."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "API Error"
    )

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(GitLabError, match="Failed to check for existing MR"):
            find_existing_pr(
                "gitlab.com",
                "owner/repo",
                "source-branch",
                "target-branch",
                "test-token",
            )


def test_create_pull_request():
    """Test creating a new MR."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "iid": 42,
        "title": "Test MR",
        "web_url": "https://gitlab.com/owner/repo/-/merge_requests/42",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response) as mock_post:
        result = create_pull_request(
            "gitlab.com",
            "owner/repo",
            "Test MR",
            "Test description",
            "source-branch",
            "target-branch",
            "test-token",
        )

    assert result["iid"] == 42
    assert result["title"] == "Test MR"

    # Verify API call
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert "https://gitlab.com/api/v4/projects/owner%2Frepo/merge_requests" in args[0]
    assert kwargs["headers"]["PRIVATE-TOKEN"] == "test-token"


def test_create_pull_request_api_error():
    """Test error handling when MR creation fails."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "API Error"
    )
    mock_response.json.return_value = {"message": "Validation failed"}

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(GitLabError, match="Failed to create merge request"):
            create_pull_request(
                "gitlab.com",
                "owner/repo",
                "Test MR",
                "Test description",
                "source-branch",
                "target-branch",
                "test-token",
            )


def test_update_pull_request():
    """Test updating an existing MR."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "iid": 42,
        "title": "Updated MR",
        "web_url": "https://gitlab.com/owner/repo/-/merge_requests/42",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.put", return_value=mock_response) as mock_put:
        result = update_pull_request(
            "gitlab.com",
            "owner/repo",
            42,
            "Updated MR",
            "Updated description",
            "test-token",
        )

    assert result["iid"] == 42
    assert result["title"] == "Updated MR"

    # Verify API call
    mock_put.assert_called_once()
    args, kwargs = mock_put.call_args
    assert (
        "https://gitlab.com/api/v4/projects/owner%2Frepo/merge_requests/42" in args[0]
    )
    assert kwargs["headers"]["PRIVATE-TOKEN"] == "test-token"


def test_update_pull_request_api_error():
    """Test error handling when MR update fails."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "API Error"
    )

    with patch("requests.put", return_value=mock_response):
        with pytest.raises(GitLabError, match="Failed to update merge request"):
            update_pull_request(
                "gitlab.com",
                "owner/repo",
                42,
                "Updated MR",
                "Updated description",
                "test-token",
            )


def test_create_gitlab_release():
    """Test creating a GitLab release."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "tag_name": "v1.0.0",
        "name": "v1.0.0",
        "_links": {"self": "https://gitlab.com/owner/repo/-/releases/v1.0.0"},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response) as mock_post:
        result = create_gitlab_release(
            "gitlab.com",
            "owner/repo",
            "v1.0.0",
            "v1.0.0",
            "Release notes",
            "test-token",
            dry_run=False,
            verbose=False,
        )

    assert result is not None
    assert result["tag_name"] == "v1.0.0"

    # Verify API call
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert "https://gitlab.com/api/v4/projects/owner%2Frepo/releases" in args[0]
    assert kwargs["headers"]["PRIVATE-TOKEN"] == "test-token"


def test_create_gitlab_release_dry_run():
    """Test dry-run mode for release creation."""
    result = create_gitlab_release(
        "gitlab.com",
        "owner/repo",
        "v1.0.0",
        "v1.0.0",
        "Release notes",
        "test-token",
        dry_run=True,
        verbose=False,
    )

    assert result is None


def test_create_gitlab_release_api_error():
    """Test error handling when release creation fails."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "API Error"
    )

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(GitLabError, match="Failed to create GitLab release"):
            create_gitlab_release(
                "gitlab.com",
                "owner/repo",
                "v1.0.0",
                "v1.0.0",
                "Release notes",
                "test-token",
                dry_run=False,
                verbose=False,
            )


def test_create_or_update_pr_creates_new():
    """Test create_or_update_pr creates new MR when none exists."""
    mock_find = MagicMock(return_value=None)
    mock_create = MagicMock(return_value={"iid": 42, "title": "New MR"})

    with (
        patch("contiamo_release_please.gitlab.find_existing_pr", mock_find),
        patch("contiamo_release_please.gitlab.create_pull_request", mock_create),
    ):
        result = create_or_update_pr(
            "gitlab.com",
            "owner/repo",
            "Test MR",
            "Test description",
            "source-branch",
            "target-branch",
            "test-token",
            dry_run=False,
            verbose=False,
        )

    assert result is not None
    assert result["iid"] == 42
    mock_find.assert_called_once()
    mock_create.assert_called_once()


def test_create_or_update_pr_updates_existing():
    """Test create_or_update_pr updates existing MR."""
    mock_find = MagicMock(return_value=42)
    mock_update = MagicMock(return_value={"iid": 42, "title": "Updated MR"})

    with (
        patch("contiamo_release_please.gitlab.find_existing_pr", mock_find),
        patch("contiamo_release_please.gitlab.update_pull_request", mock_update),
    ):
        result = create_or_update_pr(
            "gitlab.com",
            "owner/repo",
            "Updated MR",
            "Updated description",
            "source-branch",
            "target-branch",
            "test-token",
            dry_run=False,
            verbose=False,
        )

    assert result is not None
    assert result["iid"] == 42
    mock_find.assert_called_once()
    mock_update.assert_called_once()


def test_create_or_update_pr_dry_run():
    """Test create_or_update_pr in dry-run mode."""
    result = create_or_update_pr(
        "gitlab.com",
        "owner/repo",
        "Test MR",
        "Test description",
        "source-branch",
        "target-branch",
        "test-token",
        dry_run=True,
        verbose=False,
    )

    assert result is None
