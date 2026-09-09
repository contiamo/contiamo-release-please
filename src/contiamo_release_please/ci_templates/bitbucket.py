"""Bitbucket Pipelines templates for Contiamo Release Please."""

BITBUCKET_PIPELINES_TEMPLATE = """# Contiamo Release Please - Bitbucket Pipelines
#
# Two jobs, one file (Bitbucket only reads bitbucket-pipelines.yml at the repo root):
#   1. On every push to main: create/update the release PR, or, when the push is the
#      merge of the release PR, create and push the git tag.
#   2. On every pull request: validate that the PR title is a conventional commit.
#
# Requires a secured repository variable BITBUCKET_TOKEN holding a repository access
# token with scopes 'repository:write' and 'pullrequest:write'.
# See .bitbucket/README-CI-SETUP.md for the full setup.

image: ghcr.io/astral-sh/uv:python3.12-alpine

clone:
  depth: full # Full history is required for commit analysis and tag detection

definitions:
  steps:
    - step: &contiamo-release-please
        name: Contiamo Release Please
        script:
          # git is needed for the tool's own operations and to install it from GitHub
          - apk add --no-cache git
          # Bitbucket checks out a detached HEAD; the tool needs to be on the branch
          - git checkout -B "$BITBUCKET_BRANCH" "$BITBUCKET_COMMIT"
          # Push branches and tags with the access token
          - git remote set-url origin "https://x-token-auth:${BITBUCKET_TOKEN}@bitbucket.org/${BITBUCKET_REPO_FULL_NAME}.git"
          - uv tool install git+https://github.com/contiamo/contiamo-release-please.git
          # Bitbucket has no commit-message variable, so decide here. The merge of the
          # release PR always has the subject "Merged in <release-branch> (pull request #N)".
          - |
            if git log -1 --pretty=%s | grep -qE '^Merged in release-please--branches--main \\(pull request #[0-9]+\\)$'; then
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
    # Patterns here match the SOURCE branch, so use '**' to cover every PR.
    # The script itself skips PRs opened by the release tool.
    "**":
      - step: *validate-pr-title
"""

BITBUCKET_PR_VALIDATION_SCRIPT = """#!/bin/sh
set -e

# Only meaningful in a pull-requests pipeline
if [ -z "$BITBUCKET_PR_ID" ]; then
    echo "✓ Not a pull request pipeline, skipping validation"
    exit 0
fi

# The release PR is created by the tool with a valid title; no need to gate the bot
case "$BITBUCKET_BRANCH" in
    release-please--branches--*)
        echo "✓ Release PR, skipping validation"
        exit 0
        ;;
esac

if [ -z "$BITBUCKET_TOKEN" ]; then
    echo "❌ BITBUCKET_TOKEN is not set (secured repository variable required)"
    exit 1
fi

# Get the PR title from the Bitbucket API
echo "Getting PR title from Bitbucket API..."
PR_TITLE=$(curl -sf \\
    -H "Authorization: Bearer $BITBUCKET_TOKEN" \\
    "https://api.bitbucket.org/2.0/repositories/${BITBUCKET_REPO_FULL_NAME}/pullrequests/${BITBUCKET_PR_ID}" \\
    | jq -r '.title')

if [ -z "$PR_TITLE" ] || [ "$PR_TITLE" = "null" ]; then
    echo "❌ Could not retrieve PR title"
    exit 1
fi

echo "PR Title: $PR_TITLE"

# Conventional commit pattern with common types
# Matches: type(optional-scope): description or type: description
PATTERN="^(feat|fix|chore|ci|docs|refactor|test|perf|style|build)(\\(.+\\))?(!)?(:[[:space:]]+.+|!:[[:space:]]+.+)"

# Validate PR title
if echo "$PR_TITLE" | grep -qE "$PATTERN"; then
    echo "✓ PR title follows conventional commit format"
    exit 0
else
    echo "❌ PR title does not follow conventional commit format"
    echo ""
    echo "Bitbucket writes the PR title into the merge commit, and the release tool"
    echo "reads it from there. A title that is not a conventional commit is ignored"
    echo "and the change never triggers a release."
    echo ""
    echo "Expected format: <type>[(<scope>)][!]: <description>"
    echo "Allowed types: feat, fix, chore, ci, docs, refactor, test, perf, style, build"
    echo ""
    echo "Examples:"
    echo "  feat: add new feature"
    echo "  fix(api): resolve authentication issue"
    echo "  docs: update README"
    echo "  feat!: breaking change in API"
    exit 1
fi
"""

