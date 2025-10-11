"""Tests for release branch creation and management."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from contiamo_release_please.release import (
    ReleaseError,
    branch_exists,
    create_or_reset_release_branch,
    create_release_branch_workflow,
    push_release_branch,
    stage_and_commit_release_changes,
)


def test_branch_exists_local(tmp_path):
    """Test checking if branch exists locally."""
    with patch("subprocess.run") as mock_run:
        # Simulate local branch exists
        mock_run.return_value = Mock(returncode=0)

        result = branch_exists("test-branch", tmp_path)

        assert result is True
        mock_run.assert_called_once()


def test_branch_exists_remote(tmp_path):
    """Test checking if branch exists on remote."""
    with patch("subprocess.run") as mock_run:
        # First call (local) fails, second call (remote) succeeds
        mock_run.side_effect = [
            Mock(returncode=1),  # Local doesn't exist
            Mock(returncode=0),  # Remote exists
        ]

        result = branch_exists("test-branch", tmp_path)

        assert result is True
        assert mock_run.call_count == 2


def test_branch_not_exists(tmp_path):
    """Test checking if branch doesn't exist."""
    with patch("subprocess.run") as mock_run:
        # Both local and remote fail
        mock_run.return_value = Mock(returncode=1)

        result = branch_exists("test-branch", tmp_path)

        assert result is False


def test_create_or_reset_release_branch(tmp_path):
    """Test creating or resetting release branch."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0)

        create_or_reset_release_branch("release-branch", "main", tmp_path)

        # Should call git fetch and git checkout -B
        assert mock_run.call_count == 2
        calls = mock_run.call_args_list

        # First call: git fetch
        assert calls[0][0][0] == ["git", "fetch", "origin"]

        # Second call: git checkout -B
        assert calls[1][0][0] == ["git", "checkout", "-B", "release-branch", "origin/main"]


def test_create_or_reset_release_branch_dry_run(tmp_path):
    """Test dry-run mode doesn't execute git commands."""
    with patch("subprocess.run") as mock_run:
        create_or_reset_release_branch("release-branch", "main", tmp_path, dry_run=True)

        # Should not call any git commands
        mock_run.assert_not_called()


def test_create_or_reset_release_branch_failure(tmp_path):
    """Test error handling when git operations fail."""
    import subprocess

    with patch("subprocess.run") as mock_run:
        # Make the second call raise CalledProcessError
        mock_run.side_effect = [
            Mock(returncode=0),  # fetch succeeds
            subprocess.CalledProcessError(1, "git checkout", stderr=b"error: branch not found"),
        ]

        # Should raise ReleaseError
        with pytest.raises(ReleaseError, match="Failed to create/reset release branch"):
            create_or_reset_release_branch("release-branch", "main", tmp_path)


def test_stage_and_commit_release_changes(tmp_path):
    """Test staging and committing release changes."""
    with patch("subprocess.run") as mock_run:
        # Simulate changes exist (git diff returns non-zero)
        mock_run.side_effect = [
            Mock(returncode=0),  # git add
            Mock(returncode=1),  # git diff (has changes)
            Mock(returncode=0),  # git commit
        ]

        stage_and_commit_release_changes("1.2.3", "main", tmp_path)

        assert mock_run.call_count == 3
        calls = mock_run.call_args_list

        # Check git add
        assert calls[0][0][0] == ["git", "add", "-A"]

        # Check git diff
        assert calls[1][0][0] == ["git", "diff", "--cached", "--quiet"]

        # Check git commit message
        assert calls[2][0][0][0:3] == ["git", "commit", "-m"]
        assert "chore(main): update files for release 1.2.3" in calls[2][0][0][3]


def test_stage_and_commit_no_changes(tmp_path):
    """Test that no commit is made when there are no changes."""
    with patch("subprocess.run") as mock_run:
        # Simulate no changes (git diff returns 0)
        mock_run.side_effect = [
            Mock(returncode=0),  # git add
            Mock(returncode=0),  # git diff (no changes)
        ]

        stage_and_commit_release_changes("1.2.3", "main", tmp_path)

        # Should only call git add and git diff, not commit
        assert mock_run.call_count == 2


def test_stage_and_commit_dry_run(tmp_path):
    """Test dry-run mode doesn't commit changes."""
    with patch("subprocess.run") as mock_run:
        stage_and_commit_release_changes("1.2.3", "main", tmp_path, dry_run=True)

        mock_run.assert_not_called()


def test_push_release_branch(tmp_path):
    """Test pushing release branch."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0)

        push_release_branch("release-branch", tmp_path)

        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["git", "push", "-f", "origin", "release-branch"]


def test_push_release_branch_dry_run(tmp_path):
    """Test dry-run mode doesn't push."""
    with patch("subprocess.run") as mock_run:
        push_release_branch("release-branch", tmp_path, dry_run=True)

        mock_run.assert_not_called()


