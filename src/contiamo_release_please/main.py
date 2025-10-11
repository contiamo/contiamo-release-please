"""CLI interface for contiamo-release-please."""

import sys
from pathlib import Path
from typing import Any

import click

from contiamo_release_please import __version__
from contiamo_release_please.analyser import analyse_commits, get_commit_type_summary
from contiamo_release_please.bumper import FileBumperError, bump_files
from contiamo_release_please.changelog import (
    format_changelog_entry,
    group_commits_by_section,
    prepend_to_changelog,
)
from contiamo_release_please.config import ConfigError, load_config
from contiamo_release_please.git import (
    GitError,
    extract_version_from_tag,
    get_commits_since_tag,
    get_git_root,
    get_latest_tag,
)
from contiamo_release_please.release import (
    ReleaseError,
    create_release_branch_workflow,
)
from contiamo_release_please.version import FIRST_RELEASE, get_next_version


def add_help_option(f):
    """Custom decorator to add '-h' as an alias for '--help'."""
    f = click.help_option("--help", "-h")(f)
    return f


def calculate_next_version(config_path: str | None = None) -> dict[str, Any]:
    """Calculate the next semantic version based on commit history.

    Args:
        config_path: Path to configuration file (None = use git root default)

    Returns:
        Dictionary containing:
        - current_version: Current version string or None
        - next_version: Next version without prefix
        - next_version_prefixed: Next version with prefix from config
        - release_type: Release type ('major', 'minor', 'patch') or None
        - commits: List of commit messages analysed
        - commit_summary: Dictionary of commit type counts

    Raises:
        ConfigError: If configuration is invalid
        GitError: If git operations fail
    """
    # If no config specified, use git root + default filename
    if config_path is None:
        git_root = get_git_root()
        config_path = str(git_root / "contiamo-release-please.yaml")

    # Load configuration
    release_config = load_config(config_path)

    # Get latest tag
    latest_tag = get_latest_tag()

    if latest_tag:
        current_version = extract_version_from_tag(latest_tag)
    else:
        current_version = None

    # Get commits since tag
    commits = get_commits_since_tag(latest_tag)

    # Get commit summary
    commit_summary = get_commit_type_summary(commits, release_config)

    # Analyse commits to determine release type
    release_type = analyse_commits(commits, release_config)

    # Calculate next version
    next_version = get_next_version(current_version, release_type)

    # Get version prefix from config
    version_prefix = release_config.get_version_prefix()

    return {
        "current_version": current_version,
        "next_version": next_version,
        "next_version_prefixed": f"{version_prefix}{next_version}",
        "release_type": release_type,
        "commits": commits,
        "commit_summary": commit_summary,
    }


@click.group()
@add_help_option
@click.version_option(__version__, "--version", "-v")
def cli():
    """Contiamo Release Please - Automated semantic versioning and release management."""
    pass


