# Contiamo Release Please

It's exactly like Google's Release-Please but for any flavour of git. Not just Github.
Provider agnostic Release Please.

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
uv tool install git+ssh://git@github.com/contiamo/contiamo-release-please.git@v0.10.2
```

To upgrade to a specific version, use the `--force` flag:

```bash
uv tool install --force git+ssh://git@github.com/contiamo/contiamo-release-please.git@v0.10.2
```

<!--- contiamo-release-please-bump-end --->

## Shell Completion

Enable tab completion for commands, options, and arguments in your shell:

**Bash** (requires Bash 4.4+):

```bash
contiamo-release-please completion bash > ~/.contiamo-release-please-completion.bash
echo ". ~/.contiamo-release-please-completion.bash" >> ~/.bashrc
```

**Zsh**:

```bash
contiamo-release-please completion zsh > ~/.contiamo-release-please-completion.zsh
echo ". ~/.contiamo-release-please-completion.zsh" >> ~/.zshrc
```

**Fish**:

```bash
mkdir -p ~/.config/fish/completions
contiamo-release-please completion fish > ~/.config/fish/completions/contiamo-release-please.fish
```

Restart your shell or source the completion script to activate. You can then use `Tab` to complete commands and options:

```bash
contiamo-release-please <Tab>
contiamo-release-please release --<Tab>
```

## Quick Start Example (GitHub Actions)

```yaml
name: Contiamo Release Please

on:
  push:
    branches:
      - main

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Required: Fetch all history for commit analysis

      - uses: contiamo/contiamo-release-please@main
        id: release
        with:
          token: ${{ secrets.CONTIAMO_CI_TOKEN }}
```

**How it works:**

- The action automatically detects whether to create a release PR or create a tag
- On regular pushes: creates/updates a release PR with version bumps and changelog
- On release PR merge: creates git tag and GitHub release
- No need for conditional job logic - the action handles it internally

**Using Azure Pipelines?** See the [CI/CD Setup Guide](CI_SETUP.md) for a complete Azure Pipelines example.

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

Bump version in `pyproject.toml`, Helm charts, `package.json`, or any YAML/TOML/JSON file. For other text files, use marker comments:

```yaml
# contiamo-release-please.yaml
extra-files:
  - type: toml
    path: pyproject.toml
    toml-path: $.project.version
  - type: yaml
    path: charts/myapp/Chart.yaml
    yaml-path: $.version
  - type: json
    path: package.json
    json-path: $.version
  - type: generic
    path: README.md
    use-prefix: "v"
    # For generic files, add markers in your file:
    # <!--- contiamo-release-please-bump-start --->
    # Version: v0.10.2
    # <!--- contiamo-release-please-bump-end --->
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

### Generate Configuration Template

Quickly bootstrap your configuration using the built-in generator:

```bash
# Generate a complete configuration template with all parameters documented
contiamo-release-please generate-config > contiamo-release-please.yaml
```

The generated template includes:

- All required and optional parameters with inline documentation
- Default values for optional parameters
- Examples for complex configurations (extra-files, changelog sections, etc.)
- Comments explaining what each parameter does

### Manual Configuration

Alternatively, create `contiamo-release-please.yaml` in your repository root:

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

## Documentation

- **[CI/CD Setup Guide](CI_SETUP.md)** - Comprehensive guide for GitHub Actions, GitLab CI, Azure Pipelines, and other platforms
- **[Authentication Setup](docs/AUTHENTICATION.md)** - Token configuration for GitHub and Azure DevOps
- **Configuration** - Run `contiamo-release-please generate-config` to see all available options

## Requirements

- Python 3.12+
- Git
- Configured `contiamo-release-please.yaml`
- Network access to remote repository (for tag fetching)

## Licence

MIT
