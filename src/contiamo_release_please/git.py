"""Git operations for contiamo-release-please."""

import re
import subprocess
from pathlib import Path


class GitError(Exception):
    """Raised when git operations fail."""

    pass


def get_git_root() -> Path:
    """Get the root directory of the git repository.

    Returns:
        Path to git repository root

    Raises:
        GitError: If not in a git repository
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip()
        if "not a git repository" in error_msg.lower():
            raise GitError(
                "Not in a git repository. Please run this command from within a git repository.\n"
                "To initialise a git repository, run: git init"
            )
        raise GitError(f"Git command failed: {error_msg}")
    except FileNotFoundError:
        raise GitError("Git not found. Please ensure git is installed.")


def _run_git_command(args: list[str], cwd: Path | str | None = None) -> str:
    """Run a git command and return output.

    Args:
        args: Git command arguments (e.g., ['log', '--oneline'])
        cwd: Working directory for git command (default: git repository root)

    Returns:
        Command output as string

    Raises:
        GitError: If git command fails
    """
    # Default to git repository root
    if cwd is None:
        cwd = get_git_root()

    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitError(f"Git command failed: {e.stderr.strip()}")
    except FileNotFoundError:
        raise GitError("Git not found. Please ensure git is installed.")


def get_latest_tag(cwd: Path | None = None) -> str | None:
    """Get the latest git tag reachable from the current branch.

    Args:
        cwd: Repository directory (default: git root)

    Returns:
        Latest tag string (e.g., 'v1.2.3' or '1.2.3') or None if no tags exist

    Raises:
        GitError: If git operations fail
    """
    try:
        # Get the latest tag reachable from HEAD
        # --abbrev=0 shows only the tag name without commit info
        output = _run_git_command(["describe", "--tags", "--abbrev=0"], cwd=cwd)
        return output if output else None
    except GitError:
        # No tags exist yet or no tags reachable from HEAD
        return None


def get_commits_since_tag(tag: str | None = None, cwd: Path | None = None) -> list[str]:
    """Get commit messages since a given tag.

    Args:
        tag: Git tag to start from (None = get all commits)
        cwd: Repository directory (default: current directory)

    Returns:
        List of commit messages

    Raises:
        GitError: If git operations fail
    """
    # Build git log command
    if tag:
        # Get commits since tag
        range_spec = f"{tag}..HEAD"
    else:
        # Get all commits
        range_spec = "HEAD"

    try:
        # Get commit messages only (subject line)
        output = _run_git_command(
            ["log", range_spec, "--pretty=format:%s"],
            cwd=cwd,
        )

        if not output:
            return []

        return output.split("\n")
    except GitError as e:
        # If tag doesn't exist or other error, re-raise
        raise e


def extract_version_from_tag(tag: str) -> str:
    """Extract version number from a git tag.

    Args:
        tag: Git tag (e.g., 'v1.2.3' or '1.2.3')

    Returns:
        Version string without prefix (e.g., '1.2.3')
    """
    # Remove common prefixes like 'v', 'version-', etc.
    version = re.sub(r"^(v|version-?)", "", tag, flags=re.IGNORECASE)
    return version


def get_current_branch(git_root: Path) -> str:
    """Get the name of the current git branch.

    Args:
        git_root: Git repository root path

    Returns:
        Current branch name

    Raises:
        GitError: If unable to determine current branch
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=git_root,
            check=True,
            capture_output=True,
            text=True,
        )
        branch = result.stdout.strip()
        if not branch:
            raise GitError("Unable to determine current branch (detached HEAD?)")
        return branch
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to get current branch: {e.stderr.decode().strip()}")


def tag_exists(tag_name: str, git_root: Path) -> bool:
    """Check if a git tag exists locally or remotely.

    Args:
        tag_name: Name of the tag to check
        git_root: Git repository root path

    Returns:
        True if tag exists, False otherwise
    """
    try:
        # Check if tag exists locally
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/tags/{tag_name}"],
            cwd=git_root,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return True

        # Check if tag exists remotely
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "origin", tag_name],
            cwd=git_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return bool(result.stdout.strip())

    except subprocess.SubprocessError:
        return False


def create_tag(tag_name: str, message: str, git_root: Path) -> None:
    """Create an annotated git tag.

    Args:
        tag_name: Name of the tag (e.g., 'v1.2.3')
        message: Tag annotation message
        git_root: Git repository root path

    Raises:
        GitError: If tag creation fails
    """
    try:
        subprocess.run(
            ["git", "tag", "-a", tag_name, "-m", message],
            cwd=git_root,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode().strip() if e.stderr else ""
        raise GitError(f"Failed to create tag '{tag_name}': {stderr}")


def push_tag(tag_name: str, git_root: Path) -> None:
    """Push a git tag to remote origin.

    Args:
        tag_name: Name of the tag to push
        git_root: Git repository root path

    Raises:
        GitError: If tag push fails
    """
    try:
        subprocess.run(
            ["git", "push", "origin", tag_name],
            cwd=git_root,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode().strip() if e.stderr else ""
        raise GitError(f"Failed to push tag '{tag_name}': {stderr}")


def checkout_branch(branch_name: str, git_root: Path) -> None:
    """Checkout a git branch.

    Args:
        branch_name: Name of the branch to checkout
        git_root: Git repository root path

    Raises:
        GitError: If checkout fails
    """
    try:
        subprocess.run(
            ["git", "checkout", branch_name],
            cwd=git_root,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode().strip() if e.stderr else ""
        raise GitError(f"Failed to checkout branch '{branch_name}': {stderr}")


def detect_git_host(git_root: Path) -> str | None:
    """Detect git hosting provider from remote URL.

    Args:
        git_root: Git repository root path

    Returns:
        Git host identifier ('github', 'azure', 'gitlab') or None if cannot detect
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=git_root,
            check=True,
            capture_output=True,
            text=True,
        )
        remote_url = result.stdout.strip().lower()

        # Check for GitHub
        if "github.com" in remote_url:
            return "github"

        # Check for Azure DevOps
        if "dev.azure.com" in remote_url or "visualstudio.com" in remote_url:
            return "azure"

        # Future: GitLab
        # if "gitlab.com" in remote_url or "gitlab" in remote_url:
        #     return "gitlab"

        return None

    except subprocess.CalledProcessError:
        return None
