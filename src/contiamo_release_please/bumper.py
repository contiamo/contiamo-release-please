"""File version bumping for contiamo-release-please."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import tomlkit
import yaml
from jsonpath_ng import parse


class FileBumperError(Exception):
    """Raised when file bumping fails."""

    pass


class FileBumper(ABC):
    """Abstract base class for file version bumpers."""

    @abstractmethod
    def bump_version(
        self, file_path: Path, path_spec: str, version: str
    ) -> None:
        """Bump version in a file.

        Args:
            file_path: Path to the file to update
            path_spec: Path specification (e.g., JSONPath for YAML)
            version: Version string to set

        Raises:
            FileBumperError: If bumping fails
        """
        pass


class YamlFileBumper(FileBumper):
    """YAML file version bumper using JSONPath."""

    def bump_version(
        self, file_path: Path, path_spec: str, version: str
    ) -> None:
        """Bump version in a YAML file.

        Args:
            file_path: Path to the YAML file
            path_spec: JSONPath expression (e.g., '$.version', '$.project.version')
            version: Version string to set

        Raises:
            FileBumperError: If file not found, invalid path, or write fails
        """
        if not file_path.exists():
            raise FileBumperError(f"File not found: {file_path}")

        try:
            # Read YAML file
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)

            if data is None:
                raise FileBumperError(f"Empty or invalid YAML file: {file_path}")

            # Parse JSONPath
            jsonpath_expr = parse(path_spec)

            # Find and update the value
            matches = jsonpath_expr.find(data)
            if not matches:
                raise FileBumperError(
                    f"Path '{path_spec}' not found in {file_path}"
                )

            # Update all matching paths
            jsonpath_expr.update(data, version)

            # Write back to file
            with open(file_path, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        except yaml.YAMLError as e:
            raise FileBumperError(f"YAML parsing error in {file_path}: {e}")
        except Exception as e:
            raise FileBumperError(f"Failed to bump version in {file_path}: {e}")


class TomlFileBumper(FileBumper):
    """TOML file version bumper using JSONPath."""

    def bump_version(
        self, file_path: Path, path_spec: str, version: str
    ) -> None:
        """Bump version in a TOML file.

        Args:
            file_path: Path to the TOML file
            path_spec: JSONPath expression (e.g., '$.project.version')
            version: Version string to set

        Raises:
            FileBumperError: If file not found, invalid path, or write fails
        """
        if not file_path.exists():
            raise FileBumperError(f"File not found: {file_path}")

        try:
            # Read TOML file (preserves formatting and comments)
            with open(file_path, "r") as f:
                data = tomlkit.load(f)

            # Parse JSONPath
            jsonpath_expr = parse(path_spec)

            # Find and update the value
            matches = jsonpath_expr.find(data)
            if not matches:
                raise FileBumperError(
                    f"Path '{path_spec}' not found in {file_path}"
                )

            # Update all matching paths
            jsonpath_expr.update(data, version)

            # Write back to file (preserves formatting and comments)
            with open(file_path, "w") as f:
                tomlkit.dump(data, f)

        except Exception as e:
            # Catch all TOML errors (tomlkit uses various exception types)
            if "toml" in str(type(e)).lower():
                raise FileBumperError(f"TOML parsing error in {file_path}: {e}")
            raise FileBumperError(f"Failed to bump version in {file_path}: {e}")


def get_bumper_for_type(file_type: str) -> FileBumper:
    """Get the appropriate bumper for a file type.

    Args:
        file_type: File type (e.g., 'yaml', 'toml')

    Returns:
        FileBumper instance for the type

    Raises:
        FileBumperError: If file type is not supported
    """
    bumpers = {
        "yaml": YamlFileBumper(),
        "toml": TomlFileBumper(),
    }

    bumper = bumpers.get(file_type)
    if not bumper:
        raise FileBumperError(
            f"Unsupported file type: {file_type}. Supported types: {', '.join(bumpers.keys())}"
        )

    return bumper


def bump_files(
    extra_files: list[dict[str, Any]],
    version: str,
    git_root: Path,
    dry_run: bool = False,
) -> dict[str, list[str]]:
    """Bump version in multiple files according to configuration.

    Args:
        extra_files: List of file configurations from config
        version: Version string (without prefix)
        git_root: Git repository root path
        dry_run: If True, don't write changes

    Returns:
        Dictionary with 'updated' and 'errors' lists

    Raises:
        FileBumperError: If configuration is invalid
    """
    results = {"updated": [], "errors": []}

    for file_config in extra_files:
        # Validate required fields
        if "type" not in file_config:
            results["errors"].append("Missing 'type' field in file configuration")
            continue

        if "path" not in file_config:
            results["errors"].append("Missing 'path' field in file configuration")
            continue

        file_type = file_config["type"]
        file_path = git_root / file_config["path"]

        # Get path specification based on file type
        if file_type == "yaml":
            path_spec = file_config.get("yaml-path")
            if not path_spec:
                results["errors"].append(
                    f"Missing 'yaml-path' for YAML file: {file_config['path']}"
                )
                continue
        elif file_type == "toml":
            path_spec = file_config.get("toml-path")
            if not path_spec:
                results["errors"].append(
                    f"Missing 'toml-path' for TOML file: {file_config['path']}"
                )
                continue
        else:
            results["errors"].append(f"Unsupported file type: {file_type}")
            continue

        # Apply prefix if specified
        use_prefix = file_config.get("use-prefix", "")
        versioned_value = f"{use_prefix}{version}" if use_prefix else version

        try:
            if not dry_run:
                bumper = get_bumper_for_type(file_type)
                bumper.bump_version(file_path, path_spec, versioned_value)

            results["updated"].append(
                f"{file_config['path']}:{path_spec} → {versioned_value}"
            )

        except FileBumperError as e:
            results["errors"].append(str(e))

    return results
