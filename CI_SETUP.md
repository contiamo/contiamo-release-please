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
4. Creates a GitHub or GitLab release (Azure DevOps and Bitbucket Cloud have no release objects; the tag is the release)

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
   - **GitLab**: `GITLAB_TOKEN` environment variable
   - **Bitbucket Cloud**: `BITBUCKET_TOKEN` environment variable

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
4. **GitHub PR merge:** `Merge pull request #72 from contiamo/release-please--branches--main`
5. **Azure DevOps wrapped:** `Merged PR 10: chore(main): release X.Y.Z`
6. **Bitbucket Cloud:** `Merged in release-please--branches--main (pull request #7)`

Different git hosting providers may wrap or modify commit messages when merging pull requests. The tool is designed to recognise these variations automatically.

**Bitbucket Cloud merge commits:** Bitbucket always writes `Merged in <branch> (pull request #N)` as the subject of a merge or squash commit and puts the PR title in the body. The tool promotes the PR title (from the API when `BITBUCKET_TOKEN` is set, otherwise from the commit body) so analysis works as on other hosts, but this means **the PR title must be a conventional commit**. The `bootstrap -f bitbucket` output includes a PR title validation step for this reason.

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

**Bitbucket Pipelines:**

Bitbucket has no commit-message variable, so the decision is made in the step script:

```sh
if git log -1 --pretty=%s | grep -qE '^Merged in release-please--branches--main \(pull request #[0-9]+\)$'; then
  contiamo-release-please tag-release --git-host bitbucket --verbose
else
  contiamo-release-please release --git-host bitbucket --verbose
fi
```

## CI Environment Requirements

Your CI jobs need:

1. **Full git history** - Required for commit analysis:
   - GitHub Actions: `fetch-depth: 0` in `actions/checkout`
   - GitLab CI: `GIT_DEPTH: 0` or `git fetch --unshallow`
   - Azure Pipelines: `fetchDepth: 0` in checkout step
   - Bitbucket Pipelines: `clone: depth: full`

2. **Python 3.12+** and **uv** package manager

3. **Authentication token** as environment variable:
   - `GITHUB_TOKEN` for GitHub
   - `AZURE_DEVOPS_TOKEN` for Azure DevOps
   - `GITLAB_TOKEN` for GitLab
   - `BITBUCKET_TOKEN` for Bitbucket Cloud

4. **Write access** to the repository (for creating branches, PRs/MRs, and tags)

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

## Reference Implementation (GitLab CI)

Here's a complete working example for GitLab CI:

```yaml
stages:
  - release

variables:
  # Use project access token for API and git push authentication
  GITLAB_TOKEN: $CICD_TOKEN
  # Fetch full git history for commit analysis
  GIT_DEPTH: 0

# Create or update release merge request
create-release-mr:
  stage: release
  image: ghcr.io/astral-sh/uv:python3.12-alpine
  before_script:
    # Install git (required for cloning the tool and git operations)
    - apk add --no-cache git
    # Configure git remote with token authentication for push operations
    # Uses GitLab CI variables: CI_SERVER_HOST, CI_PROJECT_PATH, and CICD_TOKEN
    - git remote set-url origin "https://oauth2:${CICD_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git"
  script:
    # Install contiamo-release-please from GitHub
    - uv tool install git+https://github.com/contiamo/contiamo-release-please.git

    # Run release workflow (creates/updates MR)
    - uv tool run contiamo-release-please release --git-host gitlab --verbose
  rules:
    # Run on pushes to main, but not on release MR merges
    - if: '$CI_COMMIT_BRANCH == "main" && $CI_PIPELINE_SOURCE == "push" && $CI_COMMIT_MESSAGE !~ /^Merge branch .release-please--branches--main./'
      when: always

# Create git tag and GitLab release
create-tag-and-release:
  stage: release
  image: ghcr.io/astral-sh/uv:python3.12-alpine
  before_script:
    # Install git (required for cloning the tool and git operations)
    - apk add --no-cache git
    # Checkout the main branch (GitLab CI uses detached HEAD by default)
    - git checkout -B "$CI_COMMIT_REF_NAME" "$CI_COMMIT_SHA"
    # Configure git remote with token authentication for push operations
    # Uses GitLab CI variables: CI_SERVER_HOST, CI_PROJECT_PATH, and CICD_TOKEN
    - git remote set-url origin "https://oauth2:${CICD_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git"
  script:
    # Install contiamo-release-please from GitHub
    - uv tool install git+https://github.com/contiamo/contiamo-release-please.git

    # Create tag and GitLab release
    - uv tool run contiamo-release-please tag-release --git-host gitlab --verbose
  rules:
    # Run only when release MR is merged to main
    - if: '$CI_COMMIT_BRANCH == "main" && $CI_COMMIT_MESSAGE =~ /^Merge branch .release-please--branches--main./'
      when: always
```

