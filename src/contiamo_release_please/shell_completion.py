"""Shell completion script generation for Contiamo Release Please."""

from typing import Any

import click
from click.shell_completion import BashComplete, FishComplete, ZshComplete


def generate_completion_script(cli: click.Group, shell: str) -> str:
    """Generate shell completion script for the specified shell.

    Args:
        cli: Click CLI group to generate completions for
        shell: Shell type ('bash', 'zsh', or 'fish')

    Returns:
        Shell completion script as a string

    Raises:
        ValueError: If shell type is not supported
    """
    # Map shell names to Click completion classes
    shell_map: dict[str, type[Any]] = {
        "bash": BashComplete,
        "zsh": ZshComplete,
        "fish": FishComplete,
    }

    shell_lower = shell.lower()
    if shell_lower not in shell_map:
        raise ValueError(
            f"Unsupported shell: {shell}. Supported shells: {', '.join(shell_map.keys())}"
        )

    # Get the completion class
    completion_class = shell_map[shell_lower]

    # Create completion instance
    complete = completion_class(
        cli=cli,
        ctx_args={},
        prog_name="contiamo-release-please",
        complete_var="_CONTIAMO_RELEASE_PLEASE_COMPLETE",
    )

    # Generate and return the completion script
    return complete.source()
