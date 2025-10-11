# Contiamo Release Please

Automated semantic versioning and release management based on conventional commits.

## TL;DR

1. Create release PR (analyses commits, updates changelog, bumps versions):

```bash
contiamo-release-please release -v
```

2. Review and merge the PR

3. Create and push git tag:

```bash
contiamo-release-please tag-release -v
```

## Installation

<!--- contiamo-release-please-bump-start --->

Install using uv:

```bash
uv tool install git+ssh://git@github.com/contiamo/contiamo-release-please.git@v0.3.0
```

To upgrade to a specific version, use the `--force` flag:

```bash
uv tool install --force git+ssh://git@github.com/contiamo/contiamo-release-please.git@v0.3.0
```

<!--- contiamo-release-please-bump-end --->

## GitHub Actions Example

```yaml
name: Release

on:
  push:
    branches:
      - main

jobs:
  release-pr:
    name: Create Release PR
    runs-on: ubuntu-latest
    # Run on all pushes EXCEPT release PR merges
    if: "!startsWith(github.event.head_commit.message, 'chore(main): update files for release')"
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Required: Fetch all history for commit analysis

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Install tool
        run: uv tool install git+ssh://git@github.com/contiamo/contiamo-release-please.git@v0.1.1

      - name: Create release PR
        run: contiamo-release-please release -v
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  tag-release:
    name: Create Git Tag
    runs-on: ubuntu-latest
    # Run ONLY on release PR merges
    if: "startsWith(github.event.head_commit.message, 'chore(main): update files for release')"
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Required: Fetch all history for tags

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Install tool
        run: uv tool install git+ssh://git@github.com/contiamo/contiamo-release-please.git@v0.1.1

      - name: Create and push tag
        run: contiamo-release-please tag-release -v
```

## Features

### Automatic Version Calculation

```bash
# Show next version
contiamo-release-please next-version -v
```

### Changelog Generation

```bash
# Generate changelog (dry-run)
contiamo-release-please generate-changelog --dry-run -v
```

### File Version Bumping

Bump version in `pyproject.toml`, Helm charts, or any YAML/TOML file:

```yaml
# contiamo-release-please.yaml
extra-files:
  - type: toml
    path: pyproject.toml
    toml-path: $.project.version
  - type: yaml
    path: charts/myapp/Chart.yaml
    yaml-path: $.version
```

```bash
contiamo-release-please bump-files -v
```

### Pull Request Creation

Automatically creates PRs on GitHub or Azure DevOps:

```bash
# GitHub (auto-detected)
export GITHUB_TOKEN="ghp_xxx"
contiamo-release-please release -v

# Azure DevOps
export AZURE_DEVOPS_TOKEN="xxx"
contiamo-release-please release --git-host azure -v
```

### GitHub Release Creation

When using GitHub, releases are automatically created when you run `tag-release`:

```bash
# After merging the release PR, create tag and GitHub release
export GITHUB_TOKEN="ghp_xxx"
contiamo-release-please tag-release -v
```

The GitHub release will include:
- Tag name and release name (e.g., `v1.2.3`)
- Full changelog entry from `CHANGELOG.md` as the release body
- Link to the release page

This works automatically for GitHub repositories (detected from remote URL).

## Configuration

Create `contiamo-release-please.yaml` in your repository root:

```yaml
# Optional: Version prefix (default: "")
version-prefix: "v"

release-rules:
  major:
    - breaking
  minor:
    - feat
  patch:
    - fix
    - chore
    - docs
# Optional: Git identity for commits (default shown)
# git:
#   user-name: "Contiamo Release Bot"
#   user-email: "contiamo-release@ctmo.io"

# Optional: GitHub PR creation
# github:
#   token: "ghp_xxx"  # Or use GITHUB_TOKEN env var

# Optional: Azure DevOps PR creation
# azure:
#   token: "xxx"  # Or use AZURE_DEVOPS_TOKEN env var
```

## Conventional Commits

Use [conventional commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>
```

**Examples:**

```bash
fix: resolve authentication bug              # patch bump
feat: add user profile page                  # minor bump
feat!: redesign authentication API           # major bump
```

**Breaking changes:**

```bash
feat!: breaking change
# or
feat: new feature

BREAKING CHANGE: This changes the API
```

## Important Notes

### Automatic Tag Fetching

The tool automatically fetches tags from the remote repository before determining the next version. This ensures:
- ✅ Correct version calculation even with shallow clones in CI
- ✅ Up-to-date results in local development without manual `git fetch --tags`
- ✅ Reliable behaviour in all environments

**Note:** For CI workflows using `actions/checkout`, we still recommend `fetch-depth: 0` to fetch full commit history for accurate commit analysis.

## Requirements

- Python 3.12+
- Git
- Configured `contiamo-release-please.yaml`
- Network access to remote repository (for tag fetching)

## Licence

MIT