def test_push_release_branch_failure(tmp_path):
    """Test error handling when push fails."""
    import subprocess

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git push", stderr=b"Push failed"
        )

        with pytest.raises(ReleaseError, match="Failed to push release branch"):
            push_release_branch("release-branch", tmp_path)


def test_create_release_branch_workflow_dry_run():
    """Test dry-run mode of full workflow."""
    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.get_latest_tag") as mock_tag, \
         patch("contiamo_release_please.release.get_commits_since_tag") as mock_commits, \
         patch("contiamo_release_please.release.analyse_commits") as mock_analyse, \
         patch("contiamo_release_please.release.parse_version") as mock_parse, \
         patch("contiamo_release_please.git.detect_git_host") as mock_detect_host, \
         patch("contiamo_release_please.github.get_github_token") as mock_get_token:

        # Setup mocks
        mock_git_root.return_value = Path("/tmp/repo")
        mock_config_obj = Mock()
        mock_config_obj.get_source_branch.return_value = "main"
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_version_prefix.return_value = "v"
        mock_config_obj.get_changelog_path.return_value = "CHANGELOG.md"
        mock_config_obj.get_changelog_sections.return_value = []
        mock_config_obj.get_extra_files.return_value = []
        mock_config_obj._config = {}
        mock_config.return_value = mock_config_obj

        mock_tag.return_value = "v1.0.0"
        mock_parse.return_value = "1.0.0"  # Return string, not Version object
        mock_commits.return_value = ["feat: add feature"]
        mock_analyse.return_value = "minor"  # analyse_commits returns just the release type string

        # Mock git host detection and credentials
        mock_detect_host.return_value = "github"
        mock_get_token.return_value = "fake_token"

        # Run dry-run
        result = create_release_branch_workflow(dry_run=True, verbose=False)

        assert result["dry_run"] is True
        assert result["version"] == "1.1.0"
        assert result["version_prefixed"] == "v1.1.0"


def test_create_release_branch_workflow_no_commits():
    """Test workflow fails when no commits found."""
    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.get_latest_tag") as mock_tag, \
         patch("contiamo_release_please.release.get_commits_since_tag") as mock_commits:

        mock_git_root.return_value = Path("/tmp/repo")
        mock_config.return_value = Mock()
        mock_tag.return_value = "v1.0.0"
        mock_commits.return_value = []

        with pytest.raises(ReleaseError, match="No commits since last release"):
            create_release_branch_workflow()


def test_create_release_branch_workflow_no_releasable_commits():
    """Test workflow fails when no releasable commits found."""
    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.get_latest_tag") as mock_tag, \
         patch("contiamo_release_please.release.get_commits_since_tag") as mock_commits, \
         patch("contiamo_release_please.release.analyse_commits") as mock_analyse:

        mock_git_root.return_value = Path("/tmp/repo")
        mock_config_obj = Mock()
        mock_config_obj.get_source_branch.return_value = "main"
        mock_config.return_value = mock_config_obj

        mock_tag.return_value = "v1.0.0"
        mock_commits.return_value = ["docs: update docs"]
        mock_analyse.return_value = None  # No releasable commits

        with pytest.raises(ReleaseError, match="No releasable commits found"):
            create_release_branch_workflow()


def test_config_get_source_branch_default():
    """Test default source branch is 'main'."""
    from contiamo_release_please.config import ReleaseConfig

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("release-rules:\n  patch:\n    - fix\n")
        f.flush()
        config = ReleaseConfig(f.name)

        assert config.get_source_branch() == "main"


def test_config_get_source_branch_custom():
    """Test custom source branch from config."""
    from contiamo_release_please.config import ReleaseConfig

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("source-branch: develop\nrelease-rules:\n  patch:\n    - fix\n")
        f.flush()
        config = ReleaseConfig(f.name)

        assert config.get_source_branch() == "develop"


def test_config_get_release_branch_name_default():
    """Test default release branch name generation."""
    from contiamo_release_please.config import ReleaseConfig

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("release-rules:\n  patch:\n    - fix\n")
        f.flush()
        config = ReleaseConfig(f.name)

        assert config.get_release_branch_name() == "release-please--branches--main"


def test_config_get_release_branch_name_custom():
    """Test custom release branch name from config."""
    from contiamo_release_please.config import ReleaseConfig

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("release-branch-name: my-release-branch\nrelease-rules:\n  patch:\n    - fix\n")
        f.flush()
        config = ReleaseConfig(f.name)

        assert config.get_release_branch_name() == "my-release-branch"


def test_config_get_release_branch_name_with_custom_source():
    """Test release branch name generation with custom source branch."""
    from contiamo_release_please.config import ReleaseConfig

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("source-branch: develop\nrelease-rules:\n  patch:\n    - fix\n")
        f.flush()
        config = ReleaseConfig(f.name)

        assert config.get_release_branch_name() == "release-please--branches--develop"
