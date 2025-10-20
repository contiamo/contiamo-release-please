# Authentication Guide

This document describes how to authenticate with different git hosting providers for automated pull request creation.

## GitHub

### Creating a Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give your token a descriptive name (e.g., "contiamo-release-please")
4. Select the required scopes:
   - For **private repositories**: Select `repo` (Full control of private repositories)
   - For **public repositories**: Select `public_repo` (Access public repositories)
5. Click "Generate token"
6. **Copy the token immediately** - you won't be able to see it again

### Using the Token

There are two ways to provide the GitHub token:

#### Option 1: Environment Variable (Recommended)

Set the `GITHUB_TOKEN` environment variable:

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
uv run contiamo-release-please release --git-host github
```

For CI/CD pipelines, add `GITHUB_TOKEN` as a secret environment variable in your workflow configuration.

#### Option 2: Configuration File

Add the token to your `contiamo-release-please.yaml`:

```yaml
github:
  token: "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**⚠️ Warning**: Do not commit tokens to version control. Use environment variables or secrets management for CI/CD.

### Required Permissions

The token needs:
- **Write access** to the repository
- **Ability to create pull requests**
- For private repos: `repo` scope
- For public repos: `public_repo` scope

### Testing Authentication

Test your authentication with a dry-run:

```bash
export GITHUB_TOKEN="your-token-here"
uv run contiamo-release-please release --git-host github --dry-run --verbose
```

This will show what would be done without making actual API calls.

---

## Azure DevOps

### Creating a Personal Access Token

1. Go to Azure DevOps → User Settings (top right) → Personal Access Tokens
2. Or visit directly: `https://dev.azure.com/{your-org}/_usersSettings/tokens`
3. Click "+ New Token"
4. Give your token a descriptive name (e.g., "contiamo-release-please")
5. Select organisation and expiration
6. Select the required scopes:
   - **Code**: Read & Write (required for creating and updating PRs)
7. Click "Create"
8. **Copy the token immediately** - you won't be able to see it again

### Using the Token

There are two ways to provide the Azure DevOps token:

#### Option 1: Environment Variable (Recommended)

Set the `AZURE_DEVOPS_TOKEN` environment variable:

```bash
export AZURE_DEVOPS_TOKEN="your-pat-token-here"
uv run contiamo-release-please release --git-host azure
```

For CI/CD pipelines, add `AZURE_DEVOPS_TOKEN` as a secret variable in your pipeline configuration.

#### Option 2: Configuration File

Add the token to your `contiamo-release-please.yaml`:

```yaml
azure:
  token: "your-pat-token-here"
```

**⚠️ Warning**: Do not commit tokens to version control. Use environment variables or Azure Key Vault for CI/CD.

### Required Permissions

The token needs:
- **Code (Read & Write)** scope
- Access to the specific project and repository

### Supported URL Formats

The tool auto-detects Azure DevOps from these remote URL formats:
- `https://dev.azure.com/org/project/_git/repo`
- `https://user@dev.azure.com/org/project/_git/repo`
- `git@ssh.dev.azure.com:v3/org/project/repo`
- `https://org.visualstudio.com/project/_git/repo` (legacy)

### Testing Authentication

Test your authentication with a dry-run:

```bash
export AZURE_DEVOPS_TOKEN="your-token-here"
uv run contiamo-release-please release --git-host azure --dry-run --verbose
```

This will show what would be done without making actual API calls.

---

## GitLab

GitLab supports two types of access tokens for automation. For CI/CD pipelines, **project access tokens are recommended**.

### Option 1: Project Access Token (Recommended for CI/CD)

Project access tokens are scoped to a specific project and are ideal for CI/CD automation.

1. Go to your project's Settings → Access Tokens
   - Direct URL: `https://{your-gitlab-instance}/{group}/{project}/-/settings/access_tokens`
2. Click "Add new token"
3. Fill in the token details:
   - **Token name**: Give your token a descriptive name (e.g., `ci-cd-for-this-repo`)
   - **Expiration date**: Set an expiration date (optional but recommended)
   - **Select a role**: **Maintainer** (required for creating merge requests and pushing tags)
   - **Select scopes**:
     - `api` - Full API access (required for creating MRs and releases)
     - `write_repository` - Push to repository (required for pushing tags)
4. Click "Create project access token"
5. **Copy the token immediately** - you won't be able to see it again

**Setting up in GitLab CI/CD:**

1. Go to Settings → CI/CD → Variables
2. Click "Add variable"
3. Fill in:
   - **Key**: `CICD_TOKEN` (or any name you prefer)
   - **Value**: Your project access token (e.g., `glpat-xxxxxxxxxxxxxxxxxxxx`)
   - **Type**: Variable
   - **Flags**:
     - ✓ Protected (recommended - only available on protected branches)
     - ✓ Masked (recommended - hidden in job logs)
4. Click "Add variable"

**Using in your pipeline:**

```yaml
variables:
  GITLAB_TOKEN: $CICD_TOKEN
```

**Configuring git remote for push access:**

GitLab CI provides built-in variables for constructing the remote URL:

```yaml
before_script:
  # Uses CI_SERVER_HOST (e.g., gitlab.com) and CI_PROJECT_PATH (e.g., group/project)
  - git remote set-url origin "https://oauth2:${CICD_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git"
```

This approach works for both gitlab.com and self-hosted GitLab instances without hardcoding URLs.

### Option 2: Personal Access Token

Personal access tokens are user-scoped and work across multiple projects.

1. Go to GitLab Settings → Access Tokens
   - For gitlab.com: Click your avatar → Preferences → Access Tokens
   - For self-hosted: `https://{your-gitlab-instance}/-/profile/personal_access_tokens`
2. Fill in the token details:
   - **Name**: Give your token a descriptive name (e.g., "contiamo-release-please")
   - **Expiration date**: Set an expiration date (optional but recommended)
   - **Select scopes**: Check the `api` scope (Full API access)
3. Click "Create personal access token"
4. **Copy the token immediately** - you won't be able to see it again

### Using the Token

Regardless of which token type you use (project or personal), there are two ways to provide it to the tool:

#### Environment Variable (Recommended)

Set the `GITLAB_TOKEN` environment variable:

```bash
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
uv run contiamo-release-please release --git-host gitlab
```

**For local development:**
```bash
export GITLAB_TOKEN="your-personal-access-token"
```

**For GitLab CI/CD pipelines:**
```yaml
variables:
  GITLAB_TOKEN: $CICD_TOKEN  # References the CI/CD variable created above
```

#### Configuration File (Not Recommended for CI)

Add the token to your `contiamo-release-please.yaml`:

```yaml
gitlab:
  token: "glpat-xxxxxxxxxxxxxxxxxxxx"
```

**⚠️ Warning**: Do not commit tokens to version control. Use environment variables or GitLab CI/CD variables for automation.

### Required Permissions

**For Project Access Tokens:**
- **Role**: Maintainer (required for creating merge requests, pushing tags, and creating releases)
- **Scopes**:
  - `api` - Full API access for creating merge requests and releases
  - `write_repository` - Push to repository (for tags and release branch)

**For Personal Access Tokens:**
- **Scope**: `api` - Full API access for creating merge requests, releases, and pushing tags
- **User permissions**: Must have Maintainer or Owner role in the project

### Supported URL Formats

The tool auto-detects GitLab from these remote URL formats:
- `https://gitlab.com/owner/repo.git`
- `https://gitlab.devops.telekom.de/group/subgroup/project.git`
- `git@gitlab.com:owner/repo.git`
- `git@gitlab.devops.telekom.de:group/subgroup/project.git`

### Custom GitLab Instances

This tool works with both gitlab.com and self-hosted GitLab instances. The host is automatically detected from your git remote URL.

For self-hosted instances, ensure:
- Your GitLab instance API is accessible from where the tool runs
- API endpoint is at `https://{your-gitlab-host}/api/v4`
- Your token has the required permissions

### Testing Authentication

Test your authentication with a dry-run:

```bash
export GITLAB_TOKEN="your-token-here"
uv run contiamo-release-please release --git-host gitlab --dry-run --verbose
```

This will show what would be done without making actual API calls.

---

## Troubleshooting

### "GitHub token not found"

Make sure you've either:
1. Set the `GITHUB_TOKEN` environment variable, OR
2. Added `github.token` to your config file

### "Failed to create pull request: 401"

Your token is invalid or expired. Generate a new token following the steps above.

### "Failed to create pull request: 403"

Your token doesn't have the required permissions. Make sure you've selected the correct scopes when creating the token.

### "Failed to create pull request: 404"

The repository doesn't exist or your token doesn't have access to it. Check:
1. The repository exists
2. Your token has access to the repository
3. For organisations, ensure the token has access to the organisation's repositories

### "Could not parse GitHub owner/repo from remote URL"

Your git remote URL is not in a recognised format. The tool supports:
- HTTPS: `https://github.com/owner/repo.git`
- SSH: `git@github.com:owner/repo.git`

Check your remote URL with:
```bash
git remote get-url origin
```

### "Azure DevOps token not found"

Make sure you've either:
1. Set the `AZURE_DEVOPS_TOKEN` environment variable, OR
2. Added `azure.token` to your config file

### "Could not parse Azure DevOps org/project/repo from remote URL"

Your git remote URL is not in a recognised Azure DevOps format. The tool supports:
- `https://dev.azure.com/org/project/_git/repo`
- `git@ssh.dev.azure.com:v3/org/project/repo`
- `https://org.visualstudio.com/project/_git/repo`

Check your remote URL with:
```bash
git remote get-url origin
```

### "GitLab token not found"

Make sure you've either:
1. Set the `GITLAB_TOKEN` environment variable, OR
2. Added `gitlab.token` to your config file

### "Could not parse GitLab host/project from remote URL"

Your git remote URL is not in a recognised GitLab format. The tool supports:
- `https://gitlab.com/owner/repo.git`
- `https://gitlab.devops.telekom.de/group/subgroup/project.git`
- `git@gitlab.com:owner/repo.git`
- `git@gitlab.devops.telekom.de:group/subgroup/project.git`

Check your remote URL with:
```bash
git remote get-url origin
```

Note: The URL must contain "gitlab" in the host name for auto-detection to work.
