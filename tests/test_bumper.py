"""Tests for file version bumping."""

import tempfile
from pathlib import Path

import pytest
import tomlkit
import yaml

from contiamo_release_please.bumper import (
    FileBumperError,
    TomlFileBumper,
    YamlFileBumper,
    bump_files,
    get_bumper_for_type,
)


def test_get_bumper_for_yaml():
    """Test getting YAML bumper."""
    bumper = get_bumper_for_type("yaml")
    assert isinstance(bumper, YamlFileBumper)


def test_get_bumper_for_unsupported_type():
    """Test getting bumper for unsupported type."""
    with pytest.raises(FileBumperError, match="Unsupported file type: json"):
        get_bumper_for_type("json")


def test_yaml_bumper_simple_path():
    """Test bumping version in YAML with simple path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_file = Path(tmpdir) / "test.yaml"

        # Create test YAML
        data = {"version": "0.1.0", "name": "test"}
        with open(yaml_file, "w") as f:
            yaml.safe_dump(data, f)

        # Bump version
        bumper = YamlFileBumper()
        bumper.bump_version(yaml_file, "$.version", "1.2.3")

        # Verify
        with open(yaml_file, "r") as f:
            result = yaml.safe_load(f)

        assert result["version"] == "1.2.3"
        assert result["name"] == "test"  # Other fields unchanged


def test_yaml_bumper_nested_path():
    """Test bumping version in YAML with nested path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_file = Path(tmpdir) / "test.yaml"

        # Create test YAML
        data = {"project": {"version": "0.1.0", "name": "test"}}
        with open(yaml_file, "w") as f:
            yaml.safe_dump(data, f)

        # Bump version
        bumper = YamlFileBumper()
        bumper.bump_version(yaml_file, "$.project.version", "1.2.3")

        # Verify
        with open(yaml_file, "r") as f:
            result = yaml.safe_load(f)

        assert result["project"]["version"] == "1.2.3"
        assert result["project"]["name"] == "test"


def test_yaml_bumper_helm_chart():
    """Test bumping version in Helm Chart.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        chart_file = Path(tmpdir) / "Chart.yaml"

        # Create test Helm chart
        data = {
            "apiVersion": "v2",
            "name": "testchart",
            "description": "A test chart",
            "type": "application",
            "version": "0.1.0",
            "appVersion": "v0.1.0",
        }
        with open(chart_file, "w") as f:
            yaml.safe_dump(data, f)

        # Bump chart version
        bumper = YamlFileBumper()
        bumper.bump_version(chart_file, "$.version", "1.2.3")

        # Verify
        with open(chart_file, "r") as f:
            result = yaml.safe_load(f)

        assert result["version"] == "1.2.3"
        assert result["appVersion"] == "v0.1.0"  # Unchanged


def test_yaml_bumper_file_not_found():
    """Test error when file doesn't exist."""
    bumper = YamlFileBumper()

    with pytest.raises(FileBumperError, match="File not found"):
        bumper.bump_version(Path("/nonexistent/file.yaml"), "$.version", "1.0.0")


def test_yaml_bumper_invalid_path():
    """Test error when JSONPath doesn't match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_file = Path(tmpdir) / "test.yaml"

        # Create test YAML
        data = {"version": "0.1.0"}
        with open(yaml_file, "w") as f:
            yaml.safe_dump(data, f)

        bumper = YamlFileBumper()

        with pytest.raises(FileBumperError, match="Path '.*' not found"):
            bumper.bump_version(yaml_file, "$.nonexistent", "1.0.0")


def test_bump_files_with_prefix():
    """Test bumping files with version prefix."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_root = Path(tmpdir)
        chart_file = git_root / "Chart.yaml"

        # Create test file
        data = {"version": "0.1.0", "appVersion": "v0.1.0"}
        with open(chart_file, "w") as f:
            yaml.safe_dump(data, f)

        # Configure with prefix
        extra_files = [
            {"type": "yaml", "path": "Chart.yaml", "yaml-path": "$.version"},
            {
                "type": "yaml",
                "path": "Chart.yaml",
                "yaml-path": "$.appVersion",
                "use-prefix": "v",
            },
        ]

        # Bump files
        results = bump_files(extra_files, "1.2.3", git_root, dry_run=False)

        # Verify results
        assert len(results["updated"]) == 2
        assert len(results["errors"]) == 0
        assert "Chart.yaml:$.version → 1.2.3" in results["updated"]
        assert "Chart.yaml:$.appVersion → v1.2.3" in results["updated"]

        # Verify file contents
        with open(chart_file, "r") as f:
            result = yaml.safe_load(f)

        assert result["version"] == "1.2.3"
        assert result["appVersion"] == "v1.2.3"


