"""Tests for Bitbucket Cloud API integration."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from contiamo_release_please.bitbucket import (
    BitbucketError,
    create_or_update_pr,
    create_pull_request,
    extract_pr_id,
    find_existing_pr,
    get_bitbucket_pr_url,
    get_bitbucket_repo_info,
    get_bitbucket_token,
    get_pull_request_title,
    resolve_merge_commit_titles,
    update_pull_request,
)

API = "https://api.bitbucket.org/2.0/repositories/appdl/kamin/pullrequests"


def test_get_bitbucket_token_from_env():
    with patch.dict(os.environ, {"BITBUCKET_TOKEN": "env-token"}):
        assert get_bitbucket_token({}) == "env-token"


def test_get_bitbucket_token_from_config():
    with patch.dict(os.environ, {}, clear=True):
        assert get_bitbucket_token({"bitbucket": {"token": "cfg"}}) == "cfg"


def test_get_bitbucket_token_env_precedence():
    with patch.dict(os.environ, {"BITBUCKET_TOKEN": "env-token"}):
        assert get_bitbucket_token({"bitbucket": {"token": "cfg"}}) == "env-token"


def test_get_bitbucket_token_not_found():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(BitbucketError, match="Bitbucket token not found"):
            get_bitbucket_token({})


@pytest.mark.parametrize(
    "url",
    [
        "git@bitbucket.org:appdl/kamin.git",
        "git@bitbucket.org:appdl/kamin",
        "ssh://git@bitbucket.org/appdl/kamin.git",
        "https://bitbucket.org/appdl/kamin.git",
        "https://bitbucket.org/appdl/kamin",
        "https://greg@bitbucket.org/appdl/kamin.git",
        "https://x-token-auth:secret@bitbucket.org/appdl/kamin.git",
    ],
)
def test_get_bitbucket_repo_info(url):
    mock_run = MagicMock()
    mock_run.stdout = url + "\n"
    with patch("subprocess.run", return_value=mock_run):
        assert get_bitbucket_repo_info(Path("/repo")) == ("appdl", "kamin")


def test_get_bitbucket_repo_info_invalid_url():
    mock_run = MagicMock()
    mock_run.stdout = "https://github.com/owner/repo.git\n"
    with patch("subprocess.run", return_value=mock_run):
        with pytest.raises(BitbucketError, match="Could not parse Bitbucket"):
            get_bitbucket_repo_info(Path("/repo"))


def test_get_bitbucket_pr_url():
    assert (
        get_bitbucket_pr_url("appdl", "kamin", 12)
        == "https://bitbucket.org/appdl/kamin/pull-requests/12"
    )


def test_find_existing_pr_found():
    mock_response = MagicMock()
    mock_response.json.return_value = {"values": [{"id": 42, "title": "x"}]}

    with patch("requests.get", return_value=mock_response) as mock_get:
        pr_id = find_existing_pr(
            "appdl", "kamin", "release-please--branches--main", "main", "tok"
        )

    assert pr_id == 42
    kwargs = mock_get.call_args.kwargs
    assert mock_get.call_args.args[0] == API
    assert kwargs["headers"]["Authorization"] == "Bearer tok"
    assert kwargs["params"]["state"] == "OPEN"
    assert 'source.branch.name = "release-please--branches--main"' in kwargs["params"]["q"]
    assert 'destination.branch.name = "main"' in kwargs["params"]["q"]


def test_find_existing_pr_not_found():
    mock_response = MagicMock()
    mock_response.json.return_value = {"values": []}
    with patch("requests.get", return_value=mock_response):
        assert find_existing_pr("appdl", "kamin", "a", "b", "tok") is None


def test_find_existing_pr_api_error():
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("boom")):
        with pytest.raises(BitbucketError, match="Failed to check for existing PR"):
            find_existing_pr("appdl", "kamin", "a", "b", "tok")


def test_create_pull_request():
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 7}

    with patch("requests.post", return_value=mock_response) as mock_post:
        result = create_pull_request(
            "appdl", "kamin", "chore(main): release 1.0.0", "notes", "rel", "main", "tok"
        )

    assert result == {"id": 7}
    assert mock_post.call_args.args[0] == API
    payload = json.loads(mock_post.call_args.kwargs["data"])
    assert payload == {
        "title": "chore(main): release 1.0.0",
        "description": "notes",
        "source": {"branch": {"name": "rel"}},
        "destination": {"branch": {"name": "main"}},
        "close_source_branch": True,
    }


def test_create_pull_request_error_includes_bitbucket_message():
    response = MagicMock()
    response.json.return_value = {"error": {"message": "Access token expired."}}
    err = requests.exceptions.HTTPError("401")
    err.response = response

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = err

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(BitbucketError, match="Access token expired"):
            create_pull_request("appdl", "kamin", "t", "d", "a", "b", "tok")


def test_update_pull_request():
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 7}

    with patch("requests.put", return_value=mock_response) as mock_put:
        result = update_pull_request("appdl", "kamin", 7, "new title", "new body", "tok")

    assert result == {"id": 7}
    assert mock_put.call_args.args[0] == f"{API}/7"
    assert json.loads(mock_put.call_args.kwargs["data"]) == {
        "title": "new title",
        "description": "new body",
    }


def test_create_or_update_pr_updates_when_existing():
    with (
        patch("contiamo_release_please.bitbucket.find_existing_pr", return_value=5),
        patch("contiamo_release_please.bitbucket.update_pull_request") as mock_update,
        patch("contiamo_release_please.bitbucket.create_pull_request") as mock_create,
    ):
        create_or_update_pr("appdl", "kamin", "t", "b", "rel", "main", "tok")

    mock_update.assert_called_once_with("appdl", "kamin", 5, "t", "b", "tok")
    mock_create.assert_not_called()


def test_create_or_update_pr_creates_when_missing():
    with (
        patch("contiamo_release_please.bitbucket.find_existing_pr", return_value=None),
        patch("contiamo_release_please.bitbucket.update_pull_request") as mock_update,
        patch("contiamo_release_please.bitbucket.create_pull_request") as mock_create,
    ):
        create_or_update_pr("appdl", "kamin", "t", "b", "rel", "main", "tok")

    mock_create.assert_called_once_with("appdl", "kamin", "t", "b", "rel", "main", "tok")
    mock_update.assert_not_called()


def test_create_or_update_pr_dry_run():
    with patch("contiamo_release_please.bitbucket.find_existing_pr") as mock_find:
        assert (
            create_or_update_pr("appdl", "kamin", "t", "b", "rel", "main", "tok", dry_run=True)
            is None
        )
    mock_find.assert_not_called()


def test_get_pull_request_title():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"title": "  feat: from api  "}
    with patch("requests.get", return_value=mock_response) as mock_get:
        assert get_pull_request_title("appdl", "kamin", 12, "tok") == "feat: from api"
    assert mock_get.call_args.args[0] == f"{API}/12"


def test_get_pull_request_title_swallows_failures():
    not_found = MagicMock()
    not_found.status_code = 404
    with patch("requests.get", return_value=not_found):
        assert get_pull_request_title("appdl", "kamin", 12, "tok") is None

    with patch("requests.get", side_effect=requests.exceptions.Timeout()):
        assert get_pull_request_title("appdl", "kamin", 12, "tok") is None


def test_extract_pr_id():
    assert extract_pr_id("feat: x (pull request #12)") == 12
    assert extract_pr_id("Merged in feat/x (pull request #3)") == 3
    assert extract_pr_id("feat: x (#12)") is None
    assert extract_pr_id("feat: x") is None


def test_resolve_merge_commit_titles():
    def fake_title(ws, slug, pr_id, token):
        return {12: "feat: api title", 3: None}[pr_id]

    commits = [
        ("a", "fix: body title (pull request #12)"),
        ("b", "Merged in feat/x (pull request #3)"),
        ("c", "docs: no pr at all"),
    ]
    with patch(
        "contiamo_release_please.bitbucket.get_pull_request_title", side_effect=fake_title
    ):
        resolved = resolve_merge_commit_titles(commits, "appdl", "kamin", "tok")

    assert resolved == [
        ("a", "feat: api title (pull request #12)"),
        ("b", "Merged in feat/x (pull request #3)"),
        ("c", "docs: no pr at all"),
    ]
