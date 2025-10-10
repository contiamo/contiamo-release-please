# Contiamo Release Please

Automated semantic versioning and release management tool based on conventional commits.

## Overview

`contiamo-release-please` analyses your git commit history and automatically determines the next semantic version for your project. It uses conventional commit messages to decide whether to bump the major, minor, or patch version.

## Features

- **Automatic version calculation** based on commit messages
- **Conventional commits support** with configurable type mappings
- **Breaking change detection** via `!` or `BREAKING CHANGE:` in commits
- **Flexible configuration** via YAML file
- **Git-native** - works with any git repository

## Installation

### Using UV (recommended)

```bash
cd contiamo-release-please
uv sync
```

### Using pip

```bash
pip install -e .
```

## Usage

### Basic Usage

Calculate the next version based on commits since the last tag:

```bash
contiamo-release-please next-version
```

This will output just the version number (e.g., `1.2.3`).

### Verbose Mode

Get detailed information about the analysis:

```bash
contiamo-release-please next-version --verbose
```

Example output:
```
Latest tag: v1.2.0
Current version: 1.2.0

Found 5 commits since last release

Commit summary:
  feat: 2 → minor bump
  fix: 2 → patch bump
  chore: 1 → patch bump

Determined release type: minor
Version bump: 1.2.0 → 1.3.0

1.3.0
```

### Custom Configuration

Use a different configuration file:

```bash
contiamo-release-please next-version --config my-config.yaml
```

## Configuration

Create a `contiamo-release-please.yaml` file in your repository root:

```yaml
release-rules:
  # Major version bump (breaking changes)
  major:
    - breaking

  # Minor version bump (new features)
  minor:
    - feat

  # Patch version bump (bug fixes and minor changes)
  patch:
    - fix
    - perf
    - chore
    - docs
    - refactor
    - style
    - test
    - ci
```

### Configuration Options

#### `release-rules`

Defines how commit types map to version bumps. Each section (`major`, `minor`, `patch`) contains a list of commit type prefixes.

- **major**: Commit types that trigger a major version bump (breaking changes)
- **minor**: Commit types that trigger a minor version bump (new features)
- **patch**: Commit types that trigger a patch version bump (bug fixes, etc.)

## Conventional Commits

This tool follows the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

### Examples

**Patch release:**
```
fix: resolve issue with API response
```

**Minor release:**
```
feat: add new authentication method
```

**Major release (breaking change):**
```
feat!: redesign authentication API

BREAKING CHANGE: The authentication flow has been completely redesigned.
```

Or:
```
feat: redesign authentication API

BREAKING CHANGE: The authentication flow has been completely redesigned.
```

### Breaking Changes

Breaking changes can be indicated in two ways:

1. **Using `!` after the type/scope:**
   ```
   feat!: breaking change
   feat(api)!: breaking API change
   ```

2. **Using `BREAKING CHANGE:` in the commit body:**
   ```
   feat: new feature

   BREAKING CHANGE: This changes the public API
   ```

## How It Works

1. **Find latest git tag** - Gets the most recent tag in the repository (or uses `0.1.0` if none exists)
2. **Get commits** - Retrieves all commits since that tag
3. **Parse commits** - Extracts the type from each conventional commit message
4. **Determine release type** - Finds the highest priority release type:
   - `major` > `minor` > `patch`
5. **Calculate version** - Bumps the appropriate version component

## Version Precedence

When multiple commit types are present, the tool uses the highest priority:

```
fix: bug fix           →  patch (1.2.3 → 1.2.4)
feat: new feature      →  minor (1.2.3 → 1.3.0)
feat!: breaking change →  major (1.2.3 → 2.0.0)
```

If you have commits with different types:
```
fix: bug 1
fix: bug 2
feat: new feature
```

Result: **minor** bump (because `feat` has higher priority than `fix`)

## Development

### Running Tests

```bash
uv run pytest
```

### Code Quality

```bash
# Run linter
uv run ruff check .

# Run type checker
uv run pyright
```

## Roadmap

### Phase 1 (Current)
- ✅ Version determination based on commit analysis
- ✅ Configurable release rules
- ✅ Breaking change detection

### Phase 2 (Future)
- 📝 Changelog generation
- 📝 Configurable changelog sections
- 📝 Customisable changelog templates

### Phase 3 (Future)
- 📝 Automatic version bumping in files (like `pyproject.toml`, `version.txt`)
- 📝 Git tag creation
- 📝 Release commit creation

## Requirements

- Python 3.14+
- Git
- UV (recommended) or pip

## Licence

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
