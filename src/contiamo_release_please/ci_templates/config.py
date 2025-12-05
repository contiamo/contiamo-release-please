"""Configuration template generation for Contiamo Release Please."""


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
version-prefix: "v"

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

# GitLab authentication for merge request creation
# Type: object with token field
# Default: none (uses GITLAB_TOKEN environment variable if not specified)
#
# To configure:
# 1. Create a GitLab personal access token at:
#    Settings → Access Tokens (for gitlab.com)
#    Or: https://{your-gitlab-instance}/-/profile/personal_access_tokens
# 2. Required scopes:
#    - 'api' (full API access)
# 3. Either set GITLAB_TOKEN environment variable (recommended) or uncomment below:
#
# gitlab:
#   token: "glpat-xxx"  # GitLab personal access token
#
# Note: Works with both gitlab.com and self-hosted GitLab instances
"""
    return template