**Key differences from GitHub Actions:**

- **Git history:** Uses `GIT_DEPTH: 0` variable instead of `fetch-depth: 0`
- **Commit message variable:** Uses `$CI_COMMIT_MESSAGE` for pattern matching
- **Branch variable:** Uses `$CI_DEFAULT_BRANCH` or hardcode `"main"`
- **Authentication:** Uses `$GITLAB_TOKEN` environment variable mapped from `$CICD_TOKEN`
- **Image:** Uses `ghcr.io/astral-sh/uv:python3.12-alpine` (uv pre-installed, no manual installation needed)
- **Pattern matching:** Uses `=~` for regex matching in rules
- **Git remote authentication:** Configures remote URL using built-in CI variables (`CI_SERVER_HOST`, `CI_PROJECT_PATH`) with `oauth2:${CICD_TOKEN}@` for push access - works for gitlab.com and self-hosted instances
- **Branch checkout:** Tag job explicitly checks out the branch (GitLab CI uses detached HEAD)
- **Release pattern:** Matches `Merge branch 'release-please--branches--main'` merge commit

**Setting up GitLab Token:**

**Option 1: Project Access Token (Recommended for CI/CD)**

1. Go to Settings → Access Tokens
2. Click "Add new token"
3. Fill in details:
   - **Token name**: `ci-cd-for-this-repo` (or similar)
   - **Expiration date**: Set expiration (optional but recommended)
   - **Select a role**: Maintainer (required for creating MRs and pushing tags)
   - **Select scopes**: `api`, `write_repository`
4. Click "Create project access token"
5. Copy the token immediately

Then add to CI/CD variables:
1. Go to Settings → CI/CD → Variables
2. Add variable:
   - Key: `CICD_TOKEN`
   - Value: Your project access token (e.g., `glpat-xxxxxxxxxxxxxxxxxxxx`)
   - Flags: Protected (recommended), Masked (recommended)

**Option 2: Personal Access Token**

1. Create a personal access token with `api` scope (see [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md))
2. Add to CI/CD variables with key `CICD_TOKEN`

**Note:** The git remote URL is constructed using GitLab's built-in CI variables (`CI_SERVER_HOST` and `CI_PROJECT_PATH`), so it automatically works for any GitLab instance without hardcoding URLs.

## Reference Implementation (Bitbucket Pipelines)

Generate this with `contiamo-release-please bootstrap -f bitbucket`. Bitbucket only reads `bitbucket-pipelines.yml` at the repository root, so both jobs live in one file:

```yaml
image: ghcr.io/astral-sh/uv:python3.12-alpine

clone:
  depth: full # Full history is required for commit analysis and tag detection

definitions:
  steps:
    - step: &contiamo-release-please
        name: Contiamo Release Please
        script:
          - apk add --no-cache git
          # Bitbucket checks out a detached HEAD; the tool needs to be on the branch
          - git checkout -B "$BITBUCKET_BRANCH" "$BITBUCKET_COMMIT"
          # Push branches and tags with the access token
          - git remote set-url origin "https://x-token-auth:${BITBUCKET_TOKEN}@bitbucket.org/${BITBUCKET_REPO_FULL_NAME}.git"
          - uv tool install git+https://github.com/contiamo/contiamo-release-please.git
          # The merge of the release PR always has this subject
          - |
            if git log -1 --pretty=%s | grep -qE '^Merged in release-please--branches--main \(pull request #[0-9]+\)$'; then
              uv tool run contiamo-release-please tag-release --git-host bitbucket --verbose
            else
              uv tool run contiamo-release-please release --git-host bitbucket --verbose
            fi

    - step: &validate-pr-title
        name: Validate PR title
        script:
          - apk add --no-cache curl jq
          - .bitbucket/scripts/validate-pr-title.sh

pipelines:
  branches:
    main:
      - step: *contiamo-release-please
  pull-requests:
    "**":
      - step: *validate-pr-title
```