def test_bump_files_dry_run():
    """Test dry-run mode doesn't modify files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_root = Path(tmpdir)
        chart_file = git_root / "Chart.yaml"

        # Create test file
        data = {"version": "0.1.0"}
        with open(chart_file, "w") as f:
            yaml.safe_dump(data, f)

        extra_files = [
            {"type": "yaml", "path": "Chart.yaml", "yaml-path": "$.version"}
        ]

        # Bump files in dry-run mode
        results = bump_files(extra_files, "1.2.3", git_root, dry_run=True)

        # Verify results reported
        assert len(results["updated"]) == 1
        assert len(results["errors"]) == 0

        # Verify file NOT modified
        with open(chart_file, "r") as f:
            result = yaml.safe_load(f)

        assert result["version"] == "0.1.0"  # Still original version


def test_bump_files_missing_type():
    """Test error handling for missing type field."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_root = Path(tmpdir)

        extra_files = [{"path": "Chart.yaml", "yaml-path": "$.version"}]

        results = bump_files(extra_files, "1.2.3", git_root, dry_run=False)

        assert len(results["updated"]) == 0
        assert len(results["errors"]) == 1
        assert "Missing 'type' field" in results["errors"][0]


def test_bump_files_missing_path():
    """Test error handling for missing path field."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_root = Path(tmpdir)

        extra_files = [{"type": "yaml", "yaml-path": "$.version"}]

        results = bump_files(extra_files, "1.2.3", git_root, dry_run=False)

        assert len(results["updated"]) == 0
        assert len(results["errors"]) == 1
        assert "Missing 'path' field" in results["errors"][0]


def test_bump_files_missing_yaml_path():
    """Test error handling for missing yaml-path field."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_root = Path(tmpdir)

        extra_files = [{"type": "yaml", "path": "Chart.yaml"}]

        results = bump_files(extra_files, "1.2.3", git_root, dry_run=False)

        assert len(results["updated"]) == 0
        assert len(results["errors"]) == 1
        assert "Missing 'yaml-path'" in results["errors"][0]


def test_bump_files_file_not_found():
    """Test error handling when file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_root = Path(tmpdir)

        extra_files = [
            {
                "type": "yaml",
                "path": "nonexistent.yaml",
                "yaml-path": "$.version",
            }
        ]

        results = bump_files(extra_files, "1.2.3", git_root, dry_run=False)

        assert len(results["updated"]) == 0
        assert len(results["errors"]) == 1
        assert "File not found" in results["errors"][0]


def test_bump_files_multiple_files():
    """Test bumping multiple different files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_root = Path(tmpdir)
        file1 = git_root / "chart1.yaml"
        file2 = git_root / "chart2.yaml"

        # Create test files
        for f in [file1, file2]:
            data = {"version": "0.1.0"}
            with open(f, "w") as fh:
                yaml.safe_dump(data, fh)

        extra_files = [
            {"type": "yaml", "path": "chart1.yaml", "yaml-path": "$.version"},
            {"type": "yaml", "path": "chart2.yaml", "yaml-path": "$.version"},
        ]

        results = bump_files(extra_files, "1.2.3", git_root, dry_run=False)

        assert len(results["updated"]) == 2
        assert len(results["errors"]) == 0

        # Verify both files updated
        for f in [file1, file2]:
            with open(f, "r") as fh:
                result = yaml.safe_load(fh)
            assert result["version"] == "1.2.3"


# TOML File Bumper Tests


def test_get_bumper_for_toml():
    """Test getting TOML bumper."""
    bumper = get_bumper_for_type("toml")
    assert isinstance(bumper, TomlFileBumper)


