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

## Azure DevOps (Coming Soon)

Authentication for Azure DevOps will be documented when support is added.

---

## GitLab (Coming Soon)

Authentication for GitLab will be documented when support is added.

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