**Key differences from the other platforms:**

- **One file, one step:** there is no commit-message variable, so the step inspects `git log -1` itself and runs either `release` or `tag-release`
- **Git history:** `clone: depth: full` (default is 50 commits)
- **Authentication:** a secured repository variable `BITBUCKET_TOKEN` holding a repository access token. It is used both for the API (Bearer) and for `git push` via `x-token-auth:${BITBUCKET_TOKEN}@bitbucket.org`
- **Branch checkout:** Bitbucket checks out a detached HEAD, so the step recreates the branch first
- **PR title validation:** `pull-requests:` patterns match the *source* branch, so `"**"` covers every PR; the script skips the tool's own release PRs. Enforcing the check as a merge check needs Bitbucket Premium; without it the failed build is only a warning
- **No releases:** Bitbucket Cloud has no release objects; `tag-release` creates and pushes the tag only

**Setting up the Bitbucket token:**

1. A **repository admin** goes to Repository settings → Security → Access tokens
2. Creates a token with scopes **Repositories: Write** and **Pull requests: Write**
3. Adds it under Repository settings → Pipelines → Repository variables as `BITBUCKET_TOKEN`, ticked **Secured**

Repository access tokens are available on all Bitbucket Cloud plans. User-bound API tokens are not supported by the tool. See the generated `.bitbucket/README-CI-SETUP.md` for branch restrictions and merge checks.

## Adapting to Other CI Platforms

The reference implementations above (GitHub Actions, Azure Pipelines, GitLab CI, and Bitbucket Pipelines) follow this pattern that works for any CI platform:

### Job 1: Release PR Creation

1. **Trigger:** Push to main, excluding release PR merges
2. **Steps:**
   - Checkout with full history
   - Install Python 3.12+
   - Install uv package manager
   - Install contiamo-release-please
   - Run `contiamo-release-please release --verbose`
3. **Environment:** Set `GITHUB_TOKEN`, `AZURE_DEVOPS_TOKEN`, `GITLAB_TOKEN`, or `BITBUCKET_TOKEN`

### Job 2: Tag Creation

1. **Trigger:** Push to main, only on release PR merges
2. **Steps:**
   - Checkout with full history
   - Install Python 3.12+
   - Install uv package manager
   - Install contiamo-release-please
   - Run `contiamo-release-please tag-release --verbose`
3. **Environment:** Set `GITHUB_TOKEN`, `AZURE_DEVOPS_TOKEN`, `GITLAB_TOKEN`, or `BITBUCKET_TOKEN`

### Platform-Specific Installation Commands

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

**Bitbucket Pipelines:** see the [reference implementation](#reference-implementation-bitbucket-pipelines) above, or run `contiamo-release-please bootstrap -f bitbucket`.

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
   - GitHub or GitLab release with changelog (if using GitHub or GitLab)
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

### "GitHub token not found", "Azure DevOps token not found", "GitLab token not found", or "Bitbucket token not found"

- Ensure `GITHUB_TOKEN`, `AZURE_DEVOPS_TOKEN`, `GITLAB_TOKEN`, or `BITBUCKET_TOKEN` is set as an environment variable
- For GitHub Actions, use `${{ secrets.GITHUB_TOKEN }}` or create a custom token
- For GitLab CI, add `GITLAB_TOKEN` in Settings → CI/CD → Variables
- For Bitbucket Pipelines, add `BITBUCKET_TOKEN` in Repository settings → Pipelines → Repository variables
- See [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) for token setup

### "Permission denied" or "403 Forbidden"

- Your token doesn't have sufficient permissions
- For GitHub: Token needs `repo` scope (or `public_repo` for public repos)
- For Azure DevOps: Token needs `Code (Read & Write)` scope
- For GitLab: Token needs `api` scope
- For Bitbucket Cloud: Token needs `repository:write` and `pullrequest:write` scopes
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
5. `Merged in release-please--branches--main (pull request #7)` - Bitbucket Cloud

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
- **Bitbucket Pipelines:** [https://support.atlassian.com/bitbucket-cloud/docs/get-started-with-bitbucket-pipelines/](https://support.atlassian.com/bitbucket-cloud/docs/get-started-with-bitbucket-pipelines/)
