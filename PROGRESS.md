# Contiamo Release Please - Development Progress

## Project Status: Phase 1 Complete ✅

### What's Been Implemented

#### Phase 1: Version Determination (COMPLETE)

**Core Functionality:**
1. ✅ Git repository root detection via `git rev-parse --show-toplevel`
2. ✅ Latest tag detection via `git describe --tags --abbrev=0` (branch-aware)
3. ✅ Commit analysis since last tag using conventional commit format
4. ✅ Release type determination (major/minor/patch) based on commit types
5. ✅ Semantic version bumping
6. ✅ YAML configuration with customisable release rules
7. ✅ Version prefix support (e.g., "v" for v1.2.0)
8. ✅ Reusable `calculate_next_version()` function for future features

**Project Structure:**
```
contiamo-release-please/
├── .python-version (3.12)
├── .gitignore
├── pyproject.toml
├── README.md
├── contiamo-release-please.yaml (example config)
├── src/
│   └── contiamo_release_please/
│       ├── __init__.py
│       ├── main.py           # CLI + calculate_next_version() function
│       ├── config.py          # YAML config loading + version_prefix
│       ├── git.py             # Git operations (root detection, tags, commits)
│       ├── analyser.py        # Commit analysis (UK spelling)
│       └── version.py         # Semver bumping logic
└── tests/
    ├── __init__.py
    └── test_analyser.py (17 tests, all passing)
```

### Configuration File

**Location:** `{git_root}/contiamo-release-please.yaml`

The tool automatically finds the git repository root and looks for the config there.

**Current Config Structure:**
```yaml
# Optional: Version prefix (e.g., "v" for v1.2.0, "" for 1.2.0)
version-prefix: "v"

release-rules:
  major:
    - breaking
  minor:
    - feat
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

### Key Implementation Details

#### Git Root Detection
- Uses `git rev-parse --show-toplevel` to find repo root
- All git operations run from repo root automatically
- Config file always loaded from `{git_root}/contiamo-release-please.yaml`
- Works correctly from any subdirectory within the repo

#### Tag Detection
- Uses `git describe --tags --abbrev=0` (not `git tag --sort=-v:refname`)
- This ensures we only get tags reachable from current branch
- Strips common prefixes (v, version-) when extracting version numbers

#### Version Prefix
- Configured via `version-prefix` in YAML
- Applied only to final output, not used in version calculations
- Examples: `""` → `1.2.0`, `"v"` → `v1.2.0`, `"release-"` → `release-1.2.0`

#### Reusable Function
New `calculate_next_version()` function in `main.py` returns:
```python
{
    "current_version": str | None,      # Without prefix
    "next_version": str,                # Without prefix
    "next_version_prefixed": str,       # With prefix from config
    "release_type": str | None,         # 'major', 'minor', 'patch'
    "commits": list[str],               # All commit messages
    "commit_summary": dict[str, int]    # Commit type counts
}
```

This function is ready for reuse in future phases (changelog generation, file bumping, etc.)

### Usage Examples

```bash
# Install dependencies
uv sync

# Simple usage (outputs version with prefix)
uv run contiamo-release-please next-version
# Output: v1.2.0

# Verbose mode (shows analysis details)
uv run contiamo-release-please next-version --verbose
# Output:
# Current version: 1.1.35
# Found 8 commits since last release
# Commit summary:
#   docs: 2 → patch bump
#   feat: 2 → minor bump
#   fix: 3 → patch bump
# Determined release type: minor
# Version bump: 1.1.35 → 1.2.0
# v1.2.0

# Custom config location
uv run contiamo-release-please next-version --config /path/to/config.yaml

# Run tests
uv run pytest -v
# 17 tests, all passing
```

### Testing Status

**Current Test Results:**
```
Latest tag: v1.1.35
Commits since tag: 8
Release type: minor
Next version: v1.2.0 (with prefix) / 1.2.0 (without)
```

All 17 unit tests passing:
- Conventional commit parsing
- Breaking change detection
- Release type determination
- Commit type summary
- Priority ordering (major > minor > patch)

### Important Notes

1. **UK Spelling Throughout:**
   - `analyser.py` not `analyzer.py`
   - All code comments and docstrings use UK spelling
   - Functions: `analyse_commits()`, not `analyze_commits()`

2. **Python Version:**
   - Originally specified 3.14 (doesn't exist yet)
   - Changed to 3.12 (current stable)
   - `.python-version` file: `3.12`

3. **First Release Default:**
   - Defined in `version.py` as `FIRST_RELEASE = "0.1.0"`
   - Used when no git tags exist

4. **Breaking Changes:**
   - Detected via `!` in commit type: `feat!: breaking`
   - Or via `BREAKING CHANGE:` in commit body
   - Mapped to `breaking` type which triggers major bump

### What's Next (Future Phases)

**Phase 2: Changelog Generation**
- Read changelog config from YAML
- Generate markdown changelog from commits
- Customisable sections and formatting

**Phase 3: File Bumping**
- Read `files-to-bump` from YAML
- Update version in multiple files (pyproject.toml, version.txt, etc.)
- Pattern-based replacement

**Phase 4: Release Automation**
- Create git tags
- Create release commits
- Push to remote
- Create releases on git providers (GitHub, GitLab, Azure DevOps)

### File Locations

**Config file:**
- `contiamo-release-please.yaml` in git repository root

**Source code:**
- `src/contiamo_release_please/`

**Virtual environment:**
- `.venv` in project root (created by UV)

### Dependencies

**Runtime:**
- click >= 8.1.7
- pyyaml >= 6.0
- packaging >= 24.0

**Dev:**
- pytest >= 8.3.2
- pyright >= 1.1.377
- ruff >= 0.6.2

### Quick Reference Commands

```bash
# Install dependencies
uv sync

# Run tool
uv run contiamo-release-please next-version [--verbose]

# Run tests
uv run pytest -v

# Lint
uv run ruff check .

# Type check
uv run pyright
```

### Ready for Next Session

The project is fully functional for Phase 1. The `calculate_next_version()` function provides a clean interface for future features. All code follows UK spelling conventions and is well-tested.

To continue development:
1. Navigate to the project directory
2. Run `uv sync` to ensure dependencies are installed
3. Review this PROGRESS.md file for context
4. Continue with Phase 2, 3, or 4 as needed
