"""Release branch creation and management for contiamo-release-please."""

import subprocess
from pathlib import Path
from typing import Any

import click

from contiamo_release_please.analyser import (
    analyse_commits,
    get_commit_type_summary,
    parse_commit_message,
)
from contiamo_release_please.bumper import bump_files
from contiamo_release_please.changelog import (
    format_changelog_entry,
    prepend_to_changelog,
)
from contiamo_release_please.config import load_config
from contiamo_release_please.git import (
    get_commits_since_tag,
    get_git_root,
    get_latest_tag,
)
from contiamo_release_please.version import get_next_version, parse_version


class ReleaseError(Exception):
    """Raised when release operations fail."""

    pass


def branch_exists(branch_name: str, git_root: Path) -> bool:
    """Check if a branch exists locally or remotely.

    Args:
        branch_name: Name of the branch to check
        git_root: Git repository root path

    Returns:
        True if branch exists (local or remote), False otherwise
    """
    try:
        # Check if branch exists locally or remotely
        result = subprocess.run(
            ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
            cwd=git_root,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return True

        # Check remote
        result = subprocess.run(
            ["git", "show-ref", "--verify", f"refs/remotes/origin/{branch_name}"],
            cwd=git_root,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0

    except subprocess.SubprocessError:
        return False


def create_or_reset_release_branch(
    branch_name: str,
    source_branch: str,
    git_root: Path,
    dry_run: bool = False,
) -> None:
    """Force create or reset release branch from source branch.

    This uses git checkout -B to create a new branch or reset an existing one
    to match the source branch exactly, avoiding any merge conflicts.

    Args:
        branch_name: Name of the release branch
        source_branch: Name of the source branch to branch from
        git_root: Git repository root path
        dry_run: If True, don't actually create/reset the branch

    Raises:
        ReleaseError: If git operations fail
    """
    if dry_run:
        return

    try:
        # Fetch latest from remote
        subprocess.run(
            ["git", "fetch", "origin"],
            cwd=git_root,
            check=True,
            capture_output=True,
        )

        # Force create/reset branch from source
        # This creates a new branch or resets existing one to match source
        subprocess.run(
            ["git", "checkout", "-B", branch_name, f"origin/{source_branch}"],
            cwd=git_root,
            check=True,
            capture_output=True,
        )

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        raise ReleaseError(
            f"Failed to create/reset release branch '{branch_name}' from '{source_branch}': {stderr}"
        )


def stage_and_commit_release_changes(
    version: str,
    source_branch: str,
    git_root: Path,
    dry_run: bool = False,
) -> None:
    """Stage all changes and commit with release message.

    Args:
        version: Version number (without prefix)
        source_branch: Source branch name for commit message scope
        git_root: Git repository root path
        dry_run: If True, don't actually commit

    Raises:
        ReleaseError: If git operations fail
    """
    if dry_run:
        return

    try:
        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=git_root,
            check=True,
            capture_output=True,
        )

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=git_root,
            check=False,
            capture_output=True,
        )

        # If no changes, nothing to commit
        if result.returncode == 0:
            return

        # Commit with conventional commit message
        commit_message = f"chore({source_branch}): update files for release {version}"
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=git_root,
            check=True,
            capture_output=True,
        )

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        raise ReleaseError(f"Failed to commit release changes: {stderr}")


def push_release_branch(
    branch_name: str,
    git_root: Path,
    dry_run: bool = False,
) -> None:
    """Force push release branch to remote.

    Args:
        branch_name: Name of the release branch
        git_root: Git repository root path
        dry_run: If True, don't actually push

    Raises:
        ReleaseError: If git push fails
    """
    if dry_run:
        return

    try:
        subprocess.run(
            ["git", "push", "-f", "origin", branch_name],
            cwd=git_root,
            check=True,
            capture_output=True,
        )

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        raise ReleaseError(f"Failed to push release branch '{branch_name}': {stderr}")


