"""Configuration loading and parsing for contiamo-release-please."""

from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""

    pass


class ReleaseConfig:
    """Release configuration loaded from YAML file."""

    def __init__(self, config_path: str | Path = "contiamo-release-please.yaml"):
        """Load release configuration from YAML file.

        Args:
            config_path: Path to configuration file (default: contiamo-release-please.yaml)

        Raises:
            ConfigError: If config file doesn't exist or is invalid
        """
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise ConfigError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            self._config: dict[str, Any] = yaml.safe_load(f)

        self._validate_config()

    def _validate_config(self) -> None:
        """Validate that required configuration sections exist."""
        if "release-rules" not in self._config:
            raise ConfigError("Configuration must contain 'release-rules' section")

        rules = self._config["release-rules"]
        if not isinstance(rules, dict):
            raise ConfigError("'release-rules' must be a dictionary")

        # Check that at least one of major/minor/patch exists
        if not any(key in rules for key in ["major", "minor", "patch"]):
            raise ConfigError(
                "'release-rules' must contain at least one of: major, minor, patch"
            )

        # Validate version-prefix if present
        if "version-prefix" in self._config:
            prefix = self._config["version-prefix"]
            if not isinstance(prefix, str):
                raise ConfigError("'version-prefix' must be a string")

    def get_release_type_for_prefix(self, prefix: str) -> str | None:
        """Determine release type (major/minor/patch) for a commit prefix.

        Args:
            prefix: Commit type prefix (e.g., 'feat', 'fix', 'breaking')

        Returns:
            Release type ('major', 'minor', or 'patch') or None if no match
        """
        rules = self._config["release-rules"]

        # Check in order of priority: major > minor > patch
        for release_type in ["major", "minor", "patch"]:
            if release_type in rules:
                prefixes = rules[release_type]
                if not isinstance(prefixes, list):
                    continue
                if prefix in prefixes:
                    return release_type

        return None

    def get_all_valid_prefixes(self) -> set[str]:
        """Get all valid commit prefixes from configuration.

        Returns:
            Set of all valid prefixes
        """
        prefixes = set()
        rules = self._config["release-rules"]

        for release_type in ["major", "minor", "patch"]:
            if release_type in rules and isinstance(rules[release_type], list):
                prefixes.update(rules[release_type])

        return prefixes

    def get_version_prefix(self) -> str:
        """Get the version prefix from configuration.

        Returns:
            Version prefix string (e.g., 'v', 'version-') or empty string if not configured
        """
        return self._config.get("version-prefix", "")

    def get_changelog_path(self) -> str:
        """Get the changelog file path from configuration.

        Returns:
            Changelog file path or 'CHANGELOG.md' as default
        """
        return self._config.get("changelog-path", "CHANGELOG.md")

    def get_changelog_sections(self) -> list[dict[str, str]]:
        """Get changelog sections configuration.

        Returns:
            List of section dictionaries with 'type' and 'section' keys.
            Returns default sections if not configured.
        """
        default_sections = [
            {"type": "feat", "section": "Features"},
            {"type": "fix", "section": "Bug Fixes"},
            {"type": "chore", "section": "Miscellaneous Changes"},
            {"type": "ci", "section": "Miscellaneous Changes"},
            {"type": "docs", "section": "Documentation"},
            {"type": "refactor", "section": "Code Refactoring"},
        ]

        return self._config.get("changelog-sections", default_sections)

    def get_extra_files(self) -> list[dict[str, Any]]:
        """Get extra files configuration for version bumping.

        Returns:
            List of file configuration dictionaries
        """
        return self._config.get("extra-files", [])

    def get_source_branch(self) -> str:
        """Get the source branch name from configuration.

        Returns:
            Source branch name or 'main' as default
        """
        return self._config.get("source-branch", "main")

    def get_release_branch_name(self) -> str:
        """Get the release branch name from configuration.

        Returns:
            Release branch name or generated default based on source branch
        """
        if "release-branch-name" in self._config:
            return self._config["release-branch-name"]

        # Generate default: release-please--branches--{source-branch}
        source_branch = self.get_source_branch()
        return f"release-please--branches--{source_branch}"

    def get_git_user_name(self) -> str:
        """Get git user name for commits.

        Returns:
            Git user name or 'Contiamo Release Bot' as default
        """
        git_config = self._config.get("git", {})
        return git_config.get("user-name", "Contiamo Release Bot")

    def get_git_user_email(self) -> str:
        """Get git user email for commits.

        Returns:
            Git user email or 'contiamo-release@ctmo.io' as default
        """
        git_config = self._config.get("git", {})
        return git_config.get("user-email", "contiamo-release@ctmo.io")


def load_config(
    config_path: str | Path = "contiamo-release-please.yaml",
) -> ReleaseConfig:
    """Load release configuration from file.

    Args:
        config_path: Path to configuration file

    Returns:
        Loaded configuration object

    Raises:
        ConfigError: If config file is invalid or cannot be loaded
    """
    return ReleaseConfig(config_path)


