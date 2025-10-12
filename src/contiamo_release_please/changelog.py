"""Changelog generation for contiamo-release-please."""

from datetime import datetime
from pathlib import Path

from contiamo_release_please.analyser import ParsedCommit, parse_commit_message
from contiamo_release_please.config import ReleaseConfig


def group_commits_by_section(
    commit_messages: list[str], config: ReleaseConfig
) -> dict[str, list[ParsedCommit]]:
    """Group commits by their changelog section.

    Args:
        commit_messages: List of commit message strings
        config: Release configuration

    Returns:
        Dictionary mapping section names to lists of parsed commits
    """
    sections = config.get_changelog_sections()

    # Create mapping from commit type to section name
    type_to_section: dict[str, str] = {}
    for section_config in sections:
        commit_type = section_config["type"]
        section_name = section_config["section"]
        type_to_section[commit_type] = section_name

    # Group commits by section
    grouped: dict[str, list[ParsedCommit]] = {}

    for message in commit_messages:
        parsed = parse_commit_message(message)
        commit_type = parsed["type"]

        # Skip unknown commit types
        if commit_type == "unknown":
            continue

        # Get section name for this commit type
        section_name = type_to_section.get(commit_type)
        if not section_name:
            continue

        # Add to grouped commits
        if section_name not in grouped:
            grouped[section_name] = []

        grouped[section_name].append(parsed)

    return grouped


def format_changelog_entry(
    version: str,
    grouped_commits: dict[str, list[ParsedCommit]],
    config: ReleaseConfig,
    date: str | None = None,
) -> str:
    """Format a changelog entry for a release.

    Args:
        version: Version number (without prefix)
        grouped_commits: Commits grouped by section
        config: Release configuration
        date: Date string (YYYY-MM-DD) or None for today

    Returns:
        Formatted changelog entry as markdown string
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    lines = [f"## [{version}] ({date})", ""]

    # Get section order from config
    sections = config.get_changelog_sections()
    section_order = [s["section"] for s in sections]

    # Remove duplicates whilst preserving order
    seen = set()
    section_order = [x for x in section_order if not (x in seen or seen.add(x))]

    # Add sections in order
    for section_name in section_order:
        if section_name not in grouped_commits:
            continue

        commits = grouped_commits[section_name]
        if not commits:
            continue

        lines.append(f"### {section_name}")
        lines.append("")

        # Add each commit as a bullet point
        for commit in commits:
            description = commit["description"]
            scope = commit["scope"]

            if scope:
                lines.append(f"* **{scope}**: {description}")
            else:
                lines.append(f"* {description}")

        lines.append("")

    return "\n".join(lines)


def extract_changelog_for_version(changelog_path: Path, version: str) -> str | None:
    """Extract the changelog entry for a specific version.

    Args:
        changelog_path: Path to changelog file
        version: Version number to extract (without prefix, e.g., "1.2.3")

    Returns:
        Changelog entry content (without the version header), or None if not found
    """
    if not changelog_path.exists():
        return None

    with open(changelog_path, "r") as f:
        content = f.read()

    lines = content.split("\n")

    # Find the version header line (e.g., "## [1.2.3] (2025-01-01)")
    version_header_pattern = f"## [{version}]"
    start_index = None

    for i, line in enumerate(lines):
        if line.startswith(version_header_pattern):
            start_index = i
            break

    if start_index is None:
        return None

    # Find the end of this version section (next ## header or end of file)
    end_index = len(lines)
    for i in range(start_index + 1, len(lines)):
        if lines[i].startswith("## "):
            end_index = i
            break

    # Extract the content (excluding the version header itself)
    entry_lines = lines[start_index + 1 : end_index]

    # Remove leading/trailing empty lines
    while entry_lines and entry_lines[0].strip() == "":
        entry_lines.pop(0)
    while entry_lines and entry_lines[-1].strip() == "":
        entry_lines.pop()

    return "\n".join(entry_lines) if entry_lines else None


def prepend_to_changelog(
    changelog_path: Path, new_entry: str, create_if_missing: bool = True
) -> None:
    """Prepend a new changelog entry to the changelog file.

    Args:
        changelog_path: Path to changelog file
        new_entry: New changelog entry to prepend
        create_if_missing: Create file if it doesn't exist (default: True)
    """
    # Read existing content
    if changelog_path.exists():
        with open(changelog_path, "r") as f:
            existing_content = f.read()
    else:
        if not create_if_missing:
            raise FileNotFoundError(f"Changelog file not found: {changelog_path}")
        existing_content = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"

    # Prepend new entry
    # If existing content has a header, insert after it
    if existing_content.startswith("# Changelog"):
        # Find the end of the header section (first ## or end of intro paragraph)
        lines = existing_content.split("\n")
        insert_position = 0

        for i, line in enumerate(lines):
            if line.startswith("## "):
                insert_position = i
                break
            if i > 0 and line.strip() == "" and i < len(lines) - 1:
                if lines[i + 1].strip() != "":
                    insert_position = i + 1

        if insert_position == 0:
            # No existing releases, append after header
            insert_position = len(lines)

        lines.insert(insert_position, new_entry)
        new_content = "\n".join(lines)
    else:
        # No header, just prepend
        new_content = new_entry + "\n" + existing_content

    # Write updated content
    with open(changelog_path, "w") as f:
        f.write(new_content)
