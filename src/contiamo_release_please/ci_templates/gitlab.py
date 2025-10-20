"""GitLab CI pipeline templates for Contiamo Release Please."""

GITLAB_CI_TEMPLATE = """stages:
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
"""
