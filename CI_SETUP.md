# CI/CD Setup Guide

A guide to using Contiamo Release Please in your CI/CD pipeline.

## What This Tool Does

Contiamo Release Please automates semantic versioning and release management based on conventional commits. It analyses your commit history, determines version bumps, generates changelogs, and creates releases - all automatically.

## The Automation Process

The workflow consists of two stages:

### Stage 1: Release PR Creation

**Trigger:** Push to main branch (excluding release PR merges)

The tool:

1. Analyses commits since the last release
2. Determines the next version based on conventional commits
3. Generates/updates CHANGELOG.md
4. Bumps version in configured files
5. Creates a pull request with all changes

### Stage 2: Tag and Release Creation

**Trigger:** Merge of release PR

The tool:

1. Reads the version from version.txt
2. Creates an annotated git tag
3. Pushes the tag to the remote repository
4. Creates a GitHub release (if using GitHub)

## Prerequisites

Before setting up CI, ensure you have:

1. **Python 3.12+** available in your CI environment
2. **Configuration file** - Create `contiamo-release-please.yaml` in your repository root:

   ```bash
   contiamo-release-please generate-config > contiamo-release-please.yaml
   ```

   Then customise the generated file for your project.

3. **Authentication token** - Required for creating pull requests and releases:
   - **GitHub**: `GITHUB_TOKEN` environment variable
   - **Azure DevOps**: `AZURE_DEVOPS_TOKEN` environment variable

   See [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) for detailed token setup instructions.

