# Contiamo Release Please - Development Progress

## Project Status: Phase 3.5 Complete ✅

### What's Been Implemented

#### Phase 1: Version Determination (COMPLETE)
#### Phase 2: Changelog Generation (COMPLETE)
#### Phase 3: File Bumping - YAML Support (COMPLETE)

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
├── Taskfile.yaml
├── contiamo-release-please.yaml (example config)
├── charts/testchart/Chart.yaml (test fixture, gitignored)
├── src/
│   └── contiamo_release_please/
│       ├── __init__.py
│       ├── main.py           # CLI + all commands
│       ├── config.py          # YAML config loading
│       ├── git.py             # Git operations (root detection, tags, commits)
│       ├── analyser.py        # Commit analysis (UK spelling)
│       ├── version.py         # Semver bumping logic
│       ├── changelog.py       # Changelog generation
│       └── bumper.py          # File version bumping
└── tests/
    ├── __init__.py
    ├── test_analyser.py (17 tests)
    ├── test_changelog.py (11 tests)
    └── test_bumper.py (22 tests)

Total: 50 tests, all passing ✅
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

#### Phase 2: Changelog Generation (COMPLETE)

**Core Functionality:**
1. ✅ `generate-changelog` CLI command
2. ✅ Commit grouping by changelog sections (Features, Bug Fixes, etc.)
3. ✅ Customisable changelog sections via YAML config
4. ✅ Optional changelog path configuration (default: CHANGELOG.md)
5. ✅ Markdown formatting matching Release Please style
6. ✅ Prepend to existing CHANGELOG.md or create new file
7. ✅ Dry-run mode to preview changes
8. ✅ Verbose mode for detailed output
9. ✅ Scope formatting (e.g., **auth**: description)
10. ✅ Section ordering based on config
11. ✅ Automatic header preservation

**New Files:**
- `src/contiamo_release_please/changelog.py` - Changelog generation logic
- `tests/test_changelog.py` - 11 comprehensive tests

**Modified Files:**
- `src/contiamo_release_please/config.py` - Added `get_changelog_path()` and `get_changelog_sections()`
- `src/contiamo_release_please/main.py` - Added `generate-changelog` command
- `contiamo-release-please.yaml` - Added changelog configuration examples

**Usage:**
```bash
# Generate changelog (dry-run)
uv run contiamo-release-please generate-changelog --dry-run --verbose

# Generate and write to CHANGELOG.md
uv run contiamo-release-please generate-changelog

# Custom output path
uv run contiamo-release-please generate-changelog --output CHANGES.md
```

**Test Results:**
- 28 tests passing (17 analyser + 11 changelog)
- All existing tests still pass

#### Phase 3: File Bumping - YAML Support (COMPLETE)

**Core Functionality:**
1. ✅ `bump-files` CLI command
2. ✅ YAML file version bumping using JSONPath
3. ✅ Per-file prefix configuration (`use-prefix`)
4. ✅ Extensible `FileBumper` architecture (ABC pattern)
5. ✅ Auto-version detection (reuses `calculate_next_version()`)
6. ✅ Dry-run mode to preview changes
7. ✅ Comprehensive error handling and validation
8. ✅ Support for multiple paths in same file
9. ✅ Verbose mode for detailed output

**New Files:**
- `src/contiamo_release_please/bumper.py` - File bumping logic with extensible architecture
- `tests/test_bumper.py` - 14 comprehensive tests
- `charts/testchart/Chart.yaml` - Test Helm chart (gitignored)

**Modified Files:**
- `src/contiamo_release_please/config.py` - Added `get_extra_files()` method
- `src/contiamo_release_please/main.py` - Added `bump-files` command
- `contiamo-release-please.yaml` - Added `extra-files` configuration
- `pyproject.toml` - Added `jsonpath-ng>=1.6.0` dependency
- `.gitignore` - Added `charts/` directory
- `Taskfile.yaml` - Updated help with bump-files examples