def generate_config_template() -> str:
    """Generate a complete configuration file template with all parameters documented.

    Returns:
        YAML configuration template as a string with inline documentation
    """
    template = """# Contiamo Release Please Configuration
#
# This file defines how conventional commits map to semantic version bumps.
# For more information, visit: https://github.com/contiamo/contiamo-release-please

# ============================================================================
# REQUIRED CONFIGURATION
# ============================================================================

# REQUIRED: Release rules mapping commit types to version bumps
# Type: object with major/minor/patch keys containing lists of commit types
# At least one of major/minor/patch must be defined
release-rules:
  # Major version bump (x.0.0) - breaking changes
  major:
    - breaking

  # Minor version bump (0.x.0) - new features
  minor:
    - feat

  # Patch version bump (0.0.x) - bug fixes and minor changes
  patch:
    - fix
    - perf
    - chore
    - docs
    - refactor
    - style
    - test
    - ci

# ============================================================================
# OPTIONAL CONFIGURATION (with defaults)
# ============================================================================

# Version prefix (e.g., "v" for v1.2.3, "" for 1.2.3)
# Type: string
# Default: "" (no prefix)
version-prefix: ""

# Changelog file path
# Type: string
# Default: "CHANGELOG.md"
changelog-path: "CHANGELOG.md"

# Source branch to create releases from
# Type: string
# Default: "main"
source-branch: "main"

# Custom release branch name
# Type: string
# Default: "release-please--branches--{source-branch}" (auto-generated)
# Uncomment to customise:
# release-branch-name: "release-please--branches--main"

# Git identity for commits (used when creating release commits)
# Type: object with user-name and user-email fields
# Default: shown below
git:
  # Name to use for git commits
  # Default: "Contiamo Release Bot"
  user-name: "Contiamo Release Bot"

  # Email to use for git commits
  # Default: "contiamo-release@ctmo.io"
  user-email: "contiamo-release@ctmo.io"

# Changelog sections - groups commits by type in the changelog
# Type: list of objects with 'type' and 'section' fields
# Default: shown below
changelog-sections:
  - type: feat
    section: Features
  - type: fix
    section: Bug Fixes
  - type: chore
    section: Miscellaneous Changes
  - type: ci
    section: Miscellaneous Changes
  - type: docs
    section: Documentation
  - type: refactor
    section: Code Refactoring

# Extra files to bump version in (beyond the changelog)
# Type: list of file configuration objects
# Default: [] (empty list)
#
# Supported file types:
#   - yaml: YAML files (requires yaml-path with JSONPath)
#   - toml: TOML files (requires toml-path with JSONPath)
#   - json: JSON files (requires json-path with JSONPath)
#   - generic: Any text file (requires marker comments in the file)
#
# Examples:
extra-files: []
  # YAML file example (e.g., Helm charts, Kubernetes manifests):
  # - type: yaml
  #   path: charts/myapp/Chart.yaml
  #   yaml-path: $.version
  #   use-prefix: "v"  # Optional: include version prefix in this file

  # TOML file example (e.g., Python pyproject.toml, Rust Cargo.toml):
  # - type: toml
  #   path: pyproject.toml
  #   toml-path: $.project.version
  #   use-prefix: ""  # Optional: version prefix for this file

  # JSON file example (e.g., Node.js package.json):
  # - type: json
  #   path: package.json
  #   json-path: $.version
  #   use-prefix: ""  # Optional: version prefix for this file

  # Generic file example (any text file with marker comments):
  # - type: generic
  #   path: README.md
  #   use-prefix: "v"
  #
  # For generic files, add markers in your file:
  # <!--- contiamo-release-please-bump-start --->
  # Text containing version like: v1.2.3
  # <!--- contiamo-release-please-bump-end --->

# ============================================================================
# OPTIONAL CONFIGURATION (no defaults - typically use environment variables)
# ============================================================================

# GitHub authentication for pull request creation
# Type: object with token field
# Default: none (uses GITHUB_TOKEN environment variable if not specified)
#
# To configure:
# 1. Create a GitHub personal access token at:
#    https://github.com/settings/tokens
# 2. Required scopes:
#    - 'repo' (for private repositories)
#    - 'public_repo' (for public repositories)
# 3. Either set GITHUB_TOKEN environment variable (recommended) or uncomment below:
#
# github:
#   token: "ghp_xxx"  # GitHub personal access token

# Azure DevOps authentication for pull request creation
# Type: object with token field
# Default: none (uses AZURE_DEVOPS_TOKEN environment variable if not specified)
#
# To configure:
# 1. Create an Azure DevOps personal access token at:
#    https://dev.azure.com/{org}/_usersSettings/tokens
# 2. Required scopes:
#    - 'Code (Read & Write)'
# 3. Either set AZURE_DEVOPS_TOKEN environment variable (recommended) or uncomment below:
#
# azure:
#   token: "xxx"  # Azure DevOps personal access token
"""
    return template
