"""Tests for release branch creation and management."""

import tempfile
from contextlib import ExitStack
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
    tag_release_workflow,
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
         patch("contiamo_release_please.release.configure_git_identity"), \
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
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
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
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_latest_tag") as mock_tag, \
         patch("contiamo_release_please.release.get_commits_since_tag") as mock_commits:

        mock_git_root.return_value = Path("/tmp/repo")
        mock_config_obj = Mock()
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config.return_value = mock_config_obj
        mock_tag.return_value = "v1.0.0"
        mock_commits.return_value = []

        with pytest.raises(ReleaseError, match="No commits since last release"):
            create_release_branch_workflow()


def test_create_release_branch_workflow_no_releasable_commits():
    """Test workflow fails when no releasable commits found."""
    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_latest_tag") as mock_tag, \
         patch("contiamo_release_please.release.get_commits_since_tag") as mock_commits, \
         patch("contiamo_release_please.release.is_release_commit") as mock_is_release, \
         patch("contiamo_release_please.release.analyse_commits") as mock_analyse:

        mock_git_root.return_value = Path("/tmp/repo")
        mock_config_obj = Mock()
        mock_config_obj.get_source_branch.return_value = "main"
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config.return_value = mock_config_obj

        mock_tag.return_value = "v1.0.0"
        mock_commits.return_value = ["docs: update docs"]
        mock_is_release.return_value = False  # Not a release commit
        mock_analyse.return_value = None  # No releasable commits

        with pytest.raises(ReleaseError, match="No releasable commits found"):
            create_release_branch_workflow()


def test_create_release_branch_workflow_only_release_commits():
    """Test workflow fails when only release infrastructure commits found."""
    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_latest_tag") as mock_tag, \
         patch("contiamo_release_please.release.get_commits_since_tag") as mock_commits, \
         patch("contiamo_release_please.release.is_release_commit") as mock_is_release:

        mock_git_root.return_value = Path("/tmp/repo")
        mock_config_obj = Mock()
        mock_config_obj.get_source_branch.return_value = "main"
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config.return_value = mock_config_obj

        mock_tag.return_value = "v1.0.0"
        mock_commits.return_value = ["chore(main): update files for release 1.0.0"]
        mock_is_release.return_value = True  # This is a release commit

        with pytest.raises(
            ReleaseError,
            match="Only release infrastructure commits found since last tag"
        ):
            create_release_branch_workflow()


