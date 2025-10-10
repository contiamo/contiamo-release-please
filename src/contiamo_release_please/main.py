"""CLI interface for contiamo-release-please."""

import sys
from pathlib import Path

import click

from contiamo_release_please import __version__
from contiamo_release_please.analyser import analyse_commits, get_commit_type_summary
from contiamo_release_please.config import ConfigError, load_config
from contiamo_release_please.git import (
    GitError,
    extract_version_from_tag,
    get_commits_since_tag,
    get_git_root,
    get_latest_tag,
)
from contiamo_release_please.version import FIRST_RELEASE, get_next_version


def add_help_option(f):
    """Custom decorator to add '-h' as an alias for '--help'."""
    f = click.help_option("--help", "-h")(f)
    return f


def calculate_next_version(config_path: str | None = None) -> dict[str, any]:
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


if __name__ == "__main__":
    cli()