**Configuration:**
```yaml
extra-files:
  - type: yaml
    path: charts/testchart/Chart.yaml
    yaml-path: $.version          # Simple path
  - type: yaml
    path: charts/testchart/Chart.yaml
    yaml-path: $.appVersion
    use-prefix: "v"               # Adds "v" prefix to version
```

**Usage:**
```bash
# Bump files (auto-detects version)
uv run contiamo-release-please bump-files

# Dry-run mode (preview changes)
uv run contiamo-release-please bump-files --dry-run --verbose

# Shows:
# Updated files:
#   ✓ charts/testchart/Chart.yaml:$.version → 0.1.0
#   ✓ charts/testchart/Chart.yaml:$.appVersion → v0.1.0
```

**Test Results:**
- 42 tests passing (17 analyser + 11 changelog + 14 YAML bumper)
- All type checks passing (pyright)
- All lint checks passing (ruff)

**Architecture Highlights:**
- Abstract `FileBumper` base class for extensibility
- Type-specific bumpers: `YamlFileBumper`
- JSONPath syntax for flexible field targeting

#### Phase 3.5: TOML File Support (COMPLETE)

**Core Functionality:**
1. ✅ `TomlFileBumper` class for Python projects
2. ✅ Support for `pyproject.toml` version bumping
3. ✅ JSONPath syntax for consistency with YAML
4. ✅ Comment and formatting preservation using tomlkit
5. ✅ Same `use-prefix` functionality as YAML
6. ✅ Comprehensive error handling

**New Dependencies:**
- `tomlkit>=0.12.0` - TOML library that preserves formatting and comments

**Modified Files:**
- `src/contiamo_release_please/bumper.py` - Added `TomlFileBumper` class
- `tests/test_bumper.py` - Added 8 TOML tests (50 total tests now)
- `pyproject.toml` - Added tomlkit dependency
- `contiamo-release-please.yaml` - Added commented TOML example

**Configuration:**
```yaml
extra-files:
  - type: toml
    path: pyproject.toml
    toml-path: $.project.version
    use-prefix: "v"  # Optional prefix
```

**Architecture:**
- `TomlFileBumper` extends abstract `FileBumper` class
- Uses same JSONPath syntax as YAML bumper ($.field.nested)
- Preserves TOML comments and formatting via tomlkit
- Consistent error handling with YAML implementation

**Test Results:**
- 50 tests passing (17 analyser + 11 changelog + 14 YAML bumper + 8 TOML bumper)
- All type checks passing (pyright)
- All lint checks passing (ruff)

### What's Next (Future Phases)

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
- jsonpath-ng >= 1.6.0
- tomlkit >= 0.12.0

**Dev:**
- pytest >= 8.3.2
- pyright >= 1.1.377
- ruff >= 0.6.2

### Quick Reference Commands

**Using Taskfile (Recommended):**
```bash
# List all available tasks
task

# Show usage examples
task help

# Setup environment (create venv + install deps)
task setup

# Run tests
task test

# Lint code
task lint

# Format code
task format

# Clean project
task clean
```

**Direct commands:**
```bash
# Install dependencies
uv sync

# Run tool
uv run contiamo-release-please next-version [--verbose]
uv run contiamo-release-please generate-changelog [--dry-run] [--verbose]
uv run contiamo-release-please bump-files [--dry-run] [--verbose]

# Run tests
uv run python -m pytest -v

# Lint
uv run ruff check .

# Type check
uv run pyright
```

### Ready for Next Session

The project is fully functional through Phase 3.5. Key achievements:
- ✅ Version determination from conventional commits
- ✅ Changelog generation with customisable sections
- ✅ File version bumping with YAML support
- ✅ File version bumping with TOML support
- ✅ 50 comprehensive tests, all passing
- ✅ Full type safety and linting
- ✅ UK spelling throughout
- ✅ Extensible architecture for future enhancements

To continue development:
1. Navigate to the project directory
2. Run `uv sync` to ensure dependencies are installed
3. Run `task help` to see all available commands
4. Review this PROGRESS.md file for context
5. Next steps: Phase 4 (Release automation)