def test_create_release_branch_workflow_switches_back_to_source():
    """Test workflow switches back to source branch after completion."""
    patches = [
        patch("contiamo_release_please.release.get_git_root"),
        patch("contiamo_release_please.release.load_config"),
        patch("contiamo_release_please.release.configure_git_identity"),
        patch("contiamo_release_please.release.get_latest_tag"),
        patch("contiamo_release_please.release.parse_version"),
        patch("contiamo_release_please.release.get_commits_since_tag"),
        patch("contiamo_release_please.release.is_release_commit"),
        patch("contiamo_release_please.release.analyse_commits"),
        patch("contiamo_release_please.release.get_commit_type_summary"),
        patch("contiamo_release_please.release.parse_commit_message"),
        patch("contiamo_release_please.release.get_next_version"),
        patch("contiamo_release_please.git.detect_git_host"),
        patch("contiamo_release_please.github.get_github_token"),
        patch("contiamo_release_please.release.create_or_reset_release_branch"),
        patch("contiamo_release_please.release.prepend_to_changelog"),
        patch("contiamo_release_please.release.write_version_file"),
        patch("contiamo_release_please.release.bump_files"),
        patch("contiamo_release_please.release.stage_and_commit_release_changes"),
        patch("contiamo_release_please.release.push_release_branch"),
        patch("contiamo_release_please.github.get_repo_info"),
        patch("contiamo_release_please.github.create_or_update_pr"),
        patch("contiamo_release_please.release.checkout_branch"),
    ]

    with ExitStack() as stack:
        mocks = [stack.enter_context(p) for p in patches]
        (mock_git_root, mock_config, _, mock_tag, mock_parse, mock_commits,
         mock_is_release, mock_analyse, mock_summary, mock_parse_msg,
         mock_next_version, mock_detect_host, mock_get_token, _,
         _, _, mock_bump, _, _, mock_repo_info, mock_pr, mock_checkout) = mocks

        mock_git_root.return_value = Path("/tmp/repo")
        mock_config_obj = Mock()
        mock_config_obj.get_source_branch.return_value = "main"
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_version_prefix.return_value = "v"
        mock_config_obj.get_changelog_path.return_value = "CHANGELOG.md"
        mock_config_obj.get_extra_files.return_value = []
        mock_config_obj.get_changelog_sections.return_value = []
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config_obj._config = {}
        mock_config.return_value = mock_config_obj

        mock_tag.return_value = "v1.0.0"
        mock_parse.return_value = "1.0.0"
        mock_commits.return_value = ["feat: add feature"]
        mock_is_release.return_value = False
        mock_analyse.return_value = "minor"
        mock_summary.return_value = {"feat": 1}
        mock_parse_msg.return_value = {"type": "feat", "scope": "", "breaking": False, "description": "add feature"}
        mock_next_version.return_value = "1.1.0"
        mock_detect_host.return_value = "github"
        mock_get_token.return_value = "fake_token"
        mock_repo_info.return_value = ("owner", "repo")
        mock_pr.return_value = {"html_url": "https://github.com/owner/repo/pull/1", "number": 1}
        mock_bump.return_value = {"updated": [], "errors": []}

        result = create_release_branch_workflow()

        # Verify checkout_branch was called with source branch
        mock_checkout.assert_called_once_with("main", Path("/tmp/repo"))
        assert result["success"] is True
        assert result["source_branch"] == "main"


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


def test_tag_release_workflow_success(tmp_path):
    """Test successful tag creation workflow."""
    # Create version.txt
    version_file = tmp_path / "version.txt"
    version_file.write_text("v1.2.3\n")

    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_current_branch") as mock_branch, \
         patch("contiamo_release_please.release.tag_exists") as mock_tag_exists, \
         patch("contiamo_release_please.release.create_tag") as mock_create_tag, \
         patch("contiamo_release_please.release.push_tag") as mock_push_tag:

        mock_git_root.return_value = tmp_path
        mock_config_obj = Mock()
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config.return_value = mock_config_obj
        mock_branch.return_value = "main"
        mock_tag_exists.return_value = False

        result = tag_release_workflow()

        assert result["success"] is True
        assert result["version"] == "v1.2.3"
        assert result["current_branch"] == "main"
        mock_create_tag.assert_called_once_with("v1.2.3", "Release v1.2.3", tmp_path)
        mock_push_tag.assert_called_once_with("v1.2.3", tmp_path)


def test_tag_release_workflow_on_release_branch(tmp_path):
    """Test that tag creation fails when on release branch."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("v1.2.3\n")

    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_current_branch") as mock_branch:

        mock_git_root.return_value = tmp_path
        mock_config_obj = Mock()
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config.return_value = mock_config_obj
        mock_branch.return_value = "release-please--branches--main"

        with pytest.raises(ReleaseError, match="Cannot create tag from release branch"):
            tag_release_workflow()


def test_tag_release_workflow_no_version_file(tmp_path):
    """Test that tag creation fails when version.txt doesn't exist."""
    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_current_branch") as mock_branch:

        mock_git_root.return_value = tmp_path
        mock_config_obj = Mock()
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config.return_value = mock_config_obj
        mock_branch.return_value = "main"

        with pytest.raises(ReleaseError, match="version.txt not found"):
            tag_release_workflow()


