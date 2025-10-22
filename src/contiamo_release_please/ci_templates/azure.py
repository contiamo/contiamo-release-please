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
# Runs validation on all pull requests to main branch via build policy
trigger: none # Only run via build policy

jobs:
  - job: ValidatePRTitle
    displayName: "Validate PR Title"
    steps:
      - checkout: self
        displayName: "Checkout code"

      - bash: |
          # Install jq for JSON parsing
          if command -v sudo >/dev/null 2>&1; then
            sudo apt-get update && sudo apt-get install -y jq
          else
            apt-get update && apt-get install -y jq
          fi
        displayName: "Install jq"
      - bash: |
          # Validate PR title
          .azure/scripts/validate-pr-title.sh
        displayName: "Validate PR title format"
        env:
          SYSTEM_ACCESSTOKEN: $(System.AccessToken)
"""

AZURE_PR_VALIDATION_SCRIPT = """#!/bin/sh
set -e

# Check if this is a PR build
if [ -z "$SYSTEM_PULLREQUEST_PULLREQUESTID" ]; then
    echo "✓ Not a pull request pipeline, skipping validation"
    exit 0
fi

# Get the PR title from Azure DevOps API
echo "Getting PR title from Azure DevOps API..."
# Extract repository name from BUILD_REPOSITORY_URI
# Format: https://org@dev.azure.com/org/project/_git/repo-name
REPO_NAME=$(echo "$BUILD_REPOSITORY_URI" | sed 's/.*\\/_git\\///')

# Extract project from BUILD_REPOSITORY_URI
# Format: https://org@dev.azure.com/org/project/_git/repo-name
PROJECT_NAME=$(echo "$BUILD_REPOSITORY_URI" | sed 's/.*\\.com\\/[^\\/]*\\///; s/\\/_git.*//')

PR_TITLE=$(curl -s \\
    -H "Authorization: Bearer $SYSTEM_ACCESSTOKEN" \\
    "${SYSTEM_COLLECTIONURI}${PROJECT_NAME}/_apis/git/repositories/${REPO_NAME}/pullrequests/${SYSTEM_PULLREQUEST_PULLREQUESTID}?api-version=7.1" \\
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

AZURE_BRANCH_POLICIES_README = """# Azure DevOps Branch Protection Configuration

## Prerequisites

- Your user should have the "Edit policies" permission in `Project Settings` > `Repos` > `Repositories` > `Security tab`
- The PR validation pipeline (`.azure/pr-validation.yaml`) must be committed to the repository

## Steps to Configure Branch Policies

### 1. Create the PR Validation Pipeline

Before you can add a build validation policy, you need to create the pipeline in Azure DevOps:

1. Go to your Azure DevOps project
2. Navigate to **Pipelines** → **Pipelines**
3. Click **New Pipeline** (or **Create Pipeline**)
4. Select your repository source
5. Choose **Existing Azure Pipelines YAML file**
6. Select the branch (usually `main`)
7. Select the path: `.azure/pr-validation.yaml`
8. Click **Continue**
9. Review the pipeline YAML
10. Click **Run** to create and validate the pipeline
11. Once successful, note the pipeline name (you'll need it in the next section)

### 2. Navigate to Branch Policies

1. Go to your Azure DevOps project
2. Navigate to **Repos** → **Branches**
3. Find the `main` branch
4. Click on the three dots (⋮) next to the branch name
5. Select **Branch policies**

### 3. Configure Required Policies

#### Enable Basic Policies

- ✅ **Require a minimum number of reviewers**: Set to at least 1
- ✅ **Check for linked work items**: Optional but recommended
- ✅ **Check for comment resolution**: Enable to ensure all comments are addressed
- ✅ **Block direct pushes**: Enable "Limit merge types" and allow only pull requests

#### Add Build Validation Policy

1. Under **Build Validation**, click **+ Add build policy**
2. Select the build pipeline: `pr-validation` (or the name of your PR validation pipeline from step 1)
3. Configure the policy:
   - **Display name**: "PR Validation - Title Format"
   - **Trigger**: Automatic (required)
   - **Policy requirement**: Required
   - **Build expiration**: After 12 hours (or your preference)
4. Click **Save**

### 4. Additional Recommended Policies

#### Automatically Include Reviewers (Optional)
- Add specific users or groups as automatic reviewers for critical paths

#### Path Filters (Optional)
- Add specific policies for certain file paths if needed

"""