@cli.command()
@add_help_option
@click.option(
    "--config",
    "-c",
    default=None,
    help="Path to configuration file (default: contiamo-release-please.yaml in git root)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information about commits analysed",
)
def next_version(config: str | None, verbose: bool):
    """Calculate the next semantic version based on commit history.

    Analyses commits since the last git tag and determines what version
    bump is needed based on conventional commit types.
    """
    try:
        # Calculate next version using the reusable function
        result = calculate_next_version(config)

        # Verbose output
        if verbose:
            # Show current version info
            if result["current_version"]:
                click.echo(f"Current version: {result['current_version']}")
            else:
                click.echo("No tags found in repository")
                click.echo(f"Will use first release: {FIRST_RELEASE}")

            # Show commits found
            click.echo(f"\nFound {len(result['commits'])} commits since last release")

            # Show commit summary
            if result["commits"]:
                click.echo("\nCommit summary:")
                # Load config to check which types map to release types
                if config is None:
                    git_root = get_git_root()
                    config_path = str(git_root / "contiamo-release-please.yaml")
                else:
                    config_path = config
                release_config = load_config(config_path)

                for commit_type, count in sorted(result["commit_summary"].items()):
                    release_type = release_config.get_release_type_for_prefix(
                        commit_type
                    )
                    if release_type:
                        click.echo(f"  {commit_type}: {count} → {release_type} bump")
                    else:
                        click.echo(f"  {commit_type}: {count} → (no bump)")

            # Show release type determined
            if result["release_type"]:
                click.echo(f"\nDetermined release type: {result['release_type']}")

            # Show version bump
            if result["current_version"]:
                if result["release_type"]:
                    click.echo(
                        f"Version bump: {result['current_version']} → {result['next_version']}"
                    )
                else:
                    click.echo("No release needed (no relevant commits)")
            else:
                click.echo(f"First release version: {result['next_version']}")
            click.echo()

        # Output the final version (with prefix)
        click.echo(result["next_version_prefixed"])

    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except GitError as e:
        click.echo(f"Git error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@add_help_option
@click.option(
    "--config",
    "-c",
    default=None,
    help="Path to configuration file (default: contiamo-release-please.yaml in git root)",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Override changelog file path (default: from config or CHANGELOG.md)",
)
@click.option(
    "--dry-run",
    "-d",
    is_flag=True,
    help="Show what would be added without modifying the changelog file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information about changelog generation",
)
def generate_changelog(
    config: str | None, output: str | None, dry_run: bool, verbose: bool
):
    """Generate changelog entry for the next release.

    Analyses commits since the last git tag and generates a formatted
    changelog entry based on conventional commit types.
    """
    try:
        # Calculate next version using the reusable function
        result = calculate_next_version(config)

        # Load config to get changelog settings
        if config is None:
            git_root = get_git_root()
            config_path = str(git_root / "contiamo-release-please.yaml")
        else:
            config_path = config
        release_config = load_config(config_path)

        # Determine changelog path
        if output:
            changelog_path = Path(output)
        else:
            git_root = get_git_root()
            changelog_filename = release_config.get_changelog_path()
            changelog_path = git_root / changelog_filename

        # Check if there are any commits to process
        if not result["commits"]:
            click.echo("No commits found since last release")
            click.echo("Nothing to add to changelog")
            return

        # Group commits by section
        grouped_commits = group_commits_by_section(result["commits"], release_config)

        if not grouped_commits:
            click.echo("No conventional commits found")
            click.echo("Nothing to add to changelog")
            return

        # Format changelog entry
        changelog_entry = format_changelog_entry(
            result["next_version"], grouped_commits, release_config
        )

        # Verbose output
        if verbose:
            click.echo(f"Version: {result['next_version']}")
            click.echo(f"Changelog path: {changelog_path}")
            click.echo(f"\nFound {len(result['commits'])} commits")
            click.echo(f"Grouped into {len(grouped_commits)} sections:")
            for section_name, commits in grouped_commits.items():
                click.echo(f"  {section_name}: {len(commits)} commits")
            click.echo()

        # Show the changelog entry
        if dry_run or verbose:
            click.echo("Changelog entry:")
            click.echo("-" * 80)
            click.echo(changelog_entry)
            click.echo("-" * 80)

        # Write to file unless dry-run
        if not dry_run:
            prepend_to_changelog(changelog_path, changelog_entry)
            click.echo(f"\nChangelog updated: {changelog_path}")
        else:
            click.echo("\nDry run - no files modified")

    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except GitError as e:
        click.echo(f"Git error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@add_help_option
@click.option(
    "--config",
    "-c",
    default=None,
    help="Path to configuration file (default: contiamo-release-please.yaml in git root)",
)
@click.option(
    "--dry-run",
    "-d",
    is_flag=True,
    help="Show what would be updated without modifying files",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information about file bumping",
)
def bump_files_cmd(config: str | None, dry_run: bool, verbose: bool):
    """Bump version in configured files.

    Automatically determines the next version based on commit history
    and updates version fields in configured files.
    """
    try:
        # Calculate next version using the reusable function
        result = calculate_next_version(config)
        version = result["next_version"]

        # Load config to get extra files settings
        if config is None:
            git_root = get_git_root()
            config_path = str(git_root / "contiamo-release-please.yaml")
        else:
            config_path = config
        release_config = load_config(config_path)

        # Get extra files configuration
        extra_files = release_config.get_extra_files()

        if not extra_files:
            click.echo("No extra files configured for version bumping")
            click.echo("Add 'extra-files' section to your config file")
            return

        # Get git root
        git_root = get_git_root()

        # Verbose output
        if verbose:
            click.echo(f"Next version: {version}")
            click.echo(f"Files to update: {len(extra_files)}")
            if dry_run:
                click.echo("Dry-run mode: no files will be modified")
            click.echo()

        # Bump files
        results = bump_files(extra_files, version, git_root, dry_run=dry_run)

        # Display results
        if results["updated"]:
            click.echo("Updated files:")
            for update in results["updated"]:
                click.echo(f"  ✓ {update}")

        if results["errors"]:
            click.echo("\nErrors:")
            for error in results["errors"]:
                click.echo(f"  ✗ {error}", err=True)

        if dry_run:
            click.echo("\nDry run - no files modified")
        else:
            click.echo(f"\nSuccessfully updated {len(results['updated'])} file(s)")

        # Exit with error if there were any errors
        if results["errors"]:
            sys.exit(1)

    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except GitError as e:
        click.echo(f"Git error: {e}", err=True)
        sys.exit(1)
    except FileBumperError as e:
        click.echo(f"Bumper error: {e}", err=True)
        sys.exit(1)


@cli.command()
@add_help_option
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file (default: contiamo-release-please.yaml in git root)",
)
@click.option(
    "--dry-run",
    "-d",
    is_flag=True,
    help="Show what would be done without making any changes",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information about the release process",
)
def release(config: str | None, dry_run: bool, verbose: bool):
    """Create or update release branch with version bumps and changelog.

    This command orchestrates the full release workflow:
    1. Determines the next version from commit history
    2. Creates/resets a release branch from the source branch
    3. Generates changelog entry
    4. Bumps version in configured files
    5. Commits and pushes changes

    The release branch can then be used to create a pull request for review.
    """
    try:
        create_release_branch_workflow(
            config_path=config,
            dry_run=dry_run,
            verbose=verbose,
        )

    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except GitError as e:
        click.echo(f"Git error: {e}", err=True)
        sys.exit(1)
    except ReleaseError as e:
        click.echo(f"Release error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