BITBUCKET_CI_SETUP_README = """# Bitbucket Pipelines Release Please Setup

## Prerequisites

- Bitbucket **Cloud** (bitbucket.org). Bitbucket Server / Data Center is not supported.
- Pipelines enabled for the repository (Repository settings → Pipelines → Settings).
- A **repository admin** to create the access token (see below). Access tokens are
  available on every Bitbucket Cloud plan, but only admins see the menu.
- `bitbucket-pipelines.yml` and `.bitbucket/` committed to the repository.

## 1. Create a Repository Access Token

Bitbucket Pipelines can push over the default HTTPS origin, but creating and
updating pull requests needs a real token. App passwords no longer exist, so use a
repository access token:

1. Go to **Repository settings** → **Security** → **Access tokens**
2. Click **Create Repository Access Token**
3. Name it (e.g. `contiamo-release-please`)
4. Select scopes:
   - **Repositories: Write** (`repository:write`) – push the release branch and tags
   - **Pull requests: Write** (`pullrequest:write`) – create/update the release PR and
     read PR titles
5. Click **Create** and copy the token immediately; it is shown only once

If nobody on your side is a repository admin, ask the workspace or repository owner
to create the token. Workspace- and project-level access tokens also work (they are
a Premium feature). User-bound API tokens are not supported by the tool.

## 2. Store the Token as a Pipeline Variable

1. Go to **Repository settings** → **Pipelines** → **Repository variables**
2. Add a variable:
   - **Name**: `BITBUCKET_TOKEN`
   - **Value**: the access token
   - ✅ **Secured** (hides it in logs)

The pipeline reads `BITBUCKET_TOKEN` for both the API and `git push`.

## 3. Commit the Generated Files

```bash
git add bitbucket-pipelines.yml .bitbucket/ contiamo-release-please.yaml
git commit -m "chore: add release automation pipeline"
git push
```

Bitbucket only reads `bitbucket-pipelines.yml` at the repository root. If the
repository already has one, merge the `definitions` and `pipelines` sections from
the generated file into it.

## 4. Configure Branch Restrictions (recommended)

1. Go to **Repository settings** → **Branch restrictions** → **Add a branch restriction**
2. Branch: `main`
3. **Write access**: restrict pushes so changes only land via pull requests
4. **Merge settings** tab → **Merge checks**:
   - Enable **Minimum number of successful builds for the last commit**: `1`
   - (Premium only) **Prevent a merge with unresolved merge checks**

Without Premium, merge checks only warn; a PR with an invalid title can still be
merged. The release tool will then ignore that merge (its title is not a
conventional commit) and no version bump happens for it.

## 5. How It Works

- **Push to main**: the pipeline creates or updates a pull request from
  `release-please--branches--main` with the changelog and version bumps.
- **Merge the release PR**: Bitbucket writes the merge commit
  `Merged in release-please--branches--main (pull request #N)`. The pipeline sees
  that subject and runs `tag-release`, which creates and pushes the annotated tag.
- **Pull requests**: the title is validated against the conventional-commit format
  so that the merge commit (whose body carries the PR title) can be analysed.

Bitbucket Cloud has no release objects; the git tag is the release. Add a
`pipelines.tags` section to build or deploy from tags if needed.

## Notes on Bitbucket merge commits

Bitbucket Cloud always writes `Merged in <branch> (pull request #N)` as the merge
commit subject and puts the PR title into the body. The tool resolves the title via
the API (or from the body when no token is available), so **the PR title must be a
conventional commit**. Commit messages inside the PR do not matter when merging with
a merge commit or squash.
"""
