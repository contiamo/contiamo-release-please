"""Tests for GitHub API integration."""

from unittest.mock import MagicMock, patch

import requests

from contiamo_release_please.github import get_pr_for_commit


def test_get_pr_for_commit_found():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"number": 42, "html_url": "https://github.com/owner/repo/pull/42"}
    ]

    with patch("requests.get", return_value=mock_response):
        result = get_pr_for_commit("owner", "repo", "abc123", "test-token")

    assert result == (42, "https://github.com/owner/repo/pull/42")


def test_get_pr_for_commit_uses_first_pr():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"number": 10, "html_url": "https://github.com/owner/repo/pull/10"},
        {"number": 11, "html_url": "https://github.com/owner/repo/pull/11"},
    ]

    with patch("requests.get", return_value=mock_response):
        result = get_pr_for_commit("owner", "repo", "abc123", "test-token")

    assert result == (10, "https://github.com/owner/repo/pull/10")


def test_get_pr_for_commit_not_found():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch("requests.get", return_value=mock_response):
        result = get_pr_for_commit("owner", "repo", "abc123", "test-token")

    assert result is None


def test_get_pr_for_commit_non_200():
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("requests.get", return_value=mock_response):
        result = get_pr_for_commit("owner", "repo", "abc123", "test-token")

    assert result is None


def test_get_pr_for_commit_network_error():
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError()):
        result = get_pr_for_commit("owner", "repo", "abc123", "test-token")

    assert result is None


def test_get_pr_for_commit_sends_correct_headers():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch("requests.get", return_value=mock_response) as mock_get:
        get_pr_for_commit("owner", "repo", "abc123", "my-token")

    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["Authorization"] == "token my-token"
    assert kwargs["headers"]["Accept"] == "application/vnd.github+json"
    assert "api.github.com" in mock_get.call_args[0][0]