def test_tag_release_workflow_empty_version_file(tmp_path):
    """Test that tag creation fails when version.txt is empty."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("")

    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_current_branch") as mock_branch:

        mock_git_root.return_value = tmp_path
        mock_config_obj = Mock()
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config.return_value = mock_config_obj
        mock_branch.return_value = "main"

        with pytest.raises(ReleaseError, match="version.txt is empty"):
            tag_release_workflow()


def test_tag_release_workflow_tag_already_exists(tmp_path):
    """Test that tag creation fails when tag already exists."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("v1.2.3\n")

    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_current_branch") as mock_branch, \
         patch("contiamo_release_please.release.tag_exists") as mock_tag_exists:

        mock_git_root.return_value = tmp_path
        mock_config_obj = Mock()
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config.return_value = mock_config_obj
        mock_branch.return_value = "main"
        mock_tag_exists.return_value = True

        with pytest.raises(ReleaseError, match="Tag 'v1.2.3' already exists"):
            tag_release_workflow()


def test_tag_release_workflow_dry_run(tmp_path):
    """Test dry-run mode doesn't create or push tag."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("v1.2.3\n")

    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_current_branch") as mock_branch, \
         patch("contiamo_release_please.release.tag_exists") as mock_tag_exists, \
         patch("contiamo_release_please.release.create_tag") as mock_create_tag, \
         patch("contiamo_release_please.release.push_tag") as mock_push_tag:

        mock_git_root.return_value = tmp_path
        mock_config_obj = Mock()
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config.return_value = mock_config_obj
        mock_branch.return_value = "main"
        mock_tag_exists.return_value = False

        result = tag_release_workflow(dry_run=True)

        assert result["dry_run"] is True
        assert result["version"] == "v1.2.3"
        mock_create_tag.assert_not_called()
        mock_push_tag.assert_not_called()


def test_tag_release_workflow_creates_github_release(tmp_path):
    """Test that GitHub release is created for GitHub repositories."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("v1.2.3\n")

    # Create a mock changelog
    changelog_file = tmp_path / "CHANGELOG.md"
    changelog_content = """# Changelog

## [1.2.3] (2025-01-10)

### Features

* Add new feature
* **auth**: OAuth support

### Bug Fixes

* Fix critical bug
"""
    changelog_file.write_text(changelog_content)

    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_current_branch") as mock_branch, \
         patch("contiamo_release_please.release.tag_exists") as mock_tag_exists, \
         patch("contiamo_release_please.release.create_tag"), \
         patch("contiamo_release_please.release.push_tag"), \
         patch("contiamo_release_please.release.detect_git_host") as mock_detect_host, \
         patch("contiamo_release_please.github.get_github_token") as mock_token, \
         patch("contiamo_release_please.github.get_repo_info") as mock_repo_info, \
         patch("contiamo_release_please.github.create_github_release") as mock_create_release:

        mock_git_root.return_value = tmp_path
        mock_config_obj = Mock()
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config_obj.get_changelog_path.return_value = "CHANGELOG.md"
        mock_config_obj.get_version_prefix.return_value = "v"  # Default prefix
        mock_config_obj._config = {}
        mock_config.return_value = mock_config_obj
        mock_branch.return_value = "main"
        mock_tag_exists.return_value = False
        mock_detect_host.return_value = "github"
        mock_token.return_value = "ghp_test_token"
        mock_repo_info.return_value = ("owner", "repo")
        mock_create_release.return_value = {"html_url": "https://github.com/owner/repo/releases/tag/v1.2.3"}

        result = tag_release_workflow()

        assert result["success"] is True
        assert result["version"] == "v1.2.3"
        assert result["release_url"] == "https://github.com/owner/repo/releases/tag/v1.2.3"

        # Verify GitHub release was created
        mock_create_release.assert_called_once()
        call_args = mock_create_release.call_args
        assert call_args.kwargs["owner"] == "owner"
        assert call_args.kwargs["repo"] == "repo"
        assert call_args.kwargs["tag_name"] == "v1.2.3"
        assert call_args.kwargs["release_name"] == "v1.2.3"
        assert "Add new feature" in call_args.kwargs["body"]
        assert "Fix critical bug" in call_args.kwargs["body"]


