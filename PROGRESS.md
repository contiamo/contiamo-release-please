# Contiamo Release Please - Development Progress

## Project Status: Phase 8 Complete ✅

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
│       ├── bumper.py          # File version bumping
│       └── release.py         # Release branch orchestration
└── tests/
    ├── __init__.py
    ├── test_analyser.py (17 tests)
    ├── test_changelog.py (15 tests)
    ├── test_bumper.py (22 tests)
    └── test_release.py (24 tests)

Total: 102 tests, all passing ✅
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

#### Phase 4: Release Branch Creation and Update (COMPLETE)

**Core Functionality:**
1. ✅ `release` CLI command for full orchestrated workflow
2. ✅ Force create/reset release branch from source branch (no conflicts)
3. ✅ Auto-detect next version using existing `calculate_next_version()` logic
4. ✅ Generate changelog entry on release branch
5. ✅ Bump version in configured files on release branch
6. ✅ Commit with message: `chore({source-branch}): update files for release {version}`
7. ✅ Force push release branch to remote
8. ✅ Dry-run mode to preview changes
9. ✅ Configurable source branch and release branch name

**New Module:**
- `src/contiamo_release_please/release.py` - Release orchestration and branch management

**Key Functions:**
- `branch_exists()` - Check if branch exists locally or remotely
- `create_or_reset_release_branch()` - Force create/reset from source (avoids conflicts)
- `stage_and_commit_release_changes()` - Commit with conventional format
- `push_release_branch()` - Force push to remote
- `create_release_branch_workflow()` - Orchestrate full workflow

**Modified Files:**
- `src/contiamo_release_please/config.py` - Added `get_source_branch()`, `get_release_branch_name()`
- `src/contiamo_release_please/main.py` - Added `release` command
- `contiamo-release-please.yaml` - Added optional config: `source-branch`, `release-branch-name`
- `Taskfile.yaml` - Added release command to help

**Configuration:**
```yaml
# Optional: Release branch configuration
source-branch: "main"  # Branch to create releases from (default: main)
release-branch-name: "release-please--branches--main"  # Custom release branch name
```

**Usage:**
```bash
# Create or update release branch (auto-detect version, update files, push)
uv run contiamo-release-please release

# Dry-run mode (show what would be done)
uv run contiamo-release-please release --dry-run --verbose

# Custom config
uv run contiamo-release-please release --config /path/to/config.yaml
```

**Force Update Strategy:**
- Release branch is always force-reset from source branch
- No merge conflicts ever occur
- Previous release branch state is discarded
- Matches Google's release-please behaviour
- Clean slate on every run

**Test Results:**
- 70 tests passing (50 existing + 20 new release tests)
- All type checks passing (pyright)
- All lint checks passing (ruff)

#### Phase 5: Pull Request Creation (COMPLETE)

**Core Functionality:**
1. ✅ GitHub PR creation and update via REST API
2. ✅ Azure DevOps PR creation and update via REST API
3. ✅ Auto-detection of git hosting provider from remote URL
4. ✅ Credential validation (errors if missing)
5. ✅ PR title format: `chore(main): release {version}` (matches Google release-please)
6. ✅ PR body: Full changelog entry
7. ✅ Update existing PR if already open
8. ✅ version.txt file creation for post-merge workflows

**New Modules:**
- `src/contiamo_release_please/github.py` - GitHub REST API integration
- `src/contiamo_release_please/azure.py` - Azure DevOps REST API integration

**Key Functions:**
- `detect_git_host()` - Auto-detect GitHub/Azure from remote URL
- `get_github_token()` / `get_azure_token()` - Credential management
- `get_repo_info()` / `get_azure_repo_info()` - Parse remote URL
- `create_or_update_pr()` - Create new PR or update existing
- `write_version_file()` - Create version.txt at repo root

**Modified Files:**
- `src/contiamo_release_please/release.py` - Integrated PR creation into workflow
- `src/contiamo_release_please/git.py` - Added `detect_git_host()` function
- `src/contiamo_release_please/main.py` - Added `--git-host` option
- `contiamo-release-please.yaml` - Added GitHub and Azure DevOps config sections
- `docs/AUTHENTICATION.md` - Comprehensive authentication guide
- `README.md` - Updated with PR creation examples
- `pyproject.toml` - Added `requests>=2.31.0` dependency

