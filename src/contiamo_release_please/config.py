"""Configuration loading and parsing for contiamo-release-please."""

import os
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


def load_config(config_path: str | Path = "contiamo-release-please.yaml") -> ReleaseConfig:
    """Load release configuration from file.

    Args:
        config_path: Path to configuration file

    Returns:
        Loaded configuration object

    Raises:
        ConfigError: If config file is invalid or cannot be loaded
    """
    return ReleaseConfig(config_path)