def test_tag_release_workflow_non_github_skips_release(tmp_path):
    """Test that GitHub release creation is skipped for non-GitHub repos."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("v1.2.3\n")

    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_current_branch") as mock_branch, \
         patch("contiamo_release_please.release.tag_exists") as mock_tag_exists, \
         patch("contiamo_release_please.release.create_tag"), \
         patch("contiamo_release_please.release.push_tag"), \
         patch("contiamo_release_please.release.detect_git_host") as mock_detect_host:

        mock_git_root.return_value = tmp_path
        mock_config_obj = Mock()
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config.return_value = mock_config_obj
        mock_branch.return_value = "main"
        mock_tag_exists.return_value = False
        mock_detect_host.return_value = "azure"  # Not GitHub

        result = tag_release_workflow()

        assert result["success"] is True
        assert result["version"] == "v1.2.3"
        assert result["release_url"] is None  # No release created


def test_tag_release_workflow_github_release_failure_doesnt_fail_workflow(tmp_path):
    """Test that workflow continues even if GitHub release creation fails."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("v1.2.3\n")

    changelog_file = tmp_path / "CHANGELOG.md"
    changelog_file.write_text("# Changelog\n\n## [1.2.3] (2025-01-10)\n\n* Test\n")

    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_current_branch") as mock_branch, \
         patch("contiamo_release_please.release.tag_exists") as mock_tag_exists, \
         patch("contiamo_release_please.release.create_tag"), \
         patch("contiamo_release_please.release.push_tag"), \
         patch("contiamo_release_please.release.detect_git_host") as mock_detect_host, \
         patch("contiamo_release_please.github.get_github_token") as mock_token:

        mock_git_root.return_value = tmp_path
        mock_config_obj = Mock()
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config_obj.get_changelog_path.return_value = "CHANGELOG.md"
        mock_config_obj.config = {}
        mock_config.return_value = mock_config_obj
        mock_branch.return_value = "main"
        mock_tag_exists.return_value = False
        mock_detect_host.return_value = "github"
        mock_token.side_effect = Exception("GitHub API error")

        # Should not raise exception
        result = tag_release_workflow()

        assert result["success"] is True
        assert result["version"] == "v1.2.3"
        assert result["release_url"] is None  # Release creation failed


def test_tag_release_workflow_github_release_dry_run(tmp_path):
    """Test that dry-run mode shows GitHub release creation without creating it."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("v1.2.3\n")

    changelog_file = tmp_path / "CHANGELOG.md"
    changelog_file.write_text("# Changelog\n\n## [1.2.3] (2025-01-10)\n\n* Test\n")

    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_current_branch") as mock_branch, \
         patch("contiamo_release_please.release.tag_exists") as mock_tag_exists, \
         patch("contiamo_release_please.release.create_tag") as mock_create_tag, \
         patch("contiamo_release_please.release.push_tag") as mock_push_tag, \
         patch("contiamo_release_please.release.detect_git_host") as mock_detect_host:

        mock_git_root.return_value = tmp_path
        mock_config_obj = Mock()
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config_obj.get_changelog_path.return_value = "CHANGELOG.md"
        mock_config.return_value = mock_config_obj
        mock_branch.return_value = "main"
        mock_tag_exists.return_value = False
        mock_detect_host.return_value = "github"

        result = tag_release_workflow(dry_run=True, verbose=True)

        assert result["dry_run"] is True
        assert result["version"] == "v1.2.3"
        mock_create_tag.assert_not_called()
        mock_push_tag.assert_not_called()


def test_tag_release_workflow_github_release_custom_prefix(tmp_path):
    """Test GitHub release creation with custom prefix."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("release-2.5.0\n")

    # Create a mock changelog with version WITHOUT prefix
    changelog_file = tmp_path / "CHANGELOG.md"
    changelog_content = """# Changelog

## [2.5.0] (2025-01-15)

### Features

* Custom prefix support
"""
    changelog_file.write_text(changelog_content)

    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_current_branch") as mock_branch, \
         patch("contiamo_release_please.release.tag_exists") as mock_tag_exists, \
         patch("contiamo_release_please.release.create_tag"), \
         patch("contiamo_release_please.release.push_tag"), \
         patch("contiamo_release_please.release.detect_git_host") as mock_detect_host, \
         patch("contiamo_release_please.github.get_github_token") as mock_token, \
         patch("contiamo_release_please.github.get_repo_info") as mock_repo_info, \
         patch("contiamo_release_please.github.create_github_release") as mock_create_release:

        mock_git_root.return_value = tmp_path
        mock_config_obj = Mock()
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config_obj.get_changelog_path.return_value = "CHANGELOG.md"
        mock_config_obj.get_version_prefix.return_value = "release-"  # Custom prefix
        mock_config_obj._config = {}
        mock_config.return_value = mock_config_obj
        mock_branch.return_value = "main"
        mock_tag_exists.return_value = False
        mock_detect_host.return_value = "github"
        mock_token.return_value = "ghp_test_token"
        mock_repo_info.return_value = ("owner", "repo")
        mock_create_release.return_value = {"html_url": "https://github.com/owner/repo/releases/tag/release-2.5.0"}

        result = tag_release_workflow()

        assert result["success"] is True
        assert result["version"] == "release-2.5.0"
        assert result["release_url"] == "https://github.com/owner/repo/releases/tag/release-2.5.0"

        # Verify GitHub release was created with correct body
        mock_create_release.assert_called_once()
        call_args = mock_create_release.call_args
        assert call_args.kwargs["tag_name"] == "release-2.5.0"
        assert call_args.kwargs["release_name"] == "release-2.5.0"
        # Verify the changelog was correctly extracted (version without prefix)
        assert "Custom prefix support" in call_args.kwargs["body"]