**Configuration:**
```yaml
# Optional: GitHub PR creation
github:
  token: "ghp_xxx"  # Or set GITHUB_TOKEN environment variable

# Optional: Azure DevOps PR creation
azure:
  token: "xxx"  # Or set AZURE_DEVOPS_TOKEN environment variable
```

**Usage:**
```bash
# Auto-detect git host and create PR
export GITHUB_TOKEN="ghp_xxx"
uv run contiamo-release-please release

# Explicit git host
uv run contiamo-release-please release --git-host github

# Azure DevOps
export AZURE_DEVOPS_TOKEN="your-token"
uv run contiamo-release-please release --git-host azure
```

**Test Results:**
- 76 tests passing (70 existing + 6 new tag-release tests)
- All type checks passing (pyright)
- All lint checks passing (ruff)

#### Phase 6: Git Tag Creation (COMPLETE)

**Core Functionality:**
1. ✅ `tag-release` CLI command for post-merge git tag creation
2. ✅ Reads version from version.txt (created by `release` command)
3. ✅ Creates annotated git tag with release message
4. ✅ Pushes tag to remote origin
5. ✅ Validation: Must not be on release branch
6. ✅ Validation: Tag must not already exist
7. ✅ Dry-run and verbose modes

**New Functions in git.py:**
- `get_current_branch()` - Get current git branch name
- `tag_exists()` - Check if tag exists locally or remotely
- `create_tag()` - Create annotated git tag
- `push_tag()` - Push tag to remote origin

**New Function in release.py:**
- `tag_release_workflow()` - Orchestrate tag creation with validation

**Modified Files:**
- `src/contiamo_release_please/git.py` - Added 4 git tag functions
- `src/contiamo_release_please/release.py` - Added tag_release_workflow()
- `src/contiamo_release_please/main.py` - Added `tag-release` command
- `README.md` - Added two-stage workflow documentation with CI/CD examples
- `Taskfile.yaml` - Added tag-release examples to help

**Two-Stage Workflow:**
```bash
# Stage 1: Create release PR
contiamo-release-please release

# Stage 2: After merging PR, create git tag
contiamo-release-please tag-release
```

**Test Results:**
- 76 tests passing (70 existing + 6 new tag tests)
- All type checks passing (pyright)
- All lint checks passing (ruff)

#### Bug Fix: Filter Release Infrastructure Commits (COMPLETE)

**Problem Fixed:**
1. ❌ Running `release` after merging PR (without `tag-release`) created duplicate PRs
2. ❌ Release merge commits appeared in changelog and affected version calculation

**Solution Implemented:**
- `is_release_commit()` in `analyser.py` - Detects release infrastructure commits
- Updated `create_release_branch_workflow()` - Filters commits before analysis
- Special error when only release commits found (reminds user to run `tag-release`)

**Patterns Detected:**
- Merge commits: `"Merge branch 'release-please--branches--main' into main"`
- Squash commits: `"chore(main): update files for release 1.2.3"`

**Test Results:**
- 82 tests passing (76 existing + 5 is_release_commit tests + 1 workflow test)
- All type checks passing (pyright)
- All lint checks passing (ruff)

**Benefits:**
✅ Prevents duplicate PRs when user forgets `tag-release`
✅ Excludes release commits from changelog
✅ Excludes release commits from version calculation
✅ Clear error message guides users through correct workflow
✅ Works correctly when new commits added after merge

#### Phase 6.5: Git Identity Configuration (COMPLETE)

**Core Functionality:**
1. ✅ Optional git identity configuration in config file
2. ✅ Hardcoded defaults when git section is omitted
3. ✅ Automatic git user.name and user.email configuration
4. ✅ Fixes CI environment git identity issues
5. ✅ Configurable per-project identity

**New Functions:**
- `get_git_user_name()` in `config.py` - Get git user name (default: "Contiamo Release Bot")
- `get_git_user_email()` in `config.py` - Get git user email (default: "contiamo-release@ctmo.io")
- `configure_git_identity()` in `git.py` - Configure git user identity