def test_toml_bumper_simple_path():
    """Test bumping version in TOML with simple path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_file = Path(tmpdir) / "test.toml"

        # Create test TOML
        data = {"version": "0.1.0", "name": "test"}
        with open(toml_file, "w") as f:
            tomlkit.dump(data, f)

        # Bump version
        bumper = TomlFileBumper()
        bumper.bump_version(toml_file, "$.version", "1.2.3")

        # Verify
        with open(toml_file, "r") as f:
            result = tomlkit.load(f)

        assert result["version"] == "1.2.3"
        assert result["name"] == "test"  # Other fields unchanged


def test_toml_bumper_nested_path():
    """Test bumping version in TOML with nested path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_file = Path(tmpdir) / "pyproject.toml"

        # Create test pyproject.toml
        data = {"project": {"version": "0.1.0", "name": "test"}}
        with open(toml_file, "w") as f:
            tomlkit.dump(data, f)

        # Bump version
        bumper = TomlFileBumper()
        bumper.bump_version(toml_file, "$.project.version", "1.2.3")

        # Verify
        with open(toml_file, "r") as f:
            result = tomlkit.load(f)

        assert result["project"]["version"] == "1.2.3"  # type: ignore[index]
        assert result["project"]["name"] == "test"  # type: ignore[index]


def test_toml_bumper_preserves_formatting():
    """Test that TOML bumper preserves comments and formatting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_file = Path(tmpdir) / "test.toml"

        # Create TOML with comments
        toml_content = """# This is a comment
[project]
name = "test"
# Version comment
version = "0.1.0"
"""
        with open(toml_file, "w") as f:
            f.write(toml_content)

        # Bump version
        bumper = TomlFileBumper()
        bumper.bump_version(toml_file, "$.project.version", "1.2.3")

        # Read result
        with open(toml_file, "r") as f:
            result_content = f.read()

        # Verify version updated and comments preserved
        assert "1.2.3" in result_content
        assert "# This is a comment" in result_content
        assert "# Version comment" in result_content


def test_toml_bumper_file_not_found():
    """Test error when TOML file doesn't exist."""
    bumper = TomlFileBumper()

    with pytest.raises(FileBumperError, match="File not found"):
        bumper.bump_version(Path("/nonexistent/file.toml"), "$.version", "1.0.0")


def test_toml_bumper_invalid_path():
    """Test error when JSONPath doesn't match in TOML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_file = Path(tmpdir) / "test.toml"

        # Create test TOML
        data = {"version": "0.1.0"}
        with open(toml_file, "w") as f:
            tomlkit.dump(data, f)

        bumper = TomlFileBumper()

        with pytest.raises(FileBumperError, match="Path '.*' not found"):
            bumper.bump_version(toml_file, "$.nonexistent", "1.0.0")


def test_bump_files_toml_with_prefix():
    """Test bumping TOML files with version prefix."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_root = Path(tmpdir)
        toml_file = git_root / "pyproject.toml"

        # Create test file
        data = {"project": {"version": "0.1.0"}}
        with open(toml_file, "w") as f:
            tomlkit.dump(data, f)

        # Configure with prefix
        extra_files = [
            {
                "type": "toml",
                "path": "pyproject.toml",
                "toml-path": "$.project.version",
                "use-prefix": "v",
            }
        ]

        # Bump files
        results = bump_files(extra_files, "1.2.3", git_root, dry_run=False)

        # Verify results
        assert len(results["updated"]) == 1
        assert len(results["errors"]) == 0
        assert "pyproject.toml:$.project.version → v1.2.3" in results["updated"]

        # Verify file contents
        with open(toml_file, "r") as f:
            result = tomlkit.load(f)

        assert result["project"]["version"] == "v1.2.3"  # type: ignore[index]


def test_bump_files_missing_toml_path():
    """Test error handling for missing toml-path field."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_root = Path(tmpdir)

        extra_files = [{"type": "toml", "path": "pyproject.toml"}]

        results = bump_files(extra_files, "1.2.3", git_root, dry_run=False)

        assert len(results["updated"]) == 0
        assert len(results["errors"]) == 1
        assert "Missing 'toml-path'" in results["errors"][0]