def create_release_branch_workflow(
    config_path: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Orchestrate the full release branch creation/update workflow.

    This function:
    1. Determines the next version
    2. Creates/resets the release branch from source
    3. Generates changelog and bumps version files
    4. Commits and pushes changes

    Args:
        config_path: Path to config file (optional)
        dry_run: If True, show what would be done without doing it
        verbose: If True, show detailed output

    Returns:
        Dictionary with workflow results

    Raises:
        ReleaseError: If workflow fails
    """
    # Load configuration
    git_root = get_git_root()
    if config_path:
        config_file = Path(config_path)
    else:
        config_file = git_root / "contiamo-release-please.yaml"

    config = load_config(config_file)

    # Get configuration values
    source_branch = config.get_source_branch()
    release_branch = config.get_release_branch_name()
    version_prefix = config.get_version_prefix()
    changelog_path = config.get_changelog_path()
    extra_files = config.get_extra_files()

    # Determine next version
    latest_tag = get_latest_tag(git_root)
    if latest_tag:
        # parse_version returns Version object, convert to string
        current_version_obj = parse_version(latest_tag)
        current_version_str = str(current_version_obj)
    else:
        current_version_str = None

    commits = get_commits_since_tag(latest_tag, git_root)
    if not commits:
        raise ReleaseError("No commits since last release")

    # Analyse commits (returns release type string)
    release_type = analyse_commits(commits, config)
    if not release_type:
        raise ReleaseError("No releasable commits found")

    # Get commit summary
    commit_summary = get_commit_type_summary(commits, config)

    # Parse commits for changelog
    parsed_commits = [parse_commit_message(c) for c in commits]

    # Calculate next version (handles first release correctly)
    next_version = get_next_version(current_version_str, release_type)
    next_version_prefixed = f"{version_prefix}{next_version}"

    # Show what will be done
    if verbose or dry_run:
        click.echo(f"Source branch: {source_branch}")
        click.echo(f"Release branch: {release_branch}")
        click.echo(f"Current version: {current_version_str or 'none'}")
        click.echo(f"Next version: {next_version_prefixed}")
        click.echo(f"Release type: {release_type}")
        click.echo(f"\nCommits to include: {len(commits)}")

        if verbose:
            for commit_type, count in commit_summary.items():
                click.echo(f"  {commit_type}: {count}")

    if dry_run:
        click.echo(f"\nWould force-reset branch '{release_branch}' from '{source_branch}'")
        click.echo(f"Would update {len(extra_files)} extra files")
        click.echo(f"Would update {changelog_path}")
        click.echo(
            f"Would commit: chore({source_branch}): update files for release {next_version}"
        )
        click.echo(f"Would force-push to origin/{release_branch}")
        return {
            "dry_run": True,
            "version": next_version,
            "version_prefixed": next_version_prefixed,
        }

    # Create or reset release branch
    if verbose:
        click.echo(f"\nCreating/resetting release branch '{release_branch}'...")

    create_or_reset_release_branch(release_branch, source_branch, git_root, dry_run)

    # Generate changelog entry
    if verbose:
        click.echo("Generating changelog entry...")

    grouped_commits = {}
    for section_config in config.get_changelog_sections():
        commit_type_key = section_config["type"]
        section_name = section_config["section"]

        matching = [c for c in parsed_commits if c["type"] == commit_type_key]
        if matching:
            if section_name not in grouped_commits:
                grouped_commits[section_name] = []
            grouped_commits[section_name].extend(matching)

    changelog_entry = format_changelog_entry(next_version, grouped_commits, config)

    # Update changelog file
    changelog_file = git_root / changelog_path
    prepend_to_changelog(changelog_file, changelog_entry)

    if verbose:
        click.echo(f"Updated {changelog_path}")

    # Bump version in extra files
    if extra_files:
        if verbose:
            click.echo(f"Bumping version in {len(extra_files)} files...")

        bump_results = bump_files(extra_files, next_version, git_root, dry_run=False)

        if bump_results["errors"]:
            raise ReleaseError(f"File bumping errors: {bump_results['errors']}")

        if verbose:
            for updated in bump_results["updated"]:
                click.echo(f"  ✓ {updated}")

    # Commit changes
    if verbose:
        click.echo("\nCommitting changes...")

    stage_and_commit_release_changes(next_version, source_branch, git_root, dry_run)

    # Push to remote
    if verbose:
        click.echo(f"Pushing to origin/{release_branch}...")

    push_release_branch(release_branch, git_root, dry_run)

    # Success message
    click.echo(f"\n✓ Release branch created/updated: {release_branch}")
    click.echo(f"✓ Version: {next_version_prefixed}")
    click.echo("\nNext steps:")
    click.echo(f"  1. Create a pull request from '{release_branch}' to '{source_branch}'")
    click.echo("  2. Review the changes")
    click.echo("  3. Merge the pull request when ready to release")

    return {
        "success": True,
        "version": next_version,
        "version_prefixed": next_version_prefixed,
        "release_branch": release_branch,
        "source_branch": source_branch,
    }
