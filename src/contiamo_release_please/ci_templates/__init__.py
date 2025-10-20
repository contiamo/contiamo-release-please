"""CI/CD pipeline templates for various platforms."""

from contiamo_release_please.ci_templates.azure import (
    AZURE_CI_TEMPLATE,
    AZURE_PR_VALIDATION_SCRIPT,
    AZURE_PR_VALIDATION_TEMPLATE,
)
from contiamo_release_please.ci_templates.github import GITHUB_WORKFLOW_TEMPLATE
from contiamo_release_please.ci_templates.gitlab import GITLAB_CI_TEMPLATE

__all__ = [
    "GITHUB_WORKFLOW_TEMPLATE",
    "AZURE_CI_TEMPLATE",
    "AZURE_PR_VALIDATION_TEMPLATE",
    "AZURE_PR_VALIDATION_SCRIPT",
    "GITLAB_CI_TEMPLATE",
]
