"""Bootstrap CI/CD workflows for Contiamo Release Please."""

from pathlib import Path
from typing import Literal

from contiamo_release_please.ci_templates import (
    AZURE_BRANCH_POLICIES_README,
    AZURE_CI_TEMPLATE,
    AZURE_PR_VALIDATION_SCRIPT,
    AZURE_PR_VALIDATION_TEMPLATE,
    GITHUB_WORKFLOW_TEMPLATE,
    GITLAB_CI_TEMPLATE,
)
from contiamo_release_please.config import generate_config_template

Flavour = Literal["github", "azure", "gitlab"]


def create_github_workflows(base_path: Path, dry_run: bool = False) -> list[Path]:
    """Create GitHub Actions workflow files.

    Args:
        base_path: Base directory to create files in
        dry_run: If True, don't actually write files

    Returns:
        List of paths that were (or would be) created
    """
    workflows_dir = base_path / ".github" / "workflows"
    workflow_file = workflows_dir / "contiamo-release-please.yaml"

    if not dry_run:
        workflows_dir.mkdir(parents=True, exist_ok=True)
        workflow_file.write_text(GITHUB_WORKFLOW_TEMPLATE.strip() + "\n")

    return [workflow_file]


def create_azure_pipelines(base_path: Path, dry_run: bool = False) -> list[Path]:
    """Create Azure DevOps pipeline files.

    Args:
        base_path: Base directory to create files in
        dry_run: If True, don't actually write files

    Returns:
        List of paths that were (or would be) created
    """
    azure_dir = base_path / ".azure"
    scripts_dir = azure_dir / "scripts"

    ci_file = azure_dir / "ci.yaml"
    pr_validation_file = azure_dir / "pr-validation.yaml"
    validation_script = scripts_dir / "validate-pr-title.sh"
    readme_file = azure_dir / "README-BRANCH-POLICIES.md"

    if not dry_run:
        azure_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir.mkdir(parents=True, exist_ok=True)

        ci_file.write_text(AZURE_CI_TEMPLATE.strip() + "\n")
        pr_validation_file.write_text(AZURE_PR_VALIDATION_TEMPLATE.strip() + "\n")
        validation_script.write_text(AZURE_PR_VALIDATION_SCRIPT.strip() + "\n")
        readme_file.write_text(AZURE_BRANCH_POLICIES_README.strip() + "\n")

        # Make script executable
        validation_script.chmod(0o755)

    return [ci_file, pr_validation_file, validation_script, readme_file]


def create_gitlab_pipelines(base_path: Path, dry_run: bool = False) -> list[Path]:
    """Create GitLab CI pipeline files.

    Args:
        base_path: Base directory to create files in
        dry_run: If True, don't actually write files

    Returns:
        List of paths that were (or would be) created
    """
    ci_file = base_path / ".gitlab-ci.yml"

    if not dry_run:
        ci_file.write_text(GITLAB_CI_TEMPLATE.strip() + "\n")

    return [ci_file]


def create_config_file(base_path: Path, dry_run: bool = False) -> Path:
    """Create contiamo-release-please.yaml config file.

    Args:
        base_path: Base directory to create file in
        dry_run: If True, don't actually write file

    Returns:
        Path that was (or would be) created
    """
    config_file = base_path / "contiamo-release-please.yaml"

    if not dry_run:
        config_content = generate_config_template()
        config_file.write_text(config_content)

    return config_file


def bootstrap_flavour(
    flavour: Flavour, base_path: Path | None = None, dry_run: bool = False
) -> tuple[list[Path], str]:
    """Bootstrap CI/CD workflows for the specified flavour.

    Args:
        flavour: The CI/CD platform to bootstrap (github, azure, gitlab)
        base_path: Base directory to create files in (default: current directory)
        dry_run: If True, don't actually write files

    Returns:
        Tuple of (list of created file paths, post-generation instructions)

    Raises:
        ValueError: If flavour is not supported
    """
    if base_path is None:
        base_path = Path.cwd()

    created_files = []

    # Always create config file
    config_file = create_config_file(base_path, dry_run)
    created_files.append(config_file)

    if flavour == "github":
        workflow_files = create_github_workflows(base_path, dry_run)
        created_files.extend(workflow_files)

        instructions = """
Next Steps:

1. Review and customise the generated configuration file:
   - contiamo-release-please.yaml

2. Set up GitHub token:
   - Go to Settings → Secrets and variables → Actions
   - Create a new secret named 'CONTIAMO_CI_TOKEN'
   - Use a token with 'repo' scope (or 'public_repo' for public repos)
   - See https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token

3. Commit the generated files:
   git add .github/workflows/contiamo-release-please.yaml contiamo-release-please.yaml
   git commit -m "chore: add release automation workflow"
   git push

4. The workflow will run on the next push to main branch

For more information, see: CI_SETUP.md
"""

    elif flavour == "azure":
        pipeline_files = create_azure_pipelines(base_path, dry_run)
        created_files.extend(pipeline_files)

        instructions = """
Next Steps:

1. Review and customise the generated configuration file:
   - contiamo-release-please.yaml

2. Configure Azure DevOps CI pipeline:
   - Go to Pipelines → Create Pipeline
   - Select your repository
   - Choose "Existing Azure Pipelines YAML file"
   - Select '.azure/ci.yaml'
   - Click Continue and Run to create the pipeline

3. Grant permissions:
   - Go to Project Settings → Repositories → your repository
   - Go to Security tab
   - Find "Build Service" account
   - Grant "Contribute", "Create tag", and "Contribute to pull requests" permissions

4. Commit the generated files:
   git add .azure/ contiamo-release-please.yaml
   git commit -m "chore: add release automation pipelines"
   git push

5. Set up PR title validation:
   - See the .azure/README-BRANCH-POLICIES.md file for PR Title Validation setup instructions
   - This includes creating the PR validation pipeline and configuring branch policies

6. The CI pipeline will run on the next push to main branch

For more information, see: CI_SETUP.md
"""

    elif flavour == "gitlab":
        pipeline_files = create_gitlab_pipelines(base_path, dry_run)
        created_files.extend(pipeline_files)

        instructions = """
Next Steps:

1. Review and customise the generated configuration file:
   - contiamo-release-please.yaml
   - Update git.user-name and git.user-email fields

2. Set up GitLab CI/CD variable:
   - Go to Settings → Access Tokens
   - Create a new project access token with:
     * Name: "CICD Token" (or any name you prefer)
     * Role: Maintainer
     * Scopes: api, read_api, read_repository, write_repository
   - Copy the generated token
   - Go to Settings → CI/CD → Variables
   - Create a new variable named 'CICD_TOKEN' with the token value
   - Mark it as "Masked" (recommended for security)
   - See https://docs.gitlab.com/ee/user/project/settings/project_access_tokens.html

3. Commit the generated files:
   git add .gitlab-ci.yml contiamo-release-please.yaml
   git commit -m "chore: add release automation pipeline"
   git push

4. Configure merge request settings (recommended):
   - Go to Settings → Merge requests
   - Enable "Delete source branch" option
   - Enable "Squash commits when merging" for cleaner history

5. The pipeline will run on the next push to main branch

For more information, see: CI_SETUP.md
"""

    else:
        raise ValueError(
            f"Unknown flavour: {flavour}. Supported: github, azure, gitlab"
        )

    return created_files, instructions.strip()


def check_existing_files(files: list[Path]) -> list[Path]:
    """Check which files already exist.

    Args:
        files: List of file paths to check

    Returns:
        List of files that already exist
    """
    return [f for f in files if f.exists()]