**Modified Files:**
- `src/contiamo_release_please/config.py` - Added git identity methods with defaults
- `src/contiamo_release_please/git.py` - Added git configuration function
- `src/contiamo_release_please/release.py` - Integrated git identity setup into workflow
- `contiamo-release-please.yaml` - Added optional git section
- `tests/test_release.py` - Updated all workflow tests with git identity mocks

**Configuration:**
```yaml
# Optional: Git identity for commits (uses defaults if not specified)
git:
  user-name: "Contiamo Release Bot"
  user-email: "contiamo-release@ctmo.io"
```

**Default Values:**
- Name: "Contiamo Release Bot"
- Email: "contiamo-release@ctmo.io"

**Test Results:**
- 83 tests passing (82 existing + 1 updated)
- All type checks passing (pyright)
- All lint checks passing (ruff)

**Benefits:**
✅ Works in CI environments without git config
✅ Customisable per-project identity
✅ Sensible defaults for all users
✅ Optional configuration (no breaking changes)

#### Phase 6.75: Generic File Version Bumping (COMPLETE)

**Core Functionality:**
1. ✅ Generic file support using marker comments
2. ✅ Marker-based version detection and replacement
3. ✅ Support for configurable prefix (e.g., `use-prefix: "v"`)
4. ✅ Multiple version replacement in single block
5. ✅ Multiple marker blocks per file

**New Class:**
- `GenericFileBumper` in `bumper.py` - Marker-based version bumping

**Marker Format:**
```markdown
<!--- contiamo-release-please-bump-start --->
Version text with 1.0.0 or v1.0.0
<!--- contiamo-release-please-bump-end --->
```

**Modified Files:**
- `src/contiamo_release_please/bumper.py` - Added GenericFileBumper class
- `tests/test_bumper.py` - Added 10 comprehensive tests (93 total now)
- `README.md` - Added markers around installation commands
- `contiamo-release-please.yaml` - Added generic file example

**Configuration:**
```yaml
extra-files:
  - type: generic
    path: README.md
    use-prefix: "v"  # Optional
```

**Regex Pattern:**
- `\bv?\d+\.\d+\.\d+\b` - Matches semantic versions with/without v prefix
- Replaces all version occurrences between markers
- Preserves all other content exactly

**Test Results:**
- 93 tests passing (83 existing + 10 new generic tests)
- All type checks passing (pyright)
- All lint checks passing (ruff)

