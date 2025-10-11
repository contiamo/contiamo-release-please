"""File version bumping for contiamo-release-please."""

import re
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


class GenericFileBumper(FileBumper):
    """Generic file version bumper using marker comments."""

    # Marker names
    START_MARKER = "contiamo-release-please-bump-start"
    END_MARKER = "contiamo-release-please-bump-end"

    # Version regex pattern (matches semantic versions with optional 'v' prefix)
    VERSION_PATTERN = re.compile(r"\bv?\d+\.\d+\.\d+\b")

    def bump_version(
        self, file_path: Path, path_spec: str, version: str
    ) -> None:
        """Bump version in a generic file using marker comments.

        Scans the file for marker pairs (contiamo-release-please-bump-start/end)
        and replaces version strings between them with the new version.

        Args:
            file_path: Path to the file
            path_spec: Not used for generic files (kept for interface compatibility)
            version: Version string to set (should already include prefix if needed)

        Raises:
            FileBumperError: If file not found, no markers found, or write fails
        """
        if not file_path.exists():
            raise FileBumperError(f"File not found: {file_path}")

        try:
            # Read file
            with open(file_path, "r") as f:
                lines = f.readlines()

            # Track state and modified lines
            inside_block = False
            found_markers = False
            modified_lines = []
            versions_replaced = 0

            for line in lines:
                # Check for start marker
                if self.START_MARKER in line:
                    inside_block = True
                    found_markers = True
                    modified_lines.append(line)
                    continue

                # Check for end marker
                if self.END_MARKER in line:
                    inside_block = False
                    modified_lines.append(line)
                    continue

                # If inside block, replace version strings
                if inside_block:
                    # Replace all version occurrences on this line
                    original_line = line
                    line = self.VERSION_PATTERN.sub(version, line)
                    if line != original_line:
                        versions_replaced += 1

                modified_lines.append(line)

            # Validate markers were found
            if not found_markers:
                raise FileBumperError(
                    f"No '{self.START_MARKER}' markers found in {file_path}. "
                    f"Add marker comments to indicate where versions should be updated."
                )

            # Validate at least one version was replaced
            if versions_replaced == 0:
                raise FileBumperError(
                    f"No version strings found between markers in {file_path}"
                )

            # Write back to file
            with open(file_path, "w") as f:
                f.writelines(modified_lines)

        except FileBumperError:
            # Re-raise our own errors
            raise
        except Exception as e:
            raise FileBumperError(f"Failed to bump version in {file_path}: {e}")


def get_bumper_for_type(file_type: str) -> FileBumper:
    """Get the appropriate bumper for a file type.

    Args:
        file_type: File type (e.g., 'yaml', 'toml', 'generic')

    Returns:
        FileBumper instance for the type

    Raises:
        FileBumperError: If file type is not supported
    """
    bumpers = {
        "yaml": YamlFileBumper(),
        "toml": TomlFileBumper(),
        "generic": GenericFileBumper(),
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
        elif file_type == "generic":
            # Generic files don't need a path_spec (uses markers instead)
            path_spec = ""
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
