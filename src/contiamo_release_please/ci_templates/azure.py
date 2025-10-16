"""Azure DevOps pipeline templates for Contiamo Release Please."""

AZURE_CI_TEMPLATE = """variables:
  - name: IS_TAGGED_BUILD
    value: $[startsWith(variables['Build.SourceBranch'], 'refs/tags/')]
  - name: IS_RELEASE_PR_MERGE
    # Matches: "Merged PR X: chore(main): release 0.1.0"
    value: $[and(contains(variables['Build.SourceVersionMessage'], 'Merged PR'), and(contains(variables['Build.SourceVersionMessage'], 'chore(main)'), contains(variables['Build.SourceVersionMessage'], 'release')))]

pool:
  vmImage: ubuntu-latest

trigger:
  tags:
    include:
      - "*"
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
        fetchDepth: 0
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
        fetchDepth: 0
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
"""

AZURE_PR_VALIDATION_TEMPLATE = """# Azure DevOps PR Validation Pipeline
# Runs validation on all pull requests to main branch

trigger: none  # Don't trigger on commits

pr:
  branches:
    include:
      - main

jobs:
  - job: ValidatePRTitle
    displayName: 'Validate PR Title'
    steps:
      - checkout: self
        displayName: 'Checkout code'

      - bash: |
          # Install jq for JSON parsing
          if command -v sudo >/dev/null 2>&1; then
            sudo apt-get update && sudo apt-get install -y jq
          else
            apt-get update && apt-get install -y jq
          fi
        displayName: 'Install jq'

      - bash: |
          # Validate PR title
          .azure/scripts/validate-pr-title.sh
        displayName: 'Validate PR title format'
        env:
          SYSTEM_ACCESSTOKEN: $(System.AccessToken)
"""

AZURE_PR_VALIDATION_SCRIPT = """#!/bin/sh
set -e

# Check if this is a PR build
if [ -z "$SYSTEM_PULLREQUEST_PULLEREQUESTNUMBER" ]; then
    echo "✓ Not a pull request pipeline, skipping validation"
    exit 0
fi

# Get the PR title from Azure DevOps API
echo "Getting PR title from Azure DevOps API..."
PR_TITLE=$(curl -s \\
    -H "Authorization: Bearer $SYSTEM_ACCESSTOKEN" \\
    "$SYSTEM_COLLECTIONURI$SYSTEM_TEAMPROJECT/_apis/git/pullrequests/$SYSTEM_PULLREQUEST_PULLEREQUESTNUMBER?api-version=7.0" \\
    | jq -r '.title')

if [ -z "$PR_TITLE" ]; then
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
