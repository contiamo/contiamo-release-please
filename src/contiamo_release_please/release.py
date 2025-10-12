"""Release branch creation and management for contiamo-release-please."""

import subprocess
from pathlib import Path
from typing import Any

import click

from contiamo_release_please.analyser import (
    analyse_commits,
    get_commit_type_summary,
    is_release_commit,
    parse_commit_message,
)
from contiamo_release_please.bumper import bump_files
from contiamo_release_please.changelog import (
    extract_changelog_for_version,
    format_changelog_entry,
    prepend_to_changelog,
)
from contiamo_release_please.config import load_config
from contiamo_release_please.git import (
    checkout_branch,
    configure_git_identity,
    create_tag,
    detect_git_host,
    get_commits_since_tag,
    get_current_branch,
    get_git_root,
    get_latest_commit_message,
    get_latest_tag,
    push_tag,
    tag_exists,
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


def write_version_file(git_root: Path, version: str) -> None:
    """Write version to version.txt file in repository root.

    Args:
        git_root: Git repository root path
        version: Version string (with prefix if configured, e.g., 'v0.1.0' or '0.1.0')

    Raises:
        ReleaseError: If writing fails
    """
    version_file = git_root / "version.txt"
    try:
        version_file.write_text(f"{version}\n")
    except Exception as e:
        raise ReleaseError(f"Failed to write version.txt: {e}")


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
    git_host: str | None = None,
) -> dict[str, Any]:
    """Orchestrate the full release branch creation/update workflow.

    This function:
    1. Determines the next version
    2. Creates/resets the release branch from source
    3. Generates changelog and bumps version files
    4. Commits and pushes changes
    5. Creates/updates pull request (if git_host specified)

    Args:
        config_path: Path to config file (optional)
        dry_run: If True, show what would be done without doing it
        verbose: If True, show detailed output
        git_host: Git hosting provider for PR creation (e.g., 'github')

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

    # Configure git identity for commits
    git_user_name = config.get_git_user_name()
    git_user_email = config.get_git_user_email()
    configure_git_identity(git_user_name, git_user_email, git_root)

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

    # Get all commits since last tag
    all_commits = get_commits_since_tag(latest_tag, git_root)
    if not all_commits:
        raise ReleaseError("No commits since last release")

    # Filter out release infrastructure commits
    commits = [c for c in all_commits if not is_release_commit(c, release_branch)]

    # Check if only release commits exist (user forgot to run tag-release)
    if not commits and all_commits:
        raise ReleaseError(
            "Only release infrastructure commits found since last tag. "
            "Please run 'contiamo-release-please tag-release' to tag the merged release."
        )

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

    # Determine git host (auto-detect if not explicitly provided)
    determined_git_host = git_host
    if not determined_git_host:
        from contiamo_release_please.git import detect_git_host

        determined_git_host = detect_git_host(git_root)

    # Validate git host was determined
    if determined_git_host is None:
        raise ReleaseError(
            "Could not detect git hosting provider from remote URL. "
            "Supported providers: github.com, dev.azure.com. "
            "Use --git-host to specify provider explicitly: --git-host github|azure"
        )

    # Validate credentials for detected git host (even in dry-run)
    if determined_git_host.lower() == "github":
        from contiamo_release_please.github import GitHubError, get_github_token

        try:
            get_github_token(config._config)
        except GitHubError as e:
            raise ReleaseError(f"GitHub detected but authentication failed: {e}")

    elif determined_git_host.lower() == "azure":
        from contiamo_release_please.azure import AzureDevOpsError, get_azure_token

        try:
            get_azure_token(config._config)
        except AzureDevOpsError as e:
            raise ReleaseError(f"Azure DevOps detected but authentication failed: {e}")

    # Generate changelog entry (needed for both dry-run and actual run)
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
        click.echo(
            f"\nWould force-reset branch '{release_branch}' from '{source_branch}'"
        )
        click.echo(f"Would update {len(extra_files)} extra files")
        click.echo(f"Would update {changelog_path}")
        click.echo("Would update version.txt")
        click.echo(
            f"Would commit: chore({source_branch}): update files for release {next_version}"
        )
        click.echo(f"Would force-push to origin/{release_branch}")

        # Always show PR creation (git host is now validated above)
        pr_title = f"chore({source_branch}): release {next_version}"
        click.echo(f"\nWould create/update {determined_git_host.upper()} PR:")
        click.echo(f"  Title: {pr_title}")
        click.echo(f"  Head: {release_branch}")
        click.echo(f"  Base: {source_branch}")
        click.echo(f"  Body:\n{changelog_entry}")

        return {
            "dry_run": True,
            "version": next_version,
            "version_prefixed": next_version_prefixed,
        }

    # Create or reset release branch
    if verbose:
        click.echo(f"\nCreating/resetting release branch '{release_branch}'...")

    create_or_reset_release_branch(release_branch, source_branch, git_root, dry_run)

    # Changelog entry already generated above (needed for dry-run)
    if verbose:
        click.echo("Updating changelog file...")

    # Update changelog file
    changelog_file = git_root / changelog_path
    prepend_to_changelog(changelog_file, changelog_entry)

    if verbose:
        click.echo(f"Updated {changelog_path}")

    # Write version.txt
    write_version_file(git_root, next_version_prefixed)

    if verbose:
        click.echo("Updated version.txt")

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

    # Create or update pull request (git host is always determined at this point)
    pr_url = None
    if determined_git_host.lower() == "github":
        from contiamo_release_please.github import (
            GitHubError,
            create_or_update_pr,
            get_github_token,
            get_repo_info,
        )

        try:
            if verbose:
                click.echo("\nCreating/updating GitHub pull request...")

            # Get authentication
            token = get_github_token(config._config)

            # Get repo info
            owner, repo = get_repo_info(git_root)

            # Generate PR title (matching release-please format)
            pr_title = f"chore({source_branch}): release {next_version}"

            # Use changelog entry as PR body
            pr_body = changelog_entry

            # Create or update PR
            pr_data = create_or_update_pr(
                owner=owner,
                repo=repo,
                title=pr_title,
                body=pr_body,
                head_branch=release_branch,
                base_branch=source_branch,
                token=token,
                dry_run=dry_run,
                verbose=verbose,
            )

            if pr_data:
                pr_url = pr_data.get("html_url")
                pr_number = pr_data.get("number")
                click.echo(f"\n✓ Pull request created/updated: #{pr_number}")
                click.echo(f"  {pr_url}")

        except GitHubError as e:
            raise ReleaseError(f"GitHub PR creation failed: {e}")

    elif determined_git_host.lower() == "azure":
        from contiamo_release_please.azure import (
            AzureDevOpsError,
            create_or_update_pr,
            get_azure_repo_info,
            get_azure_token,
        )

        try:
            if verbose:
                click.echo("\nCreating/updating Azure DevOps pull request...")

            # Get authentication
            token = get_azure_token(config._config)

            # Get repo info
            org, project, repo = get_azure_repo_info(git_root)

            # Generate PR title (matching release-please format)
            pr_title = f"chore({source_branch}): release {next_version}"

            # Use changelog entry as PR body
            pr_body = changelog_entry

            # Create or update PR
            pr_data = create_or_update_pr(
                org=org,
                project=project,
                repo=repo,
                title=pr_title,
                body=pr_body,
                head_branch=release_branch,
                base_branch=source_branch,
                token=token,
                dry_run=dry_run,
                verbose=verbose,
            )

            if pr_data:
                pr_url = pr_data.get("url")
                pr_id = pr_data.get("pullRequestId")
                click.echo(f"\n✓ Pull request created/updated: #{pr_id}")
                click.echo(f"  {pr_url}")

        except AzureDevOpsError as e:
            raise ReleaseError(f"Azure DevOps PR creation failed: {e}")

    # Switch back to source branch
    if verbose:
        click.echo(f"\nSwitching back to '{source_branch}'...")

    checkout_branch(source_branch, git_root)

    # Success message
    click.echo(f"\n✓ Release branch created/updated: {release_branch}")
    click.echo(f"✓ Version: {next_version_prefixed}")
    click.echo(f"✓ Switched back to: {source_branch}")

    # PR is always created at this point, no need for manual steps message

    return {
        "success": True,
        "version": next_version,
        "version_prefixed": next_version_prefixed,
        "release_branch": release_branch,
        "source_branch": source_branch,
        "pr_url": pr_url,
    }


def tag_release_workflow(
    config_path: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Create and push git tag for a merged release.

    This function should be run after merging a release PR to the source branch.
    It reads the version from version.txt and creates an annotated git tag.

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

    # Configure git identity for commits
    git_user_name = config.get_git_user_name()
    git_user_email = config.get_git_user_email()
    configure_git_identity(git_user_name, git_user_email, git_root)

    # Get configuration values
    release_branch = config.get_release_branch_name()

    # Validation 1: Check we're NOT on the release branch
    current_branch = get_current_branch(git_root)
    if current_branch == release_branch:
        raise ReleaseError(
            f"Cannot create tag from release branch '{release_branch}'. "
            f"Please merge the release PR first and run from the source branch."
        )

    # Validation 2: Check that latest commit is a release PR merge
    latest_commit = get_latest_commit_message(git_root)
    if not is_release_commit(latest_commit, release_branch):
        source_branch = config.get_source_branch()
        raise ReleaseError(
            f"Cannot create release tag: Latest commit is not a release PR merge.\n\n"
            f"Latest commit message:\n  {latest_commit}\n\n"
            f"Expected pattern (squash merge):\n"
            f"  chore({source_branch}): update files for release X.Y.Z\n\n"
            f"Or pattern (merge commit):\n"
            f"  Merge branch '{release_branch}' into {source_branch}\n\n"
            f"The tag-release command should only be run after merging a release PR.\n\n"
            f"To create a release:\n"
            f"  1. Run: contiamo-release-please release\n"
            f"  2. Review and merge the release PR\n"
            f"  3. Run: contiamo-release-please tag-release\n\n"
            f"If you need to create a tag manually, use 'git tag' directly."
        )

    # Validation 3: Read version from version.txt
    version_file = git_root / "version.txt"
    if not version_file.exists():
        raise ReleaseError(
            "version.txt not found. Please run 'contiamo-release-please release' first "
            "and merge the release PR before creating a tag."
        )

    try:
        version = version_file.read_text().strip()
    except Exception as e:
        raise ReleaseError(f"Failed to read version.txt: {e}")

    if not version:
        raise ReleaseError("version.txt is empty")

    # Validation 4: Check if tag already exists
    if tag_exists(version, git_root):
        raise ReleaseError(
            f"Tag '{version}' already exists. "
            f"If you need to recreate the tag, delete it first with: git tag -d {version} && git push origin :refs/tags/{version}"
        )

    # Show what will be done
    if verbose or dry_run:
        click.echo(f"Current branch: {current_branch}")
        click.echo(f"Version from version.txt: {version}")
        click.echo(f"Tag to create: {version}")

    if dry_run:
        click.echo(f"\nWould create annotated tag '{version}'")
        click.echo("Would push tag to origin")
        return {
            "dry_run": True,
            "version": version,
            "current_branch": current_branch,
        }

    # Create annotated tag
    if verbose:
        click.echo(f"\nCreating tag '{version}'...")

    tag_message = f"Release {version}"
    create_tag(version, tag_message, git_root)

    if verbose:
        click.echo("✓ Tag created")

    # Push tag to remote
    if verbose:
        click.echo("Pushing tag to origin...")

    push_tag(version, git_root)

    if verbose:
        click.echo("✓ Tag pushed")

    # Try to create GitHub release if this is a GitHub repository
    git_host = detect_git_host(git_root)
    release_url = None

    if git_host == "github":
        try:
            from contiamo_release_please.github import (
                create_github_release,
                get_github_token,
                get_repo_info,
            )

            # Get GitHub credentials
            token = get_github_token(config._config)
            owner, repo = get_repo_info(git_root)

            # Extract version without prefix for changelog lookup
            # The changelog always uses versions without prefix (e.g., "## [1.2.3]")
            # but version.txt contains the prefixed version (e.g., "v1.2.3" or "release-1.2.3")
            version_prefix = config.get_version_prefix()
            if version_prefix and version.startswith(version_prefix):
                version_without_prefix = version[len(version_prefix) :]
            else:
                version_without_prefix = version

            # Get changelog content for this version
            changelog_path = config.get_changelog_path()
            changelog_file = git_root / changelog_path
            changelog_body = extract_changelog_for_version(
                changelog_file, version_without_prefix
            )

            # If no changelog found, use a simple message
            if not changelog_body:
                changelog_body = f"Release {version}"

            if verbose:
                click.echo(f"\nCreating GitHub release for {version}...")

            # Create GitHub release
            if not dry_run:
                release_data = create_github_release(
                    owner=owner,
                    repo=repo,
                    tag_name=version,
                    release_name=version,
                    body=changelog_body,
                    token=token,
                    dry_run=dry_run,
                    verbose=verbose,
                )

                if release_data:
                    release_url = release_data.get("html_url")
                    if verbose:
                        click.echo(f"✓ GitHub release created: {release_url}")
            else:
                if verbose:
                    click.echo(f"Would create GitHub release for tag {version}")

        except Exception as e:
            # Don't fail the entire workflow if GitHub release creation fails
            if verbose:
                click.echo(f"Warning: Failed to create GitHub release: {e}")

    # Success message
    click.echo(f"\n✓ Tag created and pushed: {version}")
    click.echo(f"✓ Branch: {current_branch}")
    if release_url:
        click.echo(f"✓ GitHub release: {release_url}")

    return {
        "success": True,
        "version": version,
        "current_branch": current_branch,
        "release_url": release_url,
    }
