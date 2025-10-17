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

### Creating a Personal Access Token

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

There are two ways to provide the GitLab token:

#### Option 1: Environment Variable (Recommended)

Set the `GITLAB_TOKEN` environment variable:

```bash
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
uv run contiamo-release-please release --git-host gitlab
```

For CI/CD pipelines, add `GITLAB_TOKEN` as a secret variable in your GitLab CI/CD settings.

#### Option 2: Configuration File

Add the token to your `contiamo-release-please.yaml`:

```yaml
gitlab:
  token: "glpat-xxxxxxxxxxxxxxxxxxxx"
```

**⚠️ Warning**: Do not commit tokens to version control. Use environment variables or GitLab CI/CD variables for automation.

### Required Permissions

The token needs:
- **API scope** - Full API access for creating merge requests and releases
- **Write access** to the repository

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
