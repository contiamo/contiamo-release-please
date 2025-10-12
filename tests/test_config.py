"""Tests for configuration generation and loading."""

import tempfile
from pathlib import Path

import pytest
import yaml

from contiamo_release_please.config import (
    ReleaseConfig,
    generate_config_template,
)


def test_generate_config_template_returns_string():
    """Test that generate_config_template returns a string."""
    template = generate_config_template()
    assert isinstance(template, str)
    assert len(template) > 100


def test_generate_config_template_is_valid_yaml():
    """Test that generated template is valid YAML."""
    template = generate_config_template()

    # Parse the YAML to ensure it's valid
    try:
        config_dict = yaml.safe_load(template)
        assert isinstance(config_dict, dict)
    except yaml.YAMLError as e:
        pytest.fail(f"Generated template is not valid YAML: {e}")


def test_generate_config_template_contains_required_parameters():
    """Test that generated template contains required parameters."""
    template = generate_config_template()
    config_dict = yaml.safe_load(template)

    # Check required parameter
    assert "release-rules" in config_dict
    assert isinstance(config_dict["release-rules"], dict)

    # Check that at least major/minor/patch exist
    rules = config_dict["release-rules"]
    assert any(key in rules for key in ["major", "minor", "patch"])


def test_generate_config_template_contains_optional_parameters():
    """Test that generated template contains optional parameters with defaults."""
    template = generate_config_template()
    config_dict = yaml.safe_load(template)

    # Check optional parameters with defaults
    assert "version-prefix" in config_dict
    assert "changelog-path" in config_dict
    assert "source-branch" in config_dict
    assert "git" in config_dict
    assert "changelog-sections" in config_dict
    assert "extra-files" in config_dict


def test_generate_config_template_shows_default_values():
    """Test that generated template shows correct default values."""
    template = generate_config_template()
    config_dict = yaml.safe_load(template)

    # Verify default values match those in ReleaseConfig
    assert config_dict["version-prefix"] == ""
    assert config_dict["changelog-path"] == "CHANGELOG.md"
    assert config_dict["source-branch"] == "main"
    assert config_dict["git"]["user-name"] == "Contiamo Release Bot"
    assert config_dict["git"]["user-email"] == "contiamo-release@ctmo.io"


def test_generate_config_template_includes_documentation():
    """Test that generated template includes comments/documentation."""
    template = generate_config_template()

    # Check for key documentation markers
    assert "# REQUIRED" in template
    assert "# Default:" in template
    assert "# Type:" in template
    assert "# Optional:" in template or "OPTIONAL" in template


def test_generate_config_template_includes_all_commit_types():
    """Test that generated template includes common commit types."""
    template = generate_config_template()
    config_dict = yaml.safe_load(template)

    rules = config_dict["release-rules"]

    # Collect all commit types from all rules
    all_types = set()
    for release_type in ["major", "minor", "patch"]:
        if release_type in rules and isinstance(rules[release_type], list):
            all_types.update(rules[release_type])

    # Check for common conventional commit types
    expected_types = ["feat", "fix", "chore", "docs", "breaking"]
    for commit_type in expected_types:
        assert commit_type in all_types, (
            f"Expected commit type '{commit_type}' not in generated config"
        )


def test_generate_config_template_includes_changelog_sections():
    """Test that generated template includes default changelog sections."""
    template = generate_config_template()
    config_dict = yaml.safe_load(template)

    assert "changelog-sections" in config_dict
    sections = config_dict["changelog-sections"]
    assert isinstance(sections, list)
    assert len(sections) > 0

    # Check format of sections
    for section in sections:
        assert "type" in section
        assert "section" in section
        assert isinstance(section["type"], str)
        assert isinstance(section["section"], str)


def test_generate_config_template_includes_extra_files_examples():
    """Test that generated template includes examples for extra-files."""
    template = generate_config_template()

    # Check for file type examples in comments
    assert "yaml" in template.lower()
    assert "toml" in template.lower()
    assert "generic" in template.lower()
    assert "yaml-path" in template or "yaml_path" in template
    assert "toml-path" in template or "toml_path" in template
    assert "use-prefix" in template


def test_generated_config_can_be_loaded():
    """Test that generated config can be successfully loaded by ReleaseConfig."""
    template = generate_config_template()

    # Write to temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as temp_file:
        temp_file.write(template)
        temp_file_path = temp_file.name

    try:
        # Load the config - this should not raise any errors
        config = ReleaseConfig(temp_file_path)

        # Verify it loaded correctly
        assert config is not None
        assert config.get_version_prefix() == ""
        assert config.get_changelog_path() == "CHANGELOG.md"
        assert config.get_source_branch() == "main"

    finally:
        # Clean up
        Path(temp_file_path).unlink()


def test_generated_config_has_all_release_types():
    """Test that generated config has all three release types."""
    template = generate_config_template()
    config_dict = yaml.safe_load(template)

    rules = config_dict["release-rules"]
    assert "major" in rules
    assert "minor" in rules
    assert "patch" in rules


def test_generated_config_extra_files_is_empty_list():
    """Test that generated config has empty extra-files by default."""
    template = generate_config_template()
    config_dict = yaml.safe_load(template)

    assert "extra-files" in config_dict
    assert config_dict["extra-files"] == []


def test_generated_config_does_not_include_tokens_by_default():
    """Test that generated config does not include actual tokens (only commented examples)."""
    template = generate_config_template()
    config_dict = yaml.safe_load(template)

    # Tokens should be commented out, not in the parsed YAML
    assert "github" not in config_dict or "token" not in config_dict.get("github", {})
    assert "azure" not in config_dict or "token" not in config_dict.get("azure", {})


def test_generated_config_includes_marker_documentation():
    """Test that generated config includes documentation about marker comments for generic files."""
    template = generate_config_template()

    # Check for marker documentation
    assert "contiamo-release-please-bump-start" in template
    assert "contiamo-release-please-bump-end" in template