def test_tag_release_workflow_github_release_empty_prefix(tmp_path):
    """Test GitHub release creation with empty prefix."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("3.0.0\n")  # No prefix

    # Create a mock changelog
    changelog_file = tmp_path / "CHANGELOG.md"
    changelog_content = """# Changelog

## [3.0.0] (2025-01-20)

### Features

* No prefix version
"""
    changelog_file.write_text(changelog_content)

    with patch("contiamo_release_please.release.get_git_root") as mock_git_root, \
         patch("contiamo_release_please.release.load_config") as mock_config, \
         patch("contiamo_release_please.release.configure_git_identity"), \
         patch("contiamo_release_please.release.get_current_branch") as mock_branch, \
         patch("contiamo_release_please.release.tag_exists") as mock_tag_exists, \
         patch("contiamo_release_please.release.create_tag"), \
         patch("contiamo_release_please.release.push_tag"), \
         patch("contiamo_release_please.release.detect_git_host") as mock_detect_host, \
         patch("contiamo_release_please.github.get_github_token") as mock_token, \
         patch("contiamo_release_please.github.get_repo_info") as mock_repo_info, \
         patch("contiamo_release_please.github.create_github_release") as mock_create_release:

        mock_git_root.return_value = tmp_path
        mock_config_obj = Mock()
        mock_config_obj.get_release_branch_name.return_value = "release-please--branches--main"
        mock_config_obj.get_git_user_name.return_value = "Test User"
        mock_config_obj.get_git_user_email.return_value = "test@example.com"
        mock_config_obj.get_changelog_path.return_value = "CHANGELOG.md"
        mock_config_obj.get_version_prefix.return_value = ""  # Empty prefix
        mock_config_obj._config = {}
        mock_config.return_value = mock_config_obj
        mock_branch.return_value = "main"
        mock_tag_exists.return_value = False
        mock_detect_host.return_value = "github"
        mock_token.return_value = "ghp_test_token"
        mock_repo_info.return_value = ("owner", "repo")
        mock_create_release.return_value = {"html_url": "https://github.com/owner/repo/releases/tag/3.0.0"}

        result = tag_release_workflow()

        assert result["success"] is True
        assert result["version"] == "3.0.0"
        assert result["release_url"] == "https://github.com/owner/repo/releases/tag/3.0.0"

        # Verify GitHub release was created with correct body
        mock_create_release.assert_called_once()
        call_args = mock_create_release.call_args
        assert call_args.kwargs["tag_name"] == "3.0.0"
        assert call_args.kwargs["release_name"] == "3.0.0"
        # Verify the changelog was correctly extracted
        assert "No prefix version" in call_args.kwargs["body"]