4. **Conventional commits** - Your project should use [conventional commit](https://www.conventionalcommits.org/) format

## Required Commands

Your CI pipeline needs to run these two commands:

### Command 1: Create Release PR

```bash
contiamo-release-please release --verbose
```

**When to run:** On every push to main branch, EXCEPT when merging release PRs

**What it does:** Creates or updates the release PR with version bumps and changelog

### Command 2: Create Tag and Release

```bash
contiamo-release-please tag-release --verbose
```

**When to run:** ONLY when a release PR is merged to main

**What it does:** Creates git tag, pushes it, and creates GitHub release (if applicable)

## Detecting Release PR Merges

To distinguish between regular commits and release PR merges, check the commit message. The tool recognises several patterns:

**Supported Release PR Merge Patterns:**

1. **Squash merge:** `chore(main): update files for release X.Y.Z`
2. **PR title:** `chore(main): release X.Y.Z`
3. **Standard merge:** `Merge branch 'release-please--branches--main' into main`
4. **Azure DevOps wrapped:** `Merged PR 10: chore(main): release X.Y.Z`

Different git hosting providers may wrap or modify commit messages when merging pull requests. The tool is designed to recognise these variations automatically.

### Platform-Specific Examples

For CI filtering, use the most common pattern (squash merge format):

**GitHub Actions:**

```yaml
if: "!startsWith(github.event.head_commit.message, 'chore(main): update files for release')"  # Job 1
if: "startsWith(github.event.head_commit.message, 'chore(main): update files for release')"   # Job 2
```

**GitLab CI:**

```yaml
rules:
  - if: '$CI_COMMIT_MESSAGE !~ /^chore\(main\): update files for release/' # Job 1
  - if: '$CI_COMMIT_MESSAGE =~ /^chore\(main\): update files for release/' # Job 2
```

**Azure Pipelines:**

```yaml
condition: not(startsWith(variables['Build.SourceVersionMessage'], 'chore(main): release'))  # Job 1
condition: startsWith(variables['Build.SourceVersionMessage'], 'chore(main): release')      # Job 2
```

**Note:** Azure DevOps wraps PR titles with `Merged PR N: `, so the condition checks for the inner pattern.

## CI Environment Requirements

Your CI jobs need:

1. **Full git history** - Required for commit analysis:
   - GitHub Actions: `fetch-depth: 0` in `actions/checkout`
   - GitLab CI: `GIT_DEPTH: 0` or `git fetch --unshallow`
   - Azure Pipelines: `fetchDepth: 0` in checkout step

2. **Python 3.12+** and **uv** package manager

3. **Authentication token** as environment variable:
   - `GITHUB_TOKEN` for GitHub
   - `AZURE_DEVOPS_TOKEN` for Azure DevOps

4. **Write access** to the repository (for creating branches, PRs, and tags)

## Reference Implementation (GitHub Actions)

Here's a complete working example for GitHub Actions that you can adapt to other platforms:

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
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Required: Fetch all history for commit analysis

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python
        run: uv python install 3.12

      - name: Install contiamo-release-please
        run: uv tool install git+ssh://git@github.com/contiamo/contiamo-release-please.git@v0.3.1

      - name: Create release PR
        run: contiamo-release-please release --verbose
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  tag-release:
    name: Create Git Tag and Release
    runs-on: ubuntu-latest
    # Run ONLY on release PR merges
    if: "startsWith(github.event.head_commit.message, 'chore(main): update files for release')"
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Required: Fetch all history for tags

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python
        run: uv python install 3.12

      - name: Install contiamo-release-please
        run: uv tool install git+ssh://git@github.com/contiamo/contiamo-release-please.git@v0.3.1

      - name: Create and push tag
        run: contiamo-release-please tag-release --verbose
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Reference Implementation (Azure Pipelines)

Here's a complete working example for Azure Pipelines:

```yaml
variables:
  - name: IS_RELEASE_PR_MERGE
    # Azure wraps PR merges with "Merged PR X:", so we check for each part separately
    # Matches: "Merged PR 10: chore(main): release 0.1.0"
    value: $[and(contains(variables['Build.SourceVersionMessage'], 'Merged PR'), and(contains(variables['Build.SourceVersionMessage'], 'chore(main)'), contains(variables['Build.SourceVersionMessage'], 'release')))]

trigger:
  branches:
    include:
      - main

pr: none

jobs:
  # Release PR Creation - runs on pushes to main (except release PR merges)
  - job: CreateReleasePR
    displayName: "Create or Update Release PR"
    condition: and(eq(variables['Build.SourceBranchName'], 'main'), eq(variables['Build.Reason'], 'IndividualCI'), ne(variables['IS_RELEASE_PR_MERGE'], 'True'))
    steps:
      - checkout: self
        fetchDepth: 0 # Required: Fetch all history for commit analysis
        persistCredentials: true
        displayName: "Checkout with full history"

      - bash: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          export PATH="$HOME/.local/bin:$PATH"
          uv python install 3.12
          uv tool install git+https://github.com/contiamo/contiamo-release-please.git
        displayName: "Install uv, Python 3.12, and contiamo-release-please"

      - bash: |
          export PATH="$HOME/.local/bin:$PATH"
          contiamo-release-please release --verbose
        displayName: "Create or update release PR"
        env:
          AZURE_DEVOPS_TOKEN: $(System.AccessToken)

  # Tag and Release Creation - runs only on release PR merges
  - job: CreateTagAndRelease
    displayName: "Create Git Tag and Release"
    condition: and(eq(variables['Build.SourceBranchName'], 'main'), eq(variables['IS_RELEASE_PR_MERGE'], 'True'))
    steps:
      - checkout: self
        fetchDepth: 0 # Required: Fetch all history for tags
        persistCredentials: true
        displayName: "Checkout with full history"

      - bash: |
          git checkout main
          git pull origin main
        displayName: "Ensure we're on main branch"

      - bash: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          export PATH="$HOME/.local/bin:$PATH"
          uv python install 3.12
          uv tool install git+https://github.com/contiamo/contiamo-release-please.git
        displayName: "Install uv, Python 3.12, and contiamo-release-please"

      - bash: |
          export PATH="$HOME/.local/bin:$PATH"
          contiamo-release-please tag-release --verbose
        displayName: "Create and push git tag"
        env:
          AZURE_DEVOPS_TOKEN: $(System.AccessToken)
```

**Key differences from GitHub Actions:**

- **Pattern matching:** Azure DevOps cannot use `:` in conditions, so the IS_RELEASE_PR_MERGE variable uses multiple `contains()` checks
- **Commit message variable:** Uses `Build.SourceVersionMessage` instead of GitHub's `github.event.head_commit.message`
- **Authentication:** Uses `$(System.AccessToken)` which is automatically available (no token setup required)
- **Persist credentials:** Must set `persistCredentials: true` for the tool to push branches and tags

## Adapting to Other CI Platforms

The reference implementations above (GitHub Actions and Azure Pipelines) follow this pattern that works for any CI platform:

### Job 1: Release PR Creation

1. **Trigger:** Push to main, excluding release PR merges
2. **Steps:**
   - Checkout with full history
   - Install Python 3.12+
   - Install uv package manager
   - Install contiamo-release-please
   - Run `contiamo-release-please release --verbose`
3. **Environment:** Set `GITHUB_TOKEN` or `AZURE_DEVOPS_TOKEN`

### Job 2: Tag Creation

1. **Trigger:** Push to main, only on release PR merges
2. **Steps:**
   - Checkout with full history
   - Install Python 3.12+
   - Install uv package manager
   - Install contiamo-release-please
   - Run `contiamo-release-please tag-release --verbose`
3. **Environment:** Set `GITHUB_TOKEN` or `AZURE_DEVOPS_TOKEN`

### Platform-Specific Installation Commands

**GitLab CI:**

```yaml
before_script:
  - apt-get update && apt-get install -y python3 python3-pip git
  - curl -LsSf https://astral.sh/uv/install.sh | sh
  - export PATH="$HOME/.cargo/bin:$PATH"
  - uv tool install git+ssh://git@github.com/contiamo/contiamo-release-please.git@v0.3.1
```

**Azure Pipelines:**

```yaml
steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: "3.12"
  - script: |
      curl -LsSf https://astral.sh/uv/install.sh | sh
      export PATH="$HOME/.cargo/bin:$PATH"
      uv tool install git+ssh://git@github.com/contiamo/contiamo-release-please.git@v0.3.1
    displayName: "Install uv and contiamo-release-please"
```

**Bitbucket Pipelines:**

```yaml
pipelines:
  default:
    - step:
        name: Release PR
        image: python:3.12
        script:
          - curl -LsSf https://astral.sh/uv/install.sh | sh
          - export PATH="$HOME/.cargo/bin:$PATH"
          - uv tool install git+ssh://git@github.com/contiamo/contiamo-release-please.git@v0.3.1
          - contiamo-release-please release --verbose
```

## What Happens After Setup

Once your CI is configured:

1. **Developers push to main** using conventional commits
2. **CI automatically creates a release PR** with:
   - Updated CHANGELOG.md
   - Bumped version in configured files
   - version.txt with the new version
3. **Team reviews and merges the release PR**
4. **CI automatically creates:**
   - Git tag (e.g., `v1.2.3`)
   - GitHub release with changelog (if using GitHub)
5. **Subsequent CI jobs can be triggered by the tag** (deployments, builds, etc.)

### Safety Checks

The tool includes built-in safety checks to prevent accidental tagging:

- **Release commit verification** - The `tag-release` command verifies that the latest commit is a release PR merge (either squash merge or regular merge)
- **Version file validation** - Ensures version.txt exists and contains a valid version
- **Tag existence check** - Prevents creating duplicate tags
- **Branch validation** - Prevents tagging from the release branch itself

These checks protect against:

- Running `tag-release` accidentally on non-release commits
- CI misconfiguration that would tag every commit
- Manual execution errors
- Wrong timing (running tag-release before merging the release PR)

If any check fails, the command exits with an error message explaining what's wrong and how to fix it.

## Troubleshooting

### "No commits found since last release"

- This is normal if there are no conventional commits since the last tag
- The tool will not create a release PR
- Push commits using conventional commit format (feat:, fix:, etc.)

### "GitHub token not found" or "Azure DevOps token not found"

- Ensure `GITHUB_TOKEN` or `AZURE_DEVOPS_TOKEN` is set as an environment variable
- For GitHub Actions, use `${{ secrets.GITHUB_TOKEN }}` or create a custom token
- See [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) for token setup

### "Permission denied" or "403 Forbidden"

- Your token doesn't have sufficient permissions
- For GitHub: Token needs `repo` scope (or `public_repo` for public repos)
- For Azure DevOps: Token needs `Code (Read & Write)` scope
- See [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) for required permissions

### "Failed to create pull request"

- Check that your token has write access to the repository
- Verify the token hasn't expired
- Ensure the repository exists and the remote URL is correct

### "Could not determine version"

- The tool automatically fetches tags from the remote
- If this is the first release, the tool will use version `0.1.0`
- Ensure your CI has network access to fetch from the git remote

### "Shallow clone" or "Not enough history"

- Ensure `fetch-depth: 0` (or equivalent) is set in your checkout step
- The tool automatically fetches tags, but needs commit history for analysis
- Without full history, commit analysis may be incomplete

### Release PR not created

- Check that the commit message pattern matches conventional commits
- Verify the CI job ran successfully (check logs)
- Ensure the job condition properly excludes release PR merges
- Run locally with `--dry-run --verbose` to debug

### Tag not created after merge

- Verify the CI job condition correctly detects release PR merges
- Check that the commit message starts with `chore(main): update files for release`
- Ensure version.txt exists and contains a valid version
- Check CI logs for errors

### "Cannot create release tag: Latest commit is not a release PR merge"

This error means the `tag-release` command detected that the latest commit doesn't match any known release PR merge patterns.

**Common causes:**

1. Running `tag-release` before merging the release PR
2. Running `tag-release` on a non-release commit
3. Using a git hosting provider with a different merge commit format

**Solution:**

The tool recognises these patterns (defined in `src/contiamo_release_please/analyser.py`):

1. `chore(main): update files for release X.Y.Z` - Squash merge
2. `chore(main): release X.Y.Z` - PR title format
3. `Merge branch 'release-please--branches--main' into main` - Standard merge
4. `Merged PR 10: chore(main): release X.Y.Z` - Azure DevOps

**For new git providers with different formats:**

If your git hosting provider wraps commit messages differently, you can extend the patterns by modifying the `RELEASE_COMMIT_PATTERNS` constant in `src/contiamo_release_please/analyser.py`:

```python
RELEASE_COMMIT_PATTERNS = [
    # Existing patterns...
    # Add your custom pattern here (uses Python regex)
    r"^Your-Platform-Prefix: chore\([^)]+\):\s+release",
]
```

The patterns use `{release_branch}` as a placeholder that gets substituted with your configured release branch name. Submit a PR if you'd like your provider's pattern included by default.

## Testing Your Setup

Before committing your CI configuration:

1. **Test locally:**

   ```bash
   # Dry run to see what would happen
   contiamo-release-please release --dry-run --verbose
   ```

2. **Verify configuration:**

   ```bash
   # Check your config is valid
   contiamo-release-please next-version --verbose
   ```

3. **Test authentication:**
   ```bash
   # Verify your token works (dry run)
   export GITHUB_TOKEN="your-token"
   contiamo-release-please release --dry-run --verbose
   ```

## Additional Resources

- **Authentication Setup:** [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md)
- **Configuration Options:** Run `contiamo-release-please generate-config` to see all options
- **Conventional Commits:** [https://www.conventionalcommits.org/](https://www.conventionalcommits.org/)
- **GitHub Actions:** [https://github.com/features/actions](https://github.com/features/actions)
- **GitLab CI/CD:** [https://docs.gitlab.com/ee/ci/](https://docs.gitlab.com/ee/ci/)
- **Azure Pipelines:** [https://azure.microsoft.com/en-us/services/devops/pipelines/](https://azure.microsoft.com/en-us/services/devops/pipelines/)
