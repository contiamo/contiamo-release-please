"""Tests for git log parsing and subject normalisation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from contiamo_release_please.git import (
    _FIELD_SEP,
    _RECORD_SEP,
    detect_git_host,
    get_commits_with_sha_since_tag,
    get_latest_commit_message,
    normalise_commit_subject,
)


def _record(sha: str, subject: str, body: str = "") -> str:
    return f"{sha}{_FIELD_SEP}{subject}{_FIELD_SEP}{body}{_RECORD_SEP}"


class TestNormaliseCommitSubject:
    def test_regular_subject_unchanged(self):
        assert normalise_commit_subject("feat: add x", "some body") == "feat: add x"

    def test_bitbucket_merge_promotes_first_body_line(self):
        body = "\nfeat(api): add endpoint\n\n* commit one\n* commit two\n"
        result = normalise_commit_subject(
            "Merged in feat/api-endpoint (pull request #12)", body
        )
        assert result == "feat(api): add endpoint (pull request #12)"

    def test_bitbucket_merge_with_empty_body_keeps_subject(self):
        subject = "Merged in feat/api-endpoint (pull request #12)"
        assert normalise_commit_subject(subject, "") == subject
        assert normalise_commit_subject(subject, "\n\n") == subject

    def test_bitbucket_release_merge(self):
        result = normalise_commit_subject(
            "Merged in release-please--branches--main (pull request #7)",
            "chore(main): release 1.2.3\n\nApproved-by: Someone",
        )
        assert result == "chore(main): release 1.2.3 (pull request #7)"

    def test_branch_names_with_slashes_and_spaces_in_title(self):
        result = normalise_commit_subject(
            "Merged in feature/JIRA-123-some-thing (pull request #99)",
            "fix: handle spaces in title ok",
        )
        assert result == "fix: handle spaces in title ok (pull request #99)"


class TestGetCommitsWithShaSinceTag:
    def test_parses_records_and_normalises(self):
        output = (
            _record("a" * 40, "feat: plain commit", "")
            + "\n"
            + _record(
                "b" * 40,
                "Merged in fix/bug (pull request #3)",
                "fix: squash the bug\n\n* wip\n* more wip",
            )
            + "\n"
            + _record("c" * 40, "docs: body with separators kept intact", "line1\nline2")
        )
        with patch(
            "contiamo_release_please.git._run_git_command", return_value=output
        ) as mock_run:
            commits = get_commits_with_sha_since_tag("v1.0.0", Path("/repo"))

        assert commits == [
            ("a" * 40, "feat: plain commit"),
            ("b" * 40, "fix: squash the bug (pull request #3)"),
            ("c" * 40, "docs: body with separators kept intact"),
        ]
        args = mock_run.call_args.args[0]
        assert args[0] == "log"
        assert args[1] == "v1.0.0..HEAD"

    def test_no_output_returns_empty_list(self):
        with patch("contiamo_release_please.git._run_git_command", return_value=""):
            assert get_commits_with_sha_since_tag(None, Path("/repo")) == []


class TestGetLatestCommitMessage:
    def test_returns_normalised_subject(self):
        output = _record(
            "a" * 40,
            "Merged in release-please--branches--main (pull request #7)",
            "chore(main): release 1.2.3",
        )
        with patch("contiamo_release_please.git._run_git_command", return_value=output):
            assert (
                get_latest_commit_message(Path("/repo"))
                == "chore(main): release 1.2.3 (pull request #7)"
            )

    def test_plain_subject(self):
        output = _record("a" * 40, "feat: something", "")
        with patch("contiamo_release_please.git._run_git_command", return_value=output):
            assert get_latest_commit_message(Path("/repo")) == "feat: something"


class TestDetectGitHost:
    def _detect(self, url: str) -> str | None:
        mock_run = MagicMock()
        mock_run.stdout = url + "\n"
        with patch("subprocess.run", return_value=mock_run):
            return detect_git_host(Path("/repo"))

    def test_bitbucket_ssh(self):
        assert self._detect("git@bitbucket.org:appdl/kamin.git") == "bitbucket"

    def test_bitbucket_https(self):
        assert self._detect("https://greg@bitbucket.org/appdl/kamin.git") == "bitbucket"

    def test_other_hosts_unaffected(self):
        assert self._detect("git@github.com:contiamo/x.git") == "github"
        assert self._detect("https://gitlab.com/a/b.git") == "gitlab"
        assert self._detect("git@ssh.dev.azure.com:v3/o/p/r") == "azure"
        assert self._detect("https://example.com/a/b.git") is None