**Benefits:**
✅ Works with any file type (Markdown, code, config files)
✅ Simple marker-based approach (matches Google's release-please)
✅ Automatic version updates in documentation
✅ Configurable prefix per file
✅ Multiple blocks and versions supported

#### Phase 7: GitHub Release Creation (COMPLETE)

**Core Functionality:**
1. ✅ Automatic GitHub release creation after tag push
2. ✅ Host detection (GitHub, Azure, GitLab)
3. ✅ Changelog extraction from CHANGELOG.md
4. ✅ Release body populated with changelog content
5. ✅ Graceful failure handling (doesn't break workflow)

**New Functions:**
- `create_github_release()` in `github.py` - Creates GitHub release via REST API
- `extract_changelog_for_version()` in `changelog.py` - Extracts changelog entry for specific version

**Modified Files:**
- `src/contiamo_release_please/github.py` - Added create_github_release() function
- `src/contiamo_release_please/changelog.py` - Added extract_changelog_for_version() helper
- `src/contiamo_release_please/release.py` - Integrated GitHub release creation into tag_release_workflow()
- `tests/test_changelog.py` - Added 4 tests for changelog extraction (15 total now)
- `tests/test_release.py` - Added 4 tests for GitHub release creation (85 total now)
- `README.md` - Added GitHub Release Creation section
- `PROGRESS.md` - Updated to Phase 7 complete

**Workflow:**
1. User runs `tag-release` command
2. Tag is created and pushed to remote
3. Tool detects git host (GitHub/Azure/GitLab)
4. If GitHub: extracts changelog for version from CHANGELOG.md
5. Creates GitHub release with tag name, release name, and changelog body
6. Prints release URL to console
7. If GitHub release creation fails, workflow continues (graceful degradation)

**Test Results:**
- 102 tests passing (93 existing + 4 changelog + 4 release + 1 updated)
- All type checks passing (pyright)
- All lint checks passing (ruff)

**Configuration:**
No additional configuration needed - uses existing GITHUB_TOKEN from environment or config.

**Benefits:**
✅ Automatic GitHub release creation
✅ Full changelog included in release body
✅ Works automatically for GitHub repositories
✅ Graceful failure (doesn't break tag creation)
✅ Consistent release information across PR, tag, and GitHub Release
✅ Zero-configuration for GitHub users

#### Phase 8: Config Generation Command (COMPLETE)

**Core Functionality:**
1. ✅ `generate-config` CLI command
2. ✅ Generates complete YAML configuration template
3. ✅ All parameters documented inline with comments
4. ✅ Required vs optional parameters clearly marked
5. ✅ Default values shown for all optional parameters
6. ✅ Examples for complex parameters (extra-files, changelog-sections)

**New Functions:**
- `generate_config_template()` in `config.py` - Generates complete template with documentation

**Modified Files:**
- `src/contiamo_release_please/config.py` - Added template generation function (+158 lines)
- `src/contiamo_release_please/main.py` - Added generate-config CLI command (+32 lines)
- `tests/test_config.py` - New file with 14 comprehensive tests (+155 lines)
- `README.md` - Added "Generate Configuration Template" section
- `PROGRESS.md` - Updated to Phase 8 complete

**Generated Template Includes:**
- **Required parameters:** release-rules with major/minor/patch
- **Optional parameters with defaults:** version-prefix, changelog-path, source-branch, release-branch-name, git identity, changelog-sections, extra-files
- **Optional parameters (env vars):** github.token, azure.token
- **Documentation:** Type information, default values, usage examples
- **Examples:** YAML files, TOML files, generic files with markers
- **Categories:** Clearly separated required vs optional configuration

**Usage:**
```bash
# Generate and save to file
contiamo-release-please generate-config > contiamo-release-please.yaml

# View template
contiamo-release-please generate-config

# Customise for project
contiamo-release-please generate-config > my-config.yaml
# Edit my-config.yaml
contiamo-release-please release -c my-config.yaml
```

**Test Results:**
- 117 tests passing (103 existing + 14 new config tests)
- All type checks passing (pyright)
- All lint checks passing (ruff)

**Benefits:**
✅ Quick project bootstrapping
✅ Self-documenting configuration
✅ Reduces configuration errors
✅ Shows all available options
✅ Includes examples for complex features
✅ No need to reference documentation for parameters

### What's Next (Future Phases)

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
- requests >= 2.31.0

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
uv run contiamo-release-please release [--dry-run] [--verbose]
uv run contiamo-release-please tag-release [--dry-run] [--verbose]

# Run tests
uv run python -m pytest -v

# Lint
uv run ruff check .

# Type check
uv run pyright
```

### Ready for Next Session

The project is fully functional through Phase 8. Key achievements:
- ✅ Version determination from conventional commits
- ✅ Changelog generation with customisable sections
- ✅ File version bumping with YAML, TOML, and generic (marker-based) support
- ✅ Release branch creation and management (force-update strategy)
- ✅ GitHub and Azure DevOps PR creation/update (auto-detection)
- ✅ Git tag creation workflow (post-merge)
- ✅ GitHub release creation with changelog content
- ✅ Release commit filtering (prevents duplicate PRs, clean changelogs)
- ✅ Git identity configuration (fixes CI environments)
- ✅ 117 comprehensive tests, all passing
- ✅ Full type safety and linting
- ✅ UK spelling throughout
- ✅ Complete two-stage release workflow matching Google release-please

To continue development:
1. Navigate to the project directory
2. Run `uv sync` to ensure dependencies are installed
3. Run `task help` to see all available commands
4. Review this PROGRESS.md file for context
5. Next steps: GitLab release support, interactive config generation mode
